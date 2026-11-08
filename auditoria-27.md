# Auditoria funcional — proposta 27

Base: proposta 26 (`26-melhorias-portal`, commit remoto e91e19f50d06bb427588cc51a53dcadf13c5a711). Testes com contas fictícias e PostgreSQL temporário. Nenhum dado da escola ou serviço real de envio foi utilizado. A aprovação dos testes abaixo não significa ausência de defeitos: esta auditoria encontrou problemas fora dos cenários anteriormente cobertos.

## Cobertura executada

| Área | Verificação | Resultado e limite |
|---|---|---|
| Aluno | Login por senha correta/incorreta, sessão, catálogo, busca/detalhes, pedido, mural, chat, cadastro de objeto | Suítes existentes e jornada integrada real com PostgreSQL passaram. Cadastro e recuperação por código usam serviços simulados; entrega real de e-mail não foi validada. |
| Solicitações | Duas contas solicitando simultaneamente o mesmo objeto | Uma operação retorna 200 e outra 400: sem reserva dupla no cenário testado. |
| Privacidade | Consultas públicas, autoria, permissões administrativas, cadastros e avisos por conta | Testes passaram nos cenários cobertos. Chat por RM tem uma falha adicional de colisão descrita abaixo. |
| Professores | Acesso institucional, solicitação/aprovação/revogação, operações permitidas | Testes existentes e autoria de professor aprovado passaram. Não comprova vínculo escolar real. |
| Secretaria web | Itens, moderação, categorias, entregas, doações, mural, conversas e indicadores | Rotas reais e testes Chromium existentes passaram. Reverter entrega tem inconsistência adicional reproduzida abaixo. |
| Experiência web | Fotos/preparação/falha de envio, rascunhos, notificações, teclado e movimento reduzido | 38 testes de navegador e 40 testes JavaScript passaram. Integrações externas continuam simuladas. |
| Secretaria desktop | Janela Tkinter real em Linux com Xvfb, logo, login e sete abas, cadastro de objeto | Executado com transporte ligado ao cliente Flask real e PostgreSQL temporário; cadastro apareceu no catálogo. Sem erros de callback. O servidor de produção não foi acessado. |
| Desktop — lógica | IDs do histórico, cancelamento, erros de doação, timeout, compressão de foto e arquivo de logo | Seis novos testes automatizados. Não equivalem a validação do executável Windows. |
| Impressão e integrações | Impressora, câmera/leitor QR, Google OAuth, Cloudinary, IA e push em aparelho físico | Não executados ponta a ponta nesta auditoria. Os testes de contrato/transporte existentes não comprovam funcionamento desses serviços reais. |

Resultado: **281 testes Python, 38 testes Chromium e 40 testes JavaScript passaram**, além da sessão gráfica desktop com login, sete abas e cadastro real em banco isolado.

## Problemas confirmados e ainda abertos

| Prioridade | Problema e reprodução | Consequência / melhoria recomendada |
|---|---|---|
| Alta — A27-01 | Chat usa RM como identificador da conversa. Em PostgreSQL isolado, duas contas diferentes com RM `24001`: A envia uma mensagem; B consulta `/api/chat/mensagens/24001` com o próprio token e recebe a mensagem de A. | Possível exposição entre contas. A conversa deve ter identidade por conta/e-mail e isolamento também nas respostas administrativas; registros legados ambíguos devem ser bloqueados. Essa correção técnica não exige aguardar a lista oficial de matrículas. |
| Alta — A27-02 | Entregar objeto e chamar `PUT /api/itens/{id}/recusar`: o objeto volta a `DISPONÍVEL`, mas o registro em `entregues` continua existindo. Reproduzido com resposta 200 e contagem 1 no histórico. Web e desktop usam essa rota. | Histórico e indicadores continuam contando uma entrega revertida. Definir cancelamento auditável da entrega e atualizar estatísticas na mesma transação, preservando quem realizou a ação. |
| Média — A27-03 | `POST /api/itens/cadastrar-aluno` autenticado com `{}` retorna 200 e grava campos vazios. A validação HTML não protege outros clientes. | Validar título, descrição, categoria, data e limites no servidor; rejeitar dados incompletos antes de upload ou banco. |
| Média — A27-04 | Desktop faz HTTP e processamento de imagem na thread do Tkinter; diversas consultas capturam erro com `except: pass`. Identificado na revisão de código. | Mesmo com timeout, a janela pode ficar ocupada até a resposta. Usar tarefas em segundo plano, retorno pelo `root.after`, indicador de atividade e mensagens claras de sessão expirada/falha de atualização. |
| Média — A27-05 | Desktop exporta células de texto livre diretamente com `csv.writer`. Revisão estática; não abriu Excel. | Neutralizar fórmulas de planilha em células que começam com `=`, `+`, `-` ou `@` e testar os exportadores web/desktop. |
| Baixa — A27-06 | Categorias em destaque no dashboard desktop são ordenadas pela tupla/nome, não pela quantidade. Revisão estática. | Ordenar por quantidade para exibir as categorias com mais objetos. |

Os problemas abertos acima são descobertas desta auditoria, não foram corrigidos nem encerrados por terem sido documentados. Os testes de regressão que passaram não cobriam todos eles. As tarefas anteriormente adiadas permanecem separadas em pendencias.md.

## Corrigido nesta proposta

- Logo idêntica à web (`logo_secretaria.png`) na entrada, no cabeçalho e no ícone da janela desktop. Caminho relativo ao aplicativo, com suporte ao diretório de distribuição PyInstaller.
- Histórico desktop usa `item_id` (segunda coluna), em vez da tupla inteira ou ID do registro, ao abrir, reverter ou excluir. A exclusão agora informa que remove o objeto e seu histórico.
- Doações usam a operação coletiva do servidor e conferem HTTP e `success`; não anunciam sucesso em recusa ou timeout.
- Todas as chamadas REST desktop têm limite de conexão/leitura; download de foto também tem timeout. Isso limita espera, mas não torna a interface assíncrona.
- Fallback de IA não sobrescreve os campos manuais; OCR só é encaminhado com confiança alta. Validação real do provedor não foi realizada.
- Compressão de imagens considera a orientação EXIF; dependências desktop documentadas separadamente.

## Novas funcionalidades recomendadas

1. Levar para o desktop a fila de moderação e a gestão de acesso dos professores, hoje presentes no painel web.
2. Adicionar sair/trocar conta, aviso explícito de sessão vencida e cancelamento do polling ao encerrar a sessão.
3. Mostrar estado de sincronização e permitir tentar novamente, preservando dados digitados após falha de rede.
4. Manter histórico auditável de aprovação, entrega, reversão e exclusão, com responsável e data.
5. Oferecer os rascunhos e o acompanhamento da atividade também no desktop, com isolamento entre contas.

## Reproduzir localmente

Instalar dependências do servidor e, para os testes desktop, `pip install -r requirements-desktop.txt`. Tkinter vem do instalador do Python ou do sistema operacional. Executar pytest com `DATABASE_URL` vazio, `JWT_SECRET` exclusivo de teste e `pgserver` disponível para as integrações isoladas. Para Chromium, instalar Playwright e configurar `CHROMIUM_PATH` quando necessário.

Para abrir o desktop: `python desktop_secretaria.py`. Incluir `logo_secretaria.png` na distribuição; em PyInstaller no Windows, usar `--add-data "logo_secretaria.png;."`. Esta auditoria não gerou um novo executável Windows, não testou impressora física e não alterou a hospedagem.
