from django.urls import path

from . import views

app_name = "face_analysis"

urlpatterns = [
    path("", views.index, name="face_analysis_index"),
    path("upload-model/", views.upload_model, name="upload_model"),
    path("models/", views.ModelListView.as_view(), name="model_list"),
    path("models/<int:pk>/", views.model_detail, name="model_detail"),
    path("models/<int:pk>/delete/", views.delete_model, name="delete_model"),
]
