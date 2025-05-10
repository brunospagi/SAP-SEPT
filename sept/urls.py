from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('importar/', views.importar_csv, name='importar_csv'),
    path('scan/', views.scan_codigo, name='scan'),
    path('buscar-locais/', views.buscar_locais, name='buscar_locais'),
    path('relatorio/', views.relatorio_movimentacoes, name='relatorio'),
    path('relatorio-pdf/', views.relatorio_pdf, name='relatorio_pdf'),
]