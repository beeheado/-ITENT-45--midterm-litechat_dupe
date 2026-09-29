from django.contrib.auth import views as auth_views
from django.urls import path

from . import account_views, views

urlpatterns = [
    path("", views.chat_home, name="chat_home"),
    path("c/new/", views.new_conversation, name="new_conversation"),
    path("c/<int:pk>/", views.conversation, name="conversation"),
    path("c/<int:pk>/send/", views.send, name="send"),
    path("c/<int:pk>/rename/", views.rename, name="rename"),
    path("c/<int:pk>/delete/", views.delete, name="delete"),
    path("usage/", views.usage, name="usage"),
    path("account/", account_views.account, name="account"),
    path("account/prompt/", account_views.save_prompt, name="save_prompt"),
    path("account/auto-memory/", account_views.set_auto_memory, name="set_auto_memory"),
    path("account/memory/add/", account_views.add_memory, name="add_memory"),
    path("account/memory/<int:pk>/delete/", account_views.delete_memory, name="delete_memory"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
