# Secretaria web e desktop: recursos equivalentes

Branch `28-atualizacoes-do-projeto`, proposta #29 com base em `main`. Comparação dos dois **painéis administrativos da secretaria**, preservando papéis de aluno, professor autorizado e titular. O portal do aluno mantém seus próprios recursos e permissões.

## Matriz da comparação

| Recurso administrativo | Web | Desktop |
|---|---|---|
| Login da titular e conta pessoal de professor autorizado; mostrar senha e sair/trocar conta | Sim | Sim |
| Revogação de professor conferida pelo servidor; concessão de acesso somente pela titular | Sim | Sim |
| Cadastrar, editar, excluir objeto e atualizar estoque | Sim | Sim |
| Buscar por nome/descrição/ID sem acentos, categoria, local, período e situação | Sim | Sim |
| Abrir diretamente por ID ou texto da etiqueta de leitor USB | Sim | Sim |
| Fotos de arquivo, câmera, adicionar/remover e visualizar/ampliar | Sim | Sim |
| Upload por foto, progresso confirmado, retomada e tentativa independente | Sim | Sim |
| Análise visual, sugestões e conferência manual de dados incertos; campos manuais preservados | Sim | Sim |
| Rascunho de texto de novo objeto por até 24 horas na sessão, sem guardar fotos no rascunho | Sim | Sim |
| Aprovação, motivo de recusa e lista de cadastros devolvidos para correção | Sim | Sim |
| Aviso de duplicidade e confirmação da revisão antes de publicar | Sim | Sim |
| Histórico do objeto com responsável, datas, campos alterados e consulta por ID | Sim | Sim |
| Criar e excluir categorias preservando objetos antigos | Sim | Sim |
| Indicadores, disponíveis/solicitados, categorias e locais com gráficos | Sim | Sim |
| Mural e sugestões de objetos semelhantes, com comparação e preparação de entrega | Sim | Sim |
| Chat, busca por aluno/RM, avisos de não lidas e histórico legado somente de leitura | Sim | Sim |
| Retenção automática de mensagens em 30 dias | Servidor comum | Servidor comum |
| Baixa manual, reversão identificada e histórico de entregas | Sim | Sim |
| Retirada por código, conferência presencial e assinatura desenhada/aceite digitado | Sim | Sim |
| Comprovante, aceite registrado, impressão/PDF e identificação de entrega revertida | Sim | Sim |
| Etiqueta individual em PNG e impressão/PDF | Sim | Sim |
| Etiquetas em lote com todas as páginas; PNG de página escolhida | Sim | Sim |
| Leitura de etiqueta QR por câmera ou imagem | Sim | Sim |
| Relatórios de inventário, entregas, doações e catálogo completo, em PDF/impressão e CSV | Sim | Sim |
| Filtros dos relatórios e opção de incluir entregas revertidas | Sim | Sim |
| Separar e concluir doações preservando registros | Sim | Sim |

“Sim” indica implementação e disponibilidade na interface; não significa validação de todo hardware ou de um executável Windows. As diferenças de apresentação seguem a plataforma: impressão/PDF do desktop abre um documento local no navegador padrão; gráficos nativos usam barras com rolagem; câmera depende das permissões do equipamento. Instalação PWA e mecanismos do navegador continuam próprios da versão web. A secretaria continua exigindo conexão para operar o banco; rascunho não equivale a cadastro enviado.

## Ajustes realizados

