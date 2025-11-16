from django.urls import path
from . import views

urlpatterns = [
    path('tasks/start/', views.start_calculation, name='start_calculation'),
    path('tasks/history/', views.get_task_history, name='get_task_history'),
    path('tasks/<int:task_id>/status/', views.get_task_status, name='get_task_status'),
    path('tasks/<int:task_id>/cancel/', views.cancel_task, name='cancel_task'),
]