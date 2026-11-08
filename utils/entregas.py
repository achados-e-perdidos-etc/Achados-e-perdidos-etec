"""Entregas canceladas permanecem auditáveis, fora dos indicadores ativos."""
SCHEMA_ENTREGAS = '''ALTER TABLE entregues ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMPTZ;
ALTER TABLE entregues ADD COLUMN IF NOT EXISTS cancelada_por VARCHAR(150);
CREATE INDEX IF NOT EXISTS entregues_item_ativas ON entregues(item_id) WHERE cancelada_em IS NULL;'''


def cancelar_entregas(cursor, item_id, responsavel):
    cursor.execute('''UPDATE entregues SET cancelada_em=CURRENT_TIMESTAMP,cancelada_por=%s
        WHERE item_id=%s AND cancelada_em IS NULL;''', (responsavel, item_id))


def registrar_entrega(cursor, item_id, nome, dados, item, responsavel):
    # Chamado somente com a linha do item bloqueada: repetir não duplica a entrega.
    from datetime import datetime
    cursor.execute('''INSERT INTO entregues (item_id,nome_item,retirado_por,rm_retirante,turma_curso,data_entrega,funcionario_responsavel)
        SELECT %s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS
        (SELECT 1 FROM entregues WHERE item_id=%s AND cancelada_em IS NULL);''', (
        item_id,nome,dados.get('retirado_por') or item.get('solicitado_por') or 'Não informado',
        dados.get('rm_retirante') or item.get('rm_aluno') or 'Não informado',dados.get('turma_curso') or '-',
        dados.get('data_entrega') or datetime.now().strftime('%d/%m/%Y %H:%M'),responsavel,item_id))
