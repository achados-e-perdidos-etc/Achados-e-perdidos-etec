"""Comprovante local do desktop: HTML escapado e diálogo de impressão do navegador."""
import base64
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
import webbrowser


def gerar_html_comprovante(dados,assinatura=None):
    campos=[('Comprovante',dados.get('id') or 'Registro de entrega'),('Objeto',f"#{dados.get('item_id','')} · {dados.get('nome_item','')}"),
      ('Recebido por',dados.get('retirado_por')),('RM',dados.get('rm_retirante')),('Turma / curso',dados.get('turma_curso')),
      ('Entrega registrada em',dados.get('data_entrega')),('Responsável',dados.get('funcionario_responsavel'))]
    conteudo=''.join(f'<div><dt>{escape(nome)}</dt><dd>{escape(str(valor or "Não informado"))}</dd></div>' for nome,valor in campos)
    aviso=''
    if dados.get('cancelada_em'):
        aviso='<p class="revertida">ENTREGA REVERTIDA em '+escape(str(dados['cancelada_em']))+' por '+escape(str(dados.get('cancelada_por') or 'Não informado'))+'. Este registro não representa uma entrega ativa.</p>'
    aceite=('<h3>Aceite de recebimento</h3><img alt="Assinatura ou aceite registrado no recebimento" src="data:image/jpeg;base64,'+base64.b64encode(assinatura).decode()+'">') if assinatura else '<p>Este registro não possui assinatura digitalizada.</p>'
    return '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comprovante de entrega — ETEC</title><style>
    *{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;color:#172033;background:#edf0f5;margin:0;padding:24px}main{max-width:780px;margin:auto;padding:32px;background:white;border:1px solid #d1d9e4;border-radius:12px}h1{font-size:24px;margin:0}h2{font-size:18px}h3{font-size:15px}dl>div{padding:10px 0;border-bottom:1px solid #dde3ec;break-inside:avoid}dt{font-size:12px;font-weight:bold;color:#475569}dd{margin:3px 0;white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%;max-height:180px;object-fit:contain}p{font-size:13px}.revertida{border:2px solid #991b1b;color:#991b1b;padding:12px;font-weight:bold}.controles{max-width:780px;margin:0 auto 20px}button{font:600 14px system-ui;background:#b91c1c;color:white;border:0;border-radius:8px;padding:14px 22px;cursor:pointer}button:focus-visible{outline:3px solid #1d4ed8;outline-offset:4px}@media print{@page{size:A4;margin:15mm}.controles{display:none}body{background:white;padding:0;margin:0;font-size:11pt}main{border:0;border-radius:0;padding:0;max-width:none}img{max-height:45mm;break-inside:avoid}}
    </style></head><body><div class="controles"><button type="button" onclick="window.print()">Imprimir comprovante</button><p>Escolha a impressora na janela de impressão, ou use Salvar como PDF.</p></div><main><h1>ETEC · Achados e Perdidos</h1><h2>Comprovante de entrega</h2><dl>'''+conteudo+'</dl>'+aviso+aceite+'</main></body></html>'


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
