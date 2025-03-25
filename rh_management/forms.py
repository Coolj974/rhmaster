from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Field, Div
from .models import ExpenseReport, KilometricExpense, LeaveRequest, NotificationEmail, PasswordManager
from django.contrib.auth.decorators import login_required

class BaseForm(forms.ModelForm):
    """Base form class with common functionality"""
    notification_emails = forms.ModelMultipleChoiceField(
        queryset=NotificationEmail.objects.all(),
        required=False,
        label="Voulez-vous envoyer à qui ?",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
    def setup_layout(self, title, fields):
        self.helper.layout = Layout(
            Fieldset(title, *fields),
            Div(Submit('submit', 'Soumettre', css_class='btn btn-primary'),
                css_class='d-grid gap-2')
        )

class ExpenseReportForm(BaseForm):
    """Formulaire pour soumettre un rapport de dépenses."""
    
    class Meta:
        model = ExpenseReport
        fields = [
            'date', 'description', 'amount', 'vat', 
            'project', 'location', 'attachment', 'refacturable'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description de la dépense'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'project': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du projet'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lieu de la dépense'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'refacturable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_layout('Informations sur le rapport de dépenses', self.Meta.fields)

class LeaveRequestForm(BaseForm):
    attachment = forms.FileField(required=False, label="Joindre un justificatif")

    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'attachment', 'notification_emails']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'attachment': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_layout('Demande de congé', self.Meta.fields)

class KilometricExpenseForm(BaseForm):
    class Meta:
        model = KilometricExpense
        fields = ['date', 'vehicle_type', 'project', 'fiscal_power', 'departure', 'departure_lat', 'departure_lng', 'arrival', 'arrival_lat', 'arrival_lng', 'distance', 'notification_emails']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),
            'fiscal_power': forms.NumberInput(attrs={'class': 'form-control'}),
            'departure': forms.TextInput(attrs={'class': 'form-control', 'id': 'departure'}),
            'arrival': forms.TextInput(attrs={'class': 'form-control', 'id': 'arrival'}),
            'distance': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'distance'}),
            'project': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du projet'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_layout('Frais kilométriques', self.Meta.fields)

class ExpenseForm(BaseForm):
    """Formulaire pour soumettre une dépense."""
    
    # Modifiez ici pour remplacer 'receipt' par 'attachment'
    class Meta:
        model = ExpenseReport
        fields = [
            'date', 'description', 'amount', 'vat', 
            'project', 'location', 'attachment', 'refacturable'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description de la dépense'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'project': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du projet'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lieu de la dépense'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}),
            'refacturable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_layout('Dépenses', self.Meta.fields)

class PasswordManagerForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    show_password = forms.BooleanField(required=False, initial=False, 
                                       widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 
                                                                        'onchange': 'togglePasswordVisibility()'}))
    generate_password = forms.BooleanField(required=False, initial=False,
                                          widget=forms.CheckboxInput(attrs={'class': 'form-check-input',
                                                                          'onchange': 'togglePasswordGeneration()'}))
    password_length = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '8', 'max': '32', 'value': '16'}),
                                         required=False)
    
    class Meta:
        model = PasswordManager
        fields = ['title', 'username', 'password', 'url', 'notes', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        instance = kwargs.get('instance', None)
        
        super().__init__(*args, **kwargs)
        
        # Si nous modifions un mot de passe existant, décrypter le mot de passe
        if instance and instance.pk:
            self.fields['password'].initial = instance.decrypt_password()
            
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.user = self.user
            
        # Le mot de passe est déjà en texte brut ici, la méthode save du modèle l'encryptera
        
        if commit:
            instance.save()
            
        return instance
