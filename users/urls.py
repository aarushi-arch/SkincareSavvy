from django.urls import path
from django.contrib.auth import views as auth_views

from .views import home, RegisterView, my_shelf, add_to_shelf, remove_from_shelf, profile
from .views import logout_user

urlpatterns = [
    path('', home, name='users-home'),
    path('register/', RegisterView.as_view(), name='users-register'),  
  
    path("logout/", logout_user, name="logout"),
    path('profile/', profile, name='profile'),
    path('my-shelf/', my_shelf, name='my_shelf'),
    path('add-to-shelf/<int:product_id>/', add_to_shelf, name='add_to_shelf'),
    path('remove-from-shelf/<int:product_id>/', remove_from_shelf, name='remove_from_shelf'),
]