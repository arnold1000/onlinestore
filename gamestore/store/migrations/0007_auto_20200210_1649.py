# Generated by Django 3.0.2 on 2020-02-10 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_payment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='thumbnail',
            field=models.URLField(default='https://pbs.twimg.com/profile_images/964283409425227776/xqQi0oIM.jpg'),
        ),
    ]
