"""Autoria imutável e situação de cadastros, inclusive após exclusão do item."""
SCHEMA_CADASTROS = '''
ALTER TABLE itens ADD COLUMN IF NOT EXISTS email_cadastrador VARCHAR(150);
CREATE TABLE IF NOT EXISTS cadastros_itens (
    id BIGSERIAL PRIMARY KEY,
    item_id INTEGER UNIQUE REFERENCES itens(id) ON DELETE SET NULL,
    email_aluno VARCHAR(150) NOT NULL REFERENCES alunos(email) ON DELETE CASCADE,
    nome TEXT NOT NULL, categoria VARCHAR(50) NOT NULL,
    situacao VARCHAR(30) NOT NULL,
    enviado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS cadastros_conta_id ON cadastros_itens(email_aluno,id DESC);
CREATE OR REPLACE FUNCTION acompanhar_cadastro_item() RETURNS TRIGGER AS $$
DECLARE estado TEXT; anterior TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO notificacoes (email_aluno,evento,titulo,corpo)
            SELECT email_aluno,'cadastro','Seu cadastro foi atualizado',
                'Consulte Minha atividade para acompanhar a decisão da secretaria.'
            FROM cadastros_itens WHERE item_id=OLD.id;
        UPDATE cadastros_itens SET situacao=CASE WHEN OLD.aprovado IS FALSE THEN 'RECUSADO' ELSE 'REMOVIDO' END,
            atualizado_em=CURRENT_TIMESTAMP WHERE item_id=OLD.id;
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        -- A reserva/retirada altera o RM do item; nunca altera quem o encontrou.
        NEW.email_cadastrador := OLD.email_cadastrador;
    END IF;
    IF NEW.email_cadastrador IS NULL THEN RETURN NEW; END IF;
    estado := CASE WHEN NEW.aprovado IS FALSE THEN 'AGUARDANDO'
        WHEN UPPER(NEW.status) = 'ENTREGUE' THEN 'ENTREGUE'
        WHEN UPPER(NEW.status) = 'DOAÇÃO FEITA' THEN 'DOADO'
        WHEN UPPER(NEW.status) = 'PARA DOAÇÃO' THEN 'PARA DOAÇÃO'
        ELSE 'PUBLICADO' END;
    SELECT situacao INTO anterior FROM cadastros_itens WHERE item_id=NEW.id;
    IF anterior IS NOT NULL AND anterior <> estado THEN
        INSERT INTO notificacoes (email_aluno,evento,titulo,corpo) VALUES
            (NEW.email_cadastrador,'cadastro','Seu cadastro foi atualizado',
            'Consulte Minha atividade para acompanhar a situação do objeto.');
    END IF;
    INSERT INTO cadastros_itens (item_id,email_aluno,nome,categoria,situacao)
        VALUES (NEW.id, NEW.email_cadastrador, COALESCE(NEW.nome_item,NEW.descricao,''),NEW.categoria,estado)
        ON CONFLICT (item_id) DO UPDATE SET nome=EXCLUDED.nome,categoria=EXCLUDED.categoria,
            situacao=EXCLUDED.situacao,atualizado_em=CURRENT_TIMESTAMP;
    RETURN NEW;
END; $$ LANGUAGE plpgsql;
-- AFTER INSERT porque a FK do histórico exige que o item já exista.
DROP TRIGGER IF EXISTS cadastro_inserido ON itens;
CREATE TRIGGER cadastro_inserido AFTER INSERT ON itens FOR EACH ROW EXECUTE FUNCTION acompanhar_cadastro_item();
DROP TRIGGER IF EXISTS cadastro_atualizado ON itens;
CREATE TRIGGER cadastro_atualizado BEFORE UPDATE OR DELETE ON itens FOR EACH ROW EXECUTE FUNCTION acompanhar_cadastro_item();
'''
