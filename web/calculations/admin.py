from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from .models import CalculationTask

@admin.register(CalculationTask)
class CalculationTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'number_to_calculate', 'precision', 'created_at', 'finished_at')
    list_filter = ('status', 'user')
    search_fields = ('user__username', 'number_to_calculate')
    readonly_fields = ('created_at', 'finished_at', 'celery_task_id', 'progress_percent')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'celery-monitoring/',
                self.admin_site.admin_view(self.monitoring_view),
                name='celery_monitoring'
            ),
        ]
        return custom_urls + urls

    def monitoring_view(self, request):
        context = {
            **self.admin_site.each_context(request),
            'title': 'Моніторинг Celery'
        }
        return render(request, "admin/celery_monitoring.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        monitoring_url = reverse('admin:celery_monitoring')
        extra_context['monitoring_button'] = format_html(
            '<a href="{}" class="button">Моніторинг Воркерів</a>',
            monitoring_url
        )
        return super().changelist_view(request, extra_context=extra_context)