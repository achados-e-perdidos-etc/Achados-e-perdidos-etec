# Validação das correções

O backend publicado continua sendo `server:app`, conforme o Procfile. As correções também cobrem os blueprints equivalentes.

## Configuração obrigatória antes de publicar

Configure `JWT_SECRET` no painel da hospedagem com um segredo novo, aleatório e de pelo menos 32 bytes. Não use uma senha humana nem coloque o valor no GitHub. É possível gerar um valor com `python -c "import secrets; print(secrets.token_urlsafe(48))"`. A troca invalida as sessões antigas; todos precisarão entrar novamente.

O servidor recusa iniciar se esse segredo estiver ausente ou for curto. DATABASE_URL e as credenciais das integrações continuam sendo configuradas pelo ambiente. Nenhum segredo de produção foi alterado nesta revisão.

## Executar testes locais

Instale `requirements.txt` em um ambiente virtual. Execute com banco desabilitado e segredo exclusivo para testes:

```bash
JWT_SECRET=teste-local-apenas-0123456789abcdef DATABASE_URL='' python -m pytest -q
node --check script.js
node --check seguranca-interface.js
node --check notificacoes-push.js
node --check sw.js
node tests/test_portal_auth.cjs
node tests/test_privacy_portal.cjs
node tests/test_teacher_portal.cjs
node tests/test_vision_form.cjs
node tests/test_student_operations.cjs
node tests/test_push_portal.cjs
```

Os testes usam o cliente Flask real, banco simulado e uma tabela SQLite temporária para executar o SQL de doações. Não verificam a conexão com PostgreSQL em produção nem serviços de e-mail, imagens, IA ou push. Não inserem ou removem dados reais.

## Comportamentos corrigidos

- Rotas administrativas exigem perfil `secretaria`; token de aluno recebe 403 e visitante recebe 401.
- Categorias continuam disponíveis para consulta pública; alterações exigem secretaria.
- Chat exige autenticação; aluno só pode usar o RM do token, e nome/remetente vêm da sessão. RMs genéricos não podem acessar conversas.
- Site, painel e aplicativo desktop enviam autenticação nas chamadas do chat.
- Doações pendentes são contadas pelo mesmo filtro usado na conclusão, incluindo nomes históricos. Concluir arquiva como `DOAÇÃO FEITA`, preservando registros.
- Servidor e testes usam a mesma validação de e-mail institucional, incluindo CPS e ETEC.

Esta seção descreve a primeira etapa. As revisões de exposição de dados e renderização estão registradas nas etapas posteriores. A comprovação e unicidade do RM no cadastro/alteração continuam pendentes. A sessão identifica o RM declarado na conta; não comprova vínculo com a matrícula escolar.

## Aplicar o pacote

O arquivo `correcoes-achados-etec.zip` contém somente os arquivos corrigidos e documentos, com os caminhos do repositório preservados. Faça uma cópia do projeto antes de substituir os arquivos. O pacote não contém dados do banco nem credenciais de produção. Esta etapa deve ser revisada antes da integração à branch principal.

## Segunda etapa: professores

Professores entram com e-mail institucional e senha individual cadastrada. O login professor/professor foi removido. O portal deixa de fabricar tokens quando a rede falha, descarta os antigos tokens fictícios e permite solicitar códigos para e-mails CPS e ETEC.

Todos os tokens de sessão novos carregam auth_version=2. Tokens anteriores são recusados, inclusive os da antiga conta compartilhada; alunos e secretaria precisarão entrar novamente na publicação. Isso não apaga cadastros nem mensagens. Os tokens são emitidos tanto em server.py como no módulo compartilhado com a mesma versão. Esta etapa depende da proposta #14 e tem branch própria.

Verificação desta etapa: 46 testes Python e 5 testes JavaScript passaram; sintaxe e diff também verificados. O fluxo de entrega de e-mail ao provedor externo não foi testado.

## Terceira etapa: consultas públicas e pessoais

Catálogo e mural públicos retornam somente campos permitidos. O nome público do autor no mural é Aluno; nome real, RM e e-mail ficam disponíveis apenas à secretaria autenticada. Um token de aluno não libera dados administrativos. Tokens inválidos são rejeitados. Site e desktop da secretaria precisam enviar autenticação; o desktop já o faz, e o painel web foi atualizado.

