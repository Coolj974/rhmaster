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
    ('electric_car', 'Voiture électrique'),
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
                pass

class ExpenseReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vat = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    project = models.CharField(max_length=255, blank=True, null=True)  
    location = models.CharField(max_length=255, blank=True, null=True)  
    refacturable = models.BooleanField(default=False)  
    receipt = models.FileField(upload_to="receipts/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notification_emails = models.TextField(blank=True, null=True)

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
                pass

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
        
        if self.distance:
            self.amount = self.calculate_amount()
        
        super().save(*args, **kwargs)
        self.send_notification_emails()

    def calculate_amount(self):
        """Calculate the reimbursement amount based on the distance and fiscal power."""
        rate_per_km = {
            'car': {
                3: [(0.529, 5000), (0.316, 20000, 1065), (0.37, float('inf'))],
                4: [(0.606, 5000), (0.340, 20000, 1330), (0.407, float('inf'))],
                5: [(0.636, 5000), (0.357, 20000, 1395), (0.427, float('inf'))],
                6: [(0.665, 5000), (0.374, 20000, 1457), (0.447, float('inf'))],
                7: [(0.697, 5000), (0.394, 20000, 1515), (0.470, float('inf'))],
            },
            'electric_car': {
                3: [(0.635, 5000), (0.380, 20000, 1278), (0.444, float('inf'))],
                4: [(0.727, 5000), (0.408, 20000, 1596), (0.488, float('inf'))],
                5: [(0.763, 5000), (0.428, 20000, 1674), (0.512, float('inf'))],
                6: [(0.798, 5000), (0.449, 20000, 1748), (0.536, float('inf'))],
                7: [(0.836, 5000), (0.472, 20000, 1818), (0.564, float('inf'))],
                8: [(0.875, 5000), (0.495, 20000, 1890), (0.592, float('inf'))],
            },
            'motorbike': {
                3: [(0.635, 5000), (0.380, 20000, 1278), (0.444, float('inf'))],
                4: [(0.727, 5000), (0.408, 20000, 1596), (0.488, float('inf'))],
                5: [(0.763, 5000), (0.428, 20000, 1674), (0.512, float('inf'))],
                6: [(0.798, 5000), (0.449, 20000, 1748), (0.536, float('inf'))],
                7: [(0.836, 5000), (0.472, 20000, 1818), (0.564, float('inf'))],
                8: [(0.875, 5000), (0.495, 20000, 1890), (0.592, float('inf'))],
            },
            'bike': {
                1: [(0.1, 5000), (0.05, 20000, 250), (0.07, float('inf'))],
                2: [(0.12, 5000), (0.06, 20000, 300), (0.08, float('inf'))],
                3: [(0.15, 5000), (0.07, 20000, 350), (0.1, float('inf'))],
            }
        }

        vehicle_rates = rate_per_km.get(self.vehicle_type, {})
        rates = vehicle_rates.get(self.fiscal_power, [(0.502, float('inf'))])

        amount = 0
        remaining_distance = self.distance

        for rate, max_distance, *bonus in rates:
            if remaining_distance > max_distance:
                amount += rate * max_distance
                remaining_distance -= max_distance
            else:
                amount += rate * remaining_distance
                if bonus:
                    amount += bonus[0]
                break

        return round(amount)

    def send_notification_emails(self):
        """Send notification emails when a kilometric expense is created."""
        if self.notification_emails:
            try:
                emails = json.loads(self.notification_emails)
                subject = f"Nouvelle dépense kilométrique: {self.description}"
                message = (
                    f"Une nouvelle dépense kilométrique a été soumise par {self.user.username}.\n\n"
                    f"Description: {self.description}\n"
                    f"Montant: {self.amount:.2f} €\n"
                    f"Statut: {self.status}"
                )
                send_mail(subject, message, 'no-reply@example.com', emails)
            except json.JSONDecodeError:
                pass

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.distance} km) - {self.amount:.2f} €"