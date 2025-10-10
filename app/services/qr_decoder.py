# app/services/qr_decoder.py
import logging
from PIL import Image
import io
from pyzbar import pyzbar

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью библиотеки pyzbar.
    Этот метод работает локально, не требует внешних API и является легким.
    """
    try:
        # 1. Открываем изображение из байтов
        image = Image.open(io.BytesIO(image_bytes))

        # 2. Декодируем QR-коды на изображении
        decoded_objects = pyzbar.decode(image)

        if not decoded_objects:
            logger.info("pyzbar не нашел QR-кодов на изображении.")
            return None

        # 3. Извлекаем и возвращаем содержимое первого найденного QR-кода
        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                content = obj.data.decode('utf-8')
                logger.info(f"pyzbar успешно распознал QR-код. Длина: {len(content)}")
                return apply_length_limit(content, settings)
        
        logger.info("pyzbar нашел штрих-коды, но среди них нет QR-кода.")
        return None

    except Exception as e:
        logger.error(f"Ошибка при декодировании изображения с помощью pyzbar: {e}", exc_info=True)
        return "Внутренняя ошибка сервера при обработке изображения."

def apply_length_limit(data: str, settings) -> str:
    """Применяет ограничение на длину к распознанным данным."""
    if len(data) > settings.max_qr_content_length:
        logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(data)}")
        return data[:settings.max_qr_content_length] + "..."
    return data
