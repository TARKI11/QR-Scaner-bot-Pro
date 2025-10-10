# app/services/qr_decoder.py
import logging
import cv2
import numpy as np
from qreader import QReader

# Инициализируем QReader один раз при запуске, чтобы не создавать его на каждое изображение
# Это более эффективно.
# model_size='n' (nano) - самый быстрый и легковесный вариант, идеально для сервера.
q_reader = QReader(model_size='n')

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью библиотеки QReader.
    QReader использует OpenCV "под капотом", но с улучшенной предварительной обработкой,
    что значительно повышает надежность распознавания.
    """
    try:
        # Преобразуем байты в numpy array для OpenCV и QReader
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            logger.error("Не удалось декодировать изображение для QReader.")
            return None

        # Используем QReader для обнаружения и декодирования
        # `decode` возвращает список найденных QR-кодов.
        decoded_qrs = q_reader.decode(image=image)

        if decoded_qrs and decoded_qrs[0] is not None:
            # Берем содержимое первого найденного QR-кода
            content = decoded_qrs[0]
            logger.info(f"QReader успешно распознал QR-код. Длина содержимого: {len(content)}")
            
            # Применяем ограничение на длину из настроек
            if len(content) > settings.max_qr_content_length:
                logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(content)}")
                content = content[:settings.max_qr_content_length] + "..."
            
            return content
        else:
            logger.info("QReader не нашел QR-код или не смог его декодировать.")
            return None

    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка при декодировании с помощью QReader: {e}", exc_info=True)
        return None
