"""Uma sessão por foto, partes confirmadas e tentativas independentes."""
import base64,hashlib,queue,threading
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk


class UploadsDesktop:
    def __init__(self,dono,pai):
        self.dono=dono;self.pai=pai;self.items=[];self.fila=queue.Queue();self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='etec-foto');self.fechado=threading.Event();self.timer=pai.after(80,self.receber)
        self.headers=dict(dono.get_auth_headers_get());self.token=self.headers.get('Authorization')

    def adicionar(self,foto):
        if len(self.items)>=4:raise ValueError('O limite é de quatro fotos.')
        item=dict(foto=foto,id=None,offset=0,url=foto if foto.startswith(('https://','http://')) else None,erro=None,future=None,cancelado=False)
        frame=ttk.Frame(self.pai);frame.pack(fill='x',pady=3);item['frame']=frame
        item['label']=ttk.Label(frame,text='Foto '+str(len(self.items)+1));item['label'].pack(side='left')
        item['barra']=ttk.Progressbar(frame,maximum=100,length=130);item['barra'].pack(side='left',padx=5)
        item['status']=ttk.Label(frame,text='Já enviada' if item['url'] else 'Pronta',width=24);item['status'].pack(side='left')
        item['retry']=ttk.Button(frame,text='Tentar novamente',command=lambda:self.iniciar(item));item['retry'].pack(side='left');item['retry'].state(['disabled'])
        ttk.Button(frame,text='Remover',command=lambda:self.remover(item)).pack(side='right');self.items.append(item)
        if hasattr(self,'onchange'):self.onchange()
        if item['url']:item['barra']['value']=100
        return item

    def remover(self,item):
        item['cancelado']=True;item['frame'].destroy();self.items.remove(item)
        if hasattr(self,'onchange'):self.onchange()

    def requisicao(self,method,path,**kwargs):
        if self.fechado.is_set():raise ValueError('Envio cancelado ao fechar a janela.')
        return self.dono.chamar_api(method,path,headers={**self.headers,**kwargs.pop('headers',{})},**kwargs).json()

    def executar(self,item):
        if item['url']:return item['url']
        try:
            data=base64.b64decode(item['foto'].split(',',1)[1],validate=True)
            if len(data)>2*1024*1024:raise ValueError('Foto maior que 2 MB após compressão.')
            if not item['id']:
                res=self.requisicao('POST','/api/uploads',json={'tamanho':len(data),'sha256':hashlib.sha256(data).hexdigest(),'retomar':True});item['id']=res['id']
            caminho='/api/uploads/'+item['id'];estado=self.requisicao('GET',caminho);item['offset']=estado['recebidos']
            if estado.get('url'):item['url']=estado['url'];return item['url']
            while item['offset']<len(data):
                if item['cancelado']:raise ValueError('Foto removida do envio.')
                try:res=self.requisicao('POST',caminho+'/parte',data=data[item['offset']:item['offset']+65536],headers={'Content-Type':'application/octet-stream','X-Upload-Offset':str(item['offset'])});item['offset']=res['recebidos']
                except Exception as error:
                    response=getattr(error,'response',None)
                    if response is not None and response.status_code==409:
                        novo=response.json().get('recebidos')
                        if type(novo) is int and item['offset']<novo<=len(data):item['offset']=novo
                        else:raise
                    else:raise
                self.fila.put((item,'progresso',int(100*item['offset']/len(data))))
            res=self.requisicao('POST',caminho+'/finalizar',timeout=(5,60));item['url']=res['url'];return item['url']
        except Exception as error:item['erro']=str(error);raise
        finally:self.fila.put((item,'fim',item.get('url')))

    def iniciar(self,item):
        if item.get('future') and not item['future'].done():return item['future']
        item['erro']=None;item['future']=self.pool.submit(self.executar,item);self.fila.put((item,'inicio',None));return item['future']

    def enviar_todas(self):
        items=list(self.items);futures=[(item,self.iniciar(item)) for item in items];erros=[]
        for item,future in futures:
            try:future.result()
            except Exception as error:erros.append(error)
        for error in erros:
            if getattr(error,'sessao_expirada',False):raise error
        if erros:raise ValueError('Uma ou mais fotos não terminaram. Use Tentar novamente na foto com erro; as demais foram preservadas.')
        if any(i['cancelado'] for i in items):raise ValueError('As fotos mudaram. Confira e envie novamente.')
        return [i['url'] for i in items]

    def receber(self):
        if self.fechado.is_set():return
        try:
            while True:
                item,tipo,valor=self.fila.get_nowait()
                if item['cancelado']:continue
                if tipo=='inicio':item['status'].configure(text='Enviando…');item['retry'].state(['disabled'])
                elif tipo=='progresso':item['barra']['value']=valor;item['status'].configure(text=f'{valor}% confirmado')
                else:
                    item['status'].configure(text='Enviada ✓' if valor else 'Interrompida; retome aqui')
                    if valor:item['barra']['value']=100
                    else:item['retry'].state(['!disabled'])
        except queue.Empty:pass
        for item in self.items:
            item['retry'].state(['!disabled'] if item.get('erro') and item.get('future') and item['future'].done() else ['disabled'])
        try:self.timer=self.pai.after(80,self.receber)
        except tk.TclError:self.fechar()

    def fechar(self):
        self.fechado.set()
        try:self.pai.after_cancel(self.timer)
        except tk.TclError:pass
        self.pool.shutdown(wait=False,cancel_futures=True)
        for item in self.items:item['cancelado']=True;item['foto']=''
        self.items.clear()
        if self in getattr(self.dono,'uploads_abertos',[]):self.dono.uploads_abertos.remove(self)
