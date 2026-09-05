# 🔍 Sistema de Achados e Perdidos — ETEC Profº José Ignácio

Plataforma integrada (Web + Desktop) desenvolvida para modernizar, automatizar e organizar a gestão de objetos perdidos e encontrados no ambiente escolar.

---

## 📋 Sobre o Projeto

Com o alto fluxo de alunos, a perda de pertences é comum e o gerenciamento manual desses itens pode ser ineficiente. Este sistema centraliza todo o fluxo de achados e perdidos: a secretaria cadastra e etiqueta os itens através de um aplicativo Desktop dedicado, enquanto os alunos consultam o catálogo, recebem notificações inteligentes e solicitam retiradas através de um portal Web responsivo.

---

## ✨ Principais Funcionalidades

### 💻 Portal do Aluno (Web)
- **Catálogo Digital:** Visualização limpa e paginada de todos os itens disponíveis, com filtros avançados por categoria, status e período (ex: Últimos 7 dias).
- **Mural Inteligente ("Perdi Algo"):** Alunos cadastram o que perderam e o algoritmo de *Matching* avisa instantaneamente se há um item correspondente no acervo. Caso o item seja encontrado posteriormente, o aluno recebe uma notificação na plataforma.
- **Solicitação Segura:** Para reivindicar um item, o sistema exige uma "Prova de Propriedade" (um detalhe que apenas o dono saberia), garantindo segurança na devolução.
- **Chat em Tempo Real:** Comunicação direta com a secretaria para tirar dúvidas sobre objetos sem precisar se deslocar.
- **Modo Anúncios:** Interface de carrossel em tela cheia com transições suaves, ideal para exibição automática em painéis ou totens na escola.

### 🏢 Painel da Secretaria (App Desktop)
- **Gestão de Estoque:** Cadastro, edição e exclusão de itens e categorias dinâmicas de forma rápida.
- **Gerador de Etiquetas:** Criação automática de etiquetas de identificação com ID e informações do item prontas para impressão térmica ou convencional.
- **Dashboard Gerencial:** Painel analítico com gráficos e estatísticas gerais (taxa de devolução, volume de doações e categorias com maior índice de perdas).
- **Central de Atendimento:** Painel multi-conversas para responder às dúvidas dos alunos enviadas pelo chat da Web.
- **Controle de Status e Doações:** Fluxo completo para dar baixa em itens entregues aos donos e limpeza automática de itens encaminhados para doação.

---

## 🛠️ Tecnologias Utilizadas

O ecossistema do projeto foi construído utilizando uma arquitetura distribuída via API RESTful:

- **Front-end Web:** HTML5, CSS3, Vanilla JavaScript e Tailwind CSS (para estilização ágil e responsiva).
- **Back-end / API:** Python modularizado utilizando o microframework Flask.
- **App Desktop:** Desenvolvido nativamente em Python utilizando a biblioteca Tkinter.
- **Banco de Dados:** Banco de dados relacional em nuvem com rotinas de higienização automática (arquitetura restrita e proprietária).

---

## 🔒 Segurança e Arquitetura

Este projeto foi projetado com foco em usabilidade e segurança da informação:
- A interface administrativa é isolada em um aplicativo Desktop compilado, evitando exposição de rotas administrativas na Web.
- Os dados sensíveis dos alunos (RM e Nome) trafegam de forma encapsulada no momento da solicitação de devolução.
- O código-fonte de conexão estrutural, provisionamento de banco de dados e implantação são confidenciais para proteger a integridade do sistema da escola.

---

> Desenvolvido com 💙 para a comunidade da ETEC Profº José Ignácio Azevedo Filho.
