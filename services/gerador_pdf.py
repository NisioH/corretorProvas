from fpdf import FPDF


class GeradorRelatorioPDF:
    def __init__(self, professor, disciplina, turma):
        self.professor = professor
        self.disciplina = disciplina
        self.turma = turma
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)

    def _limpar_texto(self, texto):
        return str(texto).encode('latin-1', 'replace').decode('latin-1')

    def adicionar_pagina_aluno(self, nome_aluno, dados_correcao):
        self.pdf.add_page()

        # Título principal
        self.pdf.set_font("Arial", 'B', 16)
        self.pdf.cell(0, 10, self._limpar_texto("Relatório de Correção de Avaliação"), ln=True, align='C')
        self.pdf.ln(5)

        # Bloco de Cabeçalho (Professor, Disciplina, Turma e Aluno)
        self.pdf.set_font("Arial", 'B', 12)
        self.pdf.cell(0, 8, self._limpar_texto(f"Professor(a): {self.professor}"), ln=True)
        self.pdf.cell(0, 8, self._limpar_texto(f"Disciplina: {self.disciplina} | Turma: {self.turma}"), ln=True)
        self.pdf.cell(0, 8, self._limpar_texto(f"Aluno(a): {nome_aluno}"), ln=True)

        # Linha separadora
        self.pdf.line(10, 50, 200, 50)
        self.pdf.ln(5)

        for questao, detalhes in dados_correcao.items():
            status = self._limpar_texto(detalhes.get("status", "Não avaliado"))
            feedback = self._limpar_texto(detalhes.get("feedback", "Sem comentários"))

            self.pdf.set_font("Arial", 'B', 12)
            self.pdf.cell(0, 8, self._limpar_texto(f"{questao} - Status: {status}"), ln=True)

            self.pdf.set_font("Arial", '', 11)
            self.pdf.multi_cell(0, 6, self._limpar_texto(f"Feedback: {feedback}"))
            self.pdf.ln(5)

    def adicionar_pagina_erro(self, nome_aluno, erro):
        self.pdf.add_page()
        self.pdf.set_font("Arial", 'B', 14)
        self.pdf.cell(0, 10, self._limpar_texto(f"Aluno(a): {nome_aluno} - ERRO DE LEITURA"), ln=True)
        self.pdf.set_font("Arial", '', 12)
        self.pdf.cell(0, 10, self._limpar_texto(f"Detalhe: {erro}"), ln=True)

    def gerar_bytes(self):
        return bytes(self.pdf.output())