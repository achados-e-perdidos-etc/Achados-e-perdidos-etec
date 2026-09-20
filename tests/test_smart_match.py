"""
Testes Unitários do Algoritmo Heurístico de Smart Matching
Testa a pontuação de categoria, palavras-chave, cores e locais.
"""
import unittest
from utils.smart_match import calcular_smart_match

class TestSmartMatch(unittest.TestCase):
    def test_match_perfeito(self):
        relato = {
            "categoria": "ROUPAS",
            "descricao": "Casaco moletom preto com zíper no pátio"
        }
        item = {
            "nome": "Casaco Moletom Preto",
            "categoria": "ROUPAS",
            "descricao": "Casaco moletom preto com zíper no pátio",
            "local_encontrado": "pátio"
        }
        score, motivos = calcular_smart_match(relato, item)
        # Acumula categoria (30) + 100% dos termos (40) + cor preto (15) + local pátio (15) = 100 pts
        self.assertEqual(score, 100)
        self.assertTrue(any("Mesma categoria" in m for m in motivos))
        self.assertTrue(any("Cor compatível: preto" in m for m in motivos))
        self.assertTrue(any("Local compatível (pátio)" in m for m in motivos))

    def test_match_parcial_alta_relevancia(self):
        relato = {
            "categoria": "ROUPAS",
            "descricao": "Perdi meu casaco moletom preto com zíper no pátio perto do refeitório"
        }
        item = {
            "nome": "Casaco Moletom Preto",
            "categoria": "ROUPAS",
            "descricao": "Moletom preto com zíper encontrado no pátio",
            "local_encontrado": "pátio"
        }
        score, motivos = calcular_smart_match(relato, item)
        # Termos cobrem a maior parte do relato (~89 pts)
        self.assertGreaterEqual(score, 80)
        self.assertLessEqual(score, 95)
        self.assertTrue(any("Mesma categoria" in m for m in motivos))

    def test_match_apenas_categoria(self):
        relato = {
            "categoria": "ELETRÔNICOS",
            "descricao": "Perdi fone de ouvido bluetooth branco"
        }
        item = {
            "nome": "Carregador Samsung",
            "categoria": "ELETRÔNICOS",
            "descricao": "Carregador tipo C preto",
            "local_encontrado": "laboratório 3"
        }
        score, motivos = calcular_smart_match(relato, item)
        # Deve ter apenas os 30 pontos de categoria
        self.assertEqual(score, 30)
        self.assertEqual(len(motivos), 1)
        self.assertIn("Mesma categoria (ELETRÔNICOS)", motivos[0])

    def test_match_totalmente_diferente(self):
        relato = {
            "categoria": "ESCOLARES",
            "descricao": "Perdi estojo Faber-Castell verde com canetas"
        }
        item = {
            "nome": "Blusa de Lã",
            "categoria": "ROUPAS",
            "descricao": "Blusa vermelha tamanho M",
            "local_encontrado": "quadra"
        }
        score, motivos = calcular_smart_match(relato, item)
        self.assertEqual(score, 0)
        self.assertEqual(len(motivos), 0)

    def test_match_cor_e_termos_com_categoria_diferente(self):
        relato = {
            "categoria": "ACESSÓRIOS",
            "descricao": "Garrafa térmica azul de metal"
        }
        item = {
            "nome": "Garrafa squeeze azul",
            "categoria": "OUTROS",
            "descricao": "Garrafa de água azul",
            "local_encontrado": "corredor"
        }
        score, motivos = calcular_smart_match(relato, item)
        # Categoria diferente (0), mas termos ("garrafa") + cor ("azul") devem somar pontos
        self.assertGreater(score, 20)
        self.assertTrue(any("Cor compatível: azul" in m for m in motivos))

if __name__ == '__main__':
    unittest.main()
