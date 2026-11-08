# Segurança, retirada e funcionamento offline

Atualização cumulativa da branch `28-atualizacoes-do-projeto`, proposta #29 com base em `main`. Mantém o jogo 404 e as correções anteriores.

## Avaliação das ideias

| Ideia | Decisão e implementação |
|---|---|
| Papéis de acesso | Ampliada a separação existente: aluno, moderador delegado pela escola e administrador geral (secretaria titular). O servidor calcula `perfil` e permissões; o navegador não escolhe privilégios. Somente a titular concede/revoga acesso; a revogação continua sendo verificada a cada requisição do professor. Entrega e auditoria exigem equipe autorizada. |
| Sessões | JWT exige validade, e-mail e papel; tokens em URL/corpo foram desativados. Clientes web e desktop usam cabeçalhos. Hash inválido da senha administrativa nunca vira senha em texto. Códigos de autenticação agora usam aleatoriedade criptográfica. A fila offline não guarda JWT nem senha. |
| Auditoria | Tabela `ocorrencias_itens`, com ID do item, conta responsável, perfil, ação, data do servidor e situação anterior/atual. Gatilho PostgreSQL registra alterações na mesma transação, inclusive exclusão. O e-mail identifica a conta porque já é a chave primária dos usuários. Mudanças automáticas para doação são atribuídas a `sistema:doacoes`. Não há API para alterar/apagar a auditoria; um gatilho também bloqueia UPDATE/DELETE nela. Quem administra o próprio banco continua tendo poderes administrativos. |
| Proteção de arquivos | Uma rotina Pillow verifica bytes reais JPEG/PNG/WEBP, rejeita arquivos inválidos/animados, limita bytes e 16 megapixels, ajusta orientação, reduz para até 1600 px e recria JPEG sem metadados. Aplica-se a novos uploads diretos e à finalização do upload retomável. Novos nomes são UUID; o retomável preserva seu UUID para repetição segura. Links arbitrários não são aceitos como novas fotos. Fotos legadas já vinculadas podem ser mantidas ao editar. |
| Retirada | Implementado código de **seis dígitos**, vinculado ao item e à conta solicitante, válido por 15 minutos. Cinco erros bloqueiam aquele código até vencer; abrir a tela novamente não reinicia tentativas ou prazo. A equipe confere presencialmente a identificação e detalhes do objeto, recolhe assinatura/aceite e confirma. Linha do item e código são bloqueadas no banco; entrega, comprovante e consumo do código são atômicos. Uma chave por operação evita repetir a entrega após perda da resposta. |
| QR de retirada | Escolhido o código digitável entre as duas alternativas propostas, pois funciona em computadores e celulares sem câmera/permissão adicional. Os QR de etiquetas já existentes foram preservados. Um código, assim como QR, não comprova propriedade e não libera a entrega por conta própria. |
| Termo de recebimento | Assinatura desenhada ou aceite por nome digitado é convertido em imagem pequena e guardado em coluna privada do comprovante, sem URL pública no armazenamento de fotos. Consulta exige moderação, usa cabeçalho autenticado e `no-store`. Não se trata de assinatura com certificado digital. A baixa manual existente continua restrita à equipe e agora também auditada; exclusão do item não apaga seus comprovantes. |
| OCR | Mantido o provedor visual já integrado. Nome/RM sem confiança suficiente ficam vazios e o painel de revisão fica amarelo para conferência manual. Não se inventam níveis de confiança por caractere: o provedor atual não os fornece. Anotações da foto não alteram cadastro/matrícula e não disparam notificações por RM. Foi removida a consulta de pessoas por OCR. A análise exige login e não busca imagens em URLs arbitrárias. |
| Cores e categoria | Cores locais são apresentadas como sugestões, com aviso da influência do fundo. Categoria continua dependendo de identificação visual com confiança suficiente e revisão humana. **Descartada a classificação de objeto somente por cor**, que confundiria, por exemplo, casaco e garrafa azuis. Não se adicionaram OpenCV/Tesseract nem modelos pesados só para repetir os recursos existentes. Sem provedor visual disponível, os campos manuais são preservados. |
| Alertas por semelhança | Gatilhos enfileiram itens publicados e aprovados, inclusive após moderação de cadastro do aluno. Worker a cada minuto cruza relatos com categoria e termos específicos, com pontuação mínima de 60; categoria/cor isoladas não bastam. Cada conta recebe no máximo um alerta por item. Central funciona sem permissão push; push usa a fila existente quando VAPID e assinatura do dispositivo estão configurados. Aviso genérico não expõe dados pessoais na tela bloqueada nem declara um dono. |
| PWA offline | Interface do portal, estilos, fontes e ícones estão em cache local versionado; Tailwind é compilado no desenvolvimento, sem CDN em tempo de execução. Bibliotecas administrativas também foram fixadas e hospedadas localmente. Categorias públicas ficam no dispositivo para preencher formulários sem rede. GIFs grandes não entram no precache; a abertura offline pula o splash. A API web usa a origem atual, sem dependência fixa do Railway. |
| Sincronização | Com consentimento por formulário, objetos encontrados e relatos podem entrar em fila IndexedDB, separada por conta, com fotos comprimidas. Limites: 10 envios por conta, até 6 MiB de JSON por envio e aproximadamente 16 MiB por dispositivo. Expiração de 24 horas, com limpeza no próximo acesso; sair explicitamente apaga a fila da conta antes de recarregar. Reconectar sincroniza com o site aberto; ao reabrir, a sessão válida retoma a fila. Não há promessa de envio com navegador fechado nem armazenamento de token para Background Sync. Retirada, moderação e autenticação exigem conexão. |

