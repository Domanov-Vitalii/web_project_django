from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CalculationTask(models.Model):
    
    STATUS_CHOICES = (
        ('PENDING', 'Очікує виконання'),
        ('RUNNING', 'Виконується'),
        ('SUCCESS', 'Успішно завершено'),
        ('FAILURE', 'Помилка виконання'),
        ('CANCELED', 'Скасовано'),
        ('REJECTED', 'Відхилено (перевищення ліміту)'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calculation_tasks', verbose_name="Користувач")
    celery_task_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="ID Celery Завдання")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата та Час Створення")
    

    number_to_calculate = models.DecimalField(max_digits=30, decimal_places=0, verbose_name="Число") 
    precision = models.IntegerField(verbose_name="Точність (к-ть знаків)", default=50000)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Статус")
    progress_percent = models.IntegerField(default=0, verbose_name="Прогрес (%)")
    
    result_data = models.TextField(null=True, blank=True, verbose_name="Результат")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата Завершення")

    class Meta:
        verbose_name = "Обчислювальне Завдання"
        verbose_name_plural = "Обчислювальні Завдання"
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.pk} by {self.user.username} - {self.status}"
    
    def get_progress(self):
        """Повертає поточний прогрес."""
        return f"{self.progress_percent}% - {self.get_status_display()}"