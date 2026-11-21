SCHEMA_RETENCAO = '''ALTER TABLE mensagens_chat ADD COLUMN IF NOT EXISTS criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS mensagens_data_retencao ON mensagens_chat(criada_em,id);'''
