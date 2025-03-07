from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Fieldset, Field, Div
from .models import ExpenseReport, KilometricExpense, LeaveRequest, NotificationEmail

class ExpenseReportForm(forms.ModelForm):
    receipt = forms.FileField(required=False, label="Joindre une facture")
    notification_emails = forms.ModelMultipleChoiceField(
        queryset=NotificationEmail.objects.all(),
        required=False,
        label="Voulez-vous envoyer à qui ?",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'vat', 'project', 'location', 'refacturable', 'receipt', 'notification_emails']
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
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Informations sur le rapport de dépenses',
                'date',
                'description',
                'amount',
                'vat',
                'project',
                'location',
                'refacturable',
                'receipt',
                'notification_emails'
            ),
            Div(
                Submit('submit', 'Soumettre', css_class='btn btn-primary'),
                css_class='d-grid gap-2'
            )
        )

class LeaveRequestForm(forms.ModelForm):
    attachment = forms.FileField(required=False, label="Joindre un justificatif")
    notification_emails = forms.ModelMultipleChoiceField(
        queryset=NotificationEmail.objects.all(),
        required=False,
        label="Voulez-vous envoyer à qui ?",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

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
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Demande de congé',
                'leave_type',
                'start_date',
                'end_date',
                'reason',
                'attachment',
                'notification_emails'
            ),
            Div(
                Submit('submit', 'Soumettre', css_class='btn btn-primary'),
                css_class='d-grid gap-2'
            )
        )

class KilometricExpenseForm(forms.ModelForm):
    notification_emails = forms.ModelMultipleChoiceField(
        queryset=NotificationEmail.objects.all(),
        required=False,
        label="Voulez-vous envoyer à qui ?",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

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
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Frais kilométriques',
                'date',
                'vehicle_type',
                'project',
                'fiscal_power',
                'departure',
                'departure_lat',
                'departure_lng',
                'arrival',
                'arrival_lat',
                'arrival_lng',
                'distance',
                'notification_emails'
            ),
            Div(
                Submit('submit', 'Soumettre', css_class='btn btn-primary'),
                css_class='d-grid gap-2'
            )
        )

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = ExpenseReport
        fields = ['date', 'description', 'amount', 'vat', 'project', 'location', 'refacturable', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Dépenses',
                'date',
                'description',
                'amount',
                'vat',
                'project',
                'location',
                'refacturable',
                'receipt'
            ),
            Div(
                Submit('submit', 'Soumettre', css_class='btn btn-primary'),
                css_class='d-grid gap-2'
            )
        )