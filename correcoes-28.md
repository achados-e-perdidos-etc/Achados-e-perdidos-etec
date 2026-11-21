# Atualizações do projeto — prioridades, uploads e experiência web

As propostas #29 e #30 foram integradas em `main`, preservando o histórico anterior e a logo unificada da secretaria web/desktop. Por orientação mais recente do proprietário, as próximas alterações são feitas diretamente na `main`, com preservação das versões anteriores, como registrado abaixo.

## Backups numerados — 21/11/2026

Por pedido explícito do proprietário, as três versões existentes receberam nomes em sequência, da mais antiga para a mais recente, preservando os mesmos commits:

| Nome | Código preservado |
| --- | --- |
| `backup-1` | `65ec6a44e16306d899de095964281abcddec685b` — antes dos e-mails personalizados |
| `backup-2` | `33114db045352270b65e8053658fe3fa44bd310e` — e-mails integrados e validados |
| `backup-3` | `97cf91f5599ef778f5fe08ccca64d76434f3d65c` — preservação automática das versões |

Os nomes baseados no SHA são substituídos somente após conferir as referências numeradas. As cópias ZIP também estão disponíveis com os nomes `backup-1.zip`, `backup-2.zip` e `backup-3.zip` em `/workspace/backups-etec`, fora do repositório. Os arquivos de nome anterior são preservados para não quebrar os links já fornecidos no chat.

O workflow agora identifica todos os backups numerados, inclusive com mais de uma página de tags, e reserva o maior número mais um para cada código ainda não preservado. Comparações são numéricas; `backup-10` sucede `backup-9`. Repetir a execução não duplica o backup do mesmo commit. Se dois processos disputarem um número, o alvo existente é conferido e a numeração é recalculada, sem substituir ou apagar nenhuma versão. A mudança se limita ao workflow e às instruções; o código do site permanece igual à versão validada anteriormente.

Validação: YAML/Python conferidos e nove cenários aprovados, cobrindo início da sequência, reutilização do mesmo commit, máximo numérico, paginação com mais de cem tags, duas formas de concorrência, erros de permissão/criação e SHA inválido. Os arquivos ZIP mantêm os mesmos códigos das tags correspondentes. As execuções reais ficam na aba Actions; nenhuma funcionalidade da aplicação foi modificada nesta etapa.

## Main única, integração dos e-mails e cópias de segurança — 21/11/2026

A proposta #30, dos e-mails personalizados, foi mesclada no commit `33114db045352270b65e8053658fe3fa44bd310e`. A árvore resultante é idêntica à versão que passou nos 540 testes Python e nos 12 cenários visuais; o Railway também confirmou a implantação desse commit. A branch `28-atualizacoes-do-projeto` foi excluída com conferência do SHA e somente após verificar que seu conteúdo estava no histórico de `main`. Não houve reescrita do histórico.

As tags `backup-main-65ec6a44e163` e `backup-main-33114db04535` preservam, respectivamente, a versão anterior aos e-mails personalizados e a integração validada. A cópia ZIP do código validado, sem ambientes locais ou configuração privada não versionada, foi salva em `/workspace/backups-etec/codigo-validado-540-testes-33114db04535.zip`, fora do repositório.

O workflow `.github/workflows/backup-main.yml` usa o token temporário do GitHub Actions com permissão de conteúdo para criar tags leves `backup-main-<SHA de 12 caracteres>` da versão anterior e da versão atual a cada push em `main`. Pode ser executado manualmente na própria `main`. Não depende de chave pessoal, não instala pacotes e não copia arquivos para dentro do repositório; os commits são preservados por referência. Tags existentes só são aceitas se apontarem para o mesmo commit; não são movidas ou apagadas. A criação concorrente da mesma tag é conferida antes de prosseguir. Não há exclusão automática de outras branches nesse workflow.

`agents.md` registra a nova preferência: trabalhar diretamente na `main`, guardar o estado anterior antes de cada atualização remota, testar as mudanças e conservar o histórico. O backup automático complementa essa preservação prévia. Para recuperar, consulte as tags no GitHub, compare a versão desejada e faça uma restauração por novo commit, mantendo o workflow e os registros. Uma tag de backup não é, por si só, comprovação de funcionamento; os resultados de testes e conferências públicas continuam registrados separadamente.

Validação do mecanismo: YAML e Python conferidos, com cinco cenários simulados para criação/repetição, preservação de uma tag divergente, concorrência, recusa de permissão e SHA inválido. O ZIP foi aberto e teve sua integridade conferida. Esta etapa muda apenas as instruções, este registro e o workflow; o código da aplicação permanece igual à integração validada nos 540 testes. As execuções reais do backup ficam registradas na aba Actions, e as referências podem ser conferidas na lista de tags do GitHub.

