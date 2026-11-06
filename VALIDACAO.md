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
node --check sw.js
node tests/test_portal_auth.cjs
node tests/test_privacy_portal.cjs
node tests/test_teacher_portal.cjs
node tests/test_vision_form.cjs
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
