from django import forms
from .models import ExpenseReport, KilometricExpense, ExpenseReport

# Formulaire pour les rapports de dépenses
class ExpenseReportForm(forms.ModelForm):
    receipt = forms.FileField(required=False, label="Joindre une facture")

    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'currency', 'vat', 'project', 'location', 'refacturable', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),  # Champ de date avec un sélecteur de date
            'description': forms.TextInput(attrs={'class': 'form-control'}),  # Champ de texte pour la description
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),  # Champ numérique pour le montant
            'currency': forms.TextInput(attrs={'class': 'form-control'}),  # Champ de texte pour la devise
            'vat': forms.NumberInput(attrs={'class': 'form-control'}),  # Champ numérique pour la TVA
            'project': forms.TextInput(attrs={'class': 'form-control'}),  # Champ de texte pour le projet
            'location': forms.TextInput(attrs={'class': 'form-control'}),  # Champ de texte pour la localisation
            'refacturable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  # Case à cocher pour refacturable
            'receipt': forms.FileInput(attrs={'class': 'form-control-file'}),  # Champ de fichier pour le reçu
        }

# Formulaire pour les dépenses kilométriques
class KilometricExpenseForm(forms.ModelForm):
    class Meta:
        model = KilometricExpense
        fields = ['date', 'vehicle_type', 'project', 'fiscal_power', 'departure', 'departure_lat', 'departure_lng', 'arrival', 'arrival_lat', 'arrival_lng', 'distance']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),  # Champ de date avec un sélecteur de date
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),  # Sélecteur pour le type de véhicule
            'fiscal_power': forms.NumberInput(attrs={'class': 'form-control'}),  # Champ numérique pour la puissance fiscale
            'departure': forms.TextInput(attrs={'class': 'form-control', 'id': 'departure'}),  # Champ de texte pour le départ
            'arrival': forms.TextInput(attrs={'class': 'form-control', 'id': 'arrival'}),  # Champ de texte pour l'arrivée
            'distance': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'distance'}),  # Champ numérique pour la distance (lecture seule)
            'project': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du projet'}),  # Champ de texte pour le projet avec un placeholder
        }

# Formulaire pour les dépenses générales
class ExpenseForm(forms.ModelForm):
    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'vat', 'project', 'location', 'refacturable', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),  # Champ de date avec un sélecteur de date
            'description': forms.TextInput(attrs={'class': 'form-control'}),  # Champ de texte pour la description
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),  # Champ numérique pour le montant
        }