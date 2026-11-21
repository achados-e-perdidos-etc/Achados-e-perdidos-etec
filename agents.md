# Trabalho direto na main e preservação de versões

Por orientação mais recente do proprietário em 21/11/2026, faça as próximas alterações diretamente em `main`. Não crie novas branches ou propostas sem novo pedido. As propostas #29 e #30 foram mescladas; a branch `28-atualizacoes-do-projeto` foi removida após confirmar que todo o seu conteúdo estava na `main`. O GitHub deve manter apenas `main`, salvo instrução posterior do proprietário.

Consulte o head atual de `main` no GitHub antes de começar e teste cada alteração e seus impactos antes de publicar. Nunca use uma cópia antiga de `main` como base nem sobrescreva trabalho concorrente. Atualizações remotas devem avançar o histórico normal, sem force push.

Antes de alterar remotamente a `main`, confirme uma tag leve numerada (`backup-1`, `backup-2` etc.) apontando para o commit anterior. Se o commit já tiver backup numerado, reutilize esse nome; para uma nova versão, use o maior número existente mais um, comparando os números como inteiros e consultando todas as páginas de tags. Nunca mova uma tag para outro commit. Preserve especialmente a última versão validada e em funcionamento. O workflow `.github/workflows/backup-main.yml` também guarda as versões anterior e atual de cada push em `main`, sem duplicar o mesmo commit nem sobrescrever um número já reservado. Um backup registra a versão; não certifica que ela passou em testes.

Os nomes antigos baseados no SHA foram renomeados por pedido explícito do proprietário. Renomeações futuras só devem ocorrer por novo pedido; crie e confira a nova referência antes de remover o nome anterior, mantendo o mesmo código preservado. Não exclua versões de backup como rotina de limpeza.

Se a cópia de segurança falhar, preserve o código e resolva a falha antes de publicar novas mudanças. Para recuperar uma versão, compare a tag e restaure por um novo commit, conservando o histórico e o mecanismo de backup. Não use reset remoto forçado como procedimento padrão. Não afirme ausência absoluta de erros; registre as validações executadas e eventuais limitações.

## Estabilidade

O proprietário pediu para priorizar estabilidade, desempenho e correções, sem acrescentar funcionalidades ao produto por iniciativa própria.

## Funções dos módulos removidos

Os antigos `blueprints/ai.py`, `blueprints/frontend.py` e `blueprints/ai_vision_service.py` foram removidos porque não tinham consumidores nem registro na aplicação atual. Para alterar abertura de páginas, logotipos, tratamento 404 ou rotas de IA, use os caminhos ativos em `server.py`. Para processamento de imagens e extração de cores, use `services/ai_vision_service.py`; comparação de texto reutiliza `utils/helpers.py`. `app.py` importa a mesma aplicação de `server.py`. Evolua esses caminhos existentes e evite recriar cópias dos módulos removidos. Motivos e histórico estão em `correcoes-28.md`, na seção de limpeza.

## Pendências adiadas

Em 21/11/2026, o proprietário informou que publicou o site no Railway e forneceu `https://etec-achados.up.railway.app/` para conferência. A disponibilidade desse endereço foi confirmada por GET 200. Diagnóstico e correções do serviço público estão autorizados no escopo solicitado; registre separadamente resultados locais e respostas efetivamente verificadas no servidor. O acesso ao painel/às variáveis do Railway não está conectado neste chat. Não presuma que um commit já entrou em produção sem verificar.

Novas migrações de hospedagem, validação por lista oficial de RM, testes com credenciais reais e revisão visual completa em monitores grandes continuam adiados enquanto não houver novo pedido. A integração anterior em `main` foi concluída como registrado acima; não a mantenha como tarefa adiada. Preserve os demais registros, mas não os apresente como próximos passos ativos quando ele perguntar por pendências. Responda distinguindo pendências ativas de tarefas adiadas; não afirme que tarefas adiadas foram concluídas.

O teste de carga do Reel (k6 com 100/1.000 usuários, consultas/índices, cache público e respostas acima de 1 segundo) foi explicitamente adiado em 15/11/2026. Estado e roteiro de retomada em `pendencias.md`. Nenhum teste de capacidade foi executado; não tratar os esboços como resultados ou iniciar a carga até novo pedido.
