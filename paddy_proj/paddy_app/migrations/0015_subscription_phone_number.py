# Generated by Django 5.1.7 on 2025-04-06 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paddy_app', '0014_customertable_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='phone_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
