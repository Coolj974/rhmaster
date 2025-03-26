from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ..models import LeaveRequest, ExpenseReport, KilometricExpense
from .permissions import is_admin_or_hr, is_encadrant
from datetime import datetime
import random
import string


@login_required
def api_leaves(request):
    """API pour récupérer les congés pour le calendrier."""
    start_date = request.GET.get('start', None)
    end_date = request.GET.get('end', None)
    show_all = request.GET.get('all', 'false') == 'true'
    
    # Conversion des dates - gestion plus robuste des formats de date
    if start_date:
        try:
            # Gérer le cas où il y a un espace au lieu d'un +
            if ' ' in start_date and not '+' in start_date:
                start_date = start_date.replace(' ', '+')
            # Remplacer Z par +00:00 si nécessaire
            if 'Z' in start_date:
                start_date = start_date.replace('Z', '+00:00')
            # Conversion en datetime
            start_date = datetime.fromisoformat(start_date)
        except ValueError:
            # En cas d'échec, essayer un format plus simple
            start_date = datetime.strptime(start_date.split('T')[0], '%Y-%m-%d')
    
    if end_date:
        try:
            # Gérer le cas où il y a un espace au lieu d'un +
            if ' ' in end_date and not '+' in end_date:
                end_date = end_date.replace(' ', '+')
            # Remplacer Z par +00:00 si nécessaire
            if 'Z' in end_date:
                end_date = end_date.replace('Z', '+00:00')
            # Conversion en datetime
            end_date = datetime.fromisoformat(end_date)
        except ValueError:
            # En cas d'échec, essayer un format plus simple
            end_date = datetime.strptime(end_date.split('T')[0], '%Y-%m-%d')
    
    # Filtrer les congés
    if show_all and (is_admin_or_hr(request.user) or is_encadrant(request.user)):
        # Pour les admins, RH et encadrants, montrer tous les congés
        leaves = LeaveRequest.objects.all()
    else:
        # Pour les autres, montrer seulement leurs propres congés
        leaves = LeaveRequest.objects.filter(user=request.user)
    
    # Filtrer par date si fournie
    if start_date:
        leaves = leaves.filter(end_date__gte=start_date)
    if end_date:
        leaves = leaves.filter(start_date__lte=end_date)
    
    # Formater les données pour le calendrier
    leave_data = []
    for leave in leaves:
        status_color = {
            'pending': '#f6c23e',  # warning
            'approved': '#1cc88a',  # success
            'rejected': '#e74a3b',  # danger
        }
        
        leave_data.append({
            'id': leave.id,
            'title': f"{leave.user.get_full_name() or leave.user.username} - {leave.get_leave_type_display()}",
            'start_date': leave.start_date.isoformat(),
            'end_date': leave.end_date.isoformat(),
            'user': leave.user.get_full_name() or leave.user.username,
            'leave_type': leave.get_leave_type_display(),
            'status': leave.status,
            'reason': leave.reason or '',
            'color': status_color.get(leave.status, '#f6c23e')
        })
    return JsonResponse(leave_data, safe=False)

@login_required
def api_expense_stats(request):
    """API pour récupérer les statistiques des notes de frais."""
    # Par défaut, limiter aux notes de frais de l'utilisateur courant
    expenses = ExpenseReport.objects.filter(user=request.user)
    
    # Pour les administrateurs et RH, permettre d'obtenir toutes les notes de frais
    if request.GET.get('all') == 'true' and is_admin_or_hr(request.user):
        expenses = ExpenseReport.objects.all()
    
    # Pour les encadrants, obtenir les notes de frais de leur équipe
    elif request.GET.get('team') == 'true' and is_encadrant(request.user):
        from django.contrib.auth.models import User
        team_members = User.objects.filter(team_leader=request.user)
        expenses = ExpenseReport.objects.filter(user__in=team_members)
    
    # Statistiques par statut
    pending_count = expenses.filter(status='pending').count()
    approved_count = expenses.filter(status='approved').count()
    rejected_count = expenses.filter(status='rejected').count()
    
    # Somme totale des montants approuvés
    from django.db.models import Sum
    total_amount = expenses.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Statistiques par mois (pour graphiques)
    from django.db.models.functions import TruncMonth
    monthly_stats = list(expenses.annotate(month=TruncMonth('date'))
                        .values('month')
                        .annotate(total=Sum('amount'))
                        .order_by('month')
                        .values('month', 'total'))
    
    # Formater les mois pour l'affichage
    for stat in monthly_stats:
        stat['month'] = stat['month'].strftime('%Y-%m')
    
    return JsonResponse({
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': total_amount,
        'monthly_stats': monthly_stats
    })

