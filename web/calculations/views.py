from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.validators import DecimalValidator, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
import json

from web import celery_app

from .models import CalculationTask
from .tasks import calculate_high_precision_sqrt, MAX_PRECISION


@login_required
@require_http_methods(["POST"])
def start_calculation(request):
    """Приймає запит, валідує, створює запис у БД та запускає Celery Task."""
    try:
        data = json.loads(request.body)
        number_str = data.get('number')
        precision = int(data.get('precision', 50000))
        
        # --- 1. Валідація Вхідних Даних (Пункт 1) ---
        if precision > MAX_PRECISION:
            return JsonResponse({
                'error': f"Трудомісткість перевищено. Максимальна точність: {MAX_PRECISION}.",
                'status': 'REJECTED'
            }, status=400)

        # Валідація числа (для безпеки)
        try:
            DecimalValidator(max_digits=30, decimal_places=0)(number_str)
            number = Decimal(number_str)
        except (ValidationError, TypeError, ValueError):
            return JsonResponse({'error': 'Некоректний формат числа.'}, status=400)
        
        # Перевірка, що число невід'ємне
        if number < 0:
            return JsonResponse({'error': 'Число повинно бути невід\'ємним.'}, status=400)
        
        # --- 2. Створення запису в БД (Пункт 3) ---
        task_instance = CalculationTask.objects.create(
            user=request.user,
            number_to_calculate=number,
            precision=precision,
            status='PENDING'
        )

        # --- 3. Запуск Celery-завдання (Балансування) ---
        # Передаємо ID об'єкта моделі, щоб Celery Worker міг його оновлювати
        task = calculate_high_precision_sqrt.delay(task_instance.id)
        
        # Зберігаємо Celery ID у моделі для моніторингу/скасування
        task_instance.celery_task_id = task.id
        task_instance.save(update_fields=['celery_task_id'])

        return JsonResponse({
            'task_id': task_instance.id,
            'celery_id': task.id,
            'status': 'PENDING',
            'message': 'Задача прийнята до виконання.'
        }, status=202)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Некоректний JSON-формат.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_task_status(request, task_id):
    """Повертає поточний статус завдання (Пункт 2, 3)."""
    # Перевіряємо, чи належить завдання поточному користувачу
    task = get_object_or_404(CalculationTask, pk=task_id, user=request.user)
    
    return JsonResponse({
        'task_id': task.id,
        'status': task.status,
        'progress_percent': task.progress_percent,
        'result': task.result_data,
        'created_at': task.created_at.isoformat(),
        'finished_at': task.finished_at.isoformat() if task.finished_at else None,
        'number_to_calculate': str(task.number_to_calculate),
        'precision': task.precision
    })


@login_required
def get_task_history(request):
    """Повертає історію завдань користувача (Пункт 3)."""
    tasks = CalculationTask.objects.filter(user=request.user).order_by('-created_at')[:100]
    
    history = [{
        'task_id': t.id,
        'status': t.status,
        'progress_percent': t.progress_percent,
        'created_at': t.created_at.isoformat(),
        'finished_at': t.finished_at.isoformat() if t.finished_at else None,
        'number_to_calculate': str(t.number_to_calculate),
        'precision': t.precision,
        'result_snippet': (t.result_data[:50] + '...') if t.result_data and len(t.result_data) > 50 else t.result_data
    } for t in tasks]

    return JsonResponse({'history': history})


@login_required
@require_http_methods(["POST"])
def cancel_task(request, task_id):
    """Скасовує виконання Celery-завдання."""
    
    # 1. Знаходимо завдання в БД і перевіряємо право власності
    task_instance = get_object_or_404(CalculationTask, pk=task_id, user=request.user)
    celery_id = task_instance.celery_task_id
    
    if not celery_id:
        return JsonResponse({'error': 'Завдання не було запущено в Celery.'}, status=400)

    # 2. Перевірка поточного стану
    if task_instance.status in ['SUCCESS', 'FAILURE', 'CANCELED', 'REJECTED']:
        return JsonResponse({
            'error': f'Завдання вже у стані: {task_instance.status}. Скасування неможливе.'
        }, status=400)
    
    # 3. Надсилання сигналу скасування Celery
    try:
        celery_app.control.revoke(
            celery_id, 
            terminate=True, 
            signal='SIGTERM'
        )

        # 4. Оновлення статусу в локальній БД
        task_instance.status = 'CANCELED'
        task_instance.finished_at = timezone.now()
        task_instance.progress_percent = 0
        task_instance.result_data = "Виконання скасовано користувачем."
        task_instance.save(update_fields=[
            'status', 'finished_at', 'progress_percent', 'result_data'
        ])

        return JsonResponse({
            'task_id': task_id,
            'status': 'CANCELED',
            'message': 'Завдання успішно скасовано.'
        })

    except Exception as e:
        return JsonResponse({'error': f'Помилка скасування: {str(e)}'}, status=500)