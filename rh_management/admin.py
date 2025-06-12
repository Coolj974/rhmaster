from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    LeaveRequest, ExpenseReport, KilometricExpense, 
    Notification, Profile, Department, LeaveBalance, LeaveAdjustment
)

# Unregister the original User admin
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """Administration personnalisée pour les utilisateurs"""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')
    
    # Autoriser le filtrage par groups__name en surchargeant la validation
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('groups')
    
    def get_groups(self, obj):
        """Afficher les groupes de l'utilisateur"""
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = 'Groupes'
    
    def lookup_allowed(self, lookup, value):
        """Autoriser les lookups spécifiques pour les groupes"""
        if lookup == 'groups__name':
            return True
        return super().lookup_allowed(lookup, value)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Administration pour les profils utilisateur"""
    list_display = ('user', 'department', 'position', 'phone_number', 'hire_date')
    list_filter = ('department', 'hire_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position')
    raw_id_fields = ('user', 'manager')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Administration pour les départements"""
    list_display = ('name', 'manager', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    raw_id_fields = ('manager',)

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    """Administration pour les demandes de congé"""
    list_display = ('user', 'start_date', 'end_date', 'leave_type', 'status', 'created_at')
    list_filter = ('status', 'leave_type', 'created_at', 'start_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'description')
    date_hierarchy = 'start_date'
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ExpenseReport)
class ExpenseReportAdmin(admin.ModelAdmin):
    """Administration pour les notes de frais"""
    list_display = ('user', 'date', 'description', 'amount', 'expense_type', 'status', 'created_at')
    list_filter = ('status', 'expense_type', 'created_at', 'date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'description')
    date_hierarchy = 'date'
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(KilometricExpense)
class KilometricExpenseAdmin(admin.ModelAdmin):
    """Administration pour les frais kilométriques"""
    list_display = ('user', 'date', 'departure', 'arrival', 'distance', 'amount', 'status', 'created_at')
    list_filter = ('status', 'vehicle_type', 'fiscal_power', 'created_at', 'date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'departure', 'arrival', 'description')
    date_hierarchy = 'date'
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    """Administration pour les soldes de congés"""
    list_display = ('user', 'acquired', 'taken', 'available', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(LeaveAdjustment)
class LeaveAdjustmentAdmin(admin.ModelAdmin):
    """Administration pour les ajustements de solde"""
    list_display = ('user', 'adjustment', 'reason', 'adjusted_by', 'created_at')
    list_filter = ('created_at', 'adjustment')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'reason')
    raw_id_fields = ('user', 'adjusted_by')
    readonly_fields = ('created_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administration pour les notifications"""
    list_display = ('user', 'title', 'notification_type', 'read', 'created_at')
    list_filter = ('read', 'notification_type', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Action pour marquer les notifications comme lues"""
        queryset.update(read=True)
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        """Action pour marquer les notifications comme non lues"""
        queryset.update(read=False)
    mark_as_unread.short_description = "Marquer comme non lu"

# Personnalisation du site admin
admin.site.site_header = "Administration RH CYBER"
admin.site.site_title = "RH CYBER Admin"
admin.site.index_title = "Panneau d'administration"
