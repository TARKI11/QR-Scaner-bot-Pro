# 1. Берем легкую версию Python
FROM python:3.11-slim

# 2. Настройки, чтобы логи показывались сразу и Python не создавал мусорные файлы
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Устанавливаем библиотеку для чтения QR-кодов (системная часть)
# Без этого шага zbar не будет работать на сервере!
RUN apt-get update && \
    apt-get install -y --no-install-recommends libzbar0 && \
    rm -rf /var/lib/apt/lists/*

# 4. Создаем рабочую папку
WORKDIR /app

# 5. Сначала копируем только список библиотек (для ускорения установки)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Теперь копируем весь остальной код
COPY . .

# 7. Запускаем бота
CMD ["python3", "main.py"]
