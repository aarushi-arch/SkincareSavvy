from django.urls import path
from . import views

urlpatterns = [

    path("support-chat/", views.chat_support, name="chat_support"),

]