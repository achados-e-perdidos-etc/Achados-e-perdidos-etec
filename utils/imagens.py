"""Decodifica pixels reais e recria a foto, sem metadados ou nome do arquivo."""
import base64
import io
import warnings
from PIL import Image, ImageOps

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000


def preparar_imagem(entrada, *, lado=1600, limite=MAX_BYTES):
    if isinstance(entrada, str):
        if not entrada.startswith(('data:image/jpeg;base64,', 'data:image/png;base64,', 'data:image/webp;base64,')):
            raise ValueError('Selecione uma foto JPEG, PNG ou WEBP válida.')
        encoded = entrada.split(',', 1)[1]
        if len(encoded) > (limite * 4 // 3 + 8):
            raise ValueError('A imagem excede o limite permitido.')
        try:
            data = base64.b64decode(encoded, validate=True)
        except Exception:
            raise ValueError('A imagem não pôde ser lida.') from None
    elif isinstance(entrada, bytes):
        data = entrada
    else:
        raise ValueError('Imagem inválida.')
    if not data or len(data) > limite:
        raise ValueError('A imagem excede o limite permitido.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > MAX_PIXELS:
                    raise ValueError()
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValueError()
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((lado, lado))
                output = io.BytesIO()
                if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
                    base = Image.new('RGB', image.size, 'white')
                    rgba = image.convert('RGBA'); base.paste(rgba, mask=rgba.getchannel('A'))
                    image = base
                image.convert('RGB').save(output, format='JPEG', quality=82, optimize=True)
                return output.getvalue()
    except Exception:
        raise ValueError('Use uma foto estática JPEG, PNG ou WEBP com até 16 megapixels.') from None