GET /api/itens/meus exige sessão e filtra pelo email_solicitante correspondente ao e-mail do token. A consulta de relatos por RM também exige sessão; para alunos, a seleção é feita pelo e-mail autenticado. Isso evita misturar pessoas com o mesmo nome ou RM. Solicitações legadas sem e-mail precisam de revisão pela secretaria, sem fallback por nome. A API marca respostas como private, no-store e define Vary nos cabeçalhos de autenticação.

Textos livres e imagens não são inspecionados ou anonimizados automaticamente; dados pessoais escritos neles continuam dependendo de moderação. Não há migração ou exclusão de registros. Validação: 58 testes Python e 6 testes JavaScript passaram.

## Quarta etapa: autorização de professores

No portal do professor, a área Ajudar a secretaria apresenta Solicitar acesso ao painel e Atualizar status. Somente contas institucionais de docentes (@etec.sp.gov.br e @cps.sp.gov.br, excluindo @aluno.cps.sp.gov.br) podem solicitar. A identidade vem da sessão e do cadastro; nomes, e-mails e perfis enviados pelo cliente são ignorados. Conta inexistente não cria solicitação.

No painel da secretaria titular, o menu Acesso de Professores permite aprovar ou recusar pedidos pendentes e revogar acessos aprovados. Professores aprovados ganham acesso operacional ao painel: catálogo, cadastros, alterações, exclusões, atendimento e relatórios. Não podem aprovar, recusar ou revogar acessos de outros professores. A autorização é verificada no backend a cada requisição, inclusive quando o professor mantém o mesmo token. Falha no banco retorna 503 em vez de liberar privilégios. A nova área usa textContent para nomes e e-mails.

O estado fica na tabela professores_acesso, criada por init_db em server.py e database.py. O usuário do banco deve ter permissão para criar essa tabela, que referencia alunos(email). O serviço usa a mesma DATABASE_URL já configurada e não exige novas variáveis. Faça backup antes de atualizar uma instalação real. Nenhuma conta recebe aprovação automática. O ciclo de migração foi verificado com PostgreSQL real isolado e também com os contratos SQL em banco temporário.

Se o provedor usa a implementação modular, registrar auth_bp também registra as novas rotas de professores. O backend unificado registra o blueprint diretamente. Os arquivos professores.js e professores-secretaria.js precisam ser publicados junto com HTML e Python; as interfaces dependem desses arquivos novos. Para abrir o painel mantendo a sessão, portal e painel precisam estar na mesma origem. A substituição da URL Railway durante a migração de hospedagem permanece pendente.

A versão verificada tem 72 testes Python e 11 testes JavaScript passando. As verificações de sintaxe incluem o JavaScript inline do painel. Envio de e-mail real, uso sob carga e hospedagem pública continuam fora desta validação. A aprovação confirma a decisão da secretaria, sem comprovar automaticamente vínculos escolares além da conta institucional.

## Quinta etapa: issue #13 e análise visual

Produção usa a função canônica de services.ai_vision_service, eliminando a cópia antiga de server.py. GEMINI_API_KEY ou GOOGLE_AI_API_KEY habilita o provedor e GEMINI_VISION_MODEL permite configurar um modelo disponível para a conta (o padrão existente do serviço é gemini-2.5-flash). A disponibilidade e as permissões reais do modelo não foram verificadas. Consulte as informações do provedor: https://ai.google.dev/gemini-api/docs/models e https://ai.google.dev/gemini-api/docs/deprecations .

Sem chave, quota, resposta válida e análise concluída, o serviço devolve pode_preencher=false e um aviso para preenchimento manual. A estimativa local de cores não é reconhecimento de objetos e não gera título ou descrição automática. Fotos inválidas são rejeitadas antes da chamada ao provedor. MIME é determinado pelos bytes, não pela extensão ou pelo cabeçalho informado pelo cliente.

A UI usa visao-formulario.js para aplicar somente respostas completas do método visual com confiança declarada alta/média. Ausência de confiança é tratada como baixa. OCR só é utilizado quando a análise do objeto e do texto atendem às condições conservadoras; isso não equivale a comprovação de identidade. Na secretaria foi corrigida a normalização de categorias e removida a inserção automática de cores estimadas na descrição. Corpos inline duplicados em tags de scripts externos foram removidos, pois os navegadores não os executam. Resultados atrasados de fotos anteriores são ignorados.

