import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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

        self.foto_base64 = ""
        self.item_editando_id = None  # Guarda o ID do item em edição

        # Estilização global do Tkinter
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
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        # Cabeçalho
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - BANCO DE DADOS NEON (POSTGRESQL)", 
                             font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=8)
        lbl_sub = tk.Label(header, text="ETEC Prof.º José Ignácio Azevedo Filho", 
                           font=("Helvetica", 9), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        # Painel Principal
        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Formulário Lado Esquerdo
        self.form_frame = tk.LabelFrame(container, text=" Cadastro / Edição de Objeto ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=15, pady=15)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Campo: Descrição
        tk.Label(self.form_frame, text="Descrição do Item:", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w", pady=(5,2))
        self.txt_descricao = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Categoria
        tk.Label(self.form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w", pady=(5,2))
        self.cb_categoria = ttk.Combobox(self.form_frame, values=["MOCHILA", "ROUPAS", "ACESSÓRIOS", "ESCOLARES", "OUTROS"], state="readonly", width=30)
        self.cb_categoria.current(0)
        self.cb_categoria.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Data
        tk.Label(self.form_frame, text="Data Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w", pady=(5,2))
        self.txt_data = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Local
        tk.Label(self.form_frame, text="Local Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w", pady=(5,2))
        self.txt_local = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Status
        tk.Label(self.form_frame, text="Status do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w", pady=(5,2))
        self.cb_status = ttk.Combobox(self.form_frame, values=["GUARDADO", "ENTREGUE"], state="readonly", width=30)
        self.cb_status.current(0)
        self.cb_status.grid(row=9, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Foto
        tk.Label(self.form_frame, text="Foto do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w", pady=(5,2))
        btn_foto = tk.Button(self.form_frame, text="📷 Carregar Nova Foto...", command=self.carregar_foto, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.grid(row=11, column=0, sticky="w", pady=(0, 10))
        
        self.lbl_status_foto = tk.Label(self.form_frame, text="Sem foto nova", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.grid(row=11, column=1, sticky="w", padx=5)

        # Botão Salvar (Cadastrar / Atualizar)
        self.btn_salvar = tk.Button(self.form_frame, text="✔ Gravar no Banco Nuvem", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        self.btn_salvar.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        # Botão Cancelar Edição
        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=13, column=0, columnspan=2, sticky="ew")
        self.btn_cancelar.grid_remove() # Oculto por padrão

        # Tabela Lado Direito
        table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "categoria", "data", "local", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("descricao", width=150)
        self.tree.column("categoria", width=90)
        self.tree.column("data", width=80, anchor="center")
        self.tree.column("local", width=100)
        self.tree.column("status", width=85, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Atalho: duplo clique para editar
        self.tree.bind("<Double-1>", lambda event: self.preparar_edicao_item())

        # Painel de Ações
        actions_frame = tk.Frame(table_frame, bg="#1e1e2e")
        actions_frame.pack(fill="x", pady=(10, 0))

        btn_editar = tk.Button(actions_frame, text="✏ Editar Item Selecionado", command=self.preparar_edicao_item, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_editar.pack(side="left", expand=True, fill="x", padx=(0, 2))

        btn_excluir = tk.Button(actions_frame, text="🗑 Excluir Item", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_excluir.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_refresh = tk.Button(actions_frame, text="🔄 Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        btn_refresh.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.carregar_tabela()

    def carregar_foto(self):
        filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")])
        if filename:
            try:
                with open(filename, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    self.foto_base64 = f"data:image/jpeg;base64,{encoded_string}"
                    self.lbl_status_foto.config(text="✓ Nova Foto Pronta", fg="#4ade80")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar imagem: {e}")

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
            "foto": self.foto_base64
        }

        try:
            if self.item_editando_id is None:
                # MODO CRIAÇÃO (POST)
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                msg_sucesso = "Registrado no PostgreSQL Neon!"
            else:
                # MODO EDIÇÃO COMPLETA (PUT)
                res = requests.put(f"{API_URL}/api/itens/{self.item_editando_id}", json=payload, timeout=10)
                msg_sucesso = f"Item #{self.item_editando_id} atualizado com sucesso!"

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", msg_sucesso)
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor ({res.status_code}):\n{res.text}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def preparar_edicao_item(self):
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

        if valores[5] in self.cb_status["values"]:
            self.cb_status.set(valores[5])

        self.foto_base64 = ""
        self.lbl_status_foto.config(text="Manter foto atual", fg="#94a3b8")

        # Altera o visual do formulário para MODO EDIÇÃO
        self.form_frame.config(text=f" Editando Item ID #{self.item_editando_id} ", fg="#eab308")
        self.btn_salvar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#0f172a")
        self.btn_cancelar.grid()

    def limpar_formulario(self):
        self.item_editando_id = None
        self.txt_descricao.delete(0, tk.END)
        self.cb_categoria.current(0)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_local.delete(0, tk.END)
        self.cb_status.current(0)
        self.foto_base64 = ""
        self.lbl_status_foto.config(text="Sem foto nova", fg="#94a3b8")

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

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens", timeout=10)
            if res.status_code == 200:
                itens = res.json()
                for i in itens:
                    categoria = i.get("categoria", "OUTROS")
                    self.tree.insert("", tk.END, values=(i["id"], i["txt_descricao"], categoria, i["txt_data"], i["txt_local"], i["status"]))
        except Exception as e:
            print(f"Aguardando conexão... {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
