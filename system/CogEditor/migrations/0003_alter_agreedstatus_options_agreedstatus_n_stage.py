# Generated by Django 5.2.1 on 2025-05-08 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CogEditor', '0002_alter_agreedstatus_options_alter_application_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agreedstatus',
            options={'ordering': ['n_stage'], 'verbose_name': 'статус согласования', 'verbose_name_plural': 'Статусы согласования'},
        ),
        migrations.AddField(
            model_name='agreedstatus',
            name='n_stage',
            field=models.IntegerField(default=7, verbose_name='Номер этапа согласования'),
        ),
    ]
