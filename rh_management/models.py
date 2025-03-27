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
    """Modèle pour les demandes de congés."""
    LEAVE_TYPES = (
        ('annual', 'Congé annuel'),
        ('sick', 'Congé maladie'),
        ('parental', 'Congé parental'),
        ('unpaid', 'Congé sans solde'),
        ('bereavement', 'Congé pour décès'),
        ('marriage', 'Congé pour mariage'),
        ('moving', 'Congé pour déménagement'),
        ('other', 'Autre')
    )
    
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé')
    )
    
    HALF_DAY_PERIOD_CHOICES = (
        ('morning', 'Matin'),
        ('afternoon', 'Après-midi')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=10, choices=HALF_DAY_PERIOD_CHOICES, default='morning', blank=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    attachment = models.FileField(upload_to='leave_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    days_requested = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"
    
    class Meta:
        ordering = ['-created_at']

class ExpenseReport(models.Model):
    """Modèle pour les notes de frais."""
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé')
    )
    
    EXPENSE_TYPE_CHOICES = (
        ('transport', 'Transport'),
        ('meal', 'Repas'),
        ('accommodation', 'Hébergement'),
        ('supplies', 'Fournitures'),
        ('communication', 'Communication'),
        ('representation', 'Frais de représentation'),
        ('other', 'Autre')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_reports')
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vat = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES, default='other')
    project = models.CharField(max_length=100, blank=True, null=True)  # Rendu optionnel
    location = models.CharField(max_length=100, blank=True, null=True)  # Rendu optionnel
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)  # Pour le champ du formulaire
    attachment = models.FileField(upload_to='expense_attachments/', blank=True, null=True)  # Rendu optionnel
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    refacturable = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)  # Pour les commentaires d'approbation/rejet
    
    def __str__(self):
        return f"{self.user.username} - {self.description} ({self.date})"
    
    class Meta:
        ordering = ['-created_at']

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
        """Override save to ensure amount is calculated."""
        if self.distance is None:
            self.distance = 0
        
        self.distance = abs(float(self.distance))
        self.amount = self.calculate_amount()
        
        # Ensure we have valid numeric values
        if not isinstance(self.amount, (int, float)):
            self.amount = 0
            
        super().save(*args, **kwargs)
        self.send_notification_emails()

    def calculate_amount(self):
        """Calculate the reimbursement amount based on the vehicle type and fiscal power."""
        if not self.distance or not self.vehicle_type or not self.fiscal_power:
            return 0

        # Barème kilométrique 2024 unifié
        rates = {
            'car': {
                3: 0.529, 4: 0.606, 5: 0.636, 
                6: 0.665, 7: 0.697, 8: 0.697
            },
            'electric_car': {
                3: 0.635, 4: 0.727, 5: 0.763, 
                6: 0.798, 7: 0.836, 8: 0.875
            },
            'motorbike': {
                3: 0.635, 4: 0.727, 5: 0.763, 
                6: 0.798, 7: 0.836
            },
            'bicycle': {
                1: 0.25, 2: 0.25, 3: 0.25
            }
        }

        vehicle_rates = rates.get(self.vehicle_type, {})
        rate = vehicle_rates.get(self.fiscal_power, 0.503)  # Taux par défaut
        return round(float(self.distance) * rate, 2)

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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"Profil de {self.user.username}"

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

    def get_decrypted_password(self):
        """Déchiffre et retourne le mot de passe"""
        try:
            # Créer une instance Fernet avec la clé d'encryption
            cipher_suite = Fernet(self.encryption_key.encode('utf-8'))
            # Déchiffrer le mot de passe
            decrypted_password = cipher_suite.decrypt(self.password.encode('utf-8')).decode('utf-8')
            return decrypted_password
        except Exception as e:
            # En cas d'erreur, retourner une indication
            return "[Erreur de déchiffrement]"

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