"""Identificação institucional e esquema de acesso delegado."""

def email_de_professor(email):
    email = str(email or '').strip().lower()
    return email.endswith(('@etec.sp.gov.br', '@cps.sp.gov.br')) and email.count('@') == 1

SCHEMA_ACESSO_PROFESSORES = """CREATE TABLE IF NOT EXISTS professores_acesso (
    email VARCHAR(150) PRIMARY KEY REFERENCES alunos(email),
    nome VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE'
        CHECK (status IN ('PENDENTE', 'APROVADO', 'RECUSADO', 'REVOGADO')),
    data_solicitacao TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_decisao TIMESTAMPTZ,
    decidido_por VARCHAR(150)
);"""
