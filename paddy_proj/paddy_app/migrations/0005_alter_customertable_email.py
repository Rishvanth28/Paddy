# Generated by Django 5.2 on 2025-04-03 05:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paddy_app', '0004_alter_customertable_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customertable',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
    ]
