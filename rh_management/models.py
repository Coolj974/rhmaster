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

class Leave(models.Model):
    """Modèle pour les demandes de congés"""
    LEAVE_TYPE_CHOICES = (
        ('annual', 'Congé annuel'),
        ('sick', 'Congé maladie'),
        ('parental', 'Congé parental'),
        ('unpaid', 'Congé sans solde'),
        ('bereavement', 'Congé pour décès'),
        ('marriage', 'Congé pour mariage'),
        ('moving', 'Congé pour déménagement'),
        ('other', 'Autre'),
    )
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    )
    HALF_DAY_PERIOD_CHOICES = (
        ('morning', 'Matin'),
        ('afternoon', 'Après-midi'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaves')
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    days_requested = models.DecimalField(max_digits=5, decimal_places=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)  # Commentaire pour approbation/rejet
    attachment = models.FileField(upload_to='leave_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=10, choices=HALF_DAY_PERIOD_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_leave_type_display()} ({self.start_date} au {self.end_date})"

    class Meta:
        ordering = ['-created_at']

class LeaveBalance(models.Model):
    """Modèle pour suivre le solde de congés des employés"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leave_balance')
    acquired = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # Jours acquis
    taken = models.DecimalField(max_digits=5, decimal_places=1, default=0)     # Jours pris
    available = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # Solde disponible
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Solde de congés de {self.user.username}: {self.available} jours"

    def update_balance(self, days_used=0):
        """Met à jour le solde de congés après une demande de congé approuvée"""
        self.taken += days_used
        self.available = self.acquired - self.taken
        self.save()

class LeaveAdjustment(models.Model):
    """Modèle pour suivre les ajustements de solde de congés"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_adjustments')
    adjustment = models.DecimalField(max_digits=5, decimal_places=1)  # Positif pour ajout, négatif pour déduction
    reason = models.CharField(max_length=255)
    adjusted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leave_adjustments_made')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        adjustment_type = "Ajout" if self.adjustment > 0 else "Déduction"
        return f"{adjustment_type} de {abs(self.adjustment)} jours pour {self.user.username}"

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
    
    @property
    def montant_ttc(self):
        """Calcule le montant total TTC incluant la TVA."""
        return self.amount * (1 + (self.vat / 100))
    
    class Meta:
        ordering = ['-created_at']

class Expense(models.Model):
    """Modèle pour les notes de frais"""
    EXPENSE_TYPE_CHOICES = (
        ('transport', 'Transport'),
        ('accommodation', 'Hébergement'),
        ('food', 'Repas'),
        ('supplies', 'Fournitures'),
        ('other', 'Autre'),    )
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    receipt = models.FileField(upload_to='expense_receipts/', blank=True, null=True)
    project = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    vat = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    refacturable = models.BooleanField(default=False)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.description} ({self.amount} €) - {self.user.username}"
        
    @property
    def amount_with_vat(self):
        """Calcule le montant total TTC"""
        if self.vat:
            return self.amount * (1 + self.vat / 100)
        return self.amount

    class Meta:
        ordering = ['-date']

class KilometricExpense(models.Model):
    """Modèle pour les frais kilométriques"""
    
    VEHICLE_TYPE_CHOICES = (
        ('car', 'Voiture'),
        ('electric_car', 'Voiture électrique'),
        ('motorbike', 'Moto'),
    )
    
    FISCAL_POWER_CHOICES = (
        ('small', '3 CV et moins'),
        ('medium', '4 à 5 CV'),
        ('large', '6 à 7 CV'),
        ('xlarge', '8 CV et plus'),
        ('electric', 'Électrique'),
        ('motorbike', 'Moto/Scooter'),
    )
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kilometric_expenses')
    date = models.DateField()
    description = models.CharField(max_length=255)
    departure = models.CharField(max_length=255)
    arrival = models.CharField(max_length=255)
    departure_lat = models.FloatField(blank=True, null=True)
    departure_lng = models.FloatField(blank=True, null=True)
    arrival_lat = models.FloatField(blank=True, null=True)
    arrival_lng = models.FloatField(blank=True, null=True)
    distance = models.IntegerField()  # en km
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    fiscal_power = models.CharField(max_length=20, choices=FISCAL_POWER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    project = models.CharField(max_length=100, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trajet {self.departure} → {self.arrival} ({self.distance} km) - {self.user.username}"

    class Meta:
        ordering = ['-date']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Relations pour encadrants et équipes
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='supervised_employees',
                                  help_text="Supérieur hiérarchique de l'employé")
    is_supervisor = models.BooleanField(default=False, 
                                     help_text="Indique si l'utilisateur est un encadrant")

    # Préférences utilisateur
    theme_preference = models.CharField(max_length=10, default='light', choices=[
        ('light', 'Thème clair'),
        ('dark', 'Thème sombre'),
        ('system', 'Thème du système')
    ])
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    language_preference = models.CharField(max_length=5, default='fr', choices=[
        ('fr', 'Français'),
        ('en', 'Anglais')
    ])

    def __str__(self):
        return f"Profil de {self.user.username}"
    
    def get_role(self):
        """Renvoie le rôle principal de l'utilisateur"""
        user = self.user
        if user.is_superuser:
            return "Admin"
        if user.is_staff or user.groups.filter(name="RH").exists():
            return "RH"
        if user.groups.filter(name="Encadrant").exists():
            return "Encadrant"
        if user.groups.filter(name="STP").exists():
            return "STP"
        if user.groups.filter(name="Employé").exists():
            return "Employé"
        return "Sans rôle"

class Profile(models.Model):
    """Modèle de profil utilisateur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name="Poste")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, verbose_name="Photo de profil")
    date_of_birth = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    hire_date = models.DateField(blank=True, null=True, verbose_name="Date d'embauche")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="subordinates", verbose_name="Responsable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.user.username}"
    
    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"
        ordering = ['user__first_name', 'user__last_name']

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

class CustomPermission(models.Model):
    """Modèle pour gérer les permissions personnalisées."""
    name = models.CharField(max_length=255, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Permission personnalisée'
        verbose_name_plural = 'Permissions personnalisées'

    def __str__(self):
        return self.name

class PermissionGroup(models.Model):
    """Modèle pour gérer les groupes de permissions."""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(CustomPermission)
    users = models.ManyToManyField(User, related_name='custom_groups')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Groupe de permissions'
        verbose_name_plural = 'Groupes de permissions'

    def __str__(self):
        return self.name

class Notification(models.Model):
    """Modèle pour stocker les notifications envoyées aux utilisateurs."""
    NOTIFICATION_TYPES = (
        ('leave', 'Congé'),
        ('expense', 'Note de frais'),
        ('km_expense', 'Frais kilométrique'),
        ('system', 'Système'),
        ('password', 'Mot de passe partagé'),
        ('profile', 'Profil')
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    object_id = models.IntegerField(null=True, blank=True)  # ID de l'objet concerné (congé, note de frais, etc.)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    icon = models.CharField(max_length=50, default='fa-bell')  # Classe d'icône Font Awesome
    color = models.CharField(max_length=20, default='primary')  # Classe de couleur Bootstrap
    url = models.CharField(max_length=255, blank=True, null=True)  # URL associée à la notification
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @classmethod
    def create_leave_notification(cls, user, leave_request, message, is_manager=False):
        """Crée une notification pour une demande de congé."""
        if is_manager:
            title = f"Nouvelle demande de congé de {leave_request.user.get_full_name() or leave_request.user.username}"
            icon = "fa-calendar-check"
            url = f"/manage-leaves/?user_id={leave_request.user.id}"
        else:
            title = f"Mise à jour de votre demande de congé"
            icon = "fa-calendar-alt"
            url = "/my-leaves/"
            
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type='leave',
            object_id=leave_request.id,
            icon=icon,
            color='success',
            url=url
        )
    
    @classmethod
    def create_expense_notification(cls, user, expense, message, is_manager=False):
        """Crée une notification pour une note de frais."""
        if is_manager:
            title = f"Nouvelle note de frais de {expense.user.get_full_name() or expense.user.username}"
            icon = "fa-file-invoice-dollar"
            url = f"/manage-expenses/?user_id={expense.user.id}"
        else:
            title = f"Mise à jour de votre note de frais"
            icon = "fa-receipt"
            url = "/my-expenses/"
            
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type='expense',
            object_id=expense.id,
            icon=icon,
            color='warning',
            url=url
        )
    
    @classmethod
    def create_km_expense_notification(cls, user, km_expense, message, is_manager=False):
        """Crée une notification pour des frais kilométriques."""
        if is_manager:
            title = f"Nouveaux frais kilométriques de {km_expense.user.get_full_name() or km_expense.user.username}"
            icon = "fa-car"
            url = f"/manage-kilometric-expenses/?user_id={km_expense.user.id}"
        else:
            title = f"Mise à jour de vos frais kilométriques"
            icon = "fa-route"
            url = "/my-kilometric-expenses/"
            
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type='km_expense',
            object_id=km_expense.id,
            icon=icon,
            color='danger',
            url=url
        )
        
    @classmethod
    def create_system_notification(cls, user, title, message):
        """Crée une notification système."""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type='system',
            icon="fa-info-circle",
            color='info'
        )

class Department(models.Model):
    """Modèle pour les départements de l'entreprise"""
    name = models.CharField(max_length=100, verbose_name="Nom")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_departments", verbose_name="Responsable")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Département"
        verbose_name_plural = "Départements"
        ordering = ['name']