# Generated by Django 5.1.6 on 2025-03-05 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0013_notificationemail_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='kilometricexpense',
            name='notification_emails',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='notification_emails',
            field=models.TextField(blank=True, null=True),
        ),
    ]
