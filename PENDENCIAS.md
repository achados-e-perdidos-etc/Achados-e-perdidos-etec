# Achados e Perdidos ETEC — pendências

## Situação atual — orientação do proprietário

O envio Web Push foi implementado na proposta #25. As demais pendências conhecidas ficam **adiadas por inviabilidade atual**, preservadas no histórico abaixo. Quando o proprietário perguntar por pendências, informar que não há outra pendência ativa viável nesta rodada; não reoferecer tarefas adiadas nem afirmar que foram concluídas. Isso inclui integração/publicação das propostas, hospedagem/migração, configuração real de serviços, validação de RM pela escola e revisão visual completa de monitores grandes.

Registro em 04/11/2026. Repositório: https://github.com/achados-e-perdidos-etc/Achados-e-perdidos-etec

## Prioridade atual definida pelo usuário

Corrigir as pendências do projeto. Hospedagem e migração de banco adiadas por orientação do usuário. Esta primeira etapa está preparada para revisão, sem publicação ou alteração do banco real.

## Erros identificados na revisão inicial

Os itens marcados foram corrigidos nesta etapa; as descrições abaixo registram o comportamento anterior. Detalhes e limites em VALIDACAO.md.

- [x] P1 — Autorização administrativa: `server.py:token_required` valida a assinatura do JWT, mas não o perfil. Rotas administrativas de aprovação, edição e exclusão usam esse decorador sem exigir secretaria. Reproduzido localmente com token de aluno e o decorador original extraído via AST; nenhuma operação real foi feita.
- [x] P1 — Categorias: POST e DELETE em `/api/categorias` não exigem autenticação.
- [x] P1 — Chat: envio aceita remetente informado pelo cliente; leitura por RM não exige autenticação nem verifica a identidade. Proteger leitura e escrita e derivar a identidade da sessão.
- [x] P2 — Doações: atualização automática grava `PARA DOAÇÃO`; conclusão e estatísticas usam `LIKE 'DOAÇÃO%'` ou `LIKE 'DOACAO%'`. Esses filtros não incluem o status gravado.
- [x] P2 — E-mails: o servidor em uso aceita apenas domínio de aluno, rejeitando professores CPS/ETEC. Também aceita endereço sem parte local (`@aluno.cps.sp.gov.br`). Os testes usam `utils.helpers`, cuja implementação difere da usada por `server.py`.

## Outros pontos para revisar

- [x] Removido o segredo JWT padrão do código; inicialização exige segredo com pelo menos 32 bytes.
- [ ] **ADIADO** — Configurar segredo JWT novo na hospedagem antes da publicação; a troca invalida tokens antigos.
- [ ] **ADIADO** — Comprovar e garantir unicidade do RM no cadastro e alteração, impedindo contas com matrícula de terceiros. Adiado pelo usuário até obter a lista oficial da escola com e-mail institucional e matrícula; não implementar aprovação manual nesta etapa.
- [x] Exigir sessão nas operações pessoais e obter autoria da sessão em solicitação de itens, publicação no mural e cadastro de objetos encontrados. Detalhes na sétima etapa.
- [x] Proteger a vinculação de notificações push à sessão; cadastro e exclusão exigem login e usam a conta por e-mail, sem escolher destinatário por RM. Detalhes na oitava etapa.
- [x] Implementar emissor Web Push com VAPID, criptografia, fila persistida e testes de protocolo/transporte controlado. Detalhes na proposta #25.
- [ ] **ADIADO** — Ativar e comprovar entrega em aparelhos reais após publicação HTTPS e configuração de VAPID. A implementação e os testes locais não equivalem a entrega real validada.
- [x] Revisar renderização de conteúdo informado por usuários para impedir injeção de HTML/scripts no portal e painel; detalhes e limites na sexta etapa.
- [x] Removido login compartilhado professor/professor e sessões fictícias do navegador. Professores usam conta institucional com senha individual; tokens antigos exigem novo login.
- [x] Catálogo e mural públicos usam lista explícita de campos sem nome do autor, RM ou e-mail de alunos. Dados administrativos exigem token de secretaria; consultas pessoais filtram pelo e-mail da sessão. Conteúdo livre de descrições e imagens ainda pode conter dados pessoais e exige moderação.
- [ ] **ADIADO** — Após a migração, substituir a URL Railway fixa no frontend e verificar também painel e aplicativo desktop.

