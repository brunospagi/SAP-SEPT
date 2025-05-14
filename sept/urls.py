from django.contrib import admin
from django.urls import path
from core import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls, name='perfil'),
    path('importar/', views.importar_csv, name='importar_csv'),
    path('scan/', views.scan_codigo, name='scan'),
    path('buscar-locais/', views.buscar_locais, name='buscar_locais'),
    path('relatorio/', views.relatorio_movimentacoes, name='relatorio'),
    path('relatorio-pdf/', views.relatorio_pdf, name='relatorio_pdf'),
    path('relatorio_nao_localizados/', views.relatorio_nao_localizados, name='relatorio_nao_localizados'),
    path('registro-manual/', views.registro_manual, name='registro_manual'),
    path('movimentacao-manual/', views.movimentacao_manual, name='movimentacao_manual'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),   
    path('accounts/logout/', LogoutView.as_view(template_name='registration/logged_out.html',next_page='/accounts/login/'),name='logout'),
]