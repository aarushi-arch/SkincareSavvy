from django.urls import path
from . import views

app_name = "skin_journal"

urlpatterns = [
    path("",              views.journal_list,   name="list"),
    path("new/",          views.journal_create, name="create"),
    path("<int:pk>/",     views.journal_detail, name="detail"),
    path("<int:pk>/edit/",views.journal_edit,   name="edit"),
    path("<int:pk>/delete/", views.journal_delete, name="delete"),
]
