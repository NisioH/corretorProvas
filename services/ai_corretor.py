import os
import json
import time
from google import genai


class AICorretor:
    def __init__(self, chave_api):
        self.client = genai.Client(api_key=chave_api)
        self.modelo = 'gemini-3.5-flash'

    def _chamar_api_com_retentativa(self, payload, max_tentativas=3):
        for tentativa in range(max_tentativas):
            try:
                resposta = self.client.models.generate_content(
                    model=self.modelo,
                    contents=payload
                )
                return resposta
            except Exception as e:
                erro_str = str(e).lower()
                if "429" in erro_str or "quota" in erro_str or "503" in erro_str:
                    if tentativa < max_tentativas - 1:
                        time.sleep(15)
                        continue
                raise e

    def extrair_gabarito(self, conteudo_gabarito, disciplina):
        prompt = f"""
        Você é um assistente educacional especialista. A professora informou que esta prova é da disciplina de: {disciplina}.

        Sua tarefa é analisar o documento fornecido seguindo ESTA LÓGICA RIGOROSA EM DUAS ETAPAS:

        PASSO 1: VERIFICAÇÃO DE COERÊNCIA (Regra de Segurança)
        Avalie se o documento realmente pertence à disciplina de {disciplina}.
        - EXCEÇÃO: Se o documento for apenas uma lista genérica de letras e números (ex: 1-A, 2-B), ASSUMA QUE ESTÁ CORRETO E CONTINUE.
        - BLOQUEIO: Se o documento contiver textos, mapas, fórmulas ou palavras que CLARAMENTE pertencem a uma disciplina totalmente diferente (ex: enviou um mapa de Geografia, mas a disciplina informada foi Matemática), PARE A ANÁLISE IMEDIATAMENTE e retorne APENAS a seguinte frase exata:
        ERRO_DISCIPLINA_INCOMPATIVEL

        PASSO 2: EXTRAÇÃO DE REGRAS (Se aprovado no Passo 1)
        Se o documento for coerente com a disciplina ou for um gabarito genérico:
        1. Extraia cada questão e defina a regra clara para correção.
        2. Se for múltipla escolha, indique a letra correta. 
        3. Se for dissertativa/cálculo, indique as palavras-chave, conceitos ou passos esperados.

        Formate como um texto claro e direto que servirá como um "Manual de Correção" rigoroso.
        """

        resposta = self._chamar_api_com_retentativa([prompt, conteudo_gabarito])
        return resposta.text

    def corrigir_prova(self, conteudos_aluno, gabarito_extraido, disciplina):
        prompt = f"""
        Você é um assistente educacional RIGOROSO avaliando a prova escaneada de um aluno na disciplina de {disciplina}.
        Sua correção deve se basear EXCLUSIVAMENTE nas regras do gabarito oficial abaixo:

        GABARITO OFICIAL E CRITÉRIOS: 
        {gabarito_extraido}

        Instruções OBRIGATÓRIAS de avaliação:
        1. IDENTIFIQUE A MARCAÇÃO: Veja qual alternativa o aluno assinalou.
        2. EXIJA O DESENVOLVIMENTO: Se a questão exige cálculo ou justificativa, procure esse texto escrito à mão.
        3. REGRA ANTI-CHUTE: Se o aluno APENAS assinalou a alternativa correta, mas NÃO contém o desenvolvimento, classifique como "Parcialmente Correto" ou "Incorreto", indicando no feedback a ausência da resolução.
        4. AVALIE O ERRO: Verifique passo a passo.

        Devolva um JSON no formato:
        {{
          "Questão 1": {{"status": "Correto | Parcialmente Correto | Incorreto", "feedback": "Explicação rigorosa focada no erro, acerto e na presença/ausência do desenvolvimento."}}
        }}
        Retorne APENAS o JSON válido, sem formatação markdown.
        """

        payload = [prompt] + conteudos_aluno if isinstance(conteudos_aluno, list) else [prompt, conteudos_aluno]
        resposta = self._chamar_api_com_retentativa(payload)

        texto_limpo = resposta.text.strip().removeprefix('```json').removesuffix('```').strip()
        return json.loads(texto_limpo)