from os import environ

from django import setup

environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

setup()
