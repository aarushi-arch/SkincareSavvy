from django.urls import path
from . import views

from django.contrib.auth import views as auth_views
from users.views import CustomLoginView, CustomLogoutView, profile
from users.forms import LoginForm

urlpatterns = [
    # Add this path
    path('login/', CustomLoginView.as_view(redirect_authenticated_user=True, template_name='users/login.html',
                                           authentication_form=LoginForm), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('profile/', profile, name='profile'),
]