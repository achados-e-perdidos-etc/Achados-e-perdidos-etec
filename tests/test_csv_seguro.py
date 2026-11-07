import csv,io
import pytest
from utils.exportacao import celula_planilha,salvar_csv

@pytest.mark.parametrize('valor',['=SUM(1;2)','+1','-3','@SUM(A1)',' \t=1','\ufeff=1','＝1','\ntexto'])
def test_celulas_perigosas_neutralizadas(valor):assert celula_planilha(valor).startswith("'")

def test_csv_preserva_aspas_separadores_e_quebras(tmp_path):
    file=tmp_path/'relatorio.csv';valores=['Nome; com "aspas"','duas\nlinhas',0,None,'=1']
    salvar_csv(file,['Título'],[valores])
    with file.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f,delimiter=';'))
    assert rows[1]==['Nome; com "aspas"','duas\nlinhas','0','',"'=1"]
