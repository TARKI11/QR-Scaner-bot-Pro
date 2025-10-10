# app/services/qr_decoder.py
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью OpenCV, применяя
    методы предварительной обработки для повышения надежности.
    """
    try:
        # 1. Преобразуем байты в numpy array для OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            logger.error("OpenCV не смог декодировать исходное изображение.")
            return None

        # 2. Улучшение изображения: Преобразование в оттенки серого
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 3. Улучшение изображения: Адаптивная бинаризация для повышения контрастности
        # Это помогает справиться с неравномерным освещением.
        # `adaptiveThreshold` вычисляет порог для небольших областей изображения.
        # Это дает лучшие результаты для изображений с разной яркостью.
        binary_image = cv2.adaptiveThreshold(
            gray_image, 
            255, # Максимальное значение, которое будет присвоено пикселю
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, # Метод вычисления порога
            cv2.THRESH_BINARY, # Тип порога
            11, # Размер блока (окрестности пикселя)
            2 # Константа, вычитаемая из среднего
        )

        # 4. Инициализация детектора и распознавание
        qr_detector = cv2.QRCodeDetector()
        
        # Попытка декодировать улучшенное (бинаризованное) изображение
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(binary_image)

        if bbox is not None and len(data) > 0:
            logger.info(f"Успешно распознано на улучшенном изображении. Длина: {len(data)}")
            return apply_length_limit(data, settings)

        # Если не получилось, пробуем на исходном сером изображении (без бинаризации)
        # Иногда это помогает для очень чистых изображений
        data, bbox, straight_qrcode = qr_detector.detectAndDecode(gray_image)
        
        if bbox is not None and len(data) > 0:
            logger.info(f"Успешно распознано на сером изображении. Длина: {len(data)}")
            return apply_length_limit(data, settings)

        logger.info("OpenCV не нашел QR-код после всех улучшений.")
        return None

    except cv2.error as e:
        logger.error(f"Ошибка OpenCV при обработке изображения: {e}")
        return None
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка при декодировании: {e}", exc_info=True)
        return None

def apply_length_limit(data: str, settings) -> str:
    """Применяет ограничение на длину к распознанным данным."""
    if len(data) > settings.max_qr_content_length:
        logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(data)}")
        return data[:settings.max_qr_content_length] + "..."
    return data