Validação desta revisão: 116 testes Python e 18 JavaScript passaram. Há 44 casos de visão com PNG real em memória e provedor simulado, além de casos de formulário para fallback, baixa confiança, categorias com/sem acentos, preservação de valores manuais e troca de foto durante análise. Essa validação comprova contratos e tratamento de falhas; não comprova reconhecimento visual 100%, acesso ao modelo na conta real, OCR correto em documentos reais ou melhoria quantitativa de precisão.

A issue #13 foi encerrada como concluída a pedido posterior do usuário, após os exemplos discutidos no chat. Essa decisão não substitui a validação com a API real descrita acima. Não houve mudança de hospedagem ou acesso ao banco de produção.

## Sexta etapa: renderização segura de conteúdo

O portal e o painel carregam seguranca-interface.js antes dos scripts existentes. textoHTML codifica os cinco caracteres com significado em texto/atributos HTML. argumentoHTML serializa o valor como JSON e então o codifica para um atributo delimitado por aspas duplas; por isso um nome com aspas continua sendo o argumento original do botão, sem formar código adicional. Os dados enviados à API e salvos no banco não são codificados nem modificados.

Todos os templates HTML identificados em script.js e no painel foram revisados. Fragmentos compostos internos (cards, imagens, badges e linhas de relatórios) continuam sendo HTML, mas os valores interpolados em seu interior recebem a codificação adequada. As áreas de professores já usam textContent/createElement. Diálogos que precisam de negrito e quebras de linha usam uma árvore recriada a partir de template inerte: somente b, strong, em, i, br, p, ul, ol, li, code e span, sem atributos. Não há suporte a HTML arbitrário nos textos de usuários.

URLs de imagem são normalizadas e limitadas a HTTP/HTTPS ou data URI base64 de PNG/JPEG/WebP/GIF. URLs relativas continuam funcionando; SVG inline, javascript:, file: e data:text/html são recusados. Imagens HTTP/HTTPS ainda podem ser externas; isto não valida os bytes de uma URL externa nem é um scanner de imagens. A abertura dessas URLs em outra aba remove acesso ao opener. Os textos livres podem continuar contendo dados pessoais e ainda dependem de moderação.

Validação: os 116 testes Python e 18 testes JavaScript anteriores passaram. Há também 10 testes de regressão no Chromium usando os HTML e scripts reais do projeto. Todas as solicitações de rede são interceptadas e simuladas: não há acesso ao Railway nem a outros serviços. Os testes verificam ausência de elementos/eventos injetados e execução de scripts, preservação literal de símbolos/acentos, argumentos originais de botões, filtros de URL, formatação básica de diálogos e documentos de impressão. Foram verificadas também a sintaxe dos scripts externos/inline e a consistência do diff. Isso cobre os caminhos testados, sem afirmar proteção contra toda vulnerabilidade futura ou contra scripts de terceiros comprometidos.

Para repetir os testes de navegador separadamente (dependência opcional de desenvolvimento):

```bash
pip install playwright
playwright install chromium
python tests/browser_text_safety.py
# Alternativa com Chromium existente:
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_text_safety.py
```

O novo script seguranca-interface.js deve ser publicado junto com os dois HTML e script.js. Não exige variável de ambiente nem migração de banco. A branch parte da proposta #18 e deve preservar as propostas anteriores antes da integração na main.

## Sétima etapa: operações vinculadas à sessão

A pedido do usuário, a validação da matrícula dependerá de lista oficial de e-mails e RMs fornecida pela escola. Como essa lista ainda não está disponível, a implementação da comprovação e unicidade do RM foi adiada. Não foi criada importação de alunos, aprovação manual ou restrição baseada em uma lista vazia.

Esta etapa corrige uma falha separada: POST /api/solicitar e POST /api/itens/cadastrar-aluno passam a exigir token_required. No mural, consulta_publica mantém GET anônimo, mas autentica escritas. O autor da solicitação ou do relato é extraído exclusivamente da sessão assinada. O corpo não pode escolher outro nome, e-mail ou RM. O cadastro de objeto usa o RM da sessão, sem confundir o campo nome (título do objeto) com o nome do autor.

As funções compartilhadas identidade_portal e identidade_aluno verificam o perfil e o domínio institucional da sessão. Professores identificados pelo domínio ETEC/CPS continuam cadastrando objetos e recebem o identificador PROFESSOR nesse fluxo, inclusive com acesso delegado ao painel. Ações pessoais de retirada e relato exigem perfil de aluno, domínio @aluno.cps.sp.gov.br e RM diferente dos marcadores ALUNO/PENDENTE/PROFESSOR. A palavra professor na parte local de um e-mail de aluno não o transforma em docente. A secretaria usa suas rotas administrativas próprias.

