# Generated by Django 5.2.1 on 2025-05-08 19:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('CogEditor', '0003_alter_agreedstatus_options_agreedstatus_n_stage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='role',
        ),
        migrations.AddField(
            model_name='application',
            name='roles',
            field=models.ManyToManyField(to='CogEditor.participatoryrole', verbose_name='Роль участника мероприятия'),
        ),
    ]
