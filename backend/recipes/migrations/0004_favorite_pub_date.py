# Generated by Django 3.2 on 2023-09-01 15:54

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_remove_shoppingcart_pub_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='favorite',
            name='pub_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата добавления'),
            preserve_default=False,
        ),
    ]