<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ETEC - Achados e Perdidos (Alunos)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body class="dark-theme min-h-screen flex flex-col justify-between">

    <!-- CABEÇALHO -->
    <header class="bg-header border-b border-color p-4 sticky top-0 z-40 transition-colors shadow-sm">
        <div class="max-w-4xl mx-auto flex justify-between items-center gap-4">
            <div class="flex items-center space-x-3 min-w-0">
                <img id="siteLogo" src="logo.png" alt="Logo" class="w-10 h-10 min-w-[40px] min-h-[40px] shrink-0 object-cover rounded-full">
                <div class="min-w-0">
                    <h1 class="font-bold text-lg dynamic-text leading-tight truncate">ACHADOS E PERDIDOS</h1>
                    <p class="text-xs text-muted truncate">ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO</p>
                </div>
            </div>

            <div class="flex items-center space-x-3 shrink-0">
                
                <!-- MENU DE NAVEGAÇÃO ENTRE ABAS -->
                <div id="navTabs" class="flex items-center bg-header border border-color rounded-xl p-1 mr-2 hidden sm:flex">
                    <button onclick="alternarAba('catalogo')" id="tabCatalogo" class="px-4 py-1.5 rounded-lg text-xs font-bold transition-all bg-card text-main shadow-sm">Catálogo</button>
                    <button onclick="alternarAba('mural')" id="tabMural" class="px-4 py-1.5 rounded-lg text-xs font-bold transition-all text-muted hover:text-main">Mural de Perdidos</button>
                </div>

                <!-- MENU MOBILE -->
                <button onclick="alternarAba(document.getElementById('catalogScreen').classList.contains('hidden') ? 'catalogo' : 'mural')" class="sm:hidden p-2 rounded-lg bg-card border border-color text-muted hover:text-main">
                    <i class="fas fa-exchange-alt"></i>
                </button>

                <!-- SININHO DE NOTIFICAÇÕES (APARECE QUANDO IDENTIFICADO) -->
                <div class="relative">
                    <button id="btnNotificacoes" onclick="abrirModalNotificacoes()" class="hidden p-2 rounded-lg bg-card border border-color text-muted hover:text-main transition relative" title="Notificações">
                        <i class="fas fa-bell"></i>
                        <span id="badgeNotificacao" class="hidden absolute -top-1 -right-1 flex h-3 w-3">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500 border border-white"></span>
                        </span>
                    </button>
                </div>

                <!-- CONFIGURAÇÕES DE TEMA -->
                <div class="relative">
                    <button onclick="toggleConfigMenu()" class="p-2 rounded-lg bg-card border border-color text-muted hover:text-main transition" title="Configurações de Aparência">
                        <i class="fas fa-cog text-base"></i>
                    </button>

                    <div id="configMenu" class="hidden absolute right-0 mt-2 w-48 bg-card border border-color rounded-xl shadow-2xl p-3 z-50">
                        <div>
                            <span class="text-[11px] font-bold uppercase text-muted block mb-1">Modo de Exibição</span>
                            <button onclick="alternarModoEscuroClaro()" class="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-header border border-color text-xs text-main hover:opacity-80 transition">
                                <span id="themeLabel">Modo Escuro</span>
                                <i id="themeIcon" class="fas fa-moon text-yellow-400"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- DADOS DO ALUNO / BOTÃO DE IDENTIFICAR -->
                <button id="btnIdentificar" onclick="abrirModalIdentificacao()" class="text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg transition shadow-sm">
                    Identificar-se
                </button>

                <div id="userInfo" class="hidden text-right border-l border-color pl-3 ml-2">
                    <span id="userName" class="block font-bold text-sm dynamic-text max-w-[120px] truncate"></span>
                    <span id="userRM" class="text-[10px] text-muted uppercase"></span>
                    <button onclick="logout()" class="text-[10px] text-red-400 hover:text-red-500 underline block mt-0.5">Sair</button>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-4xl mx-auto w-full p-4 flex-grow">
        
        <!-- CATÁLOGO DE ITENS (ABERTO POR PADRÃO) -->
        <section id="catalogScreen" class="w-full space-y-6">
            <div class="space-y-4">
                <div class="relative w-full">
                    <i class="fas fa-search absolute left-4 top-1/2 -translate-y-1/2 text-muted text-sm"></i>
                    <input type="text" id="searchInput" oninput="filtrarPorPalavraChave()" placeholder="Buscar por palavra-chave (ex: garrafa, casaco, chave)..." class="w-full bg-card border border-color text-main text-sm rounded-xl pl-11 pr-10 py-3 focus:outline-none focus:border-red-500 transition shadow-sm placeholder:text-muted">
                    <button id="btnClearSearch" onclick="limparBusca()" class="hidden absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-main p-1">
                        <i class="fas fa-times text-xs"></i>
                    </button>
                </div>

                <div>
                    <h3 class="text-xs font-bold uppercase text-muted mb-3">FILTRAR POR CATEGORIA:</h3>
                    <div id="categoryContainer" class="relative flex flex-wrap gap-2 p-1">
                        <div id="catIndicator" class="sliding-pill absolute rounded-full z-0 opacity-0"></div>
                        <button onclick="filtrarCategoria('TODOS', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-white border border-transparent transition-colors duration-200">TODOS</button>
                        <button onclick="filtrarCategoria('MOCHILA', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-muted hover:text-main border border-color bg-card transition-colors duration-200">MOCHILA</button>
                        <button onclick="filtrarCategoria('ROUPAS', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-muted hover:text-main border border-color bg-card transition-colors duration-200">ROUPAS</button>
                        <button onclick="filtrarCategoria('ACESSÓRIOS', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-muted hover:text-main border border-color bg-card transition-colors duration-200">ACESSÓRIOS</button>
                        <button onclick="filtrarCategoria('ESCOLARES', this)" class="cat-btn relative z-10 px-4 py-2 rounded-full text-xs font-bold text-muted hover:text-main border border-color bg-card transition-colors duration-200">ESCOLARES</button>
                    </div>
                </div>

                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-color">
                    <h3 class="text-xs font-bold uppercase text-muted">STATUS DO OBJETO:</h3>
                    <select id="statusFilter" onchange="filtrarStatus(this.value)" class="bg-card border border-color text-main text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-red-500 transition cursor-pointer">
                        <option value="TODOS">TODOS OS STATUS</option>
                        <option value="DISPONÍVEL">DISPONÍVEL</option>
                        <option value="SOLICITADO">SOLICITADO</option>
                        <option value="ENTREGUE">ENTREGUE</option>
                        <option value="PARA DOAÇÃO">PARA DOAÇÃO</option>
                        <option value="DOAÇÃO FEITA">DOAÇÃO FEITA</option>
                    </select>
                </div>
            </div>

            <div id="itemsGrid" class="grid grid-cols-1 md:grid-cols-2 gap-4"></div>
        </section>

        <!-- TELA DO MURAL DE PERDIDOS (PROCURO ALGO) -->
        <section id="muralScreen" class="hidden w-full space-y-6">
            <div class="bg-card border border-color rounded-2xl p-6 mb-6">
                <div class="flex items-center gap-4 mb-4">
                    <div class="w-12 h-12 bg-amber-500/20 text-amber-500 rounded-full flex items-center justify-center text-xl shrink-0">
                        <i class="fas fa-bullhorn"></i>
                    </div>
                    <div>
                        <h2 class="text-xl font-bold text-main">Mural de Perdidos</h2>
                        <p class="text-sm text-muted">Perdeu alguma coisa? Poste um aviso aqui. Se a secretaria encontrar, nós te avisamos na hora!</p>
                    </div>
                </div>

                <form onsubmit="publicarAvisoMural(event)" class="space-y-4 pt-4 border-t border-color">
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div class="sm:col-span-2">
                            <label class="block text-xs font-bold text-muted mb-1 ml-1">O QUE VOCÊ PERDEU?</label>
                            <input type="text" id="avisoDescricao" required placeholder="Ex: Garrafa térmica azul com adesivo..." class="w-full bg-header border border-color text-main text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-amber-500">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-muted mb-1 ml-1">CATEGORIA</label>
                            <select id="avisoCategoria" class="w-full bg-header border border-color text-main text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-amber-500">
                                <option value="MOCHILA">MOCHILA</option>
                                <option value="ROUPAS">ROUPAS</option>
                                <option value="ACESSÓRIOS">ACESSÓRIOS</option>
                                <option value="ESCOLARES">ESCOLARES</option>
                                <option value="OUTROS">OUTROS</option>
                            </select>
                        </div>
                    </div>
                    <button type="submit" id="btnPublicarAviso" class="w-full sm:w-auto bg-amber-600 hover:bg-amber-700 text-white font-bold py-3 px-6 rounded-xl text-sm uppercase transition flex items-center justify-center gap-2">
                        <span id="btnPublicarText">Publicar no Mural</span>
                        <i id="btnPublicarSpinner" class="fas fa-spinner fa-spin hidden"></i>
                    </button>
                </form>
            </div>

            <h3 class="text-xs font-bold uppercase text-muted border-b border-color pb-2">Últimos avisos de alunos:</h3>
            <div id="muralGrid" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Injetado pelo JS -->
            </div>
        </section>

        <!-- TELA DE DETALHES -->
        <section id="detailScreen" class="hidden w-full max-w-lg mx-auto bg-card border border-color rounded-2xl p-6 shadow-lg">
            <button onclick="voltarParaCatalogo()" class="text-xs text-muted hover:text-main mb-4"><i class="fas fa-arrow-left"></i> Voltar ao catálogo</button>

            <div class="flex justify-between items-center mb-2">
                <h2 class="text-xs font-bold dynamic-text uppercase">INFORMAÇÕES DO ITEM</h2>
                <span id="detailStatusBadge" class="text-[10px] font-bold px-2 py-0.5 rounded uppercase border"></span>
            </div>

            <div class="relative bg-black/20 rounded-xl overflow-hidden mb-4 border border-color h-64">
                <div id="photoCounter" class="hidden absolute top-3 right-3 z-20 bg-black/70 backdrop-blur-md text-white text-[11px] font-bold px-2.5 py-1 rounded-full border border-white/20">
                    <span id="photoCurrentIdx">1</span>/<span id="photoTotalCount">1</span>
                </div>

                <div id="carouselContainer" class="flex h-full w-full overflow-x-auto snap-x snap-mandatory scrollbar-none scroll-smooth"></div>

                <button id="btnPrevPhoto" onclick="navegarFotos(-1)" class="hidden absolute left-2 top-1/2 -translate-y-1/2 z-20 bg-black/50 text-white w-8 h-8 rounded-full flex items-center justify-center hover:bg-black/80 transition">
                    <i class="fas fa-chevron-left text-xs"></i>
                </button>
                <button id="btnNextPhoto" onclick="navegarFotos(1)" class="hidden absolute right-2 top-1/2 -translate-y-1/2 z-20 bg-black/50 text-white w-8 h-8 rounded-full flex items-center justify-center hover:bg-black/80 transition">
                    <i class="fas fa-chevron-right text-xs"></i>
                </button>

                <div id="detailPlaceholder" class="hidden h-full text-center p-6 text-muted flex flex-col items-center justify-center">
                    <i class="fas fa-box-open text-5xl mb-2"></i>
                    <p class="text-xs">Foto mantida no registro da secretaria</p>
                </div>
            </div>

            <div class="space-y-3">
                <h3 id="detailTitle" class="text-2xl font-black text-main"></h3>
                <p id="detailDescription" class="text-sm text-muted bg-header p-3 rounded-lg border border-color"></p>

                <div class="flex justify-between items-center text-xs text-muted pt-2 border-t border-color">
                    <span>Local: <strong id="detailLocal" class="text-main"></strong></span>
                    <span>Data: <strong id="detailDate" class="text-main"></strong></span>
                </div>

                <div class="pt-4">
                    <button id="btnSolicitar" onclick="processarBotaoSolicitar()" class="w-full dynamic-btn font-bold py-3.5 rounded-xl text-sm uppercase transition">
                        ESTE É O MEU ITEM / SOLICITAR COLETA
                    </button>
                </div>
            </div>
        </section>

    </main>

    <!-- ========================================== -->
    <!-- MODAIS DE INTERFACE -->
    <!-- ========================================== -->

    <!-- Modal de Identificação (Pede Nome e RM) -->
    <div id="modalIdentificacao" class="hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-card border border-color rounded-2xl p-6 w-full max-w-sm shadow-2xl transform scale-95 transition-transform duration-300" id="modalIdentificacaoContent">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-black text-main"><i class="fas fa-id-card mr-2 text-amber-500"></i>Identificação</h3>
                <button onclick="fecharModalIdentificacao()" class="text-muted hover:text-main"><i class="fas fa-times"></i></button>
            </div>
            
            <p class="text-sm text-muted mb-5">Para garantir que os itens voltem para o dono certo ou para receber notificações do Mural, informe seus dados.</p>
            
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-muted mb-1 ml-1">NOME COMPLETO</label>
                    <input type="text" id="inputIdNome" class="w-full bg-header border border-color text-main text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-amber-500 transition shadow-sm" placeholder="Ex: Maria Oliveira">
                </div>
                <div>
                    <label class="block text-xs font-bold text-muted mb-1 ml-1">RM (NÚMERO DE MATRÍCULA)</label>
                    <input type="number" id="inputIdRm" class="w-full bg-header border border-color text-main text-sm rounded-xl px-4 py-3 focus:outline-none focus:border-amber-500 transition shadow-sm" placeholder="Ex: 12345">
                </div>
            </div>
            
            <div id="modalIdError" class="hidden text-red-500 text-xs font-bold mt-3 text-center bg-red-500/10 py-2 rounded-lg border border-red-500/20"></div>
            
            <div class="mt-6">
                <button id="btnConfirmarId" onclick="confirmarIdentificacao()" class="w-full bg-amber-600 hover:bg-amber-700 text-white py-3 rounded-xl font-bold text-sm flex justify-center items-center transition">
                    <span id="btnConfirmarIdText">Salvar e Continuar</span>
                    <i id="btnConfirmarIdSpinner" class="fas fa-spinner fa-spin hidden"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- Modal de Solicitar Coleta (Confirmação) -->
    <div id="modalSolicitar" class="hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-card border border-color rounded-2xl p-6 w-full max-w-sm shadow-2xl transform scale-95 transition-transform duration-300" id="modalSolicitarContent">
            <h3 class="text-xl font-black text-main text-center mb-2"><i class="fas fa-hand-paper text-red-500 mb-2 block text-3xl"></i>Confirmar Retirada</h3>
            <p class="text-sm text-muted text-center mb-6">O item será reservado em nome de <strong id="resumoSolicitanteNome" class="text-main"></strong> (RM <strong id="resumoSolicitanteRm" class="text-main"></strong>).</p>
            
            <div class="flex gap-3 mt-6">
                <button onclick="fecharModalSolicitar()" class="flex-1 py-3 rounded-xl font-bold text-sm bg-header border border-color text-muted hover:text-main transition">Cancelar</button>
                <button id="btnConfirmarSolicitacao" onclick="confirmarSolicitacao()" class="flex-1 dynamic-btn py-3 rounded-xl font-bold text-sm flex justify-center items-center">
                    <span id="btnConfirmarText">Confirmar</span>
                    <i id="btnConfirmarSpinner" class="fas fa-spinner fa-spin hidden ml-2"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- Modal de Notificações -->
    <div id="modalNotificacoes" class="hidden fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-card border border-color rounded-2xl w-full max-w-md shadow-2xl overflow-hidden transform scale-95 transition-transform duration-300 flex flex-col max-h-[80vh]" id="modalNotificacoesContent">
            <div class="p-4 border-b border-color flex justify-between items-center bg-header">
                <h3 class="text-base font-bold text-main"><i class="fas fa-bell text-amber-500 mr-2"></i>Suas Notificações</h3>
                <button onclick="fecharModalNotificacoes()" class="text-muted hover:text-main"><i class="fas fa-times"></i></button>
            </div>
            <div id="listaNotificacoes" class="p-4 overflow-y-auto flex-grow space-y-3">
                <!-- Injetado por JS -->
            </div>
        </div>
    </div>

    <!-- Modal de Match Inteligente (Mural) -->
    <div id="modalMatch" class="hidden fixed inset-0 z-[120] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-card border border-amber-500/50 rounded-2xl p-6 w-full max-w-lg shadow-[0_0_40px_rgba(245,158,11,0.2)] transform scale-95 transition-transform duration-300" id="modalMatchContent">
            <div class="text-center mb-6">
                <i class="fas fa-magic text-5xl text-amber-500 mb-3 animate-bounce"></i>
                <h3 class="text-2xl font-black text-main">Pera aí! 🛑</h3>
                <p class="text-sm text-muted mt-2">Encontramos no estoque da secretaria itens muito parecidos com o que você acabou de postar!</p>
            </div>
            
            <div id="matchItemsContainer" class="space-y-3 max-h-60 overflow-y-auto mb-6 pr-2 scrollbar-none">
                <!-- Injetado por JS -->
            </div>
            
            <div class="flex gap-3">
                <button onclick="fecharModalMatch()" class="flex-1 py-3 rounded-xl font-bold text-sm bg-header border border-color text-muted hover:text-main transition">Nenhum é o meu</button>
                <button onclick="irParaCatalogoAposMatch()" class="flex-1 bg-amber-600 hover:bg-amber-700 text-white py-3 rounded-xl font-bold text-sm">Ir para Catálogo</button>
            </div>
        </div>
    </div>

    <!-- Modal de Aviso Global (Sucesso/Erro) -->
    <div id="modalAviso" class="hidden fixed inset-0 z-[130] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 opacity-0 transition-opacity duration-300">
        <div class="bg-card border border-color rounded-2xl p-6 w-full max-w-sm shadow-2xl text-center transform scale-95 transition-transform duration-300" id="modalAvisoContent">
            <div id="modalAvisoIcon" class="text-5xl mb-4"></div>
            <h3 id="modalAvisoTitulo" class="text-xl font-black text-main mb-2"></h3>
            <p id="modalAvisoMensagem" class="text-sm text-muted mb-6"></p>
            <button onclick="fecharModalAviso()" class="w-full dynamic-btn py-3 rounded-xl font-bold text-sm uppercase">Entendi</button>
        </div>
    </div>

    <script src="script.js"></script>
</body>
</html>
