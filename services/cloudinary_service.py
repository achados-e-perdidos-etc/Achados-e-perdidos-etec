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

def processar_fotos(fotos_array, folder="etec_achados"):
    """
    Processa uma lista de imagens (Base64 comprimido ou URLs já existentes)
    e retorna uma lista de URLs permanentes no Cloudinary.
    """
    urls_finais = []
    if not fotos_array:
        return urls_finais
        
    for foto in fotos_array:
        if not foto:
            continue
        if str(foto).startswith('http'):
            urls_finais.append(str(foto))
        else:
            try:
                res_upload = cloudinary.uploader.upload(foto, folder=folder)
                if "secure_url" in res_upload:
                    urls_finais.append(res_upload["secure_url"])
            except Exception as e:
                print(f"[Cloudinary] Erro no upload da foto: {e}")
    return urls_finais
