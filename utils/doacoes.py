"""Filtro compartilhado entre catálogo, conclusão e estatísticas de doações."""

# Aceita os nomes históricos sem incluir os registros já arquivados.
DOACOES_PENDENTES_SQL = "UPPER(TRIM(status)) IN ('PARA DOAÇÃO', 'PARA DOACAO', 'DOAÇÃO', 'DOACAO')"
