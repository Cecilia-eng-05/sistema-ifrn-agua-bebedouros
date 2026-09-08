from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path(
        "entrar/",
        auth_views.LoginView.as_view(template_name="bebedouros/login.html"),
        name="login",
    ),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("inicio/", views.inicio, name="inicio"),
    path("bebedouros/<int:pk>/", views.bebedouro_detalhe, name="bebedouro_detalhe"),
    path("", views.mapa, name="mapa"),
    path("coletas/", views.coleta_list, name="coleta_list"),
    path("coletas/nova/", views.coleta_nova, name="coleta_nova"),
    path("coletas/<int:pk>/lancamento/", views.lancamento, name="lancamento"),
    path("coletas/<int:pk>/publicar/", views.publicar, name="publicar"),
    path("coletas/<int:pk>/apagar/", views.apagar, name="apagar"),
]
