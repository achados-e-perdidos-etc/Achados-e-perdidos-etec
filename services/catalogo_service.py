"""Páginas pequenas do catálogo público e candidatos a duplicidade para a equipe."""
import json,re
from datetime import timedelta
from difflib import SequenceMatcher
from urllib.parse import urlsplit
from utils.catalogo import normalizar,data_filtro,data_encontrada,escapar_like
from utils.privacy import item_publico
from utils.validacao_item import texto

CAMPOS = '''id,COALESCE(nome_item,descricao) AS nome,descricao AS txt_descricao,
 categoria,data_encontrado AS txt_data,local_encontrado AS txt_local,
 CASE WHEN left(foto,8)='https://' OR left(foto,7)='http://' THEN foto ELSE '' END AS foto,
 CASE WHEN octet_length(COALESCE(fotos_json,''))<=8192 THEN fotos_json ELSE NULL END AS fotos_json,
 status,COALESCE(aprovado,TRUE) AS aprovado,COALESCE(cadastrado_por_aluno,FALSE) AS cadastrado_por_aluno'''


def foto_miniatura(url):
    if not isinstance(url,str):return ''
    try:parsed=urlsplit(url)
    except ValueError:return ''
    if parsed.scheme=='https' and parsed.hostname=='res.cloudinary.com' and '/image/upload/' in parsed.path:
        return url.replace('/image/upload/','/image/upload/c_limit,w_480,h_360,q_auto:eco,f_auto/',1)
    return url


def preparar_publico(row):
    out=item_publico(row)
    fotos=[u for u in (out.get('fotos',[]) if isinstance(out.get('fotos'),list) else []) if isinstance(u,str) and len(u)<=2048 and u.startswith(('https://','http://'))][:4]
    if not fotos and out.get('foto'):fotos=[out['foto']]
    out['fotos']=fotos;out['foto']=fotos[0] if fotos else '';out.pop('fotos_json',None)
    out['miniatura']=foto_miniatura(out['foto'])
    return out


def pagina(cursor,args):
    try:
        limite=int(args.get('limite','24'))
        antes=int(args['antes']) if args.get('antes') else None
        teto=int(args['teto']) if args.get('teto') else None
    except (ValueError,TypeError):raise ValueError('Página inválida.') from None
    if not 1<=limite<=48 or any(v is not None and not 0<v<=2147483647 for v in [antes,teto]):raise ValueError('Página inválida.')
    inicio,fim=data_filtro(args.get('inicio')),data_filtro(args.get('fim'))
    if inicio and fim and inicio>fim:raise ValueError('A data inicial deve vir antes da final.')
    cond=['aprovado IS NOT FALSE'];params=[]
    busca=args.get('q','').strip();local=args.get('local','').strip();categoria=args.get('categoria','').strip();status=args.get('status','TODOS').strip()
    if len(busca)>120 or len(local)>100 or len(categoria)>50:raise ValueError('O filtro é muito longo.')
    if status not in ['TODOS','DISPONÍVEL','SOLICITADO','ENTREGUE','PARA DOAÇÃO','DOAÇÃO FEITA']:raise ValueError('Situação inválida.')
    for termo in normalizar(busca).split()[:8]:
        cond.append("etec_normalizar(COALESCE(nome_item,'')||' '||descricao||' '||local_encontrado) LIKE %s")
        params.append('%'+escapar_like(termo)+'%')
    if local:cond.append('etec_normalizar(local_encontrado) LIKE %s');params.append('%'+escapar_like(normalizar(local))+'%')
    if categoria and categoria!='TODOS':cond.append('etec_normalizar(categoria)=etec_normalizar(%s)');params.append(categoria)
    if status!='TODOS':cond.append('status=%s');params.append(status)
    if inicio:cond.append('etec_data(data_encontrado)>=%s');params.append(inicio)
    if fim:cond.append('etec_data(data_encontrado)<=%s');params.append(fim)
    if antes:cond.append('id<%s');params.append(antes)
    if teto:cond.append('id<=%s');params.append(teto)
    cursor.execute('SELECT '+CAMPOS+' FROM itens WHERE '+' AND '.join(cond)+' ORDER BY id DESC LIMIT %s',(*params,limite+1))
    rows=cursor.fetchall();tem_mais=len(rows)>limite;rows=rows[:limite]
    return dict(success=True,itens=[preparar_publico(row) for row in rows],tem_mais=tem_mais,
      proximo=rows[-1]['id'] if rows and tem_mais else None,teto=teto or (rows[0]['id'] if rows else None),limite=limite)


def dados_duplicidade(dados):
    if not isinstance(dados,dict):raise ValueError('Confira os campos do objeto.')
    nome=texto(dados.get('nome'),'Título',150);categoria=texto(dados.get('categoria'),'Categoria',50)
    data=data_encontrada(dados.get('data'))
    if not data:raise ValueError('Informe uma data válida para conferir duplicidade.')
    return nome,categoria,data


def duplicados(cursor,dados,excluir=None):
    nome,categoria,data=dados_duplicidade(dados)
    palavras=set(re.findall(r'[a-z0-9]+',normalizar(nome)))-{'de','do','da','com','sem','um','uma','objeto','item'}
    if not palavras:return []
    maior=max(palavras,key=len)
    cursor.execute('''SELECT id,COALESCE(nome_item,descricao) AS nome,categoria,data_encontrado AS txt_data,status,aprovado
     FROM itens WHERE etec_normalizar(categoria)=etec_normalizar(%s) AND recusado_em IS NULL
      AND etec_data(data_encontrado) BETWEEN %s AND %s AND (%s::int IS NULL OR id<>%s)
      AND etec_normalizar(COALESCE(nome_item,descricao)) LIKE %s ORDER BY id DESC LIMIT 200''',
      (categoria,data-timedelta(days=7),data+timedelta(days=7),excluir,excluir,'%'+escapar_like(maior[:3])+'%'))
    encontrados=[]
    for item in cursor.fetchall():
        termos=set(re.findall(r'[a-z0-9]+',normalizar(item['nome'])))-{'de','do','da','com','sem','um','uma','objeto','item'}
        uniao=palavras|termos
        jaccard=len(palavras&termos)/len(uniao) if uniao else 0
        score=max(jaccard,SequenceMatcher(None,normalizar(nome),normalizar(item['nome'])).ratio())
        if score>=.67:encontrados.append({**item,'semelhanca':round(score*100)})
    return sorted(encontrados,key=lambda v:(-v['semelhanca'],-v['id']))[:5]
