"""Migrações idempotentes: auditoria, retirada, alertas e envios offline."""
SCHEMA_EVOLUCAO = r'''
CREATE TABLE IF NOT EXISTS ocorrencias_itens (
 id BIGSERIAL PRIMARY KEY, item_id INTEGER NOT NULL, acao VARCHAR(12) NOT NULL,
 ator_id VARCHAR(150) NOT NULL, perfil VARCHAR(30) NOT NULL,
 criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 anterior JSONB, atual JSONB
);
CREATE INDEX IF NOT EXISTS ocorrencias_item_id ON ocorrencias_itens(item_id,id DESC);
CREATE TABLE IF NOT EXISTS retiradas_codigos (
 item_id INTEGER PRIMARY KEY REFERENCES itens(id) ON DELETE CASCADE,
 email VARCHAR(150) NOT NULL, nonce UUID NOT NULL, expira_em TIMESTAMPTZ NOT NULL,
 tentativas INTEGER NOT NULL DEFAULT 0, usado_em TIMESTAMPTZ,
 requisicao UUID, responsavel VARCHAR(150)
);
ALTER TABLE entregues ADD COLUMN IF NOT EXISTS assinatura BYTEA;
ALTER TABLE entregues ADD COLUMN IF NOT EXISTS confirmada_em TIMESTAMPTZ;
ALTER TABLE entregues ADD COLUMN IF NOT EXISTS metodo VARCHAR(20) DEFAULT 'ATENDIMENTO';
CREATE TABLE IF NOT EXISTS requisicoes_portal (
 email VARCHAR(150) NOT NULL, chave UUID NOT NULL, tipo VARCHAR(20) NOT NULL,
 hash VARCHAR(64) NOT NULL, resposta JSONB,
 criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(email,chave)
);
CREATE TABLE IF NOT EXISTS matches_pendentes (
 item_id INTEGER PRIMARY KEY REFERENCES itens(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS matches_avisados (
 item_id INTEGER NOT NULL, relato_id INTEGER NOT NULL,
 email VARCHAR(150) NOT NULL, criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(item_id,email)
);
CREATE OR REPLACE FUNCTION auditar_item() RETURNS TRIGGER AS $$
DECLARE antes JSONB; depois JSONB; identidade TEXT; papel TEXT;
BEGIN
 identidade := COALESCE(NULLIF(current_setting('etec.ator_id',true),''),'sistema');
 papel := COALESCE(NULLIF(current_setting('etec.perfil',true),''),'sistema');
 IF TG_OP <> 'INSERT' THEN
   antes := jsonb_build_object('status',OLD.status,'aprovado',OLD.aprovado,'nome',OLD.nome_item,
        'categoria',OLD.categoria,'local',OLD.local_encontrado);
 END IF;
 IF TG_OP <> 'DELETE' THEN
   depois := jsonb_build_object('status',NEW.status,'aprovado',NEW.aprovado,'nome',NEW.nome_item,
        'categoria',NEW.categoria,'local',NEW.local_encontrado);
 END IF;
 IF TG_OP <> 'UPDATE' OR to_jsonb(OLD) IS DISTINCT FROM to_jsonb(NEW) THEN
   INSERT INTO ocorrencias_itens(item_id,acao,ator_id,perfil,anterior,atual)
      VALUES(COALESCE(NEW.id,OLD.id),TG_OP,identidade,papel,antes,depois);
 END IF;
 IF TG_OP <> 'DELETE' AND NEW.aprovado IS TRUE AND NEW.status='DISPONÍVEL' THEN
   INSERT INTO matches_pendentes(item_id) VALUES(NEW.id) ON CONFLICT DO NOTHING;
 END IF;
 IF TG_OP='DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS item_auditado ON itens;
CREATE TRIGGER item_auditado AFTER INSERT OR UPDATE OR DELETE ON itens
 FOR EACH ROW EXECUTE FUNCTION auditar_item();
CREATE OR REPLACE FUNCTION procurar_para_relato() RETURNS TRIGGER AS $$
BEGIN
 INSERT INTO matches_pendentes(item_id) SELECT id FROM itens
  WHERE aprovado IS TRUE AND status='DISPONÍVEL' AND categoria=NEW.categoria ON CONFLICT DO NOTHING;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS relato_match ON mural_perdidos;
CREATE TRIGGER relato_match AFTER INSERT ON mural_perdidos
 FOR EACH ROW EXECUTE FUNCTION procurar_para_relato();
CREATE OR REPLACE FUNCTION preservar_ocorrencias() RETURNS TRIGGER AS $$
BEGIN RAISE EXCEPTION 'O histórico de ocorrências não pode ser alterado.'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS preservar_ocorrencias_itens ON ocorrencias_itens;
CREATE TRIGGER preservar_ocorrencias_itens BEFORE UPDATE OR DELETE ON ocorrencias_itens
 FOR EACH ROW EXECUTE FUNCTION preservar_ocorrencias();
'''


def contextualizar(conexao):
    # A conexão não é reutilizada entre requisições. O contexto permanece após commit.
    from flask import has_request_context, request
    if has_request_context() and getattr(request, 'user', {}).get('email'):
        user = request.user
        with conexao.cursor() as cursor:
            cursor.execute("SELECT set_config('etec.ator_id',%s,false),set_config('etec.perfil',%s,false)",
                           (user['email'], user.get('perfil') or user.get('role') or 'aluno'))
    return conexao
