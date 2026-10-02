from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("f/<slug:slug>/", views.fill, name="fill"),
    path("f/<slug:slug>/done/", views.done, name="done"),
    path("export/<slug:slug>/csv/", views.export_csv, name="export_csv"),
]