## Segunda etapa — acesso de professores

Branch separada baseada na proposta #14, ainda não integrada à main. Removido o atalho compartilhado no servidor e no portal; o navegador não cria sessões em falhas de rede e descarta os antigos tokens fictícios. Emissão e validação de JWT exigem auth_version=2, revogando também tokens assinados da antiga conta compartilhada. Isso exige novo login de alunos e secretaria na publicação. O envio de códigos no portal aceita também domínios CPS e ETEC.

Validação: 46 testes Python e 5 testes JavaScript passaram. O acesso legítimo com senha individual continua sendo verificado pelo banco. Envio real de e-mail e comprovação do vínculo de matrícula permanecem sem validação nesta etapa.

## Validação da primeira etapa

40 testes passaram: 17 existentes, 22 testes de contratos de rotas nas implementações unificada/modular e um teste da configuração JWT. JavaScript e compilação Python também verificados. Integrações externas e dados reais permanecem sem teste. Consulte VALIDACAO.md.

## Verificações da análise inicial

- 17 testes passaram com `python -m unittest discover -s tests -v`.
- Sintaxe de `script.js` e `sw.js` passou em `node --check`.
- Compilação dos arquivos Python baixados passou.
- Os testes não cobrem o fluxo completo das rotas do servidor unificado.
- Não foi possível executar o servidor completo: faltam dependências e a conexão do shell ao proxy falhou.
- O endereço publicado não foi acessível pela ferramenta de navegação. Isso não prova, isoladamente, indisponibilidade global.
- Não foram validados banco real, login completo, e-mails, Cloudinary, push e IA.

## Plano de hospedagem a avaliar

Render Free para Flask/Gunicorn e Neon Free para PostgreSQL. Manter imagens em armazenamento externo, como o Cloudinary já previsto no código. Confirmar acesso ao banco antigo e obter backup antes de migrar: criar banco novo não recupera dados antigos.

Fontes consultadas em 04/11/2026:
- https://render.com/docs/free — serviço web dorme após 15 minutos, pode demorar cerca de um minuto para reativar; há cotas mensais. Banco PostgreSQL grátis do Render expira em 30 dias, portanto não atende ao objetivo de evitar expiração.
- https://neon.com/pricing — plano Free sem prazo de teste, sujeito às cotas do serviço.

Configuração esperada: build `pip install -r requirements.txt`; start `gunicorn --bind 0.0.0.0:$PORT server:app`. Configurar DATABASE_URL, JWT_SECRET e credenciais das integrações no painel do provedor, nunca em arquivo público. Inspecionar todos os clientes antes de mudar a URL da API.

As correções e esta lista estão preparadas para revisão em branch separada. A branch principal, a hospedagem e o banco real não foram alterados.

## Terceira etapa — privacidade de catálogo e mural

Branch separada a partir da proposta #15. Respostas públicas deixam de expor campos estruturados de identificação pessoal; a secretaria mantém acesso autenticado. A área Meus itens usa consulta autenticada por e-mail, sem filtrar por nome ou matrícula no navegador. Relatos por RM exigem sessão e restringem alunos ao próprio e-mail. Consultas retornam Cache-Control private, no-store e variam por cabeçalho de autenticação.

Validação: 58 testes Python e 6 testes JavaScript passaram. Nenhum banco de produção foi acessado. Solicitações antigas sem email_solicitante não podem ser atribuídas com segurança só pelo nome e exigem revisão pela secretaria. Os campos de texto livre e fotografias seguem públicos por finalidade do catálogo; não foi feita anonimização automática de seus conteúdos. Hospedagem continua aguardando cadastro no provedor.

## Quarta etapa — professores ajudando a secretaria

Nova branch derivada da proposta #16, conforme orientação de continuar sempre da última proposta.

