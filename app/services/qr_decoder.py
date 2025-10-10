# app/services/qr_decoder.py
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью OpenCV.
    Возвращает содержимое QR-кода или None.
    """
    try:
        # Преобразуем байты в numpy array для OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            logger.error("OpenCV не смог декодировать изображение.")
            return None

        # Инициализируем детектор QR-кодов OpenCV
        qr_detector = cv2.QRCodeDetector()
        
        # Пытаемся обнаружить и декодировать QR-код
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(image)

        if bbox is not None and len(data) > 0:
            logger.info(f"OpenCV успешно распознал QR-код. Длина содержимого: {len(data)}")
            
            # Применяем ограничение на длину из настроек
            if len(data) > settings.max_qr_content_length:
                logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(data)}")
                data = data[:settings.max_qr_content_length] + "..."
            
            return data
        else:
            logger.info("OpenCV не нашел QR-код или не смог его декодировать.")
            return None

    except cv2.error as e:
        logger.error(f"Ошибка OpenCV при декодировании QR-кода: {e}")
        return None
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка при декодировании: {e}", exc_info=True)
        return None
