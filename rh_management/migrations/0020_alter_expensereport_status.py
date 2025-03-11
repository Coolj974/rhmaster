# Generated by Django 5.1.6 on 2025-03-11 12:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0019_alter_kilometricexpense_vehicle_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expensereport',
            name='status',
            field=models.CharField(choices=[('pending', 'En attente'), ('approved', 'Approuvé'), ('rejected', 'Rejeté')], default='pending', max_length=10),
        ),
    ]