- [x] Botão no portal para professores com e-mail @etec.sp.gov.br ou @cps.sp.gov.br solicitarem acesso.
- [x] Solicitação vinculada à conta autenticada, com nome obtido do cadastro; o navegador não escolhe qual conta receberá permissão.
- [x] Área Acesso de Professores no painel para a secretaria titular aprovar, recusar e revogar.
- [x] Permissão aprovada consultada no banco a cada requisição; revogação afeta também sessões já abertas.
- [x] Professores aprovados podem operar o painel, mas não conceder permissões a outros professores.
- [x] Registro do responsável e da data da decisão; reenvio de solicitação recusada ou revogada exige nova aprovação.
- [x] Regra de branches futuras registrada em AGENTS.md.

Validação: 72 testes Python e 11 testes JavaScript passaram. Também foi executado o ciclo de login, solicitação, aprovação, operação, restrição de decisões e revogação com PostgreSQL real isolado. Nenhum dado real foi acessado. A tabela professores_acesso é criada na inicialização do banco nas duas implementações. Nenhum acesso é concedido automaticamente a contas existentes.

## Quinta etapa — issue #13: preenchimento pela foto

Branch derivada da proposta #17. A revisão identificou uma cópia antiga da visão no servidor de produção, fallback genérico anunciado como identificação e erro na normalização de categorias no painel.

- [x] O servidor unificado e o blueprint utilizam o mesmo serviço de análise; o caminho legado apenas reexporta a implementação canônica.
- [x] Modelo configurável por GEMINI_VISION_MODEL e chave enviada em cabeçalho, fora da URL.
- [x] Imagem validada pelos bytes reais, com limites de tamanho e resolução.
- [x] Falha de provedor, resposta truncada/inválida ou ausência de chave não são usadas como identificação do objeto.
- [x] Formulários só aplicam resposta completa do modelo com confiança declarada alta/média; baixa confiança e fallback preservam campos existentes.
- [x] Categorias são comparadas por igualdade após normalização correta, sem escolher a primeira opção por correspondência vazia.
- [x] Resultado atrasado de uma foto anterior é ignorado; OCR não confiável não é aplicado nem cruzado com alunos.
- [ ] **ADIADO** — Validar precisão visual com credencial real e fotos representativas. Confiança declarada pelo modelo não comprova acerto.

116 testes Python e 18 testes JavaScript passaram. Não houve chamada real a um provedor de visão nem medição da precisão visual. Após avaliar os exemplos no chat, o usuário pediu o encerramento da issue #13 como concluída; isso foi registrado no GitHub, mantendo pendente a validação da precisão com o provedor real. Os dados de produção não foram acessados.

## Sexta etapa — textos seguros no portal e painel

Branch derivada da proposta #18. Nomes, descrições, mensagens, categorias, dados de alunos e campos de relatórios eram inseridos diretamente em HTML, permitindo injeção de marcação e eventos.

- [x] Codificação de texto e atributos em catálogo, mural, Meus itens, chat, painel, comprovantes, etiquetas e relatórios impressos.
- [x] Argumentos de botões serializados como JSON e codificados para o atributo HTML, preservando aspas, acentos e os dados originais.
- [x] Imagens aceitam HTTP/HTTPS e data URI de formatos raster permitidos; protocolos executáveis, SVG inline e documentos HTML são recusados. Abertura de imagens externas usa noopener/noreferrer.
- [x] Diálogos conservam somente tags básicas de formatação, sem atributos, scripts ou elementos ativos.
- [x] Novo arquivo seguranca-interface.js carregado antes das interfaces dependentes.

Validação: 116 testes Python, 18 testes JavaScript existentes e 10 testes no Chromium com as páginas reais e respostas de API simuladas. Foram verificados textos maliciosos, botões com aspas, chat nos dois sentidos, catálogo, mural, categorias, detalhes, sugestões de itens, diálogos e relatórios de inventário/entregas. Sintaxe JavaScript também verificada. Nenhum banco, credencial ou serviço de produção foi utilizado; a proposta ainda precisa ser integrada para chegar ao site. A próxima pendência de código registrada é comprovação e unicidade do RM.

