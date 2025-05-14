from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q

# Autres imports et modèles ici...

class Expense(models.Model):
    """Modèle pour les notes de frais"""
    EXPENSE_TYPE_CHOICES = (
        ('transport', 'Transport'),
        ('accommodation', 'Hébergement'),
        ('food', 'Repas'),
        ('supplies', 'Fournitures'),
        ('other', 'Autre'),
    )
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