## E-mails com a identidade do portal — 21/11/2026

Os códigos de cadastro e recuperação eram enviados como título e número sem diagramação. O serviço transacional agora utiliza `templates/email_codigo.html`, com a logo do aluno, cabeçalho grafite, faixa vermelha, cartão do código, textos por finalidade e a assinatura “Achados, cuidados, devolvidos.”. O código continua sendo um único trecho de seis dígitos, sem caixas ou espaços inseridos, para permitir copiar e colar. Não aparece no assunto, na prévia da caixa de entrada ou em links.

O HTML usa tabelas, cores e estilos essenciais inline, fontes do sistema e adaptação de tema claro/escuro quando o cliente oferece suporte. A logo é uma imagem HTTPS do endereço oficial `PUBLIC_SITE_URL`; a mensagem mantém o nome da marca, código e instruções mesmo com imagens bloqueadas ou sem domínio configurado no ambiente de teste. Não há fontes remotas, scripts, anexos CID ou logo em base64 no e-mail enviado. A API transacional da [Brevo](https://developers.brevo.com/reference/send-transac-email) recebe HTML e alternativa `textContent`; a [orientação do provedor sobre imagens](https://community.brevo.com/t/does-transactional-email-support-embedded-image/6665) recomenda uma URL pública. Somente `/logo.png`, inclusive em resposta 304 de cache, permite incorporação externa; as fotos pessoais e demais recursos mantêm a política anterior.

O conteúdo é escapado pelo Jinja. O remetente configurado, destinatário, endpoint da Brevo, limites de tempo, recusa de redirecionamentos e confirmação de aceitação pelo provedor permanecem iguais. A validade de dez minutos, uso único, limites de tentativas/reenvio e separação de finalidade continuam no serviço de autenticação. Não foram alterados dados de contas nem enviadas mensagens reais para validar a aparência. A proposta #29 já mesclada não é reaberta; essa alteração posterior utiliza uma nova proposta na mesma branch de trabalho.

Prévias locais com código fictício `123456` em `/workspace/emails-previas`, fora do repositório: cadastro e recuperação, claro/escuro, larguras de 320, 390 e 1024 px. Nos 12 cenários conferidos no Chromium não houve rolagem horizontal; o menor contraste dos textos avaliados foi 5,83:1, e a informação permaneceu legível com imagens ocultadas. Isso valida o modelo renderizado, não uma reprodução exata de todos os clientes de e-mail; Outlook/Gmail/Apple Mail podem ajustar estilos e bloquear imagens.

Validação desta etapa: **540 testes Python aprovados**, incluindo 14 novos casos de HTML/texto, finalidade, cópia dos dígitos, escape, ausência de domínio/chave, erros de rede e recusa do provedor, incorporação da logo em respostas 200/304 e bloqueio do template na raiz estática. A suíte completa inclui os fluxos de autenticação, Flask/PostgreSQL/Chromium e desktop Tkinter/Xvfb. Passaram ainda 64 subtestes, não somados aos 540; os 12 avisos de depreciação do adaptador SQLite são os mesmos das etapas anteriores. As suítes separadas de JavaScript/Chromium do portal não foram repetidas, pois seus arquivos não mudaram. A validação visual do e-mail está descrita acima e as respostas da Brevo foram simuladas.

## Origem HTTPS atrás do proxy do Railway — 21/11/2026

Após o proprietário publicar `https://etec-achados.up.railway.app/`, a conferência pública confirmou GET 200 na página inicial, mas OPTIONS de `/api/auth/enviar-codigo` com a origem correta retornava 403, “Origem não autorizada”. A mesma recusa foi reproduzida localmente quando o navegador usa HTTPS e a conexão interna do proxy com Flask usa HTTP. A comparação anterior com `request.host_url` considerava os esquemas diferentes e bloqueava o próprio site.

O middleware agora acrescenta à lista de origens exatas a raiz HTTPS de `PUBLIC_SITE_URL` e o domínio de `RAILWAY_PUBLIC_DOMAIN`, quando configurados no ambiente do serviço. O segundo é fornecido pelo Railway, não por um cabeçalho da requisição. Não há curinga para `railway.app`, liberação de `null` ou confiança em `Forwarded`/`X-Forwarded-*`. Cabeçalhos CORS retornam somente a origem autorizada; origens adicionais explícitas e clientes nativos continuam com o comportamento anterior. Autenticação, limites e proteção das APIs permanecem exigidos. Configuração de domínio malformada falha na inicialização.

O domínio automático do Railway autoriza o navegador, mas não habilita indexação por conta própria. A consulta pública inicial encontrou `noindex` e sitemap 503 porque faltava `PUBLIC_SITE_URL`. Para configurar o endereço oficial e aplicar a liberação também na versão anterior à correção, usar nas Variables do serviço web:

```env
CORS_ORIGINS=https://etec-achados.up.railway.app
PUBLIC_SITE_URL=https://etec-achados.up.railway.app/
```

Se `CORS_ORIGINS` já tiver outras origens necessárias, preservar os valores e acrescentar a nova origem separada por vírgula. Aplicar as mudanças e reconstruir/reiniciar a implantação com o código atualizado. O chat não possui conexão com o painel do Railway; não houve edição dessas variáveis por ferramenta. Os testes públicos utilizaram apenas GET/OPTIONS, sem criar conta, emitir código de e-mail ou alterar dados da escola. A [documentação de variáveis do Railway](https://docs.railway.com/variables) descreve a variável do domínio e seu uso em tempo de execução.

Validação local: **526 testes Python aprovados**, incluindo 18 novos casos do proxy/origens, os fluxos de Flask/PostgreSQL/Chromium e o desktop em Tkinter/Xvfb. Passaram também 64 subtestes, não somados aos 526; os 12 avisos são a depreciação do adaptador SQLite já registrada nas etapas anteriores. Uma inicialização isolada do servidor real com `RAILWAY_PUBLIC_DOMAIN` confirmou preflight 200 para a origem correta, 403 para origem externa e POST sem dados chegando à validação de e-mail (400), sem consulta ao banco nem envio de mensagem. Sintaxe e diferenças Git conferidas. As suítes JavaScript e Chromium separadas, aprovadas na etapa de SEO, não foram repetidas nesta alteração do middleware HTTP.

## Preparação para aparecer nos buscadores — 21/11/2026

Por solicitação do proprietário, o portal recebeu título e descrição em português com o nome ETEC Achados e Perdidos e uma explicação natural de sua finalidade. O mesmo contexto aparece na tela de acesso. Metadados de compartilhamento, endereço canônico e dados estruturados `WebSite` são entregues pelo servidor no HTML inicial, sem depender da execução de JavaScript e sem inventar vínculo oficial com uma escola específica. Não foi adicionada uma lista oculta de palavras-chave: o Google não utiliza `meta keywords` para classificação.

As rotas `/` e `/index.html` entregam o mesmo endereço canônico. `/sitemap.xml` lista somente a apresentação pública; não inclui contas, objetos individuais, fotos de alunos, conversas, filtros, códigos ou o painel administrativo. `/robots.txt` informa esse mapa quando houver domínio configurado e permite ler CSS/JS e as orientações de indexação. Painéis, APIs, páginas HTML secundárias e erros recebem `X-Robots-Tag: noindex`; a secretaria também tem a indicação no próprio HTML. Essas orientações não substituem a autenticação e a autorização existentes.

No momento desta preparação, o proprietário informou que o site **ainda não estava publicado**. A variável opcional `PUBLIC_SITE_URL` deve ficar vazia nos ambientes de teste. Assim, o portal recebe `noindex`, não produz links para um endereço inventado e o sitemap retorna 503 enquanto falta o endereço. Quando existir hospedagem pública, configurar essa variável com a raiz HTTPS oficial, por exemplo `https://achados.exemplo.org/` (exemplo fictício), e reiniciar o servidor. Caminhos, credenciais, consultas, fragmentos e endereços locais não são aceitos. Canonical, mapa, logo e dados estruturados usam somente essa configuração; `Host` e cabeçalhos de proxy não escolhem o endereço publicado. O endereço antigo do Railway não foi adotado automaticamente nessa etapa; a confirmação posterior da publicação está registrada acima. Cache da PWA versionado para distribuir o HTML atualizado.

Depois da publicação, verificar a propriedade no Google Search Console, enviar `/sitemap.xml` e solicitar a indexação da página inicial. O mesmo mapa pode ser enviado ao Bing Webmaster Tools. Aparecer em resultados orgânicos não exige comprar anúncios; a descoberta, a indexação e a posição dependem de cada buscador. Termos amplos como “ETEC”, “achados” ou “perdidos” competem com muitos sites. Não há promessa de primeira posição nem de prazo fixo. Nenhum pedido de indexação foi feito sem domínio público.

Referências: [Google Search Essentials](https://developers.google.com/search/docs/essentials), [mapas do site](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap) e [metadados aceitos](https://developers.google.com/search/docs/crawling-indexing/special-tags).

Validação desta etapa: **508 testes Python, 50 JavaScript e oito Chromium focados em login/abertura — 566 aprovados**. A suíte Python completa inclui 26 novos casos de SEO, resposta HTML sem JavaScript, configuração ausente/inválida, canonical sem consulta ou cabeçalhos do visitante, mapa XML público e exclusão das áreas pessoais. Inclui também os fluxos existentes com PostgreSQL temporário, navegador e Tkinter/Xvfb. Passaram ainda 64 subtestes, não somados aos 566; permanecem os 12 avisos de depreciação do adaptador SQLite dos testes. Sintaxe JavaScript e diferenças Git conferidas. As demais regressões Chromium separadas, aprovadas anteriormente, não foram repetidas. Sem publicação, acesso ao banco da escola ou submissão a buscadores.

## Senhas formadas somente por espaços — 21/11/2026

A revisão de estabilidade reproduziu cadastros e redefinições que aceitavam doze espaços ou tabulações como senha. A validação compartilhada agora recusa senhas compostas somente por espaços em branco, inclusive Unicode, antes de acessar o código de e-mail. A mensagem orienta a corrigir a senha, sem apagar o código, incrementar suas tentativas ou modificar a conta. A senha com texto conserva seus espaços iniciais/finais e continua funcionando no login.

Os testes de regressão verificam as duas rotas, o cadastro ativo e modular e a recuperação em PostgreSQL temporário: a tentativa inválida preserva a conta e o código; a correção com o mesmo código conclui a operação. O teste existente de recuperação no navegador também confere a senha exata com espaços nas pontas. Nenhuma migração ou configuração nova é necessária.

Validação desta correção: **482 testes Python e 64 subtestes aprovados**, com a suíte completa e sem seleção parcial, incluindo os fluxos de navegador e Tkinter/Xvfb. Os sete casos novos estão incluídos nos 482, sem somar os subtestes à contagem. Os 12 avisos são de depreciação do adaptador de datas SQLite usado nos testes. As suítes separadas de 51 regressões Chromium e 50 JavaScript, aprovadas na revisão imediatamente anterior, não foram repetidas porque esses arquivos não mudaram. Sem acesso ao banco da escola ou implantação.

## Revisão de segurança — 16/11/2026

Autenticação com sessão revogável, proteção de recuperação/códigos por conta, finalidades distintas e uso único, política de senha, proteção de concorrência e cabeçalhos/CORS. Fotos com autoria conferida e normalização antes da análise externa; cliente desktop protege credenciais, TLS e redirecionamentos. Dependências atualizadas. Escopo, operação, resultado da auditoria e limites da validação em [seguranca-28.md](seguranca-28.md).

Validação concluída na retomada de 21/11/2026: **475 testes Python, 51 Chromium e 50 JavaScript aprovados — 576 no total**, incluindo os 140 casos integrados antes bloqueados por sockets. Auditoria completa dos 46 pacotes Python sem avisos conhecidos ou pacotes ignorados. A checagem de CSP foi corrigida para executar pela página, sem o privilégio do depurador; a política do site foi preservada. A proposta continua em rascunho, com `main` sem integração.

## Foto privada, termos e contraste — 15/11/2026

Por pedido explícito do proprietário, alunos e professores podem adicionar, substituir e remover uma foto opcional no menu do perfil. Orientações: foto individual, de frente, cabeça e ombros, rosto e olhos visíveis, boa iluminação, sem máscara, óculos escuros, filtros, montagens ou objetos sobre o rosto. A secretaria web e desktop consultam o perfil nas conversas e na retirada de um objeto solicitado, usando a conta vinculada à solicitação, sem deduzir identidade pelo RM.

O servidor valida os bytes reais (JPEG/PNG/WEBP estático, até 2 MB e 16 MP), corrige orientação, remove metadados e usa modelos locais OpenCV de rosto frontal e olhos. Rejeita enquadramento sem um único rosto detectável, pequeno ou com olhos não detectáveis. A foto é recortada e reduzida a 160 × 160 pixels; há uma única imagem de no máximo 64 KB por conta, no banco, sem envio ao provedor de análise de objetos. Arquivos/modelos vêm de `opencv-python-headless` em `requirements.txt`. A amostra NASA dos testes está atribuída em `vendor/terceiros.md`.

**Limite:** detecção não é reconhecimento de identidade, prova de autenticidade, presença física ou garantia de que toda obstrução seja identificada. Pode recusar uma foto adequada ou aceitar uma imagem inadequada. As instruções informam isso; cadastro/login continuam disponíveis sem foto e a equipe deve conferir os dados presencialmente.

Fotos não aparecem no catálogo público. A API exige sessão e permite leitura apenas ao titular e à equipe autorizada, com revogação de professor conferida por requisição. URLs UUID mudam na substituição; exclusão remove a imagem. Metadados e bytes são privados e não entram no cache PWA. O navegador usa blobs temporários, sem gravar fotos no armazenamento local; saída/troca de conta fecha as janelas e limpa as prévias.

Novos cadastros precisam abrir os Termos de Uso e percorrer o texto até o fim antes de habilitar a caixa de aceite, usando toque, roda do mouse ou teclado. A caixa nunca é marcada automaticamente. Fechar no meio mantém o bloqueio; atualizar a versão exige nova leitura. O backend aceita apenas `aceite_termos: true` com a versão atual. Conta, versão/data do aceite e consumo do código são confirmados na mesma transação; falha preserva o código e reverte a conta. Não há exigência retroativa para contas existentes. `/api/termos` e `/termos` usam o mesmo texto; alterar o texto exige atualizar `VERSAO_TERMOS` em `utils/perfis.py`.

**Limite do aceite:** a rolagem é um requisito da interface; não comprova que o texto foi lido ou compreendido. O servidor registra a declaração de aceite e a versão, não um suposto comprovante de leitura.

No tema claro, corrigidos os rótulos sobre fotos do catálogo, o link de detalhes, textos/ajudas do cadastro e a ação de descartar rascunho. Contraste dos pontos conferidos no navegador é de pelo menos 4,5:1. Cache PWA atualizado para incluir `perfil.js` e `perfil.css`.

Validação: **433 Python, 49 JavaScript e 51 Chromium — 533 testes aprovados**, incluindo 25 novos casos de foto/termos, jornadas reais com Flask/PostgreSQL/Chromium, gestos de toque, teclado e consulta de foto no Tkinter/Xvfb. O fluxo nativo existente foi ampliado, sem criar outra raiz Tk no processo. Após os ajustes finais de ajuda e validação do documento, os quatro fluxos de navegador de perfil/termos foram repetidos. Sem alteração no banco da escola, implantação, câmera/impressora físicas ou prova de autenticidade de fotos.

## Acabamento e abertura mais leve

Os GIFs de abertura foram substituídos por dois clipes MP4 H.264 de 2,2 segundos, gerados a partir da apresentação original: **27.717.854 bytes → 819.960 bytes, redução de 97,04%**. As fontes anteriores continuam no histórico Git. O portal escolhe somente o vídeo adequado à orientação da tela; não inclui os vídeos no precache da PWA. A sessão começa a carregar no DOMContentLoaded, paralelamente à apresentação, com proteção contra inicialização duplicada.

O botão “Entrar no site” permite pular imediatamente. A abertura é encerrada após no máximo 2,4 segundos; falha de reprodução, falta de rede, economia de dados, conexão 2G, movimento reduzido ou retorno na mesma sessão levam diretamente ao portal. Ao fechar, a mídia é pausada e a origem removida. Escape e foco de teclado respeitam a janela ativa. O servidor serve MP4 e aceita requisições parciais de vídeo; o cache da interface foi versionado.

Nos formulários, campos inválidos recebem instruções curtas associadas ao campo; digitação válida remove a indicação, preservando o conteúdo dos demais campos. O e-mail do login usa um exemplo mais curto. Altura útil dos modais acompanha o viewport dinâmico, há rolagem interna e maior área de toque para fechar o cadastro e limpar a pesquisa. O ajuste de altura só vale na tela, preservando a impressão. Contraste de mensagens e textos auxiliares foi revisado nos temas claro/escuro.

Verificação focada: formulários de aluno e secretaria, retenção de texto após erro, temas claro/escuro, contraste mínimo de 4,5:1 nos textos conferidos, larguras de 320/390/768/1366 e redução da altura para simular teclado aberto. A entrega de MP4 e respostas HTTP 206/Range foram conferidas pelo servidor real, com serviços externos controlados. Nenhuma funcionalidade de negócio foi acrescentada.

Validação desta etapa: **408 testes Python, 49 JavaScript e 51 Chromium — 508 aprovados**. A suíte Python inclui as jornadas com PostgreSQL/Chromium, impressão/PDF e o fluxo nativo Tkinter/Xvfb. Não houve implantação em servidor nem uso de dados da escola.

## Limpeza de arquivos sem uso

Os 194 arquivos versionados foram revisados por entradas de execução, importações Python, registros de rotas, referências de recursos estáticos, manifestos, testes e documentação. Foram removidos três módulos sem consumidores ou registro na aplicação: `blueprints/ai.py`, `blueprints/ai_vision_service.py` e `blueprints/frontend.py`. As rotas de IA, páginas, logotipos e erro 404 continuam no servidor executado pelo `Procfile`; o serviço de visão utilizado permanece em `services/ai_vision_service.py`.

Os módulos utilizados pelos testes de compatibilidade, os dois pontos de entrada (`server.py` e `app.py`), os recursos do desktop, animações referenciadas, configurações, orientações e licenças foram preservados. O `.gitignore` evita adicionar caches, ambientes locais e configuração privada. O aviso da tela de acesso passou a informar somente que o site aceita e-mails institucionais de alunos e professores; as regras de validação continuam iguais. O cache da PWA foi versionado para distribuir a mensagem atualizada.

Após a limpeza, passaram **404 testes Python, 49 JavaScript e 48 Chromium — 501 no total**, sem remover testes. Também foram conferidos 56 recursos estáticos, as páginas e os aliases da secretaria, além da resposta 404. A varredura de importações não encontrou outros módulos Python sem caminho de uso pelas entradas ou pelos testes. Não houve alteração no banco de produção nem publicação em servidor.

### Por que os três arquivos existiam

O histórico remoto registra os três na organização modular de setembro de 2026. A versão histórica de `app.py` criava uma aplicação Flask e registrava blueprints; hoje esse arquivo importa a mesma aplicação de `server.py`. A remoção de cópias que deixaram de ser carregadas preserva as funções nos caminhos ativos abaixo.

| Arquivo apagado | Finalidade original confirmada pelo conteúdo e histórico | Caminho atual a reutilizar |
| --- | --- | --- |
| `blueprints/ai.py` | Reunir as rotas de sugestão de dados de uma foto e comparação de descrições em um blueprint de IA. | Rotas `/api/ia/analisar-imagem` e `/api/ia/comparar-semantica` em [server.py](server.py); serviço de visão em `services/ai_vision_service.py` e comparação em `utils/helpers.py`. |
| `blueprints/frontend.py` | Entregar o portal, painel da secretaria, logotipos, favicon e página 404. Era registrado pela antiga fábrica de aplicação. | Rotas de páginas e tratamento 404 em [server.py](server.py); os próprios HTML, imagens e recursos do jogo continuam no projeto. |
| `blueprints/ai_vision_service.py` | Inicialmente continha processamento de fotos, extração de cores e integração de visão. Na versão anterior à exclusão, tinha apenas duas linhas para reexportar o serviço mantido em `services`, por compatibilidade. Essa reexportação já não era importada. | [services/ai_vision_service.py](services/ai_vision_service.py), que é importado diretamente pelo servidor. |

Fontes históricas: [rotas de IA](https://github.com/achados-e-perdidos-etc/Achados-e-perdidos-etec/blob/a484cacbe2c30870c3421390a8d7b110695d94ae/blueprints/ai.py), [fábrica antiga que registrava o frontend](https://github.com/achados-e-perdidos-etc/Achados-e-perdidos-etec/blob/965aa87889e161cdbe5d354e6b1f12129d2a53bc/app.py) e [serviço de visão na pasta antiga](https://github.com/achados-e-perdidos-etc/Achados-e-perdidos-etec/blob/1d9282fbb21558312642e0769d3bc4061852f9f0/blueprints/ai_vision_service.py).

Para próximas alterações, evolua os caminhos atuais acima. A orientação também está em `agents.md`, para evitar recriar arquivos de rotas ou de compatibilidade que a aplicação não utiliza. Uma eventual reorganização futura precisa migrar os pontos de entrada e consumidores de forma explícita, preservando os testes.

Na rechecagem solicitada após a remoção, os **501 testes foram executados novamente e aprovados**: 404 Python, 49 JavaScript e 48 Chromium. A conferência adicional verificou os 56 recursos estáticos, aliases da secretaria, respostas 404 HTML/JSON, proteção da análise de imagens, chamada do serviço atual com provedor simulado e comparação de descrições. Foi confirmado que `app.py` e `server.py` expõem a mesma aplicação e que a limpeza não modificou `server.py`, `app.py`, `services/` ou `utils/`. A validação foi local, com banco temporário e integrações externas controladas.

## Aparência, buscas salvas e preferências

[preferencias-e-atalhos.md](preferencias-e-atalhos.md): escolha de tema claro, escuro ou automático, com convite antes de acompanhar o sistema; dez buscas salvas por conta no navegador; filtros e apresentação lembrados; atalhos administrativos com contagens privadas; preferências e atalhos equivalentes no desktop. O [roteiro para colegas](teste-com-colegas.md) está pronto, sem alegar teste humano já realizado.

Validação cumulativa da etapa de preferências: **404 Python, 49 JavaScript e 48 Chromium — 501 testes aprovados**. As contagens das seções seguintes são registros históricos de cada etapa.

## Paridade dos painéis e comprovante personalizado

Matriz e validações em [paridade-secretaria.md](paridade-secretaria.md). Os painéis administrativos passam a oferecer os mesmos recursos de relatórios, etiquetas, filtros, mural, câmera, fotos e retirada com aceite, respeitando papéis. O comprovante compartilha um modelo A4 com logo, cores do portal e ilustrações de objetos. Validação cumulativa: **396 Python, 49 JavaScript e 48 Chromium — 493 testes aprovados**. Serviços externos/hardware e Windows seguem com os limites de validação descritos no documento.

## Comprovantes com impressão

[comprovantes-impressao.md](comprovantes-impressao.md): opção de impressora/PDF na baixa manual, no histórico e na confirmação por código. Folha A4 somente com o comprovante, aceite quando existente e identificação de entrega revertida. Desktop abre a versão local para imprimir, preservando os dados do histórico e removendo temporários ao sair.

Validação cumulativa atual: **378 testes Python, 49 JavaScript e 48 Chromium — 475 aprovados**. PDF fictício A4 de uma página em `/workspace/comprovantes-evidencias`. Equipamento físico não foi utilizado.

## Revisão de experiência, catálogo e moderação

Etapa atual em [experiencia-e-catalogo.md](experiencia-e-catalogo.md): navegação visível e responsiva, orientações de retirada e análise, login mais claro, filtros removíveis, feedback fiel à resposta do servidor e correções de sobreposição/foco/offline. Inclui catálogo paginado, fotos sob demanda, busca sem acentos com filtros combinados, recusa com motivo e correção pelo autor, histórico ampliado, aviso de duplicidade e moderação/gestão de professores no desktop.

Validação cumulativa atual: **373 testes Python, 49 JavaScript e 48 Chromium aprovados — 470 testes**. Inclui nove jornadas Flask/PostgreSQL/Chromium e fluxo Tkinter real em Linux/Xvfb. Capturas em `/workspace/experiencia-evidencias`. Resultados abaixo são históricos de cada etapa.

## Ampliação de segurança, retirada e PWA

Avaliação e implementação das novas ideias em [evolucao-seguranca-pwa.md](evolucao-seguranca-pwa.md): papéis explícitos, auditoria transacional, fotos verificadas e normalizadas no servidor, retirada com código e aceite privado, revisão visual, alertas deduplicados e fila offline por conta. A tabela de decisões explica as alternativas descartadas e os limites dos recursos externos.

## Página 404: Operação Achados

Nova tela responsiva com jogo da memória de objetos perdidos. As fases têm 6, 8 e até 10 pares, combos de até 3×, bônus de tempo, duas dicas por fase, pausa, repetição e recorde local. O jogo só começa após uma ação explícita; sair da aba pausa a partida. Teclado, toque, redução de movimento e armazenamento bloqueado são contemplados. Os links para voltar ao portal continuam disponíveis, inclusive sem JavaScript.

Validação desta atualização: **326 testes Python, 49 JavaScript e 48 Chromium aprovados (423 testes)**. As nove jornadas específicas do jogo cobrem progressão, combos, tempo, tentativas rápidas, dicas, pausa, teclado, toque e armazenamento indisponível. A correção final de foco após encontrar um par foi validada repetindo essas nove jornadas. Foram conferidas larguras de 320 a 1920 px e produzidas capturas de computador e celular.

O jogo não chama APIs, não grava no banco nem altera autenticação. CSS e JavaScript usam caminhos absolutos para carregar também em URLs inexistentes aninhadas. O service worker inclui os novos recursos em uma versão nova do cache. O servidor mantém o status HTTP 404 e o retorno JSON das rotas `/api/` inexistentes.

## Correções entregues

- **A27-01:** conversas identificadas pelo e-mail autenticado. Respostas administrativas exigem conta explícita. Contas com o mesmo RM têm conversas, leitura e notificações separadas. Mensagens sem autoria legada permanecem disponíveis apenas à secretaria, em histórico somente de leitura; não são atribuídas por suposição.
- **A27-02:** reversão na mesma transação do item, com bloqueio da linha. Guarda data e responsável em `cancelada_em`/`cancelada_por`; histórico e indicadores ativos excluem canceladas. Web e desktop permitem consultar revertidas. Repetir a entrega não duplica comprovante; um comprovante antigo não pode desfazer uma entrega nova.
- **A27-03:** validação compartilhada de título, descrição, tipos, limites, categoria cadastrada, data e situação antes de processar fotos. Atualizações parciais preservam os campos omitidos.
- **A27-04:** HTTP, compressão, download de miniaturas e gravação CSV do desktop executam em workers; callbacks e widgets são atualizados pela thread Tk. Operações duplicadas são bloqueadas/coalescidas, respostas de sessão/conversa anterior são descartadas, erros ficam visíveis e leituras podem ser tentadas novamente. Sessão expirada limpa dados e polling; há saída/troca de conta. Falha de gravação mantém o formulário sem repetir automaticamente operações incertas.
- **A27-05:** exportadores CSV web/desktop neutralizam fórmulas, inclusive com espaços/controles e formas Unicode equivalentes; aspas, separadores e quebras são preservados.
- **A27-06:** categorias desktop ordenadas por quantidade, usando agregados da API, sem depender da ordem das respostas do catálogo.

## Chat: retenção de 30 dias

O banco grava `criada_em` automaticamente. O cliente não escolhe a idade da mensagem. Mensagens com mais de 30 dias deixam de aparecer e são eliminadas em lotes; um worker inicia no primeiro acesso após as migrações e repete a limpeza a cada hora. Falhas temporárias são tentadas novamente; trava PostgreSQL coordena processos concorrentes. A limpeza abrange mensagens atuais e legadas e não remove contas, itens nem comprovantes.

**Migração conservadora:** mensagens antigas que não possuíam data estruturada recebem a data da migração. Seu prazo inicial é de 30 dias após essa migração, evitando apagar registros com base em texto de data inválido. Histórico sem autoria continua restrito à secretaria durante esse prazo.

## Fotos: retomada no portal do aluno e secretaria web

Cada foto tem barra real de bytes confirmados e seu botão de nova tentativa. Partes de 64 KB são confirmadas individualmente. Uma falha não cancela as demais fotos; concluídas são reaproveitadas e o objeto só é gravado após todas terem URL confirmada.

Antes de retomar, o navegador consulta a posição do servidor, inclusive quando a resposta de uma parte se perdeu. Repetir uma parte não duplica dados. Reselecionar a mesma imagem comprimida permite reencontrar a sessão por hash e conta. Não se armazenam fotos no localStorage/sessionStorage. As sessões temporárias expiram após 24 horas sem atividade: depois disso pode ser necessário reenviar. Cada imagem pode ter até 2 MB após compressão, no máximo quatro pendentes por conta e 32 MB de reservas temporárias globais. As partes são armazenadas separadamente para evitar regravar o arquivo inteiro; são removidas ao concluir, descartar ou expirar.

A retomada é entre navegador e servidor. Se o armazenamento externo falhar na finalização, os bytes já confirmados permanecem no servidor e apenas essa etapa é repetida. A publicação usa um identificador estável para evitar duplicar o arquivo externo. O ambiente real precisa das credenciais Cloudinary; os testes substituem o provedor por respostas controladas. Requer HTTPS ou localhost para o cálculo de hash no navegador.

O desktop mantém o envio de fotos pelo fluxo existente, agora sem bloquear a janela. As barras e sessões de upload retomável desta proposta pertencem ao portal e ao painel web.

## Validação

Suíte Python com PostgreSQL temporário; testes JavaScript e Chromium; jornadas reais com Flask/PostgreSQL isolado. Foram exercitados colisão de RM, histórico legado, reversão repetida/concorrência de recibo, rollback, cadastros inválidos, retenção, limpeza coordenada, fórmulas CSV, workers desktop e retomada de fotos por conta.

O teste integrado web interrompeu uma foto após 65.536 bytes, concluiu outra, retomou do ponto confirmado e salvou duas URLs sem reenviar a foto pronta. A interface Tkinter real foi executada em Linux/Xvfb, com login, sete abas e cadastro; confirmou que a colisão de RM não expõe mais a conversa e que cadastro vazio retorna 400.

Não houve alteração no banco da escola nem na hospedagem. Não se validou um executável Windows, impressora física ou entrega real dos serviços externos. Testes aprovados cobrem os cenários executados, sem garantir ausência absoluta de defeitos.

Resultado final das suítes: **324 testes Python, 49 testes JavaScript e 39 testes Chromium aprovados (412 testes)**. O teste específico da retomada foi repetido após acrescentar os limites de espera por requisição. As duas jornadas adicionais — desktop gráfico e upload web com Flask/PostgreSQL — também terminaram sem erro de callback ou JavaScript nos cenários executados.
