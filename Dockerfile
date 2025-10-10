# Используем официальный Python образ
FROM python:3.13-slim

# Устанавливаем системные зависимости, включая zbar
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libzbar0 \
        && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём директорию для приложения и копируем исходный код
WORKDIR /app
COPY . .

# Указываем команду запуска
CMD ["python", "main.py"]
