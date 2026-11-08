"""Abas e histórico da equipe; todo HTTP continua nos workers do desktop."""
import json
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from urllib.parse import quote,urlencode
from desktop_tasks import Trabalho,assincrono

BG='#0d1117';CARD='#161b22';FG='#c9d1d9';BLUE='#1f6feb';GREEN='#059669';RED='#dc2626'


class ModeracaoDesktop:
    def construir_tab_moderacao(self):
        self.pendentes_desktop=[];self.proximo_pendente=None
        top=tk.Frame(self.tab_moderacao,bg=BG);top.pack(fill='x',padx=12,pady=12)
        tk.Label(top,text='Cadastros dos alunos',bg=BG,fg=FG,font=('Segoe UI',13,'bold')).pack(side='left')
        self.filtro_moderacao=ttk.Combobox(top,values=['PENDENTE','RECUSADO'],state='readonly',width=15);self.filtro_moderacao.set('PENDENTE');self.filtro_moderacao.pack(side='left',padx=12)
        self.filtro_moderacao.bind('<<ComboboxSelected>>',lambda e:self.carregar_moderacao())
        tk.Button(top,text='Atualizar',command=self.carregar_moderacao).pack(side='right')
        columns=('ID','Objeto','Categoria','Data','Local','Situação')
        self.tree_moderacao=ttk.Treeview(self.tab_moderacao,columns=columns,show='headings',height=15)
        for col in columns:self.tree_moderacao.heading(col,text=col);self.tree_moderacao.column(col,width=120,anchor='w')
        self.tree_moderacao.column('ID',width=50);self.tree_moderacao.column('Objeto',width=250)
        self.tree_moderacao.pack(fill='both',expand=True,padx=12,pady=5);self.tree_moderacao.bind('<Double-1>',lambda e:self.ver_cadastro_moderacao())
        actions=tk.Frame(self.tab_moderacao,bg=BG);actions.pack(fill='x',padx=12,pady=12)
        for text,cmd in [('Conferir cadastro / fotos',self.ver_cadastro_moderacao),('Aprovar',self.aprovar_cadastro_desktop),('Pedir correção',self.recusar_cadastro_desktop),('Histórico do objeto',self.historico_cadastro_desktop)]:tk.Button(actions,text=text,command=cmd).pack(side='left',padx=4)
        self.btn_mais_moderacao=tk.Button(actions,text='Ver anteriores',command=lambda:self.carregar_moderacao(True),state='disabled');self.btn_mais_moderacao.pack(side='right')

    @assincrono
    def carregar_moderacao(self,mais=False):
        estado=self.filtro_moderacao.get()
        params={'estado':estado}
        if mais and self.proximo_pendente:params['antes']=self.proximo_pendente
        res=yield Trabalho(self.chamar_api,'GET','/api/moderacao/cadastros?'+urlencode(params),headers=self.get_auth_headers_get())
        data=res.json()
        if self.filtro_moderacao.get()!=estado:return
        self.pendentes_desktop=(self.pendentes_desktop if mais else [])+data['cadastros']
        self.proximo_pendente=data['proximo'];self.btn_mais_moderacao.configure(state='normal' if data['tem_mais'] else 'disabled')
        self.tree_moderacao.delete(*self.tree_moderacao.get_children())
        for item in self.pendentes_desktop:self.tree_moderacao.insert('','end',iid=str(item['id']),values=(item['id'],item['nome'],item['categoria'],item['txt_data'],item['txt_local'],'Correção solicitada' if item.get('recusado_em') else 'Aguardando análise'))

    def cadastro_selecionado(self):
        selected=self.tree_moderacao.selection()
        if not selected:messagebox.showinfo('Selecione um cadastro','Escolha um objeto na lista de moderação.');return None
        return next((i for i in self.pendentes_desktop if str(i['id'])==selected[0]),None)

    def ver_cadastro_moderacao(self):
        item=self.cadastro_selecionado()
        if not item:return
        modal=tk.Toplevel(self.root);modal.title('Cadastro #'+str(item['id']));modal.geometry('720x600');modal.configure(bg=BG);modal.transient(self.root)
        text=f"{item['nome']}\n\nCategoria: {item['categoria']}\nLocal: {item['txt_local']}\nData: {item['txt_data']}\n\n{item['txt_descricao']}"
        if item.get('motivo_recusa'):text+='\n\nOrientação ao aluno: '+item['motivo_recusa']
        area=tk.Text(modal,wrap='word',height=13,bg=CARD,fg=FG,font=('Segoe UI',11));area.pack(fill='x',padx=15,pady=15);area.insert('1.0',text);area.configure(state='disabled')
        photos=tk.Frame(modal,bg=BG);photos.pack(fill='both',expand=True,padx=15)
        self.carregar_fotos_moderacao(modal,photos,item)

    @assincrono
    def carregar_fotos_moderacao(self,modal,photos,item):
        fotos=item.get('fotos') or ([item['foto']] if item.get('foto') else [])
        if not fotos:tk.Label(photos,text='Nenhuma foto cadastrada.',bg=BG,fg=FG).pack()
        for col,url in enumerate(fotos[:4]):
            image=yield Trabalho(self.baixar_imagem,url)
            if image is None:tk.Label(photos,text='Foto indisponível',bg=BG,fg=FG).grid(row=0,column=col,padx=5);continue
            from PIL import ImageTk
            photo=ImageTk.PhotoImage(image);label=tk.Label(photos,image=photo,bg=CARD);label.image=photo;label.grid(row=0,column=col,padx=5)

    def revisar_duplicidade_desktop(self,payload):
        res=yield Trabalho(self.chamar_api,'POST','/api/itens/duplicados',json=payload,headers=self.get_auth_headers())
        rows=res.json()['duplicados']
        if not rows:return True,False
        text='Foram encontrados objetos parecidos:\n\n'+'\n'.join(f"#{r['id']} · {r['nome']} · {r['txt_data']} · {r['status']}" for r in rows)
        text+='\n\nObjetos parecidos podem ser diferentes. Você conferiu e deseja publicar mesmo assim?'
        return messagebox.askyesno('Conferir possível duplicidade',text),True

    @assincrono
    def aprovar_cadastro_desktop(self):
        item=self.cadastro_selecionado()
        if not item:return
        permitir,duplicado=yield from self.revisar_duplicidade_desktop({'id':item['id'],'nome':item['nome'],'categoria':item['categoria'],'data':item['txt_data']})
        if not permitir:return
        yield Trabalho(self.chamar_api,'PUT',f"/api/itens/{item['id']}/aprovar",json={'versao':item['versao'],'confirmar_duplicado':duplicado},headers=self.get_auth_headers())
        messagebox.showinfo('Aprovado','Objeto publicado no catálogo.');self.carregar_moderacao();self.carregar_itens()

    @assincrono
    def recusar_cadastro_desktop(self):
        item=self.cadastro_selecionado()
        if not item:return
        motivo=simpledialog.askstring('Pedir correção ao aluno','Explique o que precisa ser corrigido (5 a 1000 caracteres):',initialvalue=item.get('motivo_recusa') or '',parent=self.root)
        if motivo is None:return
        motivo=motivo.strip()
        if not 5<=len(motivo)<=1000:messagebox.showwarning('Motivo necessário','Explique a correção com 5 a 1000 caracteres.');return
        yield Trabalho(self.chamar_api,'PUT',f"/api/itens/{item['id']}/recusar",json={'versao':item['versao'],'motivo':motivo},headers=self.get_auth_headers())
        messagebox.showinfo('Orientação enviada','O cadastro e as fotos foram preservados. O aluno poderá corrigir e reenviar.');self.carregar_moderacao()

    def historico_cadastro_desktop(self):
        item=self.cadastro_selecionado()
        if item:self.abrir_historico_objeto(item['id'])

    def construir_tab_professores(self):
        self.professores_desktop=[]
        tk.Label(self.tab_professores,text='Acesso de professores — exclusivo da secretaria titular',bg=BG,fg=FG,font=('Segoe UI',13,'bold')).pack(anchor='w',padx=12,pady=12)
        top=tk.Frame(self.tab_professores,bg=BG);top.pack(fill='x',padx=12,pady=6)
        tk.Button(top,text='Atualizar solicitações',command=self.carregar_professores).pack(side='left')
        cols=('Nome','E-mail','Situação','Solicitado em')
        self.tree_professores=ttk.Treeview(self.tab_professores,columns=cols,show='headings')
        for col in cols:self.tree_professores.heading(col,text=col);self.tree_professores.column(col,width=180)
        self.tree_professores.column('E-mail',width=280);self.tree_professores.pack(fill='both',expand=True,padx=12,pady=12)
        actions=tk.Frame(self.tab_professores,bg=BG);actions.pack(fill='x',padx=12,pady=12)
        for action,text in [('APROVAR','Aprovar acesso'),('RECUSAR','Recusar pedido'),('REVOGAR','Revogar acesso')]:tk.Button(actions,text=text,command=lambda a=action:self.decidir_professor_desktop(a)).pack(side='left',padx=5)

    @assincrono
    def carregar_professores(self):
        res=yield Trabalho(self.chamar_api,'GET','/api/secretaria/professores',headers=self.get_auth_headers_get())
        self.professores_desktop=res.json()['solicitacoes'];self.tree_professores.delete(*self.tree_professores.get_children())
        for row in self.professores_desktop:self.tree_professores.insert('','end',iid=row['email'],values=(row['nome'],row['email'],row['status'],row.get('data_solicitacao','')))

    @assincrono
    def decidir_professor_desktop(self,acao):
        selected=self.tree_professores.selection()
        if not selected:messagebox.showinfo('Selecione um professor','Escolha uma solicitação na lista.');return
        email=selected[0];row=next((r for r in self.professores_desktop if r['email']==email),None)
        origem='APROVADO' if acao=='REVOGAR' else 'PENDENTE'
        if not row or row['status']!=origem:messagebox.showinfo('Atualize a lista','Essa ação não se aplica à situação atual.');return
        if not messagebox.askyesno('Confirmar alteração',f"{acao.title()} o acesso de {email}? A autorização permite operar itens e registrar entregas."):return
        yield Trabalho(self.chamar_api,'PUT','/api/secretaria/professores/'+quote(email,safe='')+'/acesso',json={'acao':acao},headers=self.get_auth_headers())
        self.carregar_professores();messagebox.showinfo('Acesso atualizado','A decisão foi registrada pelo servidor.')

    def abrir_historico_objeto(self,item_id):
        modal=tk.Toplevel(self.root);modal.title(f'Histórico do objeto #{item_id}');modal.geometry('790x600');modal.configure(bg=BG);modal.transient(self.root)
        text=tk.Text(modal,wrap='word',bg=CARD,fg=FG,font=('Segoe UI',10));text.pack(fill='both',expand=True,padx=12,pady=12)
        more=tk.Button(modal,text='Carregar anteriores',state='disabled');more.pack(pady=8)
        self.carregar_historico_objeto(modal,text,more,item_id)

    @assincrono
    def carregar_historico_objeto(self,modal,text,more,item_id,antes=None):
        path=f'/api/itens/{item_id}/ocorrencias'+('?antes='+str(antes) if antes else '')
        res=yield Trabalho(self.chamar_api,'GET',path,headers=self.get_auth_headers_get());data=res.json()
        text.configure(state='normal')
        if not antes:text.delete('1.0','end')
        for row in data['ocorrencias']:
            text.insert('end',f"{row['criada_em']} · {row['ator_id']} · {row['perfil']}\n")
            text.insert('end',{'INSERT':'Cadastro','UPDATE':'Alteração','DELETE':'Exclusão','REV_DUPLIC':'Duplicidade conferida'}.get(row['acao'],row['acao'])+'\n')
            for change in row.get('alteracoes',[]):text.insert('end',f"{change['campo']}: {change['antes']} → {change['depois']}\n")
            if not row.get('alteracoes'):text.insert('end',f"Antes: {row.get('anterior')}\nDepois: {row.get('atual')}\n")
            text.insert('end','\n')
        if not data['ocorrencias'] and not antes:text.insert('end','Nenhuma ocorrência registrada para esse objeto.\n')
        text.configure(state='disabled')
        more.configure(state='normal' if data['tem_mais'] else 'disabled',command=lambda:self.carregar_historico_objeto(modal,text,more,item_id,data['ocorrencias'][-1]['id']))
