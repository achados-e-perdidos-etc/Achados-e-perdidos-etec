import os
import json
import base64
import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
from datetime import datetime

# Configuração da URL da API
API_URL = os.environ.get("API_URL", "https://achados-e-perdidos-etec.vercel.app/")

class AchadosPerdidosApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Achados e Perdidos - ETEC Profº José Ignácio Azevedo Filho")
        self.root.geometry("1100x700")
        self.root.configure(bg="#0f172a")

        self.item_editando_id = None
        self.fotos_base64 = []

        self.setup_ui()
        self.carregar_tabela()

    def setup_ui(self):
        # Título Principal
        header_frame = tk.Frame(self.root, bg="#1e293b", height=60)
        header_frame.pack(fill="x", side="top")
        
        lbl_titulo = tk.Label(
            header_frame, 
            text="📦 Painel de Controle - Achados e Perdidos", 
            font=("Helvetica", 16, "bold"), 
            bg="#1e293b", 
            fg="#f8fafc"
        )
        lbl_titulo.pack(side="left", padx=20, pady=15)

        # Container Principal
        main_container = tk.Frame(self.root, bg="#0f172a")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Painel Esquerdo: Formulário
        form_frame = tk.LabelFrame(main_container, text=" Cadastro / Edição ", font=("Helvetica", 11, "bold"), bg="#1e293b", fg="#38bdf8", bd=1, relief="solid")
        form_frame.pack(side="left", fill="y", padx=(0, 15), ipadx=10, ipady=10)

        # Descrição
        tk.Label(form_frame, text="Descrição do Item *", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.txt_descricao = tk.Entry(form_frame, bg="#334155", fg="#ffffff", insertbackground="white", relief="flat", font=("Helvetica", 10))
        self.txt_descricao.pack(fill="x", padx=10, ipady=5)

        # Categoria
        tk.Label(form_frame, text="Categoria *", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.cb_categoria = ttk.Combobox(form_frame, values=["Eletrônicos", "Documentos", "Roupas / Agasalhos", "Material Escolar", "Chaves", "Garrafas / Marmitas", "Acessórios / Bijuterias", "Outros"], state="readonly")
        self.cb_categoria.current(0)
        self.cb_categoria.pack(fill="x", padx=10, ipady=3)

        # Data Encontrado
        tk.Label(form_frame, text="Data Encontrado *", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.txt_data = tk.Entry(form_frame, bg="#334155", fg="#ffffff", insertbackground="white", relief="flat", font=("Helvetica", 10))
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_data.pack(fill="x", padx=10, ipady=5)

        # Local Encontrado
        tk.Label(form_frame, text="Local Encontrado *", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.txt_local = tk.Entry(form_frame, bg="#334155", fg="#ffffff", insertbackground="white", relief="flat", font=("Helvetica", 10))
        self.txt_local.pack(fill="x", padx=10, ipady=5)

        # Status
        tk.Label(form_frame, text="Status *", bg="#1e293b", fg="#94a3b8", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        self.cb_status = ttk.Combobox(form_frame, values=["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO", "DOAÇÃO FEITA"], state="readonly")
        self.cb_status.current(0)
        self.cb_status.pack(fill="x", padx=10, ipady=3)

        # Seleção de Fotos
        btn_foto = tk.Button(form_frame, text="📷 Adicionar Fotos", command=self.carregar_fotos, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_foto.pack(fill="x", padx=10, pady=(15, 5), ipady=5)

        self.lbl_fotos_status = tk.Label(form_frame, text="Nenhuma foto anexada", bg="#1e293b", fg="#64748b", font=("Helvetica", 8))
        self.lbl_fotos_status.pack(anchor="w", padx=10)

        # Botões do Formulário
        self.btn_salvar = tk.Button(form_frame, text="💾 Salvar Item", command=self.salvar_item, bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2")
        self.btn_salvar.pack(fill="x", padx=10, pady=(20, 5), ipady=7)

        self.btn_limpar = tk.Button(form_frame, text="🧹 Limpar / Novo", command=self.limpar_formulario, bg="#475569", fg="white", font=("Helvetica", 9), relief="flat", cursor="hand2")
        self.btn_limpar.pack(fill="x", padx=10, ipady=5)

        # Painel Direito: Tabela e Ações Gerais
        table_frame = tk.Frame(main_container, bg="#0f172a")
        table_frame.pack(side="right", fill="both", expand=True)

        # Barra de Ações do Topo da Tabela
        top_actions = tk.Frame(table_frame, bg="#0f172a")
        top_actions.pack(fill="x", pady=(0, 10))

        btn_atualizar = tk.Button(top_actions, text="🔄 Atualizar Lista", command=self.carregar_tabela, bg="#0284c7", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_atualizar.pack(side="left")

        btn_concluir_doacoes = tk.Button(top_actions, text="🗑️ Limpar Itens Doados", command=self.concluir_doacoes, bg="#dc2626", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_concluir_doacoes.pack(side="right")

        # Configuração da Tabela Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1e293b", foreground="#f8fafc", fieldbackground="#1e293b", rowheight=30)
        style.configure("Treeview.Heading", background="#334155", foreground="#38bdf8", font=("Helvetica", 9, "bold"))
        style.map("Treeview", background=[("selected", "#0284c7")])

        colunas = ("id", "descricao", "categoria", "data", "local", "status", "solicitado_por", "rm_aluno")
        self.tree = ttk.Treeview(table_frame, columns=colunas, show="headings")

        self.tree.heading("id", text="ID")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("data", text="Data")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")
        self.tree.heading("solicitado_por", text="Solicitado Por")
        self.tree.heading("rm_aluno", text="RM/Doc")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("descricao", width=180)
        self.tree.column("categoria", width=110)
        self.tree.column("data", width=90, anchor="center")
        self.tree.column("local", width=110)
        self.tree.column("status", width=110, anchor="center")
        self.tree.column("solicitado_por", width=130)
        self.tree.column("rm_aluno", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.on_item_double_click)

        # Barra de Botões Ação para Item Selecionado
        bottom_actions = tk.Frame(table_frame, bg="#0f172a")
        bottom_actions.pack(fill="x", pady=(10, 0))

        btn_editar = tk.Button(bottom_actions, text="✏️ Editar Selecionado", command=self.carregar_item_selecionado, bg="#eab308", fg="#0f172a", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_editar.pack(side="left", padx=(0, 5))

        btn_comprovante = tk.Button(bottom_actions, text="📄 Gerar Comprovante", command=self.gerar_comprovante_selecionado, bg="#8b5cf6", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_comprovante.pack(side="left", padx=5)

        btn_excluir = tk.Button(bottom_actions, text="❌ Excluir Item", command=self.excluir_item_selecionado, bg="#b91c1c", fg="white", font=("Helvetica", 9, "bold"), relief="flat", cursor="hand2")
        btn_excluir.pack(side="right")

    def carregar_fotos(self):
        caminhos = filedialog.askopenfilenames(
            title="Selecione as imagens do item",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")]
        )
        if caminhos:
            self.fotos_base64 = []
            for cam in caminhos:
                try:
                    with open(cam, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                        self.fotos_base64.append(f"data:image/jpeg;base64,{b64}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao carregar imagem {cam}: {e}")
            self.lbl_fotos_status.config(text=f"{len(self.fotos_base64)} foto(s) selecionada(s)", fg="#38bdf8")

    def salvar_item(self):
        descricao = self.txt_descricao.get().strip()
        categoria = self.cb_categoria.get()
        data = self.txt_data.get().strip()
        local = self.txt_local.get().strip()
        status = self.cb_status.get()

        if not descricao or not data or not local:
            messagebox.showwarning("Atenção!", "Preencha todos os campos obrigatórios!")
            return

        solicitado_por = None
        rm_aluno = None

        # Se alterar/salvar o status como ENTREGUE, obriga o preenchimento das informações
        if status.upper() == "ENTREGUE":
            solicitado_por = simpledialog.askstring("Dados do Retirante", "Nome completo de quem retirou o item:", parent=self.root)
            if not solicitado_por:
                messagebox.showwarning("Atenção", "O nome do retirante é obrigatório para o status ENTREGUE!")
                return

            rm_aluno = simpledialog.askstring("Dados do Retirante", "RM ou Documento de identificação do retirante:", parent=self.root)
            if not rm_aluno:
                messagebox.showwarning("Atenção", "O RM/Documento é obrigatório para o status ENTREGUE!")
                return

        payload = {
            "descricao": descricao,
            "categoria": categoria,
            "data": data,
            "local": local,
            "status": status,
            "fotos": self.fotos_base64,
            "solicitado_por": solicitado_por,
            "rm_aluno": rm_aluno
        }

        try:
            if self.item_editando_id is None:
                res = requests.post(f"{API_URL}/api/itens", json=payload, timeout=10)
                msg_sucesso = "Registrado no PostgreSQL Neon!"
            else:
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

    def carregar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            res = requests.get(f"{API_URL}/api/itens", timeout=10)
            if res.status_code == 200:
                itens = res.json()
                for item in itens:
                    self.tree.insert("", "end", values=(
                        item.get("id"),
                        item.get("txt_descricao"),
                        item.get("categoria", "N/A"),
                        item.get("txt_data"),
                        item.get("txt_local"),
                        item.get("status", "DISPONÍVEL"),
                        item.get("solicitado_por") or "-",
                        item.get("rm_aluno") or "-"
                    ))
            else:
                messagebox.showerror("Erro", f"Não foi possível buscar a lista de itens. Código: {res.status_code}")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Falha ao conectar na API: {e}")

    def carregar_item_selecionado(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item da tabela para editar!")
            return

        item_values = self.tree.item(selected[0], "values")
        self.item_editando_id = item_values[0]

        self.txt_descricao.delete(0, tk.END)
        self.txt_descricao.insert(0, item_values[1])

        self.cb_categoria.set(item_values[2])

        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, item_values[3])

        self.txt_local.delete(0, tk.END)
        self.txt_local.insert(0, item_values[4])

        self.cb_status.set(item_values[5])

        self.btn_salvar.config(text=f"🔄 Atualizar Item #{self.item_editando_id}", bg="#eab308", fg="#0f172a")

    def limpar_formulario(self):
        self.item_editando_id = None
        self.txt_descricao.delete(0, tk.END)
        self.cb_categoria.current(0)
        self.txt_data.delete(0, tk.END)
        self.txt_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_local.delete(0, tk.END)
        self.cb_status.current(0)
        self.fotos_base64 = []
        self.lbl_fotos_status.config(text="Nenhuma foto anexada", fg="#64748b")
        self.btn_salvar.config(text="💾 Salvar Item", bg="#16a34a", fg="white")

    def excluir_item_selecionado(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item da tabela para excluir!")
            return

        item_values = self.tree.item(selected[0], "values")
        item_id = item_values[0]

        if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja excluir permanentemente o Item #{item_id}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", timeout=10)
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", f"Item #{item_id} excluído com sucesso!")
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Erro ao excluir o item: {res.text}")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Falha ao comunicar com a API: {e}")

    def concluir_doacoes(self):
        if messagebox.askyesno("Confirmar Limpeza", "Deseja remover do sistema todos os itens marcados como 'DOAÇÃO FEITA'?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/doacoes/concluir", timeout=10)
                if res.status_code == 200:
                    dados = res.json()
                    messagebox.showinfo("Sucesso", dados.get("message", "Concluído!"))
                    self.carregar_tabela()
                else:
                    messagebox.showerror("Erro", f"Erro ao executar ação: {res.text}")
            except Exception as e:
                messagebox.showerror("Erro de Conexão", f"Falha de comunicação: {e}")

    def on_item_double_click(self, event):
        self.carregar_item_selecionado()

    def gerar_comprovante_selecionado(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Atenção", "Selecione um item na tabela para gerar o comprovante!")
            return

        item_values = self.tree.item(selected[0], "values")
        item_data = {
            "id": item_values[0],
            "txt_descricao": item_values[1],
            "categoria": item_values[2],
            "txt_data": item_values[3],
            "txt_local": item_values[4],
            "status": item_values[5],
            "solicitado_por": item_values[6],
            "rm_aluno": item_values[7]
        }
        self.gerar_comprovante_retirada(item_data)

    def gerar_comprovante_retirada(self, item):
        solicitante = item.get('solicitado_por')
        rm = item.get('rm_aluno')

        # Solicita preenchimento caso o item ainda não tenha os dados cadastrados
        if not solicitante or solicitante == "-":
            solicitante = simpledialog.askstring("Comprovante", "Nome Completo do Retirante:", parent=self.root) or "Não informado"
        if not rm or rm == "-":
            rm = simpledialog.askstring("Comprovante", "RM ou Documento do Retirante:", parent=self.root) or "Não informado"

        comprovante = f"""==================================================
        ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO
           TERMO DE RETIRADA DE ACHADOS E PERDIDOS
==================================================
ID do Item: #{item['id']}
Descrição: {item['txt_descricao']}
Categoria: {item.get('categoria', 'N/A')}
Local Encontrado: {item['txt_local']}
Data de Registro: {item['txt_data']}

--------------------------------------------------
DADOS DO RETIRANTE:
Nome Completo: {solicitante}
RM/Documento: {rm}
Data de Devolução: {datetime.now().strftime("%d/%m/%Y às %H:%M")}

Declaro ter recebido o objeto acima descrito em devidas condições.

__________________________________________________
Assinatura do Aluno/Responsável

--------------------------------------------------
DADOS DO ATENDIMENTO:
Funcionário Responsável: ___________________________

__________________________________________________
Assinatura do Funcionário/Secretaria
=================================================="""
        
        comp_win = tk.Toplevel(self.root)
        comp_win.title(f"Comprovante de Retirada - Item #{item['id']}")
        comp_win.geometry("500x520")
        comp_win.configure(bg="#1e1e2e")
        comp_win.resizable(False, False)

        txt = tk.Text(comp_win, bg="#0f172a", fg="#38bdf8", font=("Courier", 9), padx=10, pady=10)
        txt.pack(fill="both", expand=True, padx=15, pady=(15, 10))
        txt.insert("1.0", comprovante)
        txt.config(state="disabled")

        btn_frame = tk.Frame(comp_win, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        btn_baixar = tk.Button(btn_frame, text="💾 Baixar Comprovante (.txt)", command=lambda: self.salvar_comprovante_arquivo(item['id'], comprovante), bg="#16a34a", fg="white", font=("Helvetica", 10, "bold"), relief="flat", pady=8, cursor="hand2")
        btn_baixar.pack(fill="x")

    def salvar_comprovante_arquivo(self, item_id, conteudo):
        caminho = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"comprovante_item_{item_id}.txt",
            filetypes=[("Arquivo de Texto", "*.txt")]
        )
        if caminho:
            try:
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                messagebox.showinfo("Sucesso", f"Comprovante salvo em:\n{caminho}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar o arquivo: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AchadosPerdidosApp(root)
    root.mainloop()
