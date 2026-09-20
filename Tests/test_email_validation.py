"""
Testes Unitários de Validação de E-mail Institucional
Garante conformidade com o novo padrão @aluno.cps.sp.gov.br e domínios do Centro Paula Souza.
"""
import unittest
from utils.helpers import validar_email_institucional

class TestEmailValidation(unittest.TestCase):
    def test_email_aluno_cps_valido(self):
        valido, email = validar_email_institucional("gustavo.cardoso@aluno.cps.sp.gov.br")
        self.assertTrue(valido)
        self.assertEqual(email, "gustavo.cardoso@aluno.cps.sp.gov.br")

    def test_email_servidor_cps_valido(self):
        valido, email = validar_email_institucional("coordenacao@cps.sp.gov.br")
        self.assertTrue(valido)
        self.assertEqual(email, "coordenacao@cps.sp.gov.br")

    def test_email_etec_legado_valido(self):
        valido, email = validar_email_institucional("secretaria.etec@etec.sp.gov.br")
        self.assertTrue(valido)
        self.assertEqual(email, "secretaria.etec@etec.sp.gov.br")

    def test_email_com_espacos_e_maiusculas(self):
        valido, email = validar_email_institucional("  NOME.ALUNO@ALUNO.CPS.SP.GOV.BR  ")
        self.assertTrue(valido)
        self.assertEqual(email, "nome.aluno@aluno.cps.sp.gov.br")

    def test_emails_comuns_invalidos(self):
        dominios_invalidos = [
            "gustavo@gmail.com",
            "aluno123@hotmail.com",
            "teste@outlook.com",
            "estudante@yahoo.com.br"
        ]
        for end in dominios_invalidos:
            valido, msg = validar_email_institucional(end)
            self.assertFalse(valido, f"E-mail {end} não deveria ser aceito.")
            self.assertIn("Apenas e-mails institucionais", msg)

    def test_entradas_malformadas(self):
        entradas_ruins = ["", None, "não-um-email", "@aluno.cps.sp.gov.br", "aluno@"]
        for e in entradas_ruins:
            valido, msg = validar_email_institucional(e)
            self.assertFalse(valido, f"Entrada '{e}' deveria falhar na validação.")

if __name__ == '__main__':
    unittest.main()
