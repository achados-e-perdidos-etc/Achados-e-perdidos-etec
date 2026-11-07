"""Recursos administrativos equivalentes aos da secretaria web."""
import base64,io,uuid
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from datetime import datetime
from urllib.parse import urlencode,quote
from PIL import Image,ImageDraw,ImageTk
from desktop_tasks import Trabalho,assincrono
from utils.catalogo import normalizar
from utils.ferramentas import filtrar_itens,id_etiqueta,TIPOS
from utils.comprovantes import abrir_documento_local
from utils.exportacao import salvar_csv
from utils import preferencias_desktop

BG='#0d1117';CARD='#161b22';FG='#c9d1d9';BLUE='#1f6feb';GREEN='#059669'


class FerramentasDesktop:
    def limpar_recursos_paridade(self):
        self.guardar_preferencias_desktop()
        for nome in ['timer_prioridades','timer_preferencias']:
            timer=getattr(self,nome,None)
            if timer:
                try:self.root.after_cancel(timer)
                except tk.TclError:pass
            setattr(self,nome,None)
        for camera in list(getattr(self,'cameras',[])):camera.fechar()
        for upload in list(getattr(self,'uploads_abertos',[])):upload.fechar()
        self.cameras=[];self.uploads_abertos=[];self.rascunho_item=None

    def janela_ferramenta(self,titulo,geometry='660x650'):
        modal=tk.Toplevel(self.root);modal.title(titulo);modal.geometry(geometry);modal.configure(bg=BG);modal.transient(self.root)
        return modal

    def campo_ferramenta(self,pai,texto,valor='',combo=None):
        frame=tk.Frame(pai,bg=BG);frame.pack(fill='x',padx=18,pady=6)
        tk.Label(frame,text=texto,bg=BG,fg=FG,anchor='w').pack(fill='x')
        campo=ttk.Combobox(frame,values=combo,state='readonly') if combo is not None else ttk.Entry(frame)
        if combo is not None:campo.set(valor)
        else:campo.insert(0,valor)
        campo.pack(fill='x',pady=3);return campo

    def construir_ferramentas(self):
        self.rascunho_item=None;self.cameras=[]
        frame=tk.Frame(self.tab_dash,bg=BG);frame.pack(fill='x',padx=22,pady=8)
        for label,fn in [('Retirada com código',self.abrir_retirada_codigo),('Relatórios PDF / CSV',self.abrir_relatorios),('Ocorrências por ID',self.consultar_ocorrencias),('Ler etiqueta QR',self.abrir_leitor_qr)]:ttk.Button(frame,text=label,command=fn).pack(side='left',padx=4)
        self.lbl_disponiveis=tk.Label(self.tab_dash,text='Disponíveis: — · Solicitados: —',bg=BG,fg=FG);self.lbl_disponiveis.pack(pady=6)
        graficos=tk.Frame(self.tab_dash,bg=BG);graficos.pack(fill='both',expand=True,padx=22,pady=10)
        self.graficos={}
        for chave,titulo in [('por_categoria','Objetos por categoria'),('por_local','Locais com mais ocorrências')]:
            box=tk.Frame(graficos,bg=CARD);box.pack(side='left',fill='both',expand=True,padx=5)
            tk.Label(box,text=titulo,bg=CARD,fg=FG).pack(pady=8)
            canvas=tk.Canvas(box,bg=CARD,highlightthickness=0,height=180);barra=ttk.Scrollbar(box,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=barra.set);barra.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            self.graficos[chave]=canvas
        frame=tk.Frame(self.tab_itens,bg=BG);frame.pack(fill='x',before=self.tree_itens,padx=12,pady=4)
        self.filtros_estoque={}
        for chave,label in [('q','Nome / descrição'),('categoria','Categoria'),('local','Local'),('inicio','Desde (AAAA-MM-DD)'),('fim','Até (AAAA-MM-DD)')]:
            col=tk.Frame(frame,bg=BG);col.pack(side='left',fill='x',expand=True,padx=3)
            tk.Label(col,text=label,bg=BG,fg=FG,font=('Segoe UI',8)).pack(anchor='w')
            campo=ttk.Entry(col,width=16);campo.pack(fill='x');campo.bind('<KeyRelease>',lambda e:self.aplicar_filtros_tabela());self.filtros_estoque[chave]=campo
        ttk.Button(frame,text='Limpar',command=self.limpar_filtros_estoque).pack(side='left',padx=4)
        ttk.Button(frame,text='Atualizar',command=self.carregar_itens).pack(side='left',padx=4)
        tk.Label(self.tab_chat,text='As mensagens são apagadas após 30 dias.',bg=BG,fg=FG).pack(side='bottom',pady=4)
        self.combo_filtro_status.configure(values=['TODOS','DISPONÍVEL','SOLICITADO','ENTREGUE','PARA DOAÇÃO','DOAÇÃO FEITA'])
        ttk.Button(self.tab_categorias,text='Excluir categoria selecionada',command=self.remover_categoria_desktop).pack(pady=8)
        ttk.Button(self.tab_mural,text='Comparar com objetos / preparar entrega',command=self.comparar_mural).pack(pady=6)
        pesquisa=tk.StringVar();entry=ttk.Entry(self.listbox_chat.master,textvariable=pesquisa);entry.pack(fill='x',before=self.listbox_chat,pady=5);self.busca_conversas=pesquisa
        pesquisa.trace_add('write',lambda *a:self.filtrar_conversas());self.conversas_atuais=[]
        self.construir_preferencias_atalhos()

    def construir_preferencias_atalhos(self):
        box=tk.Frame(self.tab_dash,bg=BG);box.pack(fill='x',before=self.lbl_disponiveis,padx=22,pady=6)
        self.botoes_prioridades={}
        for chave,texto,aba in [('pendentes','Cadastros para analisar','moderacao'),('retiradas','Retiradas solicitadas','itens'),('mensagens','Mensagens não lidas','chat')]:
            b=ttk.Button(box,text=texto+': —',command=lambda a=aba:self.abrir_prioridade(a));b.pack(side='left',fill='x',expand=True,padx=3);self.botoes_prioridades[chave]=(b,texto)
        ttk.Button(box,text='Atualizar atalhos',command=self.atualizar_prioridades).pack(side='left',padx=3)
        self.lbl_prioridades=tk.Label(self.tab_dash,text='Consultando prioridades…',bg=BG,fg=FG);self.lbl_prioridades.pack(before=self.lbl_disponiveis)
        self.preferencias_email=self.perfil_painel.get('email')
        dados=preferencias_desktop.ler(self.preferencias_email) if self.preferencias_email else {}
        for k,v in dados.get('filtros',{}).items():
            if k in self.filtros_estoque:self.filtros_estoque[k].insert(0,v)
        status=dados.get('filtros',{}).get('status','TODOS');self.combo_filtro_status.set(status if status in self.combo_filtro_status['values'] else 'TODOS')
        for col,width in dados.get('larguras',{}).items():
            if col in self.tree_itens['columns']:self.tree_itens.column(col,width=width)
        self.tree_itens.bind('<ButtonRelease-1>',lambda e:self.agendar_preferencias(),add='+')
        self.timer_preferencias=None;self.timer_prioridades=None
        def ciclo():
            self.atualizar_prioridades();self.timer_prioridades=self.root.after(60000,ciclo)
        self.timer_prioridades=self.root.after(60000,ciclo)

    def agendar_preferencias(self):
        if not getattr(self,'preferencias_email',None):return
        if getattr(self,'timer_preferencias',None):self.root.after_cancel(self.timer_preferencias)
        self.timer_preferencias=self.root.after(350,self.guardar_preferencias_desktop)

    def guardar_preferencias_desktop(self):
        timer=getattr(self,'timer_preferencias',None)
        if timer:
            try:self.root.after_cancel(timer)
            except tk.TclError:pass
        self.timer_preferencias=None
        if not getattr(self,'preferencias_email',None):return
        try:
            dados={'filtros':{**self.filtros_documento(),'status':self.combo_filtro_status.get()},'larguras':{col:self.tree_itens.column(col,'width') for col in self.tree_itens['columns']}}
            if not preferencias_desktop.salvar(self.preferencias_email,dados):self.status_operacao('Preferências válidas nesta sessão; não foi possível salvar no computador.',erro=True)
        except tk.TclError:pass

    def abrir_prioridade(self,aba):
        if aba=='itens':self.limpar_filtros_estoque();self.combo_filtro_status.set('SOLICITADO');self.aplicar_filtros_tabela()
        elif aba=='moderacao':self.filtro_moderacao.set('PENDENTE');self.carregar_moderacao()
        elif aba=='chat':self.busca_conversas.set('');self.carregar_conversas()
        self.notebook.select(getattr(self,'tab_'+aba))

    @assincrono
    def atualizar_prioridades(self):
        try:
            res=yield Trabalho(self.chamar_api,'GET','/api/secretaria/resumo',headers=self.get_auth_headers_get());data=res.json()
            for k,(botao,texto) in self.botoes_prioridades.items():botao.configure(text=f'{texto}: {data[k]}')
            self.lbl_prioridades.configure(text='Atualizado às '+datetime.now().strftime('%H:%M'))
        except Exception:
            for botao,texto in self.botoes_prioridades.values():botao.configure(text=texto+': —')
            self.lbl_prioridades.configure(text='Não foi possível atualizar as prioridades. Tente novamente.')

    def limpar_filtros_estoque(self):
        for campo in self.filtros_estoque.values():campo.delete(0,tk.END)
        self.combo_filtro_status.set('TODOS');self.aplicar_filtros_tabela()

    def filtros_documento(self):
        return {k:c.get().strip() for k,c in getattr(self,'filtros_estoque',{}).items()}

    def atualizar_graficos(self,data):
        if not hasattr(self,'graficos'):return
        self.lbl_disponiveis.configure(text=f"Disponíveis: {data.get('total_disponiveis',0)} · Solicitados: {data.get('total_solicitados',0)}")
        for chave,canvas in self.graficos.items():
            rows=data.get(chave,[]);canvas.delete('all');largura=max(canvas.winfo_width(),380);maior=max([int(r['qtd']) for r in rows] or [1]);maior=max(maior,1)
            for idx,row in enumerate(rows):
                nome=row.get('categoria') or row.get('local') or 'Não informado';y=10+idx*26
                canvas.create_text(8,y+9,text=nome[:22],fill=FG,anchor='w',font=('Segoe UI',9))
                width=max(1,(largura-210)*int(row['qtd'])/maior);canvas.create_rectangle(165,y,165+width,y+17,fill=BLUE,outline='');canvas.create_text(172+width,y+9,text=str(row['qtd']),fill=FG,anchor='w')
            canvas.configure(scrollregion=(0,0,largura,max(180,len(rows)*26+15)))

    def consultar_ocorrencias(self):
        valor=simpledialog.askstring('Histórico do objeto','ID do objeto:',parent=self.root)
        if valor is None:return
        try:self.abrir_historico_objeto(id_etiqueta(valor))
        except ValueError as error:messagebox.showwarning('ID inválido',str(error))

    @assincrono
    def remover_categoria_desktop(self):
        selecionado=self.listbox_cats.curselection()
        if not selecionado:return messagebox.showinfo('Categoria','Selecione uma categoria.')
        nome=self.categorias_atuais[selecionado[0]]
        if not messagebox.askyesno('Excluir categoria',f'Excluir {nome}? Os objetos anteriores continuam preservados.'):return
        yield Trabalho(self.chamar_api,'DELETE','/api/categorias/'+quote(nome,safe=''),headers=self.get_auth_headers())
        self.carregar_categorias()

    def abrir_relatorios(self):
        modal=self.janela_ferramenta('Relatórios para impressão e planilha','520x590')
        tipo=self.campo_ferramenta(modal,'Tipo','INVENTARIO',list(TIPOS));inicio=self.campo_ferramenta(modal,'Data inicial (AAAA-MM-DD)');fim=self.campo_ferramenta(modal,'Data final (AAAA-MM-DD)')
        categoria=self.campo_ferramenta(modal,'Categoria',self.filtros_documento().get('categoria') or 'TODOS',['TODOS',*self.categorias_atuais]);local=self.campo_ferramenta(modal,'Local');busca=self.campo_ferramenta(modal,'Buscar nome, descrição ou pessoa')
        for campo,chave in [(inicio,'inicio'),(fim,'fim'),(local,'local'),(busca,'q')]:campo.insert(0,self.filtros_documento().get(chave,''))
        revertidas=tk.BooleanVar(value=False);tk.Checkbutton(modal,text='Incluir entregas revertidas',variable=revertidas,bg=BG,fg=FG,selectcolor=CARD).pack(pady=7)
        @assincrono
        def gerar(csv=False):
            filtros=dict(tipo=tipo.get(),inicio=inicio.get(),fim=fim.get(),categoria=categoria.get(),local=local.get(),q=busca.get(),revertidas=str(revertidas.get()).lower())
            caminho=None
            if csv:
                caminho=filedialog.asksaveasfilename(parent=modal,defaultextension='.csv',initialfile='relatorio-'+tipo.get().lower()+'.csv')
                if not caminho:return
            res=yield Trabalho(self.chamar_api,'GET','/api/secretaria/documentos?'+urlencode(filtros),headers=self.get_auth_headers_get());data=res.json()
            if csv:yield Trabalho(salvar_csv,caminho,data['cabecalho'],data['linhas']);messagebox.showinfo('Planilha salva',caminho,parent=modal)
            else:
                pasta=yield Trabalho(abrir_documento_local,data['html']);self.impressoes_temporarias.append(pasta)
        ttk.Button(modal,text='Imprimir / salvar como PDF',command=gerar).pack(fill='x',padx=18,pady=6)
        ttk.Button(modal,text='Baixar CSV',command=lambda:gerar(True)).pack(fill='x',padx=18,pady=6)

    def etiquetas_lote_desktop(self):
        modal=self.janela_ferramenta('Etiquetas em lote','440x300');pagina=self.campo_ferramenta(modal,'Página da folha PNG','1')
        ttk.Button(modal,text='Imprimir todas as páginas / PDF',command=lambda:self.documento_desktop('ETIQUETAS')).pack(fill='x',padx=18,pady=10)
        @assincrono
        def png():
            try:numero=int(pagina.get());assert numero>0
            except (ValueError,AssertionError):return messagebox.showwarning('Página','Informe uma página válida.',parent=modal)
            caminho=filedialog.asksaveasfilename(parent=modal,defaultextension='.png',initialfile=f'etiquetas-pagina-{numero}.png')
            if not caminho:return
            res=yield Trabalho(self.chamar_api,'GET','/api/secretaria/etiquetas.png?pagina='+str(numero),headers=self.get_auth_headers_get())
            from pathlib import Path
            yield Trabalho(Path(caminho).write_bytes,res.content)
        ttk.Button(modal,text='Baixar esta página PNG',command=png).pack(fill='x',padx=18,pady=10)

    @assincrono
    def documento_desktop(self,tipo,id=None):
        params={'tipo':tipo}
        if id:params['id']=id
        res=yield Trabalho(self.chamar_api,'GET','/api/secretaria/documentos?'+urlencode(params),headers=self.get_auth_headers_get())
        pasta=yield Trabalho(abrir_documento_local,res.json()['html']);self.impressoes_temporarias.append(pasta)

    def etiqueta_desktop(self,item):
        modal=self.janela_ferramenta('Etiqueta do objeto #'+str(item['id']),'390x250')
        ttk.Button(modal,text='Imprimir etiqueta / PDF',command=lambda:self.documento_desktop('ETIQUETAS',item['id'])).pack(fill='x',padx=25,pady=22)
        @assincrono
        def png():
            caminho=filedialog.asksaveasfilename(parent=modal,defaultextension='.png',initialfile=f"etiqueta-{item['id']}.png")
            if not caminho:return
            res=yield Trabalho(self.chamar_api,'GET',f"/api/secretaria/etiquetas/{item['id']}.png",headers=self.get_auth_headers_get())
            from pathlib import Path
            yield Trabalho(Path(caminho).write_bytes,res.content)
        ttk.Button(modal,text='Baixar PNG',command=png).pack(fill='x',padx=25,pady=8)

    @assincrono
    def comparar_mural(self):
        selected=self.tree_mural.selection()
        if not selected:return messagebox.showinfo('Mural','Selecione um relato.')
        relato_id=self.tree_mural.item(selected[0])['values'][0]
        res=yield Trabalho(self.chamar_api,'GET','/api/smart-match',headers=self.get_auth_headers_get())
        resultado=next((r for r in res.json()['resultados'] if str(r['relato']['id'])==str(relato_id)),None)
        if not resultado:return messagebox.showinfo('Mural','Atualize a lista de relatos.')
        modal=self.janela_ferramenta('Possíveis objetos para o relato','740x560')
        tk.Label(modal,text=resultado['relato']['descricao'],bg=BG,fg=FG,wraplength=680,justify='left').pack(fill='x',padx=18,pady=14)
        tk.Label(modal,text='São sugestões. Confira a propriedade presencialmente antes de entregar.',bg=BG,fg='#fbbf24',wraplength=680).pack(pady=8)
        if not resultado['matches']:tk.Label(modal,text='Nenhum objeto semelhante encontrado.',bg=BG,fg=FG).pack()
        for match in resultado['matches']:
            item=match['item'];frame=tk.Frame(modal,bg=CARD);frame.pack(fill='x',padx=18,pady=6)
            tk.Label(frame,text=f"#{item['id']} · {item['nome']} · {match['score']}%\n"+'; '.join(match['motivos']),bg=CARD,fg=FG,justify='left',wraplength=650).pack(anchor='w',padx=10,pady=8)
            def preparar(item=item):
                candidato=next((i for i in self.itens_atuais if i['id']==item['id']),item).copy();candidato['solicitado_por']=resultado['relato']['nome_aluno'];candidato['rm_aluno']=resultado['relato']['rm_aluno'];modal.destroy();self.abrir_dar_baixa(candidato)
            ttk.Button(frame,text='Conferir objeto',command=lambda i=item:self.abrir_modal_detalhes_item(item_direto=i)).pack(side='left',padx=8,pady=6)
            ttk.Button(frame,text='Preparar entrega',command=preparar).pack(side='left',padx=8,pady=6)

    def filtrar_conversas(self):
        if not hasattr(self,'busca_conversas'):return
        busca=normalizar(self.busca_conversas.get());self.listbox_chat.delete(0,tk.END);self.mapa_conversas=[]
        for conta in self.conversas_atuais:
            if busca not in normalizar(str(conta.get('nome_aluno'))+' '+str(conta.get('rm_aluno'))+' '+str(conta.get('email_aluno'))):continue
            self.listbox_chat.insert('end',f"{conta.get('nao_lidas',0)} novas · {conta['nome_aluno']} (RM: {conta['rm_aluno']})");self.mapa_conversas.append(conta)

    def abrir_retirada_codigo(self):
        modal=self.janela_ferramenta('Confirmar retirada com código','650x760')
        id=self.campo_ferramenta(modal,'Número do objeto');codigo=self.campo_ferramenta(modal,'Código de seis dígitos');nome=self.campo_ferramenta(modal,'Nome completo, caso o aluno use aceite digitado')
        tk.Label(modal,text='Conferir presencialmente a identidade e os detalhes do objeto.\nO código não comprova propriedade.',bg=BG,fg='#fbbf24').pack(pady=9)
        conferido=tk.BooleanVar(value=False);tk.Checkbutton(modal,text='Conferi a identidade e o objeto',variable=conferido,bg=BG,fg=FG,selectcolor=CARD).pack()
        imagem=Image.new('RGB',(700,330),'white');draw=ImageDraw.Draw(imagem);assinou={'ok':False,'ponto':None}
        canvas=tk.Canvas(modal,width=560,height=264,bg='white',highlightthickness=1);canvas.pack(pady=10)
        def mover(e):
            ponto=(int(e.x*700/560),int(e.y*330/264))
            if assinou['ponto'] is not None:draw.line([assinou['ponto'],ponto],fill='#172033',width=3);canvas.create_line(assinou['ponto'][0]*560/700,assinou['ponto'][1]*264/330,e.x,e.y,fill='#172033',width=2);assinou['ok']=True
            assinou['ponto']=ponto
        canvas.bind('<Button-1>',lambda e:assinou.update(ponto=(int(e.x*700/560),int(e.y*330/264))))
        canvas.bind('<B1-Motion>',mover);canvas.bind('<ButtonRelease-1>',lambda e:assinou.update(ponto=None))
        def limpar():draw.rectangle((0,0,700,330),fill='white');canvas.delete('all');assinou.update(ok=False,ponto=None)
        def digitar():
            valor=nome.get().strip()
            if len(valor)<5:return messagebox.showwarning('Aceite','Informe o nome completo.',parent=modal)
            limpar();draw.text((18,80),'Aceite por nome digitado:',fill='black');draw.text((18,150),valor[:100],fill='black');preview=ImageTk.PhotoImage(imagem.resize((560,264)),master=modal);canvas.create_image(0,0,image=preview,anchor='nw');canvas.preview=preview;assinou['ok']=True
        botoes=tk.Frame(modal,bg=BG);botoes.pack(fill='x',padx=18)
        ttk.Button(botoes,text='Limpar assinatura',command=limpar).pack(side='left');ttk.Button(botoes,text='Usar nome digitado',command=digitar).pack(side='left',padx=8)
        status=tk.Label(modal,text='',bg=BG,fg=FG,wraplength=590);status.pack(pady=9)
        chave=str(uuid.uuid4());concluido={'recibo':None}
        @assincrono
        def confirmar():
            if concluido['recibo']:return
            try:item_id=id_etiqueta(id.get())
            except ValueError as error:return messagebox.showwarning('Objeto',str(error),parent=modal)
            if not conferido.get() or not assinou['ok'] or not codigo.get().isascii() or not codigo.get().isdigit() or len(codigo.get())!=6:return messagebox.showwarning('Confira os dados','Código de seis dígitos, conferência e aceite são obrigatórios.',parent=modal)
            out=io.BytesIO();imagem.save(out,'PNG');payload={'codigo':codigo.get(),'requisicao':chave,'identidade_conferida':True,'assinatura':'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()}
            res=yield Trabalho(self.chamar_api,'POST',f'/api/retiradas/{item_id}/confirmar',json=payload,headers=self.get_auth_headers());data=res.json();concluido['recibo']=data.get('comprovante_id') or -1
            status.configure(text=data['message']);botao.configure(state='disabled');canvas.unbind('<B1-Motion>');self.carregar_dados()
            if data.get('comprovante_id'):
                @assincrono
                def comprovante():
                    res=yield Trabalho(self.chamar_api,'GET',f"/api/retiradas/comprovantes/{data['comprovante_id']}",headers=self.get_auth_headers_get());registro=res.json()['comprovante']
                    aceite=yield Trabalho(self.chamar_api,'GET',f"/api/retiradas/comprovantes/{data['comprovante_id']}/assinatura",headers=self.get_auth_headers_get())
                    from utils.comprovantes import abrir_impressao_desktop
                    pasta=yield Trabalho(abrir_impressao_desktop,registro,aceite.content);self.impressoes_temporarias.append(pasta)
                ttk.Button(modal,text='Comprovante / Imprimir',command=comprovante).pack(pady=6)
        botao=ttk.Button(modal,text='Confirmar entrega',command=confirmar);botao.pack(fill='x',padx=18,pady=8)

    def abrir_leitor_qr(self):
        from desktop_camera import JanelaCamera
        camera=JanelaCamera(self,lambda codigo:self.abrir_objeto_por_etiqueta(codigo),modo='qr');self.cameras.append(camera)

    def abrir_objeto_por_etiqueta(self,valor):
        try:id=id_etiqueta(valor)
        except ValueError as error:return messagebox.showwarning('Etiqueta',str(error))
        item=next((i for i in self.itens_atuais if i['id']==id),None)
        if item:self.abrir_modal_detalhes_item(item_direto=item)
        else:messagebox.showinfo('Objeto','Objeto não encontrado. Atualize o estoque.')

    @assincrono
    def ampliar_foto_desktop(self,url):
        modal=self.janela_ferramenta('Foto do objeto','950x780');label=tk.Label(modal,text='Carregando foto…',bg=BG,fg=FG);label.pack(fill='both',expand=True)
        try:
            imagem=yield Trabalho(baixar_foto_original,url);imagem.thumbnail((900,700));foto=ImageTk.PhotoImage(imagem,master=modal);label.configure(image=foto,text='');label.image=foto
        except Exception:label.configure(text='Não foi possível abrir a foto. Confira a conexão e tente novamente.')


def baixar_foto_original(url):
    import requests
    from urllib.parse import urlsplit
    if str(url).startswith('data:image/'):
        raw=base64.b64decode(url.split(',',1)[1],validate=True)
    else:
        parsed=urlsplit(str(url))
        if parsed.scheme not in ['http','https'] or parsed.username or parsed.password:raise ValueError('Foto inválida.')
        chunks=[];total=0
        with requests.get(url,stream=True,timeout=(5,20)) as response:
            response.raise_for_status()
            for chunk in response.iter_content(65536):
                total+=len(chunk)
                if total>8*1024*1024:raise ValueError('Foto excede o limite de visualização.')
                chunks.append(chunk)
        raw=b''.join(chunks)
    if len(raw)>8*1024*1024:raise ValueError('Foto excede o limite de visualização.')
    from PIL import ImageOps
    with Image.open(io.BytesIO(raw)) as im:
        if im.width*im.height>16_000_000:raise ValueError('Imagem excede o limite de resolução.')
        return ImageOps.exif_transpose(im).convert('RGB')
