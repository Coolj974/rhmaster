import json
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models

# Constants for choices
STATUS_CHOICES = [
    ('pending', 'En attente'),
    ('approved', 'Approuvé'),
    ('rejected', 'Rejeté'),
]

LEAVE_TYPES = [
    ('CP', 'Congé payé'),
    ('RTT', 'RTT'),
    ('CM', 'Congé maladie'),
    ('SansSolde', 'Congé sans solde'),
]

VEHICLE_TYPES = [
    ('car', 'Voiture'),
    ('motorbike', 'Moto'),
    ('bike', 'Vélo'),
]

class NotificationEmail(models.Model):
    """Model to store notification email addresses for users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.email})"

admin.site.register(NotificationEmail)

class LeaveRequest(models.Model):
    """Model to handle leave requests."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPES, default='CP')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='receipts/', blank=True, null=True)
    notification_emails = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_leave_type_display()} ({self.start_date} à {self.end_date})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.send_notification_emails()

    def send_notification_emails(self):
        """Send notification emails when a leave request is created."""
        if self.notification_emails:
            try:
                emails = json.loads(self.notification_emails)
                subject = f"Nouvelle demande de congé: {self.get_leave_type_display()}"
                message = (
                    f"Une nouvelle demande de congé a été soumise par {self.user.username}.\n\n"
                    f"Type de congé: {self.get_leave_type_display()}\n"
                    f"Dates: {self.start_date} à {self.end_date}\n"
                    f"Statut: {self.status}"
                )
                send_mail(subject, message, 'no-reply@example.com', emails)
            except json.JSONDecodeError:
                pass  # Handle JSON decode error if necessary

class ExpenseReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Montant HT
    vat = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # ✅ Applique une TVA par défaut de 20%
    project = models.CharField(max_length=255, blank=True, null=True)  
    location = models.CharField(max_length=255, blank=True, null=True)  
    refacturable = models.BooleanField(default=False)  
    receipt = models.FileField(upload_to="receipts/", blank=True, null=True)  # Champ pour les pièces justificatives
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notification_emails = models.TextField(blank=True, null=True)  # Champ pour les adresses e-mail de notification

    def __str__(self):
        return f"{self.user.username} - {self.description} ({self.status})"
    
    @property
    def total_amount(self):
        """ Calcul automatique du montant TTC """
        return self.amount + (self.amount * (self.vat / 100))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.send_notification_emails()

    def send_notification_emails(self):
        if self.notification_emails:
            try:
                emails = json.loads(self.notification_emails)
                subject = f"Nouvelle note de frais: {self.description}"
                message = f"Une nouvelle note de frais a été soumise par {self.user.username}.\n\nDescription: {self.description}\nMontant: {self.amount} €\nStatut: {self.status}"
                send_mail(subject, message, 'no-reply@example.com', emails)
            except json.JSONDecodeError:
                pass  # Gérer l'erreur de décodage JSON si nécessaire

class KilometricExpense(models.Model):
    """Model to handle kilometric expenses."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    fiscal_power = models.IntegerField()
    departure = models.CharField(max_length=255)
    departure_lat = models.FloatField(blank=True, null=True)
    departure_lng = models.FloatField(blank=True, null=True)
    arrival = models.CharField(max_length=255)
    arrival_lat = models.FloatField(blank=True, null=True)
    arrival_lng = models.FloatField(blank=True, null=True)
    distance = models.FloatField(blank=True, null=True)
    project = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    description = models.CharField(max_length=255, blank=True)
    notification_emails = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = f"Frais kilométrique de {self.departure} à {self.arrival}"
        rate_per_km = {3: 0.502, 4: 0.575, 5: 0.601, 6: 0.631, 7: 0.661}
        if self.distance:
            self.amount = self.distance * rate_per_km.get(self.fiscal_power, 0.502)
        super().save(*args, **kwargs)
        self.send_notification_emails()

    def send_notification_emails(self):
        """Send notification emails when a kilometric expense is created."""
        if self.notification_emails:
            try:
                emails = json.loads(self.notification_emails)
                subject = f"Nouvelle dépense kilométrique: {self.description}"
                message = (
                    f"Une nouvelle dépense kilométrique a été soumise par {self.user.username}.\n\n"
                    f"Description: {self.description}\n"
                    f"Montant: {self.amount} {self.currency}\n"
                    f"Statut: {self.status}"
                )
                send_mail(subject, message, 'no-reply@example.com', emails)
            except json.JSONDecodeError:
                pass  # Handle JSON decode error if necessary

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.distance} km) - {self.amount:.2f} €"