O frontend já enviava Authorization nas três operações e agora omite campos de autoria. Clientes antigos que ainda enviam esses campos continuam funcionando, mas seus valores são ignorados. A consulta pública de catálogo e mural, a moderação dos objetos cadastrados e o preflight CORS foram preservados.

A atualização de solicitação também exige aprovado=TRUE ou o valor NULL legado, além de status DISPONÍVEL. Adivinhar o ID de um objeto pendente de moderação não permite solicitá-lo. A condição é verificada na própria atualização, sem separar uma consulta prévia da gravação.

Validação: 134 testes Python e 21 testes JavaScript passaram, além dos 10 testes de renderização no Chromium. Os novos casos executam as rotas reais no servidor unificado e modular, verificam rejeição antes de banco/processamento de fotos e conferem os parâmetros persistidos. Um fluxo adicional usa SQL real em SQLite temporário e duas sessões para solicitar um item, publicar um relato, cadastrar um objeto e consultar os dados pessoais sem atribuí-los à conta citada no corpo adulterado. Fotos e serviços externos foram simulados. Sintaxe Python/JavaScript e git diff --check passaram.

Não exige novas variáveis nem migração de banco nesta sétima etapa. O token continua contendo nome e RM informados durante o cadastro, sem validação contra registros escolares. A confirmação do vínculo, a unicidade do RM, a atualização de sessões antigas e a privacidade de conversas baseadas apenas no RM precisam da revisão de matrículas que foi adiada. A vinculação de push à sessão é tratada na etapa seguinte. Nenhum dado de produção foi consultado ou corrigido; esta etapa não altera a autoria de registros antigos.

## Oitava etapa: cadastro seguro de Web Push

O backend unificado registra o blueprint blueprints.Push, eliminando a rota duplicada sem autenticação. POST e DELETE /api/push/subscribe usam token_required e a identidade institucional da sessão. O servidor ignora os campos de destinatário enviados no corpo. O vínculo é feito por e-mail, inclusive para professores e alunos com RM pendente; não depende da lista oficial de matrículas. A chave pública não é secreta e continua disponível sem login. Foi corrigido também o processamento de tokens em corpos JSON que não são objetos, evitando erro interno antes da rejeição de visitantes.

A tabela push_dispositivos contém endpoint_hash como chave primária, email_aluno com referência a alunos(email), subscription_json e data de atualização. Cada endpoint tem um vínculo atual, permitindo vários dispositivos por conta sem unicidade pelo RM. O upsert é atômico. A exclusão exige correspondência de endpoint e e-mail autenticado e não informa se o endpoint pertence a outra pessoa. Uma assinatura de dispositivo compartilhado pode ser vinculada à nova conta autenticada; conhecer apenas o RM não permite fazer isso.

SCHEMA_PUSH é aplicado nas inicializações de server.py e database.py, depois da criação de alunos. É necessário que o usuário do banco possa criar a tabela. A tabela legada push_subscriptions não é apagada nem convertida automaticamente: seus vínculos anônimos não comprovam autoria. Nenhum componente novo lê essas linhas para enviar notificações. O navegador recadastra sua assinatura após login e permissão concedida, incluindo assinaturas já existentes. Não exige nova variável de ambiente; publicar notificacoes-push.js junto com index.html, script.js e os arquivos Python novos.

Os endpoints aceitam somente HTTPS na porta padrão/443, sem credenciais, fragmentos ou caracteres de controle e com limite de tamanho. As chaves exigem formato base64url e tamanhos de Web Push (auth de 16 bytes, ponto p256dh não comprimido de 65 bytes); isso valida formato, sem provar que o endpoint está ativo ou que a chave está registrada no provedor. Nenhum endpoint é contatado durante cadastro ou teste. Erros de banco retornam mensagem genérica e não registram o erro SQL que poderia incluir chaves.

