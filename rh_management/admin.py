from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import UserAdmin, AdminPasswordChangeForm
from django.contrib.auth.models import User
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _
from .models import LeaveRequest, LeaveBalance, ExpenseReport, KilometricExpense, NotificationEmail, UserProfile, CustomPermission, PermissionGroup

# Personnalisation de l'interface admin
admin.site.site_header = "CybeRH Administration"
admin.site.site_title = "CybeRH Admin"
admin.site.index_title = "Tableau de bord d'administration"

# Enregistrement simple des modèles déjà présents
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
    
    def has_delete_permission(self, request, obj=None):
        # Empêcher la suppression des soldes de congés
        return False

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
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'leave_type', 'start_date', 'end_date', 'days_requested')
        }),
        ('Détails', {
            'fields': ('reason', 'half_day', 'half_day_period', 'attachment')
        }),
        ('Statut', {
            'fields': ('status', 'comment', 'created_at', 'updated_at')
        }),
    )
    
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
    
    def get_readonly_fields(self, request, obj=None):
        # Rendre certains champs en lecture seule après la création
        if obj:  # si l'objet existe déjà
            return ('user', 'created_at', 'updated_at', 'days_requested')
        return ('created_at', 'updated_at')

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
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'date', 'description', 'amount')
        }),
        ('Détails', {
            'fields': ('expense_type', 'vat', 'project', 'location', 'refacturable')
        }),
        ('Justificatifs', {
            'fields': ('receipt', 'attachment')
        }),
        ('Statut', {
            'fields': ('status', 'comment')
        }),
    )
    
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
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('user', 'date', 'description', 'project')
        }),
        ('Trajet', {
            'fields': ('departure', 'arrival', 'distance')
        }),
        ('Véhicule', {
            'fields': ('vehicle_type', 'fiscal_power')
        }),
        ('Coordonnées GPS', {
            'fields': ('departure_lat', 'departure_lng', 'arrival_lat', 'arrival_lng'),
            'classes': ('collapse',)
        }),
        ('Montant et statut', {
            'fields': ('amount', 'status')
        }),
    )
    
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

