# Generated by Django 5.1.6 on 2025-02-21 06:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0005_remove_kilometricexpense_location_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kilometricexpense',
            name='project',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
