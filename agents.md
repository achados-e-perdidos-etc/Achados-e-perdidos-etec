# Branches e propostas

Por orientação do proprietário, concentre as próximas atualizações na branch `28-atualizacoes-do-projeto`, preservando todas as alterações anteriores; não crie uma branch para cada tarefa. A proposta #29 foi mesclada em `main` a pedido explícito em 21/11/2026, no commit `65ec6a44e16306d899de095964281abcddec685b`, sem apagar a branch de trabalho. Para mudanças posteriores, parta da `main` atual e use essa mesma branch; abra ou atualize uma nova proposta com `main` como base, sem reabrir a #29 já integrada. As branches antigas foram removidas a pedido dele, restando essa branch e `main`.

Consulte o head atual da branch no GitHub antes de começar e teste cada alteração e seus impactos antes da integração. Não use uma cópia antiga de main como base. Não afirme ausência absoluta de erros; registre as validações executadas e eventuais limitações.

## Estabilidade

O proprietário pediu para priorizar estabilidade, desempenho e correções, sem acrescentar funcionalidades ao produto por iniciativa própria.

## Funções dos módulos removidos

Os antigos `blueprints/ai.py`, `blueprints/frontend.py` e `blueprints/ai_vision_service.py` foram removidos porque não tinham consumidores nem registro na aplicação atual. Para alterar abertura de páginas, logotipos, tratamento 404 ou rotas de IA, use os caminhos ativos em `server.py`. Para processamento de imagens e extração de cores, use `services/ai_vision_service.py`; comparação de texto reutiliza `utils/helpers.py`. `app.py` importa a mesma aplicação de `server.py`. Evolua esses caminhos existentes e evite recriar cópias dos módulos removidos. Motivos e histórico estão em `correcoes-28.md`, na seção de limpeza.

## Pendências adiadas

Em 21/11/2026, o proprietário informou que publicou o site no Railway e forneceu `https://etec-achados.up.railway.app/` para conferência. A disponibilidade desse endereço foi confirmada por GET 200. Diagnóstico e correções do serviço público estão autorizados no escopo solicitado; registre separadamente resultados locais e respostas efetivamente verificadas no servidor. O acesso ao painel/às variáveis do Railway não está conectado neste chat. Não presuma que um commit já entrou em produção sem verificar.

Novas migrações de hospedagem, validação por lista oficial de RM, testes com credenciais reais e revisão visual completa em monitores grandes continuam adiados enquanto não houver novo pedido. A integração anterior em `main` foi concluída como registrado acima; não a mantenha como tarefa adiada. Preserve os demais registros, mas não os apresente como próximos passos ativos quando ele perguntar por pendências. Responda distinguindo pendências ativas de tarefas adiadas; não afirme que tarefas adiadas foram concluídas.

O teste de carga do Reel (k6 com 100/1.000 usuários, consultas/índices, cache público e respostas acima de 1 segundo) foi explicitamente adiado em 15/11/2026. Estado e roteiro de retomada em `pendencias.md`. Nenhum teste de capacidade foi executado; não tratar os esboços como resultados ou iniciar a carga até novo pedido.
