# 🔍 Achados e Perdidos — ETEC Profº José Ignácio

Sistema web para registro e busca de objetos perdidos na escola, com painel exclusivo para a secretaria e interface de consulta para os alunos.

---

## 📋 Sobre o Projeto

Muitos alunos perdem pertences no ambiente escolar e têm dificuldade em encontrá-los. Este sistema centraliza o cadastro de objetos encontrados, permitindo que a secretaria registre os itens e que os alunos busquem e solicitem a retirada diretamente pelo site — de forma rápida e organizada.

---

## ✨ Funcionalidades

- 📦 **Cadastro de itens** pela secretaria (descrição, categoria, local, data e foto)
- 🔎 **Consulta pública** para alunos buscarem objetos perdidos
- 📩 **Solicitação de retirada** com nome e RM do aluno
- ✏️ **Edição e exclusão** de itens pelo painel da secretaria
- 🔒 **Login restrito** para acesso ao painel administrativo
- 📊 Status dos itens: `Disponível`, `Solicitado` e `Entregue`

---

## 🗂️ Estrutura do Projeto

```
📁 Achados-e-perdidos-etec/
├── index.html              # Interface web para os alunos
├── script.js               # Lógica do front-end
├── style.css               # Estilização da página
├── server.py               # API REST com Flask
├── desktop_secretaria.py   # App desktop da secretaria (Tkinter)
├── requirements.txt        # Dependências Python
└── logo.png                # Logo da escola
```

---

## 🔌 Endpoints da API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/itens` | Lista todos os itens cadastrados |
| `POST` | `/api/itens` | Cadastra um novo item |
| `PUT` | `/api/itens/<id>` | Atualiza dados de um item |
| `DELETE` | `/api/itens/<id>` | Remove um item |
| `POST` | `/api/solicitar` | Aluno solicita retirada de um item |

---

## 👥 Como Usar

### Alunos
1. Acesse o site
2. Pesquise seu objeto pela descrição ou categoria
3. Clique em **"Solicitar retirada"** e informe seu nome e RM
4. Compareça à secretaria para retirar o item

---

## 📄 Licença

Este projeto foi desenvolvido para fins educacionais na ETEC Profº José Ignácio.

---

> Desenvolvido com 💙 por alunos da ETEC Profº José Ignácio
