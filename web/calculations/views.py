from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.validators import DecimalValidator, ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from decimal import Decimal
import json
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from web import celery_app

from django.contrib.admin.views.decorators import staff_member_required
from .models import CalculationTask
from .tasks import calculate_high_precision_sqrt, MAX_PRECISION

def home_page(request):
    return render(request, 'home.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm(request)
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    if request.method == 'GET':
        auth_logout(request)
    return redirect('home')

def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Акаунт створено, увійдіть.')
            auth_login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

@login_required
@require_http_methods(["POST"])
def start_calculation(request):
    try:
        data = json.loads(request.body)
        number_str = data.get('number')
        precision = int(data.get('precision', 50000))
        
        active = CalculationTask.objects.filter(
            user=request.user, status__in=['PENDING', 'RUNNING']
        ).count()
        if active >= settings.MAX_ACTIVE_TASKS_PER_USER:
            return JsonResponse({
                'error': f'Перевищено ліміт активних задач ({settings.MAX_ACTIVE_TASKS_PER_USER}). Завершіть або скасуйте поточні.'
            }, status=429)


        if precision > MAX_PRECISION:
            return JsonResponse({
                'error': f"Трудомісткість перевищено. Максимальна точність: {MAX_PRECISION}.",
                'status': 'REJECTED'
            }, status=400)

        try:
            number = Decimal(number_str)
            DecimalValidator(max_digits=30, decimal_places=0)(number)
        except (ValidationError, TypeError, ValueError):
            return JsonResponse({'error': 'Некоректний формат числа.'}, status=400)
        
        if number < 0:
            return JsonResponse({'error': 'Число повинно бути невід\'ємним.'}, status=400)
        
        task_instance = CalculationTask.objects.create(
            user=request.user,
            number_to_calculate=number,
            precision=precision,
            status='PENDING'
        )

        task = calculate_high_precision_sqrt.delay(task_instance.id)
        
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
def my_tasks_page(request):
    tasks = CalculationTask.objects.filter(user=request.user).order_by('-created_at')[:200]
    return render(request, 'my_tasks.html', {'tasks': tasks})

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
    tasks = CalculationTask.objects.filter(user=request.user).order_by('-created_at')[:100]
    
    data = [{
        'id': t.id,
        'status': t.status,
        'status_display': t.get_status_display(), 
        'progress_percent': t.progress_percent,
        'created_at': t.created_at.isoformat(),
        'finished_at': t.finished_at.isoformat() if t.finished_at else None,
        'number_to_calculate': str(t.number_to_calculate),
        'precision': t.precision,
        'result_data': t.result_data
    } for t in tasks]

    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
def cancel_task(request, task_id):
    
    task_instance = get_object_or_404(CalculationTask, pk=task_id, user=request.user)
    celery_id = task_instance.celery_task_id
    
    if not celery_id:
        return JsonResponse({'error': 'Завдання не було запущено в Celery.'}, status=400)

    if task_instance.status in ['SUCCESS', 'FAILURE', 'CANCELED', 'REJECTED']:
        return JsonResponse({
            'error': f'Завдання вже у стані: {task_instance.status}. Скасування неможливе.'
        }, status=400)
    
    try:
        celery_app.control.revoke(
            celery_id, 
            terminate=True, 
            signal='SIGTERM'
        )

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
            'message': 'CANCELED'
        })

    except Exception as e:
        return JsonResponse({'error': f'Помилка скасування: {str(e)}'}, status=500)
    

@staff_member_required
def get_active_celery_tasks(request):
    try:
        inspector = celery_app.control.inspect(timeout=1)
        active = inspector.active() or {}
        # Формат: worker -> list(task_id)
        workers = {}
        for w, tasks in active.items():
            workers[w] = [t.get('id') for t in tasks if t.get('id')]
        return JsonResponse({'workers': workers, 'ts': timezone.now().isoformat()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)