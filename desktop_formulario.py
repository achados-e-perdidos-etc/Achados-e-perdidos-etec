"""Cadastro com rascunho de texto, revisão visual e uploads por foto."""
import base64,io,time
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from datetime import datetime
from PIL import Image,ImageOps,ImageTk
from desktop_tasks import Trabalho,assincrono
from desktop_uploads import UploadsDesktop
from utils.catalogo import normalizar

BG='#161b22';FG='#cbd5e1'

def compactar_imagem(imagem):
    imagem=ImageOps.exif_transpose(imagem).convert('RGB');imagem.thumbnail((1200,1200));out=io.BytesIO();imagem.save(out,'JPEG',quality=75,optimize=True)
    if out.tell()>2*1024*1024:raise ValueError('A foto ficou maior que 2 MB. Escolha uma imagem menor.')
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()


def compactar_arquivo(caminho):
    with Image.open(caminho) as im:
        if im.width*im.height>16_000_000:raise ValueError('A foto excede 16 megapixels.')
        return compactar_imagem(im)


class FormularioDesktop:
    def abrir_formulario_paridade(self,item_edit=None):
        modal=tk.Toplevel(self.root);modal.title('Editar objeto' if item_edit else 'Cadastrar objeto');modal.geometry('740x850');modal.configure(bg=BG);modal.transient(self.root)
        canvas=tk.Canvas(modal,bg=BG,highlightthickness=0);scroll=ttk.Scrollbar(modal,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        corpo=tk.Frame(canvas,bg=BG);win=canvas.create_window((0,0),window=corpo,anchor='nw');corpo.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        campos={};valores={'nome':item_edit.get('nome','') if item_edit else '', 'descricao':item_edit.get('txt_descricao','') if item_edit else '', 'data':item_edit.get('txt_data','') if item_edit else datetime.now().strftime('%d/%m/%Y'),'local':item_edit.get('txt_local','') if item_edit else ''}
        rascunho=getattr(self,'rascunho_item',None)
        if not item_edit and rascunho and time.time()-rascunho['em']<86400:valores.update(rascunho['campos'])
        info=tk.Label(corpo,text='O texto do novo cadastro fica nesta sessão por até 24 horas. Fotos não ficam no rascunho.',bg=BG,fg=FG,wraplength=660);info.pack(pady=12)
        for chave,label in [('nome','Título'),('descricao','Descrição'),('categoria','Categoria'),('data','Data encontrada (DD/MM/AAAA)'),('local','Local'),('status','Situação')]:
            frame=tk.Frame(corpo,bg=BG);frame.pack(fill='x',padx=20,pady=5);tk.Label(frame,text=label,bg=BG,fg=FG).pack(anchor='w')
            if chave in ['categoria','status']:
                values=self.categorias_atuais if chave=='categoria' else ['DISPONÍVEL','SOLICITADO','ENTREGUE','PARA DOAÇÃO','DOAÇÃO FEITA']
                campo=ttk.Combobox(frame,values=values,state='readonly');campo.set(valores.get(chave) or (item_edit or {}).get(chave) or ('OUTROS' if chave=='categoria' else 'DISPONÍVEL'))
            else:campo=ttk.Entry(frame);campo.insert(0,valores.get(chave,''))
            campo.pack(fill='x',pady=3);campos[chave]=campo
        def guardar(*args):
            if not item_edit:self.rascunho_item={'em':time.time(),'campos':{k:c.get() for k,c in campos.items()}}
        for campo in campos.values():campo.bind('<KeyRelease>',guardar);campo.bind('<<ComboboxSelected>>',guardar)
        def descartar():
            if not item_edit and messagebox.askyesno('Rascunho','Descartar o texto deste novo cadastro?',parent=modal):
                self.rascunho_item=None
                for k in ['nome','descricao','local']:campos[k].delete(0,'end')
        if not item_edit:ttk.Button(corpo,text='Descartar rascunho',command=descartar).pack(pady=4)
        previews=tk.Frame(corpo,bg=BG);previews.pack(fill='x',padx=20,pady=8)
        container=tk.Frame(corpo,bg=BG);container.pack(fill='x',padx=20,pady=5);upload=UploadsDesktop(self,container);self.uploads_abertos.append(upload)
        for foto in ((item_edit or {}).get('fotos') or ([(item_edit or {})['foto']] if (item_edit or {}).get('foto') else []))[:4]:upload.adicionar(foto)
        status=tk.Label(corpo,text='Até quatro fotos. Você pode remover ou tentar cada foto novamente.',bg=BG,fg=FG,wraplength=670);status.pack(pady=6)
        @assincrono
        def atualizar_previews():
            for filho in previews.winfo_children():filho.destroy()
            for item in list(upload.items):
                try:
                    foto=item['foto']
                    if foto.startswith('data:'):img=Image.open(io.BytesIO(base64.b64decode(foto.split(',',1)[1])));img.thumbnail((100,85))
                    else:img=yield Trabalho(self.baixar_imagem,foto)
                    if img is None or item['cancelado']:continue
                    photo=ImageTk.PhotoImage(img,master=modal);label=tk.Label(previews,image=photo,bg=BG);label.image=photo;label.pack(side='left',padx=3)
                except (ValueError,OSError):pass
        upload.onchange=atualizar_previews;atualizar_previews()
        def adicionar(foto):upload.adicionar(foto)
        @assincrono
        def selecionar():
            arquivos=filedialog.askopenfilenames(parent=modal,title='Adicionar fotos',filetypes=[('Imagens','*.png *.jpg *.jpeg *.webp')])
            for arquivo in arquivos[:4-len(upload.items)]:
                try:foto=yield Trabalho(compactar_arquivo,arquivo);adicionar(foto)
                except Exception as error:status.configure(text=str(error))
        def camera():
            from desktop_camera import JanelaCamera
            if len(upload.items)>=4:return status.configure(text='Remova uma foto antes de fotografar outra.')
            def incluir(imagem):
                try:adicionar(compactar_imagem(imagem))
                except ValueError as error:status.configure(text=str(error))
            janela=JanelaCamera(self,incluir);self.cameras.append(janela)
        ttk.Button(corpo,text='Adicionar fotos',command=selecionar).pack(fill='x',padx=20,pady=4);ttk.Button(corpo,text='Fotografar com câmera',command=camera).pack(fill='x',padx=20,pady=4)
        @assincrono
        def analisar():
            if not upload.items:return status.configure(text='Selecione uma foto antes de analisar.')
            foto=upload.items[0]['foto']
            if not foto.startswith('data:'):return status.configure(text='Selecione uma nova foto para obter sugestões.')
            try:
                res=yield Trabalho(self.chamar_api,'POST','/api/ia/analisar-imagem',json={'foto':foto},headers=self.get_auth_headers());resultado=res.json().get('resultado') or {}
            except Exception as error:
                if getattr(error,'sessao_expirada',False):raise
                status.configure(text='Análise indisponível. Seus campos foram preservados.');return
            revisao=tk.Toplevel(modal);revisao.title('Conferir sugestões da foto');revisao.configure(bg=BG);revisao.geometry('540x390')
            texto='Cores sugeridas: '+', '.join(resultado.get('cores') or [])+'\nOCR: '+str(resultado.get('ocr_confianca') or 'não informado')+'\n'+str(resultado.get('nome') or '')+'\n'+str(resultado.get('descricao') or '')+'\nRevise tudo. OCR não altera matrícula nem identifica o dono.'
            tk.Label(revisao,text=texto,bg=BG,fg=FG,wraplength=490,justify='left').pack(padx=20,pady=20)
            def aplicar():
                valido=resultado.get('pode_preencher') is True and resultado.get('metodo')=='gemini_vision_ocr' and resultado.get('confianca_objeto') in ['alta','media']
                if valido:
                    for k in ['nome','descricao']:
                        if not campos[k].get().strip() and resultado.get(k):campos[k].insert(0,str(resultado[k])[:150 if k=='nome' else 2000])
                    categoria=next((c for c in self.categorias_atuais if normalizar(c)==normalizar(resultado.get('categoria'))),None)
                    if categoria and campos['categoria'].get() in ['','OUTROS']:campos['categoria'].set(categoria)
                guardar();revisao.destroy()
            ttk.Button(revisao,text='Aplicar somente em campos vazios',command=aplicar).pack(pady=12)
        ttk.Button(corpo,text='Analisar foto e revisar sugestões',command=analisar).pack(fill='x',padx=20,pady=5)
        concluido={'ok':False}
        def fechar():
            if not concluido['ok']:guardar()
            upload.fechar();modal.destroy()
        modal.protocol('WM_DELETE_WINDOW',fechar)
        @assincrono
        def salvar():
            payload={k:c.get().strip() for k,c in campos.items()}
            if not payload['nome'] or not payload['descricao'] or not payload['local']:return status.configure(text='Preencha título, descrição e local antes de enviar.')
            try:
                if item_edit:payload.update(id=item_edit['id'],versao=item_edit.get('versao'))
                permitir,duplicado=yield from self.revisar_duplicidade_desktop(payload)
                if not permitir:return
                payload['confirmar_duplicado']=duplicado;payload['fotos']=yield Trabalho(upload.enviar_todas)
                metodo='PUT' if item_edit else 'POST';caminho='/api/itens/'+str(item_edit['id']) if item_edit else '/api/itens'
                yield Trabalho(self.chamar_api,metodo,caminho,json=payload,headers=self.get_auth_headers())
                concluido['ok']=True
                if not item_edit:self.rascunho_item=None
                fechar();self.carregar_dados();messagebox.showinfo('Cadastro salvo','Objeto salvo no servidor.')
            except Exception as error:
                if getattr(error,'sessao_expirada',False):raise
                status.configure(text=getattr(error,'mensagem_publica',None) or str(error))
        ttk.Button(corpo,text='Salvar objeto',command=salvar).pack(fill='x',padx=20,pady=18)
        modal.upload=upload;modal.campos=campos;modal.salvar=salvar;modal.fechar=fechar
        return modal
