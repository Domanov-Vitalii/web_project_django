# Веб-застосунок для трудомістких обчислень

Django + Celery + Redis + PostgreSQL + Nginx Load Balancer

## 🏗️ Архітектура

```
┌─────────────┐
│   Клієнт    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Nginx    │ ◄── Load Balancer
│ (Port 80)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Django    │ ◄── Веб-сервер + API + Авторизація
│ (Port 8000) │
└──────┬──────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌──────────────┐  ┌─────────────┐
│ PostgreSQL   │  │    Redis    │
│ (Port 5432)  │  │ (Port 6379) │
└──────────────┘  └──────┬──────┘
                         │
                         ├──────────┬──────────┐
                         ▼          ▼          ▼
                  ┌──────────┐ ┌──────────┐
                  │ Worker 1 │ │ Worker 2 │ ◄── Celery Workers
                  └──────────┘ └──────────┘
```

## 🚀 Швидкий старт

### 1. Клонування та підготовка

```bash
git clone <your-repo>
cd web_project_django
```

### 2. Створення директорії для Nginx

```bash
mkdir -p nginx
# Скопіюйте nginx.conf в цю директорію
```

### 3. Запуск через Docker Compose

```bash
# Збірка та запуск всіх сервісів
docker-compose up --build

# Або у фоновому режимі
docker-compose up -d --build
```

### 4. Створення суперкористувача Django

```bash
docker exec -it web_django python manage.py createsuperuser
```

### 5. Відкрийте браузер

- **Головна сторінка**: http://localhost
- **Django Admin**: http://localhost/admin
- **API**: http://localhost/api/v1/

## 📋 Доступні API Endpoints

### Авторизація
- `POST /accounts/login/` - Вхід
- `POST /accounts/logout/` - Вихід

### Обчислення
- `POST /api/v1/tasks/start/` - Запуск нової задачі
  ```json
  {
    "number": "123456789",
    "precision": 50000
  }
  ```

- `GET /api/v1/tasks/<task_id>/status/` - Статус задачі
- `GET /api/v1/tasks/history/` - Історія задач
- `POST /api/v1/tasks/<task_id>/cancel/` - Скасування задачі

## 🛠️ Управління сервісами

### Перегляд логів

```bash
# Всі сервіси
docker-compose logs -f

# Тільки Django
docker-compose logs -f web

# Celery Worker 1
docker-compose logs -f celery_worker_1

# Celery Worker 2
docker-compose logs -f celery_worker_2
```

### Зупинка

```bash
docker-compose down

# З видаленням volumes (БД та кеш)
docker-compose down -v
```

### Перезапуск окремого сервісу

```bash
docker-compose restart web
docker-compose restart celery_worker_1
```

## 🔧 Розробка

### Локальний запуск без Docker

1. Встановіть PostgreSQL та Redis локально
2. Створіть віртуальне оточення:
   ```bash
   cd web
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # або
   venv\Scripts\activate  # Windows
   ```

3. Встановіть залежності:
   ```bash
   pip install -r requirements.txt
   ```

4. Налаштуйте змінні оточення:
   ```bash
   export DATABASE_HOST=localhost
   export REDIS_HOST=127.0.0.1
   export SECRET_KEY=your-secret-key
   export DEBUG=True
   ```

5. Виконайте міграції:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. Запустіть сервери:
   ```bash
   # Термінал 1 - Django
   python manage.py runserver

   # Термінал 2 - Celery Worker
   celery -A web worker --loglevel=info
   ```

## 📊 Моніторинг Celery

### Flower (опціонально)

Додайте в `docker-compose.yml`:

```yaml
flower:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: celery_flower
  command: celery -A web flower --port=5555
  ports:
    - "5555:5555"
  environment:
    - DJANGO_SETTINGS_MODULE=web.settings
  depends_on:
    - redis
```

Потім відкрийте: http://localhost:5555

## ⚙️ Налаштування балансування

### Збільшення кількості Celery Workers

У `docker-compose.yml` додайте більше воркерів:

```yaml
celery_worker_3:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: celery_worker_3
  command: celery -A web worker --loglevel=info --concurrency=2 --hostname=worker3@%h
  # ... решта конфігурації як у worker_1
```

### Балансування Django інстансів

У `docker-compose.yml`:

```yaml
web2:
  # Копія сервісу web
  ports:
    - "8001:8000"  # Інший порт

web3:
  # Копія сервісу web
  ports:
    - "8002:8000"  # Інший порт
```

Потім у `nginx.conf`:

```nginx
upstream django_backend {
    least_conn;
    server web:8000;
    server web2:8000;
    server web3:8000;
}
```

## 🧪 Тестування

### Приклад тестового запиту (curl)

```bash
# Логін
curl -X POST http://localhost/accounts/login/ \
  -d "username=admin&password=admin123" \
  -c cookies.txt

# Запуск задачі
curl -X POST http://localhost/api/v1/tasks/start/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"number": "12345", "precision": 1000}'

# Статус задачі
curl http://localhost/api/v1/tasks/1/status/ -b cookies.txt
```

## 📝 Особливості реалізації

### ✅ Виконані вимоги:

1. **Обмеження трудомісткості** - `MAX_PRECISION = 10_000_000`
2. **Відображення прогресу** - Оновлення `progress_percent` в БД
3. **Історія та управління** - CRUD операції для задач
4. **Авторизація** - Django authentication через `@login_required`
5. **Балансування навантаження** - 2 Celery Workers + Nginx

### 🔐 Безпека

- CSRF токени для POST запитів
- Авторизація для всіх API endpoints
- Валідація вхідних даних
- Обмеження `ALLOWED_HOSTS` у продакшені

## 🐛 Troubleshooting

### База даних не підключається

```bash
# Перевірте статус PostgreSQL
docker-compose ps db

# Перевірте логи
docker-compose logs db
```

### Celery не обробляє задачі

```bash
# Перевірте, чи працює Redis
docker exec -it web_redis redis-cli ping
# Має повернути: PONG

# Перевірте статус воркерів
docker-compose ps | grep celery
```

### Порт зайнятий

```bash
# Знайдіть процес на порту 80
sudo lsof -i :80

# Або змініть порт в docker-compose.yml
ports:
  - "8080:80"  # Використовуйте 8080 замість 80
```

## 📚 Додаткова інформація

- Django Documentation: https://docs.djangoproject.com/
- Celery Documentation: https://docs.celeryq.dev/
- Nginx Documentation: https://nginx.org/en/docs/

## 📄 Ліцензія

MIT License - див. файл LICENSE