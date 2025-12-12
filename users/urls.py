from django.urls import path
from django.contrib.auth import views as auth_views

from .views import home, RegisterView  # Import the view here
from .views import logout_user

urlpatterns = [
    path('', home, name='users-home'),
    path('register/', RegisterView.as_view(), name='users-register'),  
  
    path("logout/", logout_user, name="logout"),


]