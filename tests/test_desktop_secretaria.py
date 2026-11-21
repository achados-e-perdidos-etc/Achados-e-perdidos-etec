"""Lógica real do desktop com widgets e transporte controlados; dispensa monitor."""
import io
import pytest
pytest.importorskip("tkinter")
pytest.importorskip("qrcode")
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from PIL import Image
import desktop_secretaria as desktop


class Imediato:
    def executar(self,funcao,args,kwargs,modal=None):
        gen=funcao(*args,**kwargs)
        try:
            job=next(gen)
            while True:
                try:result=job.executar()
                except Exception as error:job=gen.throw(error)
                else:job=gen.send(result)
        except StopIteration:return


def app():
    obj=object.__new__(desktop.SecretariaApp)
    obj.tarefas=Imediato()
    obj.tree_entregues=MagicMock()
    obj.tree_entregues.selection.return_value=['linha']
    obj.tree_entregues.item.return_value={'values':[91,7,'Estojo','Ana','123','DS','Hoje']}
    obj.carregar_dados=MagicMock()
    return obj


def test_logo_usa_arquivo_exato_da_secretaria_web():
    path=desktop.caminho_logo_secretaria()
    assert path.name=='logo_secretaria.png' and path.is_file()
    with Image.open(path) as im:assert im.width>0 and im.height>0


def test_timeout_padrao_e_customizado():
    with patch.object(desktop.requests,'request') as request:
        desktop.requisicao_desktop('GET','https://teste.invalid/api/itens')
        assert request.call_args.kwargs['timeout']==(5,25)
        desktop.requisicao_desktop('POST','https://teste.invalid/api/ia',timeout=9)
        assert request.call_args.kwargs['timeout']==9


def test_historico_abre_item_pelo_id_do_objeto():
    obj=app();obj.itens_atuais=[{'id':7,'nome':'Estojo'}];obj.abrir_modal_detalhes_item=MagicMock()
    obj.abrir_detalhes_do_historico(None)
    obj.abrir_modal_detalhes_item.assert_called_once_with(item_direto=obj.itens_atuais[0])


def test_desfazer_e_excluir_usam_id_correto_e_pedem_confirmacao():
    obj=app();obj.tree_entregues.item.return_value=[91,7,'Estojo']
    with patch.object(desktop.messagebox,'askyesno',return_value=True) as confirm, patch.object(desktop,'requisicao_desktop') as req:
        req.return_value.status_code=200
        obj.desfazer_entrega();assert req.call_args.args[1].endswith('/api/itens/7/recusar')
        obj.excluir_entregue();assert req.call_args.args[1].endswith('/api/itens/7')
        assert 'permanentemente o objeto' in confirm.call_args.args[1]
    with patch.object(desktop.messagebox,'askyesno',return_value=False), patch.object(desktop,'requisicao_desktop') as req:
        obj.excluir_entregue();req.assert_not_called()


def test_compactacao_limita_tamanho_e_foto_invalida_nao_envia(tmp_path):
    import base64
    file=tmp_path/'foto.png';Image.new('RGB',(2400,1600),'blue').save(file)
    result=desktop.comprimir_foto_desktop(file)
    with Image.open(io.BytesIO(base64.b64decode(result.split(',')[1]))) as im:
        assert max(im.size)==1200 and im.format=='JPEG'
    assert desktop.comprimir_foto_desktop(tmp_path/'inexistente') is None


def test_doacao_nao_anuncia_sucesso_em_recusa_ou_falha_de_rede():
    obj=app();obj.tab_doacoes=MagicMock();commands=[]
    def button(*args,**kwargs):
        commands.append(kwargs['command']);return MagicMock()
    with patch.object(desktop.tk,'Frame'),patch.object(desktop.tk,'Label'),patch.object(desktop.tk,'Button',side_effect=button),patch.object(desktop.ttk,'Treeview'):
        obj.construir_tab_doacoes()
    with patch.object(desktop.messagebox,'askyesno',return_value=True),patch.object(desktop.messagebox,'showinfo') as info,patch.object(desktop.messagebox,'showerror') as erro,patch.object(desktop,'requisicao_desktop') as req:
        req.return_value.ok=False;commands[0]();info.assert_not_called();erro.assert_called_once()
        req.reset_mock();erro.reset_mock();req.side_effect=desktop.requests.Timeout();commands[0]()
        info.assert_not_called();erro.assert_called_once();assert req.call_count==1

def test_dashboard_ordena_por_quantidade_sem_depender_de_lista_desatualizada():
    obj=app()
    for key in ['lbl_stat_itens','lbl_stat_entregues','lbl_stat_doacoes','lbl_taxa_devolucao','lbl_distribuicao_cats']:setattr(obj,key,MagicMock())
    desktop.TOKEN_SECRETARIA='token-de-teste'
    with patch.object(desktop,'requisicao_desktop') as req:
        req.return_value.status_code=200
        req.return_value.json.return_value={'por_categoria':[{'categoria':'OUTROS','qtd':1},{'categoria':'ACESSÓRIOS','qtd':12}]}
        obj.carregar_dashboard()
    texto=obj.lbl_distribuicao_cats.config.call_args.kwargs['text']
    assert texto.index('ACESSÓRIOS: 12')<texto.index('OUTROS: 1')
    desktop.TOKEN_SECRETARIA=None