# Modification de notre UserAdmin pour inclure les groupes et permissions
class EnhancedUserAdmin(UserAdmin):
    # Ajout de l'affichage des groupes dans la liste
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_groups', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    # Ajout d'actions pour gérer les rôles
    actions = ['assign_employee_role', 'assign_rh_role', 'assign_stp_role', 'assign_encadrant_role', 
               'remove_employee_role', 'remove_rh_role', 'remove_stp_role', 'remove_encadrant_role']
    
    def get_groups(self, obj):
        """Affiche les groupes de l'utilisateur"""
        return ", ".join([g.name for g in obj.groups.all()]) or "-"
    get_groups.short_description = 'Rôles'
    
    # Actions pour ajouter des rôles
    def assign_employee_role(self, request, queryset):
        group, _ = Group.objects.get_or_create(name='Employé')
        for user in queryset:
            user.groups.add(group)
        messages.success(request, f"{queryset.count()} utilisateur(s) ont reçu le rôle Employé.")
    assign_employee_role.short_description = "Attribuer le rôle Employé"
    
    def assign_rh_role(self, request, queryset):
        group, _ = Group.objects.get_or_create(name='RH')
        for user in queryset:
            user.groups.add(group)
        messages.success(request, f"{queryset.count()} utilisateur(s) ont reçu le rôle RH.")
    assign_rh_role.short_description = "Attribuer le rôle RH"
    
    def assign_stp_role(self, request, queryset):
        group, _ = Group.objects.get_or_create(name='STP')
        for user in queryset:
            user.groups.add(group)
        messages.success(request, f"{queryset.count()} utilisateur(s) ont reçu le rôle STP.")
    assign_stp_role.short_description = "Attribuer le rôle STP"
    
    def assign_encadrant_role(self, request, queryset):
        group, _ = Group.objects.get_or_create(name='Encadrant')
        for user in queryset:
            user.groups.add(group)
        messages.success(request, f"{queryset.count()} utilisateur(s) ont reçu le rôle Encadrant.")
    assign_encadrant_role.short_description = "Attribuer le rôle Encadrant"
    
    # Actions pour retirer des rôles
    def remove_employee_role(self, request, queryset):
        try:
            group = Group.objects.get(name='Employé')
            for user in queryset:
                user.groups.remove(group)
            messages.success(request, f"Rôle Employé retiré pour {queryset.count()} utilisateur(s).")
        except Group.DoesNotExist:
            messages.error(request, "Le groupe Employé n'existe pas.")
    remove_employee_role.short_description = "Retirer le rôle Employé"
    
    def remove_rh_role(self, request, queryset):
        try:
            group = Group.objects.get(name='RH')
            for user in queryset:
                user.groups.remove(group)
            messages.success(request, f"Rôle RH retiré pour {queryset.count()} utilisateur(s).")
        except Group.DoesNotExist:
            messages.error(request, "Le groupe RH n'existe pas.")
    remove_rh_role.short_description = "Retirer le rôle RH"
    
    def remove_stp_role(self, request, queryset):
        try:
            group = Group.objects.get(name='STP')
            for user in queryset:
                user.groups.remove(group)
            messages.success(request, f"Rôle STP retiré pour {queryset.count()} utilisateur(s).")
        except Group.DoesNotExist:
            messages.error(request, "Le groupe STP n'existe pas.")
    remove_stp_role.short_description = "Retirer le rôle STP"
    
    def remove_encadrant_role(self, request, queryset):
        try:
            group = Group.objects.get(name='Encadrant')
            for user in queryset:
                user.groups.remove(group)
            messages.success(request, f"Rôle Encadrant retiré pour {queryset.count()} utilisateur(s).")
        except Group.DoesNotExist:
            messages.error(request, "Le groupe Encadrant n'existe pas.")
    remove_encadrant_role.short_description = "Retirer le rôle Encadrant"
    
    # Ajout d'un panneau de statistiques pour chaque utilisateur
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:  # Si nous sommes en mode édition d'un utilisateur existant
            # Ajouter un fieldset pour les statistiques
            stats_fieldset = ('Statistiques', {
                'fields': ('user_leaves_count', 'user_expenses_count', 'user_km_expenses_count'),
                'classes': ('collapse',),
            })
            return fieldsets + (stats_fieldset,)
        return fieldsets
    
    def user_leaves_count(self, obj):
        count = LeaveRequest.objects.filter(user=obj).count()
        pending = LeaveRequest.objects.filter(user=obj, status='pending').count()
        return format_html('<a href="{}?user__id__exact={}">{} demande(s) de congés (dont {} en attente)</a>',
                           reverse('admin:rh_management_leaverequest_changelist'), obj.id, count, pending)
    user_leaves_count.short_description = "Congés"
    
    def user_expenses_count(self, obj):
        count = ExpenseReport.objects.filter(user=obj).count()
        return format_html('<a href="{}?user__id__exact={}">{} note(s) de frais</a>',
                           reverse('admin:rh_management_expensereport_changelist'), obj.id, count)
    user_expenses_count.short_description = "Notes de frais"
    
    def user_km_expenses_count(self, obj):
        count = KilometricExpense.objects.filter(user=obj).count()
        return format_html('<a href="{}?user__id__exact={}">{} frais kilométriques</a>',
                           reverse('admin:rh_management_kilometricexpense_changelist'), obj.id, count)
    user_km_expenses_count.short_description = "Frais kilométriques"
    
    # Ajout de méthodes pour les champs calculés
    def get_readonly_fields(self, request, obj=None):
        # Ces champs sont calculés, donc en lecture seule
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            return readonly_fields + ('user_leaves_count', 'user_expenses_count', 'user_km_expenses_count')
        return readonly_fields

