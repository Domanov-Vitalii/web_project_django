"""
URL configuration for web project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Підключення стандартних URL-адрес для автентифікації (логін/логаут)
    path('accounts/', include('django.contrib.auth.urls')), # Пункт 4
    # Підключення URL-адрес для обчислень
    path('api/v1/', include('calculations.urls')),
    
    # Можливо, вам потрібен домашній URL для frontend-сторінки:
    # path('', views.home, name='home'),
]