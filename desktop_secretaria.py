import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import base64
from datetime import datetime

# Substitua pela URL final do seu backend (ex: no Render)
API_URL = "https://SEU-APP-NO-RENDER.onrender.com"

class AdminDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Achados e Perdidos | Administração / Secretaria")
        self.root.geometry("950x680")
        self.root.configure(bg="#1e1e2e")
        
        self.foto_base64 = ""

        # Estilização Tkinter
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

        # Painel Principal
        container = tk.Frame(self.root, bg="#1e1e2e")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Formulário Lado Esquerdo
        form_frame = tk.LabelFrame(container, text=" Cadastro de Objeto Encontrado ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=15, pady=15)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Campo: Descrição (txt_descricao)
        tk.Label(form_frame, text="Descrição do Item (txt_descricao):", bg="#1e1e2e", fg="#e2e8f0").grid(row=0, column=0, sticky="w", pady=(5,2))
        self.txt_descricao = tk.Entry(form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_descricao.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Categoria
        tk.Label(form_frame, text="Categoria:", bg="#1e1e2e", fg="#e2e8f0").grid(row=2, column=0, sticky="w", pady=(5,2))
        self.cb_categoria = ttk.Combobox(form_frame, values=["MOCHILA", "ROUPAS", "ACESSÓRIOS", "ESCOLARES", "OUTROS"], state="readonly", width=30)
        self.cb_categoria.current(0)
        self.cb_categoria.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Data (txt_data)
        tk.Label(form_frame, text="Data Encontrado (txt_data):", bg="#1e1e2e", fg="#e2e8f0").grid(row=4, column=0, sticky="w", pady=(5,2))
        self.txt_data = tk.Entry(form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.grid(row=5, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Local (txt_local)
        tk.Label(form_frame, text="Local Encontrado (txt_local):", bg="#1e1e2e", fg="#e2e8f0").grid(row=6, column=0, sticky="w", pady=(5,2))
        self.txt_local = tk.Entry(form_frame, width=32, font=("Helvetica", 11), bg="#334155", fg="#ffffff", insertbackground="white")
        self.txt_local.grid(row=7, column=0, columnspan=2, pady=(0, 10), sticky="w")

        # Campo: Foto (foto)
        tk.Label(form_frame, text="Foto do Objeto (foto):", bg="#1e1e2e", fg="#e2e8f0").grid(row=8, column=0, sticky="w", pady=(5,2))
        btn_foto = tk.Button(form_frame, text="📷 Carregar Foto...", command=self.carregar_foto, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.grid(row=9, column=0, sticky="w", pady=(0, 10))
        
        self.lbl_status_foto = tk.Label(form_frame, text="Sem foto", bg="#1e1e2e", fg="#94a3b8", font=("Helvetica", 9, "italic"))
        self.lbl_status_foto.grid(row=9, column=1, sticky="w", padx=5)

        # Botão Enviar
        btn_cadastrar = tk.Button(form_frame, text="✔ Gravar no Banco Nuvem", command=self.cadastrar_item, bg="#16a34a", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10, pady=8, cursor="hand2")
        btn_cadastrar.grid(row=10, column=0, columnspan=2, fill="x", pady=(15, 0))

        # Tabela Lado Direito
        table_frame = tk.LabelFrame(container, text=" Registros no Neon PostgreSQL ", bg="#1e1e2e", fg="#38bdf8", font=("Helvetica", 11, "bold"), padx=10, pady=10)
        table_frame.grid(row=0, column=1, sticky="nsew")

        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        columns = ("id", "descricao", "data", "local", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("descricao", width=190)
        self.tree.column("data", width=85, anchor="center")
        self.tree.column("local", width=110)
        self.tree.column("status", width=95, anchor="center")

        self.tree.pack(fill="both", expand=True)

        btn_refresh = tk.Button(table_frame, text="🔄 Sincronizar / Atualizar", command=self.carregar_tabela, bg="#334155", fg="white", font=("Helvetica", 9), relief="flat")
        btn_refresh.pack(fill="x", pady=(8, 0))

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

    def cadastrar_item(self):
        descricao = self.txt_descricao.get().strip()
        data = self.txt_data.get().strip()
        local = self.txt_local.get().strip()
        categoria = self.cb_categoria.get()

        if not descricao or not data or not local:
            messagebox.showwarning("Atenção!", "Preencha todos os campos obrigatórios!")
            return

        payload = {
            "descricao": descricao,
            "categoria": categoria,
            "data": data,
            "local": local,
            "foto": self.foto_base64
        }

        try:
            res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
            if res.status_code == 200:
                messagebox.showinfo("Sucesso", "Registrado no PostgreSQL Neon!")
                self.txt_descricao.delete(0, tk.END)
                self.txt_local.delete(0, tk.END)
                self.foto_base64 = ""
                self.lbl_status_foto.config(text="Sem foto", fg="#94a3b8")
                self.carregar_tabela()
            else:
                messagebox.showerror("Erro", f"Falha no servidor: {res.text}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar à API: {e}")

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens", timeout=10)
            if res.status_code == 200:
                itens = res.json()
                for i in itens:
                    self.tree.insert("", tk.END, values=(i["id"], i["txt_descricao"], i["txt_data"], i["txt_local"], i["status"]))
        except Exception as e:
            print(f"Aguardando conexão... {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AdminDesktopApp(root)
    root.mainloop()