# Revisão de segurança — validação concluída em 21/11/2026

Alterações na branch `28-atualizacoes-do-projeto`, proposta #29, preservando `main`. A revisão abrangeu contas, autorização, recuperação de senha, arquivos, respostas HTTP, integrações e clientes web/desktop. Não houve implantação nem acesso ao banco da escola.

## Contas e sessões

- JWT com emissor e público definidos, identificador aleatório de sessão, data de emissão, expiração e `auth_version=3`. Assinatura limitada a HS256. Tokens anteriores exigem novo login. Validade padrão: sete dias para o portal pessoal e oito horas para a secretaria.
- Logout registra a revogação do token no PostgreSQL. Redefinir senha invalida as sessões anteriores da conta, inclusive entre workers. Se o banco não puder confirmar a sessão, a operação privada retorna indisponibilidade e não prossegue por omissão.
- A limpeza de tokens revogados conserva os 60 segundos de tolerância usados na validação de expiração. Atualizar o RM mantém a identidade da sessão e sua validade original; não cria outra sessão capaz de escapar de uma revogação. O RM continua sendo informação declarada, sem alegação de validação pela lista oficial da escola.
- Login bloqueia a linha da conta durante a conferência e emite o token antes de liberá-la, impedindo uma redefinição concorrente de deixar válido um token emitido com a senha anterior. Código, senha e revogação são gravados na transação correspondente.
- A saída local continua imediata. Revogação remota depende de alcançar o servidor; no navegador há um limite de espera de dois segundos. Sair sem conexão não comprova revogação remota. Professores continuam com aprovação/revogação conferida por requisição, e a concessão de privilégios pertence apenas à secretaria titular.

## Códigos, senhas e tentativas

- Código de seis dígitos, válido por dez minutos, armazenado como HMAC com a chave do servidor, sem guardar o valor enviado por e-mail. Cadastro e recuperação possuem finalidades distintas; um código não autoriza a outra operação. O uso é único e protegido por trava da linha.
- Cinco códigos incorretos bloqueiam o código. Solicitações de envio têm intervalo de um minuto e limite de três por conta em quinze minutos. Contadores persistidos não são contornados apenas trocando de IP ou worker.
- Login pessoal e administrativo têm limite de oito tentativas por conta em quinze minutos; autenticar corretamente limpa esse contador. Há também limites por IP no servidor unificado. O armazenamento dos contadores possui limpeza de registros antigos e índices para essa limpeza.
- Novas senhas e redefinições exigem de 12 a 128 caracteres. Senhas existentes continuam podendo ser usadas; espaços e maiúsculas não são removidos pelos clientes nem pelo servidor durante login/cadastro/redefinição. Hashes usam o mecanismo atual do Werkzeug.
- `ADMIN_SENHA_HASH` tem prioridade sobre a configuração legada de senha em texto. Quando somente a configuração legada existe, a comparação usa tempo constante. O valor do hash não é aceito como senha.
- Respostas de recuperação usam mensagem genérica; isso não constitui garantia contra inferências de tempo de resposta. O provedor precisa aceitar o e-mail para confirmar a operação; falha retorna indisponibilidade e remove o código daquela tentativa, sem apagar eventual código mais recente.
- Rotas de conta aceitam até 16 KB por requisição. Campos malformados são recusados antes do processamento sensível. Implementações de autenticação ativa e modular compartilham o mesmo serviço de códigos/senhas. O SSO modular permanece fora do servidor ativo; nele, a configuração de client ID, audiência, emissor e expiração são obrigatórias, e contas novas devem seguir o cadastro com termos.

## Navegador e arquivos

- CORS aberto foi removido. O padrão aceita a mesma origem; origens adicionais precisam constar explicitamente em `CORS_ORIGINS`. `Origin: null`, origens estranhas e curingas não recebem acesso por CORS. Clientes nativos continuam autenticando por token, sem precisar enviar `Origin`.
- Cabeçalhos `nosniff`, política de referência, proteção contra enquadramento, isolamento de abertura e restrição de câmera/microfone/localização. HSTS é enviado quando o Flask recebe HTTPS; uma terminação TLS no proxy precisa aplicar HSTS ou fornecer uma configuração de proxy confiável. Cabeçalhos de proxy fornecidos pelo visitante não são considerados confiáveis automaticamente.
- CSP restringe conexões, imagens, fontes e mídia; bloqueia objetos/plugins, enquadramento, formulários externos e `unsafe-eval`. Scripts/estilos inline permanecem permitidos por compatibilidade com a interface existente. Esta CSP não substitui o escape de HTML nem deve ser apresentada como bloqueio de todo XSS. Testes existentes de escape foram preservados.
- APIs, inclusive erros de autenticação, recebem `private, no-store` e variação por origem/autorização. Não são expostos arquivos Python, configuração ou testes pela raiz estática.
- Fotos prontas reaproveitadas em um novo cadastro devem pertencer a um upload da conta autenticada. Fotos já vinculadas ao item editado permanecem permitidas. Links arbitrários não são aceitos como novo envio.
- A análise visual recria a imagem pelos pixels, remove metadados como EXIF/GPS, limita dimensões e recusa animações antes de enviar ao provedor. Utiliza o normalizador de imagens existente. A comparação pública de texto tem limite de tamanho e frequência.
- Mantidas as proteções anteriores: validação real de imagens, nomes UUID, limites de resolução/bytes, retomada por conta, acesso privado às fotos de perfil, histórico de itens e comprovantes, isolamento do chat, retenção e exportação protegida contra fórmulas.

