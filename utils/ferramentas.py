"""Filtros e documentos usados pelos dois painéis da secretaria."""
import base64,io,re
from datetime import datetime
from html import escape
from utils.catalogo import normalizar,data_encontrada,data_filtro

TIPOS={'INVENTARIO':'Inventário de objetos ativos','ENTREGAS':'Histórico de entregas','DOACOES':'Objetos destinados à doação','COMPLETO':'Catálogo completo'}


def id_etiqueta(valor):
    match=re.fullmatch(r'(?:ETEC-ITEM-)?([1-9][0-9]{0,9})',str(valor or '').strip())
    if not match or int(match[1])>2147483647:raise ValueError('Leia uma etiqueta ETEC-ITEM-ID válida ou informe o número do objeto.')
    return int(match[1])


def filtrar_itens(itens,filtros):
    inicio,fim=data_filtro(filtros.get('inicio')),data_filtro(filtros.get('fim'))
    if inicio and fim and inicio>fim:raise ValueError('A data inicial deve vir antes da final.')
    categoria=filtros.get('categoria','TODOS');status=filtros.get('status','TODOS');q=normalizar(filtros.get('q','')).split();local=normalizar(filtros.get('local',''))
    rows=[]
    for item in itens:
        st=item.get('status') or 'DISPONÍVEL';data=data_encontrada((item.get('txt_data') or item.get('data_entrega') or '')[:10])
        texto=normalizar(' '.join(str(item.get(k) or '') for k in ['id','nome','txt_descricao','txt_local','nome_item','retirado_por','rm_retirante']))
        if categoria not in ('TODOS','') and normalizar(item.get('categoria'))!=normalizar(categoria):continue
        if status not in ('TODOS','') and st!=status:continue
        if local not in normalizar(item.get('txt_local')) or not all(t in texto for t in q):continue
        if inicio and (not data or data<inicio):continue
        if fim and (not data or data>fim):continue
        rows.append(item)
    return rows


