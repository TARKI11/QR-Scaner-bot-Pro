import logging
from PIL import Image
import io
from pyzbar import pyzbar

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью библиотеки pyzbar.
    """
    try:
        # 1. Открываем изображение из байтов
        image = Image.open(io.BytesIO(image_bytes))

        # 2. УСКОРЕНИЕ: Переводим в черно-белый формат (так быстрее читается)
        image = image.convert('L')

        # 3. Декодируем
        decoded_objects = pyzbar.decode(image)

        if not decoded_objects:
            # QR-код не найден
            return None

        # 4. Ищем именно QR-код
        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                content = obj.data.decode('utf-8')
                return apply_length_limit(content, settings)
        
        return None

    except Exception as e:
        logger.error(f"Ошибка при чтении QR: {e}")
        # Возвращаем None, чтобы бот просто сказал "Не нашел код", а не пугал ошибками
        return None

def apply_length_limit(data: str, settings) -> str:
    """Обрезает слишком длинный текст."""
    if len(data) > settings.max_qr_content_length:
        return data[:settings.max_qr_content_length] + "..."
    return data