## Uso

- **Aluno:** solicitar um item abre o código; em Minha atividade, o botão **Código de retirada** permite consultá-lo novamente ou gerar outro após vencer.
- **Secretaria:** menu **Retirada com código**, número do objeto, código apresentado, conferência presencial e assinatura/aceite. O histórico de entregas permite **Ver aceite**.
- **Auditoria:** menu **Ocorrências dos objetos**, informar número do objeto; resultados paginados, inclusive após excluir o item.
- **Offline:** marcar a opção no formulário antes de enviar sem internet. **Minha atividade → Ver fila offline** mostra os cadastros, falhas e descarte. Dados locais só são enviados após verificar a conta no servidor. Campo inválido fica visível como falha; nenhum cadastro local é anunciado como enviado à escola.

## Migração e operação

`SCHEMA_EVOLUCAO` é executado por `server.init_db()` e `database.init_db()` após as tabelas existentes. Cria auditoria, códigos, deduplicação e fila de correspondências; acrescenta assinatura, método e confirmação ao comprovante. Não reconstitui ocorrências anteriores à migração. Mudanças de estado posteriores passam a ser registradas. A rotina de retenção mantém os 30 dias do chat e limpa chaves de sincronização após sete dias; o cadastro e o comprovante não são apagados por essa limpeza.

Os novos workers começam após a inicialização, no primeiro acesso, com coordenação por bloqueios PostgreSQL. A fila de alertas não requer serviço de IA ou serviço pago adicional. Configuração VAPID e credenciais do armazenamento continuam necessárias para os serviços externos reais; um plano gratuito pode suspender processos ociosos, que retomam as filas ao voltar.

A auditoria identifica a conta autenticada. Atendentes devem usar suas contas individuais autorizadas; compartilhar a conta da titular não permite distinguir as pessoas que a utilizaram.

Arquivos internos Python/configuração/testes não são mais servidos pela raiz estática. Respostas incluem `nosniff` e política de referência na mesma origem. Cabeçalhos de preflight incluem os usados por partes de upload e por idempotência.

## Validação

PostgreSQL temporário, migrações repetidas, testes Python/JavaScript e Chromium. Jornadas com Flask real e banco isolado verificam PWA reaberta sem internet, formulário real guardado e sincronizado, upload com resposta perdida após commit sem duplicação, isolamento e expiração da fila, logout, código apresentado pelo aluno, aceite na secretaria, auditoria e revisão visual sem alterar a conta. O armazenamento de imagens é simulado; não se usaram serviços externos reais nem o banco da escola.

Detalhes históricos das etapas anteriores permanecem em `correcoes-28.md`. Evidências locais desta etapa ficam em `/workspace/evolucao-evidencias`.

Resultado: **353 testes Python (incluindo cinco jornadas Flask/PostgreSQL/Chromium), 49 testes JavaScript e 48 testes Chromium das telas anteriores aprovados — 450 testes ao todo**. Após os ajustes finais da assinatura e da apresentação do histórico, as cinco jornadas integradas foram repetidas e passaram novamente. O CSS foi recompilado com as classes atuais do projeto.
