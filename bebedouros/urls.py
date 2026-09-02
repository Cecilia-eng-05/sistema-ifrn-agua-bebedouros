from django.urls import path

from . import views

urlpatterns = [
    path("", views.coleta_list, name="coleta_list"),
    path("coletas/nova/", views.coleta_nova, name="coleta_nova"),
    path("coletas/<int:pk>/lancamento/", views.lancamento, name="lancamento"),
    path("coletas/<int:pk>/publicar/", views.publicar, name="publicar"),
    path("coletas/<int:pk>/apagar/", views.apagar, name="apagar"),
]
