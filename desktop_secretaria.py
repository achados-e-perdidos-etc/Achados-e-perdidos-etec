from desktop_tasks import Trabalho, TarefasDesktop, assincrono
from desktop_moderacao import ModeracaoDesktop
from desktop_ferramentas import FerramentasDesktop,baixar_foto_original
from desktop_formulario import FormularioDesktop
from utils.ferramentas import filtrar_itens
from urllib.parse import urlencode, quote
from utils.exportacao import salvar_csv
from utils.comprovantes import abrir_impressao_desktop
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests
import json
import base64
import io
import os
import sys
from pathlib import Path
import csv
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageOps
from datetime import datetime
import qrcode

# ==========================================
# CONFIGURAÇÕES DA API E JWT
# ==========================================
API_URL = os.environ.get("ETEC_API_URL", "https://etec-achados.up.railway.app").rstrip("/")
TOKEN_SECRETARIA = None

def requisicao_desktop(metodo, url, **kwargs):
    """Limita a espera em conexões interrompidas, inclusive durante login."""
    permitir_falha_login=kwargs.pop('permitir_falha_login',False)
    kwargs.setdefault('timeout', (5, 25))
    res = requests.request(metodo, url, **kwargs)
    if res.status_code == 401 and url.startswith(API_URL+'/api/') and not url.endswith('/api/login') and kwargs.get('headers',{}).get('Authorization'):
        error = requests.HTTPError('Sessão expirada.');error.sessao_expirada = True;raise error
    if permitir_falha_login and res.status_code==401 and url.endswith(('/api/login','/api/auth/login-aluno')):return res
    if not res.ok:
        error=requests.HTTPError(f'Operação não confirmada (HTTP {res.status_code}).',response=res)
        try:
            mensagem=res.json().get('message')
            if isinstance(mensagem,str):error.mensagem_publica=mensagem[:300]
        except (ValueError,AttributeError):pass
        raise error
    return res


def caminho_logo_secretaria():
    raiz = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return raiz / 'logo_secretaria.png'


# Paleta de Cores Visual Moderna
COR_BG_GERAL = "#0d1117"
COR_BG_CARD = "#161b22"
COR_BG_HEADER = "#21262d"
COR_TEXTO_PRINCIPAL = "#c9d1d9"
COR_DESTAQUE = "#dc2626"      # Vermelho ETEC
COR_VERDE = "#10b981"
COR_AZUL = "#1f6feb"
COR_BORDA = "#30363d"

# ==========================================
# FUNÇÃO DE COMPRESSÃO DE FOTOS NO DESKTOP
# ==========================================
def comprimir_foto_desktop(caminho_arquivo, max_dim=1200, qualidade=75):
    try:
        with Image.open(caminho_arquivo) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            w, h = img.size
            if w > max_dim or h > max_dim:
                if w > h:
                    novo_h = int((h * max_dim) / w)
                    novo_w = max_dim
                else:
                    novo_w = int((w * max_dim) / h)
                    novo_h = max_dim
                img = img.resize((novo_w, novo_h), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=qualidade, optimize=True)
            enc = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{enc}"
    except Exception as e:
        print(f"Erro ao comprimir imagem desktop: {e}")
        return None

def baixar_miniatura(url):
    try:
        res = requisicao_desktop('GET',url)
        with Image.open(io.BytesIO(res.content)) as original:
            img = ImageOps.exif_transpose(original).convert('RGB')
            img.thumbnail((160,160),Image.Resampling.LANCZOS)
            return img.copy()
    except (requests.RequestException,OSError,ValueError):
        return None


