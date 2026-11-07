"""I/O em workers; geradores são retomados exclusivamente pela thread do Tk."""
import functools
import inspect
import queue
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
import requests


class Trabalho:
    def __init__(self, funcao, *args, **kwargs):
        self.funcao,self.args,self.kwargs=funcao,args,kwargs
    def executar(self): return self.funcao(*self.args, **self.kwargs)


def assincrono(funcao):
    @functools.wraps(funcao)
    def iniciar(*args, **kwargs):
        dono = args[0] if args and hasattr(args[0],'tarefas') else inspect.getclosurevars(funcao).nonlocals['self']
        modal = inspect.getclosurevars(funcao).nonlocals.get('modal')
        return dono.tarefas.executar(funcao,args,kwargs,modal)
    return iniciar


class TarefasDesktop:
    def __init__(self, dono):
        self.dono=dono; self.root=dono.root;self.geracao=0;self.fechado=False
        self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='secretaria-io')
        self.fila=queue.Queue();self.ativos={};self.falhas={};self.ultima_leitura=None
        self.timer=self.root.after(25,self._receber)

    def _contexto(self, funcao):
        return (self.geracao, getattr(self.dono,'email_chat_ativo',None),getattr(self.dono,'rm_chat_ativo',None)) if funcao.__name__=='carregar_mensagens_aluno' else (self.geracao,)

    def executar(self,funcao,args,kwargs,modal=None):
        if self.fechado:return
        chave=funcao.__qualname__;leitura=funcao.__name__.startswith('carregar_')
        if chave in self.ativos:
            if leitura and (self.ativos[chave]['contexto']!=self._contexto(funcao) or any(not j['leitura'] for j in self.ativos.values())):
                self.ativos[chave]['repetir']=(funcao,args,kwargs,modal)
            return
        job=dict(chave=chave,funcao=funcao,gerador=funcao(*args,**kwargs),contexto=self._contexto(funcao),
                 leitura=leitura,args=args,kwargs=kwargs,repetir=None,widgets=[],modal=modal,protocolo=None)
        self.ativos[chave]=job
        if not leitura and modal is not None and modal.winfo_exists():
            job['protocolo']=modal.protocol('WM_DELETE_WINDOW')
            modal.protocol('WM_DELETE_WINDOW',lambda:None)
            def bloquear(pai):
                for widget in pai.winfo_children():
                    if widget.winfo_class() in {'Entry','TEntry','TCombobox','Button','Text'}:
                        estado=widget.cget('state');job['widgets'].append((widget,estado));widget.configure(state='disabled')
                    bloquear(widget)
            bloquear(modal)
        self.dono.status_operacao('Sincronizando…')
        self._passo(job)

    def _passo(self,job,resultado=None,inicial=True):
        try:
            trabalho=next(job['gerador']) if inicial else job['gerador'].send(resultado)
            if not isinstance(trabalho,Trabalho):raise TypeError('Operação de fundo inválida.')
            job['janela']=getattr(job['gerador'],'gi_frame',None).f_locals.get('modal') if getattr(job['gerador'],'gi_frame',None) else None
            future=self.pool.submit(trabalho.executar)
            future.add_done_callback(lambda pronto:self.fila.put((job,pronto)))
        except StopIteration:
            self._terminar(job)
        except Exception as error:
            self._erro(job,error)

    def _erro(self,job,error):
        if getattr(error,'sessao_expirada',False):
            self.dono.encerrar_sessao(expirada=True);return
        if job['leitura']:
            self.ultima_leitura=(job['funcao'],job['args'],job['kwargs'],job['modal'])
            self.falhas[job['chave']]=self.ultima_leitura
            self.dono.status_operacao('Não foi possível atualizar. Use “Tentar novamente”.',erro=True)
        else:
            self.dono.erro_operacao(getattr(error,'mensagem_publica',None) or 'Não foi possível confirmar a operação. Seus campos foram preservados. Atualize os dados antes de tentar novamente.')
        self._terminar(job,sucesso=False)

    def _terminar(self,job,sucesso=True):
        try:job['gerador'].close()
        except (RuntimeError,tk.TclError):pass
        self.ativos.pop(job['chave'],None)
        if sucesso:self.falhas.pop(job['chave'],None)
        for widget,estado in job['widgets']:
            try:
                if widget.winfo_exists():widget.configure(state=estado)
            except tk.TclError:pass
        modal=job['modal']
        if modal is not None:
            try:
                if modal.winfo_exists():modal.protocol('WM_DELETE_WINDOW',job['protocolo'] or modal.destroy)
            except tk.TclError:pass
        if job['funcao'].__name__=='verificar_login':
            try:
                if self.dono.btn_entrar.winfo_exists():self.dono.btn_entrar.config(text='ENTRAR NO SISTEMA',state='normal')
            except tk.TclError:pass
        if job['repetir'] and not self.fechado and job['contexto'][0]==self.geracao:
            self.executar(*job['repetir'])
        elif sucesso and not self.ativos:self.dono.status_operacao('Não foi possível atualizar parte dos dados. Use “Tentar novamente”.' if self.falhas else 'Dados atualizados.',erro=bool(self.falhas))

    def _receber(self):
        if self.fechado:return
        try:
            while True:
                job,future=self.fila.get_nowait()
                if job['contexto'][0]!=self.geracao:continue
                janela=job.get('janela')
                if janela is not None and not janela.winfo_exists():self._terminar(job);continue
                if job['contexto']!=self._contexto(job['funcao']) or job['repetir']:
                    self._terminar(job);continue
                try:resultado=future.result()
                except Exception as error:self._erro(job,error)
                else:self._passo(job,resultado,inicial=False)
        except queue.Empty:pass
        self.timer=self.root.after(25,self._receber)

    def repetir(self):
        if self.falhas:self.executar(*next(iter(self.falhas.values())))

    def invalidar(self):
        self.geracao+=1;self.ultima_leitura=None;self.falhas.clear()
        for job in list(self.ativos.values()):
            job['repetir']=None;self._terminar(job,sucesso=False)

    def fechar(self):
        self.fechado=True;self.invalidar()
        self.root.after_cancel(self.timer)
        self.pool.shutdown(wait=False,cancel_futures=True)
