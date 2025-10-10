# app/services/qr_decoder.py
import logging
from io import BytesIO
from PIL import Image
from pyzbar import pyzbar
# УБРАНО: from app.config import settings

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None: # Принимаем settings как аргумент
    """
    Декодирует QR-код из байтов изображения с помощью pyzbar.
    Возвращает содержимое QR-кода или None.
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        # pyzbar возвращает список декодированных объектов
        decoded_objects = pyzbar.decode(image)
        if decoded_objects:
            # Берем первое найденное содержимое
            content = decoded_objects[0].data.decode('utf-8')
            if len(content) > settings.max_qr_content_length: # Используем settings
                content = content[:settings.max_qr_content_length] + "..." # Используем settings
            return content
        else:
            logger.info("QR code not found in image.")
            return None
    except Exception as e:
        logger.error(f"Error decoding QR code locally: {e}")
        return None
