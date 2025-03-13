from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Field, Div
from .models import ExpenseReport, KilometricExpense, LeaveRequest, NotificationEmail
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
    receipt = forms.FileField(required=False, label="Joindre une facture")

    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'vat', 'project', 'location', 'refacturable', 'receipt', 'notification_emails']
        labels = {
            'date': 'Date',
            'description': 'Description',
            'amount': 'Montant',
            'vat': 'TVA',
            'project': 'Projet',
            'location': 'Localisation',
            'refacturable': 'Refacturable'
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'refacturable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control-file'}),
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
    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'vat', 'project', 'location', 'refacturable', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'vat': forms.NumberInput(attrs={'class': 'form-control'}),
            'project': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'refacturable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_layout('Dépenses', self.Meta.fields)
