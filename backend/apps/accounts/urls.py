from django.urls import path

from apps.accounts.views import LoginView, LogoutView, SessionView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", SessionView.as_view(), name="me"),
]