## Sétima etapa — autoria nas operações de alunos

Branch derivada da proposta #19. A validação do RM pela lista oficial foi adiada a pedido do usuário, pois a lista ainda está com a escola. A revisão revelou que solicitar um item, publicar no mural e cadastrar um objeto não exigiam autenticação nas rotas correspondentes. As gravações aceitavam dados de autoria escolhidos pelo navegador.

- [x] As três operações exigem token válido antes de consultar o banco ou processar fotos.
- [x] Nome, e-mail e RM da solicitação e do relato vêm da sessão assinada; dados de autoria enviados no corpo são ignorados.
- [x] O RM de quem cadastra um objeto vem da sessão; o nome do objeto continua sendo o título informado no formulário.
- [x] Professores podem cadastrar objetos encontrados, inclusive quando aprovados para ajudar a secretaria. São identificados como PROFESSOR, sem usar RM de aluno, e não podem solicitar retiradas ou publicar relatos de perda.
- [x] Contas sem RM individual informado recebem orientação para completá-lo antes de solicitar ou publicar; consulta pública do catálogo/mural e OPTIONS continuam disponíveis.
- [x] Frontend envia somente ID/conteúdo e autenticação, sem dados de autoria escolhidos localmente.
- [x] Solicitar por ID também exige que o objeto já esteja aprovado para o catálogo, preservando a moderação.

Validação: 134 testes Python, 21 testes JavaScript e 10 testes no Chromium passaram. Os casos novos cobrem visitantes, tokens forjados, alteração dos campos de autoria, perfis de professor com/sem aprovação e consultas de duas contas após gravações reais em SQLite temporário. Tanto o servidor unificado quanto os blueprints foram verificados. Não houve migração, alteração de conta ou acesso a produção. Esta correção vincula as operações à sessão; comprovar a titularidade e unicidade do RM continua pendente da lista oficial, sem ser considerado resolvido por esta etapa.

## Oitava etapa — notificações vinculadas à conta (proposta 21)

Branch numerada 21-protecao-notificacoes-push, derivada da proposta #20. A numeração das branches futuras também foi registrada em AGENTS.md por orientação do usuário.

- [x] POST/DELETE /api/push/subscribe exigem sessão institucional válida; a chave pública e OPTIONS continuam públicos.
- [x] Assinaturas pertencem ao e-mail autenticado, sem usar RM/e-mail/perfil enviados no corpo. Contas que declaram o mesmo RM não sobrescrevem dispositivos diferentes.
- [x] Nova tabela push_dispositivos com vínculo à conta e chave única por endpoint; permite vários dispositivos por conta. Um navegador compartilhado passa para a última conta que o vinculou, e uma conta anterior não pode apagar esse novo vínculo.
- [x] Assinaturas legadas em push_subscriptions são preservadas, mas não adotadas como vínculos autenticados. O portal recadastra a assinatura do próprio navegador após o login com permissão concedida.
- [x] Validação de endpoint HTTPS, formato/tamanho das chaves e validade da assinatura antes do banco; erros não retornam dados de assinatura.
- [x] Logout tenta cancelar a assinatura no navegador e excluir somente o vínculo da conta que está saindo; tarefas de cadastro anteriores ao logout são invalidadas.
- [x] Portal registra /sw.js quando ainda não há service worker, em vez de apenas aguardar um registro inexistente.
- [x] Backend unificado usa o mesmo blueprint de push que a versão modular; ambas as inicializações criam a nova tabela de forma idempotente.

Validação: 195 testes Python, 33 testes JavaScript e 10 testes no Chromium passaram. Também foi executada uma migração de tabelas legadas em PostgreSQL real temporário, repetindo as duas inicializações e verificando múltiplos dispositivos, contas com o mesmo RM e exclusão restrita. Serviços push e credenciais de produção não foram usados. Cadastro protegido não equivale a envio real de notificações; o emissor e a entrega em dispositivos reais continuam pendentes. A validação do RM pela lista oficial permanece adiada.

