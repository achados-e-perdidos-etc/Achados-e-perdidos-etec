# Achados e Perdidos ETEC — pendências

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
- [ ] Configurar segredo JWT novo na hospedagem antes da publicação; a troca invalida tokens antigos.
- [ ] Comprovar e garantir unicidade do RM no cadastro e alteração, impedindo contas com matrícula de terceiros.
- [ ] Revisar renderização de conteúdo informado por usuários para impedir injeção de HTML/scripts.
- [x] Removido login compartilhado professor/professor e sessões fictícias do navegador. Professores usam conta institucional com senha individual; tokens antigos exigem novo login.
- [x] Catálogo e mural públicos usam lista explícita de campos sem nome do autor, RM ou e-mail de alunos. Dados administrativos exigem token de secretaria; consultas pessoais filtram pelo e-mail da sessão. Conteúdo livre de descrições e imagens ainda pode conter dados pessoais e exige moderação.
- [ ] Após a migração, substituir a URL Railway fixa no frontend e verificar também painel e aplicativo desktop.

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
