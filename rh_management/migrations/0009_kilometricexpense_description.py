# Generated by Django 5.1.6 on 2025-02-27 05:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0008_alter_expensereport_vat'),
    ]

    operations = [
        migrations.AddField(
            model_name='kilometricexpense',
            name='description',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