## Desktop

O cliente exige HTTPS para enviar senha/código/token ao servidor configurado, exceto em `localhost`, `127.0.0.1` ou `::1` durante desenvolvimento. Não segue redirecionamentos de requisições e não permite desativar a verificação TLS. A conferência inclui cabeçalhos de autorização em letras minúsculas e formulários. Fotos públicas continuam separadas das requisições autenticadas. Logout tenta revogar a sessão pelo servidor; falha de rede não mantém dados abertos na interface.

## Dependências e operação

| Dependência | Versão anterior | Versão/piso desta revisão |
| --- | --- | --- |
| Flask | 3.0.3 | 3.1.3 |
| Werkzeug | 3.0.3 | 3.1.9 |
| PyJWT | 2.8.0 | 2.15.0 |
| Requests | 2.32.3 | 2.34.2, também no desktop |
| Pillow | mínimo 10 | mínimo 13, menor que 14 |
| pytest | 8.2.2 | 9.0.3 |
| Flask-Cors | 4.0.1 | removido; política explícita na aplicação |

Há também pisos para dependências já utilizadas indiretamente: cryptography 50.0.2, urllib3 2.8.0 e Jinja2 3.1.6. O conjunto instalado e verificado usa Python 3.12; Pillow 13 exige Python 3.11 ou superior. Não foi validado executável Windows.

Na retomada de 20–21/11/2026, a auditoria completa com `pip-audit --path /tmp/etec-security-runtime` avaliou **46 pacotes Python, sem pacotes ignorados e sem avisos conhecidos**. Isso inclui Requests e urllib3, que não haviam entrado no relatório automático parcial de 16/11. As versões auditadas são as utilizadas nos testes integrados. O resultado descreve o catálogo consultado nessa data e não garante ausência de falhas desconhecidas.

As migrações adicionam dados de finalidade/tentativas aos códigos e as tabelas `auth_limites`, `auth_revogacoes` e `auth_tokens_revogados`. São idempotentes, preservam contas, itens e mensagens e descartam os códigos antigos em texto. O serviço precisa das migrações antes de aceitar sessões novas. Não remover essas tabelas para contornar uma falha de acesso.

Configuração normal da mesma origem não precisa de `CORS_ORIGINS`. Se houver frontend separado, use origens completas e explícitas, sem caminho. Mantenha os segredos nas variáveis do servidor, use chave JWT aleatória e hash administrativo; não coloque a chave JWT no aplicativo desktop. Rotacionar a chave encerra tokens e invalida códigos emitidos com ela. O proxy/hospedagem deve fornecer HTTPS; a conexão PostgreSQL existente continua exigindo SSL. Configuração de certificados, backups, privilégios do banco e infraestrutura pública não foi verificada sem servidor/credenciais reais.

## Validação e limite da entrega

- **576 testes aprovados: 475 Python, 51 Chromium de regressão e 50 JavaScript.** A suíte Python completa foi executada sem seleção parcial, incluindo Flask/PostgreSQL, navegador e Tkinter/Xvfb, com os requisitos atualizados. A execução terminou com 475 aprovados e nenhuma falha. As suítes Chromium/JavaScript também terminaram sem falhas.
- O bloqueio anterior de sockets foi resolvido na retomada. **Os 140 casos antes deixados fora da seleção foram executados e aprovados**; não há exclusão permanente nem transformação de testes bloqueados em testes aprovados. A seleção temporária sem sockets não foi utilizada nesta execução completa.
- Cobertura específica: códigos com HMAC/finalidade, expiração/tentativas/reenvio, reset/login concorrentes, revogação de tokens, alteração de RM sem renovar a sessão, dados de contas distintas, falha do banco sem autorização por omissão, login administrativo, autoria das fotos, EXIF/MIME, limites HTTP, CORS e credenciais/TLS do desktop.
- O teste de CSP executa um script da própria página em uma tarefa normal do navegador. O canal privilegiado `Runtime.evaluate` pode liberar `eval` para o depurador e não serve como prova da política aplicada ao usuário. A checagem confirma o bloqueio de `eval`, o bloqueio de conexão externa e a revogação após logout. A política do site não foi afrouxada para fazer o teste passar.
- Os demais predicados Playwright foram convertidos de expressões que precisavam de `eval` para funções equivalentes. Testes unitários sem banco isolam o estado persistido de sessão, enquanto os testes PostgreSQL específicos exercitam a implementação real.
- Comandos completos: `python -m pytest -q tests`; `CHROMIUM_PATH=/usr/bin/chromium python -m unittest discover -s tests -p 'browser_*.py'`; `for t in tests/test_*.cjs; do node "$t" || exit; done`. Necessários PostgreSQL temporário (`pgserver`), Chromium/Playwright e Tkinter/Xvfb para as jornadas correspondentes. Sintaxe e diferenças Git também foram conferidas.

Os serviços externos usam respostas controladas nos testes. Não houve teste de intrusão contra hospedagem real, envio real de e-mails/push ou uso de credenciais da escola. Câmera/impressora físicas e executável Windows não foram validados. A proposta permanece em rascunho e a `main` não foi integrada. Não houve publicação em servidor nem alteração no banco da escola.
