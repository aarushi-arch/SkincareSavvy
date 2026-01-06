from django.urls import path
from .views import ShopHealthCheck

urlpatterns = [
    path("", ShopHealthCheck.as_view()),
]