## Nona etapa — lembrar acesso e animação de autenticação (proposta 22)

Branch 22-lembrar-login-animacao, baseada na proposta #21.

- [x] Lembrar de mim no login e no cadastro do portal. Desmarcado por padrão: sessão da aba em sessionStorage. Marcado: acesso persistido em localStorage até expiração do token ou logout, sem salvar senha.
- [x] Sessões antigas sem escolha explícita migram para armazenamento da sessão. Logout limpa ambas as formas de armazenamento.
- [x] Consultas pessoais, chat, solicitações, notificações e acesso delegado dos professores usam a mesma leitura de sessão. O painel aceita o token temporário do professor sem torná-lo persistente.
- [x] Animação de busca em vermelho/rosa, órbitas, brilho, progresso indeterminado e confirmação verde após resposta de sucesso, tanto no login quanto no cadastro.
- [x] Envios duplicados bloqueados; falhas restauram o formulário e o foco. Movimento reduzido respeitado, com estado anunciado por leitores de tela.

Validação: 195 testes Python e 33 testes JavaScript anteriores passaram, com fixtures atualizadas para o acesso compartilhado à sessão. Cinco novos testes no Chromium cobrem persistência, nova aba, logout, cadastro, falhas, duplicidade, sessão legada e acesso de professor. Os 10 testes de renderização anteriores também passaram. Prévia visual verificada em celular de 390 × 844, sem rolagem horizontal. Não houve publicação em produção, mudança de validade do JWT ou uso de credenciais reais. O envio real de Web Push e a comprovação do RM continuam nas pendências anteriores.

## Décima etapa — preparação e envio de fotos (proposta 23)

Branch 23-carregamento-imagens, baseada na proposta #22.

- [x] Indicador animado na seleção e no envio das fotos, no portal e no painel, com texto específico para preparação, envio, sucesso e falha.
- [x] Check verde sem espera artificial: preparação informa que o envio acontece ao salvar; envio concluído exige confirmação da API. A confirmação visível de cadastro usa o toast existente, sem prolongar a operação.
- [x] Impede salvar enquanto as fotos estão sendo preparadas e bloqueia envios duplicados. Arquivos inválidos não deixam o indicador preso nem recebem confirmação verde.
- [x] Preparações antigas são ignoradas ao reabrir o formulário; fotos são mantidas quando o envio falha para permitir nova tentativa.
- [x] Compressão compartilhada em até 1200 px/JPEG 75%, preservando a ordem e o limite de quatro fotos; no painel, uma substituição totalmente inválida preserva as fotos existentes.
- [x] Falhas no armazenamento não são ignoradas pelo servidor: o item não é criado/atualizado como se todas as fotos tivessem sido enviadas.
- [x] Corrigida a edição no servidor unificado, que antes ignorava as fotos enviadas no formulário. Omitir o campo preserva as fotos; enviar lista vazia remove a associação de fotos nas duas versões.

Validação: 214 testes Python, 33 testes JavaScript e 21 testes no Chromium passaram, incluindo seis novos fluxos de fotos. Foram usadas imagens PNG reais para leitura e compressão no navegador, APIs/provedor simulados e SQL real em SQLite temporário para edição de fotos. Não houve upload para Cloudinary real nem acesso a produção. Nenhuma espera artificial ou porcentagem fictícia foi adicionada; o indicador de envio cobre a requisição completa de fotos e gravação do item. O emissor Web Push e a lista oficial de RM permanecem pendentes.

## Décima primeira etapa — movimento no site (proposta 24)

Branch 24-animacoes-transicoes, baseada na proposta #23.

- [x] Estilo de movimento compartilhado pelo portal, painel e página 404, sem biblioteca ou observador JavaScript novo.
- [x] Entradas leves em abas, menus, filtros, janela de chat, modais, cards e avisos; respostas visuais em botões, links, campos e linhas de tabela.
- [x] Movimentos curtos e sequência de cards limitada a 90 ms; fechamento continua imediato, sem aguardar animação ou bloquear ações.
- [x] Hover de cards restrito a ponteiro preciso; chat não reanima mensagens a cada polling e a impressão não recebe animações.
- [x] Foco visível de teclado e preferência de movimento reduzido aplicada aos efeitos CSS, ao carrossel e à abertura com GIF, que é ignorada nessa preferência.

