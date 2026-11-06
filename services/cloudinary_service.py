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


def processar_fotos(fotos_array, folder="etec_achados"):
    urls = []
    if not fotos_array:
        return urls
    if not isinstance(fotos_array, list) or len(fotos_array) > 4:
        raise FalhaUploadFotos('Selecione no máximo quatro fotos válidas.')
    for foto in fotos_array:
        if not isinstance(foto, str) or not foto:
            raise FalhaUploadFotos('Uma das fotos é inválida. Selecione novamente.')
        if foto.startswith(('https://', 'http://')):
            urls.append(foto)
            continue
        try:
            resultado = cloudinary.uploader.upload(foto, folder=folder)
            url = resultado.get('secure_url')
            if not isinstance(url, str) or not url.startswith('https://'):
                raise ValueError('Resposta de armazenamento incompleta.')
            urls.append(url)
        except Exception:
            raise FalhaUploadFotos('Não foi possível enviar todas as fotos. Tente novamente.') from None
    return urls
