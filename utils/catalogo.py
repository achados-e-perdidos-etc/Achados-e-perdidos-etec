"""Busca normalizada e datas legadas seguras, sem extensões extras do PostgreSQL."""
import re
import unicodedata
from datetime import datetime,date


def normalizar(valor):
    return ''.join(c for c in unicodedata.normalize('NFD',str(valor or '').lower()) if not unicodedata.combining(c))


def data_encontrada(valor):
    if not isinstance(valor,str):return None
    for formato,padrao in [('%d/%m/%Y',r'\d{2}/\d{2}/\d{4}'),('%Y-%m-%d',r'\d{4}-\d{2}-\d{2}')]:
        if re.fullmatch(padrao,valor):
            try:return datetime.strptime(valor,formato).date()
            except ValueError:return None
    return None


def data_filtro(valor):
    if not valor:return None
    if not isinstance(valor,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',valor):raise ValueError('Informe uma data válida.')
    try:return date.fromisoformat(valor)
    except ValueError:raise ValueError('Informe uma data válida.') from None


def escapar_like(texto):
    return texto.replace('\\','\\\\').replace('%',r'\%').replace('_',r'\_')


SCHEMA_CATALOGO=r'''
ALTER TABLE itens ADD COLUMN IF NOT EXISTS versao INTEGER NOT NULL DEFAULT 1;
CREATE OR REPLACE FUNCTION etec_normalizar(TEXT) RETURNS TEXT AS $$
 SELECT translate(lower(COALESCE($1,'')),'áàâãäåéèêëíìîïóòôõöúùûüçñýÿ','aaaaaaeeeeiiiiooooouuuucnyy');
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE;
CREATE OR REPLACE FUNCTION etec_data(TEXT) RETURNS DATE AS $$
DECLARE resultado DATE;
BEGIN
 IF $1 ~ '^\d{2}/\d{2}/\d{4}$' THEN
  resultado:=to_date($1,'DD/MM/YYYY');
  IF to_char(resultado,'DD/MM/YYYY')=$1 THEN RETURN resultado; END IF;
 ELSIF $1 ~ '^\d{4}-\d{2}-\d{2}$' THEN
  resultado:=to_date($1,'YYYY-MM-DD');
  IF to_char(resultado,'YYYY-MM-DD')=$1 THEN RETURN resultado; END IF;
 END IF;
 RETURN NULL;
EXCEPTION WHEN OTHERS THEN RETURN NULL;
END; $$ LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE;
CREATE INDEX IF NOT EXISTS catalogo_publicado_id ON itens(id DESC) WHERE aprovado IS NOT FALSE;
CREATE INDEX IF NOT EXISTS catalogo_categoria_id ON itens(etec_normalizar(categoria),id DESC) WHERE aprovado IS NOT FALSE;
CREATE INDEX IF NOT EXISTS catalogo_data_id ON itens(etec_data(data_encontrado),id DESC) WHERE aprovado IS NOT FALSE;
CREATE INDEX IF NOT EXISTS itens_moderacao_id ON itens(id DESC) WHERE aprovado IS FALSE;
CREATE OR REPLACE FUNCTION versao_item() RETURNS TRIGGER AS $$
BEGIN
 IF (to_jsonb(OLD)-'versao') IS DISTINCT FROM (to_jsonb(NEW)-'versao') THEN NEW.versao:=OLD.versao+1;
 ELSE NEW.versao:=OLD.versao; END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS zz_versao_item ON itens;
CREATE TRIGGER zz_versao_item BEFORE UPDATE ON itens FOR EACH ROW EXECUTE FUNCTION versao_item();
CREATE OR REPLACE FUNCTION auditar_item() RETURNS TRIGGER AS $$
DECLARE antes JSONB; depois JSONB; identidade TEXT; papel TEXT;
BEGIN
 identidade:=COALESCE(NULLIF(current_setting('etec.ator_id',true),''),'sistema');
 papel:=COALESCE(NULLIF(current_setting('etec.perfil',true),''),'sistema');
 IF TG_OP<>'INSERT' THEN
  antes:=jsonb_build_object('status',OLD.status,'aprovado',OLD.aprovado,'nome',OLD.nome_item,
   'descricao',OLD.descricao,'categoria',OLD.categoria,'local',OLD.local_encontrado,'data',OLD.data_encontrado,
   'fotos',COALESCE(OLD.fotos_json,OLD.foto),'motivo_recusa',OLD.motivo_recusa,'versao',OLD.versao);
 END IF;
 IF TG_OP<>'DELETE' THEN
  depois:=jsonb_build_object('status',NEW.status,'aprovado',NEW.aprovado,'nome',NEW.nome_item,
   'descricao',NEW.descricao,'categoria',NEW.categoria,'local',NEW.local_encontrado,'data',NEW.data_encontrado,
   'fotos',COALESCE(NEW.fotos_json,NEW.foto),'motivo_recusa',NEW.motivo_recusa,'versao',NEW.versao);
 END IF;
 IF TG_OP<>'UPDATE' OR to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
  INSERT INTO ocorrencias_itens(item_id,acao,ator_id,perfil,anterior,atual)
   VALUES(COALESCE(NEW.id,OLD.id),TG_OP,identidade,papel,antes,depois);
 END IF;
 IF TG_OP<>'DELETE' AND NEW.aprovado IS TRUE AND NEW.status='DISPONÍVEL' THEN
  INSERT INTO matches_pendentes(item_id) VALUES(NEW.id) ON CONFLICT DO NOTHING;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
END; $$ LANGUAGE plpgsql;
'''