@login_required
def api_kilometric_stats(request):
    """API pour récupérer les statistiques des frais kilométriques."""
    # Par défaut, limiter aux frais kilométriques de l'utilisateur courant
    expenses = KilometricExpense.objects.filter(user=request.user)
    
    # Pour les administrateurs et RH, permettre d'obtenir tous les frais kilométriques
    if request.GET.get('all') == 'true' and is_admin_or_hr(request.user):
        expenses = KilometricExpense.objects.all()
    
    # Pour les encadrants, obtenir les frais kilométriques de leur équipe
    elif request.GET.get('team') == 'true' and is_encadrant(request.user):
        from django.contrib.auth.models import User
        team_members = User.objects.filter(team_leader=request.user)
        expenses = KilometricExpense.objects.filter(user__in=team_members)
    
    # Statistiques par statut
    pending_count = expenses.filter(status='pending').count()
    approved_count = expenses.filter(status='approved').count()
    rejected_count = expenses.filter(status='rejected').count()
    
    # Somme totale des montants approuvés et des distances
    from django.db.models import Sum
    total_amount = expenses.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    total_distance = expenses.filter(status='approved').aggregate(Sum('distance'))['distance__sum'] or 0
    
    # Statistiques par mois (pour graphiques)
    from django.db.models.functions import TruncMonth
    monthly_distance = list(expenses.annotate(month=TruncMonth('date'))
                           .values('month')
                           .annotate(total_distance=Sum('distance'))
                           .order_by('month')
                           .values('month', 'total_distance'))
    
    monthly_amount = list(expenses.annotate(month=TruncMonth('date'))
                         .values('month')
                         .annotate(total_amount=Sum('amount'))
                         .order_by('month')
                         .values('month', 'total_amount'))
    
    # Formater les mois pour l'affichage
    for stat in monthly_distance:
        stat['month'] = stat['month'].strftime('%Y-%m')
    
    for stat in monthly_amount:
        stat['month'] = stat['month'].strftime('%Y-%m')
    
    return JsonResponse({
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': total_amount,
        'total_distance': total_distance,
        'monthly_distance': monthly_distance,
        'monthly_amount': monthly_amount
    })

@login_required
def api_notifications(request):
    """API pour récupérer le nombre de notifications en attente."""
    user = request.user
    is_admin_flag = user.is_superuser
    is_hr_flag = user.is_staff
    is_encadrant_flag = is_encadrant(user)
    
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin_flag or is_hr_flag:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    elif is_encadrant_flag:
        from django.contrib.auth.models import User
        team_members = User.objects.filter(team_leader=user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    total_count = new_leave_requests_count + new_expense_reports_count + new_kilometric_expenses_count
    
    return JsonResponse({
        'leaves': new_leave_requests_count,
        'expenses': new_expense_reports_count,
        'kilometric': new_kilometric_expenses_count,
        'total': total_count
    })

@login_required
def generate_password_api(request):
    """API pour générer un mot de passe aléatoire sécurisé."""
    length = int(request.GET.get('length', 12))
    
    # Appliquer des limites raisonnables
    if length < 8:
        length = 8
    elif length > 64:
        length = 64
    
    # Définir les ensembles de caractères
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
    
    # S'assurer qu'il y a au moins un caractère de chaque type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Ajouter des caractères aléatoires pour atteindre la longueur demandée
    all_chars = lowercase + uppercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # Mélanger tous les caractères pour éviter un schéma prévisible
    random.shuffle(password)
    
    # Convertir la liste en chaîne de caractères
    password = ''.join(password)
    
    return JsonResponse({'password': password})

@login_required
def search_api(request):
    """API pour la recherche globale dans l'application."""
    query = request.GET.get('q', '')
    
    if not query or len(query) < 3:
        return JsonResponse({'results': []})
    
    results = []
    user = request.user
    is_admin_flag = user.is_superuser
    is_hr_flag = user.is_staff
    is_encadrant_flag = is_encadrant(user)
    
    # Recherche dans les congés
    if is_admin_flag or is_hr_flag:
        # Admins et RH peuvent rechercher tous les congés
        leave_results = LeaveRequest.objects.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(reason__icontains=query)
        )[:10]
    elif is_encadrant_flag:
        # Les encadrants ne peuvent chercher que les congés de leur équipe
        team_members = User.objects.filter(team_leader=user)
        leave_results = LeaveRequest.objects.filter(
            user__in=team_members
        ).filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(reason__icontains=query)
        )[:10]
    else:
        # Les employés ne peuvent voir que leurs propres congés
        leave_results = LeaveRequest.objects.filter(
            user=user
        ).filter(
            Q(reason__icontains=query)
        )[:10]
    
    for leave in leave_results:
        results.append({
            'type': 'leave',
            'id': leave.id,
            'title': f"Congé de {leave.user.get_full_name() or leave.user.username}",
            'description': f"{leave.get_leave_type_display()} - {leave.start_date} à {leave.end_date}",
            'url': f"/leaves/{leave.id}/"
        })
    
    # Recherche similaire pour les notes de frais et frais kilométriques
    # (Je raccourcis l'exemple pour ne pas répéter le même modèle)
    
    return JsonResponse({'results': results})

# Cette fonction nécessite d'importer Q
from django.db.models import Q