Validação desta etapa: 33 testes JavaScript e 27 testes no Chromium passaram (21 regressões anteriores e seis novos fluxos de movimento). Conferidos abertura/fechamento durante animação, término sem transformações persistentes, sequência limitada, chat estável, foco de teclado, 404 e preferência de movimento reduzido. Prévia de celular em 390 × 844 sem transbordamento horizontal. Backend e banco não foram modificados; a suíte Python do backend não foi repetida nesta etapa visual. Nenhuma publicação em produção ou integração à main.


## Décima segunda etapa — emissor de Web Push (proposta 25)

Branch 25-envio-notificacoes, baseada na proposta #24.

- [x] Emissor com pywebpush, VAPID correspondente à chave pública e criptografia AES128GCM; mensagens genéricas, sem texto privado do chat, nomes, RM ou descrição de item na tela bloqueada.
- [x] Fila persistida por dispositivo, reserva exclusiva entre workers e retomada após reinicialização. Não bloqueia rotas aguardando o provedor.
- [x] Avisos de resposta da secretaria, mudança de status/recusa de pedido e possíveis correspondências com relatos do mural, sempre por e-mail da conta.
- [x] Autoria de novas mensagens registrada por e-mail autenticado. Conversas antigas ou ambíguas não recebem destinatário adivinhado por RM.
- [x] Assinaturas removidas/revinculadas são conferidas antes de enviar; 404/410 removem apenas a assinatura correspondente, sem apagar novo vínculo durante uma troca de conta.
- [x] Timeout de oito segundos, até quatro tentativas e intervalos de reenvio. Endpoints de provedores conhecidos e sem redirecionamento; erros não registram chaves ou endpoints.
- [x] Botão Testar Notificações solicita envio somente para a própria conta, com limite de um teste a cada 30 segundos e sem declarar entrega antes da recepção.
- [x] Rotação de VAPID no navegador renova a assinatura quando necessário; chave de exemplo removida. Clique na notificação abre somente a origem do site.
- [x] Orientação sobre pendências adiadas registrada em AGENTS.md e nesta lista.

Validação: testes criptografam/assinam com chaves efêmeras reais, interceptam o transporte sem contatar provedores e decifram/verificam o payload/JWT. Fila e migrações foram exercitadas em PostgreSQL temporário, com ambas as implementações de rotas. O recebimento por um aparelho real não foi comprovado: ativação e validação com serviços reais ficam adiadas junto das demais tarefas atualmente inviáveis. Nenhum banco/credencial de produção foi usado, nenhuma notificação foi enviada a contas reais e a proposta permanece separada da main.

Verificação desta etapa: 266 testes Python (incluindo 13 casos em PostgreSQL real temporário), 40 testes JavaScript e 29 testes no Chromium passaram. O transporte dos testes foi interceptado; não houve entrega a um serviço/dispositivo de produção.

## Proposta 26 — melhorias solicitadas

- [x] Central de notificações com histórico privado, paginação e marcação de leitura, independente da permissão push.
- [x] Acompanhamento de objetos cadastrados por quem os encontrou; autoria por e-mail, decisão da secretaria e histórico preservado após recusa/exclusão.
- [x] Rascunhos de texto em cadastros e mural, separados por conta, com limpeza após envio confirmado ou saída.
- [x] Revisão de navegação por teclado, foco, rótulos, contraste e apresentação dos novos fluxos no celular.

As quatro melhorias compõem uma única branch `26-melhorias-portal`, dependente da proposta 25. Acompanhamento de autoria vale para novos objetos; registros legados sem e-mail de autoria não são atribuídos por suposição. O código proposto e validado localmente ainda precisa ser integrado para chegar ao site publicado. Permanecem preservados os registros das tarefas anteriormente adiadas.
