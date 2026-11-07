# Branches e propostas

Por orientação mais recente do proprietário, concentre as próximas atualizações na branch `28-atualizacoes-do-projeto`, preservando todas as alterações anteriores. Mantenha a proposta #29 com `main` como base; não crie uma branch para cada tarefa. As branches antigas foram removidas a pedido dele, restando essa branch e `main`.

Consulte o head atual da branch no GitHub antes de começar e teste cada alteração e seus impactos antes da integração. Não use uma cópia antiga de main como base. Não afirme ausência absoluta de erros; registre as validações executadas e eventuais limitações.

Por orientação do proprietário, os nomes dos novos arquivos devem usar letras minúsculas, incluindo documentos. Atualize referências ao renomear. Os quatro nomes originais com maiúsculas (`Procfile`, `animacao.GIF`, `animacao_pc.GIF` e `blueprints/Push.py`) foram preservados; a solicitação se refere aos arquivos adicionados nas atualizações.

## Estabilidade e ambiente de testes

O proprietário pediu para priorizar estabilidade, desempenho e correções, sem acrescentar funcionalidades ao produto por iniciativa própria. A configuração de desenvolvimento do GitHub Codespaces foi solicitada para permitir testes antes da hospedagem; instruções em `testar-no-codespaces.md`. Use o banco e as contas de demonstração desse ambiente, mantendo a porta 5000 privada. Não conecte o preparo de demonstração ao banco da escola. O SSL do banco continua obrigatório por padrão; apenas o banco interno desse devcontainer usa `DATABASE_SSLMODE=disable`.

## Funções dos módulos removidos

Os antigos `blueprints/ai.py`, `blueprints/frontend.py` e `blueprints/ai_vision_service.py` foram removidos porque não tinham consumidores nem registro na aplicação atual. Para alterar abertura de páginas, logotipos, tratamento 404 ou rotas de IA, use os caminhos ativos em `server.py`. Para processamento de imagens e extração de cores, use `services/ai_vision_service.py`; comparação de texto reutiliza `utils/helpers.py`. `app.py` importa a mesma aplicação de `server.py`. Evolua esses caminhos existentes e evite recriar cópias dos módulos removidos. Motivos e histórico estão em `correcoes-28.md`, na seção de limpeza.

## Pendências adiadas

Por orientação do proprietário, integração/publicação das propostas, hospedagem/migração, validação por lista oficial de RM, testes com credenciais reais e revisão visual completa em monitores grandes estão adiados por inviabilidade atual. Preserve os registros, mas não os apresente como próximos passos ativos quando ele perguntar por pendências. Responda distinguindo pendências ativas de tarefas adiadas; não afirme que tarefas adiadas foram concluídas. Reabra esse trabalho somente quando o proprietário indicar que já é viável.