# Amélioration de l'admin pour CustomPermission
class CustomPermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'description', 'get_groups_count')
    search_fields = ('name', 'codename', 'description')
    ordering = ('name',)
    
    # Ajouter un champ pour voir les groupes utilisant cette permission
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            kwargs["widget"] = admin.widgets.FilteredSelectMultiple(
                db_field.verbose_name, False
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def get_groups_count(self, obj):
        """Nombre de groupes utilisant cette permission"""
        return PermissionGroup.objects.filter(permissions=obj).count()
    get_groups_count.short_description = "Groupes"

# Amélioration de l'admin pour PermissionGroup
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'get_users_count', 'get_permissions_count')
    filter_horizontal = ('permissions', 'users')
    search_fields = ('name', 'description')
    
    # Amélioration du filtre sur les utilisateurs
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "users" or db_field.name == "permissions":
            kwargs["widget"] = admin.widgets.FilteredSelectMultiple(
                db_field.verbose_name, False
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def get_users_count(self, obj):
        return obj.users.count()
    get_users_count.short_description = 'Utilisateurs'
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'Permissions'

# Interface admin pour les groupes Django standard (rôles)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_users_count', 'get_permissions_count')
    filter_horizontal = ('permissions',)
    search_fields = ('name',)
    
    # Ajout d'une action pour voir les utilisateurs avec ce rôle
    def view_users(self, request, queryset):
        if queryset.count() != 1:
            messages.error(request, "Veuillez sélectionner un seul rôle à la fois.")
            return
            
        role = queryset.first()
        return redirect(f"/admin/auth/user/?groups__name={role.name}")
    view_users.short_description = "Voir les utilisateurs avec ce rôle"
    
    # Ajouter l'action à la liste
    actions = ['view_users']
    
    def get_users_count(self, obj):
        return obj.user_set.count()
    get_users_count.short_description = 'Utilisateurs'
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = 'Permissions'

# Désenregistrez l'admin user par défaut et enregistrez notre version améliorée
admin.site.unregister(User)
admin.site.register(User, EnhancedUserAdmin)

# Désenregistrez les groupes standard et enregistrez notre version améliorée
admin.site.unregister(Group)
admin.site.register(Group, RoleAdmin)

# Enregistrez les modèles personnalisés de permissions
admin.site.register(CustomPermission, CustomPermissionAdmin)
admin.site.register(PermissionGroup, PermissionGroupAdmin)

# Redéfinir l'approche de personnalisation pour éviter de remplacer admin.site
def setup_admin_site(admin_site):
    """Configure le site d'administration sans remplacer l'instance admin.site."""
    # Personnalisation du site admin
    admin_site.site_header = "CybeRH Administration"
    admin_site.site_title = "CybeRH Admin"
    admin_site.index_title = "Tableau de bord d'administration"
    
    # Méthode statique pour l'affichage du tableau de bord
    @staticmethod
    def dashboard_view(request):
        if not request.user.is_staff:
            return redirect('admin:login')
            
        # Statistiques pour le tableau de bord admin
        stats = {
            'users_count': User.objects.count(),
            'leaves_count': LeaveRequest.objects.count(),
            'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
            'expenses_count': ExpenseReport.objects.filter(status='pending').count(),
            'km_expenses_count': KilometricExpense.objects.filter(status='pending').count(),
        }
        
        # Groupes par nombre d'utilisateurs
        groups_stats = Group.objects.annotate(users_count=Count('user')).order_by('-users_count')
        
        context = {
            'title': 'Tableau de bord',
            'stats': stats,
            'groups_stats': groups_stats,
            'has_permission': True,  # Important pour que les templates admin fonctionnent
            'site_header': admin_site.site_header,
            'site_title': admin_site.site_title,
        }
        
        return render(request, 'admin/dashboard.html', context)
    
    # Assigner la méthode statique
    setup_admin_site.dashboard_view = dashboard_view
    
    return admin_site

# Créer le template admin/dashboard.html dans le dossier templates de votre projet