def cabecalho_documento(titulo):
    from utils.comprovantes import logo_documento
    return '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(titulo)+'''</title><style>
    *{box-sizing:border-box}body{font:13px/1.6 system-ui,sans-serif;color:#172033;background:#eef1f6;padding:24px;margin:0}main{max-width:1050px;margin:auto;background:white;padding:28px}h1{font-size:22px}h2{font-size:21px;letter-spacing:-.025em;color:#172033}.marca-relatorio{display:flex;gap:12px;align-items:center;padding:16px 20px;background:#151c28;color:white;border-radius:12px;border-top:4px solid #dc2626;margin-bottom:20px}.marca-relatorio img{width:48px;height:48px;border-radius:12px}.marca-relatorio strong{display:block;font-size:17px;letter-spacing:.03em}.marca-relatorio small{display:block;color:#fda4af;font-size:10px;letter-spacing:.12em}.tela-relatorio{color:#b91c1c;font-size:10px;letter-spacing:.12em;font-weight:bold}table{border-collapse:collapse;width:100%;font-size:11px}th,td{padding:8px;border:1px solid #cbd5e1;text-align:left;overflow-wrap:anywhere}th{background:#fff1f3;color:#9f1239;border-bottom:2px solid #dc2626}tbody tr:nth-child(even){background:#f8fafc}tr{break-inside:avoid}.controles{max-width:1050px;margin:0 auto 20px}.controles button{padding:12px 18px;background:#b91c1c;color:white;border:0;border-radius:8px;font-weight:bold;cursor:pointer}.folha{break-after:page;display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.folha:last-child{break-after:auto}.etiqueta{border:1px dashed #64748b;padding:12px;break-inside:avoid;overflow:hidden}.etiqueta img{width:100px;height:100px;display:block}.etiqueta p{margin:3px 0;font-size:10px;overflow-wrap:anywhere}
    @media print{@page{size:A4;margin:12mm}.controles{display:none}body,main{padding:0;margin:0;background:white;max-width:none}table{font-size:9px}thead{display:table-header-group}.marca-relatorio,.marca-relatorio *{-webkit-print-color-adjust:exact;print-color-adjust:exact}.folha{grid-template-rows:repeat(5,38mm);gap:2mm;break-inside:avoid}.etiqueta{padding:3mm}.etiqueta img{float:left;width:19mm;height:19mm;margin:0 2mm 2mm 0}.etiqueta strong{font-size:9pt}.etiqueta p{font-size:7.5pt;line-height:1.2}}
    </style></head><body><div class="controles"><button type="button" onclick="window.print()">Imprimir / Salvar como PDF</button></div><main><header class="marca-relatorio"><img alt="Logo secretaria" src="data:image/png;base64,'''+logo_documento()+'''"><div><strong>ETEC ACHADOS</strong><small>SECRETARIA · ACHADOS E PERDIDOS</small></div></header><p class="tela-relatorio">CUIDADO COM O QUE É SEU</p><h2>'''+escape(titulo)+'</h2>'


def documento_relatorio(itens,tipo,filtros):
    if tipo not in TIPOS:raise ValueError('Tipo de relatório inválido.')
    rows=filtrar_itens(itens,filtros)
    if tipo=='INVENTARIO':rows=[i for i in rows if i.get('status') in ['DISPONÍVEL','SOLICITADO']]
    if tipo=='DOACOES':rows=[i for i in rows if normalizar(i.get('status')) in ['para doacao','doacao feita']]
    if tipo=='ENTREGAS':
        headers=['Recibo','Objeto','Nome do objeto','Recebido por','RM','Turma','Data de entrega','Responsável','Situação']
        linhas=[[i.get('id'),i.get('item_id'),i.get('nome_item'),i.get('retirado_por'),i.get('rm_retirante'),i.get('turma_curso'),i.get('data_entrega'),i.get('funcionario_responsavel'),'REVERTIDA' if i.get('cancelada_em') else 'ATIVA'] for i in rows]
    else:
        headers=['ID','Nome','Descrição','Categoria','Local','Data encontrada','Situação','Solicitante','RM']
        linhas=[[i.get(k) for k in ['id','nome','txt_descricao','categoria','txt_local','txt_data','status','solicitado_por','rm_aluno']] for i in rows]
    esc=lambda v:escape(str(v if v is not None else ''))
    html=cabecalho_documento(TIPOS[tipo])+'<p>Emitido em '+datetime.now().strftime('%d/%m/%Y %H:%M')+' · '+str(len(rows))+' registros. Filtros: '+esc(', '.join(f'{k}: {v}' for k,v in filtros.items() if v and v!='TODOS'))+'</p><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in linha)+'</tr>' for linha in linhas)+'</tbody></table><p>Relação dos registros consultados no sistema. Não substitui conferência ou assinatura da escola.</p></main></body></html>'
    return dict(html=html,cabecalho=headers,linhas=linhas,total=len(rows))


def qr_png(item_id):
    import qrcode
    out=io.BytesIO();qrcode.make('ETEC-ITEM-'+str(id_etiqueta(item_id))).save(out,format='PNG');return out.getvalue()


def documento_etiquetas(itens):
    html=cabecalho_documento('Etiquetas dos objetos')
    for inicio in range(0,len(itens),15):
        html+='<section class="folha">'
        for i in itens[inicio:inicio+15]:
            html+='<article class="etiqueta"><img alt="Etiqueta QR" src="data:image/png;base64,'+base64.b64encode(qr_png(i['id'])).decode()+'"><strong>Objeto #'+str(i['id'])+'</strong><p>'+escape(str(i.get('nome') or ''))+'</p><p>'+escape(str(i.get('categoria') or ''))+'</p><p>'+escape(str(i.get('txt_local') or ''))+'</p></article>'
        html+='</section>'
    return html+'</main></body></html>'


def folha_etiquetas_png(itens,pagina=1):
    from PIL import Image,ImageDraw,ImageFont
    if type(pagina) is not int or pagina<1 or (pagina-1)*15>=len(itens):raise ValueError('Página de etiquetas não encontrada.')
    folha=Image.new('RGB',(1240,1754),'white');draw=ImageDraw.Draw(folha)
    try:fonte=ImageFont.truetype('DejaVuSans.ttf',18)
    except OSError:fonte=ImageFont.load_default()
    draw.text((45,25),f'ETEC · Etiquetas de objetos · Página {pagina}',font=fonte,fill='black')
    for idx,item in enumerate(itens[(pagina-1)*15:pagina*15]):
        x=45+(idx%3)*390;y=80+(idx//3)*325;draw.rectangle((x,y,x+375,y+305),outline='#64748b',width=2)
        with Image.open(io.BytesIO(qr_png(item['id']))) as qr:folha.paste(qr.resize((185,185)),(x+10,y+12))
        draw.text((x+205,y+30),'#'+str(item['id']),font=fonte,fill='black')
        draw.text((x+10,y+210),str(item.get('nome') or '')[:31],font=fonte,fill='black')
        draw.text((x+10,y+240),str(item.get('categoria') or '')[:31],font=fonte,fill='black')
        draw.text((x+10,y+270),str(item.get('txt_local') or '')[:31],font=fonte,fill='black')
    out=io.BytesIO();folha.save(out,format='PNG');return out.getvalue()
