"""
URL configuration for reticulum project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path, re_path, include
from django.urls import reverse_lazy
from django.conf import settings
from django.http import HttpResponse

from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password/', auth_views.PasswordChangeView.as_view(success_url=reverse_lazy('password_change_done')), name='password'),
    path('password/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    # robots.txt
    path('robots.txt', lambda _: HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")),

    # Admin panel
    path('admin/', admin.site.urls),
]
