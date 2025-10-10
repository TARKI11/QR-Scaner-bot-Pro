# app/services/qr_decoder.py
import logging
import cv2
import numpy as np
# from app.config import settings # <-- УБРАНО

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью OpenCV.
    Возвращает содержимое QR-кода или None.
    settings передается как аргумент.
    """
    try:
        # Преобразуем байты в numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        # Декодируем изображение OpenCV
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            logger.error("Failed to decode image using OpenCV.")
            return None

        # Создаем детектор QR-кодов
        qr_detector = cv2.QRCodeDetector()
        # Декодируем QR-код
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(image)

        if bbox is not None and len(data) > 0:
            if len(data) > settings.max_qr_content_length:
                data = data[:settings.max_qr_content_length] + "..."
            return data
        else:
            logger.info("QR code not found or could not be decoded by OpenCV.")
            return None

    except cv2.error as e:
        logger.error(f"OpenCV error decoding QR code: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding QR code locally: {e}")
        return None
