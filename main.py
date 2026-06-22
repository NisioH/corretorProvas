import streamlit as st
import os
import re
import time
from collections import defaultdict

from google.genai import types  # <-- NOVA IMPORTAÇÃO AQUI

from services.ai_corretor import AICorretor
from services.gerador_pdf import GeradorRelatorioPDF

st.set_page_config(page_title="Corretor Escolar Inteligente", page_icon="📝", layout="wide")

st.title("📝 Assistente de Correção Escolar")
st.write("---")

# ==========================================
# 1. RECUPERAÇÃO SILENCIOSA DA CHAVE (SECRETS)
# ==========================================
try:
    chave_api = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    chave_api = os.environ.get("GEMINI_API_KEY")

if not chave_api:
    st.error(
        "🚨 Ocorreu um erro de configuração no servidor: Chave da IA não encontrada. Avise o administrador do sistema.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    nome_professor = st.text_input("Nome do Professor(a):", placeholder="Ex: Ana Lúcia")
with col2:
    disciplina = st.text_input("Disciplina:", placeholder="Ex: Matemática, Português...")
with col3:
    turma = st.text_input("Turma/Série:", placeholder="Ex: 8º Ano A")

st.write("---")

# ==========================================
# 2. MOTOR DA APLICAÇÃO
# ==========================================
if nome_professor and disciplina and turma:

    corretor = AICorretor(chave_api=chave_api)

    if "gabarito_extraido" not in st.session_state:
        st.session_state["gabarito_extraido"] = None

    st.header("1️⃣ Configurar o Gabarito")
    arquivo_gabarito = st.file_uploader("Selecione a prova oficial resolvida (Gabarito)",
                                        type=["pdf", "jpg", "jpeg", "png"], key="upload_gabarito")

    if arquivo_gabarito and st.button("Ler e Salvar Gabarito"):
        with st.spinner(f"Extraindo regras com o Gemini..."):
            try:
                mime_type = "application/pdf" if arquivo_gabarito.type == "application/pdf" else "image/jpeg"

                # CORREÇÃO AQUI: Usando types.Part.from_bytes em vez de dicionário
                conteudo_gabarito = types.Part.from_bytes(
                    data=arquivo_gabarito.read(),
                    mime_type=mime_type
                )

                resultado_extracao = corretor.extrair_gabarito(conteudo_gabarito, disciplina)

                if "ERRO_DISCIPLINA_INCOMPATIVEL" in resultado_extracao:
                    st.error(f"🚨 ALERTA: O conteúdo não condiz com a disciplina de {disciplina}.")
                    st.session_state["gabarito_extraido"] = None
                else:
                    st.session_state["gabarito_extraido"] = resultado_extracao
                    st.success("Gabarito memorizado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler gabarito: {e}")

    # ==========================================
    # 3. CORREÇÃO DOS ALUNOS E FILA INTELIGENTE
    # ==========================================
    if st.session_state["gabarito_extraido"]:
        with st.expander("👀 Ver Gabarito Memorizado"):
            st.write(st.session_state["gabarito_extraido"])
            if st.button("🗑️ Limpar Gabarito Atual (Trocar de Prova)"):
                st.session_state["gabarito_extraido"] = None
                st.rerun()

        st.write("---")

        st.header("2️⃣ Corrigir Provas e Gerar Relatórios")
        arquivos_alunos = st.file_uploader("Arraste as provas/fotos dos alunos para cá",
                                           type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True,
                                           key="upload_alunos")

        if arquivos_alunos and st.button("Corrigir e Gerar PDF"):
            gerador_pdf = GeradorRelatorioPDF(nome_professor, disciplina, turma)

            provas_por_aluno = defaultdict(list)
            for arquivo in arquivos_alunos:
                nome_base = os.path.splitext(arquivo.name)[0]
                match_num = re.search(r'(?:_|-| )?(?:pg|pag|página|p)?(\d+)$', nome_base, flags=re.IGNORECASE)
                num_pagina = int(match_num.group(1)) if match_num else 1

                nome_limpo = re.sub(r'(_|-| )?(pg|pag|página|p)?\d+$', '', nome_base, flags=re.IGNORECASE)
                nome_limpo = nome_limpo.replace("_", " ").strip().title()

                conteudo_bytes = arquivo.read()
                mime_type = "application/pdf" if arquivo.type == "application/pdf" else "image/jpeg"

                provas_por_aluno[nome_limpo].append((num_pagina, conteudo_bytes, mime_type))

            total_alunos = len(provas_por_aluno)

            tempo_estimado_seg = total_alunos * 8
            minutos = tempo_estimado_seg // 60
            segundos = tempo_estimado_seg % 60

            st.info(
                f"☕ Lote de **{total_alunos} alunos** detectado! Para respeitar os limites da versão gratuita, o sistema fará pausas automáticas. **Tempo estimado: {minutos}m e {segundos}s.** Pode ir tomar uma água!")

            barra_progresso = st.progress(0)
            texto_status = st.empty()

            for index, (nome_aluno, lista_paginas) in enumerate(provas_por_aluno.items()):
                lista_paginas.sort(key=lambda x: x[0])

                # CORREÇÃO AQUI: Transformando a lista em objetos Part
                conteudos_ordenados = [
                    types.Part.from_bytes(data=conteudo, mime_type=mime)
                    for num, conteudo, mime in lista_paginas
                ]

                texto_status.markdown(f"⏳ **Corrigindo prova de:** {nome_aluno} ({index + 1}/{total_alunos})...")

                try:
                    dados_correcao = corretor.corrigir_prova(conteudos_ordenados, st.session_state["gabarito_extraido"],
                                                             disciplina)
                    gerador_pdf.adicionar_pagina_aluno(nome_aluno, dados_correcao)
                except Exception as e:
                    gerador_pdf.adicionar_pagina_erro(nome_aluno, str(e))

                barra_progresso.progress((index + 1) / total_alunos)

                if index < total_alunos - 1:
                    for s in range(5, 0, -1):
                        texto_status.markdown(
                            f"🛑 Resfriando os motores da IA gratuita... Próximo aluno em **{s} segundos**.")
                        time.sleep(1)

            texto_status.markdown("✅ **Relatório em PDF gerado com sucesso!**")
            st.success("Tudo pronto! Baixe o relatório completo abaixo:")

            st.download_button(
                label="🖨️ Baixar Relatórios para Impressão",
                data=gerador_pdf.gerar_bytes(),
                file_name=f"Correcoes_{turma.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

else:
    st.info("👆 Por favor, preencha o nome do professor, disciplina e turma para destravar o sistema.")