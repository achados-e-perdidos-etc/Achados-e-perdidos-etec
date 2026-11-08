# Impressão dos comprovantes de entrega

Atualização na branch `28-atualizacoes-do-projeto`, proposta #29 com base em `main`.

O modelo visual foi ampliado em [paridade-secretaria.md](paridade-secretaria.md): logo, cores vermelha/grafite, ilustrações de objetos e campos reorganizados no mesmo modelo da web/desktop. O exemplo atual está em `/workspace/comprovantes-evidencias/comprovante-personalizado.pdf`. Os resultados de testes abaixo descrevem a etapa original da impressão.

- **Secretaria web:** botão Imprimir no comprovante da baixa manual; Comprovante / Imprimir no histórico de entregas e após a confirmação por código. Ver aceite continua disponível e abre o comprovante completo.
- **Folha de impressão:** A4, fundo branco, dados do objeto/aluno, data registrada e responsável. O comprovante do histórico inclui o aceite quando existir; sem assinatura, informa essa ausência. Registros revertidos recebem identificação explícita. Menu, chat, painel e botões ficam fora da impressão. Imprimir/cancelar não registra outra entrega nem altera o banco.
- **Impressora ou PDF:** o botão web abre a janela de impressão do navegador. Ali o atendente escolhe uma impressora instalada, as opções de papel ou Salvar como PDF.
- **Aplicativo desktop:** botão Imprimir comprovante no termo e Comprovante / Imprimir no histórico. Abre um documento local no navegador padrão; nele, Imprimir comprovante abre a escolha da impressora/PDF. Usa a data histórica e o aceite persistido quando a ação vem do histórico. O HTML escapa os valores e não carrega recursos externos. Arquivos temporários ficam em pasta privada e são removidos ao sair/trocar a conta ou fechar o aplicativo. Falha em abrir o navegador é apresentada como erro, sem anunciar impressão concluída.
- **Privacidade:** os dados e a imagem do aceite são buscados com a sessão da equipe autorizada, sem URL contendo token e com resposta `no-store`. Imagens em memória são liberadas quando a janela é fechada. O comprovante continua disponível à equipe após exclusão do objeto, com a situação de reversão preservada.

Validação: testes com Flask/PostgreSQL/Chromium, emulação de mídia de impressão, PDF A4 de uma página, conteúdo do recibo e restauração do painel após impressão. Verificados autenticação, ausência de assinatura no JSON, reversão/exclusão, HTML escapado e falha do navegador. O fluxo Tkinter em Linux/Xvfb acionou o botão, conferiu o documento temporário e sua remoção ao sair. A abertura do navegador desktop foi simulada para não iniciar uma impressão durante os testes.

Resultado cumulativo: **378 testes Python, 49 JavaScript e 48 Chromium aprovados — 475 testes**. A suíte Python inclui onze jornadas Flask/PostgreSQL/Chromium e o fluxo gráfico Tkinter. Exemplo fictício de impressão em `/workspace/comprovantes-evidencias/comprovante-exemplo.pdf`.

Não foi utilizado um equipamento de impressão físico nem validado um executável Windows. A impressão depende do navegador e das impressoras disponíveis no computador do atendente. Não houve implantação ou alteração no banco da escola.
