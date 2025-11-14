from celery import shared_task
from decimal import Decimal, getcontext
from django.utils import timezone
import time

# Імпортуємо модель, яку будемо оновлювати
from .models import CalculationTask 

MAX_PRECISION = 10_000_000 # Ліміт максимальної трудомісткості (Пункт 1)

@shared_task(bind=True)
def calculate_high_precision_sqrt(self, task_db_id):
    """
    Трудомістке завдання: обчислення кореня з високою точністю.
    Оновлює стан і результат безпосередньо в моделі CalculationTask.
    """
    
    try:
        # Отримуємо об'єкт моделі для оновлення
        task_instance = CalculationTask.objects.get(pk=task_db_id)
        number = task_instance.number_to_calculate
        precision = task_instance.precision

        # --- 1. Перевірка Трудомісткості (Пункт 1) ---
        if precision > MAX_PRECISION:
            task_instance.status = 'REJECTED'
            task_instance.finished_at = timezone.now()
            task_instance.result_data = f"Error: Precision limit exceeded ({precision} > {MAX_PRECISION})."
            task_instance.save(update_fields=['status', 'finished_at', 'result_data'])
            return "REJECTED: PRECISION LIMIT"

        # Оновлюємо статус на 'RUNNING' у моделі
        task_instance.status = 'RUNNING'
        task_instance.progress_percent = 0
        task_instance.save(update_fields=['status', 'progress_percent'])

        # Встановлення контексту
        getcontext().prec = precision
        
        # --- 2. Імітація Прогресу (Пункт 2) ---
        
        # Оновлення прогресу (на початку)
        task_instance.progress_percent = 10
        task_instance.save(update_fields=['progress_percent'])
        
        # Це єдиний обчислювальний блок, тому прогрес оновимо лише один раз після нього.
        # У реальному FEM або розпізнаванні, прогрес оновлювався б у циклі ітерацій.
        
        # Виконуємо трудомістке обчислення
        start_calc_time = time.time()
        result_decimal = Decimal(number).sqrt() 
        end_calc_time = time.time()
        
        # --- 3. Збереження Результату та Статусу ---
        
        task_instance.status = 'SUCCESS'
        task_instance.progress_percent = 100
        task_instance.result_data = str(result_decimal)
        task_instance.finished_at = timezone.now()
        task_instance.save(update_fields=[
            'status', 'progress_percent', 'result_data', 'finished_at'
        ])

        return f"SUCCESS: Calculated in {round(end_calc_time - start_calc_time, 2)}s"

    except CalculationTask.DoesNotExist:
        # Якщо завдання було видалено (можливо, користувачем)
        return "FAILURE: Task ID not found"
    except Exception as e:
        # Обробка інших помилок
        if 'task_instance' in locals():
            task_instance.status = 'FAILURE'
            task_instance.finished_at = timezone.now()
            task_instance.result_data = f"Task failed with error: {str(e)}"
            task_instance.save(update_fields=['status', 'finished_at', 'result_data'])
        
        # Це також позначить завдання Celery як FAILED
        raise