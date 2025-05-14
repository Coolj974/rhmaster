from django.db import migrations, models

def update_fiscal_power(apps, schema_editor):
    KilometricExpense = apps.get_model('rh_management', 'KilometricExpense')
    
    # Migrer les anciennes valeurs vers les nouvelles
    for expense in KilometricExpense.objects.filter(fiscal_power='normal'):
        expense.fiscal_power = 'medium'
        expense.save()
    
    for expense in KilometricExpense.objects.filter(fiscal_power='high'):
        expense.fiscal_power = 'large'
        expense.save()

class Migration(migrations.Migration):

    dependencies = [
        ('rh_management', '0001_initial'),  # Remplacer par la dernière migration
    ]

    operations = [
        migrations.AlterField(
            model_name='kilometricexpense',
            name='fiscal_power',
            field=models.CharField(
                choices=[
                    ('small', '3 CV et moins'),
                    ('medium', '4 à 5 CV'),
                    ('large', '6 à 7 CV'),
                    ('xlarge', '8 CV et plus'),
                    ('electric', 'Électrique'),
                    ('motorbike', 'Moto/Scooter'),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(update_fiscal_power),
    ]
