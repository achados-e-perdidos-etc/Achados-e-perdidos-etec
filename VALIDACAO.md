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
node --check sw.js
node tests/test_portal_auth.cjs
```

Os testes usam o cliente Flask real, banco simulado e uma tabela SQLite temporária para executar o SQL de doações. Não verificam a conexão com PostgreSQL em produção nem serviços de e-mail, imagens, IA ou push. Não inserem ou removem dados reais.

## Comportamentos corrigidos

- Rotas administrativas exigem perfil `secretaria`; token de aluno recebe 403 e visitante recebe 401.
- Categorias continuam disponíveis para consulta pública; alterações exigem secretaria.
- Chat exige autenticação; aluno só pode usar o RM do token, e nome/remetente vêm da sessão. RMs genéricos não podem acessar conversas.
- Site, painel e aplicativo desktop enviam autenticação nas chamadas do chat.
- Doações pendentes são contadas pelo mesmo filtro usado na conclusão, incluindo nomes históricos. Concluir arquiva como `DOAÇÃO FEITA`, preservando registros.
- Servidor e testes usam a mesma validação de e-mail institucional, incluindo CPS e ETEC.

Esta é uma primeira etapa. Ainda é necessário revisar a comprovação e unicidade do RM no cadastro/alteração, exposição de dados pessoais e renderização de conteúdo informado por usuários. A sessão identifica o RM declarado na conta; não comprova vínculo com a matrícula escolar.

## Aplicar o pacote

O arquivo `correcoes-achados-etec.zip` contém somente os arquivos corrigidos e documentos, com os caminhos do repositório preservados. Faça uma cópia do projeto antes de substituir os arquivos. O pacote não contém dados do banco nem credenciais de produção. Esta etapa deve ser revisada antes da integração à branch principal.

## Segunda etapa: professores

Professores entram com e-mail institucional e senha individual cadastrada. O login professor/professor foi removido. O portal deixa de fabricar tokens quando a rede falha, descarta os antigos tokens fictícios e permite solicitar códigos para e-mails CPS e ETEC.

Todos os tokens de sessão novos carregam auth_version=2. Tokens anteriores são recusados, inclusive os da antiga conta compartilhada; alunos e secretaria precisarão entrar novamente na publicação. Isso não apaga cadastros nem mensagens. Os tokens são emitidos tanto em server.py como no módulo compartilhado com a mesma versão. Esta etapa depende da proposta #14 e tem branch própria.

Verificação desta etapa: 46 testes Python e 5 testes JavaScript passaram; sintaxe e diff também verificados. O fluxo de entrega de e-mail ao provedor externo não foi testado.
