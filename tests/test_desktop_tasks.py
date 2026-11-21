import pytest
pytest.importorskip("tkinter")
import threading,time
from types import SimpleNamespace
from unittest.mock import MagicMock
from desktop_tasks import TarefasDesktop,Trabalho

class Root:
    def after(self,*a):return 'timer'
    def after_cancel(self,*a):pass

def test_io_fora_do_tk_retorno_na_thread_principal_e_ignora_sessao_antiga():
    owner=SimpleNamespace(root=Root(),status_operacao=MagicMock(),erro_operacao=MagicMock())
    tasks=TarefasDesktop(owner);event=threading.Event();threads=[];vistos=[]
    def io():threads.append(threading.get_ident());event.wait(2);return 'dados'
    def carregar_teste():
        valor=yield Trabalho(io)
        vistos.append((valor,threading.get_ident()))
    tasks.executar(carregar_teste,(),{})
    assert vistos==[]
    event.set()
    for _ in range(100):
        tasks._receber()
        if not tasks.ativos:break
        time.sleep(.01)
    assert vistos==[('dados',threading.get_ident())] and threads[0]!=threading.get_ident()
    event.clear();tasks.executar(carregar_teste,(),{});tasks.invalidar();event.set();time.sleep(.05);tasks._receber()
    assert len(vistos)==1
    tasks.fechar()

def test_falha_de_leitura_fica_visivel_e_pode_tentar_novamente():
    owner=SimpleNamespace(root=Root(),status_operacao=MagicMock(),erro_operacao=MagicMock())
    tasks=TarefasDesktop(owner);tentativas=[]
    def io():
        tentativas.append(1)
        if len(tentativas)==1:raise OSError('offline')
        return 2
    def carregar_teste():yield Trabalho(io)
    for iniciar in [lambda:tasks.executar(carregar_teste,(),{}),tasks.repetir]:
        iniciar()
        for _ in range(100):
            tasks._receber()
            if not tasks.ativos:break
            time.sleep(.01)
    assert len(tentativas)==2
    assert any('Tentar novamente' in c.args[0] for c in owner.status_operacao.call_args_list)
    tasks.fechar()
