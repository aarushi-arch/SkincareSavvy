from django.urls import path

from . import views

app_name = "face_analysis"

urlpatterns = [
    path("", views.index, name="face_analysis_index"),
    path("upload-model/", views.upload_model, name="upload_model"),
    path("models/", views.ModelListView.as_view(), name="model_list"),
    path("models/<int:pk>/", views.model_detail, name="model_detail"),
    path("models/<int:pk>/delete/", views.delete_model, name="delete_model"),
    path("realtime/", views.realtime, name="realtime"),
    path("realtime/analyze/", views.realtime_analyze, name="realtime_analyze"),
    path("realtime/yolo/", views.realtime_yolo_analyze, name="realtime_yolo_analyze"),
    path("yolo/", views.yolo_index, name="yolo_index"),
    path("yolo/analyze/", views.yolo_analyze, name="yolo_analyze"),
    path("recommendations-for-concern/", views.get_recommendations_for_concern, name="recommendations_for_concern"),
]
