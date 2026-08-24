import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import base64
from datetime import datetime

# URL da sua API no Render
API_URL = "https://achados-etec-api.onrender.com"

class AdminDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Achados e Perdidos | Administração / Secretaria")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1e1e2e")
        
        self.foto_base64 = ""
        self.item_id_em_edicao = None  # Indica se estamos editando um item

        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#1e1e2e", foreground="#ffffff", font=("Helvetica", 10))
        style.configure("Treeview", font=("Helvetica", 9), rowheight=25)
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

        # Header
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - ACHADOS E PERDIDOS", 
                             font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=10)

        # Container Principal
        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # Formulário Lado Esquerdo
        self.form_frame = tk.LabelFrame(container, text=" Cadastrar / Editar Item ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 10, "bold"), padx=12, pady=12)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Descrição
        tk.Label(self.form_frame, text="Descrição do Item (txt_descricao):", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w")
        self.txt_descricao = tk.Entry(self.form_frame, width=32, font=("Helvetica", 10), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=1, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Categoria
        tk.Label(self.form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w")
        self.cb_categoria = ttk.Combobox(self.form_frame, values=["MOCHILA", "ROUPAS", "ACESSÓRIOS", "ESCOLARES", "OUTROS"], state="readonly", width=30)
        self.cb_categoria.current(0)
        self.cb_categoria.grid(row=3, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Data
        tk.Label(self.form_frame, text="Data Encontrado (txt_data):", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w")
        self.txt_data = tk.Entry(self.form_frame, width=32, font=("Helvetica", 10), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=5, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Local
        tk.Label(self.form_frame, text="Local Encontrado (txt_local):", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w")
        self.txt_local = tk.Entry(self.form_frame, width=32, font=("Helvetica", 10), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=7, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Status (Apenas visível para alteração manual se necessário)
        tk.Label(self.form_frame, text="Status do Item:", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w")
        self.cb_status = ttk.Combobox(self.form_frame, values=["Disponível", "Solicitado", "Entregue"], state="readonly", width=30)
        self.cb_status.current(0)
        self.cb_status.grid(row=9, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Foto
        tk.Label(self.form_frame, text="Foto do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w")
        btn_foto = tk.Button(self.form_frame, text="📷 Selecionar Foto...", command=self.carregar_foto, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.grid(row=11, column=0, sticky="w", pady=(0, 8))
        
        self.lbl_status_foto = tk.Label(self.form_frame, text="Nenhuma foto", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 8, "italic"))
        self.lbl_status_foto.grid(row=11, column=1, sticky="w")

        # Botões do Formulário
        self.btn_salvar = tk.Button(self.form_frame, text="✔ Cadastrar no Sistema", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", pady=6, cursor="hand2")
        self.btn_salvar.grid(row=12, column=0, columnspan=2, fill="x", pady=(10, 5))

        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=13, column=0, columnspan=2, fill="x")

        # Tabela Lado Direito
        table_frame = tk.LabelFrame(container, text=" Lista de Itens Cadastrados ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 10, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "categoria", "data", "local", "status", "aluno")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")
        self.tree.heading("aluno", text="Solicitado Por")

        self.tree.column("id", width=30)
        self.tree.column("descricao", width=150)
        self.tree.column("categoria", width=90)
        self.tree.column("data", width=70)
        self.tree.column("local", width=80)
        self.tree.column("status", width=80)
        self.tree.column("aluno", width=120)

        self.tree.pack(fill="both", expand=True)

        # Painel de Ações de Seleção (Editar / Excluir)
        btn_action_frame = tk.Frame(table_frame, bg="#1e1e2e")
        btn_action_frame.pack(fill="x", pady=(8, 0))

        btn_editar = tk.Button(btn_action_frame, text="✏ Editar Selecionado", command=self.carregar_para_edicao, bg="#eab308", fg="#000000", font=("Helvetica", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2")
        btn_editar.pack(side="left", padx=(0, 5))

        btn_excluir = tk.Button(btn_action_frame, text="🗑 Excluir Selecionado", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2")
        btn_excluir.pack(side="left", padx=5)

        btn_refresh = tk.Button(btn_action_frame, text="🔄 Sincronizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", padx=10, pady=5)
        btn_refresh.pack(side="right")

        self.itens_cache = {}
        self.carregar_tabela()

    def carregar_foto(self):
        filename = filedialog.askopenfilename(filetypes=[("Imagens", "*.png;*.jpg;*.jpeg;*.webp")])
        if filename:
            try:
                with open(filename, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    self.foto_base64 = f"data:image/jpeg;base64,{encoded_string}"
                    self.lbl_status_foto.config(text="✓ Foto Alterada", fg="#4ade80")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na imagem: {e}")

    def carregar_para_edicao(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Seleção", "Por favor, selecione um item na tabela para editar!")
            return

        item_values = self.tree.item(selected_item[0])['values']
        item_id = item_values[0]
        
        item = self.itens_cache.get(item_id)
        if not item:
            return

        self.item_id_em_edicao = item_id
        
        # Preencher campos
        self.txt_descricao.delete(0, tk.END)
        self.txt_descricao.insert(0, item["txt_descricao"])

        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, item["txt_data"])

        self.txt_local.delete(0, tk.END)
        self.txt_local.insert(0, item["txt_local"])

        if item["categoria"] in self.cb_categoria['values']:
            self.cb_categoria.set(item["categoria"])

        if item["status"] in self.cb_status['values']:
            self.cb_status.set(item["status"])

        self.foto_base64 = item.get("foto", "")
        if self.foto_base64:
            self.lbl_status_foto.config(text="✓ Foto Existente", fg="#4ade80")
        else:
            self.lbl_status_foto.config(text="Sem Foto", fg="#94a3b8")

        # Alterar botões
        self.form_frame.config(text=f" Editando Item ID: {item_id} ")
        self.btn_salvar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#000000")

    def limpar_formulario(self):
        self.item_id_em_edicao = None
        self.txt_descricao.delete(0, tk.END)
        self.txt_local.delete(0, tk.END)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.cb_categoria.current(0)
        self.cb_status.current(0)
        self.foto_base64 = ""
        self.lbl_status_foto.config(text="Nenhuma foto", fg="#94a3b8")
        
        self.form_frame.config(text=" Cadastrar / Editar Item ")
        self.btn_salvar.config(text="✔ Cadastrar no Sistema", bg="#16a34a", fg="white")

    def salvar_item(self):
        descricao = self.txt_descricao.get().strip()
        data = self.txt_data.get().strip()
        local = self.txt_local.get().strip()
        categoria = self.cb_categoria.get()
        status = self.cb_status.get()

        if not descricao or not data or not local:
            messagebox.showwarning("Atenção!", "Preencha todos os campos obrigatórios!")
            return

        payload = {
            "descricao": descricao,
            "categoria": categoria,
            "data": data,
            "local": local,
            "foto": self.foto_base64,
            "status": status
        }

        try:
            if self.item_id_em_edicao:
                # EDITAR (PUT)
                res = requests.put(f"{API_URL}/api/itens/{self.item_id_em_edicao}", json=payload)
                msg = "Item alterado com sucesso!"
            else:
                # CADASTRAR NOVO (POST)
                res = requests.post(f"{API_URL}/api/itens", json=payload)
                msg = "Item cadastrado com sucesso!"

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", msg)
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", "Ocorreu um erro na requisição.")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def excluir_item(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Seleção", "Por favor, selecione um item na tabela para excluir!")
            return

        item_values = self.tree.item(selected_item[0])['values']
        item_id = item_values[0]
        descricao = item_values[1]

        confirm = messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir permanentemente o item:\n\nID {item_id}: {descricao}?")
        if confirm:
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}")
                if res.status_code == 200:
                    messagebox.showinfo("Excluído", "Objeto removido do sistema!")
                    self.limpar_formulario()
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", "Não foi possível excluir o item.")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Falha ao conectar: {e}")

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens")
            if res.status_code == 200:
                itens = res.json()
                self.itens_cache = {}
                for i in itens:
                    self.itens_cache[i["id"]] = i
                    aluno_info = f"{i['solicitado_por']} (RM: {i['rm_aluno']})" if i['solicitado_por'] else "-"
                    self.tree.insert("", tk.END, values=(
                        i["id"], 
                        i["txt_descricao"], 
                        i["categoria"], 
                        i["txt_data"], 
                        i["txt_local"], 
                        i["status"],
                        aluno_info
                    ))
        except Exception as e:
            print("Erro ao carregar tabela:", e)

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()