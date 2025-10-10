# app/services/qr_decoder.py
import logging
import base64
import aiohttp

logger = logging.getLogger(__name__)

# URL для Google Cloud Vision API
VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

async def decode_qr_locally(image_bytes: bytes, settings) -> str | None:
    """
    Декодирует QR-код, отправляя изображение в Google Cloud Vision API.
    Это обеспечивает максимальное качество распознавания, как в Google Lens.
    Использует ключ API, уже настроенный в проекте (gsb_api_key).
    """
    api_key = settings.gsb_api_key
    if not api_key:
        logger.error("Ключ для Google Vision API (GSB_API_KEY) не найден в настройках.")
        return "Ошибка: Ключ Google API не настроен на сервере."

    try:
        # 1. Кодируем изображение в Base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # 2. Формируем тело запроса к API
        request_body = {
            'requests': [
                {
                    'image': {
                        'content': base64_image
                    },
                    'features': [
                        {
                            'type': 'BARCODE_DETECTION', # Просим API искать штрихкоды (включая QR)
                            'maxResults': 5 # Искать до 5 кодов на одном изображении
                        }
                    ]
                }
            ]
        }

        # 3. Асинхронно отправляем запрос с помощью aiohttp
        async with aiohttp.ClientSession() as session:
            params = {'key': api_key}
            async with session.post(VISION_API_URL, params=params, json=request_body) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ошибка от Google Vision API ({response.status}): {error_text}")
                    return f"Ошибка сервера при распознавании ({response.status})."
                
                data = await response.json()

        # 4. Парсим ответ от API
        responses = data.get('responses', [])
        if not responses:
            logger.info("Google Vision API вернул пустой ответ.")
            return None

        barcode_annotations = responses[0].get('barcodeAnnotations', [])
        if not barcode_annotations:
            logger.info("QR-код не найден на изображении (по данным Google Vision).")
            return None

        # Ищем именно QR-код среди всех найденных штрихкодов
        for barcode in barcode_annotations:
            if barcode.get('format') == 'QR_CODE':
                content = barcode.get('rawValue')
                if content:
                    logger.info(f"Google Vision успешно распознал QR-код. Длина: {len(content)}")
                    return apply_length_limit(content, settings)
        
        logger.info("Найдены штрихкоды, но среди них нет QR-кода.")
        return None # Найдены другие типы штрихкодов, но не QR

    except aiohttp.ClientError as e:
        logger.error(f"Сетевая ошибка при обращении к Google Vision API: {e}", exc_info=True)
        return "Ошибка: Не удалось связаться с сервисом распознавания."
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка при декодировании через Google Vision: {e}", exc_info=True)
        return "Внутренняя ошибка сервера при обработке изображения."

def apply_length_limit(data: str, settings) -> str:
    """Применяет ограничение на длину к распознанным данным."""
    if len(data) > settings.max_qr_content_length:
        logger.warning(f"Содержимое QR-кода было обрезано. Исходная длина: {len(data)}")
        return data[:settings.max_qr_content_length] + "..."
    return data
