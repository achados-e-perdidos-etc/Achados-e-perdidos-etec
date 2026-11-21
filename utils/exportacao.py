"""Células de planilha sem execução de fórmulas informadas por usuários."""
import csv
import unicodedata


def celula_planilha(valor):
    texto = '' if valor is None else str(valor)
    inicio = unicodedata.normalize('NFKC',texto).lstrip(' \t\r\n\v\f\ufeff\u200b')
    if inicio.startswith(('=','+','-','@')) or texto.startswith(('\t','\r','\n')):
        return "'" + texto
    return texto


def salvar_csv(caminho, cabecalho, linhas):
    with open(caminho,'w',newline='',encoding='utf-8-sig') as arquivo:
        writer = csv.writer(arquivo,delimiter=';',quoting=csv.QUOTE_ALL)
        writer.writerow([celula_planilha(v) for v in cabecalho])
        writer.writerows([celula_planilha(v) for v in linha] for linha in linhas)
