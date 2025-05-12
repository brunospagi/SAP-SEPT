from django.contrib import admin
from .models import Responsavel, Item, Movimentacao, ItemNaoEncontrado

admin.site.register(Responsavel)
admin.site.register(Item)
admin.site.register(Movimentacao)
admin.site.register(ItemNaoEncontrado)