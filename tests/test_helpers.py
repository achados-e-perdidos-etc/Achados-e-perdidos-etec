"""
Testes Unitários para Funções Utilitárias Gerais
"""
import unittest
from datetime import datetime, timedelta
from utils.helpers import extrair_termos, calcular_dias_passados, sanitizar_texto

class TestHelpers(unittest.TestCase):
    def test_extrair_termos_basico(self):
        texto = "Perdi meu casaco azul com zíper na quadra de esportes"
        termos = extrair_termos(texto)
        # Stopwords como 'perdi', 'meu', 'com', 'na', 'de' devem ser removidas
        self.assertNotIn("perdi", termos)
        self.assertNotIn("meu", termos)
        self.assertNotIn("com", termos)
        # Palavras relevantes devem estar presentes
        self.assertIn("casaco", termos)
        self.assertIn("azul", termos)
        self.assertIn("quadra", termos)
        self.assertIn("esportes", termos)

    def test_extrair_termos_vazio(self):
        self.assertEqual(extrair_termos(""), set())
        self.assertEqual(extrair_termos(None), set())

    def test_calcular_dias_passados_hoje(self):
        hoje_str = datetime.now().strftime("%d/%m/%Y")
        dias = calcular_dias_passados(hoje_str)
        self.assertEqual(dias, 0)

    def test_calcular_dias_passados_90_dias(self):
        data_passada = datetime.now() - timedelta(days=95)
        data_str = data_passada.strftime("%d/%m/%Y")
        dias = calcular_dias_passados(data_str)
        self.assertGreaterEqual(dias, 94)

    def test_calcular_dias_passados_invalido(self):
        self.assertEqual(calcular_dias_passados("data-invalida"), 0)
        self.assertEqual(calcular_dias_passados(None), 0)

    def test_sanitizar_texto(self):
        texto_sujo = "Caderno ETEC\x00\x08 teste com caracteres"
        sanitizado = sanitizar_texto(texto_sujo)
        self.assertNotIn("\x00", sanitizado)
        self.assertNotIn("\x08", sanitizado)
        self.assertTrue(sanitizado.startswith("Caderno ETEC"))

if __name__ == '__main__':
    unittest.main()
