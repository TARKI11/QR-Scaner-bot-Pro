# app/utils/markdown.py
import re

def escape_markdown_v2(text: str) -> str:
    """
    Экранирует специальные символы MarkdownV2.
    Список из https://core.telegram.org/bots/api#formatting-options
    """
    # Список специальных символов для экранирования
    special_chars = r'\_*[]()~`>#+-=|{}.!'
    # Заменяем каждый специальный символ на \ + символ
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)
