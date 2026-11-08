"""
Serviço de Armazenamento e Processamento de Imagens em Nuvem
Integração com Cloudinary.
"""
import cloudinary
import cloudinary.uploader
from config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )

class FalhaUploadFotos(RuntimeError):
    """Nenhum item deve ser salvo como sucesso quando uma foto falha."""
    status_code = 502

class FotoInvalida(FalhaUploadFotos):
    status_code = 400


def processar_fotos(fotos_array, folder="etec_achados", *, existentes=()):
    import io, uuid
    from urllib.parse import urlsplit
    from utils.imagens import preparar_imagem
    urls, preparados = [], []
    if fotos_array is None or fotos_array == []: return urls
    if not isinstance(fotos_array, list) or len(fotos_array) > 4:
        raise FotoInvalida('Selecione no máximo quatro fotos válidas.')
    try:
        for foto in fotos_array:
            if not isinstance(foto,str): raise ValueError('Foto inválida.')
            if foto.startswith(('http://','https://')):
                parsed=urlsplit(foto)
                permitido=(parsed.scheme=='https' and parsed.hostname=='res.cloudinary.com'
                    and not parsed.username and not parsed.password and not parsed.query
                    and bool(CLOUDINARY_CLOUD_NAME) and parsed.path.startswith('/'+CLOUDINARY_CLOUD_NAME+'/image/upload/')
                    and '/etec_achados/' in parsed.path)
                if foto not in existentes and not permitido:
                    raise ValueError('Selecione a foto neste site; links externos não são aceitos.')
                preparados.append(foto)
            else: preparados.append(preparar_imagem(foto))
    except ValueError as error: raise FotoInvalida(str(error)) from None
    for foto in preparados:
        if isinstance(foto,str): urls.append(foto); continue
        try:
            resultado=cloudinary.uploader.upload(io.BytesIO(foto),
                public_id=folder+'/'+str(uuid.uuid4()),resource_type='image',overwrite=False,timeout=30)
            url=resultado.get('secure_url')
            if not isinstance(url,str) or not url.startswith('https://'):raise ValueError()
            urls.append(url)
        except Exception:
            raise FalhaUploadFotos('Não foi possível enviar todas as fotos. Tente novamente.') from None
    return urls
