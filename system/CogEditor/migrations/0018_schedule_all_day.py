# Generated by Django 5.2.1 on 2025-05-19 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CogEditor', '0017_alter_sources_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='all_day',
            field=models.BooleanField(default=False, verbose_name='Весь день'),
        ),
    ]
