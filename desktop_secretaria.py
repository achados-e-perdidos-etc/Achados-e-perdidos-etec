import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
import base64
from datetime import datetime

API_URL = "https://achados-etec-api.onrender.com"

_AUTH_EMAIL_HASH = "YWNoYWRvc2VwZXJkaWRvc2V0ZWNAZ21haWwuY29t"
_AUTH_PASS_HASH = "ZXRlY2FjaGFkb3M=" 

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

    def iniciar_painel_principal(self):
        self.root.title("ETEC - Achados e Perdidos | Administração / Secretaria")
        self.root.geometry("1260x730")
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

        tk.Label(self.form_frame, text="Descrição do Item:", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w", pady=(5,2))
        self.txt_descricao = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w", pady=(5,2))
        self.cb_categoria = ttk.Combobox(self.form_frame, values=["MOCHILA", "ROUPAS", "ACESSÓRIOS", "ESCOLARES", "OUTROS"], state="readonly", width=30)
        self.cb_categoria.current(0)
        self.cb_categoria.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Data Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w", pady=(5,2))
        self.txt_data = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Local Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w", pady=(5,2))
        self.txt_local = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Status do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w", pady=(5,2))
        self.cb_status = ttk.Combobox(self.form_frame, values=["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO", "DOAÇÃO FEITA"], state="readonly", width=30)
        self.cb_status.current(0)
        self.cb_status.grid(row=9, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(self.form_frame, text="Fotos do Objeto (Até 4):", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w", pady=(5,2))
        
        btn_foto_frame = tk.Frame(self.form_frame, bg="#1e1e2e")
        btn_foto_frame.grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        btn_foto = tk.Button(btn_foto_frame, text="📷 Selecionar Fotos...", command=self.carregar_fotos, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.pack(side="left", padx=(0, 5))

        btn_limpar_fotos = tk.Button(btn_foto_frame, text="🗑 Limpar Fotos", command=self.limpar_fotos_selecionadas, bg="#475569", fg="white", font=("Helvetica", 8), relief="flat", cursor="hand2")
        btn_limpar_fotos.pack(side="left")

        self.lbl_status_foto = tk.Label(self.form_frame, text="0 / 4 fotos selecionadas", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.btn_salvar = tk.Button(self.form_frame, text="✔ Gravar no Banco Nuvem", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        self.btn_salvar.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=14, column=0, columnspan=2, sticky="ew")
        self.btn_cancelar.grid_remove()

        # TABELA
        self.table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        self.table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        top_actions = tk.Frame(self.table_frame, bg="#1e1e2e")
        top_actions.pack(fill="x", pady=(0, 5))

        self.btn_alternar_tabela = tk.Button(top_actions, text="🔄 Ver Tabela: HISTÓRICO DE ENTREGAS", command=self.alternar_modo_tabela, bg="#3b82f6", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2", pady=4)
        self.btn_alternar_tabela.pack(side="right")

        self.tree = ttk.Treeview(self.table_frame, show="headings", height=15)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", lambda event: self.preparar_edicao_item() if self.tabela_visualizada == "itens" else None)

        actions_frame = tk.Frame(self.table_frame, bg="#1e1e2e")
        actions_frame.pack(fill="x", pady=(10, 0))

        self.btn_editar = tk.Button(actions_frame, text="✏ Editar", command=self.preparar_edicao_item, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_editar.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_localizar = tk.Button(actions_frame, text="🔍 Localizar", command=self.abrir_janela_localizar, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_localizar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_recusar = tk.Button(actions_frame, text="❌ Recusar Pedido", command=self.recusar_solicitacao, bg="#f97316", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_recusar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_excluir = tk.Button(actions_frame, text="🗑 Excluir", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_excluir.pack(side="left", expand=True, fill="x", padx=(2, 2))

        self.btn_doacao = tk.Button(actions_frame, text="🎁 Limpar Doações", command=self.concluir_doacoes, bg="#9333ea", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_doacao.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_refresh = tk.Button(actions_frame, text="🔄 Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        btn_refresh.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.configurar_colunas()
        self.carregar_tabela()

    def alternar_modo_tabela(self):
        if self.tabela_visualizada == "itens":
            self.tabela_visualizada = "entregues"
            self.btn_alternar_tabela.config(text="📦 Ver Tabela: ITENS DO ESTOQUE", bg="#8b5cf6")
            self.table_frame.config(text=" Histórico de Entregas Realizadas ")
            self.btn_editar.config(state="disabled")
            self.btn_localizar.config(state="disabled")
            self.btn_recusar.config(state="disabled")
            self.btn_excluir.config(state="disabled")
            self.btn_doacao.config(state="disabled")
        else:
            self.tabela_visualizada = "itens"
            self.btn_alternar_tabela.config(text="🔄 Ver Tabela: HISTÓRICO DE ENTREGAS", bg="#3b82f6")
            self.table_frame.config(text=" Registros no Neon PostgreSQL ")
            self.btn_editar.config(state="normal")
            self.btn_localizar.config(state="normal")
            self.btn_recusar.config(state="normal")
            self.btn_excluir.config(state="normal")
            self.btn_doacao.config(state="normal")
            
        self.configurar_colunas()
        self.carregar_tabela()

    def configurar_colunas(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if self.tabela_visualizada == "itens":
            self.tree["columns"] = ("id", "descricao", "categoria", "data", "local", "status", "solicitado_por", "rm_aluno")
            self.tree.heading("id", text="ID")
            self.tree.heading("descricao", text="Descrição")
            self.tree.heading("categoria", text="Categoria")
            self.tree.heading("data", text="Data")
            self.tree.heading("local", text="Local")
            self.tree.heading("status", text="Status")
            self.tree.heading("solicitado_por", text="Solicitante")
            self.tree.heading("rm_aluno", text="RM")

            self.tree.column("id", width=35, anchor="center")
            self.tree.column("descricao", width=140)
            self.tree.column("categoria", width=90)
            self.tree.column("data", width=80, anchor="center")
            self.tree.column("local", width=90)
            self.tree.column("status", width=100, anchor="center")
            self.tree.column("solicitado_por", width=110)
            self.tree.column("rm_aluno", width=65, anchor="center")
        else:
            self.tree["columns"] = ("id", "item_id", "nome_item", "retirado_por", "rm_retirante", "turma_curso", "data_entrega", "funcionario_responsavel")
            self.tree.heading("id", text="Registro")
            self.tree.heading("item_id", text="ID Item")
            self.tree.heading("nome_item", text="Descrição")
            self.tree.heading("retirado_por", text="Retirado Por")
            self.tree.heading("rm_retirante", text="RM Retirante")
            self.tree.heading("turma_curso", text="Turma")
            self.tree.heading("data_entrega", text="Data Retirada")
            self.tree.heading("funcionario_responsavel", text="Atendente")

            self.tree.column("id", width=50, anchor="center")
            self.tree.column("item_id", width=50, anchor="center")
            self.tree.column("nome_item", width=130)
            self.tree.column("retirado_por", width=120)
            self.tree.column("rm_retirante", width=80, anchor="center")
            self.tree.column("turma_curso", width=80, anchor="center")
            self.tree.column("data_entrega", width=95, anchor="center")
            self.tree.column("funcionario_responsavel", width=100)

    def recusar_solicitacao(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item solicitado para recusar!")
            return

        valores = self.tree.item(selected[0], "values")
        item_id = valores[0]
        status = valores[5].upper()

        if status != "SOLICITADO":
            messagebox.showinfo("Aviso", "Apenas itens com status SOLICITADO podem ser recusados.")
            return

        if messagebox.askyesno("Confirmar", f"Recusar a solicitação do item #{item_id}?\nOs dados do solicitante serão limpos e o item voltará para DISPONÍVEL."):
            try:
                res = requests.put(f"{API_URL}/api/itens/{item_id}/recusar", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Solicitação cancelada com sucesso!")
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Falha no servidor: {res.text}")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def carregar_fotos(self):
        filenames = filedialog.askopenfilenames(
            title="Selecione até 4 fotos",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")]
        )
        if filenames:
            novas_fotos = list(filenames)
            disponiveis = 4 - len(self.fotos_base64)
            
            if disponiveis <= 0:
                messagebox.showwarning("Limite Atingido", "Limite de 4 fotos já foi atingido!")
                return

            if len(novas_fotos) > disponiveis:
                novas_fotos = novas_fotos[:disponiveis]

            for file in novas_fotos:
                try:
                    with open(file, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        self.fotos_base64.append(f"data:image/jpeg;base64,{encoded_string}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao processar imagem {file}: {e}")

            qtd = len(self.fotos_base64)
            self.lbl_status_foto.config(text=f"✓ {qtd} / 4 fotos selecionadas", fg="#4ade80")

    def limpar_fotos_selecionadas(self):
        self.fotos_base64 = []
        self.lbl_status_foto.config(text="0 / 4 fotos selecionadas", fg="#94a3b8")

    def salvar_item(self):
        descricao = self.txt_descricao.get().strip()
        categoria = self.cb_categoria.get()
        data = self.txt_data.get().strip()
        local = self.txt_local.get().strip()
        status = self.cb_status.get()

        if not descricao or not data or not local:
            messagebox.showwarning("Atenção!", "Preencha todos os campos obrigatórios!")
            return

        payload = {
            "descricao": descricao,
            "categoria": categoria,
            "data": data,
            "local": local,
            "status": status,
            "fotos": self.fotos_base64
        }

        try:
            if self.item_editando_id is None:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                if res.status_code == 200:
                    novo_id = res.json().get("id")
                    messagebox.showinfo("Sucesso!", f"Objeto cadastrado com Sucesso!\nID #{novo_id}")
            else:
                res = requests.put(f"{API_URL}/api/itens/{self.item_editando_id}", json=payload, timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso!", f"Item #{self.item_editando_id} atualizado com sucesso!")

            if res.status_code == 200:
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor: {res.text}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def preparar_edicao_item(self, id_direto=None):
        if self.tabela_visualizada != "itens":
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item da tabela para editar!")
            return

        valores = self.tree.item(selected[0], "values")
        self.item_editando_id = valores[0]
        self.txt_descricao.delete(0, tk.END)
        self.txt_descricao.insert(0, valores[1])
        self.cb_categoria.set(valores[2])
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, valores[3])
        self.txt_local.delete(0, tk.END)
        self.txt_local.insert(0, valores[4])

        status_norm = valores[5].upper()
        if status_norm in self.cb_status["values"]:
            self.cb_status.set(status_norm)

        self.form_frame.config(text=f" Editando Item #{self.item_editando_id} ", fg="#eab308")
        self.btn_salvar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#0f172a")
        self.btn_cancelar.grid()

    def abrir_janela_localizar(self):
        top = tk.Toplevel(self.root)
        top.title("Localizar Item / Dar Baixa")
        top.geometry("520x560")
        top.configure(bg="#1e1e2e")
        top.transient(self.root)
        top.grab_set()

        tk.Label(top, text="Digite o ID / Código do Item:", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold")).pack(pady=(15, 5))
        frame_busca = tk.Frame(top, bg="#1e1e2e")
        frame_busca.pack(pady=5)

        txt_busca_id = tk.Entry(frame_busca, font=("Helvetica", 12, "bold"), bg="#334155", fg="white", justify="center", width=12)
        txt_busca_id.pack(side="left", padx=5)
        txt_busca_id.focus()

        lbl_resultado = tk.Label(top, text="Digite o ID e clique em Buscar.", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 10), justify="left", wraplength=460)
        lbl_resultado.pack(pady=10)

        options_frame = tk.Frame(top, bg="#1e1e2e")

        def buscar():
            item_id = txt_busca_id.get().strip()
            if not item_id.isdigit():
                messagebox.showwarning("Aviso", "Digite um ID válido!", parent=top)
                return

            try:
                res = requests.get(f"{API_URL}/api/itens/localizar/{item_id}", timeout=10)
                if res.status_code == 200:
                    data = res.json().get("item", {})
                    st = data.get("status", "DISPONÍVEL")
                    text = f"📦 ID #{data.get('id')} - {data.get('txt_descricao')}\nCategoria: {data.get('categoria')} | Data: {data.get('txt_data')}\nLocal: {data.get('txt_local')}\nStatus: {st}\n"
                    lbl_resultado.config(text=text, fg="#ffffff")

                    for child in options_frame.winfo_children():
                        child.destroy()
                    options_frame.pack(fill="x", padx=20, pady=10)

                    tk.Button(options_frame, text="✅ Dar Baixa como 'Entregue ao Dono'", command=lambda: self.dar_baixa_entregue(data.get('id'), data.get('txt_descricao'), top), bg="#16a34a", fg="white", font=("Helvetica", 9, "bold"), relief="flat", pady=6).pack(fill="x", pady=3)
                else:
                    lbl_resultado.config(text="❌ Item não encontrado!", fg="#f87171")
                    options_frame.pack_forget()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na requisição: {e}", parent=top)

        tk.Button(frame_busca, text="🔍 Buscar", command=buscar, bg="#0284c7", fg="white", font=("Helvetica", 10, "bold"), relief="flat").pack(side="left")

    def dar_baixa_entregue(self, item_id, descricao, parent_top):
        top_baixa = tk.Toplevel(parent_top)
        top_baixa.title(f"Baixa / Devolução #{item_id}")
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

        tk.Label(top_baixa, text="Turma / Curso:", bg="#1e1e2e", fg="#e2e8f0").pack(anchor="w", padx=25, pady=(5, 2))
        txt_turma = tk.Entry(top_baixa, font=("Helvetica", 10), bg="#334155", fg="white")
        txt_turma.pack(fill="x", padx=25)

        def salvar_baixa():
            nome = txt_nome.get().strip()
            rm = txt_rm.get().strip()
            turma = txt_turma.get().strip()

            if not nome or not rm:
                messagebox.showwarning("Atenção", "Preencha Nome e RM!", parent=top_baixa)
                return

            payload = {
                "status": "ENTREGUE",
                "retirado_por": nome,
                "rm_retirante": rm,
                "turma_curso": turma,
                "funcionario_responsavel": "Secretaria ETEC",
                "data_entrega": datetime.now().strftime("%d/%m/%Y %H:%M")
            }

            try:
                res = requests.put(f"{API_URL}/api/itens/{item_id}", json=payload, timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item entregue com sucesso!", parent=top_baixa)
                    top_baixa.destroy()
                    parent_top.destroy()
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Erro no servidor: {res.text}", parent=top_baixa)
            except Exception as e:
                messagebox.showerror("Erro", f"Conexão falhou: {e}", parent=top_baixa)

        tk.Button(top_baixa, text="✔ Confirmar Baixa", command=salvar_baixa, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", pady=8).pack(fill="x", padx=25, pady=20)

    def limpar_formulario(self):
        self.item_editando_id = None
        self.txt_descricao.delete(0, tk.END)
        self.cb_categoria.current(0)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_local.delete(0, tk.END)
        self.cb_status.current(0)
        self.fotos_base64 = []
        self.lbl_status_foto.config(text="0 / 4 fotos selecionadas", fg="#94a3b8")
        self.form_frame.config(text=" Cadastro / Edição de Objeto ", fg="#38bdf8")
        self.btn_salvar.config(text="✔ Gravar no Banco Nuvem", bg="#16a34a", fg="white")
        self.btn_cancelar.grid_remove()

    def excluir_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item para excluir!")
            return

        item_id = self.tree.item(selected[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"Excluir definitivamente o item #{item_id}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item removido com sucesso!")
                    self.limpar_formulario()
                    self.carregar_tabela()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao conectar: {e}")

    def concluir_doacoes(self):
        if messagebox.askyesno("Confirmar", "Deseja remover todos os itens com status 'DOAÇÃO FEITA'?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/doacoes/concluir", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Itens doados removidos do banco!")
                    self.carregar_tabela()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha na requisição: {e}")

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            if self.tabela_visualizada == "itens":
                res = requests.get(f"{API_URL}/api/itens", timeout=10)
                if res.status_code == 200:
                    for i in res.json():
                        self.tree.insert("", tk.END, values=(
                            i["id"], i["txt_descricao"], i.get("categoria", "OUTROS"),
                            i["txt_data"], i["txt_local"], i.get("status", "DISPONÍVEL"),
                            i.get("solicitado_por") or "-", i.get("rm_aluno") or "-"
                        ))
            else:
                res = requests.get(f"{API_URL}/api/entregues", timeout=10)
                if res.status_code == 200:
                    for ent in res.json():
                        self.tree.insert("", tk.END, values=(
                            ent["id"], ent["item_id"], ent["nome_item"],
                            ent["retirado_por"], ent["rm_retirante"], ent.get("turma_curso") or "-",
                            ent["data_entrega"], ent.get("funcionario_responsavel") or "Secretaria"
                        ))
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