O portal envia Authorization e somente subscription no cadastro. Quando não há service worker registrado, registra /sw.js antes de aguardar sua ativação; o código anterior somente aguardava um registro que não criava. A recusa do servidor e falhas de rede retornam false, sem anunciar cadastro bem-sucedido. A assinatura nova só é solicitada se a permissão do navegador já foi concedida; o pedido de permissão continua no fluxo existente. Ao sair, a sessão local é limpa imediatamente, tenta-se cancelar a assinatura nativa e excluir o vínculo usando o token capturado. Há espera máxima de 1,5 segundo antes de recarregar para manter o logout disponível em falhas de rede. Operações aguardando o service worker verificam se a sessão mudou; assinaturas novas concluídas após logout são canceladas quando não há outra sessão. A limpeza de navegador/servidor é uma tentativa: falha de rede ou do navegador pode deixar registro para limpeza posterior, e uma requisição já enviada pode concluir depois do logout. Não é revogação global de JWT.

Validação: 195 testes Python e 33 testes JavaScript passaram. Os casos novos executam o SQL real em SQLite isolado e verificam autenticação, persistência por e-mail, contas com o mesmo RM, vários dispositivos, troca de conta, exclusão restrita, validação de entrada, rollback e erros sem dados de assinatura. Os testes JavaScript cobrem assinatura existente/nova, registro do service worker, Authorization, permissão, recusa, falha de rede e tarefas atrasadas no logout. Os 10 testes de renderização no Chromium também passaram. Foi executada uma atualização com tabelas legadas em PostgreSQL real temporário, repetindo ambas as inicializações e exercitando as operações por conta. Sintaxe e git diff --check foram verificados. Nenhum banco ou credencial de produção foi acessado.

Esta etapa protege o cadastro e a desvinculação, sem afirmar entrega de notificações em segundo plano. A revisão encontrou service worker receptor e notificações locais de página, mas não um emissor Web Push no servidor nem dependência correspondente. Implementar o envio deve usar push_dispositivos por e-mail autenticado e nunca voltar à tabela legada por RM. Entrega real ainda requer emissor, VAPID válido, site HTTPS e teste em dispositivos; o valor VAPID de exemplo não serve como credencial de produção.

## Nona etapa: acesso lembrado e animações

O novo acesso-portal.js centraliza SessaoPortal. Login e cadastro oferecem escolha explícita, inicialmente desmarcada. Sem lembrar, token e dados da conta ficam em sessionStorage; ao lembrar, ficam em localStorage com um marcador de consentimento. A senha nunca é persistida pelo aplicativo e o campo é limpo após autenticação bem-sucedida. A duração do JWT continua sendo a existente: a escolha muda o armazenamento do navegador, sem estender o token. Navegadores podem restaurar abas e seu sessionStorage; fechar uma aba não revoga o JWT no servidor.

Sessões legadas persistidas sem o marcador migram para sessionStorage no primeiro uso, para não presumir consentimento. Leitura de token/dados, chamadas do portal, notificações e professores usam a mesma implementação. Ao abrir o painel como docente, o token delegado conserva a preferência de armazenamento; o painel lê sessionStorage antes de localStorage. O login direto da secretaria mantém seu comportamento anterior. Logout remove os tokens das duas áreas e preserva a tentativa de desvincular push da etapa anterior.

A animação usa CSS e SVG locais, sem biblioteca nova: órbitas, lupa, pontos e progresso sem porcentagem fictícia. O estado de sucesso só aparece depois de resposta válida da API e da gravação da sessão; a transição de confirmação dura 450 ms, eliminada em prefers-reduced-motion. Os formulários ficam inertes durante envio, com guarda contra duplicação, aria-busy e status anunciado. Erros encerram a animação, restauram interações e foco e não criam sessão. Formulários também têm transição leve de entrada. Não houve alteração de rotas de autenticação, credenciais ou esquema de banco.

Validação: 195 testes Python, 33 testes JavaScript e 15 testes no Chromium passaram (10 regressões anteriores e 5 novos fluxos em tests/browser_login_experience.py). APIs foram simuladas. Os testes verificam armazenamento real no Chromium, acesso em nova aba, logout, sucesso e recusa do cadastro, falha de rede, cliques repetidos, movimento reduzido, migração de sessão legada e armazenamento do token delegado. Também houve inspeção visual de celular em 390 × 844 sem transbordamento horizontal. O teste de nova aba usa uma aba aberta sem opener, evitando a cópia de sessionStorage que alguns navegadores fazem ao duplicar uma aba. Sintaxe e diff verificados.

Para repetir os fluxos de interface com Playwright e Chromium instalados:

```bash
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_login_experience.py
```

Publicar acesso-portal.js antes dos demais scripts do portal, junto com index.html, script.js, style.css, notificacoes-push.js, professores.js, professores-secretaria.js e o HTML do painel. Não há novas variáveis ou migração de banco. Hospedagem, envio real de e-mail/Web Push e vínculo de matrícula não foram validados nesta etapa.

