from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from ..models import LeaveRequest, ExpenseReport, KilometricExpense, UserProfile, PasswordManager, LeaveBalance, Notification
from .permissions import is_rh, is_encadrant, is_stp, is_admin_or_hr

@login_required
def dashboard_view(request):
    """
    Vue principale du tableau de bord
    """
    # Vérifier les permissions de l'utilisateur
    is_admin = request.user.is_superuser
    is_hr = request.user.groups.filter(name='RH').exists() or request.user.is_staff
    is_manager = request.user.groups.filter(name='Manager').exists()
    
    # Récupérer les notifications non lues
    unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()
    
    # Initialiser les contextes selon le profil
    context = {
        'is_admin': is_admin,
        'is_hr': is_hr,
        'is_manager': is_manager,
        'unread_notifications': unread_notifications_count,
    }
    
    # Pour les RH et les admins: voir toutes les demandes en attente
    if is_admin or is_hr:
        # Demandes de congés en attente
        pending_leaves = LeaveRequest.objects.filter(
            status='pending'
        ).select_related('user').order_by('-created_at')
        
        # Frais en attente
        pending_expenses = ExpenseReport.objects.filter(
            status='pending'
        ).select_related('user').order_by('-created_at')
        
        # Frais kilométriques en attente
        pending_kilometrics = KilometricExpense.objects.filter(
            status='pending'
        ).select_related('user').order_by('-created_at')
        
        context.update({
            'pending_leaves': pending_leaves,
            'pending_expenses': pending_expenses,
            'pending_kilometrics': pending_kilometrics,
            'pending_leaves_count': pending_leaves.count(),  # Ajoutez des compteurs explicites
            'pending_expenses_count': pending_expenses.count(),
            'pending_kilometrics_count': pending_kilometrics.count()
        })
    
    # Pour les managers: voir les demandes de leur équipe
    elif is_manager:
        # Ajoutez ici la logique pour les managers
        pass
    
    # Pour tous: voir mes demandes récentes
    my_recent_leaves = LeaveRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    my_recent_expenses = ExpenseReport.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    my_recent_kilometrics = KilometricExpense.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context.update({
        'my_recent_leaves': my_recent_leaves,
        'my_recent_expenses': my_recent_expenses,
        'my_recent_kilometrics': my_recent_kilometrics
    })
    
    return render(request, 'rh_management/dashboard.html', context)

@login_required
def some_view(request):
    # Vérification des rôles standards
    if request.user.is_staff:
        # Accès fonctionnalités RH
        pass
        
    if request.user.is_superuser:
        # Accès administrateur
        pass
    
    # Vérification des rôles personnalisés
    try:
        profile = request.user.profile
        if profile.is_supervisor:
            # Accès fonctionnalités superviseur
            pass
        
        if profile.is_stp:
            # Accès fonctionnalités STP
            pass
            
        if profile.is_employee:
            # Accès fonctionnalités employé
            pass
    except UserProfile.DoesNotExist:
        # Gérer le cas où le profil n'existe pas encore
        pass

@login_required
@login_required
@user_passes_test(is_admin_or_hr)
def dashboard_filtered(request):
    # Filtrage et tri des demandes de congés
    leave_requests = LeaveRequest.objects.all()
    status_leave = request.GET.get('status_leave')
    sort_leave = request.GET.get('sort_leave')

    if status_leave:
        leave_requests = leave_requests.filter(status=status_leave)

    if sort_leave == 'date_desc':
        leave_requests = leave_requests.order_by('-start_date')
    elif sort_leave == 'date_asc':
        leave_requests = leave_requests.order_by('start_date')

    # Filtrage et tri des notes de frais
    expense_reports = ExpenseReport.objects.all()
    status_expense = request.GET.get('status_expense')
    sort_expense = request.GET.get('sort_expense')

    if status_expense:
        expense_reports = expense_reports.filter(status=status_expense)

    if sort_expense == 'date_desc':
        expense_reports = expense_reports.order_by('-date')
    elif sort_expense == 'date_asc':
        expense_reports = expense_reports.order_by('date')

    # Filtrage et tri des frais kilométriques
    kilometric_expenses = KilometricExpense.objects.all()
    status_kilometric_expense = request.GET.get('status_kilometric_expense')
    sort_kilometric_expense = request.GET.get('sort_kilometric_expense')

    if status_kilometric_expense:
        kilometric_expenses = kilometric_expenses.filter(status=status_kilometric_expense)

    if sort_kilometric_expense == 'date_desc':
        kilometric_expenses = kilometric_expenses.order_by('-date')
    elif sort_kilometric_expense == 'date_asc':
        kilometric_expenses = kilometric_expenses.order_by('date')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'leave_requests': render_to_string('rh_management/partials/leave_requests.html', {'leave_requests': leave_requests, 'is_admin': request.user.is_superuser}),
            'expense_reports': render_to_string('rh_management/partials/expense_reports.html', {'expense_reports': expense_reports, 'is_admin': request.user.is_superuser}),
            'kilometric_expense_reports': render_to_string('rh_management/partials/kilometric_expense_reports.html', {'kilometric_expenses': kilometric_expenses, 'is_admin': request.user.is_superuser}),
        })

    return render(request, 'rh_management/dashboard.html', {
        'leave_requests': leave_requests,
        'expense_reports': expense_reports,
        'kilometric_expenses': kilometric_expenses,
        'is_hr': request.user.groups.filter(name='HR').exists(),
        'is_admin': request.user.is_superuser,
    })

@login_required
def dashboard_stats_api(request):
    """API endpoint pour les statistiques du tableau de bord."""
    try:
        user = request.user
        
        # Récupérer le solde des congés
        leave_balance = LeaveBalance.objects.get_or_create(
            user=user,
            defaults={'acquired': 25.0, 'taken': 0.0}
        )[0]
        
        stats = {
            'leave_count': leave_balance.available,
            'expense_count': ExpenseReport.objects.filter(user=user).count(),
            'km_expense_count': KilometricExpense.objects.filter(user=user).count(),
            'password_count': PasswordManager.objects.filter(user=user).count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def dashboard(request):
    """
    Vue principale du tableau de bord
    """
    # Ajoutons ici une fonction index qui redirige vers dashboard
    return render(request, 'rh_management/dashboard.html')

# Fonction index pour rétrocompatibilité
def index(request):
    """
    Vue index qui redirige vers le tableau de bord
    """
    return dashboard(request)
