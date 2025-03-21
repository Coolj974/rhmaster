import json
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.utils.crypto import get_random_string
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

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

    def get_duration_days(self):
        """Calcule la durée du congé en jours."""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days + 1
        return 0

    def save(self, *args, **kwargs):
        # Vérifier si c'est une modification et si le statut change à "approved"
        if self.pk:  # Si l'objet existe déjà (modification)
            old_instance = LeaveRequest.objects.get(pk=self.pk)
            status_changed_to_approved = old_instance.status != 'approved' and self.status == 'approved'
            status_changed_from_approved = old_instance.status == 'approved' and self.status != 'approved'
            
            # Mettre à jour après sauvegarde pour éviter problèmes de transaction
            super().save(*args, **kwargs)

            # Mettre à jour le solde de congés quand le statut change à approved
            if status_changed_to_approved and self.leave_type in ['CP', 'RTT']:
                leave_balance, created = LeaveBalance.objects.get_or_create(user=self.user)
                leave_balance.taken += self.get_duration_days()
                leave_balance.save()
            
            # Rendre les jours de congés si le statut passe de approved à autre chose
            elif status_changed_from_approved and self.leave_type in ['CP', 'RTT']:
                leave_balance, created = LeaveBalance.objects.get_or_create(user=self.user)
                leave_balance.taken = max(0, leave_balance.taken - self.get_duration_days())
                leave_balance.save()
        else:
            # Nouvelle demande, pas de mise à jour du solde nécessaire
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
        from decimal import Decimal
        return self.amount + (self.amount * (self.vat / Decimal('100')))

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
    created_at = models.DateTimeField(auto_now_add=True)  # Date de soumission automatique
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

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_employee = models.BooleanField(default=False)
    is_stp = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)
    # Les champs is_staff et is_superuser sont déjà dans le modèle User

class LeaveBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leave_balance')
    acquired = models.FloatField(default=0.0, help_text="Total des jours de congés acquis")
    taken = models.FloatField(default=0.0, help_text="Total des jours de congés pris")
    
    @property
    def available(self):
        """Calcule le solde de congés disponible."""
        return self.acquired - self.taken
        
    def __str__(self):
        return f"Solde de congés de {self.user.username}: {self.available} jours"

class PasswordManager(models.Model):
    """Model to handle password entries securely."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    password = models.TextField()  # Will store encrypted password
    url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    # Encryption key securely stored for each password
    encryption_key = models.TextField()

    def __str__(self):
        return f"{self.title} ({self.user.username})"

    def save(self, *args, **kwargs):
        # Generate a new encryption key if not present
        if not self.encryption_key:
            self.encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        
        # Encrypt the password if it's not already encrypted
        if not kwargs.pop('skip_encryption', False):
            self.encrypt_password()
        
        super().save(*args, **kwargs)

    def encrypt_password(self):
        """Encrypt the password using the object's encryption key."""
        if not self.password:
            return
            
        cipher_suite = Fernet(self.encryption_key.encode())
        encrypted_password = cipher_suite.encrypt(self.password.encode())
        self.password = encrypted_password.decode()

    def decrypt_password(self):
        """Decrypt the password using the object's encryption key."""
        try:
            cipher_suite = Fernet(self.encryption_key.encode())
            decrypted_password = cipher_suite.decrypt(self.password.encode())
            return decrypted_password.decode()
        except Exception:
            return "Erreur de déchiffrement"

    def generate_password(self, length=16):
        """Generate a strong random password."""
        chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?'
        return get_random_string(length, chars)

class PasswordShare(models.Model):
    """Model to handle password sharing between users."""
    password_entry = models.ForeignKey(PasswordManager, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_passwords')
    created_at = models.DateTimeField(auto_now_add=True)
    can_edit = models.BooleanField(default=False)  # Détermine si l'utilisateur peut modifier le mot de passe partagé
    
    class Meta:
        unique_together = ('password_entry', 'shared_with')
        
    def __str__(self):
        return f"{self.password_entry.title} partagé avec {self.shared_with.username}"