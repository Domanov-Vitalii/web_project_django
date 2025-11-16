from celery import shared_task
from decimal import Decimal, getcontext
from django.utils import timezone
import time

from .models import CalculationTask 

MAX_PRECISION = 3_000_000 

@shared_task(bind=True)
def calculate_high_precision_sqrt(self, task_db_id):

    try:
        task_instance = CalculationTask.objects.get(pk=task_db_id)
        number = task_instance.number_to_calculate
        precision = task_instance.precision

        if precision > MAX_PRECISION:
            task_instance.status = 'REJECTED'
            task_instance.finished_at = timezone.now()
            task_instance.result_data = f"Error: Precision limit exceeded ({precision} > {MAX_PRECISION})."
            task_instance.save(update_fields=['status', 'finished_at', 'result_data'])
            return "REJECTED: PRECISION LIMIT"

        task_instance.status = 'RUNNING'
        task_instance.progress_percent = 0
        task_instance.started_at = timezone.now()
        task_instance.save(update_fields=['status', 'progress_percent', 'started_at'])

        getcontext().prec = precision
        
        task_instance.progress_percent = 10
        task_instance.save(update_fields=['progress_percent'])
        
        start_calc_time = time.time()
        result_decimal = Decimal(number).sqrt() 
        end_calc_time = time.time()
        
        task_instance.status = 'SUCCESS'
        task_instance.progress_percent = 100
        task_instance.result_data = str(result_decimal)
        task_instance.finished_at = timezone.now()
        task_instance.save(update_fields=[
            'status', 'progress_percent', 'result_data', 'finished_at'
        ])

        return f"SUCCESS: Calculated in {round(end_calc_time - start_calc_time, 2)}s"

    except CalculationTask.DoesNotExist:
        return "FAILURE: Task ID not found"
    except Exception as e:
        if 'task_instance' in locals():
            task_instance.status = 'FAILURE'
            task_instance.finished_at = timezone.now()
            task_instance.result_data = f"Task failed with error: {str(e)}"
            task_instance.save(update_fields=['status', 'finished_at', 'result_data'])
        raise