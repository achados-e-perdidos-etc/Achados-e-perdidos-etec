# Catálogo, moderação e experiência do portal

Atualização cumulativa da branch `28-atualizacoes-do-projeto`, proposta #29 com base em `main`. Preserva os fluxos de segurança, retirada, upload retomável, fila offline, retenção do chat e jogo 404 já implementados. As alterações continuam nesta branch por orientação do proprietário.

## Revisão de interface e usabilidade

| Problema observado | Ajuste |
|---|---|
| Navegação principal escondida no menu | Barra visível com Objetos encontrados, Perdi algo e Minha atividade. No celular fica na parte inferior, com espaço reservado e indicação da seção atual. A opção de relato respeita o perfil de professor. |
| Pouco contexto sobre análise e retirada | Orientações de três etapas, indicação de publicação pela secretaria, instruções por situação do objeto e texto de confirmação sobre conferência presencial. A interface não promete entrega automática nem comprovação de propriedade por código. |
| Apresentação carregada e leitura irregular | Hierarquia de títulos, espaçamento e contrastes consistentes, cartões com data/local e chamada Ver objeto, textos de ajuda e hero compacto no celular. Preservadas as cores e logos existentes. |
| Login mencionava somente alunos | Identidade visual do projeto, indicação de contas institucionais de aluno/professor, títulos para cadastro/recuperação, mostrar/ocultar senha, códigos com preenchimento assistido e aviso sobre computador compartilhado. Erros permanecem junto ao formulário, além do aviso temporário. |
| Filtros ocultos dificultavam compreender resultados | Cada filtro aplicado aparece com opção de remover. Botão para limpar todos, busca com rótulo e exemplo, estado de carregamento e vazio com ações para ajustar busca ou relatar perda. Contagem corresponde aos objetos carregados, sem alegar o total do banco. |
| Atualização podia anunciar sucesso após falha | Confirmação de atualização depende da resposta bem-sucedida do catálogo. Falhas conservam os dados mostrados e apresentam nova tentativa; consulta tem limite de espera de 15 segundos. |
| Avisos fechados cobriam a página | Correção da precedência CSS de `.central-avisos.hidden`. O carregamento também é encerrado ao abrir o catálogo offline. |
| Foco e controles pouco claros | Ícones decorativos fora do nome acessível, estado expandido dos filtros, foco em detalhes e retorno ao cartão, texto maior nos campos e controles de toque. Preferência por redução de movimento respeitada inclusive no carregamento inicial. |
| Menu da secretaria podia abrir ao trocar de seção por atalho | A troca de seção somente fecha um menu que esteja aberto. Moderação recebe instruções para revisão e correção, com controles e espaçamento consistentes. |

A permissão de notificações é solicitada pela ação do usuário no perfil. A central de avisos continua funcionando sem permissão push. O selo genérico “Oficial” e o ponto verde junto da logo foram retirados; não representavam uma verificação de disponibilidade ou de afiliação.

## Melhorias funcionais da etapa anterior, concluídas nesta atualização

- Catálogo público paginado: 24 objetos por solicitação, limite máximo de 48. Cursor por ID e âncora evitam repetição por novas inserções; fotos dos cartões são solicitadas quando entram na tela. Miniaturas Cloudinary têm dimensões limitadas. Cache público local limitado a 96 objetos e aviso sobre resultados incompletos/desatualizados sem rede.
- Busca normalizada sem acentos, combinando categoria, situação, local e intervalo da data encontrada. Datas legadas inválidas não interrompem a consulta. Filtros são parâmetros SQL e caracteres especiais de LIKE são tratados como texto.
- Recusa preserva cadastro, fotos, autoria e histórico; secretaria informa motivo. Somente o autor pode corrigir o mesmo objeto e reenviar para análise. Versão da linha e bloqueio transacional impedem decisões baseadas em um cadastro que já mudou. Correções exigem rede e não entram na fila como novos objetos.
- Histórico da equipe acessível nos detalhes web/desktop e na moderação: conta, perfil, data e alterações de título, descrição, categoria, local, data encontrada, fotos, situação, aprovação e motivo. Mudanças completas são registradas a partir desta migração; eventos antigos são preservados sem inventar dados ausentes.
- Possível duplicidade conferida antes de publicar: título normalizado, categoria e data com até sete dias de diferença; comparação local de termos/texto, sem contratar IA. Exibe até cinco sugestões entre até 200 candidatos. Trata-se de um aviso, não garantia de unicidade: a equipe pode confirmar que conferiu, e essa decisão fica auditada. Não há fusão ou exclusão automática.
- Desktop Tkinter inclui moderação e gestão de professores. A gestão de acessos aparece somente para a titular; professores autorizados entram com sua conta individual e continuam sujeitos à revogação no servidor. HTTP e imagens permanecem nos workers. `ETEC_API_URL` permite definir a origem da API no ambiente do aplicativo.

## Banco e atualização

`SCHEMA_CATALOGO` é executado após os esquemas existentes por `server.init_db()` e `database.init_db()`. Acrescenta versão e metadados de recusa, funções de normalização/data, índices do catálogo e a ampliação da auditoria. Não exige extensões PostgreSQL adicionais. Inicialização repetida foi exercitada em banco temporário.

Portal e painel web compartilham os novos recursos locais; o service worker utiliza um novo nome de cache e inclui CSS/JS da experiência, catálogo e moderação. Tailwind permanece compilado localmente. Não foram adicionadas dependências de runtime nesta etapa.

## Validação e limites

**470 testes aprovados: 373 Python, 49 JavaScript e 48 Chromium de regressão.** A suíte Python inclui nove jornadas com Flask, PostgreSQL e Chromium reais, além de um fluxo gráfico do desktop Tkinter em Linux/Xvfb. As nove jornadas web foram repetidas após os ajustes finais de foco, filtros e abertura offline. A revisão de acessibilidade dos menus foi coberta novamente pelas telas de regressão.

Foram exercitados paginação, busca combinada, fotos fora da tela sem solicitação, descarte de resposta antiga, falha sem falso sucesso, recusa/correção/aprovação no mesmo ID, isolamento por conta, conflito de versão/decisões concorrentes, avisos de duplicidade e auditoria. O desktop executou login, moderação, correção pelo aluno, aprovação, histórico, concessão de acesso e login pessoal do professor; a revogação foi recusada pelo servidor. Larguras de 320, 390, 768 e 1366 px foram verificadas sem rolagem horizontal no catálogo. Redução de movimento foi utilizada nos fluxos web.

Capturas locais de computador, celular, login, histórico e desktop estão em `/workspace/experiencia-evidencias`. Os registros são de testes com objetos e contas fictícios.

Não houve implantação ou acesso ao banco da escola. Armazenamento de fotos, visão e entrega push reais continuam dependentes das credenciais/provedores; os testes utilizam respostas controladas. O desktop foi exercitado em Linux, sem gerar ou validar um executável Windows. Os testes cobrem os cenários executados e não garantem ausência absoluta de defeitos.
