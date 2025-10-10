# app/services/qr_decoder.py
import logging
import tempfile
import os
from pyzxing import BarCodeReader

logger = logging.getLogger(__name__)

def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код из байтов изображения с помощью библиотеки ZXing (через pyzxing).
    Это более надежный метод, чем стандартные декодеры OpenCV или pyzbar.
    Возвращает содержимое QR-кода или None.
    """
    # pyzxing требует путь к файлу, поэтому мы создаем временный файл.
    # delete=False важно для Windows, чтобы ридер мог получить к нему доступ.
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            temp_file.write(image_bytes)
            temp_file_path = temp_file.name
        
        logger.info(f"Декодирование изображения из временного файла: {temp_file_path}")
        
        # Инициализируем ридер ZXing
        reader = BarCodeReader()
        results = reader.decode(temp_file_path)

        if results:
            # Берем первый успешный результат
            decoded_data = results[0].get('raw')
            if decoded_data:
                # pyzxing возвращает байты, поэтому декодируем в строку
                content = decoded_data.decode('utf-8')
                logger.info(f"ZXing успешно распознал QR-код. Длина содержимого: {len(content)}")
                
                # Применяем ограничение на длину из настроек
                if len(content) > settings.max_qr_content_length:
                    logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(content)}")
                    content = content[:settings.max_qr_content_length] + "..."
                
                return content
            else:
                logger.info("ZXing нашел штрих-код, но не смог извлечь необработанные данные.")
                return None
        else:
            logger.info("ZXing не смог найти или распознать штрих-код на изображении.")
            return None

    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка во время декодирования с помощью ZXing: {e}", exc_info=True)
        return None
    finally:
        # Очищаем временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Временный файл удален: {temp_file_path}")
            except OSError as e:
                logger.error(f"Ошибка при удалении временного файла {temp_file_path}: {e}")
