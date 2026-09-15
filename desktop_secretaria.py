import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import base64
import io
import os
import csv
from PIL import Image, ImageTk, ImageDraw, ImageFont
from datetime import datetime
import qrcode

# ==========================================
# CONFIGURAÇÕES DA API E JWT
# ==========================================
API_URL = "https://etec-achados.up.railway.app"
TOKEN_SECRETARIA = None

class SecretariaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Painel da Secretaria")
        self.root.geometry("1100x750")
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
        self.estilo.configure("Treeview.Heading", background="#21262d", foreground="#ffffff", font=("Arial", 10, "bold"))

        self.tela_login()

    def get_auth_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN_SECRETARIA}"
        }

    def get_auth_headers_get(self):
        return {
            "Authorization": f"Bearer {TOKEN_SECRETARIA}"
        }

    def tela_login(self):
        self.frame_login = tk.Frame(self.root, bg="#0d1117")
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", width=420, height=320)

        tk.Label(self.frame_login, text="Acesso Restrito - Secretaria", font=("Arial", 16, "bold"), bg="#0d1117", fg="#f87171").pack(pady=15)
        tk.Label(self.frame_login, text="Área Administrativa", font=("Arial", 8, "italic"), bg="#0d1117", fg="#10b981").pack(pady=(0, 10))

        tk.Label(self.frame_login, text="E-mail:", bg="#0d1117", fg="#c9d1d9").pack(anchor="w", padx=40)
        self.entry_email = ttk.Entry(self.frame_login, width=35)
        self.entry_email.pack(pady=2, padx=40, fill="x")

        tk.Label(self.frame_login, text="Senha:", bg="#0d1117", fg="#c9d1d9").pack(anchor="w", padx=40, pady=(5,0))
        self.entry_senha = ttk.Entry(self.frame_login, show="*", width=35)
        self.entry_senha.pack(pady=2, padx=40, fill="x")

        self.entry_email.bind("<Return>", lambda e: self.entry_senha.focus())
        self.entry_senha.bind("<Return>", lambda e: self.verificar_login())

        self.btn_entrar = tk.Button(self.frame_login, text="ENTRAR NO SISTEMA", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), relief="flat", command=self.verificar_login)
        self.btn_entrar.pack(pady=20, fill="x", padx=40)
        
        self.entry_email.focus()

    def verificar_login(self):
        global TOKEN_SECRETARIA
        email = self.entry_email.get().strip().lower()
        senha = self.entry_senha.get().strip()

        if not email or not senha:
            return messagebox.showerror("Erro", "Preencha o e-mail e a senha!")

        self.btn_entrar.config(text="CONECTANDO...", state="disabled")
        self.root.update()

        try:
            res = requests.post(f"{API_URL}/api/login", json={"email": email, "senha": senha})
            data = res.json()

            if res.status_code == 200 and data.get("success"):
                TOKEN_SECRETARIA = data.get("token")
                self.frame_login.destroy()
                self.construir_interface_principal()
            else:
                messagebox.showerror("Acesso Negado", data.get("message", "E-mail ou senha incorretos!"))
                self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível falar com o servidor:\n{e}")
            self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")

    def construir_interface_principal(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_dash = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_itens = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_categorias = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_entregues = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_doacoes = tk.Frame(self.notebook, bg="#0d1117")
        self.tab_chat = tk.Frame(self.notebook, bg="#0d1117")

        self.notebook.add(self.tab_dash, text="Dashboard")
        self.notebook.add(self.tab_itens, text="Estoque / Gerenciar")
        self.notebook.add(self.tab_categorias, text="Categorias")
        self.notebook.add(self.tab_entregues, text="Histórico Entregues")
        self.notebook.add(self.tab_doacoes, text="Doações")
        self.notebook.add(self.tab_chat, text="Chat Alunos")

        self.construir_tab_dash()
        self.construir_tab_itens()
        self.construir_tab_categorias()
        self.construir_tab_entregues()
        self.construir_tab_doacoes()
        self.construir_tab_chat()

        self.carregar_dados()

    def carregar_dados(self):
        self.carregar_categorias()
        self.carregar_itens()
        self.carregar_entregues()
        self.carregar_dashboard()
        self.carregar_conversas()
        
    # --- DASHBOARD E RELATÓRIOS ---
    def construir_tab_dash(self):
        tk.Label(self.tab_dash, text="Visão Geral do Sistema", font=("Arial", 18, "bold"), bg="#0d1117", fg="#f87171").pack(pady=20)
        frame_cards = tk.Frame(self.tab_dash, bg="#0d1117")
        frame_cards.pack(pady=20)
        
        def criar_card(parent, titulo, cor):
            f = tk.Frame(parent, bg="#161b22", bd=1, relief="solid", width=200, height=120)
            f.pack_propagate(False)
            f.pack(side="left", padx=15)
            tk.Label(f, text=titulo, font=("Arial", 10, "bold"), bg="#161b22", fg="#8b949e").pack(pady=(15,5))
            lbl_valor = tk.Label(f, text="0", font=("Arial", 28, "bold"), bg="#161b22", fg=cor)
            lbl_valor.pack()
            return lbl_valor

        self.lbl_stat_itens = criar_card(frame_cards, "TOTAL DE ITENS", "#3b82f6")
        self.lbl_stat_entregues = criar_card(frame_cards, "ITENS ENTREGUES", "#10b981")
        self.lbl_stat_doacoes = criar_card(frame_cards, "DOAÇÕES", "#f59e0b")

        # Container para os botões do Dashboard
        frame_botoes = tk.Frame(self.tab_dash, bg="#0d1117")
        frame_botoes.pack(pady=30)
        
        tk.Button(frame_botoes, text="Atualizar Dados", bg="#21262d", fg="white", font=("Arial", 10), relief="solid", command=self.carregar_dashboard).pack(side="left", padx=10)
        tk.Button(frame_botoes, text="📊 Exportar Relatório (Excel/CSV)", bg="#10b981", fg="white", font=("Arial", 10, "bold"), relief="flat", command=self.exportar_relatorio).pack(side="left", padx=10)

    def carregar_dashboard(self):
        try:
            res = requests.get(f"{API_URL}/api/estatisticas", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                data = res.json()
                self.lbl_stat_itens.config(text=str(data.get('total_itens', 0)))
                self.lbl_stat_entregues.config(text=str(data.get('total_entregues', 0)))
                self.lbl_stat_doacoes.config(text=str(data.get('total_doacoes', 0)))
        except: pass

    def exportar_relatorio(self):
        if not TOKEN_SECRETARIA: return
        
        # Pede para o usuário escolher onde salvar o arquivo
        nome_sugerido = f"relatorio_achados_etec_{datetime.now().strftime('%Y%m')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=nome_sugerido,
            title="Salvar Relatório",
            filetypes=[("Arquivo CSV (Abre no Excel)", "*.csv")]
        )
        
        if not file_path:
            return # Usuário cancelou a janela de salvar
            
        try:
            # Baixar os dados atualizados para gerar o relatório
            res_itens = requests.get(f"{API_URL}/api/itens", headers=self.get_auth_headers_get())
            if res_itens.status_code != 200:
                messagebox.showerror("Erro", "Não foi possível conectar ao servidor para gerar o relatório.")
                return
                
            itens = res_itens.json()
            
            # Escrever o CSV com formato brasileiro (ponto e vírgula) e suporte a acentos (utf-8-sig)
            with open(file_path, mode='w', newline='', encoding='utf-8-sig') as arquivo_csv:
                escritor = csv.writer(arquivo_csv, delimiter=';')
                
                # Criar o cabeçalho das colunas
                escritor.writerow(['ID do Sistema', 'Nome do Item', 'Descrição', 'Categoria', 'Data Encontrado', 'Local', 'Status', 'Solicitante / Retirado Por', 'RM Aluno'])
                
                # Preencher as linhas com os dados
                for i in itens:
                    id_item = i.get('id', '')
                    nome = i.get('nome') or i.get('txt_descricao') or ''
                    desc = i.get('txt_descricao', '')
                    cat = i.get('categoria', '')
                    data = i.get('txt_data', '')
                    local = i.get('txt_local', '')
                    status = i.get('status', 'DISPONÍVEL').upper()
                    solicitante = i.get('solicitado_por') or ''
                    rm = i.get('rm_aluno') or ''
                    
                    escritor.writerow([id_item, nome, desc, cat, data, local, status, solicitante, rm])
                    
            messagebox.showinfo("Relatório Concluído", f"A planilha foi salva com sucesso em:\n\n{file_path}\n\nVocê já pode abri-la no Excel.")
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Ocorreu um erro ao gerar o arquivo:\n{str(e)}")

    # --- ESTOQUE ---
    def construir_tab_itens(self):
        frame_top = tk.Frame(self.tab_itens, bg="#0d1117")
        frame_top.pack(fill="x", pady=10, padx=10)

        tk.Button(frame_top, text="➕ CADASTRAR NOVO ITEM", bg="#059669", fg="white", font=("Arial", 10, "bold"), command=lambda: self.abrir_modal_form()).pack(side="left", padx=10)

        frame_busca = tk.Frame(frame_top, bg="#0d1117")
        frame_busca.pack(side="right", padx=10)

        tk.Label(frame_busca, text="Buscar ID:", bg="#0d1117", fg="white").pack(side="left")
        self.entry_busca = ttk.Entry(frame_busca, width=15)
        self.entry_busca.pack(side="left", padx=5)
        self.entry_busca.bind("<Return>", lambda e: self.buscar_por_id_direto())

        tk.Label(frame_busca, text="Status:", bg="#0d1117", fg="white").pack(side="left", padx=(10,0))
        self.combo_filtro_status = ttk.Combobox(frame_busca, values=["TODOS", "DISPONÍVEL", "SOLICITADO", "PARA DOAÇÃO"], state="readonly", width=15)
        self.combo_filtro_status.current(0)
        self.combo_filtro_status.pack(side="left", padx=5)
        self.combo_filtro_status.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros_tabela())

        tk.Button(frame_busca, text="🔍 Buscar ID", bg="#1f6feb", fg="white", command=self.buscar_por_id_direto).pack(side="left")
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Local", "Solicitante")
        self.tree_itens = ttk.Treeview(self.tab_itens, columns=colunas, show="headings", height=15)
        for col in colunas:
            self.tree_itens.heading(col, text=col)
            self.tree_itens.column(col, anchor="center")
        
        self.tree_itens.column("ID", width=40)
        self.tree_itens.column("Nome / Descrição", width=250, anchor="w")
        self.tree_itens.column("Solicitante", width=150)
        self.tree_itens.pack(fill="both", expand=True, pady=5, padx=10)

        self.tree_itens.bind("<Double-1>", self.abrir_modal_detalhes_item)
        tk.Label(self.tab_itens, text="Dê um duplo-clique em um item da lista para Ver Fotos, Editar ou Dar Baixa.", bg="#0d1117", fg="#8b949e", font=("Arial", 9, "italic")).pack(pady=5)

    def carregar_itens(self):
        try:
            res = requests.get(f"{API_URL}/api/itens", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.itens_atuais = res.json()
                self.aplicar_filtros_tabela()
        except Exception as e: messagebox.showerror("Erro de Conexão", f"Não foi possível carregar os itens: {e}")

    def buscar_por_id_direto(self):
        id_buscado = self.entry_busca.get().strip()
        if not id_buscado:
            self.aplicar_filtros_tabela()
            return
        if not id_buscado.isdigit():
            messagebox.showwarning("Aviso", "Por favor, digite apenas números no campo de ID.")
            return
        item = next((i for i in self.itens_atuais if str(i['id']) == id_buscado), None)
        if item:
            self.entry_busca.delete(0, tk.END)
            self.aplicar_filtros_tabela()
            self.abrir_modal_detalhes_item(item_direto=item)
        else:
            messagebox.showinfo("Não encontrado", f"Nenhum objeto encontrado no sistema com o ID #{id_buscado}.")

    def aplicar_filtros_tabela(self):
        status_filtro = self.combo_filtro_status.get().upper()
        self.tree_itens.delete(*self.tree_itens.get_children())
        self.tree_doacoes.delete(*self.tree_doacoes.get_children())

        for i in self.itens_atuais:
            st = (i.get('status') or 'DISPONÍVEL').upper()
            nome_exibicao = i.get('nome') or i.get('txt_descricao') or "Sem Título"
            
            if st in ['PARA DOAÇÃO', 'DOAÇÃO FEITA']:
                self.tree_doacoes.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_data', '')))

            if status_filtro != "TODOS" and st != status_filtro: continue
            if status_filtro == "TODOS" and st in ['ENTREGUE', 'DOAÇÃO FEITA']: continue 

            solicitante = i.get('solicitado_por')
            solicitante_str = f"{solicitante} (RM: {i.get('rm_aluno', '-')})" if solicitante else "-"

            self.tree_itens.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_local', ''), solicitante_str))

    # --- MODAL CADASTRO / EDIÇÃO ---
    def abrir_modal_form(self, item_edit=None):
        modal = tk.Toplevel(self.root)
        modal.title("Novo Item" if not item_edit else f"Editar Item #{item_edit['id']}")
        modal.geometry("500x650")
        modal.configure(bg="#161b22")
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text="CADASTRAR NOVO OBJETO" if not item_edit else "EDITAR OBJETO", font=("Arial", 14, "bold"), bg="#161b22", fg="#38bdf8").pack(pady=15)

        var_nome = tk.StringVar(value=item_edit.get('nome', '') if item_edit else "")
        var_desc = tk.StringVar(value=item_edit.get('txt_descricao', '') if item_edit else "")
        var_data = tk.StringVar(value=item_edit.get('txt_data', datetime.now().strftime("%d/%m/%Y")) if item_edit else datetime.now().strftime("%d/%m/%Y"))
        var_local = tk.StringVar(value=item_edit.get('txt_local', '') if item_edit else "")
        
        fotos_atuais = item_edit['fotos'] if item_edit and item_edit.get('fotos') else ([item_edit['foto']] if item_edit and item_edit.get('foto') else [])
        fotos_upload_base64 = fotos_atuais.copy()

        def criar_campo(label, var, widget_type="entry", values=None):
            frame = tk.Frame(modal, bg="#161b22")
            frame.pack(fill="x", padx=40, pady=5)
            tk.Label(frame, text=label, bg="#161b22", fg="#c9d1d9", font=("Arial", 9, "bold")).pack(anchor="w")
            if widget_type == "entry":
                w = ttk.Entry(frame, textvariable=var, font=("Arial", 11))
                w.pack(fill="x", pady=2)
                return w
            else:
                w = ttk.Combobox(frame, values=values, state="readonly", font=("Arial", 10))
                if var: w.set(var)
                w.pack(fill="x", pady=2)
                return w

        criar_campo("Nome / Título Curto:", var_nome)
        criar_campo("Descrição Detalhada:", var_desc)
        cb_cat = criar_campo("Categoria:", item_edit.get('categoria', 'OUTROS') if item_edit else "OUTROS", "combo", self.categorias_atuais)
        criar_campo("Data Encontrado:", var_data)
        criar_campo("Local Encontrado:", var_local)
        cb_status = criar_campo("Status:", item_edit.get('status', 'DISPONÍVEL') if item_edit else "DISPONÍVEL", "combo", ["DISPONÍVEL", "SOLICITADO", "ENTREGUE", "PARA DOAÇÃO"])

        frame_fotos = tk.Frame(modal, bg="#161b22")
        frame_fotos.pack(fill="x", padx=40, pady=10)
        lbl_foto_status = tk.Label(frame_fotos, text=f"Fotos carregadas: {len(fotos_upload_base64)} (Máx 4)", bg="#161b22", fg="#94a3b8")
        lbl_foto_status.pack(side="right")

        def selecionar_fotos():
            filenames = filedialog.askopenfilenames(title="Selecione até 4 fotos", filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")])
            if filenames:
                fotos_upload_base64.clear()
                for f in filenames[:4]:
                    try:
                        with open(f, "rb") as image_file:
                            enc = base64.b64encode(image_file.read()).decode('utf-8')
                            fotos_upload_base64.append(f"data:image/jpeg;base64,{enc}")
                    except: pass
                lbl_foto_status.config(text=f"Fotos prontas para envio: {len(fotos_upload_base64)}", fg="#10b981")

        tk.Button(frame_fotos, text="📷 Selecionar Fotos do PC", bg="#4b5563", fg="white", relief="flat", command=selecionar_fotos).pack(side="left")

        def salvar():
            payload = {
                "nome": var_nome.get().strip(), "descricao": var_desc.get().strip(),
                "categoria": cb_cat.get(), "data": var_data.get().strip(),
                "local": var_local.get().strip(), "status": cb_status.get(), "fotos": fotos_upload_base64
            }
            if not payload['nome'] or not payload['descricao']: return messagebox.showwarning("Aviso", "Preencha título e descrição!")
            try:
                if item_edit:
                    res = requests.put(f"{API_URL}/api/itens/{item_edit['id']}", json=payload, headers=self.get_auth_headers())
                else:
                    res = requests.post(f"{API_URL}/api/itens", json=payload, headers=self.get_auth_headers())

                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item salvo na nuvem com segurança!")
                    modal.destroy()
                    self.carregar_itens()
                    self.carregar_dashboard()
                else: messagebox.showerror("Erro", "Acesso Negado ou erro no servidor.")
            except Exception as e: messagebox.showerror("Erro", str(e))

        tk.Button(modal, text="💾 GRAVAR NO BANCO NUVEM", bg="#16a34a", fg="white", font=("Arial", 11, "bold"), pady=10, relief="flat", command=salvar).pack(fill="x", padx=40, pady=20)

    # --- MODAL DETALHES DO ITEM ---
    def abrir_modal_detalhes_item(self, event=None, item_direto=None):
        if item_direto: item = item_direto
        else:
            selecionado = self.tree_itens.selection()
            if not selecionado: return
            item_id = self.tree_itens.item(selecionado[0])['values'][0]
            item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
            
        if not item: return

        modal = tk.Toplevel(self.root)
        modal.title(f"Detalhes do Item #{item['id']}")
        modal.geometry("750x650")
        modal.configure(bg="#0d1117")
        modal.transient(self.root)

        nome_titulo = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
        tk.Label(modal, text=nome_titulo, font=("Arial", 16, "bold"), bg="#0d1117", fg="#f87171").pack(pady=10)

        frame_info = tk.Frame(modal, bg="#161b22", bd=1, relief="solid")
        frame_info.pack(fill="x", padx=20, pady=5)
        st = item.get('status', 'DISPONÍVEL').upper()

        info_texto = f"CATEGORIA: {item.get('categoria', '')}   |   STATUS: {st}\n\nLOCAL: {item.get('txt_local', '')}\nDATA: {item.get('txt_data', '')}\nDESCRIÇÃO: {item.get('txt_descricao', '')}\n"
        if item.get('solicitado_por'): info_texto += f"\n🚨 SOLICITADO POR: {item.get('solicitado_por')} (RM: {item.get('rm_aluno', '')})"

        tk.Label(frame_info, text=info_texto, justify="left", bg="#161b22", fg="#c9d1d9", font=("Arial", 11)).pack(padx=15, pady=10, anchor="w")

        tk.Label(modal, text="Galeria de Fotos:", font=("Arial", 12, "bold"), bg="#0d1117", fg="#c9d1d9").pack(pady=5, anchor="w", padx=20)
        frame_fotos = tk.Frame(modal, bg="#0d1117")
        frame_fotos.pack(fill="both", expand=True, padx=20)

        fotos_array = item.get('fotos', [])
        if not fotos_array and item.get('foto'): fotos_array = [item['foto']]

        if not fotos_array: tk.Label(frame_fotos, text="Nenhuma foto registrada.", bg="#0d1117", fg="#8b949e").pack(pady=10)
        else:
            for col, foto_url in enumerate(fotos_array):
                try:
                    if foto_url.startswith('http'):
                        import urllib.request
                        with urllib.request.urlopen(foto_url) as u:
                            raw_data = u.read()
                        img = Image.open(io.BytesIO(raw_data))
                        img.thumbnail((180, 180), Image.Resampling.LANCZOS)
                        img_tk = ImageTk.PhotoImage(img)
                        lbl_img = tk.Label(frame_fotos, image=img_tk, bg="#161b22", bd=2, relief="solid")
                        lbl_img.image = img_tk
                        lbl_img.grid(row=0, column=col, padx=10, pady=5)
                except: pass

        frame_acoes = tk.Frame(modal, bg="#0d1117")
        frame_acoes.pack(fill="x", pady=15, padx=20)

        def btn(txt, cor, cmd):
            tk.Button(frame_acoes, text=txt, bg=cor, fg="white", font=("Arial", 9, "bold"), command=cmd).pack(side="left", padx=5, fill="x", expand=True)

        btn("🖨️ Etiqueta QR", "#2563eb", lambda: self.abrir_modal_etiqueta_qr(item))
        btn("✏️ Editar", "#eab308", lambda: [modal.destroy(), self.abrir_modal_form(item)])
        
        if st == 'SOLICITADO': btn("🚫 Recusar", "#d97706", lambda: self.acao_rapida(item['id'], 'recusar', modal))
        if st not in ['ENTREGUE', 'DOAÇÃO FEITA']: btn("✅ Dar Baixa", "#059669", lambda: [modal.destroy(), self.abrir_dar_baixa(item)])
        if st not in ['PARA DOAÇÃO', 'DOAÇÃO FEITA', 'ENTREGUE']: btn("🎁 Marcar Doação", "#9333ea", lambda: self.acao_rapida(item['id'], 'doacao', modal))
        btn("🗑️ Excluir", "#991b1b", lambda: self.acao_rapida(item['id'], 'excluir', modal))

    # --- GERADOR DE QR CODE ETIQUETA ---
    def abrir_modal_etiqueta_qr(self, item):
        modal = tk.Toplevel(self.root)
        modal.title("Impressão de Etiqueta QR")
        modal.geometry("350x450")
        modal.configure(bg="#161b22")
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(modal, text=f"Etiqueta do Item #{item['id']}", font=("Arial", 14, "bold"), bg="#161b22", fg="#f87171").pack(pady=15)
        
        payload = f"ETEC-ITEM-{item['id']}"
        qr = qrcode.QRCode(version=1, box_size=8, border=1)
        qr.add_data(payload)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        largura, altura = img_qr.size
        etiqueta_img = Image.new('RGB', (largura, altura + 30), color='white')
        etiqueta_img.paste(img_qr, (0, 0))
        
        draw = ImageDraw.Draw(etiqueta_img)
        texto = f"ID: {item['id']}"
        try: fonte = ImageFont.truetype("arial.ttf", 20)
        except: fonte = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        w_texto = bbox[2] - bbox[0]
        x_texto = (largura - w_texto) / 2
        draw.text((x_texto, altura), texto, fill="black", font=fonte)

        preview = etiqueta_img.copy()
        preview.thumbnail((200, 200), Image.Resampling.LANCZOS)
        preview_tk = ImageTk.PhotoImage(preview)
        lbl_preview = tk.Label(modal, image=preview_tk, bg="#161b22", bd=2, relief="solid")
        lbl_preview.image = preview_tk
        lbl_preview.pack(pady=10)

        def salvar_png():
            path = filedialog.asksaveasfilename(defaultextension=".png", initialfile=f"qr_etec_{item['id']}.png", title="Salvar Imagem da Etiqueta", filetypes=[("Imagem PNG", "*.png")])
            if path:
                etiqueta_img.save(path)
                messagebox.showinfo("Sucesso", f"Etiqueta salva em: {path}", parent=modal)

        def imprimir_direto():
            temp_path = os.path.abspath(f"temp_etiqueta_qr_{item['id']}.png")
            etiqueta_img.save(temp_path)
            try: os.startfile(temp_path, "print")
            except Exception as e: messagebox.showerror("Erro", f"Erro na impressão direta: {e}", parent=modal)

        tk.Button(modal, text="💾 SALVAR COMO IMAGEM (.PNG)", bg="#16a34a", fg="white", font=("Arial", 10, "bold"), pady=8, command=salvar_png).pack(fill="x", padx=30, pady=5)
        tk.Button(modal, text="🖨️ IMPRIMIR DIRETO", bg="#2563eb", fg="white", font=("Arial", 10, "bold"), pady=8, command=imprimir_direto).pack(fill="x", padx=30, pady=5)

    # --- AÇÕES RÁPIDAS COM JWT ---
    def acao_rapida(self, item_id, acao, modal=None):
        try:
            if acao == 'excluir' and messagebox.askyesno("Excluir", "Deseja excluir este item permanentemente?"):
                res = requests.delete(f"{API_URL}/api/itens/{item_id}", headers=self.get_auth_headers())
            elif acao == 'recusar' and messagebox.askyesno("Recusar", "Deseja recusar a solicitação?"):
                res = requests.put(f"{API_URL}/api/itens/{item_id}/recusar", headers=self.get_auth_headers())
            elif acao == 'doacao':
                res = requests.put(f"{API_URL}/api/itens/{item_id}", json={"status": "PARA DOAÇÃO"}, headers=self.get_auth_headers())
            else: return

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", "Operação realizada!")
                if modal: modal.destroy()
                self.carregar_dados()
            else:
                messagebox.showerror("Erro", "Acesso Negado.")
        except Exception as e: messagebox.showerror("Erro", str(e))

    # --- DAR BAIXA COM JWT ---
    def abrir_dar_baixa(self, item):
        modal_baixa = tk.Toplevel(self.root)
        modal_baixa.title(f"Dar Baixa - Item #{item['id']}")
        modal_baixa.geometry("450x400")
        modal_baixa.configure(bg="#0d1117")
        modal_baixa.transient(self.root)
        modal_baixa.grab_set()

        tk.Label(modal_baixa, text="Registrar Entrega ao Dono", font=("Arial", 14, "bold"), bg="#0d1117", fg="#10b981").pack(pady=15)

        tk.Label(modal_baixa, text="Nome Completo do Aluno:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_nome = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_nome.insert(0, item.get('solicitado_por') or '')
        entry_nome.pack(padx=30, pady=(0, 10))

        tk.Label(modal_baixa, text="RM:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_rm = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_rm.insert(0, item.get('rm_aluno') or '')
        entry_rm.pack(padx=30, pady=(0, 10))

        tk.Label(modal_baixa, text="Turma / Curso:", bg="#0d1117", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=30, pady=(5,2))
        entry_turma = ttk.Entry(modal_baixa, width=45, font=("Arial", 11))
        entry_turma.pack(padx=30, pady=(0, 20))

        def confirmar():
            n, r, t = entry_nome.get().strip(), entry_rm.get().strip(), entry_turma.get().strip() or "-"
            if not n or not r: return messagebox.showwarning("Aviso", "Preencha Nome e RM", parent=modal_baixa)
            try:
                res = requests.put(f"{API_URL}/api/itens/{item['id']}", json={"status": "ENTREGUE", "retirado_por": n, "rm_retirante": r, "turma_curso": t, "funcionario_responsavel": "Secretaria Desktop"}, headers=self.get_auth_headers())
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item baixado com sucesso!", parent=modal_baixa)
                    modal_baixa.destroy()
                    self.carregar_dados()
                    nome_obj = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
                    self.abrir_tela_comprovante(item['id'], nome_obj, item.get('txt_descricao') or '', item.get('txt_local') or '', n, r, t)
                else: messagebox.showerror("Erro", "Acesso Negado.", parent=modal_baixa)
            except Exception as e: messagebox.showerror("Erro", str(e), parent=modal_baixa)

        tk.Button(modal_baixa, text="Confirmar e Gerar Comprovante", bg="#059669", fg="white", font=("Arial", 10, "bold"), pady=8, command=confirmar).pack(fill="x", padx=30)
        entry_nome.focus()

    def abrir_tela_comprovante(self, item_id, nome_item, desc_item, local_item, retirado_por, rm, turma):
        top_comp = tk.Toplevel(self.root)
        top_comp.title("Comprovante de Retirada")
        top_comp.geometry("650x700")
        top_comp.configure(bg="#e5e7eb") 
        top_comp.transient(self.root)
        top_comp.grab_set()

        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        folha = tk.Frame(top_comp, bg="white", padx=40, pady=30)
        folha.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(folha, text="ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO", font=("Arial", 14, "bold"), bg="white", fg="black").pack()
        tk.Label(folha, text="Sistema de Achados e Perdidos - Termo de Retirada", font=("Arial", 10, "bold"), bg="white", fg="#4b5563").pack(pady=(0, 20))

        f_aluno = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_aluno.pack(fill="x", pady=5)
        tk.Label(f_aluno, text=f"Nome: {retirado_por}\nRM: {rm}", font=("Arial", 11), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        f_item = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_item.pack(fill="x", pady=5)
        tk.Label(f_item, text=f"Item #{item_id}: {nome_item}\nData da Entrega: {data_atual}", font=("Arial", 11), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        def baixar_comprovante_txt():
            file_path = filedialog.asksaveasfilename(parent=top_comp, defaultextension=".txt", initialfile=f"comprovante_{rm}.txt", title="Salvar Comprovante")
            if file_path:
                txt_content = f"ETEC - TERMO DE RETIRADA\nAluno: {retirado_por} (RM: {rm})\nItem #{item_id}: {nome_item}\nData: {data_atual}"
                with open(file_path, "w", encoding="utf-8") as f: f.write(txt_content)
                messagebox.showinfo("Sucesso", "Comprovante salvo!", parent=top_comp)

        b_frame = tk.Frame(top_comp, bg="#e5e7eb")
        b_frame.pack(fill="x", padx=30, pady=(0, 20))
        tk.Button(b_frame, text="📥 BAIXAR TXT", command=baixar_comprovante_txt, bg="#2563eb", fg="white", font=("Arial", 10, "bold"), pady=10).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(b_frame, text="Fechar", command=top_comp.destroy, bg="#475569", fg="white", font=("Arial", 10, "bold"), pady=10).pack(side="left", fill="x", expand=True, padx=(5, 0))

    # --- DOAÇÕES, CATEGORIAS E ENTREGUES ---
    def construir_tab_doacoes(self):
        frame_top = tk.Frame(self.tab_doacoes, bg="#0d1117")
        frame_top.pack(fill="x", pady=10, padx=10)
        tk.Label(frame_top, text="Gerenciamento de Doações", font=("Arial", 14, "bold"), bg="#0d1117", fg="#f59e0b").pack(side="left")
        def concluir_doacoes():
            if messagebox.askyesno("Confirmar Doação", "Deseja remover todos os itens doados do sistema?"):
                try:
                    for child in self.tree_doacoes.get_children():
                        requests.put(f"{API_URL}/api/itens/{self.tree_doacoes.item(child)['values'][0]}", json={"status": "DOAÇÃO FEITA"}, headers=self.get_auth_headers())
                    requests.delete(f"{API_URL}/api/itens/doacoes/concluir", headers=self.get_auth_headers())
                    messagebox.showinfo("Sucesso", "Doações concluídas!")
                    self.carregar_dados()
                except: pass
        tk.Button(frame_top, text="🎁 CONCLUIR E LIMPAR DOAÇÕES", bg="#f59e0b", fg="#0d1117", font=("Arial", 10, "bold"), command=concluir_doacoes).pack(side="right")
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Data Encontrado")
        self.tree_doacoes = ttk.Treeview(self.tab_doacoes, columns=colunas, show="headings", height=15)
        for col in colunas: self.tree_doacoes.heading(col, text=col); self.tree_doacoes.column(col, anchor="center")
        self.tree_doacoes.pack(fill="both", expand=True, pady=5, padx=10)

    def construir_tab_categorias(self):
        frame_add = tk.Frame(self.tab_categorias, bg="#0d1117")
        frame_add.pack(pady=20)
        tk.Label(frame_add, text="Nova Categoria:", bg="#0d1117", fg="white").pack(side="left", padx=5)
        self.entry_cat = ttk.Entry(frame_add, width=30)
        self.entry_cat.pack(side="left", padx=5)
        self.entry_cat.bind("<Return>", lambda e: self.adicionar_categoria())
        tk.Button(frame_add, text="Adicionar", bg="#dc2626", fg="white", command=self.adicionar_categoria).pack(side="left", padx=5)
        self.listbox_cats = tk.Listbox(self.tab_categorias, bg="#161b22", fg="white", font=("Arial", 12), height=15)
        self.listbox_cats.pack(fill="x", padx=50, pady=10)

    def carregar_categorias(self):
        try:
            res = requests.get(f"{API_URL}/api/categorias")
            if res.status_code == 200:
                self.listbox_cats.delete(0, tk.END)
                self.categorias_atuais = []
                for c in res.json():
                    self.listbox_cats.insert(tk.END, c['nome'])
                    self.categorias_atuais.append(c['nome'])
        except: pass

    def adicionar_categoria(self):
        nome = self.entry_cat.get().strip().upper()
        if nome:
            try:
                res = requests.post(f"{API_URL}/api/categorias", json={"nome": nome}, headers=self.get_auth_headers())
                if res.status_code == 200:
                    self.entry_cat.delete(0, tk.END)
                    self.carregar_categorias()
            except: pass

    def construir_tab_entregues(self):
        frame_top = tk.Frame(self.tab_entregues, bg="#0d1117")
        frame_top.pack(fill="x", pady=10, padx=10)
        tk.Button(frame_top, text="🔄 Atualizar Histórico", command=self.carregar_entregues, bg="#1f6feb", fg="white", font=("Arial", 9, "bold")).pack(side="left")
        tk.Button(frame_top, text="🗑️ Excluir Registro", command=self.excluir_entregue, bg="#dc2626", fg="white", font=("Arial", 9, "bold")).pack(side="right", padx=(10, 0))
        tk.Button(frame_top, text="↩️ Desfazer Entrega", command=self.desfazer_entrega, bg="#d97706", fg="white", font=("Arial", 9, "bold")).pack(side="right")

        colunas = ("Recibo", "ID Item", "Item", "Retirado Por", "RM", "Turma", "Data")
        self.tree_entregues = ttk.Treeview(self.tab_entregues, columns=colunas, show="headings", height=20)
        for col in colunas: self.tree_entregues.heading(col, text=col); self.tree_entregues.column(col, anchor="center")
        self.tree_entregues.pack(fill="both", expand=True, pady=5, padx=10)
        self.tree_entregues.bind("<Double-1>", self.abrir_detalhes_do_historico)

    def carregar_entregues(self):
        if not TOKEN_SECRETARIA: return
        try:
            res = requests.get(f"{API_URL}/api/entregues", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.tree_entregues.delete(*self.tree_entregues.get_children())
                for e in res.json():
                    self.tree_entregues.insert("", "end", values=(e['id'], e['item_id'], e['nome_item'], e['retirado_por'], e['rm_retirante'], e['turma_curso'], e['data_entrega']))
        except: pass

    def abrir_detalhes_do_historico(self, event):
        selecionado = self.tree_entregues.selection()
        if selecionado:
            item_id = self.tree_entregues.item(selecionado[0])['values'][1]
            item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
            if item: self.abrir_modal_detalhes_item(item_direto=item)

    def desfazer_entrega(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        vals = self.tree_entregues.item(selecionado[0], "values")
        if messagebox.askyesno("Desfazer", f"Reverter entrega do item #{vals[1]}?"):
            try:
                res = requests.put(f"{API_URL}/api/itens/{vals[1]}/recusar", headers=self.get_auth_headers())
                if res.status_code == 200: self.carregar_dados()
            except: pass

    def excluir_entregue(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        vals = self.tree_entregues.item(selecionado[0], "values")
        if messagebox.askyesno("Excluir", f"Excluir histórico do item #{vals[1]}?"):
            try:
                res = requests.delete(f"{API_URL}/api/itens/{vals[1]}", headers=self.get_auth_headers())
                if res.status_code == 200: self.carregar_dados()
            except: pass

    # --- TAB: CHAT ---
    def construir_tab_chat(self):
        frame_esq = tk.Frame(self.tab_chat, bg="#0d1117", width=250)
        frame_esq.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(frame_esq, text="Conversas Ativas", bg="#0d1117", fg="white", font=("Arial", 12, "bold")).pack(pady=5)
        self.listbox_chat = tk.Listbox(frame_esq, bg="#161b22", fg="white", font=("Arial", 10))
        self.listbox_chat.pack(fill="both", expand=True)
        self.listbox_chat.bind("<<ListboxSelect>>", self.selecionar_conversa)
        
        frame_dir = tk.Frame(self.tab_chat, bg="#161b22", bd=1, relief="solid")
        frame_dir.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.lbl_chat_titulo = tk.Label(frame_dir, text="Selecione um aluno", bg="#161b22", fg="#f87171", font=("Arial", 14, "bold"))
        self.lbl_chat_titulo.pack(pady=10)
        self.txt_mensagens = tk.Text(frame_dir, bg="#0d1117", fg="white", state="disabled", wrap="word", font=("Arial", 11))
        self.txt_mensagens.pack(fill="both", expand=True, padx=10, pady=5)
        
        frame_input = tk.Frame(frame_dir, bg="#161b22")
        frame_input.pack(fill="x", padx=10, pady=10)
        self.entry_chat = ttk.Entry(frame_input, font=("Arial", 12))
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_chat.bind("<Return>", lambda e: self.enviar_mensagem())
        tk.Button(frame_input, text="Enviar", bg="#dc2626", fg="white", font=("Arial", 10, "bold"), command=self.enviar_mensagem).pack(side="right")
        self.atualizar_chat_continuo()

    def carregar_conversas(self):
        if not TOKEN_SECRETARIA: return
        try:
            res = requests.get(f"{API_URL}/api/chat/conversas", headers=self.get_auth_headers_get())
            if res.status_code == 200:
                self.listbox_chat.delete(0, tk.END)
                self.mapa_conversas = []
                for c in res.json():
                    notif = f"({c['nao_lidas']} novas) " if c['nao_lidas'] > 0 else ""
                    self.listbox_chat.insert(tk.END, f"{notif}{c['nome_aluno']} - RM: {c['rm_aluno']}")
                    self.mapa_conversas.append(c['rm_aluno'])
        except: pass

    def selecionar_conversa(self, event):
        selecao = self.listbox_chat.curselection()
        if selecao:
            idx = selecao[0]
            self.rm_chat_ativo = self.mapa_conversas[idx]
            self.lbl_chat_titulo.config(text=f"Chat: {self.listbox_chat.get(idx)}")
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
        if not self.rm_chat_ativo or not self.entry_chat.get().strip(): return
        try:
            res = requests.post(f"{API_URL}/api/chat/enviar", json={"rm": self.rm_chat_ativo, "nome": "Secretaria", "remetente": "SECRETARIA", "mensagem": self.entry_chat.get().strip()})
            if res.status_code == 200:
                self.entry_chat.delete(0, tk.END)
                self.carregar_mensagens_aluno()
        except: pass

    def atualizar_chat_continuo(self):
        if TOKEN_SECRETARIA:
            self.carregar_conversas()
            if self.rm_chat_ativo: self.carregar_mensagens_aluno()
        self.chat_timer = self.root.after(3000, self.atualizar_chat_continuo)

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretariaApp(root)
    root.mainloop()
