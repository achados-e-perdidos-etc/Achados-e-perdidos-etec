# Testar o site pelo GitHub Codespaces

Este ambiente executa o site e um PostgreSQL de demonstração dentro do Codespace. Não usa o banco da escola. A configuração não acrescenta funcionalidades ao produto.

## Abrir pela primeira vez

1. Abra o repositório no GitHub e selecione a branch `28-atualizacoes-do-projeto`.
2. Toque em **Code → Codespaces → Create codespace on 28-atualizacoes-do-projeto**. No celular, a opção de visualizar o GitHub como site para computador pode facilitar.
3. Aguarde a criação dos contêineres e a instalação das dependências.
4. No editor que abrir, entre em **Ports / Portas**, localize **5000** e toque em **Open in Browser / Abrir no navegador**. Mantenha a visibilidade **Private / Privada**.
5. Abra o terminal do Codespace e execute:

```sh
python .devcontainer/ambiente.py contas
```

O terminal mostra os e-mails e a senha aleatória das contas de demonstração. Entre como aluno no endereço principal e como secretaria em `/secretaria`. Há também outro aluno e um professor para testar isolamento das conversas e solicitação/aprovação de acesso. Existem dois objetos fictícios para começar; você pode cadastrar outros sem foto.

Se já tinha criado um Codespace antes desta configuração, selecione a branch correta e execute **Codespaces: Rebuild Container** na paleta de comandos do editor. Alterações nos arquivos precisam estar salvas antes da reconstrução.

## Se o site não iniciar automaticamente

No terminal, execute:

```sh
python .devcontainer/ambiente.py iniciar
```

Confira os detalhes em `.devcontainer/.env.codespaces.log` se houver erro. A preparação pode ser repetida sem duplicar contas e objetos iniciais. Ela preserva as senhas de alunos já existentes; se você alterar uma senha durante o teste, use a senha que escolheu para essa conta.

## O que pode testar

Login, catálogo, filtros, temas, buscas salvas, cadastro sem foto, aprovação, solicitação/retirada, chat, histórico, comprovantes/PDF e gestão de professores. Use o [roteiro de teste com colegas](teste-com-colegas.md) para orientar as tarefas; uma porta privada exige autenticação e acesso ao Codespace.

Upload de fotos usa Cloudinary; códigos por e-mail usam o provedor de e-mail; notificações push e análise com provedor externo usam suas próprias configurações. Para exercitar essas integrações de verdade, configure as variáveis necessárias como **Codespaces secrets** do repositório e reinicie o Codespace. Os nomes estão em `config.py`. Não coloque chaves em arquivos versionados nem no chat. A base de demonstração continua fixa mesmo se existir um secret chamado `DATABASE_URL`.

## Dados, variáveis e limite gratuito

O volume `banco-testes` mantém os dados enquanto o armazenamento do Codespace existir. Parar o Codespace não equivale a apagar os dados; excluir o Codespace e seu armazenamento pode apagá-los. Este ambiente não importa nem faz backup do banco antigo.

Os acessos gerados ficam somente em `.devcontainer/.env.codespaces.json`, ignorado pelo Git. O servidor continua exigindo SSL no banco por padrão. Apenas este ambiente configura `DATABASE_SSLMODE=disable`, pois o banco está na rede interna do Docker, sem porta de banco publicada.

Codespaces tem franquia de computação e armazenamento conforme a conta; não é hospedagem permanente ou gratuita ilimitada. Confira o saldo em **GitHub Settings → Billing / Usage → Codespaces**, prefira a máquina menor e pare o Codespace ao terminar. O link funciona enquanto o ambiente estiver ligado. O aplicativo desktop nativo precisa de uma sessão gráfica própria; este ambiente abre o portal e o painel web.

Configuração conferida com validação do Compose e JSON e testes locais de preparo com PostgreSQL. A criação real do Codespace na sua conta ainda precisa ser feita pelos passos acima.
