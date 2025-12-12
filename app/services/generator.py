import qrcode
from io import BytesIO

def generate_qr_code(text: str) -> BytesIO:
    """
    Создает QR-код из текста и возвращает его как байтовый объект (в памяти).
    """
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=None,  # Автоматический размер
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)

    # Создаем картинку (черный код, белый фон)
    img = qr.make_image(fill_color="black", back_color="white")

    # Сохраняем в память (не на диск!)
    bio = BytesIO()
    img.save(bio)
    bio.seek(0)
    
    return bio