## Décima etapa: indicador de fotos e confirmação de armazenamento

estado-fotos.js e estado-fotos.css são compartilhados pelo portal e painel. O indicador usa spinner discreto e check verde, aria-live/aria-busy e movimento reduzido. A preparação local mostra a posição real do arquivo no lote; não há porcentagem de rede inventada. Como fotos e dados são enviados na mesma requisição JSON, o estado de envio dura até a resposta da operação completa, incluindo gravação. Não há timeout visual, pausa mínima ou espera pelo toast.

Selecionar arquivos não é anunciado como upload: o estado informa que as fotos estão prontas e serão enviadas ao salvar. O sucesso de envio exige HTTP bem-sucedido e success=true. O formulário fecha após confirmação, com mensagem de sucesso no toast já existente; não se segura o usuário no modal para exibir uma animação. Falhas deixam mensagem e preservam fotos/dados para nova tentativa. Controles de envio, seleção e análise são bloqueados durante as operações pertinentes; guardas impedem chamadas duplicadas. Lotes antigos não preenchem um formulário reaberto. Fotos parcialmente inválidas são indicadas e as válidas permanecem disponíveis, sem anunciar sucesso total.

A compressão usa o mesmo FileReader/Image/canvas nas duas interfaces, até 1200 px e qualidade JPEG 0,75. Erros de leitura/decodificação são tratados. O painel mantém a análise automática existente como etapa separada, sem esperar IA para concluir o indicador de preparação; resultados de análise não são aplicados durante gravação.

A revisão identificou duas causas de confirmação incorreta: processar_fotos ignorava falhas de provedor e retornava uma lista incompleta; o PUT de edição em server.py ignorava completamente o campo fotos. O processamento agora é canônico em services.cloudinary_service. Qualquer foto inválida, falha de upload ou resposta sem URL HTTPS interrompe a operação com erro público genérico. Criações não chegam ao banco; edições não executam UPDATE e fazem rollback. Provider/credenciais não são expostos pela mensagem. URLs existentes continuam sendo reutilizadas sem novo upload. A edição persiste foto de capa/fotos_json, preserva quando o campo é omitido e limpa quando a lista é explicitamente vazia. Não há exclusão de arquivos remotos.

Uploads parciais já concluídos no Cloudinary não são revertidos: em falha posterior, esses arquivos podem permanecer sem associação. Uma falha após envio da requisição também pode deixar resultado incerto por perda de conexão; não há idempotência global de criação nesta etapa. O painel deixou de repetir automaticamente um POST de criação após falha de rede, evitando uma fonte de duplicação; o fallback de PUT para POST de um item existente permanece.

Validação: 214 testes Python, 33 JavaScript e 21 no Chromium passaram. São 19 novos casos Python para contrato do provedor, falha parcial, ausência de URL, criação/edição nas duas versões e persistência de fotos em SQLite real temporário. Os seis novos testes de navegador executam PNG real e verificam preparação, bloqueios, resposta adiada, falha/retry, arquivos inválidos, conservação de fotos existentes, descarte de lote antigo e movimento reduzido. Os 15 casos anteriores de autenticação/renderização continuam passando. O provedor e as APIs foram simulados; a conta real do Cloudinary e hospedagem não foram utilizadas. Sintaxe Python, JS externo/inline e diff verificados.

Para repetir os novos fluxos de navegador:

```bash
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_image_upload.py
```

Publicar os dois novos arquivos estado-fotos.js/estado-fotos.css junto com ambos os HTML, script.js, server.py, blueprints/itens.py e services/cloudinary_service.py. Não há migração de banco ou variável nova. A branch parte da proposta #22; não foi integrada à main nem publicada em produção.

## Décima primeira etapa: transições compartilhadas

movimento.css é carregado no portal, painel e 404. Usa propriedades visuais e keyframes CSS locais, sem observar mutações do DOM, criar timers ou alterar rotas. Há entradas de 150–240 ms para seções, menus e modais; os cards usam 180 ms e uma sequência limitada a 90 ms. Botões, links, campos e tabelas recebem transições de cor/borda/sombra e resposta de pressionamento. Hover com elevação é restrito a ponteiro preciso, evitando deslocamento de cards em telas de toque.

