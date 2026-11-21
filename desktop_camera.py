"""Câmera/QR sem bloquear o Tk; captura é liberada ao fechar a janela ou sair."""
import io,queue,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from PIL import Image,ImageTk


def ler_qr_arquivo(caminho):
    import cv2,numpy as np
    arquivo=Path(caminho)
    if arquivo.stat().st_size>16*1024*1024:raise ValueError('A imagem excede 16 MB.')
    with Image.open(arquivo) as im:
        if im.width*im.height>16_000_000:raise ValueError('A imagem excede 16 megapixels.')
        frame=cv2.cvtColor(np.array(im.convert('RGB')),cv2.COLOR_RGB2BGR)
    texto,_,_=cv2.QRCodeDetector().detectAndDecode(frame)
    if not texto:raise ValueError('Nenhuma etiqueta QR foi encontrada nesta imagem.')
    return texto


class JanelaCamera:
    def __init__(self,dono,callback,modo='foto'):
        self.dono=dono;self.callback=callback;self.modo=modo;self.fila=queue.Queue(maxsize=2);self.parar=threading.Event();self.frame=None;self.ativa=False
        self.modal=tk.Toplevel(dono.root);self.modal.title('Ler etiqueta QR' if modo=='qr' else 'Fotografar objeto');self.modal.geometry('700x630');self.modal.configure(bg='#0d1117');self.modal.transient(dono.root)
        self.preview=tk.Label(self.modal,bg='#161b22');self.preview.pack(fill='both',expand=True,padx=14,pady=12)
        self.status=tk.Label(self.modal,text='Ative a câmera ou selecione uma imagem.',bg='#0d1117',fg='#cbd5e1',wraplength=650);self.status.pack(pady=8)
        self.indice=tk.StringVar(value='0');ttk.Entry(self.modal,textvariable=self.indice,width=5).pack();self.btn=ttk.Button(self.modal,text='Ativar câmera',command=self.iniciar);self.btn.pack(pady=5)
        if modo=='foto':ttk.Button(self.modal,text='Usar esta foto',command=self.capturar).pack(pady=5)
        else:ttk.Button(self.modal,text='Ler QR de uma imagem',command=self.arquivo).pack(pady=5)
        ttk.Button(self.modal,text='Fechar',command=self.fechar).pack(pady=5);self.modal.protocol('WM_DELETE_WINDOW',self.fechar);self.timer=self.modal.after(80,self.receber)

    def iniciar(self):
        if self.ativa:return
        try:indice=int(self.indice.get());assert 0<=indice<=9
        except (ValueError,AssertionError):self.status.configure(text='Informe uma câmera de 0 a 9.');return
        self.ativa=True;self.btn.configure(state='disabled');threading.Thread(target=self.captura,args=(indice,),daemon=True).start()

    def publicar(self,tipo,valor):
        try:self.fila.put_nowait((tipo,valor))
        except queue.Full:
            if tipo!='foto':
                try:self.fila.get_nowait();self.fila.put_nowait((tipo,valor))
                except (queue.Empty,queue.Full):pass

    def captura(self,indice):
        cap=None
        try:
            import cv2
            cap=cv2.VideoCapture(indice)
            if not cap.isOpened():raise ValueError('Câmera indisponível. Confira a permissão do sistema ou selecione uma imagem.')
            detector=cv2.QRCodeDetector();contador=0
            while not self.parar.is_set():
                ok,frame=cap.read()
                if not ok:raise ValueError('A câmera foi desconectada. Feche e abra o leitor para tentar novamente.')
                contador+=1
                if self.modo=='qr' and contador%5==0:
                    texto,_,_=detector.detectAndDecode(frame)
                    if texto:self.publicar('qr',texto);return
                img=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));img.thumbnail((640,440));self.publicar('foto',img)
                self.parar.wait(.06)
        except Exception as error:self.publicar('erro',str(error))
        finally:
            if cap is not None:cap.release()

    def receber(self):
        if self.parar.is_set():return
        try:
            while True:
                tipo,valor=self.fila.get_nowait()
                if tipo=='foto':
                    self.frame=valor;preview=ImageTk.PhotoImage(valor,master=self.modal);self.preview.configure(image=preview);self.preview.image=preview
                elif tipo=='qr':self.fechar();self.callback(valor);return
                else:self.status.configure(text=valor);self.ativa=False;self.btn.configure(state='normal')
        except queue.Empty:pass
        self.timer=self.modal.after(80,self.receber)

    def capturar(self):
        if self.frame is None:self.status.configure(text='Ative a câmera antes de fotografar.');return
        imagem=self.frame.copy();self.fechar();self.callback(imagem)

    def arquivo(self):
        caminho=filedialog.askopenfilename(parent=self.modal,filetypes=[('Imagens','*.png *.jpg *.jpeg *.webp')])
        if not caminho:return
        def ler():
            try:self.publicar('qr',ler_qr_arquivo(caminho))
            except Exception as error:self.publicar('erro',str(error))
        threading.Thread(target=ler,daemon=True).start()

    def fechar(self):
        self.parar.set()
        try:self.modal.after_cancel(self.timer);self.modal.destroy()
        except tk.TclError:pass
        self.frame=None
        if self in getattr(self.dono,'cameras',[]):self.dono.cameras.remove(self)
