# Generated by Django 5.1.4 on 2025-04-05 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paddy_app', '0009_alter_customertable_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='admintable',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
