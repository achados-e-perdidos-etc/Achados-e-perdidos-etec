import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import base64
import io
import os
from PIL import Image, ImageTk
import hashlib
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DA API
# ==========================================
API_URL = "https://achados-etec-api.onrender.com"

HASH_EMAIL = "7547c4fd75b0c4cf47ee844f1c6c00f1e77b95b261edb083dfc9a08cd7cf22cd"
HASH_SENHA = "4a20e32e157a100f269d27cb60696b5b8fe17829c0305283de04fdb0094cec5c"

# ==========================================
# CLASSE PRINCIPAL DO APLICATIVO
# ==========================================
class SecretariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Painel Desktop da Secretaria")
        self.root.geometry("1100x750")
        self.root.configure(bg="#0d1117")
        
        self.itens_atuais = []
        self.categorias_atuais = []
        self.chat_timer = None
        self.rm_chat_ativo = None

        self.estilo = ttk.Style()
        self.estilo.theme_use("clam")
        self.estilo.configure("TNotebook", background="#0d1117", borderwidth=0)
        self.estilo.configure("TNotebook.Tab", background="#161b22", foreground="#c9d1d9", padding=[15, 5], font=("Arial", 10, "bold"))
        self.estilo.map("TNotebook.Tab", background=[("selected", "#dc2626")], foreground=[("selected", "white")])
        self.estilo.configure("Treeview", background="#161b22", foreground="#c9d1d9", fieldbackground="#161b22", rowheight=30)
        self.estilo.map("Treeview", background=[("selected", "#dc2626")])
        self.estilo.configure("Treeview.Heading", background="#21262d", foreground="#ffffff", font=("Arial", 10, "bold"))

        self.tela_login()

    def sha256_hash(self, texto):
        return hashlib.sha256(texto.encode('utf-8')).hexdigest()

    # --- TELA DE LOGIN ---
    def tela_login(self):
        self.frame_login = tk.Frame(self.root, bg="#0d1117")
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", width=400, height=300)

        tk.Label(self.frame_login, text="Acesso Restrito - Secretaria", font=("Arial", 16, "bold"), bg="#0d1117", fg="#f87171").pack(pady=20)

        tk.Label(self.frame_login, text="E-mail:", bg="#0d1117", fg="#c9d1d9").pack()
        self.entry_email = ttk.Entry(self.frame_login, width=30)
        self.entry_email.pack(pady=5)

        tk.Label(self.frame_login, text="Senha:", bg="#0d1117", fg="#c9d1d9").pack()
        self.entry_senha = ttk.Entry(self.frame_login, show="*", width=30)
        self.entry_senha.pack(pady=5)

        # Eventos para o botão ENTER
        self.entry_email.bind("<Return>", lambda e: self.entry_senha.focus())
        self.entry_senha.bind("<Return>", lambda e: self.verificar_login())

        btn_entrar = tk.Button(self.frame_login, text="ENTRAR", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), relief="flat", command=self.verificar_login)
        btn_entrar.pack(pady=20, fill="x", padx=50)
        
        self.entry_email.focus()

    def verificar_login(self):
        email = self.entry_email.get().strip().lower()
        senha = self.entry_senha.get().strip()

        if self.sha256_hash(email) == HASH_EMAIL and self.sha256_hash(senha) == HASH_SENHA:
            self.frame_login.destroy()
            self.construir_interface_principal()
        else:
            messagebox.showerror("Erro", "E-mail ou senha incorretos!")

    # --- INTERFACE PRINCIPAL ---
    def construir_interface_principal(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_dash = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_itens = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_categorias = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_entregues = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_doacoes = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_chat = tk.Frame(self.notebook, bg="#0d1117")

        self.notebook.add(self.tab_dash, text="Dashboard")
        self.notebook.add(self.tab_itens, text="Estoque / Gerenciar")
        self.notebook.add(self.tab_categorias, text="Categorias")
        self.notebook.add(self.tab_entregues, text="Histórico Entregues")
        self.notebook.add(self.tab_doacoes, text="Doações")
        self.notebook.add(self.tab_chat, text="Chat Alunos")

        self.construir_tab_dash()
        self.construir_tab_itens()
        self.construir_tab_categorias()
        self.construir_tab_entregues()
        self.construir_tab_doacoes()
        self.construir_tab_chat()

        self.carregar_dados()

    def carregar_dados(self):
        self.carregar_categorias()
        self.carregar_itens()
        self.carregar_entregues()
        self.carregar_dashboard()
        self.carregar_conversas()

    # --- TAB: DASHBOARD ESTATÍSTICAS ---
    def construir_tab_dash(self):
        tk.Label(self.tab_dash, text="Visão Geral do Sistema", font=("Arial", 18, "bold"), bg="#0d1117", fg="#f87171").pack(pady=20)
        
        frame_cards = tk.Frame(self.tab_dash, bg="#0d1117")
        frame_cards.pack(pady=20)

        def criar_card(parent, titulo, cor):
            f = tk.Frame(parent, bg="#161b22", bd=1, relief="solid", width=200, height=120)
            f.pack_propagate(False)
            f.pack(side="left", padx=15)
            tk.Label(f, text=titulo, font=("Arial", 10, "bold"), bg="#161b22", fg="#8b949e").pack(pady=(15,5))
            lbl_valor = tk.Label(f, text="0", font=("Arial", 28, "bold"), bg="#161b22", fg=cor)
            lbl_valor.pack()
            return lbl_valor

        self.lbl_stat_itens = criar_card(frame_cards, "TOTAL DE ITENS", "#3b82f6")
        self.lbl_stat_entregues = criar_card(frame_cards, "ITENS ENTREGUES", "#10b981")
        self.lbl_stat_doacoes = criar_card(frame_cards, "DOAÇÕES", "#f59e0b")

        tk.Button(self.tab_dash, text="Atualizar Dados", bg="#21262d", fg="white", font=("Arial", 10), relief="solid", command=self.carregar_dashboard).pack(pady=30)

    def carregar_dashboard(self):
        try:
            res = requests.get(f"{API_URL}/api/estatisticas")
            if res.status_code == 200:
                data = res.json()
                self.lbl_stat_itens.config(text=str(data.get('total_itens', 0)))
                self.lbl_stat_entregues.config(text=str(data.get('total_entregues', 0)))
                self.lbl_stat_doacoes.config(text=str(data.get('total_doacoes', 0)))
        except: pass

    # --- TAB: ESTOQUE (ITENS E BUSCA) ---
    def construir_tab_itens(self):
        frame_top = tk.Frame(self.tab_itens, bg="#0d1117")
        frame_top.pack(fill="x", pady=10, padx=10)

        tk.Button(frame_top, text="➕ CADASTRAR NOVO ITEM", bg="#059669", fg="white", font=("Arial", 10, "bold"), command=lambda: self.abrir_modal_form()).pack(side="left", padx=10)

        frame_busca = tk.Frame(frame_top, bg="#0d1117")
        frame_busca.pack(side="right", padx=10)

        tk.Label(frame_busca, text="Buscar ID:", bg="#0d1117", fg="white").pack(side="left")
        self.entry_busca = ttk.Entry(frame_busca, width=15)
        self.entry_busca.pack(side="left", padx=5)
        self.entry_busca.bind("<Return>", lambda e: self.aplicar_filtros_tabela())

        tk.Label(frame_busca, text="Status:", bg="#0d1117", fg="white").pack(side="left", padx=(10,0))
        self.combo_filtro_status = ttk.Combobox(frame_busca, values=["TODOS", "DISPONÍVEL", "SOLICITADO", "PARA DOAÇÃO"], state="readonly", width=15)
        self.combo_filtro_status.current(0)
        self.combo_filtro_status.pack(side="left", padx=5)
        self.combo_filtro_status.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros_tabela())

        tk.Button(frame_busca, text="🔍 Filtrar", bg="#1f6feb", fg="white", command=self.aplicar_filtros_tabela).pack(side="left")
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Local", "Solicitante")
        self.tree_itens = ttk.Treeview(self.tab_itens, columns=colunas, show="headings", height=15)
        for col in colunas:
            self.tree_itens.heading(col, text=col)
            self.tree_itens.column(col, anchor="center")
        
        self.tree_itens.column("ID", width=40)
        self.tree_itens.column("Nome / Descrição", width=250, anchor="w")
        self.tree_itens.column("Solicitante", width=150)
        self.tree_itens.pack(fill="both", expand=True, pady=5, padx=10)

        self.tree_itens.bind("<Double-1>", self.abrir_modal_detalhes_item)
        tk.Label(self.tab_itens, text="Dê um duplo-clique em um item da lista para Ver Fotos, Editar ou Dar Baixa.", bg="#0d1117", fg="#8b949e", font=("Arial", 9, "italic")).pack(pady=5)

    def carregar_itens(self):
        try:
            res = requests.get(f"{API_URL}/api/itens")
            if res.status_code == 200:
                self.itens_atuais = res.json()
                self.aplicar_filtros_tabela()
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível carregar os itens: {e}")

    def aplicar_filtros_tabela(self):
        termo_id = self.entry_busca.get().strip()
        status_filtro = self.combo_filtro_status.get().upper()

        self.tree_itens.delete(*self.tree_itens.get_children())
        self.tree_doacoes.delete(*self.tree_doacoes.get_children())

        for i in self.itens_atuais:
            st = (i.get('status') or 'DISPONÍVEL').upper()
            nome_val = i.get('nome') or ''
            desc_val = i.get('txt_descricao') or ''
            local_val = i.get('txt_local') or ''
            
            nome_exibicao = nome_val if nome_val else desc_val
            if not nome_exibicao: nome_exibicao = "Sem Título"
            
            if st in ['PARA DOAÇÃO', 'DOAÇÃO FEITA']:
                self.tree_doacoes.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_data', '')))

            if status_filtro != "TODOS" and st != status_filtro: continue
            if status_filtro == "TODOS" and st in ['ENTREGUE', 'DOAÇÃO FEITA']: continue 

            # Busca exata por ID
            if termo_id and str(i['id']) != termo_id: 
                continue

            solicitante = i.get('solicitado_por')
            if solicitante:
                rm_val = i.get('rm_aluno') or '-'
                solicitante_str = f"{solicitante} (RM: {rm_val})"
            else:
                solicitante_str = "-"

            self.tree_itens.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, local_val, solicitante_str))

    # ==========================================
    # MODAL DE FORMULÁRIO (CADASTRAR / EDITAR)
    # ==========================================
    def abrir_modal_form(self, item_edit=None):
        modal = tk.Toplevel(self.root)
        modal.title("Novo Item" if not item_edit else f"Editar Item #{item_edit['id']}")
        modal.geometry("500x650")
        modal.configure(bg="#161b22")
        modal.transient(self.root)
        modal.grab_set()

        titulo = "CADASTRAR NOVO OBJETO" if not item_edit else "EDITAR OBJETO"
        tk.Label(modal, text=titulo, font=("Arial", 14, "bold"), bg="#161b22", fg="#38bdf8").pack(pady=15)

        var_nome = tk.StringVar(value=item_edit.get('nome', '') if item_edit else "")
        var_desc = tk.StringVar(value=item_edit.get('txt_descricao', '') if item_edit else "")
        var_data = tk.StringVar(value=item_edit.get('txt_data', datetime.now().strftime("%d/%m/%Y")) if item_edit else datetime.now().strftime("%d/%m/%Y"))
        var_local = tk.StringVar(value=item_edit.get('txt_local', '') if item_edit else "")
        
        fotos_atuais = []
        if item_edit:
            if item_edit.get('fotos'): fotos_atuais = item_edit['fotos']
            elif item_edit.get('foto'): fotos_atuais = [item_edit['foto']]
        
        fotos_upload_base64 = fotos_atuais.copy()

        def criar_campo(label, var, widget_type="entry", values=None):
            frame = tk.Frame(modal, bg="#161b22")
            frame.pack(fill="x", padx=40, pady=5)
            tk.Label(frame, text=label, bg="#161b22", fg="#c9d1d9", font=("Arial", 9, "bold")).pack(anchor="w")
            if widget_type == "entry":
                w = ttk.Entry(frame, textvariable=var, font=("Arial", 11))
                w.pack(fill="x", pady=2)
                return w
            elif widget_type == "combo":
                w = ttk.Combobox(frame, values=values, state="readonly", font=("Arial", 10))
                if var: w.set(var)
                w.pack(fill="x", pady=2)
                return w

        criar_campo("Nome / Título Curto:", var_nome)
        criar_campo("Descrição Detalhada:", var_desc)
        cb_cat = criar_campo("Categoria:", item_edit.get('categoria', 'OUTROS') if item_edit else "OUTROS", "combo", self.categorias_atuais)
        criar_campo("Data Encontrado:", var_data)
        criar_campo("Local Encontrado:", var_local)
        cb_status = criar_campo("Status:", item_edit.get('status', 'DISPONÍVEL') if item_edit else "DISPONÍVEL", "combo", ["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO"])

        frame_fotos = tk.Frame(modal, bg="#161b22")
        frame_fotos.pack(fill="x", padx=40, pady=10)
        lbl_foto_status = tk.Label(frame_fotos, text=f"Fotos carregadas: {len(fotos_upload_base64)} (Máx 4)", bg="#161b22", fg="#94a3b8")
        lbl_foto_status.pack(side="right")

        def selecionar_fotos():
            filenames = filedialog.askopenfilenames(title="Selecione até 4 fotos", filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")])
            if filenames:
                fotos_upload_base64.clear()
                for f in filenames[:4]:
                    try:
                        with open(f, "rb") as image_file:
                            enc = base64.b64encode(image_file.read()).decode('utf-8')
                            fotos_upload_base64.append(f"data:image/jpeg;base64,{enc}")
                    except: pass
                lbl_foto_status.config(text=f"Fotos prontas para envio: {len(fotos_upload_base64)}", fg="#10b981")

        tk.Button(frame_fotos, text="📷 Selecionar Fotos do PC", bg="#4b5563", fg="white", relief="flat", command=selecionar_fotos).pack(side="left")

        def salvar():
            payload = {
                "nome": var_nome.get().strip(),
                "descricao": var_desc.get().strip(),
                "categoria": cb_cat.get(),
                "data": var_data.get().strip(),
                "local": var_local.get().strip(),
                "status": cb_status.get(),
                "fotos": fotos_upload_base64
            }
            if not payload['nome'] or not payload['descricao']:
                return messagebox.showwarning("Aviso", "Preencha título e descrição!")

            try:
                if item_edit:
                    res = requests.put(f"{API_URL}/api/itens/{item_edit['id']}", json=payload)
                else:
                    res = requests.post(f"{API_URL}/api/itens", json=payload)
                
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item salvo com sucesso!")
                    modal.destroy()
                    self.carregar_itens()
                    self.carregar_dashboard()
                else:
                    messagebox.showerror("Erro", "Erro ao salvar na nuvem.")
            except Exception as e: messagebox.showerror("Erro", str(e))

        tk.Button(modal, text="💾 GRAVAR NO BANCO NUVEM", bg="#16a34a", fg="white", font=("Arial", 11, "bold"), pady=10, relief="flat", command=salvar).pack(fill="x", padx=40, pady=20)

    # ==========================================
    # MODAL DE DETALHES NO DUPLO CLIQUE
    # ==========================================
    def abrir_modal_detalhes_item(self, event):
        selecionado = self.tree_itens.selection()
        if not selecionado: return
        item_id = self.tree_itens.item(selecionado[0])['values'][0]

        item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
        if not item: return

        modal = tk.Toplevel(self.root)
        modal.title(f"Detalhes do Item #{item['id']}")
        modal.geometry("750x650")
        modal.configure(bg="#0d1117")
        modal.transient(self.root)

        nome_titulo = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
        tk.Label(modal, text=nome_titulo, font=("Arial", 16, "bold"), bg="#0d1117", fg="#f87171").pack(pady=10)

        frame_info = tk.Frame(modal, bg="#161b22", bd=1, relief="solid")
        frame_info.pack(fill="x", padx=20, pady=5)

        info_texto = f"CATEGORIA: {item.get('categoria', '')}   |   STATUS: {item.get('status', '')}\n\n"
        info_texto += f"LOCAL: {item.get('txt_local', '')}\n"
        info_texto += f"DATA: {item.get('txt_data', '')}\n"
        info_texto += f"DESCRIÇÃO: {item.get('txt_descricao', '')}\n"
        if item.get('solicitado_por'):
            info_texto += f"\n🚨 SOLICITADO POR: {item.get('solicitado_por')} (RM: {item.get('rm_aluno', '')})"

        tk.Label(frame_info, text=info_texto, justify="left", bg="#161b22", fg="#c9d1d9", font=("Arial", 11)).pack(padx=15, pady=10, anchor="w")

        tk.Label(modal, text="Galeria de Fotos:", font=("Arial", 12, "bold"), bg="#0d1117", fg="#c9d1d9").pack(pady=5, anchor="w", padx=20)
        frame_fotos = tk.Frame(modal, bg="#0d1117")
        frame_fotos.pack(fill="both", expand=True, padx=20)

        fotos_array = []
        if item.get('fotos'): fotos_array = item['fotos']
        elif item.get('fotos_json'):
            try: fotos_array = json.loads(item['fotos_json'])
            except: pass
        if not fotos_array and item.get('foto'): fotos_array = [item['foto']]

        if not fotos_array:
            tk.Label(frame_fotos, text="Nenhuma foto registrada.", bg="#0d1117", fg="#8b949e").pack(pady=10)
        else:
            for col, foto_b64 in enumerate(fotos_array):
                try:
                    if foto_b64.startswith("data:image"): foto_b64 = foto_b64.split(",")[1]
                    img_data = base64.b64decode(foto_b64)
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail((180, 180), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)
                    lbl_img = tk.Label(frame_fotos, image=img_tk, bg="#161b22", bd=2, relief="solid")
                    lbl_img.image = img_tk
                    lbl_img.grid(row=0, column=col, padx=10, pady=5)
                except: pass

        frame_acoes = tk.Frame(modal, bg="#0d1117")
        frame_acoes.pack(fill="x", pady=15, padx=20)

        def btn(txt, cor, cmd):
            tk.Button(frame_acoes, text=txt, bg=cor, fg="white", font=("Arial", 9, "bold"), command=cmd).pack(side="left", padx=5, fill="x", expand=True)

        btn("✏️ Editar", "#eab308", lambda: [modal.destroy(), self.abrir_modal_form(item)])
        
        if item.get('status') == 'SOLICITADO':
            btn("🚫 Recusar", "#d97706", lambda: self.acao_rapida(item['id'], 'recusar', modal))
        
        if item.get('status') != 'ENTREGUE':
            btn("✅ Dar Baixa", "#059669", lambda: [modal.destroy(), self.abrir_dar_baixa(item)])
            
        if item.get('status') != 'PARA DOAÇÃO':
            btn("🎁 Marcar Doação", "#9333ea", lambda: self.acao_rapida(item['id'], 'doacao', modal))

        btn("🗑️ Excluir", "#991b1b", lambda: self.acao_rapida(item['id'], 'excluir', modal))

    # --- AÇÕES RÁPIDAS ---
    def acao_rapida(self, item_id, acao, modal=None):
        try:
            if acao == 'excluir' and messagebox.askyesno("Excluir", "Deseja excluir este item permanentemente?"):
                res = requests.delete(f"{API_URL}/api/itens/{item_id}")
            elif acao == 'recusar' and messagebox.askyesno("Recusar", "Deseja recusar a solicitação?"):
                res = requests.put(f"{API_URL}/api/itens/{item_id}/recusar")
            elif acao == 'doacao':
                res = requests.put(f"{API_URL}/api/itens/{item_id}", json={"status": "PARA DOAÇÃO"})
            else: return

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", "Operação realizada!")
                if modal: modal.destroy()
                self.carregar_itens()
                self.carregar_dashboard()
        except Exception as e: messagebox.showerror("Erro", str(e))

    # --- DAR BAIXA (ENTREGA) ---
    def abrir_dar_baixa(self, item):
        modal_baixa = tk.Toplevel(self.root)
        modal_baixa.title(f"Dar Baixa - Item #{item['id']}")
        modal_baixa.geometry("450x400")
        modal_baixa.configure(bg="#0d1117")
        modal_baixa.transient(self.root)
        modal_baixa.grab_set()

        tk.Label(modal_baixa, text="Registrar Entrega ao Dono", font=("Arial", 14, "bold"), bg="#0d1117", fg="#10b981").pack(pady=15)

        tk.Label(modal_baixa, text="Nome Completo do Aluno:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_nome = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_nome.insert(0, item.get('solicitado_por') or '')
        entry_nome.pack(padx=30, pady=(0, 10))

        tk.Label(modal_baixa, text="RM:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_rm = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_rm.insert(0, item.get('rm_aluno') or '')
        entry_rm.pack(padx=30, pady=(0, 10))

        tk.Label(modal_baixa, text="Turma / Curso:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_turma = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_turma.pack(padx=30, pady=(0, 20))

        # Eventos do Enter
        entry_nome.bind("<Return>", lambda e: entry_rm.focus())
        entry_rm.bind("<Return>", lambda e: entry_turma.focus())
        entry_turma.bind("<Return>", lambda e: confirmar())

        def confirmar():
            n, r, t = entry_nome.get().strip(), entry_rm.get().strip(), entry_turma.get().strip() or "-"
            if not n or not r: return messagebox.showwarning("Aviso", "Preencha Nome e RM", parent=modal_baixa)
            try:
                res = requests.put(f"{API_URL}/api/itens/{item['id']}", json={
                    "status": "ENTREGUE", "retirado_por": n, "rm_retirante": r, "turma_curso": t, "funcionario_responsavel": "Secretaria"
                })
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item baixado com sucesso!", parent=modal_baixa)
                    modal_baixa.destroy()
                    self.carregar_dados()
                    nome_obj = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
                    desc_obj = item.get('txt_descricao') or ''
                    local_obj = item.get('txt_local') or ''
                    self.abrir_tela_comprovante(item['id'], nome_obj, desc_obj, local_obj, n, r, t)
            except Exception as e: messagebox.showerror("Erro", str(e), parent=modal_baixa)

        tk.Button(modal_baixa, text="Confirmar e Gerar Comprovante", bg="#059669", fg="white", font=("Arial", 10, "bold"), pady=8, command=confirmar).pack(fill="x", padx=30)

    # --- TELA DO COMPROVANTE (IDÊNTICO AO MOBILE) ---
    def abrir_tela_comprovante(self, item_id, nome_item, desc_item, local_item, retirado_por, rm, turma):
        top_comp = tk.Toplevel(self.root)
        top_comp.title("Comprovante de Retirada")
        top_comp.geometry("600x650")
        top_comp.configure(bg="#e5e7eb") # Fundo cinza para destacar a "folha" branca
        top_comp.transient(self.root)
        top_comp.grab_set()

        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Container branco imitando o papel (como no Mobile)
        folha = tk.Frame(top_comp, bg="white", padx=30, pady=30, relief="flat")
        folha.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho do Comprovante
        tk.Label(folha, text="ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO", font=("Arial", 14, "bold"), bg="white", fg="black").pack()
        tk.Label(folha, text="Sistema de Achados e Perdidos - Termo de Retirada de Objeto", font=("Arial", 10, "bold"), bg="white", fg="#4b5563").pack(pady=(0, 20))

        # Seção 1: Dados do Aluno
        f_aluno = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_aluno.pack(fill="x", pady=5)
        tk.Label(f_aluno, text="DADOS DO ALUNO BENEFICIÁRIO:", font=("Arial", 9, "bold"), bg="#f3f4f6", fg="#374151", anchor="w").pack(fill="x", pady=(0, 5))
        tk.Label(f_aluno, text=f"Nome: {retirado_por}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")
        tk.Label(f_aluno, text=f"RM: {rm}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")
        tk.Label(f_aluno, text=f"Turma/Curso: {turma}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        # Seção 2: Informações do Item
        f_item = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_item.pack(fill="x", pady=5)
        tk.Label(f_item, text="INFORMAÇÕES DO ITEM DEVOLVIDO:", font=("Arial", 9, "bold"), bg="#f3f4f6", fg="#374151", anchor="w").pack(fill="x", pady=(0, 5))
        tk.Label(f_item, text=f"Item: {nome_item}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")
        tk.Label(f_item, text=f"Descrição: {desc_item}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")
        tk.Label(f_item, text=f"Local Encontrado: {local_item}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")
        tk.Label(f_item, text=f"Data da Entrega: {data_atual}", font=("Arial", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        tk.Label(folha, text="Declaro para os devidos fins que recebi o item acima descrito, conferindo suas\ncaracterísticas e estado atual de conservação nas dependências da secretaria da ETEC.", font=("Arial", 9, "italic"), bg="white", fg="#374151", justify="left").pack(anchor="w", pady=15)

        # Seção 3: Assinaturas
        f_ass = tk.Frame(folha, bg="white")
        f_ass.pack(fill="x", pady=(30, 0))
        
        box1 = tk.Frame(f_ass, bg="white")
        box1.pack(side="left", expand=True, fill="x", padx=10)
        tk.Frame(box1, bg="black", height=1).pack(fill="x", pady=(0, 5))
        tk.Label(box1, text="Assinatura do Aluno", font=("Arial", 9, "bold"), bg="white", fg="black").pack()

        box2 = tk.Frame(f_ass, bg="white")
        box2.pack(side="right", expand=True, fill="x", padx=10)
        tk.Frame(box2, bg="black", height=1).pack(fill="x", pady=(0, 5))
        tk.Label(box2, text="Funcionário Responsável (Secretaria)", font=("Arial", 9, "bold"), bg="white", fg="black").pack()

        # Botão Download HTML
        def baixar_comprovante():
            file_path = filedialog.asksaveasfilename(parent=top_comp, defaultextension=".html", initialfile=f"comprovante_{rm}.html", title="Salvar Comprovante", filetypes=[("Página Web HTML", "*.html")])
            if file_path:
                html_content = f"""
                <!DOCTYPE html>
                <html lang="pt-BR">
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: sans-serif; color: black; margin: 0; padding: 20px; }}
                        .print-area {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #ccc; border-radius: 15px; }}
                        .text-center {{ text-align: center; }}
                        .border-b {{ border-bottom: 1px solid #ccc; padding-bottom: 15px; margin-bottom: 15px; }}
                        .font-black {{ font-weight: 900; font-size: 20px; text-transform: uppercase; }}
                        .text-xs {{ font-size: 12px; }}
                        .text-gray-600 {{ color: #4b5563; }}
                        .bg-gray-100 {{ background-color: #f3f4f6; padding: 15px; border-radius: 10px; margin-bottom: 15px; }}
                        .font-bold {{ font-weight: bold; }}
                        .uppercase {{ text-transform: uppercase; }}
                        .text-gray-700 {{ color: #374151; }}
                        .italic {{ font-style: italic; }}
                        .grid {{ display: flex; justify-content: space-between; margin-top: 50px; text-align: center; font-size: 12px; }}
                        .sig-box {{ width: 45%; }}
                        .border-black {{ border-bottom: 1px solid black; margin-bottom: 5px; }}
                        @media print {{ body {{ padding: 0; }} .print-area {{ border: none; padding: 0; }} .no-print {{ display: none; }} }}
                    </style>
                </head>
                <body>
                    <div class="print-area">
                        <div class="text-center border-b">
                            <div class="font-black">ETEC Profº José Ignácio Azevedo Filho</div>
                            <div class="text-xs font-bold text-gray-600">Sistema de Achados e Perdidos - Termo de Retirada de Objeto</div>
                        </div>
                        <div class="bg-gray-100">
                            <div class="font-bold uppercase text-gray-700" style="margin-bottom: 8px;">Dados do Aluno Beneficiário:</div>
                            <div><strong>Nome:</strong> {retirado_por}</div>
                            <div><strong>RM:</strong> {rm}</div>
                            <div><strong>Turma/Curso:</strong> {turma}</div>
                        </div>
                        <div class="bg-gray-100">
                            <div class="font-bold uppercase text-gray-700" style="margin-bottom: 8px;">Informações do Item Devolvido:</div>
                            <div><strong>Item:</strong> {nome_item}</div>
                            <div><strong>Descrição:</strong> {desc_item}</div>
                            <div><strong>Local Encontrado:</strong> {local_item}</div>
                            <div><strong>Data da Entrega:</strong> {data_atual}</div>
                        </div>
                        <div class="text-xs text-gray-700 italic" style="margin-top: 15px;">
                            Declaro para os devidos fins que recebi o item acima descrito, conferindo suas características e estado atual de conservação nas dependências da secretaria da ETEC.
                        </div>
                        <div class="grid">
                            <div class="sig-box"><div class="border-black"></div><div class="font-bold">Assinatura do Aluno</div></div>
                            <div class="sig-box"><div class="border-black"></div><div class="font-bold">Funcionário Responsável (Secretaria)</div></div>
                        </div>
                        <div class="text-center no-print" style="margin-top: 40px;">
                            <button onclick="window.print()" style="padding: 10px 20px; font-size: 16px; background-color: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer;">🖨️ Imprimir / Salvar PDF</button>
                        </div>
                    </div>
                </body>
                </html>
                """
                try:
                    with open(file_path, "w", encoding="utf-8") as f: f.write(html_content)
                    messagebox.showinfo("Sucesso", f"Comprovante salvo com sucesso em:\n{file_path}", parent=top_comp)
                except Exception as e: messagebox.showerror("Erro", str(e), parent=top_comp)

        tk.Button(top_comp, text="📥 BAIXAR COMPROVANTE", command=baixar_comprovante, bg="#2563eb", fg="white", font=("Arial", 10, "bold"), relief="flat", pady=10).pack(fill="x", padx=20, pady=(0, 15))


    # --- TAB: DOAÇÕES ---
    def construir_tab_doacoes(self):
        frame_top = tk.Frame(self.tab_doacoes, bg="#0d1117")
        frame_top.pack(fill="x", pady=10, padx=10)

        tk.Label(frame_top, text="Gerenciamento de Doações", font=("Arial", 14, "bold"), bg="#0d1117", fg="#f59e0b").pack(side="left")
        
        def concluir_doacoes():
            if messagebox.askyesno("Confirmar Doação", "Deseja remover todos os itens 'PARA DOAÇÃO' e 'DOAÇÃO FEITA' do sistema definitivamente?"):
                try:
                    for child in self.tree_doacoes.get_children():
                        item_id = self.tree_doacoes.item(child)["values"][0]
                        requests.put(f"{API_URL}/api/itens/{item_id}", json={"status": "DOAÇÃO FEITA"})
                    res = requests.delete(f"{API_URL}/api/itens/doacoes/concluir")
                    if res.status_code == 200:
                        messagebox.showinfo("Sucesso", "Itens doados e removidos do sistema!")
                        self.carregar_dados()
                except Exception as e: messagebox.showerror("Erro", str(e))

        tk.Button(frame_top, text="🎁 CONCLUIR E LIMPAR DOAÇÕES EM LOTE", bg="#f59e0b", fg="#0d1117", font=("Arial", 10, "bold"), command=concluir_doacoes).pack(side="right")

        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Data Encontrado")
        self.tree_doacoes = ttk.Treeview(self.tab_doacoes, columns=colunas, show="headings", height=15)
        for col in colunas:
            self.tree_doacoes.heading(col, text=col)
            self.tree_doacoes.column(col, anchor="center")
        self.tree_doacoes.pack(fill="both", expand=True, pady=5, padx=10)

    # --- TAB: CATEGORIAS ---
    def construir_tab_categorias(self):
        frame_add = tk.Frame(self.tab_categorias, bg="#0d1117")
        frame_add.pack(pady=20)

        tk.Label(frame_add, text="Nova Categoria:", bg="#0d1117", fg="white").pack(side="left", padx=5)
        self.entry_cat = ttk.Entry(frame_add, width=30)
        self.entry_cat.pack(side="left", padx=5)
        self.entry_cat.bind("<Return>", lambda e: self.adicionar_categoria())
        tk.Button(frame_add, text="Adicionar", bg="#dc2626", fg="white", command=self.adicionar_categoria).pack(side="left", padx=5)

        self.listbox_cats = tk.Listbox(self.tab_categorias, bg="#161b22", fg="white", font=("Arial", 12), height=15)
        self.listbox_cats.pack(fill="x", padx=50, pady=10)

    def carregar_categorias(self):
        try:
            res = requests.get(f"{API_URL}/api/categorias")
            if res.status_code == 200:
                self.listbox_cats.delete(0, tk.END)
                self.categorias_atuais = []
                for c in res.json():
                    self.listbox_cats.insert(tk.END, c['nome'])
                    self.categorias_atuais.append(c['nome'])
        except: pass

    def adicionar_categoria(self):
        nome = self.entry_cat.get().strip().upper()
        if nome:
            try:
                res = requests.post(f"{API_URL}/api/categorias", json={"nome": nome})
                if res.status_code == 200:
                    self.entry_cat.delete(0, tk.END)
                    self.carregar_categorias()
            except: messagebox.showerror("Erro", "Erro ao adicionar categoria")

    # --- TAB: HISTÓRICO DE ENTREGUES ---
    def construir_tab_entregues(self):
        tk.Button(self.tab_entregues, text="🔄 Atualizar Histórico", command=self.carregar_entregues, bg="#1f6feb", fg="white").pack(pady=10, anchor="w", padx=10)
        colunas = ("Item", "Retirado Por", "RM", "Turma", "Data")
        self.tree_entregues = ttk.Treeview(self.tab_entregues, columns=colunas, show="headings", height=20)
        for col in colunas:
            self.tree_entregues.heading(col, text=col)
            self.tree_entregues.column(col, anchor="center")
        self.tree_entregues.pack(fill="both", expand=True, pady=5, padx=10)

    def carregar_entregues(self):
        try:
            res = requests.get(f"{API_URL}/api/entregues")
            if res.status_code == 200:
                self.tree_entregues.delete(*self.tree_entregues.get_children())
                for e in res.json():
                    self.tree_entregues.insert("", "end", values=(e['nome_item'], e['retirado_por'], e['rm_retirante'], e['turma_curso'], e['data_entrega']))
        except: pass

    # --- TAB: CHAT ---
    def construir_tab_chat(self):
        frame_esq = tk.Frame(self.tab_chat, bg="#0d1117", width=250)
        frame_esq.pack(side="left", fill="y", padx=10, pady=10)
        
        tk.Label(frame_esq, text="Conversas Ativas", bg="#0d1117", fg="white", font=("Arial", 12, "bold")).pack(pady=5)
        self.listbox_chat = tk.Listbox(frame_esq, bg="#161b22", fg="white", font=("Arial", 10))
        self.listbox_chat.pack(fill="both", expand=True)
        self.listbox_chat.bind("<<ListboxSelect>>", self.selecionar_conversa)

        frame_dir = tk.Frame(self.tab_chat, bg="#161b22", bd=1, relief="solid")
        frame_dir.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.lbl_chat_titulo = tk.Label(frame_dir, text="Selecione um aluno", bg="#161b22", fg="#f87171", font=("Arial", 14, "bold"))
        self.lbl_chat_titulo.pack(pady=10)

        self.txt_mensagens = tk.Text(frame_dir, bg="#0d1117", fg="white", state="disabled", wrap="word", font=("Arial", 11))
        self.txt_mensagens.pack(fill="both", expand=True, padx=10, pady=5)

        frame_input = tk.Frame(frame_dir, bg="#161b22")
        frame_input.pack(fill="x", padx=10, pady=10)

        self.entry_chat = ttk.Entry(frame_input, font=("Arial", 12))
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_chat.bind("<Return>", lambda e: self.enviar_mensagem())

        tk.Button(frame_input, text="Enviar", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), command=self.enviar_mensagem).pack(side="right")

        self.atualizar_chat_continuo()

    def carregar_conversas(self):
        try:
            res = requests.get(f"{API_URL}/api/chat/conversas")
            if res.status_code == 200:
                conversas = res.json()
                self.listbox_chat.delete(0, tk.END)
                self.mapa_conversas = []
                for c in conversas:
                    notif = f"({c['nao_lidas']} novas) " if c['nao_lidas'] > 0 else ""
                    self.listbox_chat.insert(tk.END, f"{notif}{c['nome_aluno']} - RM: {c['rm_aluno']}")
                    self.mapa_conversas.append(c['rm_aluno'])
        except: pass

    def selecionar_conversa(self, event):
        selecao = self.listbox_chat.curselection()
        if selecao:
            idx = selecao[0]
            self.rm_chat_ativo = self.mapa_conversas[idx]
            nome = self.listbox_chat.get(idx).split(" - RM:")[0].replace("( novas) ", "")
            self.lbl_chat_titulo.config(text=f"Chat: {nome}")
            self.carregar_mensagens_aluno()

    def carregar_mensagens_aluno(self):
        if not self.rm_chat_ativo: return
        try:
            res = requests.get(f"{API_URL}/api/chat/mensagens/{self.rm_chat_ativo}?marcar_lida=true&origem=SECRETARIA")
            if res.status_code == 200:
                self.txt_mensagens.config(state="normal")
                self.txt_mensagens.delete("1.0", tk.END)
                for m in res.json():
                    remetente = "Secretaria" if m['remetente'] == "SECRETARIA" else m['nome_aluno']
                    self.txt_mensagens.insert(tk.END, f"[{m['data_envio']}] {remetente}:\n{m['mensagem']}\n\n")
                self.txt_mensagens.see(tk.END)
                self.txt_mensagens.config(state="disabled")
        except: pass

    def enviar_mensagem(self):
        if not self.rm_chat_ativo: return
        texto = self.entry_chat.get().strip()
        if not texto: return
        payload = {"rm": self.rm_chat_ativo, "nome": "Secretaria", "remetente": "SECRETARIA", "mensagem": texto}
        try:
            if requests.post(f"{API_URL}/api/chat/enviar", json=payload).status_code == 200:
                self.entry_chat.delete(0, tk.END)
                self.carregar_mensagens_aluno()
        except: pass

    def atualizar_chat_continuo(self):
        self.carregar_conversas()
        if self.rm_chat_ativo: self.carregar_mensagens_aluno()
        self.chat_timer = self.root.after(3000, self.atualizar_chat_continuo)

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretariaApp(root)
    root.mainloop()
