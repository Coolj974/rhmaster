from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.contrib import messages
from .models import LeaveRequest, LeaveBalance, ExpenseReport, KilometricExpense, NotificationEmail, UserProfile

# Enregistrement simple des modèles déjà présents (si pas déjà fait)
# admin.site.register(NotificationEmail)  # Déjà enregistré dans models.py
admin.site.register(UserProfile)

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'acquired', 'taken', 'available', 'user_email')
    list_filter = ('user__groups',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('available',)
    
    def user_email(self, obj):
        return obj.user.email
    
    user_email.short_description = 'Email'
    
    def available(self, obj):
        """Affiche le solde disponible avec mise en forme colorée."""
        color = 'green' if obj.available > 0 else 'red'
        return format_html('<span style="color:{};">{}</span>', color, obj.available)
    
    available.short_description = 'Solde disponible'

def approve_leaves(modeladmin, request, queryset):
    """Approuve les congés sélectionnés et met à jour les soldes de congés."""
    approved_count = 0
    skipped_count = 0
    
    for leave in queryset:
        # Vérifier que l'utilisateur n'approuve pas sa propre demande
        if leave.user == request.user:
            skipped_count += 1
            continue
            
        # Ne traiter que les demandes en attente pour éviter les mises à jour multiples
        if leave.status != 'approved':
            leave.status = 'approved'
            leave.save()  # Déclenche la mise à jour du solde via la méthode save()
            approved_count += 1
    
    if approved_count > 0:
        messages.success(request, f"{approved_count} demande(s) de congé approuvée(s).")
    
    if skipped_count > 0:
        messages.warning(request, f"{skipped_count} demande(s) de congé vous appartenant ont été ignorées. Vous ne pouvez pas approuver vos propres demandes.")

approve_leaves.short_description = "Approuver les congés sélectionnés"

def reject_leaves(modeladmin, request, queryset):
    """Rejette les congés sélectionnés."""
    rejected_count = 0
    skipped_count = 0
    
    for leave in queryset:
        # Vérifier que l'utilisateur ne rejette pas sa propre demande
        if leave.user == request.user:
            skipped_count += 1
            continue
            
        # Ne traiter que les demandes en attente ou approuvées
        if leave.status != 'rejected':
            leave.status = 'rejected'
            leave.save()  # Déclenche la réattribution des jours si nécessaire via save()
            rejected_count += 1
    
    if rejected_count > 0:
        messages.success(request, f"{rejected_count} demande(s) de congé rejetée(s).")
    
    if skipped_count > 0:
        messages.warning(request, f"{skipped_count} demande(s) de congé vous appartenant ont été ignorées. Vous ne pouvez pas rejeter vos propres demandes.")

reject_leaves.short_description = "Refuser les congés sélectionnés"

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'leave_type', 'start_date', 'end_date', 'status', 'duration', 'created_at')
    list_filter = ('status', 'leave_type', 'start_date', 'user__groups')
    search_fields = ('user__username', 'user__email', 'reason')
    date_hierarchy = 'start_date'
    actions = [approve_leaves, reject_leaves]
    readonly_fields = ('created_at',)
    
    def duration(self, obj):
        """Calcule la durée du congé en jours."""
        delta = obj.end_date - obj.start_date
        return f"{delta.days + 1} jour(s)"
    
    duration.short_description = 'Durée'
    
    def get_queryset(self, request):
        # Tri par défaut: les demandes en attente d'abord, puis par date de début
        return super().get_queryset(request).order_by(
            # -1 pour pending, 0 pour approved, 1 pour rejected
            # Cette astuce assure que "pending" est toujours en premier
            models.Case(
                models.When(status='pending', then=models.Value(-1)),
                models.When(status='approved', then=models.Value(0)),
                models.When(status='rejected', then=models.Value(1)),
                default=models.Value(2),
                output_field=models.IntegerField(),
            ),
            '-start_date'
        )
    
    def save_model(self, request, obj, form, change):
        """Surcharge pour mettre à jour le solde de congés à l'enregistrement dans l'admin."""
        # Vérifier si le statut est modifié vers "approved" ou depuis "approved"
        if change:
            original_obj = LeaveRequest.objects.get(pk=obj.pk)
            status_changed = original_obj.status != obj.status
        else:
            status_changed = False
        
        # Laisser la méthode save() du modèle gérer les mises à jour
        super().save_model(request, obj, form, change)

