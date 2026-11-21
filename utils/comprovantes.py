"""Comprovante local do desktop: HTML escapado e diálogo de impressão do navegador."""
import base64
import io
from functools import lru_cache
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
import webbrowser


@lru_cache(maxsize=1)
def logo_documento():
    from PIL import Image
    with Image.open(Path(__file__).resolve().parent.parent/'logo_secretaria.png') as img:
        img.thumbnail((156,156));out=io.BytesIO();img.save(out,format='PNG',optimize=True)
    return base64.b64encode(out.getvalue()).decode()


def corpo_comprovante(dados,assinatura=None,aguardar_assinatura=False):
    esc=lambda v:escape(str(v if v not in (None,'') else 'Não informado'))
    logo=logo_documento()
    objetos='''<div class="comp-objetos" aria-hidden="true"><span><svg viewBox="0 0 32 40"><path d="M8 12V9a8 8 0 0 1 16 0v3M6 13h20v23H6zM10 24h12v8H10zM10 17h12"/></svg></span><span><svg viewBox="0 0 32 40"><path d="M12 3h8v5l4 5v22H8V13l4-5zM12 3h8M9 18h14M10 29h12"/></svg></span><span><svg viewBox="0 0 32 40"><path d="M5 26V16a11 11 0 0 1 22 0v10M5 19H2v13h7V19zM27 19h3v13h-7V19z"/></svg></span></div>'''
    html='<article class="comp-documento"><header class="comp-cabecalho"><div class="comp-marca"><img class="comp-logo" alt="Logo da secretaria ETEC" src="data:image/png;base64,'+logo+'"><div><strong>ETEC ACHADOS</strong><small>SECRETARIA · ACHADOS E PERDIDOS</small></div></div><div class="comp-numero">REGISTRO DE ENTREGA<strong>'+('#'+esc(dados['id']) if dados.get('id') else 'Retirada')+'</strong></div></header>'
    html+='<section class="comp-apresentacao"><div><p>UM REENCONTRO REGISTRADO</p><h2>Comprovante de entrega</h2><small>Cuidado com o que é seu. Compromisso de todos.</small></div>'+objetos+'</section>'
    if dados.get('cancelada_em'):html+='<div class="comprovante-revertido"><strong>ENTREGA REVERTIDA</strong>Em '+esc(dados['cancelada_em'])+' por '+esc(dados.get('cancelada_por'))+'. Este registro não representa uma entrega ativa.</div>'
    html+='<section class="comp-objeto"><span>OBJETO #'+esc(dados.get('item_id'))+'</span><h3>'+esc(dados.get('nome_item'))+'</h3></section><dl class="comp-campos">'
    campos=[('Recebido por',dados.get('retirado_por')),('Registro de matrícula (RM)',dados.get('rm_retirante')),('Turma / curso',dados.get('turma_curso')),('Entrega registrada em',dados.get('data_entrega')),('Responsável pelo registro',dados.get('funcionario_responsavel')),('Forma de registro','Código e aceite presencial' if dados.get('metodo')=='CODIGO' else 'Registro pela secretaria')]
    html+=''.join('<div><dt>'+esc(nome)+'</dt><dd>'+esc(valor)+'</dd></div>' for nome,valor in campos)+'</dl><section class="comp-aceite"><h3>Aceite de recebimento</h3>'
    if assinatura:html+='<p>Assinatura ou aceite registrado durante a retirada.</p><img class="comp-assinatura" alt="Assinatura ou aceite registrado no recebimento" src="data:image/jpeg;base64,'+base64.b64encode(assinatura).decode()+'">'
    elif aguardar_assinatura:html+='<p>Assinatura ou aceite registrado durante a retirada.</p><div data-aceite></div>'
    else:html+='<p>Este registro não possui assinatura digitalizada.</p>'
    return html+'</section><footer class="comp-rodape"><span><strong>Achados, cuidados, devolvidos.</strong><br>ETEC · Comunidade escolar</span><span>Registro interno da entrega. As informações correspondem ao cadastro consultado pela secretaria.</span></footer></article>'


def gerar_html_comprovante(dados,assinatura=None):
    css=(Path(__file__).resolve().parent.parent/'comprovantes.css').read_text(encoding='utf-8')
    return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comprovante de entrega — ETEC</title><style>'+css+'''body{font-family:system-ui,sans-serif;background:#eef1f6;margin:0;padding:24px}main{max-width:820px;margin:auto}.comp-controles{max-width:820px;margin:0 auto 16px;font-size:12px;color:#526077}.comp-controles button{font:600 14px system-ui;background:#b91c1c;color:white;border:0;border-radius:8px;padding:12px 20px;cursor:pointer}.comp-controles button:focus-visible{outline:3px solid #1d4ed8;outline-offset:4px}@media print{body{padding:0;background:white}main{max-width:none}.comprovante-papel{border:0;padding:0;border-radius:0}.comp-controles{display:none}}</style></head><body><div class="comp-controles"><button type="button" onclick="window.print()">Imprimir comprovante</button><p>Escolha a impressora na janela de impressão, ou use Salvar como PDF.</p></div><main class="comprovante-papel">'''+corpo_comprovante(dados,assinatura)+'</main></body></html>'


def abrir_impressao_desktop(dados,assinatura=None):
    pasta=TemporaryDirectory(prefix='etec-comprovante-')
    try:
        arquivo=Path(pasta.name)/'comprovante.html'
        arquivo.write_text(gerar_html_comprovante(dados,assinatura),encoding='utf-8')
        arquivo.chmod(0o600)
        if not webbrowser.open(arquivo.as_uri(),new=2):raise RuntimeError('Não foi possível abrir o navegador para imprimir. Confira o navegador padrão do computador.')
        return pasta
    except Exception:
        pasta.cleanup();raise


def abrir_documento_local(html):
    pasta=TemporaryDirectory(prefix='etec-documento-')
    try:
        arquivo=Path(pasta.name)/'documento.html';arquivo.write_text(html,encoding='utf-8');arquivo.chmod(0o600)
        if not webbrowser.open(arquivo.as_uri(),new=2):raise RuntimeError('Não foi possível abrir o navegador padrão para imprimir.')
        return pasta
    except Exception:pasta.cleanup();raise
