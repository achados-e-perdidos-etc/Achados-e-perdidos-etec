"""Pré-verificação local de enquadramento. Não reconhece identidade nem prova autenticidade."""
import io,threading
from functools import lru_cache
from PIL import Image
from utils.imagens import preparar_imagem

_lock=threading.Lock()


@lru_cache(maxsize=1)
def modelos():
    import cv2
    nomes=['haarcascade_frontalface_default.xml','haarcascade_frontalface_alt2.xml','haarcascade_eye_tree_eyeglasses.xml']
    classificadores=[cv2.CascadeClassifier(cv2.data.haarcascades+n) for n in nomes]
    if any(c.empty() for c in classificadores):raise RuntimeError('Modelos de verificação indisponíveis.')
    return cv2,classificadores


def preparar_foto(entrada):
    dados=preparar_imagem(entrada,lado=640,limite=2*1024*1024)
    try:cv2,detectores=modelos()
    except (ImportError,RuntimeError):raise RuntimeError('A verificação da foto está indisponível. Tente novamente mais tarde.') from None
    import numpy as np
    with Image.open(io.BytesIO(dados)) as foto:
        if min(foto.size)<200:raise ValueError('Use uma foto maior e nítida, com pelo menos 200 pixels de cada lado.')
        cinza=cv2.cvtColor(np.asarray(foto.convert('RGB')),cv2.COLOR_RGB2GRAY)
        with _lock:
            rostos=detectores[0].detectMultiScale(cinza,scaleFactor=1.1,minNeighbors=6,minSize=(40,40))
            if len(rostos)!=1:raise ValueError('Use uma foto só sua, de frente, com o rosto inteiro visível. Não conseguimos confirmar um único rosto nesta imagem.')
            x,y,w,h=map(int,rostos[0])
            if w<70 or w<foto.width*.22:raise ValueError('Aproxime o enquadramento: mostre a cabeça e os ombros, com o rosto em destaque.')
            segundo=detectores[1].detectMultiScale(cinza,scaleFactor=1.1,minNeighbors=6,minSize=(40,40))
            if not any(abs(int(a)-x)<w*.35 and abs(int(b)-y)<h*.35 for a,b,_,_ in segundo):
                raise ValueError('O rosto não ficou claro para a verificação. Use outra foto de frente, sem máscara ou objetos cobrindo o rosto.')
            olhos=detectores[2].detectMultiScale(cinza[y:y+int(h*.65),x:x+w],scaleFactor=1.1,minNeighbors=5,minSize=(12,12))
            centros=[(int(a)+int(c)/2,int(b)+int(d)/2) for a,b,c,d in olhos]
            par=any(a[0]<w*.5<b[0] and w*.2<b[0]-a[0]<w*.8 and abs(a[1]-b[1])<h*.18 for a in centros for b in centros)
            if not par:raise ValueError('Deixe os dois olhos visíveis e olhe de frente. Evite óculos escuros, filtros e objetos cobrindo o rosto.')
        lado=min(foto.width,foto.height,int(max(w,h)*1.8));esquerda=max(0,min(foto.width-lado,int(x+w/2-lado/2)));topo=max(0,min(foto.height-lado,int(y+h/2-lado/2)))
        miniatura=foto.crop((esquerda,topo,esquerda+lado,topo+lado)).resize((160,160),Image.Resampling.LANCZOS)
        saida=io.BytesIO();miniatura.convert('RGB').save(saida,'JPEG',quality=80,optimize=True)
        if len(saida.getvalue())>65536:raise ValueError('Não foi possível preparar uma foto pequena. Escolha outra imagem.')
        return saida.getvalue()
