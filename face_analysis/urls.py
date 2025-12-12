from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="face_analysis_index"),
]

