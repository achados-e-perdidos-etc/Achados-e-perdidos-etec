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
        self.root.geometry("1180x730")
        self.root.resizable(True, True)

        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - BANCO DE DADOS NEON (POSTGRESQL)", font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=8)
        lbl_sub = tk.Label(header, text="ETEC Prof.º José Ignácio Azevedo Filho", font=("Helvetica", 9), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

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

        table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "categoria", "data", "local", "status", "solicitado_por", "rm_aluno")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
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

        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", lambda event: self.preparar_edicao_item())

        actions_frame = tk.Frame(table_frame, bg="#1e1e2e")
        actions_frame.pack(fill="x", pady=(10, 0))

        btn_editar = tk.Button(actions_frame, text="✏ Editar Item", command=self.preparar_edicao_item, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_editar.pack(side="left", expand=True, fill="x", padx=(0, 2))

        btn_localizar = tk.Button(actions_frame, text="🔍 Localizar / Baixa", command=self.abrir_janela_localizar, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_localizar.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_excluir = tk.Button(actions_frame, text="🗑 Excluir Item", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_excluir.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_doacao = tk.Button(actions_frame, text="🎁 Concluir Doações", command=self.concluir_doacoes, bg="#9333ea", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_doacao.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_refresh = tk.Button(actions_frame, text="🔄 Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        btn_refresh.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.carregar_tabela()

    def carregar_fotos(self):
        filenames = filedialog.askopenfilenames(
            title="Selecione até 4 fotos",
            filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")]
        )
        if filenames:
            novas_fotos = list(filenames)
            disponiveis = 4 - len(self.fotos_base64)
            
            if disponiveis <= 0:
                messagebox.showwarning("Limite Atingido", "Limite de 4 fotos já foi atingido! Clique em 'Limpar Fotos' se quiser mudar.")
                return

            if len(novas_fotos) > disponiveis:
                messagebox.showinfo("Aviso", f"Você pode adicionar mais {disponiveis} foto(s). Apenas as primeiras {disponiveis} serão adicionadas.")
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
        if self.item_editando_id:
            self.lbl_status_foto.config(text="Fotos limpas (não substituirá fotos atuais se não carregar novas)", fg="#94a3b8")
        else:
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

        # Solicita dados de quem retirou se for marcado como ENTREGUE
        if status.upper() == 'ENTREGUE':
            nome_ret = simpledialog.askstring("Dados da Entrega", "Nome completo do retirante:", parent=self.root)
            rm_ret = simpledialog.askstring("Dados da Entrega", "RM/Documento do retirante:", parent=self.root)
            if not nome_ret or not rm_ret:
                messagebox.showwarning("Atenção", "É necessário informar o nome e RM/Documento para marcar como ENTREGUE!")
                return
            payload["retirado_por"] = nome_ret
            payload["rm_retirante"] = rm_ret
            payload["data_entrega"] = datetime.now().strftime("%d/%m/%Y")

        try:
            if self.item_editando_id is None:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                msg_sucesso = "Registrado no PostgreSQL Neon!"
            else:
                res = requests.put(f"{API_URL}/api/itens/{self.item_editando_id}", json=payload, timeout=10)
                msg_sucesso = f"Item #{self.item_editando_id} atualizado com sucesso!"

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", msg_sucesso)
                if status.upper() == 'ENTREGUE':
                    self.exibir_comprovante_retirada(
                        self.item_editando_id or "NOVO",
                        descricao,
                        payload.get("retirado_por"),
                        payload.get("rm_retirante")
                    )
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor ({res.status_code}):\n{res.text}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def preparar_edicao_item(self, id_direto=None):
        if id_direto is not None:
            for child in self.tree.get_children():
                if str(self.tree.item(child, "values")[0]) == str(id_direto):
                    self.tree.selection_set(child)
                    break

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item da tabela para editar!")
            return

        valores = self.tree.item(selected[0], "values")
        
        self.item_editando_id = valores[0]
        self.txt_descricao.delete(0, tk.END)
        self.txt_descricao.insert(0, valores[1])
        
        if valores[2] in self.cb_categoria["values"]:
            self.cb_categoria.set(valores[2])

        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, valores[3])

        self.txt_local.delete(0, tk.END)
        self.txt_local.insert(0, valores[4])

        status_normalizado = valores[5].upper()
        if status_normalizado in ["GUARDADO", "DISPONIVEL"]:
            status_normalizado = "DISPONÍVEL"

        if status_normalizado in self.cb_status["values"]:
            self.cb_status.set(status_normalizado)

        self.fotos_base64 = []
        self.lbl_status_foto.config(text="Manter foto(s) atual(is)", fg="#94a3b8")

        self.form_frame.config(text=f" Editando Item ID #{self.item_editando_id} ", fg="#eab308")
        self.btn_salvar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#0f172a")
        self.btn_cancelar.grid()

    def abrir_janela_localizar(self):
        top = tk.Toplevel(self.root)
        top.title("Localizar Item / Dar Baixa")
        top.geometry("450x380")
        top.configure(bg="#1e1e2e")
        top.transient(self.root)
        top.grab_set()

        tk.Label(top, text="Digite o ID do Item:", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold")).pack(pady=(20, 5))
        txt_busca_id = tk.Entry(top, font=("Helvetica", 12), bg="#334155", fg="white", justify="center", insertbackground="white")
        txt_busca_id.pack(pady=5)
        txt_busca_id.focus()

        lbl_resultado = tk.Label(top, text="", bg="#1e1e2e", fg="#e2e8f0", font=("Helvetica", 10), justify="left", wraplength=400)
        lbl_resultado.pack(pady=15)

        btn_editar_loc = tk.Button(top, text="✏ Editar Este Item", bg="#eab308", fg="#0f172a", font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2")
        btn_editar_loc.pack_forget()

        def buscar():
            item_id = txt_busca_id.get().strip()
            if not item_id.isdigit():
                messagebox.showwarning("Aviso", "Digite um ID válido (número)!", parent=top)
                return

            try:
                res = requests.get(f"{API_URL}/api/itens/localizar/{item_id}", timeout=10)
                if res.status_code == 200:
                    data = res.json().get("item", {})
                    st = data.get("status", "DISPONÍVEL")
                    
                    text = f"ID: #{data.get('id')}\n"
                    text += f"Descrição: {data.get('txt_descricao')}\n"
                    text += f"Categoria: {data.get('categoria')}\n"
                    text += f"Data: {data.get('txt_data')} | Local: {data.get('txt_local')}\n"
                    text += f"Status: {st}\n"

                    if st.upper() == 'ENTREGUE' and "entrega" in data:
                        ent = data["entrega"]
                        text += f"\n--- DADOS DA RETIRADA ---\n"
                        text += f"Retirado Por: {ent.get('retirado_por')}\n"
                        text += f"RM/Doc: {ent.get('rm_retirante')}\n"
                        text += f"Data Entrega: {ent.get('data_entrega')}\n"

                    lbl_resultado.config(text=text)

                    btn_editar_loc.config(command=lambda: [top.destroy(), self.preparar_edicao_item(data.get('id'))])
                    btn_editar_loc.pack(pady=5)
                else:
                    lbl_resultado.config(text="❌ Item não encontrado no banco de dados!")
                    btn_editar_loc.pack_forget()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na requisição: {e}", parent=top)

        btn_buscar = tk.Button(top, text="🔍 Buscar", command=buscar, bg="#0284c7", fg="white", font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2")
        btn_buscar.pack(pady=5)

    def exibir_comprovante_retirada(self, item_id, descricao, retirante, rm):
        top = tk.Toplevel(self.root)
        top.title("Comprovante de Retirada de Objeto")
        top.geometry("480x520")
        top.configure(bg="#1e1e2e")

        func_nome = simpledialog.askstring("Assinatura", "Nome do funcionário que efetuou a devolução:", parent=self.root) or "Secretaria ETEC"

        texto_comprovante = f"""---------------------------------------------------
        ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO
           COMPROVANTE DE RETIRADA DE OBJETO
---------------------------------------------------
Data/Hora: {datetime.now().strftime("%d/%m/%Y - %H:%M")}
ID do Item: #{item_id}
Descrição: {descricao}

DADOS DO RETIRANTE:
Nome Completo: {retirante}
RM / Documento: {rm}

RESPONSÁVEL PELA DEVOLUÇÃO:
Funcionário: {func_nome}

---------------------------------------------------
Assinatura do Retirante: ___________________________

Assinatura do Funcionário: _________________________
---------------------------------------------------"""

        lbl_txt = tk.Text(top, font=("Courier", 10), bg="#0f172a", fg="#38bdf8", padx=10, pady=10)
        lbl_txt.insert("1.0", texto_comprovante)
        lbl_txt.config(state="disabled")
        lbl_txt.pack(fill="both", expand=True, padx=15, pady=15)

        def baixar():
            fn = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Arquivo de Texto", "*.txt")], initialfile=f"comprovante_item_{item_id}.txt")
            if fn:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(texto_comprovante)
                messagebox.showinfo("Sucesso", "Comprovante salvo com sucesso!", parent=top)

        btn_dl = tk.Button(top, text="💾 Baixar / Imprimir Comprovante", command=baixar, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2", pady=8)
        btn_dl.pack(fill="x", padx=15, pady=(0, 15))

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
            messagebox.showwarning("Atenção", "Selecione um item da tabela para excluir!")
            return

        item_values = self.tree.item(selected[0], "values")
        item_id = item_values[0]
        item_desc = item_values[1]

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir o item '{item_desc}' (ID #{item_id})?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item removido com sucesso!")
                    self.limpar_formulario()
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Falha ao excluir item ({res.status_code}):\n{res.text}")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Não foi possível se conectar à API: {e}")

    def concluir_doacoes(self):
        if messagebox.askyesno("Confirmar Conclusão de Doações", "Tem certeza que deseja APAGAR TODOS os itens com o status 'DOAÇÃO FEITA'?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/doacoes/concluir", timeout=10)
                if res.status_code == 200:
                    dados = res.json()
                    messagebox.showinfo("Sucesso", f"Operação concluída!\n{dados.get('removidos', 0)} item(ns) removido(s) do banco de dados.")
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Falha ao concluir doações ({res.status_code}):\n{res.text}")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Não foi possível se conectar à API: {e}")

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens", timeout=10)
            if res.status_code == 200:
                itens = res.json()
                for i in itens:
                    categoria = i.get("categoria", "OUTROS")
                    solicitado_por = i.get("solicitado_por") or "-"
                    rm_aluno = i.get("rm_aluno") or "-"
                    status = i.get("status", "DISPONÍVEL")
                    if status.upper() == "GUARDADO":
                        status = "DISPONÍVEL"
                    self.tree.insert("", tk.END, values=(i["id"], i["txt_descricao"], categoria, i["txt_data"], i["txt_local"], status, solicitado_por, rm_aluno))
        except Exception as e:
            print(f"Aguardando conexão... {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
