# ETEC Achados — melhorias OCR, Fast Drop e resiliência

## Alterações
- A análise visual com Gemini agora solicita OCR de texto legível em carteirinhas, documentos, cadernos, agendas e etiquetas (`ocr_texto`, `ocr_nome_aluno`, `ocr_rm`, `ocr_serie` e confiança). A IA deve deixar campos vazios quando não conseguir ler os dados.
- O endpoint `/api/ia/analisar-imagem` tenta cruzar RM/nome com a tabela `alunos` e retorna somente um indicador/nome de possível correspondência, sem expor e-mail ao navegador.
- Ao cadastrar um item pela secretaria, se o OCR identificou um RM correspondente, o sistema grava uma mensagem interna e tenta enviar e-mail ao aluno cadastrado. A notificação é um aviso de possível correspondência, não uma confirmação de propriedade.
- No painel web, selecionar uma foto inicia automaticamente a análise, preenche nome/descrição/categoria e preserva o RM OCR no envio do cadastro.
- No desktop, selecionar fotos inicia a análise, preenche os campos quando possível e mostra mensagens de erro com etapa e código/detalhe útil; o cadastro manual continua disponível.
- Flask-Limiter foi adicionado às dependências, com limites por IP para login, análise de imagem e cadastros. Há limite global adicional, limite de tamanho de requisição e respostas JSON para HTTP 413/429/erros inesperados.
- Sanitização básica dos campos textuais do cadastro e logs técnicos no servidor.
- Corrigido um erro de sintaxe pré-existente em `desktop_secretaria.py` (`padding=` sem valor), que impedia o programa desktop de iniciar.

## Implantação
1. Instale dependências com `pip install -r requirements.txt`.
2. Configure `RATELIMIT_STORAGE_URI` com um backend compartilhado (por exemplo Redis) ao executar múltiplos workers/instâncias. O padrão `memory://` é adequado apenas para desenvolvimento/instância única.
3. Configure `GEMINI_API_KEY` (ou `GOOGLE_AI_API_KEY`) para análise por IA; sem a chave, a análise cai no modo visual local e não há OCR por modelo.
4. Configure as variáveis já usadas pelo projeto para banco de dados, autenticação, e-mail e armazenamento.
5. Faça testes em ambiente de homologação antes de produção. A notificação OCR só ocorre se o RM extraído corresponder a um registro existente em `alunos`.

## Diagnóstico
- Os logs do servidor incluem data/hora, nível, rota e stack trace para erros inesperados; não devolva stack traces ao cliente.
- Respostas de limite excedido usam HTTP 429 (`RATE_LIMITED`); payload acima do limite usa HTTP 413 (`PAYLOAD_TOO_LARGE`).
- A análise de imagem usa `VISION_ANALYSIS_FAILED` quando o serviço de visão falha.
