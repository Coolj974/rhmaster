from django.db import models
from django.contrib.auth.models import User

# ✅ Définition des choix de statut AVANT leur utilisation
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

class LeaveRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=10, choices=LEAVE_TYPES, default='CP')  # ✅ Type de congé
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)  # ✅ Commentaire optionnel
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')  # ✅ Correction
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_leave_type_display()} ({self.start_date} à {self.end_date})"


# Modèle pour les notes de frais
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
    currency = models.CharField(max_length=10, default="€")  
    vat = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # ✅ Applique une TVA par défaut de 20%
    project = models.CharField(max_length=255, blank=True, null=True)  
    location = models.CharField(max_length=255, blank=True, null=True)  
    refacturable = models.BooleanField(default=False)  
    receipt = models.FileField(upload_to="receipts/", blank=True, null=True)  # Champ pour les pièces justificatives
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.user.username} - {self.description} ({self.status})"
    
    @property
    def total_amount(self):
        """ Calcul automatique du montant TTC """
        return self.amount + (self.amount * (self.vat / 100))


# Liste des types de véhicules
VEHICLE_TYPES = [
    ('car', 'Voiture'),
    ('motorbike', 'Moto'),
    ('bike', 'Vélo'),
]

class KilometricExpense(models.Model):
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("approved", "Approuvé"),
        ("rejected", "Rejeté"),
    ]
    
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
    project = models.CharField(max_length=255, blank=True, null=True)  # Nouveau champ "Projet"
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Déjà limité à 2 décimales
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def save(self, *args, **kwargs):
        rate_per_km = {3: 0.502, 4: 0.575, 5: 0.601, 6: 0.631, 7: 0.661}
        if self.distance:
            self.amount = self.distance * rate_per_km.get(self.fiscal_power, 0.502)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.distance} km) - {self.amount:.2f} €"