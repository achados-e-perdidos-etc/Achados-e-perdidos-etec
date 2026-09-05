import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
import hashlib
from datetime import datetime
import threading
import time
import os
import webbrowser

API_URL = "https://achados-etec-api.onrender.com"

_AUTH_EMAIL_HASH = "7547c4fd75b0c4cf47ee844f1c6c00f1e77b95b261edb083dfc9a08cd7cf22cd"
_AUTH_PASS_HASH = "a115236c51dd5498e7683f79d9de387c842f70c258f69719855184ed54ecea56"

class AdminDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Achados e Perdidos | Login Secretaria")
        self.root.geometry("400x450")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)

        self.fotos_base64 = []
        self.item_editando_id = None
        self.tabela_visualizada = "itens"
        self.janela_chat_aberta = False
        self.rm_chat_ativo = None
        self.chat_polling_ativo = False

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", background="#2d3748", foreground="#ffffff", fieldbackground="#2d3748", rowheight=28)
        self.style.configure("Treeview.Heading", background="#1e293b", foreground="#38bdf8", font=("Helvetica", 10, "bold"))
        self.style.map("Treeview", background=[('selected', '#2563eb')])

        self.mostrar_tela_login()

    def mostrar_tela_login(self):
        self.login_frame = tk.Frame(self.root, bg="#1e1e2e", padx=30, pady=30)
        self.login_frame.pack(expand=True, fill="both")

        lbl_icone = tk.Label(self.login_frame, text="🔒", font=("Helvetica", 40), bg="#1e1e2e", fg="#38bdf8")
        lbl_icone.pack(pady=(10, 5))

        lbl_titulo = tk.Label(self.login_frame, text="Acesso Restrito", font=("Helvetica", 16, "bold"), bg="#1e1e2e", fg="#ffffff")
        lbl_titulo.pack()

        lbl_sub = tk.Label(self.login_frame, text="Secretaria - ETEC Profº José Ignácio", font=("Helvetica", 9), bg="#1e1e2e", fg="#94a3b8")
        lbl_sub.pack(pady=(0, 20))

        tk.Label(self.login_frame, text="E-mail de Acesso:", bg="#1e1e2e", fg="#e2e8f0", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(5, 2))
        self.txt_login_email = tk.Entry(self.login_frame, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_login_email.pack(fill="x", pady=(0, 15))

        tk.Label(self.login_frame, text="Senha:", bg="#1e1e2e", fg="#e2e8f0", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(5, 2))
        self.txt_login_senha = tk.Entry(self.login_frame, font=("Helvetica", 11), show="•", bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_login_senha.pack(fill="x", pady=(0, 20))

        self.txt_login_senha.bind("<Return>", lambda event: self.validar_login())

        btn_entrar = tk.Button(self.login_frame, text="ENTRAR NO SISTEMA", command=self.validar_login, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", pady=8, cursor="hand2")
        btn_entrar.pack(fill="x")

    def validar_login(self):
        email_digitado = self.txt_login_email.get().strip()
        senha_digitada = self.txt_login_senha.get().strip()
        email_real = base64.b64decode(_AUTH_EMAIL_HASH).decode('utf-8')
        senha_real = base64.b64decode(_AUTH_PASS_HASH).decode('utf-8')
        if email_digitado == email_real and senha_digitada == senha_real:
            self.login_frame.destroy()
            self.iniciar_painel_principal()
        else:
            messagebox.showerror("Acesso Negado", "E-mail ou senha incorretos!\nApenas a secretaria tem acesso a este sistema.")

    def carregar_categorias_api(self):
        try:
            res = requests.get(f"{API_URL}/api/categorias", timeout=5)
            if res.status_code == 200:
                cats = [c["nome"] for c in res.json()]
                if cats:
                    self.cb_categoria["values"] = cats
                    if self.cb_categoria.get() not in cats:
                        self.cb_categoria.current(0)
        except Exception as e: print("Erro ao puxar categorias:", e)

    def adicionar_nova_categoria(self):
        nova_cat = simpledialog.askstring("Nova Categoria", "Digite o nome da nova categoria:", parent=self.root)
        if nova_cat:
            nova_cat = nova_cat.strip().upper()
            try:
                res = requests.post(f"{API_URL}/api/categorias", json={"nome": nova_cat}, timeout=5)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", f"Categoria '{nova_cat}' adicionada!")
                    self.carregar_categorias_api()
                    self.cb_categoria.set(nova_cat)
            except Exception as e: messagebox.showerror("Erro de Conexão", str(e))

    def verificar_regra_eletronicos(self, event):
        if self.cb_categoria.get() == "ELETRÔNICOS" and "somente os pais" not in self.txt_descricao.get().lower():
            self.txt_descricao.insert(tk.END, "\n(Atenção: Somente os pais ou responsáveis podem retirar na secretaria).")

    def iniciar_painel_principal(self):
        self.root.title("ETEC - Achados e Perdidos | Administração / Secretaria")
        self.root.geometry("1300x740")
        self.root.resizable(True, True)

        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - BANCO DE DADOS NEON (POSTGRESQL)", font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=8)
        lbl_sub = tk.Label(header, text="ETEC Prof.º José Ignácio Azevedo Filho", font=("Helvetica", 9), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # FORMULÁRIO
        self.form_frame = tk.LabelFrame(container, text=" Cadastro / Edição de Objeto ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=15, pady=15)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(self.form_frame, text="Nome do Item (Curto/Título):", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w", pady=(5,2))
        self.txt_nome = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11, "bold"), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_nome.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Descrição Detalhada:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w", pady=(5,2))
        self.txt_descricao = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w", pady=(5,2))
        
        frame_cat = tk.Frame(self.form_frame, bg="#1e1e2e")
        frame_cat.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.cb_categoria = ttk.Combobox(frame_cat, state="readonly", width=25)
        self.cb_categoria.pack(side="left")
        self.cb_categoria.bind("<<ComboboxSelected>>", self.verificar_regra_eletronicos)
        
        tk.Button(frame_cat, text="+", command=self.adicionar_nova_categoria, bg="#3b82f6", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", padx=(5,0))

        tk.Label(self.form_frame, text="Data Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w", pady=(5,2))
        self.txt_data = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Local Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w", pady=(5,2))
        self.txt_local = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=9, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Status do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w", pady=(5,2))
        self.cb_status = ttk.Combobox(self.form_frame, values=["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO", "DOAÇÃO FEITA"], state="readonly", width=30)
        self.cb_status.current(0)
        self.cb_status.grid(row=11, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Fotos do Objeto (Até 4):", bg="#1e1e2e", fg="#e2e8f0").grid(row=12, column=0, sticky="w", pady=(5,2))
        
        btn_foto_frame = tk.Frame(self.form_frame, bg="#1e1e2e")
        btn_foto_frame.grid(row=13, column=0, columnspan=2, sticky="w", pady=(0, 10))
        tk.Button(btn_foto_frame, text="📷 Selecionar...", command=self.carregar_fotos, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", padx=(0, 5))
        tk.Button(btn_foto_frame, text="🗑 Limpar", command=self.limpar_fotos_selecionadas, bg="#475569", fg="white", font=("Helvetica", 8), relief="flat", cursor="hand2").pack(side="left")

        self.lbl_status_foto = tk.Label(self.form_frame, text="0 / 4 fotos", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.btn_salvar = tk.Button(self.form_frame, text="✔ Gravar no Banco Nuvem", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        self.btn_salvar.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=16, column=0, columnspan=2, sticky="ew")
        self.btn_cancelar.grid_remove()

        # TABELA
        self.table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        self.table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        top_actions = tk.Frame(self.table_frame, bg="#1e1e2e")
        top_actions.pack(fill="x", pady=(0, 5))

        tk.Button(top_actions, text="💬 Chat Alunos", command=self.abrir_janela_chat, bg="#ec4899", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2", pady=4, padx=5).pack(side="left", padx=(0, 5))
        
        self.btn_alternar_tabela = tk.Button(top_actions, text="🔄 Ver Tabela: HISTÓRICO DE ENTREGAS", command=self.alternar_modo_tabela, bg="#3b82f6", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2", pady=4, padx=5)
        self.btn_alternar_tabela.pack(side="right")

        self.tree = ttk.Treeview(self.table_frame, show="headings", height=15)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda event: self.preparar_edicao_item() if self.tabela_visualizada == "itens" else None)

        actions_frame = tk.Frame(self.table_frame, bg="#1e1e2e")
        actions_frame.pack(fill="x", pady=(10, 0))

        # BOTÃO DASHBOARD (NOVO)
        tk.Button(actions_frame, text="📊 Dashboard", command=self.abrir_dashboard, bg="#8b5cf6", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_editar = tk.Button(actions_frame, text="✏ Editar", command=self.preparar_edicao_item, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_editar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_localizar = tk.Button(actions_frame, text="🔍 Localizar", command=self.abrir_janela_localizar, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_localizar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_recusar = tk.Button(actions_frame, text="❌ Recusar", command=self.recusar_solicitacao, bg="#f97316", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_recusar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_excluir = tk.Button(actions_frame, text="🗑 Excluir", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_excluir.pack(side="left", expand=True, fill="x", padx=(2, 2))

        tk.Button(actions_frame, text="🔄 Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2").pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.carregar_categorias_api()
        self.configurar_colunas()
        self.carregar_tabela()

    # ==============================================================
    # JANELA DASHBOARD (ESTATÍSTICAS)
    # ==============================================================
    def abrir_dashboard(self):
        dash = tk.Toplevel(self.root)
        dash.title("Dashboard - Estatísticas Gerais")
        dash.geometry("500x550")
        dash.configure(bg="#1e1e2e")
        dash.transient(self.root)

        tk.Label(dash, text="📊 Resumo e Estatísticas", font=("Helvetica", 14, "bold"), bg="#1e1e2e", fg="#38bdf8").pack(pady=(20, 15))

        frame_cards = tk.Frame(dash, bg="#1e1e2e")
        frame_cards.pack(fill="x", padx=20)

        try:
            res = requests.get(f"{API_URL}/api/estatisticas", timeout=10)
            if res.status_code == 200:
                data = res.json()
                t_itens = data.get("total_itens", 0)
                t_entregues = data.get("total_entregues", 0)
                t_doacoes = data.get("total_doacoes", 0)

                # Cards Superiores
                def criar_card(parent, titulo, valor, cor):
                    f = tk.Frame(parent, bg="#334155", bd=1, relief="ridge", pady=10)
                    f.pack(side="left", expand=True, fill="both", padx=5)
                    tk.Label(f, text=titulo, font=("Helvetica", 9, "bold"), bg="#334155", fg="#cbd5e1").pack()
                    tk.Label(f, text=str(valor), font=("Helvetica", 20, "bold"), bg="#334155", fg=cor).pack()

                criar_card(frame_cards, "Total Acervo", t_itens, "#38bdf8")
                criar_card(frame_cards, "Devolvidos", t_entregues, "#4ade80")
                criar_card(frame_cards, "Doações", t_doacoes, "#c084fc")

                tk.Label(dash, text="🏆 Top Categorias Encontradas:", font=("Helvetica", 11, "bold"), bg="#1e1e2e", fg="#e2e8f0").pack(anchor="w", padx=25, pady=(25, 10))

                # Barras Horizontais Simplificadas (Tkinter Native)
                frame_barras = tk.Frame(dash, bg="#1e1e2e")
                frame_barras.pack(fill="both", expand=True, padx=25)

                categorias = data.get("categorias", [])
                max_val = max([c['qtd'] for c in categorias]) if categorias else 1

                for c in categorias:
                    f_linha = tk.Frame(frame_barras, bg="#1e1e2e")
                    f_linha.pack(fill="x", pady=4)
                    
                    lbl_cat = tk.Label(f_linha, text=c['categoria'], font=("Helvetica", 9), bg="#1e1e2e", fg="#94a3b8", width=15, anchor="e")
                    lbl_cat.pack(side="left", padx=(0,10))
                    
                    # Calcula o tamanho da barra
                    largura = int((c['qtd'] / max_val) * 250)
                    barra = tk.Frame(f_linha, bg="#ef4444", width=largura, height=20)
                    barra.pack(side="left")
                    
                    tk.Label(f_linha, text=str(c['qtd']), font=("Helvetica", 9, "bold"), bg="#1e1e2e", fg="#ffffff").pack(side="left", padx=5)

            else:
                tk.Label(dash, text="Erro ao carregar dados.", bg="#1e1e2e", fg="red").pack()
        except Exception as e:
            tk.Label(dash, text=f"Erro: {e}", bg="#1e1e2e", fg="red").pack()

    # ==============================================================
    # ETIQUETAS E LOCALIZAR
    # ==============================================================
    def gerar_etiqueta(self, item_id, nome, cat, data):
        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; display: flex; justify-content: center; padding-top: 50px; background-color: #f1f1f1;">
            <div style="width: 350px; background-color: #fff; border: 3px dashed #000; padding: 20px; text-align: center; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <h3 style="margin: 0; color: #333; text-transform: uppercase;">ETEC Profº José Ignácio</h3>
                <p style="margin: 0; font-size: 10px; color: #666;">Setor de Achados & Perdidos</p>
                <hr style="border: 1px solid #ccc; margin: 15px 0;">
                <h1 style="font-size: 65px; margin: 5px 0; color: #dc2626;">#{item_id}</h1>
                <h2 style="margin: 10px 0 5px 0; font-size: 22px;">{nome}</h2>
                <p style="margin: 0; font-size: 16px; color: #555; font-weight: bold;">{cat}</p>
                <p style="margin: 10px 0 0 0; font-size: 14px; color: #777;">Registrado em: {data}</p>
            </div>
            <script>
                setTimeout(() => window.print(), 500);
            </script>
        </body>
        </html>
        """
        filepath = os.path.abspath(f"etiqueta_{item_id}.html")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            webbrowser.open('file://' + filepath)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível gerar a etiqueta: {e}")

    def abrir_janela_localizar(self):
        top = tk.Toplevel(self.root)
        top.title("Localizar Item / Dar Baixa")
        top.geometry("520x650")
        top.configure(bg="#1e1e2e")
        top.transient(self.root)
        top.grab_set()

        tk.Label(top, text="Digite o ID do Item:", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold")).pack(pady=(15, 5))
        frame_busca = tk.Frame(top, bg="#1e1e2e")
        frame_busca.pack(pady=5)
        txt_busca_id = tk.Entry(frame_busca, font=("Helvetica", 12, "bold"), bg="#334155", fg="white", justify="center", width=12)
        txt_busca_id.pack(side="left", padx=5)
        txt_busca_id.focus()
        lbl_resultado = tk.Label(top, text="Aguardando ID...", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 10), justify="left", wraplength=460)
        lbl_resultado.pack(pady=10)
        options_frame = tk.Frame(top, bg="#1e1e2e")

        def buscar():
            item_id = txt_busca_id.get().strip()
            if not item_id.isdigit(): return
            try:
                res = requests.get(f"{API_URL}/api/itens/localizar/{item_id}", timeout=10)
                if res.status_code == 200:
                    data = res.json().get("item", {})
                    st = data.get("status", "DISPONÍVEL")
                    text = f"📦 ID #{data.get('id')} - {data.get('nome')}\nDesc: {data.get('txt_descricao')}\nCat: {data.get('categoria')} | Local: {data.get('txt_local')}\nStatus: {st}\n"
                    
                    if st.upper() == 'SOLICITADO':
                        text += f"Solicitante: {data.get('solicitado_por')} (RM: {data.get('rm_aluno')})\n"
                        prova = data.get('prova_propriedade')
                        if prova:
                            text += f"\n🔒 PROVA DE PROPRIEDADE INFORMADA:\n\"{prova}\"\n"

                    lbl_resultado.config(text=text, fg="#ffffff")
                    for child in options_frame.winfo_children(): child.destroy()
                    options_frame.pack(fill="x", padx=20, pady=10)
                    
                    # NOVO BOTÃO DE ETIQUETA
                    tk.Button(options_frame, text="🖨️ Imprimir Etiqueta de Identificação", command=lambda: self.gerar_etiqueta(data.get('id'), data.get('nome'), data.get('categoria'), data.get('txt_data')), bg="#475569", fg="white", font=("Helvetica", 9, "bold"), relief="flat", pady=6).pack(fill="x", pady=3)
                    
                    if st.upper() != 'ENTREGUE':
                        tk.Button(options_frame, text="✅ Dar Baixa como 'Entregue ao Dono'", command=lambda: self.dar_baixa_entregue(data.get('id'), data.get('nome'), top), bg="#16a34a", fg="white", font=("Helvetica", 9, "bold"), relief="flat", pady=6).pack(fill="x", pady=3)
                else:
                    lbl_resultado.config(text="❌ Item não encontrado!", fg="#f87171")
                    options_frame.pack_forget()
            except Exception as e: messagebox.showerror("Erro", str(e), parent=top)

        tk.Button(frame_busca, text="🔍 Buscar", command=buscar, bg="#0284c7", fg="white", font=("Helvetica", 10, "bold"), relief="flat").pack(side="left")

    def dar_baixa_entregue(self, item_id, nome_desc, parent_top):
        top_baixa = tk.Toplevel(parent_top)
        top_baixa.title(f"Baixa #{item_id}")
        top_baixa.geometry("380x350")
        top_baixa.configure(bg="#1e1e2e")
        top_baixa.transient(parent_top)
        top_baixa.grab_set()

        tk.Label(top_baixa, text="Nome Completo do Retirante:", bg="#1e1e2e", fg="#e2e8f0").pack(anchor="w", padx=25, pady=(15, 2))
        txt_nome = tk.Entry(top_baixa, font=("Helvetica", 10), bg="#334155", fg="white")
        txt_nome.pack(fill="x", padx=25)

        tk.Label(top_baixa, text="RM / Documento:", bg="#1e1e2e", fg="#e2e8f0").pack(anchor="w", padx=25, pady=(5, 2))
        txt_rm = tk.Entry(top_baixa, font=("Helvetica", 10), bg="#334155", fg="white")
        txt_rm.pack(fill="x", padx=25)

        def salvar_baixa():
            n, r = txt_nome.get().strip(), txt_rm.get().strip()
            if not n or not r: return messagebox.showwarning("Aviso", "Preencha Nome e RM", parent=top_baixa)
            try:
                res = requests.put(f"{API_URL}/api/itens/{item_id}", json={"status": "ENTREGUE", "retirado_por": n, "rm_retirante": r, "funcionario_responsavel": "Secretaria ETEC"}, timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Baixa concluída!", parent=top_baixa)
                    top_baixa.destroy()
                    parent_top.destroy()
                    self.carregar_tabela()
            except Exception as e: messagebox.showerror("Erro", str(e), parent=top_baixa)
        tk.Button(top_baixa, text="✔ Confirmar Baixa", command=salvar_baixa, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", pady=8).pack(fill="x", padx=25, pady=20)

    # ==============================================================
    # JANELA DE CHAT
    # ==============================================================
    def abrir_janela_chat(self):
        if self.janela_chat_aberta: return
        self.janela_chat_aberta = True
        self.top_chat = tk.Toplevel(self.root)
        self.top_chat.title("Central de Atendimento - Chat com Alunos")
        self.top_chat.geometry("780x520")
        self.top_chat.configure(bg="#1e1e2e")

        def ao_fechar():
            self.janela_chat_aberta = False
            self.chat_polling_ativo = False
            self.top_chat.destroy()

        self.top_chat.protocol("WM_DELETE_WINDOW", ao_fechar)

        frame_conversas = tk.LabelFrame(self.top_chat, text=" Conversas ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 10, "bold"), width=280)
        frame_conversas.pack(side="left", fill="y", padx=10, pady=10)
        self.tree_conversas = ttk.Treeview(frame_conversas, columns=("rm", "nome", "novas"), show="headings", height=15)
        self.tree_conversas.heading("rm", text="RM")
        self.tree_conversas.heading("nome", text="Nome")
        self.tree_conversas.heading("novas", text="Novas")
        self.tree_conversas.column("rm", width=65, anchor="center")
        self.tree_conversas.column("nome", width=120)
        self.tree_conversas.column("novas", width=50, anchor="center")
        self.tree_conversas.pack(fill="both", expand=True)
        self.tree_conversas.bind("<<TreeviewSelect>>", self.ao_selecionar_aluno_chat)
        tk.Button(frame_conversas, text="🔄 Recarregar Alunos", command=self.carregar_lista_conversas, bg="#334155", fg="white", font=("Helvetica", 8, "bold"), relief="flat").pack(fill="x", pady=5)

        frame_mensagens = tk.LabelFrame(self.top_chat, text=" Mensagens ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 10, "bold"))
        frame_mensagens.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)
        self.lbl_aluno_atual = tk.Label(frame_mensagens, text="Selecione um aluno", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 10, "bold"))
        self.lbl_aluno_atual.pack(anchor="w", padx=10, pady=(5, 5))
        self.txt_chat_historico = tk.Text(frame_mensagens, bg="#0f172a", fg="#ffffff", font=("Helvetica", 10), state="disabled", wrap="word", padx=10, pady=10)
        self.txt_chat_historico.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        frame_input = tk.Frame(frame_mensagens, bg="#1e1e2e")
        frame_input.pack(fill="x", padx=10, pady=(0, 10))
        self.txt_chat_resposta = tk.Entry(frame_input, font=("Helvetica", 11), bg="#334155", fg="white", insertbackground="white")
        self.txt_chat_resposta.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.txt_chat_resposta.bind("<Return>", lambda e: self.enviar_resposta_secretaria())
        tk.Button(frame_input, text="Enviar 💬", command=self.enviar_resposta_secretaria, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2", padx=10).pack(side="right")

        self.carregar_lista_conversas()
        self.chat_polling_ativo = True
        self.iniciar_loop_polling_chat()

    def carregar_lista_conversas(self):
        for item in self.tree_conversas.get_children(): self.tree_conversas.delete(item)
        try:
            res = requests.get(f"{API_URL}/api/chat/conversas", timeout=6)
            if res.status_code == 200:
                for c in res.json():
                    novas = f"🔥 {c['nao_lidas']}" if c['nao_lidas'] > 0 else "0"
                    self.tree_conversas.insert("", tk.END, values=(c['rm_aluno'], c['nome_aluno'], novas))
        except Exception: pass

    def ao_selecionar_aluno_chat(self, event):
        sel = self.tree_conversas.selection()
        if not sel: return
        vals = self.tree_conversas.item(sel[0], "values")
        self.rm_chat_ativo = str(vals[0])
        self.lbl_aluno_atual.config(text=f"Conversando com: {vals[1]} (RM: {self.rm_chat_ativo})", fg="#38bdf8")
        self.carregar_mensagens_aluno_ativo()

    def carregar_mensagens_aluno_ativo(self):
        if not self.rm_chat_ativo: return
        try:
            res = requests.get(f"{API_URL}/api/chat/mensagens/{self.rm_chat_ativo}?marcar_lida=true&origem=SECRETARIA", timeout=6)
            if res.status_code == 200:
                self.txt_chat_historico.config(state="normal")
                self.txt_chat_historico.delete("1.0", tk.END)
                for m in res.json():
                    autor = "VOCÊ" if m['remetente'] == 'SECRETARIA' else f"{m['nome_aluno']}"
                    self.txt_chat_historico.insert(tk.END, f"[{m['data_envio']}] {autor}:\n", "header")
                    self.txt_chat_historico.insert(tk.END, f"{m['mensagem']}\n\n", "corpo")
                self.txt_chat_historico.tag_config("header", foreground="#38bdf8", font=("Helvetica", 9, "bold"))
                self.txt_chat_historico.tag_config("corpo", foreground="#f1f5f9", font=("Helvetica", 10))
                self.txt_chat_historico.see(tk.END)
                self.txt_chat_historico.config(state="disabled")
        except Exception: pass

    def enviar_resposta_secretaria(self):
        if not self.rm_chat_ativo: return
        texto = self.txt_chat_resposta.get().strip()
        if not texto: return
        self.txt_chat_resposta.delete(0, tk.END)
        try:
            res = requests.post(f"{API_URL}/api/chat/enviar", json={"rm": self.rm_chat_ativo, "nome": "Secretaria ETEC", "remetente": "SECRETARIA", "mensagem": texto}, timeout=6)
            if res.status_code == 200: self.carregar_mensagens_aluno_ativo()
        except Exception: pass

    def iniciar_loop_polling_chat(self):
        def loop():
            while self.chat_polling_ativo:
                time.sleep(3)
                if self.janela_chat_aberta and self.rm_chat_ativo:
                    try: self.carregar_mensagens_aluno_ativo()
                    except Exception: pass
        threading.Thread(target=loop, daemon=True).start()

    # ==============================================================
    # DEMAIS FUNÇÕES DO SISTEMA
    # ==============================================================
    def alternar_modo_tabela(self):
        if self.tabela_visualizada == "itens":
            self.tabela_visualizada = "entregues"
            self.btn_alternar_tabela.config(text="📦 Ver Tabela: ITENS DO ESTOQUE", bg="#8b5cf6")
            self.table_frame.config(text=" Histórico de Entregas Realizadas ")
            self.btn_editar.config(state="disabled")
            self.btn_localizar.config(state="disabled")
            self.btn_recusar.config(state="disabled")
            self.btn_excluir.config(state="disabled")
        else:
            self.tabela_visualizada = "itens"
            self.btn_alternar_tabela.config(text="🔄 Ver Tabela: HISTÓRICO DE ENTREGAS", bg="#3b82f6")
            self.table_frame.config(text=" Registros no Neon PostgreSQL ")
            self.btn_editar.config(state="normal")
            self.btn_localizar.config(state="normal")
            self.btn_recusar.config(state="normal")
            self.btn_excluir.config(state="normal")
        self.configurar_colunas()
        self.carregar_tabela()

    def configurar_colunas(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if self.tabela_visualizada == "itens":
            self.tree["columns"] = ("id", "nome", "categoria", "data", "local", "status", "solicitado_por")
            self.tree.heading("id", text="ID")
            self.tree.heading("nome", text="Nome do Item")
            self.tree.heading("categoria", text="Categoria")
            self.tree.heading("data", text="Data")
            self.tree.heading("local", text="Local")
            self.tree.heading("status", text="Status")
            self.tree.heading("solicitado_por", text="Solicitante")
            self.tree.column("id", width=35, anchor="center")
            self.tree.column("nome", width=160)
            self.tree.column("categoria", width=90)
            self.tree.column("data", width=80, anchor="center")
            self.tree.column("local", width=90)
            self.tree.column("status", width=90, anchor="center")
            self.tree.column("solicitado_por", width=100)
        else:
            self.tree["columns"] = ("id", "item_id", "nome_item", "retirado_por", "rm_retirante", "turma_curso", "data_entrega")
            self.tree.heading("id", text="Recibo")
            self.tree.heading("item_id", text="ID Item")
            self.tree.heading("nome_item", text="Descrição/Nome")
            self.tree.heading("retirado_por", text="Retirado Por")
            self.tree.heading("rm_retirante", text="RM")
            self.tree.heading("turma_curso", text="Turma")
            self.tree.heading("data_entrega", text="Data Retirada")
            self.tree.column("id", width=50, anchor="center")
            self.tree.column("item_id", width=50, anchor="center")
            self.tree.column("nome_item", width=140)
            self.tree.column("retirado_por", width=120)
            self.tree.column("rm_retirante", width=70, anchor="center")
            self.tree.column("turma_curso", width=80, anchor="center")
            self.tree.column("data_entrega", width=95, anchor="center")

    def recusar_solicitacao(self):
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("Atenção", "Selecione um item!")
        vals = self.tree.item(selected[0], "values")
        if vals[5].upper() != "SOLICITADO": return messagebox.showinfo("Aviso", "Apenas itens SOLICITADO podem ser recusados.")
        if messagebox.askyesno("Confirmar", f"Recusar solicitação do item #{vals[0]}?"):
            try:
                res = requests.put(f"{API_URL}/api/itens/{vals[0]}/recusar", timeout=10)
                if res.status_code == 200: self.carregar_tabela()
            except Exception as e: messagebox.showerror("Erro", str(e))

    def carregar_fotos(self):
        filenames = filedialog.askopenfilenames(title="Selecione até 4 fotos", filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")])
        if filenames:
            novas = list(filenames)
            disp = 4 - len(self.fotos_base64)
            if disp <= 0: return messagebox.showwarning("Limite", "Limite atingido!")
            if len(novas) > disp: novas = novas[:disp]
            for f in novas:
                try:
                    with open(f, "rb") as image_file:
                        enc = base64.b64encode(image_file.read()).decode('utf-8')
                        self.fotos_base64.append(f"data:image/jpeg;base64,{enc}")
                except Exception as e: messagebox.showerror("Erro", str(e))
            self.lbl_status_foto.config(text=f"✓ {len(self.fotos_base64)} / 4 fotos", fg="#4ade80")

    def limpar_fotos_selecionadas(self):
        self.fotos_base64 = []
        self.lbl_status_foto.config(text="0 / 4 fotos", fg="#94a3b8")

    def salvar_item(self):
        nome, descricao, categoria, data, local, status = self.txt_nome.get().strip(), self.txt_descricao.get().strip(), self.cb_categoria.get(), self.txt_data.get().strip(), self.txt_local.get().strip(), self.cb_status.get()
        if not nome or not descricao or not data or not local: return messagebox.showwarning("Atenção", "Preencha Nome, Descrição, Data e Local!")
        payload = {"nome": nome, "descricao": descricao, "categoria": categoria, "data": data, "local": local, "status": status, "fotos": self.fotos_base64}
        try:
            if self.item_editando_id is None:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                if res.status_code == 200: messagebox.showinfo("Sucesso", f"Item #{res.json().get('id')} salvo!")
            else:
                res = requests.put(f"{API_URL}/api/itens/{self.item_editando_id}", json=payload, timeout=10)
                if res.status_code == 200: messagebox.showinfo("Sucesso", "Atualizado!")
            if res.status_code == 200:
                self.limpar_formulario()
                self.carregar_tabela()
        except Exception as e: messagebox.showerror("Erro", str(e))

    def preparar_edicao_item(self, id_direto=None):
        if self.tabela_visualizada != "itens": return
        selected = self.tree.selection()
        if not selected: return messagebox.showwarning("Atenção", "Selecione um item!")
        item_id = self.tree.item(selected[0], "values")[0]
        try:
            res = requests.get(f"{API_URL}/api/itens/localizar/{item_id}", timeout=10)
            if res.status_code == 200:
                i = res.json().get("item", {})
                self.item_editando_id = i['id']
                self.txt_nome.delete(0, tk.END)
                self.txt_nome.insert(0, i.get('nome') or '')
                self.txt_descricao.delete(0, tk.END)
                self.txt_descricao.insert(0, i.get('txt_descricao') or '')
                self.cb_categoria.set(i.get('categoria') or 'OUTROS')
                self.txt_data.delete(0, tk.END)
                self.txt_data.insert(0, i.get('txt_data') or '')
                self.txt_local.delete(0, tk.END)
                self.txt_local.insert(0, i.get('txt_local') or '')
                self.cb_status.set(i.get('status') or 'DISPONÍVEL')
                self.fotos_base64 = []
                self.lbl_status_foto.config(text="Mantendo fotos originais...", fg="#94a3b8")
                self.form_frame.config(text=f" Editando Item #{self.item_editando_id} ", fg="#eab308")
                self.btn_salvar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#0f172a")
                self.btn_cancelar.grid()
        except Exception as e: messagebox.showerror("Erro", str(e))

    def limpar_formulario(self):
        self.item_editando_id = None
        self.txt_nome.delete(0, tk.END)
        self.txt_descricao.delete(0, tk.END)
        self.cb_categoria.current(0)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_local.delete(0, tk.END)
        self.cb_status.current(0)
        self.fotos_base64 = []
        self.lbl_status_foto.config(text="0 / 4 fotos", fg="#94a3b8")
        self.form_frame.config(text=" Cadastro / Edição de Objeto ", fg="#38bdf8")
        self.btn_salvar.config(text="✔ Gravar no Banco Nuvem", bg="#16a34a", fg="white")
        self.btn_cancelar.grid_remove()

    def excluir_item(self):
        selected = self.tree.selection()
        if not selected: return
        item_id = self.tree.item(selected[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"Excluir item #{item_id}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", timeout=10)
                if res.status_code == 200:
                    self.limpar_formulario()
                    self.carregar_tabela()
            except Exception: pass

    def concluir_doacoes(self):
        if messagebox.askyesno("Confirmar", "Remover itens com status 'DOAÇÃO FEITA'?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/doacoes/concluir", timeout=10)
                if res.status_code == 200: self.carregar_tabela()
            except Exception: pass

    def carregar_tabela(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            if self.tabela_visualizada == "itens":
                res = requests.get(f"{API_URL}/api/itens", timeout=10)
                if res.status_code == 200:
                    for i in res.json():
                        self.tree.insert("", tk.END, values=(
                            i["id"], i.get("nome", "-"), i.get("categoria", "OUTROS"),
                            i["txt_data"], i["txt_local"], i.get("status", "DISPONÍVEL"),
                            i.get("solicitado_por") or "-"
                        ))
            else:
                res = requests.get(f"{API_URL}/api/entregues", timeout=10)
                if res.status_code == 200:
                    for ent in res.json():
                        self.tree.insert("", tk.END, values=(
                            ent["id"], ent["item_id"], ent["nome_item"],
                            ent["retirado_por"], ent["rm_retirante"], ent.get("turma_curso") or "-",
                            ent["data_entrega"]
                        ))
        except Exception as e: print("Erro ao carregar dados:", e)

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
