# core/templatetags/auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='is_admin')
def is_admin(user):
    return user.groups.filter(name='Administradores').exists() or user.is_superuser