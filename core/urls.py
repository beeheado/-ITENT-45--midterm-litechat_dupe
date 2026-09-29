from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.chat_home, name="chat_home"),
    path("c/new/", views.new_conversation, name="new_conversation"),
    path("c/<int:pk>/", views.conversation, name="conversation"),
    path("c/<int:pk>/send/", views.send, name="send"),
    path("c/<int:pk>/rename/", views.rename, name="rename"),
    path("c/<int:pk>/delete/", views.delete, name="delete"),
    path("usage/", views.usage, name="usage"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
