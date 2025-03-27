from django.shortcuts import render, redirect
from django.db.models import Count, Sum
from django.contrib.auth.models import User, Group
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin
from .models import LeaveRequest, ExpenseReport, KilometricExpense

@staff_member_required
def admin_dashboard(request):
    """
    Vue pour afficher le tableau de bord administratif personnalisé
    """
    # Statistiques pour le tableau de bord admin
    leaves_count = LeaveRequest.objects.count()
    pending_leaves = LeaveRequest.objects.filter(status='pending').count()
    
    # Calculer le pourcentage de congés en attente
    if leaves_count > 0:
        pending_percentage = (pending_leaves / leaves_count) * 100
    else:
        pending_percentage = 0
    
    stats = {
        'users_count': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'leaves_count': leaves_count,
        'pending_leaves': pending_leaves,
        'pending_percentage': pending_percentage,
        'approved_leaves': LeaveRequest.objects.filter(status='approved').count(),
        'expenses_count': ExpenseReport.objects.filter(status='pending').count(),
        'approved_expenses': ExpenseReport.objects.filter(status='approved').count(),
        'km_expenses_count': KilometricExpense.objects.filter(status='pending').count(),
    }
    
    # Groupes par nombre d'utilisateurs avec IDs
    groups_stats = Group.objects.annotate(users_count=Count('user')).order_by('-users_count').values('id', 'name', 'users_count')
    
    context = {
        'title': 'Tableau de bord CybeRH',
        'stats': stats,
        'groups_stats': groups_stats,
        'has_permission': True,  # Important pour que les templates admin fonctionnent
        'site_header': admin.site.site_header,
        'site_title': admin.site.site_title,
    }
    
    return render(request, 'admin/dashboard.html', context)
