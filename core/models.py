# core/models.py
from django.db import models
from django.contrib.auth.models import User

class Responsavel(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=200)
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"

class Item(models.Model):
    STATUS_CHOICES = [
        ('localizado', 'Localizado'),
        ('nao_localizado', 'Não Localizado'),
    ]
    
    tombo = models.CharField(max_length=20, unique=True)
    descricao = models.TextField()
    local_oficial = models.CharField(max_length=255)
    caracteristicas = models.TextField(blank=True)
    local_atual = models.CharField(max_length=255, blank=True)
    responsavel = models.ForeignKey(Responsavel, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='nao_localizado')
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tombo} - {self.descricao}"

class Movimentacao(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    local_anterior = models.CharField(max_length=100)
    novo_local = models.CharField(max_length=100)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateTimeField(auto_now_add=True)  # Novo campo