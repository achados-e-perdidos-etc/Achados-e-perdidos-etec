"""Histórico por conta; independente da permissão Web Push do dispositivo."""
SCHEMA_NOTIFICACOES = '''CREATE TABLE IF NOT EXISTS notificacoes (
    id BIGSERIAL PRIMARY KEY, email_aluno VARCHAR(150) NOT NULL REFERENCES alunos(email) ON DELETE CASCADE,
    evento VARCHAR(30) NOT NULL, titulo TEXT NOT NULL, corpo TEXT NOT NULL,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, lida BOOLEAN NOT NULL DEFAULT FALSE
); CREATE INDEX IF NOT EXISTS notificacoes_conta_id ON notificacoes(email_aluno, id DESC);'''
EVENTOS = {
    'chat': ('Nova mensagem da secretaria', 'Abra a conversa para ver a resposta da secretaria.'),
    'item': ('Atualização do seu pedido', 'Há uma atualização sobre seu item. Confira no portal.'),
    'match': ('Um objeto pode ter sido encontrado', 'Há um objeto parecido com seu relato. Confira o catálogo.'),
    'cadastro': ('Atualização do objeto cadastrado', 'A secretaria atualizou um objeto que você cadastrou. Consulte Meus cadastros.')
}
