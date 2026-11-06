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