Abas/ancestrais são animados somente por opacidade, evitando criar um containing block transformado para menus e elementos fixos. Modais/cards usam transformações pequenas com animation-fill-mode backwards, sem deixar transformações persistentes após a entrada. A classe hidden mantém seu efeito imediato, inclusive se o usuário fechar durante uma animação. Não são interceptados cliques nem aguardados eventos de animação para efetivar ações. O chat não ganha animações por mensagem, para evitar reentrada de todo o histórico quando o polling o recria. Impressão desativa efeitos CSS.

prefers-reduced-motion desativa animações e transições CSS, incluindo as das etapas anteriores; o carrossel passa a usar scroll automático e o splash com GIF é ignorado antes de definir a imagem. Isso não muda a duração de operações de rede nem animações internas de bibliotecas gráficas existentes. Foco por teclado permanece visível. A coleta de objetos na página 404 conserva seu estado final sem depender da animação quando o movimento é reduzido.

Validação desta etapa: 33 testes JavaScript passaram e 27 testes no Chromium (10 renderização, 5 acesso, 6 fotos e 6 movimento). Os novos casos verificam seções, menus, modais, fechamento imediato, fim sem transform persistente, sequência limitada de cards, ausência de animação nos balões do chat, foco, 404, movimento reduzido e primeiro acesso sem GIF nessa preferência. Foi inspecionada prévia de celular em 390 × 844 sem transbordamento horizontal. Sintaxe JS/inline e git diff --check passaram. APIs simuladas e nenhum dado real utilizado. O backend não mudou e seus testes Python não foram repetidos nesta etapa visual.

```bash
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_site_motion.py
```

Publicar movimento.css junto com os três HTML e script.js. Não há novas dependências, variáveis ou migração de banco. A branch parte da proposta #23; permanecem pendentes o envio real de Web Push, a lista oficial de RM e a hospedagem.


## Décima segunda etapa: emissor de notificações (proposta 25)

Esta etapa implementa o envio Web Push, além do cadastro de dispositivos já protegido. O emissor usa pywebpush 2.5.0, AES128GCM e VAPID P-256. A chave pública só é anunciada quando corresponde à privada; o valor de exemplo foi removido. Sem configuração válida, o teste informa que o envio está desabilitado, e operações normais do site continuam funcionando sem enfileirar notificações. Não foi criada ou publicada credencial de produção.

Os eventos implementados são: resposta da secretaria a uma conversa com autoria autenticada inequívoca, mudança de status/recusa de um item solicitado com email_solicitante e correspondência de objeto cadastrado com relatos do mural que tenham email_aluno. O destino da assinatura é sempre o e-mail da conta. Notificações não contêm nome de aluno, RM, texto do chat ou descrição do objeto; orientam abrir o portal. O OCR por RM não cria um destinatário push. Conversas antigas sem autoria por e-mail ou com mais de uma conta no mesmo RM não recebem destinatário adivinhado; o chat continua gravando normalmente. Mensagens novas de alunos guardam o e-mail da sessão, ignorando autoria enviada no corpo.

As inicializações de server.py e database.py criam push_entregas, índice de agenda, push_ultimo_teste e a coluna opcional mensagens_chat.email_aluno, de forma idempotente. push_entregas guarda um evento por dispositivo, com snapshot da assinatura e e-mail de destino. O worker confere se esse vínculo ainda existe antes de enviar. Reservas com SELECT FOR UPDATE SKIP LOCKED e lease de 90 segundos permitem workers concorrentes e retomada após falha; conclusões condicionadas à tentativa evitam que um worker antigo apague uma reserva nova. O processamento é limitado a lotes de 20, com um thread daemon por processo web, fora da resposta das rotas.

O worker é iniciado preguiçosamente na primeira requisição com configuração válida e retoma a fila persistida, consultando a cada 30 segundos quando ocioso. HTTP 2xx significa aceitação pelo serviço push, não confirmação de que o aparelho exibiu a notificação. 404/410 removem somente a assinatura cujo snapshot/e-mail ainda corresponde; mudanças de conta durante o envio não apagam o vínculo novo. Falhas de rede, 401/403, 408, 429 e erros 5xx recebem no máximo quatro tentativas, com intervalos de 60, 300 e 900 segundos. A requisição ao provedor tem timeout de oito segundos e TTL de uma hora. Um tag estável por evento ajuda o navegador a substituir um aviso repetido, mas não há promessa de entrega exatamente uma vez. Uma conexão perdida após aceitação pode causar repetição.

