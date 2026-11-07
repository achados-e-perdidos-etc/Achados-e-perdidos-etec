# Atualizações do projeto — prioridades, uploads e experiência web

Branch única `28-atualizacoes-do-projeto`, com a proposta #29 apontando para `main`. Reúne o histórico anterior e preserva a logo unificada da secretaria web/desktop. Por orientação do proprietário, as próximas atualizações ficam nesta mesma branch.

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

Validação cumulativa mais recente: **404 Python, 49 JavaScript e 48 Chromium — 501 testes aprovados**. As contagens das seções seguintes são registros históricos de cada etapa.

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
