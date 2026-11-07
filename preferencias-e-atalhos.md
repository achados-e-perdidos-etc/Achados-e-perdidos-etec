# Aparência, buscas e prioridades

## Aparência do site

O portal e a secretaria web oferecem Claro, Escuro e Automático. Na primeira visita, o convite pergunta se a pessoa quer acompanhar o aparelho. Até responder, mantém o escuro já usado pelo projeto, mesmo que o sistema esteja em modo claro. A escolha pode ser alterada em Aparência, inclusive antes de entrar na conta. Automático reage às mudanças do sistema; Claro e Escuro ficam fixos. A preferência de aparência vale para este navegador e é compartilhada entre portal e painel.

As paletas de tela não alteram a composição dos documentos para impressão. Movimento reduzido, contraste dos controles e navegação por teclado continuam sendo respeitados.

## Preferências por conta

No catálogo, “Minhas buscas e preferências” oferece até dez buscas com seus filtros, remoção individual, cartões ou lista compacta e limpeza das preferências da conta. Busca, categoria, situação, local e período são restaurados ao voltar. Os dados ficam no navegador e não dependem de uma API paga ou de uma nova tabela no banco. Não há sincronização entre aparelhos.

Os registros locais são separados entre contas e entre portal e secretaria. Trocar de conta ou sair limpa o estado exibido; cada conta recupera somente suas próprias escolhas ao retornar. Credenciais, mensagens e fotos não fazem parte desses registros. Se o navegador impedir o salvamento, a interface informa que as escolhas valem apenas na página atual.

A secretaria web também lembra filtros e apresentação da lista. No aplicativo nativo, filtros e larguras das colunas ficam em um JSON local por conta, escrito de forma atômica. O arquivo contém somente esses campos; não inclui token ou senha. O tema solicitado para o site se aplica ao portal e painel web; o aplicativo nativo conserva sua aparência própria.

## Atalhos da secretaria

Os dois painéis consultam `GET /api/secretaria/resumo`, protegido pela autorização administrativa e sem cache. Uma consulta retorna: cadastros aguardando análise (sem os devolvidos para correção), objetos aprovados com retirada solicitada e mensagens de alunos não lidas dos últimos trinta dias.

Os cartões abrem a área correspondente; o atalho de retirada limpa outros filtros para evitar ocultar solicitações. Há atualização manual e periódica a cada minuto. Na web, a atualização periódica pausa com a aba escondida. Uma falha mostra “—” e a indicação para tentar novamente, em vez de apresentar zero como se a fila estivesse vazia.

## Validação humana

O roteiro [Teste com colegas](teste-com-colegas.md) está pronto para aplicação. Não houve contato com colegas nem sessão humana conduzida pelo assistente.

## Validações executadas

Total cumulativo de **404 casos Python, 49 JavaScript e 48 Chromium de regressão: 501 aprovados**. A execução completa aprovou 403 casos Python; o teste adicional de preferências offline passou junto aos outros sete testes focados desta etapa. A suíte inclui vinte jornadas com Flask, PostgreSQL e Chromium, além do fluxo nativo em Tkinter/Xvfb.

Nesta etapa foram conferidos: escolha explícita antes de acompanhar o sistema, atualização automática do tema, escolha fixa após recarga, busca salva e retomada, isolamento de contas, limpeza e limite de dez buscas, armazenamento bloqueado, funcionamento offline, contagens administrativas privadas, revogação de acesso, recuperação de erro 503 e larguras de 320, 390, 768 e 1366 pixels. O desktop exercitou os atalhos, persistência dos filtros e troca de conta. Scripts inline também passaram pela verificação sintática do Node.

As capturas fictícias estão em `/workspace/preferencias-evidencias`. Documentos e licenças adicionados nas etapas anteriores foram renomeados para minúsculas, com referências atualizadas; o conteúdo dos avisos de licença foi preservado. Os quatro nomes com maiúsculas que já existiam em `main` permanecem como estavam.
