SCHEMA_UPLOADS = '''CREATE TABLE IF NOT EXISTS uploads_fotos (
 id UUID PRIMARY KEY, email VARCHAR(150) NOT NULL, tamanho INTEGER NOT NULL,
 sha256 VARCHAR(64) NOT NULL, recebidos INTEGER NOT NULL DEFAULT 0,
 url TEXT,
 atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS uploads_partes (
 upload_id UUID NOT NULL REFERENCES uploads_fotos(id) ON DELETE CASCADE,
 posicao INTEGER NOT NULL, conteudo BYTEA NOT NULL, PRIMARY KEY(upload_id,posicao));
CREATE INDEX IF NOT EXISTS uploads_fotos_conta ON uploads_fotos(email);
CREATE INDEX IF NOT EXISTS uploads_fotos_data ON uploads_fotos(atualizado_em);'''
