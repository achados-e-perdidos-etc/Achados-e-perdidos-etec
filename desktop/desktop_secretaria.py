import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import base64
import io
from PIL import Image, ImageTk
import hashlib
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DA API
# ==========================================
API_URL = "https://achados-etec-api.onrender.com"

# Hashes de Segurança
HASH_EMAIL = "7547c4fd75b0c4cf47ee844f1c6c00f1e77b95b261edb083dfc9a08cd7cf22cd"
HASH_SENHA = "4a20e32e157a100f269d27cb60696b5b8fe17829c0305283de04fdb0094cec5c"

# ==========================================
# CLASSE PRINCIPAL DO APLICATIVO
# ==========================================
class SecretariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Painel Desktop da Secretaria")
        self.root.geometry("1000x700")
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

        btn_entrar = tk.Button(self.frame_login, text="ENTRAR", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), relief="flat", command=self.verificar_login)
        btn_entrar.pack(pady=20, fill="x", padx=50)

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

        self.tab_itens = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_categorias = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_entregues = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_chat = tk.Frame(self.notebook, bg="#0d1117")

        self.notebook.add(self.tab_itens, text="Gerenciar Itens")
        self.notebook.add(self.tab_categorias, text="Categorias")
        self.notebook.add(self.tab_entregues, text="Histórico de Entregas")
        self.notebook.add(self.tab_chat, text="Chat c/ Alunos")

        self.construir_tab_itens()
        self.construir_tab_categorias()
        self.construir_tab_entregues()
        self.construir_tab_chat()

        self.carregar_dados()

    def carregar_dados(self):
        self.carregar_categorias()
        self.carregar_itens()
        self.carregar_entregues()
        self.carregar_conversas()

    # --- TAB: ITENS ---
    def construir_tab_itens(self):
        frame_top = tk.Frame(self.tab_itens, bg="#0d1117")
        frame_top.pack(fill="x", pady=10)

        tk.Button(frame_top, text="🔄 Atualizar Lista", bg="#1f6feb", fg="white", command=self.carregar_itens).pack(side="left", padx=5)
        
        # Tabela (Treeview)
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Local")
        self.tree_itens = ttk.Treeview(self.tab_itens, columns=colunas, show="headings", height=15)
        for col in colunas:
            self.tree_itens.heading(col, text=col)
            self.tree_itens.column(col, anchor="center")
        
        self.tree_itens.column("ID", width=50)
        self.tree_itens.column("Nome / Descrição", width=300)
        self.tree_itens.pack(fill="both", expand=True, pady=5)

        # EVENTO DE DUPLO CLIQUE PARA ABRIR O MODAL DE FOTOS
        self.tree_itens.bind("<Double-1>", self.abrir_modal_detalhes_item)

        tk.Label(self.tab_itens, text="Dê um duplo-clique em um item da lista para visualizar as fotos e detalhes.", bg="#0d1117", fg="#8b949e", font=("Arial", 9, "italic")).pack(pady=5)

    def carregar_itens(self):
        try:
            res = requests.get(f"{API_URL}/api/itens")
            if res.status_code == 200:
                self.itens_atuais = res.json()
                self.tree_itens.delete(*self.tree_itens.get_children())
                for i in self.itens_atuais:
                    nome_desc = i.get('nome') or i.get('txt_descricao')
                    self.tree_itens.insert("", "end", values=(i['id'], nome_desc, i['categoria'], i['status'], i.get('txt_local', '')))
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível carregar os itens: {e}")

    # ==========================================
    # MODAL DE DETALHES E MULTI-FOTOS (DOUBLE CLICK)
    # ==========================================
    def abrir_modal_detalhes_item(self, event):
        selecionado = self.tree_itens.selection()
        if not selecionado: return
        item_id = self.tree_itens.item(selecionado[0])['values'][0]

        item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
        if not item: return

        # Janela Toplevel
        modal = tk.Toplevel(self.root)
        modal.title(f"Detalhes do Item #{item['id']}")
        modal.geometry("750x600")
        modal.configure(bg="#0d1117")
        modal.transient(self.root) # Mantém sobre a janela principal

        nome_titulo = item.get('nome') or item.get('txt_descricao')
        tk.Label(modal, text=nome_titulo, font=("Arial", 16, "bold"), bg="#0d1117", fg="#f87171").pack(pady=10)

        # Frame de Informações
        frame_info = tk.Frame(modal, bg="#161b22", bd=1, relief="solid")
        frame_info.pack(fill="x", padx=20, pady=5)

        info_texto = f"CATEGORIA: {item.get('categoria', '')}   |   STATUS: {item.get('status', '')}\n\n"
        info_texto += f"LOCAL ENCONTRADO: {item.get('txt_local', '')}\n"
        info_texto += f"DATA: {item.get('txt_data', '')}\n"
        info_texto += f"DESCRIÇÃO: {item.get('txt_descricao', '')}\n"

        if item.get('solicitado_por'):
            info_texto += f"\n🚨 SOLICITADO POR: {item.get('solicitado_por')} (RM: {item.get('rm_aluno', '')})"

        tk.Label(frame_info, text=info_texto, justify="left", bg="#161b22", fg="#c9d1d9", font=("Arial", 11)).pack(padx=15, pady=10, anchor="w")

        # Frame da Galeria de Fotos
        tk.Label(modal, text="Fotos do Item:", font=("Arial", 12, "bold"), bg="#0d1117", fg="#c9d1d9").pack(pady=10, anchor="w", padx=20)
        
        frame_fotos = tk.Frame(modal, bg="#0d1117")
        frame_fotos.pack(fill="both", expand=True, padx=20)

        # Carregamento e renderização das fotos Base64
        fotos_array = []
        if item.get('fotos'):
            fotos_array = item['fotos']
        elif item.get('fotos_json'):
            try: fotos_array = json.loads(item['fotos_json'])
            except: pass
        if not fotos_array and item.get('foto'):
            fotos_array = [item['foto']]

        if not fotos_array:
            tk.Label(frame_fotos, text="Nenhuma foto registrada para este item.", bg="#0d1117", fg="#8b949e").pack(pady=20)
        else:
            for col, foto_b64 in enumerate(fotos_array):
                try:
                    if foto_b64.startswith("data:image"):
                        foto_b64 = foto_b64.split(",")[1]
                    
                    img_data = base64.b64decode(foto_b64)
                    img = Image.open(io.BytesIO(img_data))
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)

                    lbl_img = tk.Label(frame_fotos, image=img_tk, bg="#161b22", bd=2, relief="solid")
                    lbl_img.image = img_tk # Previne Garbage Collection
                    lbl_img.grid(row=0, column=col, padx=10, pady=5)
                except Exception as e:
                    print(f"Erro ao exibir foto: {e}")

        # Frame de Botões de Ação no Modal
        frame_acoes = tk.Frame(modal, bg="#0d1117")
        frame_acoes.pack(fill="x", pady=20, padx=20)

        if item.get('status') == 'SOLICITADO':
            tk.Button(frame_acoes, text="🚫 Recusar Solicitação", bg="#d97706", fg="white", font=("Arial", 10, "bold"), command=lambda: self.recusar_solicitacao(item['id'], modal)).pack(side="left", padx=5, fill="x", expand=True)

        if item.get('status') != 'ENTREGUE':
            tk.Button(frame_acoes, text="✅ Dar Baixa (Entrega)", bg="#059669", fg="white", font=("Arial", 10, "bold"), command=lambda: self.abrir_dar_baixa(item, modal)).pack(side="left", padx=5, fill="x", expand=True)

        tk.Button(frame_acoes, text="🗑️ Excluir Item", bg="#991b1b", fg="white", font=("Arial", 10, "bold"), command=lambda: self.excluir_item(item['id'], modal)).pack(side="left", padx=5, fill="x", expand=True)

    # --- AÇÕES DO ITEM ---
    def recusar_solicitacao(self, item_id, modal):
        if messagebox.askyesno("Recusar", "Deseja recusar a solicitação e voltar o item para DISPONÍVEL?"):
            try:
                res = requests.put(f"{API_URL}/api/itens/{item_id}/recusar")
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Solicitação recusada!")
                    modal.destroy()
                    self.carregar_itens()
            except Exception as e: messagebox.showerror("Erro", str(e))

    def abrir_dar_baixa(self, item, modal_detalhes):
        modal_baixa = tk.Toplevel(self.root)
        modal_baixa.title(f"Dar Baixa - Item #{item['id']}")
        modal_baixa.geometry("400x350")
        modal_baixa.configure(bg="#0d1117")

        tk.Label(modal_baixa, text="Registrar Entrega", font=("Arial", 14, "bold"), bg="#0d1117", fg="#10b981").pack(pady=15)

        tk.Label(modal_baixa, text="Nome do Aluno:", bg="#0d1117", fg="white").pack()
        entry_nome = ttk.Entry(modal_baixa, width=40)
        entry_nome.insert(0, item.get('solicitado_por', ''))
        entry_nome.pack(pady=5)

        tk.Label(modal_baixa, text="RM:", bg="#0d1117", fg="white").pack()
        entry_rm = ttk.Entry(modal_baixa, width=40)
        entry_rm.insert(0, item.get('rm_aluno', ''))
        entry_rm.pack(pady=5)

        tk.Label(modal_baixa, text="Turma / Curso:", bg="#0d1117", fg="white").pack()
        entry_turma = ttk.Entry(modal_baixa, width=40)
        entry_turma.pack(pady=5)

        def confirmar():
            payload = {
                "status": "ENTREGUE",
                "retirado_por": entry_nome.get().strip(),
                "rm_retirante": entry_rm.get().strip(),
                "turma_curso": entry_turma.get().strip()
            }
            try:
                res = requests.put(f"{API_URL}/api/itens/{item['id']}", json=payload)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item baixado com sucesso!")
                    modal_baixa.destroy()
                    modal_detalhes.destroy()
                    self.carregar_dados()
            except Exception as e: messagebox.showerror("Erro", str(e))

        tk.Button(modal_baixa, text="Confirmar Entrega", bg="#059669", fg="white", font=("Arial", 10, "bold"), command=confirmar).pack(pady=20)

    def excluir_item(self, item_id, modal):
        if messagebox.askyesno("Excluir", "Deseja excluir este item permanentemente?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}")
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item excluído!")
                    modal.destroy()
                    self.carregar_itens()
            except Exception as e: messagebox.showerror("Erro", str(e))

    # --- TAB: CATEGORIAS ---
    def construir_tab_categorias(self):
        frame_add = tk.Frame(self.tab_categorias, bg="#0d1117")
        frame_add.pack(pady=20)

        tk.Label(frame_add, text="Nova Categoria:", bg="#0d1117", fg="white").pack(side="left", padx=5)
        self.entry_cat = ttk.Entry(frame_add, width=30)
        self.entry_cat.pack(side="left", padx=5)
        tk.Button(frame_add, text="Adicionar", bg="#dc2626", fg="white", command=self.adicionar_categoria).pack(side="left", padx=5)

        self.listbox_cats = tk.Listbox(self.tab_categorias, bg="#161b22", fg="white", font=("Arial", 12), height=15)
        self.listbox_cats.pack(fill="x", padx=50, pady=10)

    def carregar_categorias(self):
        try:
            res = requests.get(f"{API_URL}/api/categorias")
            if res.status_code == 200:
                self.listbox_cats.delete(0, tk.END)
                for c in res.json():
                    self.listbox_cats.insert(tk.END, c['nome'])
        except Exception as e: pass

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
        colunas = ("Item", "Retirado Por", "RM", "Turma", "Data")
        self.tree_entregues = ttk.Treeview(self.tab_entregues, columns=colunas, show="headings", height=20)
        for col in colunas:
            self.tree_entregues.heading(col, text=col)
            self.tree_entregues.column(col, anchor="center")
        self.tree_entregues.pack(fill="both", expand=True, pady=10, padx=10)

    def carregar_entregues(self):
        try:
            res = requests.get(f"{API_URL}/api/entregues")
            if res.status_code == 200:
                self.tree_entregues.delete(*self.tree_entregues.get_children())
                for e in res.json():
                    self.tree_entregues.insert("", "end", values=(e['nome_item'], e['retirado_por'], e['rm_retirante'], e['turma_curso'], e['data_entrega']))
        except Exception: pass

    # --- TAB: CHAT ---
    def construir_tab_chat(self):
        # Painel Esquerdo (Lista de alunos)
        frame_esq = tk.Frame(self.tab_chat, bg="#0d1117", width=250)
        frame_esq.pack(side="left", fill="y", padx=5, pady=5)
        
        tk.Label(frame_esq, text="Conversas Ativas", bg="#0d1117", fg="white", font=("Arial", 12, "bold")).pack(pady=5)
        self.listbox_chat = tk.Listbox(frame_esq, bg="#161b22", fg="white")
        self.listbox_chat.pack(fill="both", expand=True)
        self.listbox_chat.bind("<<ListboxSelect>>", self.selecionar_conversa)

        # Painel Direito (Mensagens)
        frame_dir = tk.Frame(self.tab_chat, bg="#161b22", bd=1, relief="solid")
        frame_dir.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.lbl_chat_titulo = tk.Label(frame_dir, text="Selecione um aluno para conversar", bg="#161b22", fg="#f87171", font=("Arial", 14, "bold"))
        self.lbl_chat_titulo.pack(pady=10)

        self.txt_mensagens = tk.Text(frame_dir, bg="#0d1117", fg="white", state="disabled", wrap="word")
        self.txt_mensagens.pack(fill="both", expand=True, padx=10, pady=5)

        frame_input = tk.Frame(frame_dir, bg="#161b22")
        frame_input.pack(fill="x", padx=10, pady=10)

        self.entry_chat = ttk.Entry(frame_input, font=("Arial", 12))
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_chat.bind("<Return>", lambda e: self.enviar_mensagem())

        tk.Button(frame_input, text="Enviar", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), command=self.enviar_mensagem).pack(side="right")

        # Inicia Polling
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
                    texto = f"{notif}{c['nome_aluno']} - RM: {c['rm_aluno']}"
                    self.listbox_chat.insert(tk.END, texto)
                    self.mapa_conversas.append(c['rm_aluno'])
        except: pass

    def selecionar_conversa(self, event):
        selecao = self.listbox_chat.curselection()
        if selecao:
            idx = selecao[0]
            self.rm_chat_ativo = self.mapa_conversas[idx]
            nome = self.listbox_chat.get(idx).split(" - RM:")[0].replace("( novas) ", "")
            self.lbl_chat_titulo.config(text=f"Chat com: {nome}")
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

        payload = {
            "rm": self.rm_chat_ativo,
            "nome": "Secretaria ETEC",
            "remetente": "SECRETARIA",
            "mensagem": texto
        }
        try:
            res = requests.post(f"{API_URL}/api/chat/enviar", json=payload)
            if res.status_code == 200:
                self.entry_chat.delete(0, tk.END)
                self.carregar_mensagens_aluno()
        except Exception as e: messagebox.showerror("Erro", str(e))

    def atualizar_chat_continuo(self):
        self.carregar_conversas()
        if self.rm_chat_ativo:
            self.carregar_mensagens_aluno()
        self.chat_timer = self.root.after(3000, self.atualizar_chat_continuo)

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretariaApp(root)
    root.mainloop()