- Novos `desktop_ferramentas.py`, `desktop_formulario.py`, `desktop_uploads.py` e `desktop_camera.py` mantêm HTTP, decodificação, câmera e gravação em workers; atualizações Tk permanecem na thread principal. Câmera, uploads e rascunhos são encerrados/limpos ao sair. Controles `ttk.Button` também são protegidos durante operações. O novo formulário preserva o texto ao fechar e só limpa o rascunho após sucesso.
- Upload nativo usa as mesmas sessões por conta e partes de 64 KB da web. Uma resposta perdida é reconciliada consultando os bytes recebidos. Fotos prontas são reaproveitadas; falha de uma não interrompe as demais. Os limites/expiração do servidor continuam valendo.
- `blueprints/ferramentas.py` e `utils/ferramentas.py` geram os mesmos documentos e etiquetas para as duas interfaces. Dados de relatórios incluem os mesmos campos. Não se inventa um “código de autenticidade”; os relatórios apresentam registros consultados no sistema. CSV continua neutralizando fórmulas em ambas as interfaces.
- O mural web passou a usar o mesmo `/api/smart-match` utilizado no desktop. Sugestões não confirmam dono nem entregam automaticamente.
- Leitura QR aceita somente ID numérico ou `ETEC-ITEM-ID`, sem extrair números de uma URL/texto arbitrário. A câmera é ativada por ação explícita, liberada ao fechar e tem alternativa por arquivo. Nenhum resultado de OCR modifica matrícula ou identifica o dono.
- Etiquetas em lote deixaram de ficar limitadas aos primeiros 15 objetos: HTML/PDF inclui todas as páginas e a folha PNG pode ser escolhida por número. QR é gerado localmente no servidor, sem serviço externo de QR.
- Foco/teclado dos diálogos nativos web são coordenados com os modais existentes, inclusive quando a etiqueta é aberta nos detalhes de um objeto.

## Comprovante personalizado

O modelo compartilhado da web e do desktop tem logo da secretaria, cabeçalho grafite, detalhes vermelhos, ilustrações vetoriais discretas de mochila/garrafa/fone, destaque do objeto, campos organizados e bloco do aceite. As cores são solicitadas também na impressão; uma impressora configurada em preto e branco continua determinando a saída física. Dados e assinatura permanecem legíveis sobre fundo branco. A logo embutida é reduzida e reutilizada em memória, sem serviço externo. O comprovante de teste ficou em uma página A4.

A confirmação manual agora retorna o ID do comprovante persistido; a web abre o registro efetivamente salvo, em vez de montar o documento somente com o relógio do navegador. A auditoria e os comprovantes antigos continuam preservados. O documento de entrega revertida permanece claramente identificado.

## Dependências e instalação

Servidor: `requirements.txt` inclui `qrcode[pil]`. Desktop: instalar `requirements-desktop.txt`, que acrescenta `opencv-python-headless` para captura/decodificação QR. Tkinter continua vindo do Python/sistema operacional. A imagem da logo e `comprovantes.css` devem acompanhar a distribuição, assim como os módulos novos; a instalação por código-fonte usa a pasta do projeto. `ETEC_API_URL` aponta o aplicativo para o servidor escolhido.

## Validação

**396 testes Python, 49 JavaScript e 48 Chromium de regressão — 493 aprovados nesta etapa.** A suíte Python inclui quinze jornadas Flask/PostgreSQL/Chromium e um fluxo gráfico Tkinter em Linux/Xvfb. A câmera web foi testada com um stream sintético; a leitura de QR usou PNG real gerado pelo servidor e o decodificador OpenCV. O fluxo nativo exercitou filtros, rascunho, foto enviada, categoria, relatório comum, código e aceite, além de moderação, professores, login pessoal e revogação. A validação posterior de temas, preferências e atalhos está em [preferencias-e-atalhos.md](preferencias-e-atalhos.md), com 501 casos cumulativos aprovados.

Também foram verificados documento privado/HTML escapado, tipos de relatório, etiquetas em duas páginas, PNG, câmera liberada, progresso independente e foto com resposta perdida após commit, retomada sem reenviar a foto pronta. Suítes anteriores cobrem retirada concorrente, idempotência, privacidade, retenção e fila offline do aluno.

Não houve publicação em servidor ou alteração no banco da escola. Não foram usados câmera ou impressora físicas nem validado um executável Windows. Armazenamento externo de fotos e abertura do navegador desktop foram simulados nos testes. Evidências fictícias em `/workspace/paridade-evidencias` e `/workspace/comprovantes-evidencias/comprovante-personalizado.pdf`.
