from django.urls import path
from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.home, name="home"),
    path("recommend/", views.recommend, name="recommend"),
    path("filtered-options/", views.get_filtered_options, name="filtered-options"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
]