@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    # Ajout d'une méthode pour calculer le montant total
    def total_amount(self, obj):
        """
        Calcule le montant total incluant la TVA
        """
        if obj.vat and obj.amount:
            # Calculer le montant avec TVA
            total = obj.amount * (1 + (obj.vat / 100))
            return f"{total:.2f} €"
        return f"{obj.amount} €"
    
    total_amount.short_description = "Montant total (TVA incluse)"
    
    # Assurez-vous que list_display et les autres attributs restent inchangés
    list_display = ['user', 'date', 'description', 'amount', 'vat', 'total_amount', 'status', 'created_at']
    list_filter = ('status', 'date', 'refacturable', 'user__groups')
    search_fields = ('user__username', 'description', 'project', 'location')
    date_hierarchy = 'date'
    actions = ['approve_expenses', 'reject_expenses']
    
    def approve_expenses(self, request, queryset):
        approved_count = 0
        skipped_count = 0
        
        for expense in queryset:
            # Vérifier que l'utilisateur n'approuve pas sa propre note de frais
            if expense.user == request.user:
                skipped_count += 1
                continue
                
            expense.status = 'approved'
            expense.save()
            approved_count += 1
        
        if approved_count > 0:
            messages.success(request, f"{approved_count} note(s) de frais approuvée(s).")
        
        if skipped_count > 0:
            messages.warning(request, f"{skipped_count} note(s) de frais vous appartenant ont été ignorées. Vous ne pouvez pas approuver vos propres notes de frais.")
    
    approve_expenses.short_description = "Approuver les notes de frais sélectionnées"
    
    def reject_expenses(self, request, queryset):
        rejected_count = 0
        skipped_count = 0
        
        for expense in queryset:
            # Vérifier que l'utilisateur ne rejette pas sa propre note de frais
            if expense.user == request.user:
                skipped_count += 1
                continue
                
            expense.status = 'rejected'
            expense.save()
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f"{rejected_count} note(s) de frais rejetée(s).")
        
        if skipped_count > 0:
            messages.warning(request, f"{skipped_count} note(s) de frais vous appartenant ont été ignorées. Vous ne pouvez pas rejeter vos propres notes de frais.")
    
    reject_expenses.short_description = "Refuser les notes de frais sélectionnées"

@admin.register(KilometricExpense)
class KilometricExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'departure', 'arrival', 'distance', 'amount', 'status')
    list_filter = ('status', 'date', 'vehicle_type', 'user__groups')
    search_fields = ('user__username', 'departure', 'arrival', 'project', 'description')
    date_hierarchy = 'date'
    actions = ['approve_kilometric_expenses', 'reject_kilometric_expenses']
    
    def approve_kilometric_expenses(self, request, queryset):
        approved_count = 0
        skipped_count = 0
        
        for expense in queryset:
            # Vérifier que l'utilisateur n'approuve pas ses propres frais kilométriques
            if expense.user == request.user:
                skipped_count += 1
                continue
                
            expense.status = 'approved'
            expense.save()
            approved_count += 1
        
        if approved_count > 0:
            messages.success(request, f"{approved_count} frais kilométrique(s) approuvé(s).")
        
        if skipped_count > 0:
            messages.warning(request, f"{skipped_count} frais kilométrique(s) vous appartenant ont été ignorés. Vous ne pouvez pas approuver vos propres frais kilométriques.")
    
    approve_kilometric_expenses.short_description = "Approuver les frais kilométriques sélectionnés"
    
    def reject_kilometric_expenses(self, request, queryset):
        rejected_count = 0
        skipped_count = 0
        
        for expense in queryset:
            # Vérifier que l'utilisateur ne rejette pas ses propres frais kilométriques
            if expense.user == request.user:
                skipped_count += 1
                continue
                
            expense.status = 'rejected'
            expense.save()
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f"{rejected_count} frais kilométrique(s) rejeté(s).")
        
        if skipped_count > 0:
            messages.warning(request, f"{skipped_count} frais kilométrique(s) vous appartenant ont été ignorés. Vous ne pouvez pas rejeter vos propres frais kilométriques.")
    
    reject_kilometric_expenses.short_description = "Refuser les frais kilométriques sélectionnés"