class SecretariaApp(ModeracaoDesktop,FerramentasDesktop,FormularioDesktop):
    def __init__(self, root):
        self.root = root
        self.root.title("ETEC - Painel da Secretaria")
        self.root.geometry("1150x780")
        self.root.configure(bg=COR_BG_GERAL)
        
        self.itens_atuais = []
        self.categorias_atuais = []
        self.uploads_abertos=[];self.cameras=[];self.rascunho_item=None
        self.perfil_painel = {}
        self.impressoes_temporarias=[]
        self.chat_timer = None
        self.email_chat_ativo = None
        self.chat_legado = False
        self.rm_chat_ativo = None

        self.estilo = ttk.Style()
        self.estilo.theme_use("clam")
        
        self.estilo.configure("TNotebook", background=COR_BG_GERAL, borderwidth=0)
        self.estilo.configure("TNotebook.Tab", background=COR_BG_HEADER, foreground=COR_TEXTO_PRINCIPAL, padding=(10, 8), font=("Segoe UI", 10, "bold"), relief="flat")
        self.estilo.map("TNotebook.Tab", background=[("selected", COR_DESTAQUE)], foreground=[("selected", "white")])
        
        self.estilo.configure("Treeview", background=COR_BG_CARD, foreground=COR_TEXTO_PRINCIPAL, fieldbackground=COR_BG_CARD, borderwidth=0, rowheight=34, font=("Segoe UI", 10))
        self.estilo.map("Treeview", background=[("selected", COR_DESTAQUE)], foreground=[("selected", "white")])
        self.estilo.configure("Treeview.Heading", background=COR_BG_HEADER, foreground="#ffffff", font=("Segoe UI", 10, "bold"), relief="flat")

        self.logo_secretaria = None
        try:
            with Image.open(caminho_logo_secretaria()) as logo:
                self.logo_secretaria = ImageTk.PhotoImage(logo.resize((64, 64), Image.Resampling.LANCZOS))
            self.root.iconphoto(True, self.logo_secretaria)
        except (OSError, tk.TclError):
            pass  # O arquivo acompanha a distribuição; ausência não impede o login.
        self.barra_status = tk.Frame(self.root,bg=COR_BG_HEADER)
        self.barra_status.pack(side='bottom',fill='x')
        self.var_status = tk.StringVar(value='Pronto para conectar.')
        tk.Label(self.barra_status,textvariable=self.var_status,bg=COR_BG_HEADER,fg='white').pack(side='left',padx=10,pady=6)
        self.tarefas = TarefasDesktop(self)
        tk.Button(self.barra_status,text='Tentar novamente',command=self.tarefas.repetir).pack(side='right',padx=8)
        self.root.protocol('WM_DELETE_WINDOW',self.fechar_aplicativo)
        self.tela_login()

    def status_operacao(self,texto,erro=False):
        self.var_status.set(texto)

    def erro_operacao(self,texto):
        self.status_operacao(texto,erro=True)
        messagebox.showerror('Operação não confirmada',texto)

    def encerrar_sessao(self,expirada=False):
        global TOKEN_SECRETARIA
        TOKEN_SECRETARIA = None
        self.tarefas.invalidar()
        self.limpar_impressoes()
        self.limpar_recursos_paridade()
        if self.chat_timer:
            self.root.after_cancel(self.chat_timer);self.chat_timer=None
        for widget in list(self.root.winfo_children()):
            if widget is not self.barra_status:widget.destroy()
        self.itens_atuais=[];self.categorias_atuais=[];self.mapa_conversas=[]
        self.rm_chat_ativo=None;self.email_chat_ativo=None
        self.tela_login()
        self.status_operacao('Sua sessão expirou. Entre novamente.' if expirada else 'Sessão encerrada.')

    def fechar_aplicativo(self):
        global TOKEN_SECRETARIA
        TOKEN_SECRETARIA = None
        if self.chat_timer:self.root.after_cancel(self.chat_timer)
        self.tarefas.fechar();self.limpar_impressoes();self.limpar_recursos_paridade();self.root.destroy()

    def chamar_api(self,metodo,caminho,**kwargs):
        return requisicao_desktop(metodo,API_URL+caminho,**kwargs)

    def baixar_imagem(self,url):
        return baixar_miniatura(url)

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
        self.frame_login = tk.Frame(self.root, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", width=440, height=450)

        tk.Label(self.frame_login, image=self.logo_secretaria, text='' if self.logo_secretaria else 'Secretaria ETEC',
                 compound='top', bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL).pack(pady=(20, 0))
        tk.Label(self.frame_login, text="Acesso Restrito - Secretaria", font=("Segoe UI", 16, "bold"), bg=COR_BG_CARD, fg=COR_DESTAQUE).pack(pady=(5, 2))
        tk.Label(self.frame_login, text="Painel Administrativo Seguro", font=("Segoe UI", 9, "italic"), bg=COR_BG_CARD, fg=COR_VERDE).pack(pady=(0, 20))

        frame_inputs = tk.Frame(self.frame_login, bg=COR_BG_CARD)
        frame_inputs.pack(fill="x", padx=40)

        tk.Label(frame_inputs, text="E-mail Institucional:", font=("Segoe UI", 9, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL).pack(anchor="w", pady=(0, 2))
        self.entry_email = tk.Entry(frame_inputs, font=("Segoe UI", 11), bg=COR_BG_GERAL, fg="white", insertbackground="white", relief="flat", highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE, highlightthickness=1)
        self.entry_email.pack(fill="x", pady=(0, 12), ipady=6)

        tk.Label(frame_inputs, text="Senha de Acesso:", font=("Segoe UI", 9, "bold"), bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL).pack(anchor="w", pady=(0, 2))
        self.entry_senha = tk.Entry(frame_inputs, font=("Segoe UI", 11), show="*", bg=COR_BG_GERAL, fg="white", insertbackground="white", relief="flat", highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE, highlightthickness=1)
        self.entry_senha.pack(fill="x", pady=(0, 8), ipady=6)
        visivel=tk.BooleanVar(value=False)
        tk.Checkbutton(frame_inputs,text='Mostrar senha',variable=visivel,command=lambda:self.entry_senha.configure(show='' if visivel.get() else '*'),bg=COR_BG_CARD,fg=COR_TEXTO_PRINCIPAL,selectcolor=COR_BG_GERAL).pack(anchor='w',pady=(0,12))

        self.entry_email.bind("<Return>", lambda e: self.entry_senha.focus())
        self.entry_senha.bind("<Return>", lambda e: self.verificar_login())

        self.btn_entrar = tk.Button(self.frame_login, text="ENTRAR NO SISTEMA", font=("Segoe UI", 10, "bold"), bg=COR_DESTAQUE, fg="white", activebackground="#b91c1c", activeforeground="white", relief="flat", cursor="hand2", command=self.verificar_login)
        self.btn_entrar.pack(fill="x", padx=40, ipady=10)
        self.entry_email.focus()

    @assincrono
    def verificar_login(self):
        global TOKEN_SECRETARIA
        email = self.entry_email.get().strip().lower()
        senha = self.entry_senha.get().strip()

        if not email or not senha:
            return messagebox.showerror("Erro", "Preencha o e-mail e a senha!")

        self.btn_entrar.config(text="CONECTANDO...", state="disabled")
        pass

        try:
            res = (yield Trabalho(requisicao_desktop, 'POST', f"{API_URL}/api/login", json={"email": email, "senha": senha},permitir_falha_login=True))
            if res.status_code==401:
                res=(yield Trabalho(requisicao_desktop,'POST',f"{API_URL}/api/auth/login-aluno",json={"email":email,"senha":senha},permitir_falha_login=True))
            data = res.json()

            if res.status_code == 200 and data.get("success"):
                candidato=data.get('token')
                verificacao=yield Trabalho(requisicao_desktop,'GET',f"{API_URL}/api/auth/verificar",headers={'Authorization':'Bearer '+str(candidato)})
                perfil=verificacao.json().get('user') or {}
                if perfil.get('role')!='secretaria':
                    messagebox.showerror('Acesso não autorizado','Sua conta não tem autorização da escola para operar a secretaria.');return
                self.perfil_painel=perfil
                TOKEN_SECRETARIA = candidato
                self.entry_senha.delete(0,tk.END)
                self.frame_login.destroy()
                self.construir_interface_principal()
            else:
                messagebox.showerror("Acesso Negado", data.get("message", "E-mail ou senha incorretos!"))
                self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível falar com o servidor:\n{e}")
            self.btn_entrar.config(text="ENTRAR NO SISTEMA", state="normal")

    def construir_interface_principal(self):
        cabecalho = tk.Frame(self.root, bg=COR_BG_HEADER)
        cabecalho.pack(fill='x')
        tk.Button(cabecalho,text='Sair / trocar conta',command=self.encerrar_sessao).pack(side='right',padx=12)
        tk.Label(cabecalho, image=self.logo_secretaria, text='  SECRETARIA ETEC', compound='left',
                 bg=COR_BG_HEADER, fg='white', font=('Segoe UI', 13, 'bold')).pack(side='left', padx=12, pady=6)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_dash = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_itens = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_categorias = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_entregues = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_doacoes = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_chat = tk.Frame(self.notebook, bg=COR_BG_GERAL)
        self.tab_mural = tk.Frame(self.notebook, bg=COR_BG_GERAL)

        self.notebook.add(self.tab_dash, text="📊 Dashboard")
        self.notebook.add(self.tab_itens, text="📦 Estoque")
        self.notebook.add(self.tab_categorias, text="🏷️ Categorias")
        self.notebook.add(self.tab_entregues, text="📋 Entregas")
        self.notebook.add(self.tab_doacoes, text="🎁 Doações")
        self.notebook.add(self.tab_chat, text="💬 Chat")
        self.notebook.add(self.tab_mural, text="📢 Mural")

        self.construir_tab_dash()
        self.construir_tab_itens()
        self.construir_tab_categorias()
        self.construir_tab_entregues()
        self.construir_tab_doacoes()
        self.construir_tab_chat()
        self.construir_tab_mural()
        self.tab_moderacao=tk.Frame(self.notebook,bg=COR_BG_GERAL);self.notebook.add(self.tab_moderacao,text='Moderação');self.construir_tab_moderacao()
        self.tab_professores=None
        if 'gerir_acessos' in self.perfil_painel.get('permissoes',[]):
            self.tab_professores=tk.Frame(self.notebook,bg=COR_BG_GERAL);self.notebook.add(self.tab_professores,text='Professores');self.construir_tab_professores()
        self.construir_ferramentas()
        self.notebook.bind('<<NotebookTabChanged>>',self.aba_equipe_alterada)
        self.carregar_dados()

    def aba_equipe_alterada(self,event=None):
        selecionada=self.notebook.select()
        if selecionada==str(self.tab_moderacao):self.carregar_moderacao()
        elif self.tab_professores is not None and selecionada==str(self.tab_professores):self.carregar_professores()

    def carregar_dados(self):
        self.atualizar_prioridades()
        self.carregar_categorias()
        self.carregar_itens()
        self.carregar_entregues()
        self.carregar_dashboard()
        self.carregar_conversas()
        self.carregar_mural()
        
    def construir_tab_dash(self):
        tk.Label(self.tab_dash, text="Visão Geral do Sistema", font=("Segoe UI", 18, "bold"), bg=COR_BG_GERAL, fg="#f87171").pack(pady=(20, 10))
        
        frame_cards = tk.Frame(self.tab_dash, bg=COR_BG_GERAL)
        frame_cards.pack(pady=10)
        
        def criar_card(parent, titulo, cor):
            f = tk.Frame(parent, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1, width=220, height=120)
            f.pack_propagate(False)
            f.pack(side="left", padx=12)
            tk.Label(f, text=titulo, font=("Segoe UI", 9, "bold"), bg=COR_BG_CARD, fg="#8b949e").pack(pady=(16, 4))
            lbl_valor = tk.Label(f, text="0", font=("Segoe UI", 26, "bold"), bg=COR_BG_CARD, fg=cor)
            lbl_valor.pack()
            return lbl_valor

        self.lbl_stat_itens = criar_card(frame_cards, "TOTAL DE ITENS", "#3b82f6")
        self.lbl_stat_entregues = criar_card(frame_cards, "ITENS ENTREGUES", COR_VERDE)
        self.lbl_stat_doacoes = criar_card(frame_cards, "DOAÇÕES", "#f59e0b")

        frame_indicadores = tk.Frame(self.tab_dash, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        frame_indicadores.pack(fill="x", padx=30, pady=15)

        self.lbl_taxa_devolucao = tk.Label(frame_indicadores, text="Taxa de Devolução aos Alunos: 0%", font=("Segoe UI", 12, "bold"), bg=COR_BG_CARD, fg=COR_VERDE)
        self.lbl_taxa_devolucao.pack(pady=(12, 6))

        self.lbl_distribuicao_cats = tk.Label(frame_indicadores, text="Categorias mais frequentes: Carregando...", font=("Segoe UI", 10), bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL)
        self.lbl_distribuicao_cats.pack(pady=(0, 12))

        frame_botoes = tk.Frame(self.tab_dash, bg=COR_BG_GERAL)
        frame_botoes.pack(pady=15)
        
        tk.Button(frame_botoes, text="🔄 Atualizar Dados", bg=COR_BG_HEADER, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", command=self.carregar_dashboard).pack(side="left", padx=10)
        tk.Button(frame_botoes, text="📊 Exportar Relatório (CSV)", bg=COR_VERDE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", command=self.exportar_relatorio).pack(side="left", padx=10)

    @assincrono
    def carregar_dashboard(self):
        try:
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/estatisticas", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                data = res.json()
                self.atualizar_graficos(data)
                total = data.get('total_itens', 0)
                entregues = data.get('total_entregues', 0)
                doacoes = data.get('total_doacoes', 0)

                self.lbl_stat_itens.config(text=str(total))
                self.lbl_stat_entregues.config(text=str(entregues))
                self.lbl_stat_doacoes.config(text=str(doacoes))

                soma = total + entregues
                taxa = int((entregues / soma * 100)) if soma > 0 else 0
                self.lbl_taxa_devolucao.config(text=f"Taxa de Devolução aos Alunos: {taxa}% ({entregues} recuperados)")

                ordenadas = sorted(((c['categoria'],int(c['qtd'])) for c in data.get('por_categoria',[])),key=lambda x:(-x[1],x[0]))[:4]
                texto_cats = " | ".join([f"{k}: {v}" for k, v in ordenadas]) if ordenadas else "Sem dados de categorias"
                self.lbl_distribuicao_cats.config(text=f"Categorias em destaque: {texto_cats}")
        except: raise

    def exportar_relatorio(self):
        return self.abrir_relatorios()

    def construir_tab_mural(self):
        frame_top = tk.Frame(self.tab_mural, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        
        tk.Button(frame_top, text="🔄 Atualizar Mural", command=self.carregar_mural, bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(frame_top, text="🗑️ Excluir Relato", command=self.excluir_mural, bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")
        
        colunas = ("ID", "Aluno", "RM", "Categoria", "Descrição", "Data")
        self.tree_mural = ttk.Treeview(self.tab_mural, columns=colunas, show="headings", height=20)
        for col in colunas: self.tree_mural.heading(col, text=col); self.tree_mural.column(col, anchor="center")
        self.tree_mural.column("Descrição", width=420, anchor="w")
        self.tree_mural.pack(fill="both", expand=True, pady=5, padx=12)
        
    @assincrono
    def carregar_mural(self):
        try:
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/mural", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                self.tree_mural.delete(*self.tree_mural.get_children())
                for m in res.json():
                    self.tree_mural.insert("", "end", values=(m['id'], m['nome_aluno'], m['rm_aluno'], m['categoria'], m['descricao'], m['data_registro']))
        except: raise
        
    @assincrono
    def excluir_mural(self):
        selecionado = self.tree_mural.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um relato para excluir.")
        item_id = self.tree_mural.item(selecionado[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"Deseja apagar definitivamente o relato #{item_id}?"):
            try:
                res = (yield Trabalho(requisicao_desktop, 'DELETE', f"{API_URL}/api/mural/{item_id}", headers=self.get_auth_headers()))
                if res.status_code == 200: self.carregar_mural()
            except: raise

    def construir_tab_itens(self):
        frame_top = tk.Frame(self.tab_itens, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)

        tk.Button(frame_top, text="➕ CADASTRAR ITEM", bg="#059669", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=lambda: self.abrir_modal_form()).pack(side="left")
        
        tk.Button(frame_top, text="📄 ETIQUETAS A4 EM LOTE", bg="#7c3aed", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=self.gerar_folha_etiquetas_a4).pack(side="left", padx=8)

        frame_busca = tk.Frame(frame_top, bg=COR_BG_GERAL)
        frame_busca.pack(side="right")

        tk.Label(frame_busca, text="Buscar ID:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9)).pack(side="left")
        self.entry_busca = ttk.Entry(frame_busca, width=12)
        self.entry_busca.pack(side="left", padx=6)
        self.entry_busca.bind("<Return>", lambda e: self.buscar_por_id_direto())

        tk.Label(frame_busca, text="Status:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9)).pack(side="left", padx=(10,0))
        self.combo_filtro_status = ttk.Combobox(frame_busca, values=["TODOS", "DISPONÍVEL", "SOLICITADO", "PARA DOAÇÃO"], state="readonly", width=14)
        self.combo_filtro_status.current(0)
        self.combo_filtro_status.pack(side="left", padx=6)
        self.combo_filtro_status.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtros_tabela())

        tk.Button(frame_busca, text="🔍 Buscar", bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2", command=self.buscar_por_id_direto).pack(side="left", padx=(6,0))
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Local", "Solicitante")
        self.tree_itens = ttk.Treeview(self.tab_itens, columns=colunas, show="headings", height=18)
        for col in colunas:
            self.tree_itens.heading(col, text=col)
            self.tree_itens.column(col, anchor="center")
        
        self.tree_itens.column("ID", width=50)
        self.tree_itens.column("Nome / Descrição", width=280, anchor="w")
        self.tree_itens.column("Solicitante", width=160)
        self.tree_itens.pack(fill="both", expand=True, pady=5, padx=12)

        self.tree_itens.bind("<Double-1>", self.abrir_modal_detalhes_item)
        tk.Label(self.tab_itens, text="💡 Dica: Dê um duplo-clique em um item da lista para visualizar fotos, editar os dados ou dar baixa.", bg=COR_BG_GERAL, fg="#8b949e", font=("Segoe UI", 9, "italic")).pack(pady=6)

    @assincrono
    def carregar_itens(self):
        try:
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/itens", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                self.itens_atuais = res.json()
                self.aplicar_filtros_tabela()
        except Exception as e: messagebox.showerror("Erro de Conexão", f"Não foi possível carregar os itens: {e}")

    def buscar_por_id_direto(self):
        valor=self.entry_busca.get().strip()
        if not valor:return self.aplicar_filtros_tabela()
        self.abrir_objeto_por_etiqueta(valor)

    def aplicar_filtros_tabela(self):
        self.agendar_preferencias()
        status_filtro = self.combo_filtro_status.get().upper()
        self.tree_itens.delete(*self.tree_itens.get_children())
        self.tree_doacoes.delete(*self.tree_doacoes.get_children())

        try:filtrados=filtrar_itens(self.itens_atuais,self.filtros_documento())
        except ValueError as error:self.status_operacao(str(error),erro=True);return
        ids_filtrados={i['id'] for i in filtrados}
        for i in self.itens_atuais:
            st = (i.get('status') or 'DISPONÍVEL').upper()
            nome_exibicao = i.get('nome') or i.get('txt_descricao') or "Sem Título"
            
            if st in ['PARA DOAÇÃO', 'DOAÇÃO FEITA']:
                self.tree_doacoes.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_data', '')))

            if i['id'] not in ids_filtrados:continue
            if status_filtro != "TODOS" and st != status_filtro: continue
            if status_filtro == "TODOS" and st in ['ENTREGUE', 'DOAÇÃO FEITA']: continue 
            solicitante = i.get('solicitado_por')
            solicitante_str = f"{solicitante} (RM: {i.get('rm_aluno', '-')})" if solicitante else "-"
            self.tree_itens.insert("", "end", values=(i['id'], nome_exibicao, i.get('categoria', 'OUTROS'), st, i.get('txt_local', ''), solicitante_str))

    def gerar_folha_etiquetas_a4(self):
        self.etiquetas_lote_desktop()

    def abrir_modal_form(self,item_edit=None):
        return self.abrir_formulario_paridade(item_edit)

    @assincrono
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
        modal.geometry("780x680")
        modal.configure(bg=COR_BG_GERAL)
        modal.transient(self.root)

        nome_titulo = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
        tk.Label(modal, text=nome_titulo, font=("Segoe UI", 16, "bold"), bg=COR_BG_GERAL, fg="#f87171").pack(pady=12)

        frame_info = tk.Frame(modal, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        frame_info.pack(fill="x", padx=20, pady=5)
        st = item.get('status', 'DISPONÍVEL').upper()

        info_texto = f"CATEGORIA: {item.get('categoria', '')}   |   STATUS: {st}\n\nLOCAL: {item.get('txt_local', '')}\nDATA: {item.get('txt_data', '')}\nDESCRIÇÃO: {item.get('txt_descricao', '')}\n"
        if item.get('solicitado_por'): info_texto += f"\n🚨 SOLICITADO POR: {item.get('solicitado_por')} (RM: {item.get('rm_aluno', '')})"

        tk.Label(frame_info, text=info_texto, justify="left", bg=COR_BG_CARD, fg=COR_TEXTO_PRINCIPAL, font=("Segoe UI", 11)).pack(padx=20, pady=15, anchor="w")

        tk.Label(modal, text="Galeria de Fotos:", font=("Segoe UI", 12, "bold"), bg=COR_BG_GERAL, fg=COR_TEXTO_PRINCIPAL).pack(pady=(10, 5), anchor="w", padx=20)
        frame_fotos = tk.Frame(modal, bg=COR_BG_GERAL)
        frame_fotos.pack(fill="both", expand=True, padx=20)

        fotos_array = item.get('fotos', [])
        if not fotos_array and item.get('foto'): fotos_array = [item['foto']]

        if not fotos_array: tk.Label(frame_fotos, text="Nenhuma foto registrada.", bg=COR_BG_GERAL, fg="#8b949e", font=("Segoe UI", 10)).pack(pady=10, anchor="w")
        else:
            for col, foto_url in enumerate(fotos_array):
                try:
                    img=yield Trabalho(baixar_miniatura if foto_url.startswith('http') else baixar_foto_original,foto_url)
                    if img is None:raise ValueError('Foto indisponível')
                    img.thumbnail((160,160));img_tk=ImageTk.PhotoImage(img,master=modal)
                    lbl_img=tk.Label(frame_fotos,image=img_tk,bg=COR_BG_CARD,bd=1,relief='solid',cursor='hand2');lbl_img.image=img_tk
                    lbl_img.bind('<Button-1>',lambda e,url=foto_url:self.ampliar_foto_desktop(url));lbl_img.grid(row=0,column=col,padx=8,pady=5)
                except (ValueError,OSError,requests.RequestException):tk.Label(frame_fotos,text='Foto indisponível',bg=COR_BG_CARD,fg='#f87171').grid(row=0,column=col,padx=8,pady=5)

        frame_acoes = tk.Frame(modal, bg=COR_BG_GERAL)
        frame_acoes.pack(fill="x", pady=20, padx=20)

        def btn(txt, cor, cmd):
            tk.Button(frame_acoes, text=txt, bg=cor, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=8, cursor="hand2", command=cmd).pack(side="left", padx=4, fill="x", expand=True)

        btn("Histórico", COR_AZUL, lambda:self.abrir_historico_objeto(item['id']))
        btn("🖨️ Etiqueta", COR_AZUL, lambda: self.abrir_modal_etiqueta_qr(item))
        btn("✏️ Editar", "#d97706", lambda: [modal.destroy(), self.abrir_modal_form(item)])
        
        if st == 'SOLICITADO': btn("🚫 Recusar", "#b45309", lambda: self.acao_rapida(item['id'], 'recusar', modal))
        if st not in ['ENTREGUE', 'DOAÇÃO FEITA']: btn("✅ Baixa", COR_VERDE, lambda: [modal.destroy(), self.abrir_dar_baixa(item)])
        if st not in ['PARA DOAÇÃO', 'DOAÇÃO FEITA', 'ENTREGUE']: btn("🎁 Doação", "#9333ea", lambda: self.acao_rapida(item['id'], 'doacao', modal))
        btn("🗑️ Excluir", COR_DESTAQUE, lambda: self.acao_rapida(item['id'], 'excluir', modal))

    def abrir_modal_etiqueta_qr(self,item):
        return self.etiqueta_desktop(item)

    @assincrono
    def acao_rapida(self, item_id, acao, modal=None):
        try:
            if acao == 'excluir' and messagebox.askyesno("Excluir", "Deseja excluir este item permanentemente?"):
                res = (yield Trabalho(requisicao_desktop, 'DELETE', f"{API_URL}/api/itens/{item_id}", headers=self.get_auth_headers()))
            elif acao == 'recusar' and messagebox.askyesno("Recusar", "Deseja recusar a solicitação?"):
                res = (yield Trabalho(requisicao_desktop, 'PUT', f"{API_URL}/api/itens/{item_id}/recusar", headers=self.get_auth_headers()))
            elif acao == 'doacao':
                res = (yield Trabalho(requisicao_desktop, 'PUT', f"{API_URL}/api/itens/{item_id}", json={"status": "PARA DOAÇÃO"}, headers=self.get_auth_headers()))
            else: return

            if res.status_code == 200:
                messagebox.showinfo("Sucesso", "Operação realizada!")
                if modal: modal.destroy()
                self.carregar_dados()
            else:
                messagebox.showerror("Erro", "Acesso Negado.")
        except Exception as e: messagebox.showerror("Erro", str(e))

    def abrir_dar_baixa(self, item):
        modal_baixa = tk.Toplevel(self.root)
        modal_baixa.title(f"Dar Baixa - Item #{item['id']}")
        modal_baixa.geometry("460x420")
        modal_baixa.configure(bg=COR_BG_GERAL)
        modal_baixa.transient(self.root)
        modal_baixa.grab_set()

        tk.Label(modal_baixa, text="Registrar Entrega ao Dono", font=("Segoe UI", 14, "bold"), bg=COR_BG_GERAL, fg=COR_VERDE).pack(pady=15)
        
        tk.Label(modal_baixa, text="Nome Completo do Aluno:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_nome = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_nome.insert(0, item.get('solicitado_por') or '')
        entry_nome.pack(padx=35, pady=(0, 10), fill="x")

        tk.Label(modal_baixa, text="RM do Aluno:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_rm = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_rm.insert(0, item.get('rm_aluno') or '')
        entry_rm.pack(padx=35, pady=(0, 10), fill="x")

        tk.Label(modal_baixa, text="Turma / Curso:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=35, pady=(5,2))
        entry_turma = ttk.Entry(modal_baixa, font=("Segoe UI", 11))
        entry_turma.pack(padx=35, pady=(0, 20), fill="x")

        @assincrono
        def confirmar():
            n, r, t = entry_nome.get().strip(), entry_rm.get().strip(), entry_turma.get().strip() or "-"
            if not n or not r: return messagebox.showwarning("Aviso", "Preencha Nome e RM", parent=modal_baixa)
            try:
                res = (yield Trabalho(requisicao_desktop, 'PUT', f"{API_URL}/api/itens/{item['id']}", json={"status": "ENTREGUE", "retirado_por": n, "rm_retirante": r, "turma_curso": t, "funcionario_responsavel": "Secretaria Desktop"}, headers=self.get_auth_headers()))
                if res.status_code == 200:
                    messagebox.showinfo("Sucesso", "Item baixado com sucesso!", parent=modal_baixa)
                    modal_baixa.destroy()
                    self.carregar_dados()
                    nome_obj = item.get('nome') or item.get('txt_descricao') or 'Sem Título'
                    self.abrir_tela_comprovante(item['id'], nome_obj, item.get('txt_descricao') or '', item.get('txt_local') or '', n, r, t,comprovante_id=res.json().get('comprovante_id'))
                else: messagebox.showerror("Erro", "Acesso Negado.", parent=modal_baixa)
            except Exception as e: messagebox.showerror("Erro", str(e), parent=modal_baixa)

        tk.Button(modal_baixa, text="Confirmar e Gerar Comprovante", bg=COR_VERDE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=10, cursor="hand2", command=confirmar).pack(fill="x", padx=35)
        entry_nome.focus()

    def abrir_tela_comprovante(self, item_id, nome_item, desc_item, local_item, retirado_por, rm, turma,comprovante_id=None):
        top_comp = tk.Toplevel(self.root)
        top_comp.title("Comprovante de Retirada")
        top_comp.geometry("650x700")
        top_comp.configure(bg="#e5e7eb") 
        top_comp.transient(self.root)
        top_comp.grab_set()

        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        folha = tk.Frame(top_comp, bg="white", padx=40, pady=30)
        folha.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(folha, text="ETEC PROFº JOSÉ IGNÁCIO AZEVEDO FILHO", font=("Segoe UI", 13, "bold"), bg="white", fg="black").pack()
        tk.Label(folha, text="Sistema de Achados e Perdidos - Termo de Retirada", font=("Segoe UI", 10, "bold"), bg="white", fg="#4b5563").pack(pady=(0, 20))

        f_aluno = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_aluno.pack(fill="x", pady=5)
        tk.Label(f_aluno, text=f"Nome: {retirado_por}\nRM: {rm}\nTurma/Curso: {turma}", font=("Segoe UI", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        f_item = tk.Frame(folha, bg="#f3f4f6", padx=15, pady=10)
        f_item.pack(fill="x", pady=5)
        tk.Label(f_item, text=f"Item #{item_id}: {nome_item}\nLocal Encontrado: {local_item}\nData da Entrega: {data_atual}", font=("Segoe UI", 10), bg="#f3f4f6", fg="black", anchor="w").pack(fill="x")

        def baixar_comprovante_txt():
            file_path = filedialog.asksaveasfilename(parent=top_comp, defaultextension=".txt", initialfile=f"comprovante_{rm}.txt", title="Salvar Comprovante")
            if file_path:
                txt_content = f"ETEC - TERMO DE RETIRADA\nAluno: {retirado_por} (RM: {rm}, Turma: {turma})\nItem #{item_id}: {nome_item}\nData: {data_atual}"
                with open(file_path, "w", encoding="utf-8") as f: f.write(txt_content)
                messagebox.showinfo("Sucesso", "Comprovante salvo!", parent=top_comp)

        b_frame = tk.Frame(top_comp, bg="#e5e7eb")
        b_frame.pack(fill="x", padx=30, pady=(0, 20))
        tk.Button(b_frame, text="📥 BAIXAR TXT", command=baixar_comprovante_txt, bg=COR_AZUL, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 5))
        dados={'item_id':item_id,'nome_item':nome_item,'retirado_por':retirado_por,'rm_retirante':rm,'turma_curso':turma,'data_entrega':data_atual,'funcionario_responsavel':self.perfil_painel.get('email') or 'Secretaria Desktop'}
        tk.Button(b_frame,text='Imprimir comprovante',command=lambda:self.imprimir_comprovante_desktop(dados,recibo=comprovante_id),bg=COR_VERDE,fg='white',font=('Segoe UI',10,'bold'),relief='flat',pady=8,cursor='hand2').pack(side='left',fill='x',expand=True,padx=5)
        tk.Button(b_frame, text="Fechar", command=top_comp.destroy, bg="#475569", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", pady=8, cursor="hand2").pack(side="left", fill="x", expand=True, padx=(5, 0))

    def limpar_impressoes(self):
        for pasta in getattr(self,'impressoes_temporarias',[]):pasta.cleanup()
        self.impressoes_temporarias=[]

    @assincrono
    def imprimir_comprovante_desktop(self,dados,assinatura=None,recibo=None):
        if recibo:
            res=yield Trabalho(self.chamar_api,'GET',f'/api/retiradas/comprovantes/{recibo}',headers=self.get_auth_headers_get());dados=res.json()['comprovante']
            if dados.get('tem_assinatura'):
                res=yield Trabalho(self.chamar_api,'GET',f'/api/retiradas/comprovantes/{recibo}/assinatura',headers=self.get_auth_headers_get());assinatura=res.content
        pasta=yield Trabalho(abrir_impressao_desktop,dados,assinatura)
        self.impressoes_temporarias.append(pasta)
        self.status_operacao('Comprovante aberto no navegador. Clique em Imprimir comprovante e escolha a impressora.')

    @assincrono
    def imprimir_comprovante_historico(self):
        selecionado=self.tree_entregues.selection()
        if not selecionado:return messagebox.showinfo('Selecione uma entrega','Escolha uma entrega para imprimir o comprovante.')
        recibo=self.tree_entregues.item(selecionado[0])['values'][0]
        res=yield Trabalho(requisicao_desktop,'GET',f'{API_URL}/api/retiradas/comprovantes/{recibo}',headers=self.get_auth_headers_get())
        dados=res.json()['comprovante'];assinatura=None
        if dados.get('tem_assinatura'):
            res=yield Trabalho(requisicao_desktop,'GET',f'{API_URL}/api/retiradas/comprovantes/{recibo}/assinatura',headers=self.get_auth_headers_get())
            if res.headers.get('Content-Type','').split(';')[0]!='image/jpeg':raise ValueError('O aceite não pôde ser carregado. Atualize o histórico e tente novamente.')
            assinatura=res.content
        pasta=yield Trabalho(abrir_impressao_desktop,dados,assinatura)
        self.impressoes_temporarias.append(pasta)
        self.status_operacao('Comprovante aberto no navegador. Escolha a impressora ou Salvar como PDF.')

    def construir_tab_doacoes(self):
        frame_top = tk.Frame(self.tab_doacoes, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        tk.Label(frame_top, text="Gerenciamento de Doações", font=("Segoe UI", 14, "bold"), bg=COR_BG_GERAL, fg="#f59e0b").pack(side="left")
        
        @assincrono
        def concluir_doacoes():
            if messagebox.askyesno("Confirmar Doação", "Confirmar a doação dos itens elegíveis? Os registros serão preservados."):
                try:
                    res = (yield Trabalho(requisicao_desktop, 'DELETE', f"{API_URL}/api/itens/doacoes/concluir", headers=self.get_auth_headers()))
                    if not res.ok or res.json().get('success') is not True:
                        return messagebox.showerror('Doação não concluída', 'O servidor não confirmou a operação. Atualize a lista e tente novamente.')
                    messagebox.showinfo("Sucesso", "Doações concluídas!")
                    self.carregar_dados()
                except (requests.RequestException, ValueError):
                    messagebox.showerror('Falha de conexão', 'Não foi possível confirmar a doação. Atualize a lista antes de tentar novamente.')
                
        tk.Button(frame_top, text="🎁 CONCLUIR E LIMPAR DOAÇÕES", bg="#f59e0b", fg="#0d1117", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=concluir_doacoes).pack(side="right")
        
        colunas = ("ID", "Nome / Descrição", "Categoria", "Status", "Data Encontrado")
        self.tree_doacoes = ttk.Treeview(self.tab_doacoes, columns=colunas, show="headings", height=18)
        for col in colunas: self.tree_doacoes.heading(col, text=col); self.tree_doacoes.column(col, anchor="center")
        self.tree_doacoes.pack(fill="both", expand=True, pady=5, padx=12)

    def construir_tab_categorias(self):
        frame_add = tk.Frame(self.tab_categorias, bg=COR_BG_GERAL)
        frame_add.pack(pady=25)
        tk.Label(frame_add, text="Nova Categoria:", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 10, "bold")).pack(side="left", padx=6)
        self.entry_cat = ttk.Entry(frame_add, width=30, font=("Segoe UI", 10))
        self.entry_cat.pack(side="left", padx=6)
        self.entry_cat.bind("<Return>", lambda e: self.adicionar_categoria())
        tk.Button(frame_add, text="Adicionar", bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=5, cursor="hand2", command=self.adicionar_categoria).pack(side="left", padx=6)
        
        self.listbox_cats = tk.Listbox(self.tab_categorias, bg=COR_BG_CARD, fg="white", font=("Segoe UI", 11), height=15, bd=0, highlightthickness=1, highlightbackground=COR_BORDA)
        self.listbox_cats.pack(fill="x", padx=60, pady=15)

    @assincrono
    def carregar_categorias(self):
        try:
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/categorias"))
            if res.status_code == 200:
                self.listbox_cats.delete(0, tk.END)
                self.categorias_atuais = []
                for c in res.json():
                    self.listbox_cats.insert(tk.END, f"   • {c['nome']}")
                    self.categorias_atuais.append(c['nome'])
        except: raise

    @assincrono
    def adicionar_categoria(self):
        nome = self.entry_cat.get().strip().upper()
        if nome:
            try:
                res = (yield Trabalho(requisicao_desktop, 'POST', f"{API_URL}/api/categorias", json={"nome": nome}, headers=self.get_auth_headers()))
                if res.status_code == 200:
                    self.entry_cat.delete(0, tk.END)
                    self.carregar_categorias()
            except: raise

    def construir_tab_entregues(self):
        frame_top = tk.Frame(self.tab_entregues, bg=COR_BG_GERAL)
        frame_top.pack(fill="x", pady=12, padx=12)
        
        tk.Button(frame_top, text="🔄 Atualizar Histórico", command=self.carregar_entregues, bg=COR_AZUL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(frame_top, text="🗑️ Excluir objeto", command=self.excluir_entregue, bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=(10, 0))
        tk.Button(frame_top, text="↩️ Desfazer Entrega", command=self.desfazer_entrega, bg="#d97706", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right")

        tk.Button(frame_top,text='Comprovante / Imprimir',command=self.imprimir_comprovante_historico,bg=COR_VERDE,fg='white',relief='flat',padx=10,pady=6).pack(side='left',padx=8)
        self.incluir_canceladas=tk.BooleanVar(value=False)
        tk.Checkbutton(frame_top,text='Mostrar revertidas',variable=self.incluir_canceladas,command=self.carregar_entregues,bg=COR_BG_GERAL,fg=COR_TEXTO_PRINCIPAL,selectcolor=COR_BG_CARD).pack(side='left')
        colunas = ("Recibo", "ID Item", "Item", "Retirado Por", "RM", "Turma", "Data")
        self.tree_entregues = ttk.Treeview(self.tab_entregues, columns=colunas, show="headings", height=18)
        for col in colunas: self.tree_entregues.heading(col, text=col); self.tree_entregues.column(col, anchor="center")
        self.tree_entregues.pack(fill="both", expand=True, pady=5, padx=12)
        self.tree_entregues.bind("<Double-1>", self.abrir_detalhes_do_historico)

    @assincrono
    def carregar_entregues(self):
        if not TOKEN_SECRETARIA: return
        try:
            sufixo='?incluir_canceladas=true' if getattr(self,'incluir_canceladas',None) and self.incluir_canceladas.get() else ''
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/entregues{sufixo}", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                self.tree_entregues.delete(*self.tree_entregues.get_children())
                linhas=res.json();self.historico_entregues={str(e['id']):e for e in linhas}
                for e in linhas:
                    self.tree_entregues.insert("", "end", values=(e['id'], e['item_id'], e['nome_item']+(' [REVERTIDA]' if e.get('cancelada_em') else ''), e['retirado_por'], e['rm_retirante'], e['turma_curso'], e['data_entrega']))
        except: raise

    def abrir_detalhes_do_historico(self, event):
        selecionado = self.tree_entregues.selection()
        if selecionado:
            item_id = self.tree_entregues.item(selecionado[0])['values'][1]
            item = next((i for i in self.itens_atuais if str(i['id']) == str(item_id)), None)
            if item: self.abrir_modal_detalhes_item(item_direto=item)

    @assincrono
    def desfazer_entrega(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        recibo=self.tree_entregues.item(selecionado[0], "values")[0]
        if getattr(self,"historico_entregues",{}).get(str(recibo),{}).get("cancelada_em"):
            return messagebox.showwarning("Histórico", "Esta entrega já foi revertida.")
        vals = self.tree_entregues.item(selecionado[0], "values")[1]
        if messagebox.askyesno("Desfazer", f"Reverter entrega do item #{vals}?"):
            try:
                res = (yield Trabalho(requisicao_desktop, 'PUT', f"{API_URL}/api/itens/{vals}/recusar", headers=self.get_auth_headers(),json={"entrega_id":recibo}))
                if res.status_code == 200: self.carregar_dados()
            except: raise

    @assincrono
    def excluir_entregue(self):
        selecionado = self.tree_entregues.selection()
        if not selecionado: return messagebox.showwarning("Aviso", "Selecione um item.")
        vals = self.tree_entregues.item(selecionado[0], "values")[1]
        if messagebox.askyesno("Excluir", f"Excluir permanentemente o objeto #{vals} e seu histórico de entregas?"):
            try:
                res = (yield Trabalho(requisicao_desktop, 'DELETE', f"{API_URL}/api/itens/{vals}", headers=self.get_auth_headers()))
                if res.status_code == 200: self.carregar_dados()
            except: raise

    def construir_tab_chat(self):
        frame_esq = tk.Frame(self.tab_chat, bg=COR_BG_GERAL, width=280)
        frame_esq.pack(side="left", fill="y", padx=12, pady=12)
        
        tk.Label(frame_esq, text="Conversas Ativas", bg=COR_BG_GERAL, fg="white", font=("Segoe UI", 12, "bold")).pack(pady=(0, 8))
        self.listbox_chat = tk.Listbox(frame_esq, bg=COR_BG_CARD, fg="white", font=("Segoe UI", 10), bd=0, highlightthickness=1, highlightbackground=COR_BORDA)
        self.listbox_chat.pack(fill="both", expand=True)
        self.listbox_chat.bind("<<ListboxSelect>>", self.selecionar_conversa)
        
        frame_dir = tk.Frame(self.tab_chat, bg=COR_BG_CARD, highlightbackground=COR_BORDA, highlightthickness=1)
        frame_dir.pack(side="right", fill="both", expand=True, padx=12, pady=12)
        
        self.lbl_chat_titulo = tk.Label(frame_dir, text="Selecione um aluno para iniciar", bg=COR_BG_CARD, fg="#f87171", font=("Segoe UI", 13, "bold"))
        self.lbl_chat_titulo.pack(pady=12)
        
        self.txt_mensagens = tk.Text(frame_dir, bg=COR_BG_GERAL, fg="white", state="disabled", wrap="word", font=("Segoe UI", 11), bd=0)
        self.txt_mensagens.pack(fill="both", expand=True, padx=12, pady=5)
        
        frame_input = tk.Frame(frame_dir, bg=COR_BG_CARD)
        frame_input.pack(fill="x", padx=12, pady=12)
        
        self.entry_chat = ttk.Entry(frame_input, font=("Segoe UI", 11))
        self.entry_chat.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_chat.bind("<Return>", lambda e: self.enviar_mensagem())
        
        tk.Button(frame_input, text="Enviar", bg=COR_DESTAQUE, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=self.enviar_mensagem).pack(side="right")
        self.atualizar_chat_continuo()

    @assincrono
    def carregar_conversas(self):
        if not TOKEN_SECRETARIA: return
        try:
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}/api/chat/conversas", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                self.conversas_atuais=res.json()
                self.filtrar_conversas()
        except: raise

    def selecionar_conversa(self, event):
        selecao = self.listbox_chat.curselection()
        if selecao:
            idx = selecao[0]
            conta = self.mapa_conversas[idx]
            self.rm_chat_ativo = conta['rm_aluno']
            self.email_chat_ativo = conta.get('email_aluno')
            self.chat_legado = not self.email_chat_ativo
            self.entry_chat.config(state='disabled' if self.chat_legado else 'normal')
            self.lbl_chat_titulo.config(text=f"Chat com: {self.listbox_chat.get(idx)}")
            self.carregar_mensagens_aluno()

    @assincrono
    def carregar_mensagens_aluno(self):
        if not self.rm_chat_ativo: return
        try:
            caminho = f"/api/chat/legado/{quote(str(self.rm_chat_ativo),safe='')}" if self.chat_legado else f"/api/chat/mensagens/{quote(str(self.rm_chat_ativo),safe='')}?{urlencode({'email':self.email_chat_ativo,'marcar_lida':'true'})}"
            res = (yield Trabalho(requisicao_desktop, 'GET', f"{API_URL}{caminho}", headers=self.get_auth_headers_get()))
            if res.status_code == 200:
                self.txt_mensagens.config(state="normal")
                self.txt_mensagens.delete("1.0", tk.END)
                for m in res.json():
                    remetente = "Secretaria" if m['remetente'] == "SECRETARIA" else m['nome_aluno']
                    self.txt_mensagens.insert(tk.END, f"[{m['data_envio']}] {remetente}:\n{m['mensagem']}\n\n")
                self.txt_mensagens.see(tk.END)
                self.txt_mensagens.config(state="disabled")
        except: raise

    @assincrono
    def enviar_mensagem(self):
        if not self.rm_chat_ativo or self.chat_legado or not self.entry_chat.get().strip(): return
        destino=self.email_chat_ativo
        try:
            res = (yield Trabalho(requisicao_desktop, 'POST', f"{API_URL}/api/chat/enviar", headers=self.get_auth_headers(), json={"rm": self.rm_chat_ativo, "email":self.email_chat_ativo, "nome": "Secretaria", "remetente": "SECRETARIA", "mensagem": self.entry_chat.get().strip()}))
            if res.status_code == 200:
                if destino!=self.email_chat_ativo:return
                self.entry_chat.delete(0, tk.END)
                self.carregar_mensagens_aluno()
        except: raise

    def atualizar_chat_continuo(self):
        if TOKEN_SECRETARIA:
            self.carregar_conversas()
            if self.rm_chat_ativo: self.carregar_mensagens_aluno()
        self.chat_timer = self.root.after(3000, self.atualizar_chat_continuo)

if __name__ == "__main__":
    root = tk.Tk()
    app = SecretariaApp(root)
    root.mainloop()

