# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0003_merge_0002_update_fiscal_power_update_fiscal_power'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='theme_preference',
            field=models.CharField(choices=[('light', 'Clair'), ('dark', 'Sombre'), ('system', 'Système')], default='light', max_length=20, verbose_name='Thème préféré'),
        ),
        migrations.AddField(
            model_name='profile',
            name='language_preference',
            field=models.CharField(choices=[('fr', 'Français'), ('en', 'English')], default='fr', max_length=10, verbose_name='Langue préférée'),
        ),
        migrations.AddField(
            model_name='profile',
            name='notifications_enabled',
            field=models.BooleanField(default=True, verbose_name='Notifications activées'),
        ),
        migrations.AddField(
            model_name='profile',
            name='email_notifications',
            field=models.BooleanField(default=True, verbose_name='Notifications par email'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_encadrant',
            field=models.BooleanField(default=False, verbose_name='Est encadrant'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_stp',
            field=models.BooleanField(default=False, verbose_name='Est STP'),
        ),
    ]
