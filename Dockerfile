# Используем официальный Python образ
FROM python:3.13-slim

# Устанавливаем необходимые системные зависимости для opencv-python-headless
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
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
