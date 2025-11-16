# Використовуємо офіційний образ Python
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо необхідні системні залежності для PostgreSQL та ін.
# Це потрібно для пакетів типу psycopg2
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код застосунку
COPY . .

# Визначаємо змінну середовища для налаштувань Django
ENV DJANGO_SETTINGS_MODULE=web.settings
ENV PYTHONUNBUFFERED=1

# Визначаємо порт Gunicorn/Django
EXPOSE 8000

# Визначаємо команду за замовчуванням.
# Ця команда буде перезаписана в docker-compose для запуску Gunicorn або Celery Worker.
CMD ["/bin/bash"]