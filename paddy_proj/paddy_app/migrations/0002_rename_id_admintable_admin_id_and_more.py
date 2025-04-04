# Generated by Django 5.1.4 on 2025-04-02 17:28

import paddy_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paddy_app', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='admintable',
            old_name='id',
            new_name='admin_id',
        ),
        migrations.RenameField(
            model_name='customertable',
            old_name='id',
            new_name='customer_id',
        ),
        migrations.AlterField(
            model_name='admintable',
            name='phone_number',
            field=models.CharField(max_length=15),
        ),
        migrations.AlterField(
            model_name='customertable',
            name='GST',
            field=models.CharField(blank=True, max_length=15, null=True, validators=[paddy_app.models.validate_gst]),
        ),
        migrations.AlterField(
            model_name='customertable',
            name='phone_number',
            field=models.CharField(max_length=15),
        ),
    ]
