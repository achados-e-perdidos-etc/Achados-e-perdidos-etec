# 🔍 Achados e Perdidos — ETEC Profº José Ignácio

Sistema de achados e perdidos para facilitar a reencontrar seu itens perdidos pela escola.

Descrição do repositório
------------------------
Sistema de achados e perdidos para facilitar a reencontrar seu itens perdidos pela escola.

Linguagens no repositório
-------------------------
- Python: 50.9%
- JavaScript: 26.8%
- HTML: 20.3%
- CSS: 2.0%

Resumo
------
Este projeto é uma solução escolar para registrar, buscar e gerenciar objetos perdidos encontrados na ETEC Profº José Ignácio. Inclui uma interface web para alunos consultarem itens, uma API em Python (Flask) e um app desktop utilizado pela secretaria para registrar objetos.

Funcionalidades
---------------
- Cadastro de itens encontrados (descrição, categoria, local, data e foto)
- Consulta pública para alunos
- Solicitação de retirada com nome e RM do aluno
- Painel da secretaria (edição, exclusão e gerenciamento de status)
- Status dos itens: Disponível, Solicitado, Entregue

Tecnologias (observadas no repositório)
--------------------------------------
- Front-end: HTML, CSS, JavaScript
- Back-end: Python (Flask)
- Banco de dados: PostgreSQL (ex.: Neon)
- App desktop: Python (Tkinter)

Estrutura do projeto (visão geral)
---------------------------------
- index.html              — Interface web para os alunos
- script.js               — Lógica do front-end
- style.css               — Estilos
- server.py               — API REST (Flask)
- desktop_secretaria.py   — App desktop da secretaria (Tkinter)
- requirements.txt        — Dependências Python
- logo.png                — Logo da escola

Como executar localmente
------------------------
Pré-requisitos:
- Python 3.8+
- PostgreSQL (ou outra base compatível)

1) Clone o repositório
```bash
git clone https://github.com/achados-e-perdidos-etc/Achados-e-perdidos-etec.git
cd Achados-e-perdidos-etec
```

2) Crie e ative um ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.\.venv\Scripts\activate   # Windows (PowerShell/CMD)
```

3) Instale dependências
```bash
pip install -r requirements.txt
```

4) Configure variáveis de ambiente (exemplo)
```bash
export DATABASE_URL="sua_url_de_conexao"
export FLASK_APP=server.py
export FLASK_ENV=development
```

5) Rode migrações e inicie o servidor (se houver suporte)
```bash
python manage.py migrate   # se o projeto usar Django ou script equivalente
python server.py           # ou flask run
```

6) Acesse em http://localhost:5000

App desktop (secretaria)
------------------------
Execute:
```bash
python desktop_secretaria.py
```

Endpoints (exemplos)
--------------------
As rotas reais dependem da implementação; abaixo estão rotas comuns esperadas:

- GET  /api/itens         — listar itens
- POST /api/itens         — cadastrar novo item
- GET  /api/itens/:id     — ver detalhes
- PUT  /api/itens/:id     — atualizar item
- DELETE /api/itens/:id   — remover item
- POST /api/solicitar     — solicitar retirada de item

Exemplo de payload (JSON)
```json
{
  "title": "Carteira preta",
  "description": "Carteira de couro com documentos e cartões",
  "category": "documentos",
  "location": "Cantina",
  "found_date": "2026-09-01",
  "contact": "email@exemplo.com"
}
```

Contribuição
------------
Contribuições são bem-vindas:
1. Fork do projeto
2. Crie uma branch: `git checkout -b feat/minha-melhoria`
3. Faça as alterações e testes
4. Abra um Pull Request descrevendo a mudança

Licença
-------
Este projeto foi desenvolvido para fins educacionais na ETEC Profº José Ignácio. Adicione um arquivo LICENSE com a licença desejada (por exemplo MIT) se desejar permitir contribuições externas com termos claros.

Contato
-------
- Mantenedor: (adicione nome)
- Email: (adicione email para contato)

Notas finais
-----------
Posso ajustar este README para incluir badges, instruções de CI/CD, exemplos reais de endpoints extraídos do código, screenshots ou tradução para inglês. Deseja que eu adicione algum desses elementos agora?