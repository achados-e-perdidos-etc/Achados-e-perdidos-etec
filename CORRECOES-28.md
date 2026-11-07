# Proposta 28 — prioridades da auditoria e upload retomável

Branch única `28-correcoes-prioridades`, dependente da proposta 27. Preserva a logo unificada da secretaria web/desktop.

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
