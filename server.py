```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import base64
from datetime import datetime

# Lembre-se de alterar para a URL real do seu app no Render!
API_URL = "https://achados-etec-api.onrender.com"

class AdminDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Achados e Perdidos | Administração / Secretaria")
        self.root.geometry("1020x720")
        self.root.configure(bg="#1e1e2e")
        
        self.foto_base64 = ""
        self.item_id_em_edicao = None

        # Estilização
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#2d3748", foreground="#ffffff", fieldbackground="#2d3748", rowheight=28)
        style.configure("Treeview.Heading", background="#1e293b", foreground="#38bdf8", font=("Helvetica", 10, "bold"))
        style.map("Treeview", background=[('selected', '#2563eb')])

        # Cabeçalho
        header = tk.Frame(self.root, bg="#0f172a", height=70)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(header, text="SECRETARIA - BANCO DE DADOS NEON (POSTGRESQL)", 
                             font=("Helvetica", 14, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(pady=8)
        lbl_sub = tk.Label(header, text="ETEC Prof.º José Ignácio Azevedo Filho", 
                           font=("Helvetica", 9), bg="#0f172a", fg="#94a3b8")
        lbl_sub.pack()

        # Container Principal
        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Formulário Lado Esquerdo
        self.form_frame = tk.LabelFrame(container, text=" Cadastro / Edição de Objeto ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=15, pady=15)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Descrição
        tk.Label(self.form_frame, text="Descrição do Item:", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w", pady=(5,2))
        self.txt_descricao = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Categoria
        tk.Label(self.form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w", pady=(5,2))
        self.cb_categoria = ttk.Combobox(self.form_frame, values=["MOCHILA", "ROUPAS", "ACESSÓRIOS", "ESCOLARES", "OUTROS"], state="readonly", width=30)
        self.cb_categoria.current(0)
        self.cb_categoria.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Data
        tk.Label(self.form_frame, text="Data Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w", pady=(5,2))
        self.txt_data = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Local
        tk.Label(self.form_frame, text="Local Encontrado:", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w", pady=(5,2))
        self.txt_local = tk.Entry(self.form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Status
        tk.Label(self.form_frame, text="Status:", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w", pady=(5,2))
        self.cb_status = ttk.Combobox(self.form_frame, values=["Disponível", "Solicitado", "Entregue"], state="readonly", width=30)
        self.cb_status.current(0)
        self.cb_status.grid(row=9, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Foto
        tk.Label(self.form_frame, text="Foto do Objeto:", bg="#1e1e2e", fg="#e2e8f0").grid(row=10, column=0, sticky="w", pady=(5,2))
        btn_foto = tk.Button(self.form_frame, text="📷 Carregar Foto...", command=self.carregar_foto, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.grid(row=11, column=0, sticky="w", pady=(0, 10))
        
        self.lbl_status_foto = tk.Label(self.form_frame, text="Sem foto", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.grid(row=11, column=1, sticky="w", padx=5)

        # Botão Salvar
        self.btn_cadastrar = tk.Button(self.form_frame, text="✔ Gravar no Banco Nuvem", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        self.btn_cadastrar.grid(row=12, column=0, columnspan=2, fill="x", pady=(15, 5))

        self.btn_cancelar = tk.Button(self.form_frame, text="✖ Cancelar Edição", command=self.limpar_formulario, bg="#64748b", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        self.btn_cancelar.grid(row=13, column=0, columnspan=2, fill="x")

        # Tabela Lado Direito
        table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "data", "local", "status", "solicitado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")
        self.tree.heading("solicitado", text="Solicitado Por")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("descricao", width=140)
        self.tree.column("data", width=80, anchor="center")
        self.tree.column("local", width=90)
        self.tree.column("status", width=85, anchor="center")
        self.tree.column("solicitado", width=110)

        self.tree.pack(fill="both", expand=True)

        # Botões da Tabela
        btn_action_frame = tk.Frame(table_frame, bg="#1e1e2e")
        btn_action_frame.pack(fill="x", pady=(8, 0))

        btn_editar = tk.Button(btn_action_frame, text="✏ Editar", command=self.carregar_para_edicao, bg="#eab308", fg="#000000", font=("Helvetica", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2")
        btn_editar.pack(side="left", padx=(0, 5))

        btn_excluir = tk.Button(btn_action_frame, text="🗑 Excluir", command=self.excluir_item, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2")
        btn_excluir.pack(side="left", padx=5)

        btn_refresh = tk.Button(btn_action_frame, text="🔄 Sincronizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat", padx=10, pady=4)
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
                    self.lbl_status_foto.config(text="✓ Foto Pronta", fg="#4ade80")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar imagem: {e}")

    def carregar_para_edicao(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item na tabela para editar!")
            return

        item_values = self.tree.item(selected[0])['values']
        item_id = item_values[0]
        item = self.itens_cache.get(item_id)
        if not item:
            return

        self.item_id_em_edicao = item_id
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
        self.lbl_status_foto.config(text="✓ Foto Mantida" if self.foto_base64 else "Sem foto", fg="#4ade80" if self.foto_base64 else "#94a3b8")

        self.form_frame.config(text=f" Editando ID {item_id} ")
        self.btn_cadastrar.config(text="💾 Salvar Alterações", bg="#eab308", fg="#000000")

    def limpar_formulario(self):
        self.item_id_em_edicao = None
        self.txt_descricao.delete(0, tk.END)
        self.txt_local.delete(0, tk.END)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.cb_categoria.current(0)
        self.cb_status.current(0)
        self.foto_base64 = ""
        self.lbl_status_foto.config(text="Sem foto", fg="#94a3b8")
        self.form_frame.config(text=" Cadastro / Edição de Objeto ")
        self.btn_cadastrar.config(text="✔ Gravar no Banco Nuvem", bg="#16a34a", fg="white")

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
                res = requests.put(f"{API_URL}/api/itens/{self.item_id_em_edicao}", json=payload, timeout=10)
                msg = "Item alterado com sucesso no Neon!"
            else:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                msg = "Registrado no Neon PostgreSQL com sucesso!"

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", msg)
                self.limpar_formulario()
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor: {res.text}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def excluir_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item na tabela para excluir!")
            return

        item_values = self.tree.item(selected[0])['values']
        item_id = item_values[0]

        if messagebox.askyesno("Confirmar Exclusão", f"Deseja excluir permanentemente o item ID {item_id}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Excluído", "Item removido do Neon PostgreSQL!")
                    self.limpar_formulario()
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", "Não foi possível excluir.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha de conexão: {e}")

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens", timeout=10)
            if res.status_code == 200:
                itens = res.json()
                self.itens_cache = {}
                for i in itens:
                    self.itens_cache[i["id"]] = i
                    solicitado = f"{i['solicitado_por']} (RM:{i['rm_aluno']})" if i.get('solicitado_por') else "-"
                    self.tree.insert("", tk.END, values=(i["id"], i["txt_descricao"], i["txt_data"], i["txt_local"], i["status"], solicitado))
        except Exception as e:
            print(f"Aguardando conexão com a API... {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()
```
