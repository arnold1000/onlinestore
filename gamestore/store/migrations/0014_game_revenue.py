# Generated by Django 3.0.2 on 2020-02-14 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0013_game_last_download'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='revenue',
            field=models.FloatField(default=0.0),
        ),
    ]
