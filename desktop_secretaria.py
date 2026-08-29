import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import base64
import json
from datetime import datetime
from PIL import Image, ImageTk
import io

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

        self.fotos_base64 = [] # Now a list to hold up to 4 photos
        self.foto_thumbnails = [] # To keep references to PhotoImage objects
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
        self.root.geometry("1200x750")
        self.root.resizable(True, True)

        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - BANCO DE DADOS NEON (POSTGRESQL)", font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=8)
        lbl_sub = tk.Label(header, text="ETEC Prof.º José Ignácio Azevedo Filho", font=("Helvetica", 9), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Formulário Frame
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

        # Fotos Section
        tk.Label(self.form_frame, text="Fotos do Objeto (Max 4):", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w", pady=(5,2))
        
        btn_foto_frame = tk.Frame(self.form_frame, bg="#1e1e2e")
        btn_foto_frame.grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 5))

        btn_foto = tk.Button(btn_foto_frame, text="📷 Adicionar Foto", command=self.adicionar_foto, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.pack(side="left")
        
        btn_limpar_fotos = tk.Button(btn_foto_frame, text="🗑 Limpar Fotos", command=self.limpar_fotos_ui, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_limpar_fotos.pack(side="left", padx=10)

        self.lbl_status_foto = tk.Label(btn_foto_frame, text="0/4 fotos", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.pack(side="left")

        # Container for photo previews
        self.preview_frame = tk.Frame(self.form_frame, bg="#334155", height=80, width=280)
        self.preview_frame.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 15))
        self.preview_frame.grid_propagate(False) # Keep size fixed

        # Botões de Ação do Formulário
        self.btn_salvar = tk.Button(self.form_frame, text="✔ Gravar no Banco Nuvem", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        self.btn_salvar.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=14, column=0, columnspan=2, sticky="ew")
        self.btn_cancelar.grid_remove()

        # Tabela Frame
        table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "categoria", "data", "local", "status", "solicitado_por", "rm_aluno", "qtd_fotos")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")
        self.tree.heading("solicitado_por", text="Solicitante")
        self.tree.heading("rm_aluno", text="RM")
        self.tree.heading("qtd_fotos", text="Fotos")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("descricao", width=140)
        self.tree.column("categoria", width=90)
        self.tree.column("data", width=80, anchor="center")
        self.tree.column("local", width=90)
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("solicitado_por", width=110)
        self.tree.column("rm_aluno", width=65, anchor="center")
        self.tree.column("qtd_fotos", width=40, anchor="center")

        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Double-1>", lambda event: self.preparar_edicao_item())

        actions_frame = tk.Frame(table_frame, bg="#1e1e2e")
        actions_frame.pack(fill="x", pady=(10, 0))

        btn_editar = tk.Button(actions_frame, text="✏ Editar Item", command=self.preparar_edicao_item, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_editar.pack(side="left", expand=True, fill="x", padx=(0, 2))

        btn_excluir = tk.Button(actions_frame, text="🗑 Excluir Item", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_excluir.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_doacao = tk.Button(actions_frame, text="🎁 Concluir Doações", command=self.concluir_doacoes, bg="#9333ea", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_doacao.pack(side="left", expand=True, fill="x", padx=(2, 2))

        btn_refresh = tk.Button(actions_frame, text="🔄 Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        btn_refresh.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.carregar_tabela()

    def redimensionar_imagem(self, image_path, max_size=(800, 800)):
        """Redimensiona e comprime a imagem antes de converter para base64"""
        img = Image.open(image_path)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Converte para RGB se tiver transparência (necessário para JPEG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=75) # Comprime com JPEG
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
        
    def criar_miniatura_ui(self, base64_str):
        """Cria e exibe uma miniatura no frame de preview"""
        try:
            # Decode base64 if it has the data URI prefix
            if base64_str.startswith('data:image'):
                base64_data = base64_str.split(',')[1]
            else:
                base64_data = base64_str
                
            img_data = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_data))
            img.thumbnail((70, 70))
            
            photo = ImageTk.PhotoImage(img)
            self.foto_thumbnails.append(photo) # Manter referência
            
            idx = len(self.foto_thumbnails) - 1
            lbl = tk.Label(self.preview_frame, image=photo, bg="#334155")
            lbl.grid(row=0, column=idx, padx=2, pady=5)
        except Exception as e:
            print(f"Erro ao criar miniatura: {e}")

    def limpar_fotos_ui(self):
        self.fotos_base64 = []
        self.foto_thumbnails = []
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        self.lbl_status_foto.config(text="0/4 fotos", fg="#94a3b8")

    def adicionar_foto(self):
        if len(self.fotos_base64) >= 4:
            messagebox.showinfo("Limite de Fotos", "Você já atingiu o limite máximo de 4 fotos por item.")
            return

        filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")])
        if filename:
            try:
                # Comprimir a imagem
                encoded_string = self.redimensionar_imagem(filename)
                full_base64 = f"data:image/jpeg;base64,{encoded_string}"
                
                self.fotos_base64.append(full_base64)
                self.criar_miniatura_ui(full_base64)
                
                self.lbl_status_foto.config(text=f"{len(self.fotos_base64)}/4 fotos", fg="#4ade80")
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
            "fotos": self.fotos_base64 # Agora envia a lista de fotos
        }

        try:
            if self.item_editando_id is None:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=20)
                msg_sucesso = "Registrado no PostgreSQL Neon!"
            else:
                res = requests.put(f"{API_URL}/api/itens/{self.item_editando_id}", json=payload, timeout=20)
                msg_sucesso = f"Item #{self.item_editando_id} atualizado com sucesso!"

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", msg_sucesso)
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor ({res.status_code}):\n{res.text}")
        except requests.exceptions.Timeout:
            messagebox.showerror("Timeout", "O servidor demorou muito para responder. As imagens podem ser muito grandes.")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def preparar_edicao_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item da tabela para editar!")
            return

        valores = self.tree.item(selected[0], "values")
        self.item_editando_id = valores[0]
        
        # Buscar os dados completos da API para pegar as fotos
        try:
            res = requests.get(f"{API_URL}/api/itens/{self.item_editando_id}", timeout=10)
            if res.status_code == 200:
                item_data = res.json()
            else:
                messagebox.showerror("Erro", "Não foi possível carregar os dados completos do item.")
                return
        except Exception as e:
             messagebox.showerror("Erro de Conexão", f"Falha ao buscar item: {e}")
             return

        self.txt_descricao.delete(0, tk.END)
        self.txt_descricao.insert(0, item_data.get('txt_descricao', ''))
        
        cat = item_data.get('categoria', 'OUTROS')
        if cat in self.cb_categoria["values"]:
            self.cb_categoria.set(cat)

        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, item_data.get('txt_data', ''))

        self.txt_local.delete(0, tk.END)
        self.txt_local.insert(0, item_data.get('txt_local', ''))

        status_normalizado = item_data.get('status', 'DISPONÍVEL').upper()
        if status_normalizado in ["GUARDADO", "DISPONIVEL"]:
            status_normalizado = "DISPONÍVEL"

        if status_normalizado in self.cb_status["values"]:
            self.cb_status.set(status_normalizado)

        # Tratar as fotos existentes
        self.limpar_fotos_ui()
        fotos_data = item_data.get('fotos', [])
        
        if fotos_data:
            self.fotos_base64 = fotos_data
            for foto in self.fotos_base64:
                self.criar_miniatura_ui(foto)
            self.lbl_status_foto.config(text=f"{len(self.fotos_base64)}/4 fotos (Mantidas)", fg="#94a3b8")
        else:
            # Compatibilidade com versão antiga ('foto' única)
            foto_antiga = item_data.get('foto')
            if foto_antiga:
                 self.fotos_base64 = [foto_antiga]
                 self.criar_miniatura_ui(foto_antiga)
                 self.lbl_status_foto.config(text="1/4 fotos (Mantida)", fg="#94a3b8")
            else:
                self.lbl_status_foto.config(text="0/4 fotos", fg="#94a3b8")

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
        self.limpar_fotos_ui()

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
                        
                    # Determinar quantidade de fotos
                    qtd_fotos = 0
                    if i.get("fotos"):
                        qtd_fotos = len(i.get("fotos"))
                    elif i.get("foto"): # Legacy
                        qtd_fotos = 1
                        
                    self.tree.insert("", tk.END, values=(i["id"], i["txt_descricao"], categoria, i["txt_data"], i["txt_local"], status, solicitado_por, rm_aluno, qtd_fotos))
        except Exception as e:
            print(f"Aguardando conexão... {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
