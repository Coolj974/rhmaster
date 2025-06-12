from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from ..models import LeaveRequest, ExpenseReport, KilometricExpense, Notification
from datetime import datetime, timedelta

@login_required
def dashboard(request):
    """
    Vue principale du tableau de bord avec synthèses mises à jour
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
        # Demandes de congés en attente avec les bonnes requêtes
        pending_leaves = LeaveRequest.objects.filter(status='pending')
        pending_leaves_count = pending_leaves.count()
        
        # Notes de frais en attente
        pending_expenses = ExpenseReport.objects.filter(status='pending')
        pending_expenses_count = pending_expenses.count()
        
        # Frais kilométriques en attente
        pending_kilometrics = KilometricExpense.objects.filter(status='pending')
        pending_kilometrics_count = pending_kilometrics.count()
        
        # Statistiques globales pour les RH/Admins
        leaves_stats = {
            'total': LeaveRequest.objects.count(),
            'pending': pending_leaves_count,
            'approved': LeaveRequest.objects.filter(status='approved').count(),
            'rejected': LeaveRequest.objects.filter(status='rejected').count(),
        }
        
        expenses_stats = {
            'total': ExpenseReport.objects.count(),
            'pending': pending_expenses_count,
            'approved': ExpenseReport.objects.filter(status='approved').count(),
            'rejected': ExpenseReport.objects.filter(status='rejected').count(),
            'total_amount': ExpenseReport.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending_amount': ExpenseReport.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        
        kilometrics_stats = {
            'total': KilometricExpense.objects.count(),
            'pending': pending_kilometrics_count,
            'approved': KilometricExpense.objects.filter(status='approved').count(),
            'rejected': KilometricExpense.objects.filter(status='rejected').count(),
            'total_distance': KilometricExpense.objects.aggregate(Sum('distance'))['distance__sum'] or 0,
            'total_amount': KilometricExpense.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        
        context.update({
            'pending_leaves': pending_leaves.order_by('-created_at')[:5],  # Les 5 plus récents
            'pending_expenses': pending_expenses.order_by('-created_at')[:5],
            'pending_kilometrics': pending_kilometrics.order_by('-created_at')[:5],
            'pending_leaves_count': pending_leaves_count,
            'pending_expenses_count': pending_expenses_count,
            'pending_kilometrics_count': pending_kilometrics_count,
            'leaves_stats': leaves_stats,
            'expenses_stats': expenses_stats,
            'kilometrics_stats': kilometrics_stats,
        })
    
    # Pour les managers: voir les demandes de leur équipe
    elif is_manager:
        # Récupérer les membres de l'équipe
        team_members = User.objects.filter(manager=request.user)  # Ajustez selon votre modèle
        
        team_pending_leaves = LeaveRequest.objects.filter(user__in=team_members, status='pending')
        team_pending_expenses = ExpenseReport.objects.filter(user__in=team_members, status='pending')
        team_pending_kilometrics = KilometricExpense.objects.filter(user__in=team_members, status='pending')
        
        context.update({
            'team_pending_leaves': team_pending_leaves,
            'team_pending_expenses': team_pending_expenses,
            'team_pending_kilometrics': team_pending_kilometrics,
            'team_pending_leaves_count': team_pending_leaves.count(),
            'team_pending_expenses_count': team_pending_expenses.count(),
            'team_pending_kilometrics_count': team_pending_kilometrics.count(),
        })
    
    # Pour tous: voir mes demandes récentes et mes statistiques personnelles
    my_recent_leaves = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')[:5]
    my_recent_expenses = ExpenseReport.objects.filter(user=request.user).order_by('-created_at')[:5]
    my_recent_kilometrics = KilometricExpense.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Statistiques personnelles
    my_stats = {
        'leaves': {
            'total': LeaveRequest.objects.filter(user=request.user).count(),
            'pending': LeaveRequest.objects.filter(user=request.user, status='pending').count(),
            'approved': LeaveRequest.objects.filter(user=request.user, status='approved').count(),
        },
        'expenses': {
            'total': ExpenseReport.objects.filter(user=request.user).count(),
            'pending': ExpenseReport.objects.filter(user=request.user, status='pending').count(),
            'total_amount': ExpenseReport.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0,
        },
        'kilometrics': {
            'total': KilometricExpense.objects.filter(user=request.user).count(),
            'pending': KilometricExpense.objects.filter(user=request.user, status='pending').count(),
            'total_distance': KilometricExpense.objects.filter(user=request.user).aggregate(Sum('distance'))['distance__sum'] or 0,
        }
    }
    
    context.update({
        'my_recent_leaves': my_recent_leaves,
        'my_recent_expenses': my_recent_expenses,
        'my_recent_kilometrics': my_recent_kilometrics,
        'my_stats': my_stats,
    })
    
    return render(request, 'rh_management/dashboard.html', context)

# Fonction alias pour dashboard_view (utilisée dans les URLs)
@login_required
def dashboard_view(request):
    """
    Vue alias pour dashboard - maintient la compatibilité avec les URLs existantes
    """
    return dashboard(request)

# Fonction alias pour rétrocompatibilité
def index(request):
    """
    Vue index qui redirige vers le tableau de bord
    """
    return dashboard(request)

@login_required
def some_view(request):
    """
    Vue générique - fonction placeholder pour maintenir la compatibilité
    """
    return dashboard(request)

@login_required
def dashboard_filtered(request):
    """
    Vue pour dashboard avec filtres - version filtrée du tableau de bord
    """
    # Récupérer les paramètres de filtre depuis la requête GET
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    type_filter = request.GET.get('type', '')
    
    # Commencer avec le contexte de base du dashboard principal
    context = dashboard(request).context_data if hasattr(dashboard(request), 'context_data') else {}
    
    # Appliquer les filtres si spécifiés
    if status_filter or date_filter or type_filter:
        # Filtrer les demandes de congés
        if 'pending_leaves' in context:
            leaves = LeaveRequest.objects.filter(status='pending')
            if status_filter:
                leaves = leaves.filter(status=status_filter)
            if date_filter:
                leaves = leaves.filter(created_at__date=date_filter)
            context['pending_leaves'] = leaves.order_by('-created_at')[:10]
        
        # Filtrer les notes de frais
        if 'pending_expenses' in context:
            expenses = ExpenseReport.objects.filter(status='pending')
            if status_filter:
                expenses = expenses.filter(status=status_filter)
            if date_filter:
                expenses = expenses.filter(created_at__date=date_filter)
            context['pending_expenses'] = expenses.order_by('-created_at')[:10]
        
        # Filtrer les frais kilométriques
        if 'pending_kilometrics' in context:
            kilometrics = KilometricExpense.objects.filter(status='pending')
            if status_filter:
                kilometrics = kilometrics.filter(status=status_filter)
            if date_filter:
                kilometrics = kilometrics.filter(created_at__date=date_filter)
            context['pending_kilometrics'] = kilometrics.order_by('-created_at')[:10]
    
    # Ajouter les paramètres de filtre au contexte
    context.update({
        'applied_filters': {
            'status': status_filter,
            'date': date_filter,
            'type': type_filter
        }
    })
    
    return render(request, 'rh_management/dashboard.html', context)

@login_required
def dashboard_stats_api(request):
    """
    API pour récupérer les statistiques du dashboard en temps réel (format JSON)
    """
    from django.http import JsonResponse
    
    # Vérifier les permissions de l'utilisateur
    is_admin = request.user.is_superuser
    is_hr = request.user.groups.filter(name='RH').exists() or request.user.is_staff
    
    stats = {}
    
    if is_admin or is_hr:
        # Statistiques globales pour les RH/Admins
        stats = {
            'leaves': {
                'total': LeaveRequest.objects.count(),
                'pending': LeaveRequest.objects.filter(status='pending').count(),
                'approved': LeaveRequest.objects.filter(status='approved').count(),
                'rejected': LeaveRequest.objects.filter(status='rejected').count(),
            },
            'expenses': {
                'total': ExpenseReport.objects.count(),
                'pending': ExpenseReport.objects.filter(status='pending').count(),
                'approved': ExpenseReport.objects.filter(status='approved').count(),
                'rejected': ExpenseReport.objects.filter(status='rejected').count(),
                'total_amount': float(ExpenseReport.objects.aggregate(Sum('amount'))['amount__sum'] or 0),
                'pending_amount': float(ExpenseReport.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0),
            },
            'kilometrics': {
                'total': KilometricExpense.objects.count(),
                'pending': KilometricExpense.objects.filter(status='pending').count(),
                'approved': KilometricExpense.objects.filter(status='approved').count(),
                'rejected': KilometricExpense.objects.filter(status='rejected').count(),
                'total_distance': float(KilometricExpense.objects.aggregate(Sum('distance'))['distance__sum'] or 0),
                'total_amount': float(KilometricExpense.objects.aggregate(Sum('amount'))['amount__sum'] or 0),
            },
            'notifications': Notification.objects.filter(user=request.user, read=False).count()
        }
    else:
        # Statistiques personnelles pour les employés
        stats = {
            'my_leaves': {
                'total': LeaveRequest.objects.filter(user=request.user).count(),
                'pending': LeaveRequest.objects.filter(user=request.user, status='pending').count(),
                'approved': LeaveRequest.objects.filter(user=request.user, status='approved').count(),
            },
            'my_expenses': {
                'total': ExpenseReport.objects.filter(user=request.user).count(),
                'pending': ExpenseReport.objects.filter(user=request.user, status='pending').count(),
                'total_amount': float(ExpenseReport.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0),
            },
            'my_kilometrics': {
                'total': KilometricExpense.objects.filter(user=request.user).count(),
                'pending': KilometricExpense.objects.filter(user=request.user, status='pending').count(),
                'total_distance': float(KilometricExpense.objects.filter(user=request.user).aggregate(Sum('distance'))['distance__sum'] or 0),
            },
            'notifications': Notification.objects.filter(user=request.user, read=False).count()
        }
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'user_type': 'admin_hr' if (is_admin or is_hr) else 'employee'
    })
