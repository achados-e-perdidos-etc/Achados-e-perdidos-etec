import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import base64
import io
import os
import csv
from PIL import Image, ImageTk, ImageDraw, ImageFont
from datetime import datetime
import qrcode

# ==========================================
# CONFIGURAÇÕES DA API E JWT
# ==========================================
API_URL = "https://etec-achados.up.railway.app"
TOKEN_SECRETARIA = None

# Paleta de Cores Visual Moderna
COR_BG_GERAL = "#0d1117"
COR_BG_CARD = "#161b22"
COR_BG_HEADER = "#21262d"
COR_TEXTO_PRINCIPAL = "#c9d1d9"
COR_DESTAQUE = "#dc2626"      # Vermelho ETEC
COR_VERDE = "#10b981"
COR_AZUL = "#1f6feb"
COR_BORDA = "#30363d"

class SecretariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Painel da Secretaria")
        self.root.geometry("1150x780")
        self.root.configure(bg=COR_BG_GERAL)
        
        self.itens_atuais = []
        self.categorias_atuais = []
        self.chat_timer = None
        self.rm_chat_ativo = None

        # Estilização Moderna para o Tkinter/TTK
        self.estilo = ttk.Style()
        self.estilo.theme_use("clam")
        
        # Notebook (Abas) com visual moderno e espaçado
        self.estilo.configure("TNotebook", background=COR_BG_GERAL, borderwidth=0)
        self.estilo.configure("TNotebook.Tab", background=COR_BG_HEADER, foreground=COR_TEXTO_PRINCIPAL, padding=[16, 8], font=("Segoe UI", 10, "bold"), relief="flat")
        self.estilo.map("TNotebook.Tab", background=[("selected", COR_DESTAQUE)], foreground=[("selected", "white")])
        
        # Tabelas (Treeview) refinadas e limpas
        self.estilo.configure("Treeview", background=COR_BG_CARD, foreground=COR_TEXTO_PRINCIPAL, fieldbackground=COR_BG_CARD, borderwidth=0, rowheight=34, font=("Segoe UI", 10))
        self.estilo.map("Treeview", background=[("selected", COR_DESTAQUE)], foreground=[("selected", "white")])
        self.estilo.configure("Treeview.Heading", background=COR_BG_HEADER, foreground="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat")

        self.tela_login()

    def get_auth_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN_SECRETARIA}"
        }

    def get_auth_headers_get(self):
        return {
            "Authorization": f"Bearer {TOKEN_SECRETARIA}"
        }

    # ==========================================
    # TELA DE LOGIN REFORMULADA (MODERNA)
    # ==========================================
    def tela_login(self):
        self.frame_login = tk.Frame(self.root, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", width=440, height=380)

        # Ícone ou Cabeçalho Visual do Card
        tk.Label(self.frame_login, text="🔐", font=("Segoe UI", 24), bg=COR_BG_CARD).pack(pady=(25, 0))
        tk.Label(self.frame_login, text="Acesso Restrito - Secretaria", font=("Segoe UI", 16, "bold"), bg=COR_BG_CARD, fg=COR_DESTAQUE).pack(pady=(5, 2))
        tk.Label(self.frame_login, text="Painel Administrativo Seguro", font=("Segoe UI", 9, "italic"), bg=COR_BG_CARD, fg=COR_VERDE).pack(pady=(0, 20))

        # Campos de Entrada com Padding e Cores Harmonizadas
        frame_inputs = tk.Frame(self.frame_login, bg=COR_BG_CARD)
        frame_inputs.pack(fill="x", padx=40)

        tk.Label(frame_inputs, text="E-mail Institucional:", font=("Segoe UI", 9, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL).pack(anchor="w", pady=(0, 2))
        self.entry_email = tk.Entry(frame_inputs, font=("Segoe UI", 11), bg=COR_BG_GERAL, fg="white", insertbackground="white", relief="flat", highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE, highlightthickness=1)
        self.entry_email.pack(fill="x", pady=(0, 12), ipady=6)

        tk.Label(frame_inputs, text="Senha de Acesso:", font=("Segoe UI", 9, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL).pack(anchor="w", pady=(0, 2))
        self.entry_senha = tk.Entry(frame_inputs, font=("Segoe UI", 11), show="*", bg=COR_BG_GERAL, fg="white", insertbackground="white", relief="flat", highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE, highlightthickness=1)
        self.entry_senha.pack(fill="x", pady=(0, 20), ipady=6)

        self.entry_email.bind("<Return>", lambda e: self.entry_senha.focus())
        self.entry_senha.bind("<Return>", lambda e: self.verificar_login())

        self.btn_entrar = tk.Button(self.frame_login, text="ENTRAR NO SISTEMA", font=("Segoe UI", 10, "bold"), bg=COR_DESTAQUE, fg="white", activebackground="#b91c1c", activeforeground="white", relief="flat", cursor="hand2", command=self.verificar_login)
        self.btn_entrar.pack(fill="x", padx=40, ipady=10)
        
        self.entry_email.focus()

    def verificar_login(self):
        global TOKEN_SECRETARIA
        email = self.entry_email.get().strip().lower()
        senha = self.entry_senha.get().strip()

        if not email or not senha:
            return messagebox.showerror("Erro", "Preencha o e-mail e a senha!")

        self.btn_entrar.config(text="CONECTANDO...", state="disabled")
        self.root.update()

        try:
            res = requests.post(f"{API_URL}/api/login", json={"email": email, "senha": senha})
            data = res.json()

            if res.status_code == 200 and data.get("success"):
                TOKEN_SECRETARIA = data.get("token")
                self.frame_login.destroy()
                self.construir_interface_principal()
            else:
                messagebox.showerror("Acesso Negado", data.get("message", "E-mail ou senha incorretos!"))
                self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível falar com o servidor:\n{e}")
            self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")

    def construir_interface_principal(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_dash = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_itens = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_categorias = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_entregues = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_doacoes = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_chat = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_mural = tk.Frame(self.notebook, bg=COR_BG_GERAL)

        self.notebook.add(self.tab_dash, text="📊 Dashboard")
        self.notebook.add(self.tab_itens, text="📦 Estoque / Gerenciar")
        self.notebook.add(self.tab_categorias, text="🏷️ Categorias")
        self.notebook.add(self.tab_entregues, text="📋 Histórico Entregues")
        self.notebook.add(self.tab_doacoes, text="🎁 Doações")
        self.notebook.add(self.tab_chat, text="💬 Chat Alunos")
        self.notebook.add(self.tab_mural, text="📢 Mural de Relatos")

        self.construir_tab_dash()
        self.construir_tab_itens()
        self.construir_tab_categorias()
        self.construir_tab_entregues()
        self.construir_tab_doacoes()
        self.construir_tab_chat()
        self.construir_tab_mural()

        self.carregar_dados()

    def carregar_dados(self):
        self.carregar_categorias()
        self.carregar_itens()
        self.carregar_entregues()
        self.carregar_dashboard()
        self.carregar_conversas()
        self.carregar_mural()
        
    # --- DASHBOARD E RELATÓRIOS ---
    def construir_tab_dash(self):
        tk.Label(self.tab_dash, text="Visão Geral do Sistema", font=("Segoe UI", 18, "bold"), bg=COR_BG_GERAL, fg="#f87171").pack(pady=25)
        
        frame_cards = tk.Frame(self.tab_dash, bg=COR_BG_GERAL)
        frame_cards.pack(pady=10)
        
        def criar_card(parent, titulo, cor):
            f = tk.Frame(parent, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1, width=220, height=130)
            f.pack_propagate(False)
            f.pack(side="left", padx=15)
            tk.Label(f, text=titulo, font=("Segoe UI", 10, "bold"), bg=COR_BG_CARD, fg="#8b949e").pack(pady=(20, 5))
            lbl_valor = tk.Label(f, text="0", font=("Segoe UI", 28, "bold"), bg=COR_BG_CARD, fg=cor)
            lbl_valor.pack()
            return lbl_valor

        self.lbl_stat_itens = criar_card(frame_cards, "TOTAL DE ITENS", "#3b82f6")
        self.lbl_stat_entregues = criar_card(frame_cards, "ITENS ENTREGUES", COR_VERDE)
        self.lbl_stat_doacoes = criar_card(frame_cards, "DOAÇÕES", "#f59e0b")

        frame_botoes = tk.Frame(self.tab_dash, bg=COR_BG_GERAL)
        frame_botoes.pack(pady=40)
        
        tk.Button(frame_botoes, text="🔄 Atualizar Dados", bg=COR_BG_HEADER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", command=self.carregar_dashboard).pack(side="left", padx=10)
        tk.Button(frame_botoes, text="📊 Exportar Relatório (CSV)", bg=COR_VERDE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", command=self.exportar_relatorio).pack(side="left", padx=10)

    def carregar_dashboard(self):
        try:
            res = requests.get(f"{API_URL}/api/estatisticas", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                data = res.json()
                self.lbl_stat_itens.config(text=str(data.get('total_itens', 0)))
                self.lbl_stat_entregues.config(text=str(data.get('total_entregues', 0)))
                self.lbl_stat_doacoes.config(text=str(data.get('total_doacoes', 0)))
        except: pass

    def exportar_relatorio(self):
        if not TOKEN_SECRETARIA: return
        nome_sugerido = f"relatorio_achados_etec_{datetime.now().strftime('%Y%m')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile=nome_sugerido, title="Salvar Relatório", filetypes=[("Arquivo CSV", "*.csv")]
        )
        if not file_path: return
        try:
            res_itens = requests.get(f"{API_URL}/api/itens", headers=self.get_auth_headers_get())
            if res_itens.status_code != 200: return messagebox.showerror("Erro", "Erro ao conectar ao servidor.")
            itens = res_itens.json()
            with open(file_path, mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
                escritor = csv.writer(arquivo_csv, delimiter=';')
                escritor.writerow(['ID', 'Nome do Item', 'Descrição', 'Categoria', 'Data Encontrado', 'Local', 'Status', 'Solicitante / Retirado Por', 'RM Aluno'])
                for i in itens:
                    escritor.writerow([
                        i.get('id', ''), i.get('nome') or i.get('txt_descricao') or '', i.get('txt_descricao', ''),
                        i.get('categoria', ''), i.get('txt_data', ''), i.get('txt_local', ''),
                        i.get('status', 'DISPONÍVEL').upper(), i.get('solicitado_por') or '', i.get('rm_aluno') or ''
                    ])
            messagebox.showinfo("Sucesso", f"Planilha salva em:\n{file_path}")
        except Exception as e: messagebox.showerror("Erro", str(e))

    # --- ABA: MURAL DE RELATOS ---
    def construir_tab_mural(self):
        frame_top = tk.Frame(self.tab_mural, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        
        tk.Button(frame_top, text="🔄 Atualizar Mural", command=self.carregar_mural, bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(frame_top, text="🗑️ Excluir Relato", command=self.excluir_mural, bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")
        
        colunas = ("ID", "Aluno", "RM", "Categoria", "Descrição", "Data")
        self.tree_mural = ttk.Treeview(self.tab_mural, columns=colunas, show="headings", height=20)
        for col in colunas: self.tree_mural.heading(col, text=col); self.tree_mural.column(col, anchor="center")
        self.tree_mural.column("Descrição", width=420, anchor="w")
        self.tree_mural.pack(fill="both", expand=True, pady=5, padx=12)
        
    def carregar_mural(self):
        try:
            res = requests.get(f"{API_URL}/api/mural", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.tree_mural.delete(*self.tree_mural.get_children())
                for m in res.json():
                    self.tree_mural.insert("", "end", values=(m['id'], m['nome_aluno'], m['rm_aluno'], m['categoria'], m['descricao'], m['data_registro']))
        except: pass
        
    def excluir_mural(self):
        selecionado = self.tree_mural.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um relato para excluir.")
        item_id = self.tree_mural.item(selecionado[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"Deseja apagar definitivamente o relato #{item_id}?"):
            try:
                res = requests.delete(f"{API_URL}/api/mural/{item_id}", headers=self.get_auth_headers())
                if res.status_code == 200: self.carregar_mural()
            except: pass

    # --- ESTOQUE ---
    def construir_tab_itens(self):
        frame_top = tk.Frame(self.tab_itens, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)

        tk.Button(frame_top, text="➕ CADASTRAR NOVO ITEM", bg="#059669", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=lambda: self.abrir_modal_form()).pack(side="left")

        frame_busca = tk.Frame(frame_top, bg=COR_BG_GERAL)
        frame_busca.pack(side="right")

        tk.Label(frame_busca, text="Buscar ID:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9)).pack(side="left")
        self.entry_busca = ttk.Entry(frame_busca, width=12)
        self.entry_busca.pack(side="left", padx=6)
        self.entry_busca.bind("<Return>", lambda e: self.buscar_por_id_direto())

        tk.Label(frame_busca, text="Status:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9)).pack(side="left", padx=(10,0))
        self.combo_filtro_status = ttk.Combobox(frame_busca, values=["TODOS", "DISPONÍVEL", "SOLICITADO", "PARA DOAÇÃO"], state="readonly", width=14)
        self.combo_filtro_status.current(0)
        self.combo_filtro_status.pack(side="left", padx=6)
        self.combo_filtro_status.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros_tabela())

        tk.Button(frame_busca, text="🔍 Buscar", bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2", command=self.buscar_por_id_direto).pack(side="left", padx=(6,0))
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Local", "Solicitante")
        self.tree_itens = ttk.Treeview(self.tab_itens, columns=colunas, show="headings", height=18)
        for col in colunas:
            self.tree_itens.heading(col, text=col)
            self.tree_itens.column(col, anchor="center")
        
        self.tree_itens.column("ID", width=50)
        self.tree_itens.column("Nome / Descrição", width=280, anchor="w")
        self.tree_itens.column("Solicitante", width=160)
        self.tree_itens.pack(fill="both", expand=True, pady=5, padx=12)

        self.tree_itens.bind("<Double-1>", self.abrir_modal_detalhes_item)
        tk.Label(self.tab_itens, text="💡 Dica: Dê um duplo-clique em um item da lista para visualizar fotos, editar os dados ou dar baixa.", bg=COR_BG_GERAL, fg="#8b949e", font=("Segoe UI", 9, "italic")).pack(pady=6)

    def carregar_itens(self):
        try:
            res = requests.get(f"{API_URL}/api/itens", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.itens_atuais = res.json()
                self.aplicar_filtros_tabela()
        except Exception as e: messagebox.showerror("Erro de Conexão", f"Não foi possível carregar os itens: {e}")

    def buscar_por_id_direto(self):
        id_buscado = self.entry_busca.get().strip()
        if not id_buscado: return self.aplicar_filtros_tabela()
        if not id_buscado.isdigit(): return messagebox.showwarning("Aviso", "Apenas números no campo de ID.")
        item = next((i for i in self.itens_atuais if str(i['id']) == id_buscado), None)
        if item:
            self.entry_busca.delete(0, tk.END)
            self.aplicar_filtros_tabela()
            self.abrir_modal_detalhes_item(item_direto=item)
        else: messagebox.showinfo("Não encontrado", f"ID #{id_buscado} não localizado.")

    def aplicar_filtros_tabela(self):
        status_filtro = self.combo_filtro_status.get().upper()
        self.tree_itens.delete(*self.tree_itens.get_children())
        self.tree_doacoes.delete(*self.tree_doacoes.get_children())

        for i in self.itens_atuais:
            st = (i.get('status') or 'DISPONÍVEL').upper()
            nome_exibicao = i.get('nome') or i.get('txt_descricao') or "Sem Título"
            
            if st in ['PARA DOAÇÃO', 'DOAÇÃO FEITA']:
                self.tree_doacoes.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_data', '')))

            if status_filtro != "TODOS" and st != status_filtro: continue
            if status_filtro == "TODOS" and st in ['ENTREGUE', 'DOAÇÃO FEITA']: continue 
            solicitante = i.get('solicitado_por')
            solicitante_str = f"{solicitante} (RM: {i.get('rm_aluno', '-')})" if solicitante else "-"
            self.tree_itens.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_local', ''), solicitante_str))

    # --- MODAL CADASTRO / EDIÇÃO ---
    def abrir_modal_form(self, item_edit=None):
        modal = tk.Toplevel(self.root)
        modal.title("Novo Item" if not item_edit else f"Editar Item #{item_edit['id']}")
        modal.geometry("520x680")
        modal.configure(bg=COR_BG_CARD)
        modal.transient(self.root)
        modal.grab_set()

        # TÍTULO CORRIGIDO: Vermelho ETEC para edição ou Azul para cadastro novo
        cor_titulo = COR_DESTAQUE if item_edit else "#38bdf8"
        tk.Label(modal, text="CADASTRAR NOVO OBJETO" if not item_edit else "EDITAR OBJETO", font=("Segoe UI", 15, "bold"), bg=COR_BG_CARD, fg=cor_titulo).pack(pady=20)

        var_nome = tk.StringVar(value=item_edit.get('nome', '') if item_edit else "")
        var_desc = tk.StringVar(value=item_edit.get('txt_descricao', '') if item_edit else "")
        var_data = tk.StringVar(value=item_edit.get('txt_data', datetime.now().strftime("%d/%m/%Y")) if item_edit else datetime.now().strftime("%d/%m/%Y"))
        var_local = tk.StringVar(value=item_edit.get('txt_local', '') if item_edit else "")
        
        fotos_atuais = item_edit['fotos'] if item_edit and item_edit.get('fotos') else ([item_edit['foto']] if item_edit and item_edit.get('foto') else [])
        fotos_upload_base64 = fotos_atuais.copy()

        def criar_campo(label, var, widget_type="entry", values=None):
            frame = tk.Frame(modal, bg=COR_BG_CARD)
            frame.pack(fill="x", padx=40, pady=6)
            tk.Label(frame, text=label, bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            if widget_type == "entry":
                w = ttk.Entry(frame, textvariable=var, font=("Segoe UI", 11))
                w.pack(fill="x", pady=3)
                return w
            else:
                w = ttk.Combobox(frame, values=values, state="readonly", font=("Segoe UI", 10))
                if var: w.set(var)
                w.pack(fill="x", pady=3)
                return w

        criar_campo("Nome / Título Curto:", var_nome)
        criar_campo("Descrição Detalhada:", var_desc)
        cb_cat = criar_campo("Categoria:", item_edit.get('categoria', 'OUTROS') if item_edit else "OUTROS", "combo", self.categorias_atuais)
        criar_campo("Data Encontrado:", var_data)
        criar_campo("Local Encontrado:", var_local)
        cb_status = criar_campo("Status:", item_edit.get('status', 'DISPONÍVEL') if item_edit else "DISPONÍVEL", "combo", ["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO"])

        frame_fotos = tk.Frame(modal, bg=COR_BG_CARD)
        frame_fotos.pack(fill="x", padx=40, pady=10)
        lbl_foto_status = tk.Label(frame_fotos, text=f"Fotos carregadas: {len(fotos_upload_base64)} (Máx 4)", bg=COR_BG_CARD, fg="#94a3b8", font=("Segoe UI", 9))
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
                lbl_foto_status.config(text=f"Fotos prontas: {len(fotos_upload_base64)}", fg=COR_VERDE)

        tk.Button(frame_fotos, text="📷 Selecionar Fotos", bg="#374151", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2", command=selecionar_fotos).pack(side="left")

        def salvar():
            payload = {
                "nome": var_nome.get().strip(), "descricao": var_desc.get().strip(),
                "categoria": cb_cat.get(), "data": var_data.get().strip(),
                "local": var_local.get().strip(), "status": cb_status.get(), "fotos": fotos_upload_base64
            }
            if not payload['nome'] or not payload['descricao']: return messagebox.showwarning("Aviso", "Preencha título e descrição!")
            try:
                if item_edit:
                    res = requests.put(f"{API_URL}/api/itens/{item_edit['id']}", json=payload, headers=self.get_auth_headers())
                else:
                    res = requests.post(f"{API_URL}/api/itens", json=payload, headers=self.get_auth_headers())

                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item salvo na nuvem com segurança!")
                    modal.destroy()
                    self.carregar_itens()
                    self.carregar_dashboard()
                else: messagebox.showerror("Erro", "Acesso Negado ou erro no servidor.")
            except Exception as e: messagebox.showerror("Erro", str(e))

        tk.Button(modal, text="💾 GRAVAR NO BANCO NUVEM", bg=COR_VERDE, fg="white", font=("Segoe UI", 11, "bold"), pady=12, relief="flat", cursor="hand2", command=salvar).pack(fill="x", padx=40, pady=25)

    # --- MODAL DETALHES DO ITEM ---
    def abrir_modal_detalhes_item(self, event=None, item_direto=None):
        if item_direto: item = item_direto
        else:
            selecionado = self.tree_itens.selection()
            if not selecionado: return
            item_id = self.tree_itens.item(selecionado[0])['values'][0]
            item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
            
        if not item: return

        modal = tk.Toplevel(self.root)
        modal.title(f"Detalhes do Item #{item['id']}")
        modal.geometry("780x680")
        modal.configure(bg=COR_BG_GERAL)
        modal.transient(self.root)

        nome_titulo = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
        tk.Label(modal, text=nome_titulo, font=("Segoe UI", 16, "bold"), bg=COR_BG_GERAL, fg="#f87171").pack(pady=12)

        frame_info = tk.Frame(modal, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        frame_info.pack(fill="x", padx=20, pady=5)
        st = item.get('status', 'DISPONÍVEL').upper()

        info_texto = f"CATEGORIA: {item.get('categoria', '')}   |   STATUS: {st}\n\nLOCAL: {item.get('txt_local', '')}\nDATA: {item.get('txt_data', '')}\nDESCRIÇÃO: {item.get('txt_descricao', '')}\n"
        if item.get('solicitado_por'): info_texto += f"\n🚨 SOLICITADO POR: {item.get('solicitado_por')} (RM: {item.get('rm_aluno', '')})"

        tk.Label(frame_info, text=info_texto, justify="left", bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL, font=("Segoe UI", 11)).pack(padx=20, pady=15, anchor="w")

        tk.Label(modal, text="Galeria de Fotos:", font=("Segoe UI", 12, "bold"), bg=COR_BG_GERAL, fg=COR_TEXTO_PRINCIPAL).pack(pady=(10, 5), anchor="w", padx=20)
        frame_fotos = tk.Frame(modal, bg=COR_BG_GERAL)
        frame_fotos.pack(fill="both", expand=True, padx=20)

        fotos_array = item.get('fotos', [])
        if not fotos_array and item.get('foto'): fotos_array = [item['foto']]

        if not fotos_array: tk.Label(frame_fotos, text="Nenhuma foto registrada.", bg=COR_BG_GERAL, fg="#8b949e", font=("Segoe UI", 10)).pack(pady=10, anchor="w")
        else:
            for col, foto_url in enumerate(fotos_array):
                try:
                    if foto_url.startswith('http'):
                        import urllib.request
                        with urllib.request.urlopen(foto_url) as u: raw_data = u.read()
                        img = Image.open(io.BytesIO(raw_data))
                        img.thumbnail((160, 160), Image.Resampling.LANCZOS)
                        img_tk = ImageTk.PhotoImage(img)
                        lbl_img = tk.Label(frame_fotos, image=img_tk, bg=COR_BG_CARD, bd=1, relief="solid")
                        lbl_img.image = img_tk
                        lbl_img.grid(row=0, column=col, padx=8, pady=5)
                except: pass

        frame_acoes = tk.Frame(modal, bg=COR_BG_GERAL)
        frame_acoes.pack(fill="x", pady=20, padx=20)

        def btn(txt, cor, cmd):
            tk.Button(frame_acoes, text=txt, bg=cor, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=8, cursor="hand2", command=cmd).pack(side="left", padx=4, fill="x", expand=True)

        btn("🖨️ Etiqueta", COR_AZUL, lambda: self.abrir_modal_etiqueta_qr(item))
        btn("✏️ Editar", "#d97706", lambda: [modal.destroy(), self.abrir_modal_form(item)])
        
        if st == 'SOLICITADO': btn("🚫 Recusar", "#b45309", lambda: self.acao_rapida(item['id'], 'recusar', modal))
        if st not in ['ENTREGUE', 'DOAÇÃO FEITA']: btn("✅ Baixa", COR_VERDE, lambda: [modal.destroy(), self.abrir_dar_baixa(item)])
        if st not in ['PARA DOAÇÃO', 'DOAÇÃO FEITA', 'ENTREGUE']: btn("🎁 Doação", "#9333ea", lambda: self.acao_rapida(item['id'], 'doacao', modal))
        btn("🗑️ Excluir", COR_DESTAQUE, lambda: self.acao_rapida(item['id'], 'excluir', modal))

    # --- GERADOR DE QR CODE ETIQUETA ---
    def abrir_modal_etiqueta_qr(self, item):
        modal = tk.Toplevel(self.root)
        modal.title("Impressão de Etiqueta QR")
        modal.geometry("360x470")
        modal.configure(bg=COR_BG_CARD)
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text=f"Etiqueta do Item #{item['id']}", font=("Segoe UI", 14, "bold"), bg=COR_BG_CARD, fg="#f87171").pack(pady=15)
        
        payload = f"ETEC-ITEM-{item['id']}"
        qr = qrcode.QRCode(version=1, box_size=8, border=1)
        qr.add_data(payload)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        largura, altura = img_qr.size
        etiqueta_img = Image.new('RGB', (largura, altura + 30), color='white')
        etiqueta_img.paste(img_qr, (0, 0))
        
        draw = ImageDraw.Draw(etiqueta_img)
        texto = f"ID: {item['id']}"
        try: fonte = ImageFont.truetype("arial.ttf", 20)
        except: fonte = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        w_texto = bbox[2] - bbox[0]
        x_texto = (largura - w_texto) / 2
        draw.text((x_texto, altura), texto, fill="black", font=fonte)

        preview = etiqueta_img.copy()
        preview.thumbnail((190, 190), Image.Resampling.LANCZOS)
        preview_tk = ImageTk.PhotoImage(preview)
        lbl_preview = tk.Label(modal, image=preview_tk, bg=COR_BG_CARD, bd=1, relief="solid")
        lbl_preview.image = preview_tk
        lbl_preview.pack(pady=10)

        def salvar_png():
            path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=f"qr_etec_{item['id']}.png", title="Salvar Imagem da Etiqueta", filetypes=[("Imagem PNG", "*.png")])
            if path:
                etiqueta_img.save(path)
                messagebox.showinfo("Sucesso", f"Etiqueta salva em: {path}", parent=modal)

        def imprimir_direto():
            temp_path = os.path.abspath(f"temp_etiqueta_qr_{item['id']}.png")
            etiqueta_img.save(temp_path)
            try: os.startfile(temp_path, "print")
            except Exception as e: messagebox.showerror("Erro", f"Erro na impressão direta: {e}", parent=modal)

        tk.Button(modal, text="💾 SALVAR COMO PNG", bg=COR_VERDE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2", command=salvar_png).pack(fill="x", padx=30, pady=5)
        tk.Button(modal, text="🖨️ IMPRIMIR DIRETO", bg=COR_AZUL, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2", command=imprimir_direto).pack(fill="x", padx=30, pady=5)

    # --- AÇÕES RÁPIDAS COM JWT ---
    def acao_rapida(self, item_id, acao, modal=None):
        try:
            if acao == 'excluir' and messagebox.askyesno("Excluir", "Deseja excluir este item permanentemente?"):
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", headers=self.get_auth_headers())
            elif acao == 'recusar' and messagebox.askyesno("Recusar", "Deseja recusar a solicitação?"):
                res = requests.put(f"{API_URL}/api/itens/{item_id}/recusar", headers=self.get_auth_headers())
            elif acao == 'doacao':
                res = requests.put(f"{API_URL}/api/itens/{item_id}", json={"status": "PARA DOAÇÃO"}, headers=self.get_auth_headers())
            else: return

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", "Operação realizada!")
                if modal: modal.destroy()
                self.carregar_dados()
            else:
                messagebox.showerror("Erro", "Acesso Negado.")
        except Exception as e: messagebox.showerror("Erro", str(e))

    # --- DAR BAIXA COM JWT ---
    def abrir_dar_baixa(self, item):
        modal_baixa = tk.Toplevel(self.root)
        modal_baixa.title(f"Dar Baixa - Item #{item['id']}")
        modal_baixa.geometry("460x420")
        modal_baixa.configure(bg=COR_BG_GERAL)
        modal_baixa.transient(self.root)
        modal_baixa.grab_set()

        tk.Label(modal_baixa, text="Registrar Entrega ao Dono", font=("Segoe UI", 14, "bold"), bg=COR_BG_GERAL, fg=COR_VERDE).pack(pady=15)
        
        tk.Label(modal_baixa, text="Nome Completo do Aluno:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_nome = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_nome.insert(0, item.get('solicitado_por') or '')
        entry_nome.pack(padx=35, pady=(0, 10), fill="x")

        tk.Label(modal_baixa, text="RM do Aluno:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_rm = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_rm.insert(0, item.get('rm_aluno') or '')
        entry_rm.pack(padx=35, pady=(0, 10), fill="x")

        tk.Label(modal_baixa, text="Turma / Curso:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_turma = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_turma.pack(padx=35, pady=(0, 20), fill="x")

        def confirmar():
            n, r, t = entry_nome.get().strip(), entry_rm.get().strip(), entry_turma.get().strip() or "-"
            if not n or not r: return messagebox.showwarning("Aviso", "Preencha Nome e RM", parent=modal_baixa)
            try:
                res = requests.put(f"{API_URL}/api/itens/{item['id']}", json={"status": "ENTREGUE", "retirado_por": n, "rm_retirante": r, "turma_curso": t, "funcionario_responsavel": "Secretaria Desktop"}, headers=self.get_auth_headers())
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item baixado com sucesso!", parent=modal_baixa)
                    modal_baixa.destroy()
                    self.carregar_dados()
                    nome_obj = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
                    self.abrir_tela_comprovante(item['id'], nome_obj, item.get('txt_descricao') or '', item.get('txt_local') or '', n, r, t)
                else: messagebox.showerror("Erro", "Acesso Negado.", parent=modal_baixa)
            except Exception as e: messagebox.showerror("Erro", str(e), parent=modal_baixa)

        tk.Button(modal_baixa, text="Confirmar e Gerar Comprovante", bg=COR_VERDE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=10, cursor="hand2", command=confirmar).pack(fill="x", padx=35)
        entry_nome.focus()

    def abrir_tela_comprovante(self, item_id, nome_item, desc_item, local_item, retirado_por, rm, turma):
        top_comp = tk.Toplevel(self.root)
        top_comp.title("Comprovante de Retirada")
        top_comp.geometry("650x700")
        top_comp.configure(bg="#e5e7eb") 
        top_comp.transient(self.root)
        top_comp.grab_set()

        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        folha = tk.Frame(top_comp, bg="white", padx=40, pady=30)
        folha.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(folha, text="ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO", font=("Segoe UI", 13, "bold"), bg="white", fg="black").pack()
        tk.Label(folha, text="Sistema de Achados e Perdidos - Termo de Retirada", font=("Segoe UI", 10, "bold"), bg="white", fg="#4b5563").pack(pady=(0, 20))

        f_aluno = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_aluno.pack(fill="x", pady=5)
        tk.Label(f_aluno, text=f"Nome: {retirado_por}\nRM: {rm}\nTurma/Curso: {turma}", font=("Segoe UI", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        f_item = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_item.pack(fill="x", pady=5)
        tk.Label(f_item, text=f"Item #{item_id}: {nome_item}\nLocal Encontrado: {local_item}\nData da Entrega: {data_atual}", font=("Segoe UI", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        def baixar_comprovante_txt():
            file_path = filedialog.asksaveasfilename(parent=top_comp, defaultextension=".txt", initialfile=f"comprovante_{rm}.txt", title="Salvar Comprovante")
            if file_path:
                txt_content = f"ETEC - TERMO DE RETIRADA\nAluno: {retirado_por} (RM: {rm}, Turma: {turma})\nItem #{item_id}: {nome_item}\nData: {data_atual}"
                with open(file_path, "w", encoding="utf-8") as f: f.write(txt_content)
                messagebox.showinfo("Sucesso", "Comprovante salvo!", parent=top_comp)

        b_frame = tk.Frame(top_comp, bg="#e5e7eb")
        b_frame.pack(fill="x", padx=30, pady=(0, 20))
        tk.Button(b_frame, text="📥 BAIXAR TXT", command=baixar_comprovante_txt, bg=COR_AZUL, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(b_frame, text="Fechar", command=top_comp.destroy, bg="#475569", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(5, 0))

    # --- DOAÇÕES E CATEGORIAS ---
    def construir_tab_doacoes(self):
        frame_top = tk.Frame(self.tab_doacoes, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        tk.Label(frame_top, text="Gerenciamento de Doações", font=("Segoe UI", 14, "bold"), bg=COR_BG_GERAL, fg="#f59e0b").pack(side="left")
        
        def concluir_doacoes():
            if messagebox.askyesno("Confirmar Doação", "Deseja remover todos os itens doados do sistema?"):
                try:
                    for child in self.tree_doacoes.get_children():
                        requests.put(f"{API_URL}/api/itens/{self.tree_doacoes.item(child)['values'][0]}", json={"status": "DOAÇÃO FEITA"}, headers=self.get_auth_headers())
                    requests.delete(f"{API_URL}/api/itens/doacoes/concluir", headers=self.get_auth_headers())
                    messagebox.showinfo("Sucesso", "Doações concluídas!")
                    self.carregar_dados()
                except: pass
                
        tk.Button(frame_top, text="🎁 CONCLUIR E LIMPAR DOAÇÕES", bg="#f59e0b", fg="#0d1117", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=concluir_doacoes).pack(side="right")
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Data Encontrado")
        self.tree_doacoes = ttk.Treeview(self.tab_doacoes, columns=colunas, show="headings", height=18)
        for col in colunas: self.tree_doacoes.heading(col, text=col); self.tree_doacoes.column(col, anchor="center")
        self.tree_doacoes.pack(fill="both", expand=True, pady=5, padx=12)

    def construir_tab_categorias(self):
        frame_add = tk.Frame(self.tab_categorias, bg=COR_BG_GERAL)
        frame_add.pack(pady=25)
        tk.Label(frame_add, text="Nova Categoria:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=6)
        self.entry_cat = ttk.Entry(frame_add, width=30, font=("Segoe UI", 10))
        self.entry_cat.pack(side="left", padx=6)
        self.entry_cat.bind("<Return>", lambda e: self.adicionar_categoria())
        tk.Button(frame_add, text="Adicionar", bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2", command=self.adicionar_categoria).pack(side="left", padx=6)
        
        self.listbox_cats = tk.Listbox(self.tab_categorias, bg=COR_BG_CARD, fg="white", font=("Segoe UI", 11), height=15, bd=0, highlightthickness=1, highlightbackground=COR_BORDA)
        self.listbox_cats.pack(fill="x", padx=60, pady=15)

    def carregar_categorias(self):
        try:
            res = requests.get(f"{API_URL}/api/categorias")
            if res.status_code == 200:
                self.listbox_cats.delete(0, tk.END)
                self.categorias_atuais = []
                for c in res.json():
                    self.listbox_cats.insert(tk.END, f"   • {c['nome']}")
                    self.categorias_atuais.append(c['nome'])
        except: pass

    def adicionar_categoria(self):
        nome = self.entry_cat.get().strip().upper()
        if nome:
            try:
                res = requests.post(f"{API_URL}/api/categorias", json={"nome": nome}, headers=self.get_auth_headers())
                if res.status_code == 200:
                    self.entry_cat.delete(0, tk.END)
                    self.carregar_categorias()
            except: pass

    def construir_tab_entregues(self):
        frame_top = tk.Frame(self.tab_entregues, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        
        tk.Button(frame_top, text="🔄 Atualizar Histórico", command=self.carregar_entregues, bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(frame_top, text="🗑️ Excluir Registro", command=self.excluir_entregue, bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=(10, 0))
        tk.Button(frame_top, text="↩️ Desfazer Entrega", command=self.desfazer_entrega, bg="#d97706", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")

        colunas = ("Recibo", "ID Item", "Item", "Retirado Por", "RM", "Turma", "Data")
        self.tree_entregues = ttk.Treeview(self.tab_entregues, columns=colunas, show="headings", height=18)
        for col in colunas: self.tree_entregues.heading(col, text=col); self.tree_entregues.column(col, anchor="center")
        self.tree_entregues.pack(fill="both", expand=True, pady=5, padx=12)
        self.tree_entregues.bind("<Double-1>", self.abrir_detalhes_do_historico)

    def carregar_entregues(self):
        if not TOKEN_SECRETARIA: return
        try:
            res = requests.get(f"{API_URL}/api/entregues", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.tree_entregues.delete(*self.tree_entregues.get_children())
                for e in res.json():
                    self.tree_entregues.insert("", "end", values=(e['id'], e['item_id'], e['nome_item'], e['retirado_por'], e['rm_retirante'], e['turma_curso'], e['data_entrega']))
        except: pass

    def abrir_detalhes_do_historico(self, event):
        selecionado = self.tree_entregues.selection()
        if selecionado:
            item_id = self.tree_entregues.item(selecionado[0])['values'][1]
            item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
            if item: self.abrir_modal_detalhes_item(item_direto=item)

    def desfazer_entrega(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        vals = self.tree_entregues.item(selecionado[0], "values")
        if messagebox.askyesno("Desfazer", f"Reverter entrega do item #{vals[1]}?"):
            try:
                res = requests.put(f"{API_URL}/api/itens/{vals[1]}/recusar", headers=self.get_auth_headers())
                if res.status_code == 200: self.carregar_dados()
            except: pass

    def excluir_entregue(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        vals = self.tree_entregues.item(selecionado[0], "values")
        if messagebox.askyesno("Excluir", f"Excluir histórico do item #{vals[1]}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{vals[1]}", headers=self.get_auth_headers())
                if res.status_code == 200: self.carregar_dados()
            except: pass

    # --- CHAT ---
    def construir_tab_chat(self):
        frame_esq = tk.Frame(self.tab_chat, bg=COR_BG_GERAL, width=280)
        frame_esq.pack(side="left", fill="y", padx=12, pady=12)
        
        tk.Label(frame_esq, text="Conversas Ativas", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 12, "bold")).pack(pady=(0, 8))
        self.listbox_chat = tk.Listbox(frame_esq, bg=COR_BG_CARD, fg="white", font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground=COR_BORDA)
        self.listbox_chat.pack(fill="both", expand=True)
        self.listbox_chat.bind("<<ListboxSelect>>", self.selecionar_conversa)
        
        frame_dir = tk.Frame(self.tab_chat, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        frame_dir.pack(side="right", fill="both", expand=True, padx=12, pady=12)
        
        self.lbl_chat_titulo = tk.Label(frame_dir, text="Selecione um aluno para iniciar", bg=COR_BG_CARD, fg="#f87171", font=("Segoe UI", 13, "bold"))
        self.lbl_chat_titulo.pack(pady=12)
        
        self.txt_mensagens = tk.Text(frame_dir, bg=COR_BG_GERAL, fg="white", state="disabled", wrap="word", font=("Segoe UI", 11), bd=0)
        self.txt_mensagens.pack(fill="both", expand=True, padx=12, pady=5)
        
        frame_input = tk.Frame(frame_dir, bg=COR_BG_CARD)
        frame_input.pack(fill="x", padx=12, pady=12)
        
        self.entry_chat = ttk.Entry(frame_input, font=("Segoe UI", 11))
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_chat.bind("<Return>", lambda e: self.enviar_mensagem())
        
        tk.Button(frame_input, text="Enviar", bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=self.enviar_mensagem).pack(side="right")
        self.atualizar_chat_continuo()

    def carregar_conversas(self):
        if not TOKEN_SECRETARIA: return
        try:
            res = requests.get(f"{API_URL}/api/chat/conversas", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.listbox_chat.delete(0, tk.END)
                self.mapa_conversas = []
                for c in res.json():
                    notif = f"🔥 ({c['nao_lidas']} novas) " if c['nao_lidas'] > 0 else "   "
                    self.listbox_chat.insert(tk.END, f"{notif}{c['nome_aluno']} (RM: {c['rm_aluno']})")
                    self.mapa_conversas.append(c['rm_aluno'])
        except: pass

    def selecionar_conversa(self, event):
        selecao = self.listbox_chat.curselection()
        if selecao:
            idx = selecao[0]
            self.rm_chat_ativo = self.mapa_conversas[idx]
            self.lbl_chat_titulo.config(text=f"Chat com: {self.listbox_chat.get(idx)}")
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
        if not self.rm_chat_ativo or not self.entry_chat.get().strip(): return
        try:
            res = requests.post(f"{API_URL}/api/chat/enviar", json={"rm": self.rm_chat_ativo, "nome": "Secretaria", "remetente": "SECRETARIA", "mensagem": self.entry_chat.get().strip()})
            if res.status_code == 200:
                self.entry_chat.delete(0, tk.END)
                self.carregar_mensagens_aluno()
        except: pass

    def atualizar_chat_continuo(self):
        if TOKEN_SECRETARIA:
            self.carregar_conversas()
            if self.rm_chat_ativo: self.carregar_mensagens_aluno()
        self.chat_timer = self.root.after(3000, self.atualizar_chat_continuo)

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretariaApp(root)
    root.mainloop()