O envio só acessa endpoints HTTPS dos serviços conhecidos de Chrome/Google, Firefox/Mozilla, Apple e Windows, sem seguir redirecionamentos; URLs arbitrárias não transformam o emissor em cliente HTTP aberto. O contato VAPID é mailto. Erros de provedor e SQL da fila não são registrados com endpoints/chaves. Uma falha ao enfileirar após o commit principal não transforma um cadastro/resposta já salvo em erro. Isso também significa que a gravação principal e a criação do evento são transações distintas: se o banco falhar nesse intervalo, o aviso pode não entrar na fila. O histórico de chat/item permanece a referência do usuário.

O botão Testar Notificações fica no menu de perfil. Ele ativa/recadastra a assinatura do próprio navegador, envia Authorization e pede somente o próprio teste. A API ignora destinatários do corpo e usa a sessão; aplica limite atômico de um teste por conta a cada 30 segundos. A interface informa Teste solicitado, sem anunciar entrega. Ao trocar a chave VAPID, o navegador detecta uma assinatura vinculada à chave anterior e solicita outra. Cliques no aviso abrem somente a origem do site, com ícone local e texto limitado.

### Ativação quando a publicação voltar a ser viável

Instalar requirements.txt atualizado e manter as variáveis já previstas no projeto:

- DATABASE_URL e JWT_SECRET da aplicação.
- VAPID_PRIVATE_KEY: chave privada P-256, em base64url de 32 bytes, DER/base64url ou PEM (quebras reais ou escapes de nova linha).
- VAPID_PUBLIC_KEY: ponto público não comprimido de 65 bytes em base64url, correspondente à privada.
- VAPID_CLAIMS_EMAIL: contato em formato mailto:responsavel@dominio.

O usuário do banco precisa poder criar tabelas/índice e adicionar a coluna de autoria. O site precisa ser servido em HTTPS e ter permissão de notificações concedida no aparelho. No iOS, o Web Push pode depender da instalação do site na tela inicial e da versão do sistema. Não colar chaves no GitHub ou no chat. Não reutilizar chaves de testes. O thread funciona enquanto o processo web estiver ativo; hospedagem que suspende processos suspende também o worker, retomando a fila ao voltar. Há opção de executar um processo dedicado com o mesmo ambiente:

```bash
python -m services.push_delivery
```

Essa ativação e a confirmação em aparelhos reais ficam adiadas por orientação do proprietário, assim como as demais tarefas inviáveis no momento. A implementação foi concluída e os registros antigos de pendência permanecem preservados; não tratá-los como tarefas ativas nem afirmar que já foram executados.

### Verificação realizada

266 testes Python passaram, incluindo 39 casos novos de protocolo/rotas e 13 integrações em PostgreSQL real temporário. A biblioteca Web Push cifrou o payload e assinou VAPID de verdade com chaves efêmeras; somente o transporte HTTP foi interceptado. Os testes decifraram o corpo com a chave do destinatário e verificaram o JWT, TTL, timeout e bloqueio de redirects. Também foram verificados erros de provedor, configuração inválida, fila concorrente, retomada de reserva, cooldown, troca de conta, falha de fila sem desfazer chat e eventos de chat/item/mural nas implementações unificada e modular.

Passaram ainda 40 testes JavaScript e 29 no Chromium: o botão de teste usa a sessão, bloqueia duplicidade, restaura em recusa e anuncia solicitação; o service worker mostra o aviso, abre só o portal e respeita dispensar. As regressões anteriores de acesso, upload, renderização e movimento continuam passando. Sintaxe Python/JS/inline e git diff --check foram verificados.

Não houve contato com um provedor push real, envio para uma conta/dispositivo real, uso de VAPID de produção ou acesso ao banco antigo. Essa verificação comprova implementação de protocolo e integração local; não comprova disponibilidade/aceitação das credenciais da conta de produção, exibição no sistema operacional ou funcionamento com o servidor suspenso.

```bash
python -m pytest -q
node --test tests/*.cjs
CHROMIUM_PATH=/usr/bin/chromium python tests/browser_push_delivery.py
```

Os testes de PostgreSQL são opcionais e requerem pgserver instalado e permissão de socket local; sem ele, esse módulo é ignorado. No ambiente desta tarefa, ele estava instalado e os 13 casos rodaram. Publicar os arquivos Python/JS/HTML, dependência e migrações em conjunto. A branch 25-envio-notificacoes parte da proposta #24 e permanece sem integração à main ou publicação em produção.
