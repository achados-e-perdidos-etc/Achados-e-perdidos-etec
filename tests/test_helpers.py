import unittest
from datetime import datetime, timedelta
from utils.helpers import extrair_termos, calcular_dias_passados, sanitizar_texto, expandir_termos_semanticos, calcular_afinidade_semantica

class TestHelpers(unittest.TestCase):
    def test_extrair_termos(self):
        termos = extrair_termos("Perdi meu casaco azul na quadra")
        self.assertIn("casaco", termos)
        self.assertIn("azul", termos)
        self.assertNotIn("perdi", termos)

    def test_calcular_dias_90(self):
        dt = (datetime.now() - timedelta(days=95)).strftime("%d/%m/%Y")
        self.assertGreaterEqual(calcular_dias_passados(dt), 90)

    def test_expansao_semantica(self):
        expandidos = expandir_termos_semanticos({"moletom"})
        self.assertIn("casaco", expandidos)
        self.assertIn("blusa", expandidos)

    def test_afinidade_semantica(self):
        score, _ = calcular_afinidade_semantica("moletom azul", "casaco azul")
        self.assertGreater(score, 0.5)

if __name__ == '__main__':
    unittest.main()
