from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Sum, Q
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import Group, User
from ..models import LeaveRequest, LeaveBalance, ExpenseReport, KilometricExpense, Notification, Leave, LeaveAdjustment, Department
from ..forms import LeaveRequestForm
from .permissions import is_admin_or_hr, is_admin_hr_or_encadrant, can_approve_leaves, user_is_hr_or_admin
from datetime import datetime, timedelta
import csv
from django.core.paginator import Paginator

def calculate_working_days(start_date, end_date, half_day=False):
    """Calcule le nombre de jours ouvrés entre deux dates."""
    if half_day:
        return 0.5
    
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # 0-4 pour lundi à vendredi
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days

@login_required
def leave_request_view(request):
    """Vue pour soumettre une demande de congé."""
    if request.method == "POST":
        # Récupérer les données du formulaire
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        reason = request.POST.get('reason')
        
        # Validation des données
        if not all([start_date, end_date, leave_type]):
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('leave_request')
        
        try:
            # Conversion des dates
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Vérifier que la date de fin est après la date de début
            if end_date < start_date:
                messages.error(request, "La date de fin doit être après la date de début.")
                return redirect('leave_request')
                
            # Créer la demande de congé
            leave_request = LeaveRequest(
                user=request.user,
                start_date=start_date,
                end_date=end_date,
                leave_type=leave_type,
                reason=reason,
                status='pending'  # Par défaut, la demande est en attente
            )
            
            # Calculer le nombre de jours ouvrés
            working_days = calculate_working_days(start_date, end_date)
            leave_request.days_requested = working_days
            
            # Enregistrer la demande
            leave_request.save()
            
            # Trouver tous les RH et managers
            from django.contrib.auth.models import User, Group
            rh_group = Group.objects.filter(name='RH').first()
            admin_users = User.objects.filter(is_superuser=True)
            rh_users = User.objects.filter(groups=rh_group) if rh_group else User.objects.none()
            
            # Si l'utilisateur a un superviseur, notifier aussi le superviseur
            supervisor = None
            try:
                if request.user.userprofile.supervisor:
                    supervisor = request.user.userprofile.supervisor
            except:
                pass
                
            # Créer des notifications pour les RH, les admins et le superviseur
            from ..models import Notification
            for user in set(list(admin_users) + list(rh_users) + ([supervisor] if supervisor else [])):
                if user:  # Vérifier que l'utilisateur existe
                    Notification.create_leave_notification(
                        user,
                        leave_request,
                        f"Nouvelle demande de congé de {leave_request.user.get_full_name() or leave_request.user.username} du {leave_request.start_date} au {leave_request.end_date}.",
                        is_manager=True
                    )
            
            messages.success(request, "Votre demande de congé a été soumise avec succès.")
            return redirect('my_leaves')  # Rediriger vers la liste des congés
        except ValueError as e:
            messages.error(request, f"Erreur lors de la soumission de votre demande: {str(e)}")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier si l'utilisateur a un solde de congés
    leave_balance, created = LeaveBalance.objects.get_or_create(
        user=request.user,
        defaults={'acquired': 25.0, 'taken': 0.0}
    )
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.user = request.user
            
            # Gérer l'option demi-journée
            if request.POST.get('half_day') == 'on':
                leave_request.half_day = True
                leave_request.half_day_period = request.POST.get('half_day_period', 'morning')
                # Assurez-vous que les dates de début et de fin sont identiques
                leave_request.end_date = leave_request.start_date
            
            leave_request.save()
            
            # Traiter les notifications
            notify_manager = request.POST.get('notify_manager') == 'on'
            notify_hr = request.POST.get('notify_hr') == 'on'
            
            recipients = []
            if notify_manager:
                recipients.extend(['alain@example.com', 'bastien@example.com'])
            if notify_hr:
                recipients.extend(['sarah@example.com', 'coordinateur@example.com'])
            
            if recipients:
                subject = f"Nouvelle demande de congé de {request.user.get_full_name() or request.user.username}"
                message = f"""
                Une nouvelle demande de congé a été soumise:
                
                Employé: {request.user.get_full_name() or request.user.username}
                Type de congé: {leave_request.get_leave_type_display()}
                Du: {leave_request.start_date}
                Au: {leave_request.end_date}
                {f"Demi-journée: {leave_request.get_half_day_period_display()}" if leave_request.half_day else ""}
                Raison: {leave_request.reason or "Non spécifiée"}
                
                Veuillez vous connecter à l'application pour examiner cette demande.
                """
                
                send_mail(
                    subject,
                    message,
                    'noreply@rhcyber.com',
                    recipients
                )
            
            messages.success(request, "Votre demande de congé a été soumise avec succès.")
            return redirect('dashboard')
    else:
        form = LeaveRequestForm()
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
        # Seuls les admins, RH et encadrants peuvent voir les compteurs
        if is_admin or is_rh:
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif is_encadrant:
            # Pour les encadrants, montrer uniquement les demandes de leur équipe
            team_members = User.objects.filter(team_leader=request.user)
            new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'form': form,
        'leave_balance': leave_balance,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/leave_request.html', context)

@login_required
def leave_request(request):
    """
    Vue pour soumettre une demande de congé
    """
    # Récupérer le solde de congés de l'utilisateur
    leave_balance = LeaveBalance.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        # Traiter le formulaire de demande
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        reason = request.POST.get('reason', '')
        days_requested = float(request.POST.get('days_requested', 0))
        half_day = request.POST.get('half_day') == 'on'
        half_day_period = request.POST.get('half_day_period') if half_day else None
        
        # Vérifier les dates
        if not start_date or not end_date:
            messages.error(request, "Veuillez sélectionner les dates de début et de fin.")
            return redirect('leave_request')
        
        # Vérifier le nombre de jours
        if days_requested <= 0:
            messages.error(request, "La période sélectionnée ne contient aucun jour ouvrable valide.")
            return redirect('leave_request')
        
        # Créer la demande de congé
        leave = Leave(
            user=request.user,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            days_requested=days_requested,
            reason=reason,
            status='pending',
            half_day=half_day,
            half_day_period=half_day_period
        )
        
        # Gestion des pièces jointes
        if 'attachment' in request.FILES:
            attachment = request.FILES['attachment']
            # Vérifier la taille et le type du fichier
            if attachment.size > 5 * 1024 * 1024:  # 5MB
                messages.error(request, "Le fichier est trop volumineux. La limite est de 5Mo.")
                return redirect('leave_request')
                
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if attachment.content_type not in allowed_types:
                messages.error(request, "Format de fichier non accepté. Veuillez soumettre un fichier PDF, PNG ou JPG.")
                return redirect('leave_request')
                
            leave.attachment = attachment
        
        leave.save()
        
        # Notifier les RH
        hr_users = User.objects.filter(groups__name='RH')
        for hr_user in hr_users:
            Notification.objects.create(
                user=hr_user,
                title="Nouvelle demande de congé",
                message=f"{request.user.get_full_name()} a soumis une demande de congé pour {days_requested} jour(s).",
                url="/manage-leaves/",
                icon="fa-calendar-check"
            )
        
        messages.success(request, "Votre demande de congé a été soumise avec succès et est en attente de validation.")
        return redirect('my_leaves')
    
    return render(request, 'rh_management/leave_request.html', {
        'leave_balance': leave_balance
    })

@login_required
@user_passes_test(is_admin_or_hr)
def manage_leave_balances(request):
    """
    Vue pour gérer les soldes de congés des employés
    """
    # Récupérer les filtres de la requête
    name = request.GET.get('name', '')
    department_id = request.GET.get('department', '')
    balance_status = request.GET.get('balance_status', '')
    
    # Construire la requête de base
    queryset = LeaveBalance.objects.select_related('user', 'user__profile').all()
    
    # Appliquer les filtres
    if name:
        queryset = queryset.filter(
            Q(user__first_name__icontains=name) | 
            Q(user__last_name__icontains=name) |
            Q(user__username__icontains=name)
        )
    
    if department_id and department_id.isdigit():
        queryset = queryset.filter(user__profile__department_id=department_id)
    
    if balance_status:
        if balance_status == 'low':
            queryset = queryset.filter(available__lt=5, available__gt=0)
        elif balance_status == 'medium':
            queryset = queryset.filter(available__gte=5, available__lte=15)
        elif balance_status == 'high':
            queryset = queryset.filter(available__gt=15)
    
    # Statistiques
    stats = {
        'total_employees': LeaveBalance.objects.count(),
        'total_acquired_days': LeaveBalance.objects.aggregate(Sum('acquired'))['acquired__sum'] or 0,
        'total_taken_days': LeaveBalance.objects.aggregate(Sum('taken'))['taken__sum'] or 0,
        'total_available_days': LeaveBalance.objects.aggregate(Sum('available'))['available__sum'] or 0,
    }
    
    # Pagination
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    leave_balances = paginator.get_page(page_number)
    
    # Départements pour le filtre
    departments = Department.objects.all()
    
    # Construire la chaîne de requête pour la pagination
    query_params = []
    if name:
        query_params.append(f'name={name}')
    if department_id:
        query_params.append(f'department={department_id}')
    if balance_status:
        query_params.append(f'balance_status={balance_status}')
    
    query_string = '&'.join(query_params)
    
    context = {
        'leave_balances': leave_balances,
        'stats': stats,
        'departments': departments,
        'filters': {
            'name': name,
            'department': department_id,
            'balance_status': balance_status,
            'query_string': query_string
        }
    }
    
    return render(request, 'rh_management/manage_leave_balances.html', context)

@login_required
@user_passes_test(is_admin_or_hr)
def update_leave_balance(request, user_id):
    """Vue pour mettre à jour le solde de congés d'un utilisateur."""
    user = get_object_or_404(User, id=user_id)
    leave_balance, created = LeaveBalance.objects.get_or_create(user=user, defaults={'acquired': 25.0})
    
    if request.method == 'POST':
        try:
            acquired = float(request.POST.get('acquired', 0.0))
            taken = float(request.POST.get('taken', 0.0))
            
            leave_balance.acquired = acquired
            leave_balance.taken = taken
            leave_balance.save()
            
            messages.success(request, f"Solde de congés mis à jour pour {user.get_full_name() or user.username}")
        except ValueError:
            messages.error(request, "Format de valeur invalide. Veuillez entrer des nombres valides.")
        
    return redirect('manage_leave_balances')

@login_required
@user_passes_test(is_admin_or_hr)
def bulk_update_leave_balance(request):
    """Attribution collective de congés."""
    if request.method == "POST":
        employee_group = request.POST.get('employee_group', 'all')
        days_to_add = float(request.POST.get('days_to_add', 0))
        
        # Filtrer les utilisateurs selon le groupe sélectionné
        users_query = User.objects.filter(is_active=True)
        
        if employee_group == 'permanent':
            # Filtrer les employés permanents (exemple)
            users_query = users_query.filter(groups__name='Permanent')
        elif employee_group == 'temporary':
            # Filtrer les employés temporaires (exemple)
            users_query = users_query.filter(groups__name='Temporary')
        elif employee_group == 'zero':
            # Employés sans solde de congés
            users_with_balance = LeaveBalance.objects.filter(acquired__gt=0).values_list('user_id', flat=True)
            users_query = users_query.exclude(id__in=users_with_balance)
        
        updated_count = 0
        for user in users_query:
            balance, created = LeaveBalance.objects.get_or_create(user=user)
            balance.acquired += days_to_add
            balance.save()
            updated_count += 1
        
        messages.success(request, f"Solde de congés mis à jour pour {updated_count} employés.")
        return redirect('manage_leave_balances')
    
    return redirect('manage_leave_balances')

@login_required
@user_is_hr_or_admin
def adjust_leave_balance(request):
    """
    Vue pour ajuster le solde de congés d'un employé
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        adjustment = float(request.POST.get('adjustment', 0))
        reason = request.POST.get('reason')
        
        if not user_id or not reason:
            messages.error(request, "Veuillez fournir toutes les informations requises.")
            return redirect('manage_leave_balances')
        
        try:
            user = User.objects.get(id=user_id)
            leave_balance = LeaveBalance.objects.get_or_create(user=user)[0]
            
            # Créer l'ajustement
            leave_adjustment = LeaveAdjustment.objects.create(
                user=user,
                adjustment=adjustment,
                reason=reason,
                adjusted_by=request.user
            )
            
            # Mettre à jour le solde
            leave_balance.acquired += adjustment if adjustment > 0 else 0
            leave_balance.taken -= adjustment if adjustment < 0 else 0
            leave_balance.available += adjustment
            leave_balance.save()
            
            # Envoyer notification à l'employé
            Notification.objects.create(
                user=user,
                title="Ajustement de solde de congés",
                message=f"Votre solde de congés a été ajusté de {adjustment} jour(s). Raison : {reason}",
                icon="fa-calendar-day",
                url="/my-leaves/"
            )
            
            messages.success(request, f"Le solde de congés de {user.get_full_name()} a été ajusté de {adjustment} jour(s).")
        except User.DoesNotExist:
            messages.error(request, "Utilisateur introuvable.")
        except Exception as e:
            messages.error(request, f"Une erreur est survenue: {str(e)}")
            
    return redirect('manage_leave_balances')

@login_required
@user_is_hr_or_admin
def adjust_collective_leave_balance(request):
    """
    Vue pour ajuster les soldes de congés de plusieurs employés en une fois
    """
    if request.method == 'POST':
        employee_ids = request.POST.get('employee_ids', '')
        adjustment = float(request.POST.get('collective_adjustment', 0))
        reason = request.POST.get('reason')
        
        if not employee_ids or not reason:
            messages.error(request, "Veuillez fournir toutes les informations requises.")
            return redirect('manage_leave_balances')
        
        employee_id_list = [int(id) for id in employee_ids.split(',') if id]
        success_count = 0
        
        for user_id in employee_id_list:
            try:
                user = User.objects.get(id=user_id)
                leave_balance = LeaveBalance.objects.get_or_create(user=user)[0]
                
                # Créer l'ajustement
                LeaveAdjustment.objects.create(
                    user=user,
                    adjustment=adjustment,
                    reason=f"{reason} (Ajustement collectif)",
                    adjusted_by=request.user
                )
                
                # Mettre à jour le solde
                leave_balance.acquired += adjustment if adjustment > 0 else 0
                leave_balance.taken -= adjustment if adjustment < 0 else 0
                leave_balance.available += adjustment
                leave_balance.save()
                
                # Envoyer notification à l'employé
                Notification.objects.create(
                    user=user,
                    title="Ajustement de solde de congés",
                    message=f"Votre solde de congés a été ajusté de {adjustment} jour(s). Raison : {reason}",
                    icon="fa-calendar-day",
                    url="/my-leaves/"
                )
                
                success_count += 1
            except User.DoesNotExist:
                continue
            except Exception as e:
                continue
        
        if success_count > 0:
            messages.success(request, f"Le solde de congés de {success_count} employé(s) a été ajusté de {adjustment} jour(s).")
        else:
            messages.error(request, "Aucun ajustement n'a pu être effectué.")
            
    return redirect('manage_leave_balances')

@login_required
@user_is_hr_or_admin
def get_leave_balance_history(request, user_id):
    """
    API pour obtenir l'historique des ajustements de solde de congés d'un employé
    """
    try:
        user = User.objects.get(id=user_id)
        adjustments = LeaveAdjustment.objects.filter(user=user).order_by('-created_at')
        
        history_data = []
        for adj in adjustments:
            history_data.append({
                'date': adj.created_at.strftime('%d/%m/%Y %H:%M'),
                'adjustment': adj.adjustment,
                'reason': adj.reason,
                'adjusted_by': adj.adjusted_by.get_full_name() if adj.adjusted_by else 'Système'
            })
        
        return JsonResponse({'status': 'success', 'history': history_data})
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Utilisateur introuvable.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def manage_leaves_view(request):
    """Vue pour gérer les demandes de congés."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    from .permissions import is_encadrant, is_rh, is_admin
    is_admin_flag = is_admin(request.user)
    is_rh_flag = is_rh(request.user)
    is_encadrant_flag = is_encadrant(request.user)
    
    if not (is_admin_flag or is_rh_flag or is_encadrant_flag):
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrer les demandes de congés selon le rôle de l'utilisateur
    if is_admin_flag:
        # Les admins voient toutes les demandes
        pending_leaves = LeaveRequest.objects.filter(status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.exclude(status='pending').order_by('-updated_at')
    elif is_rh_flag:
        # Les RH voient les demandes des employés
        employee_group = Group.objects.get(name='Employé')
        employee_users = employee_group.user_set.all()
        pending_leaves = LeaveRequest.objects.filter(user__in=employee_users, status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.filter(user__in=employee_users).exclude(status='pending').order_by('-updated_at')
    elif is_encadrant_flag:
        # Les encadrants voient les demandes des STP
        stp_group = Group.objects.get(name='STP')
        stp_users = stp_group.user_set.all()
        pending_leaves = LeaveRequest.objects.filter(user__in=stp_users, status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.filter(user__in=stp_users).exclude(status='pending').order_by('-updated_at')
    else:
        pending_leaves = LeaveRequest.objects.none()
        processed_leaves = LeaveRequest.objects.none()
    
    # Récupérer les demandes de l'utilisateur connecté
    user_leaves = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Ajouter les compteurs de notifications
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    
    context = {
        'pending_leaves': pending_leaves,
        'user_leaves': user_leaves,
        'processed_leaves': processed_leaves,
        'is_admin': is_admin_flag,
        'is_hr': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_leaves.html', context)

@login_required
@user_passes_test(can_approve_leaves)
def approve_leave(request, leave_id):
    """Approuve une demande de congé."""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    leave.status = 'approved'
    leave.save()

    # Créer une notification pour l'employé
    from ..models import Notification
    Notification.create_leave_notification(
        leave.user,
        leave,
        f"Votre demande de congé du {leave.start_date} au {leave.end_date} a été approuvée."
    )

    messages.success(request, f"Congé approuvé pour {leave.user.username}.")
    return redirect('manage_leaves')

@login_required
@user_passes_test(can_approve_leaves)
def reject_leave(request, leave_id):
    """Rejette une demande de congé."""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    leave.status = 'rejected'
    leave.save()

    # Créer une notification pour l'employé
    from ..models import Notification
    Notification.create_leave_notification(
        leave.user,
        leave,
        f"Votre demande de congé du {leave.start_date} au {leave.end_date} a été refusée."
    )

    messages.error(request, f"Congé refusé pour {leave.user.username}.")
    return redirect('manage_leaves')

@login_required
def leave_action(request, leave_id):
    """
    Vue pour approuver ou rejeter une demande de congé
    """
    # Utiliser LeaveRequest au lieu de Leave
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    # CORRECTION: Empêcher l'auto-validation/rejet des congés
    if leave.user == request.user:
        messages.error(request, "Vous ne pouvez pas traiter votre propre demande de congé.")
        return redirect('manage_leaves')
    
    # Vérifier que la demande est encore en attente
    if leave.status != 'pending':
        messages.error(request, "Cette demande de congé a déjà été traitée.")
        return redirect('manage_leaves')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            leave.status = 'approved'
            if hasattr(leave, 'comment'):
                leave.comment = comment
            leave.save()
            
            # Notifier l'utilisateur
            Notification.objects.create(
                user=leave.user,
                title="Demande de congé approuvée",
                message=f"Votre demande de congé du {leave.start_date.strftime('%d/%m/%Y')} au {leave.end_date.strftime('%d/%m/%Y')} a été approuvée.",
                url="/my-leaves/",
                icon="fa-calendar-check"
            )
            
            messages.success(request, f"La demande de congé de {leave.user.get_full_name()} a été approuvée.")
            
        elif action == 'reject':
            if not comment:
                messages.error(request, "Un motif de rejet est requis.")
                return redirect('manage_leaves')
                
            leave.status = 'rejected'
            if hasattr(leave, 'comment'):
                leave.comment = comment
            elif hasattr(leave, 'rejection_reason'):
                leave.rejection_reason = comment
            leave.save()
            
            # Notifier l'utilisateur
            Notification.objects.create(
                user=leave.user,
                title="Demande de congé rejetée",
                message=f"Votre demande de congé du {leave.start_date.strftime('%d/%m/%Y')} au {leave.end_date.strftime('%d/%m/%Y')} a été rejetée. Motif: {comment}",
                url="/my-leaves/",
                icon="fa-calendar-times"
            )
            
            messages.success(request, f"La demande de congé de {leave.user.get_full_name()} a été rejetée.")
    
    return redirect('manage_leaves')

@login_required
@user_is_hr_or_admin
def approve_all_leaves(request):
    """
    Approuve toutes les demandes de congé en attente
    """
    # Utiliser LeaveRequest au lieu de Leave
    pending_leaves = LeaveRequest.objects.filter(status='pending')
    
    # CORRECTION: Exclure les propres demandes de l'utilisateur
    pending_leaves = pending_leaves.exclude(user=request.user)
    
    count = pending_leaves.count()
    
    for leave in pending_leaves:
        leave.status = 'approved'
        leave.save()
        
        # Notifier l'utilisateur
        Notification.objects.create(
            user=leave.user,
            title="Demande de congé approuvée",
            message=f"Votre demande de congé du {leave.start_date.strftime('%d/%m/%Y')} au {leave.end_date.strftime('%d/%m/%Y')} a été approuvée.",
            url="/my-leaves/",
            icon="fa-calendar-check"
        )
    
    if count > 0:
        messages.success(request, f"{count} demande(s) de congé ont été approuvées avec succès (vos propres demandes ont été exclues).")
    else:
        messages.info(request, "Aucune demande de congé à approuver.")
    
    return redirect('manage_leaves')

@login_required
@user_passes_test(is_admin_or_hr)
def export_leaves(request):
    """
    Exporte les demandes de congés au format Excel ou PDF
    """
    format = request.GET.get('format', 'excel')
    
    if format == 'excel':
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=leaves.xlsx'
        
        # Logique d'export Excel à implémenter
        
        return response
        
    elif format == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=leaves.pdf'
        
        # Logique d'export PDF à implémenter
        
        return response
    
    else:
        messages.error(request, "Format d'export non supporté")
        return redirect('manage_leaves')

@login_required
def my_leaves(request):
    """
    Vue pour afficher les congés de l'utilisateur connecté
    """
    # Créer automatiquement un solde de congés s'il n'existe pas
    leave_balance, created = LeaveBalance.objects.get_or_create(
        user=request.user,
        defaults={
            'acquired': 25.0,  # 25 jours par défaut (ajustable selon votre politique)
            'taken': 0.0,
            'available': 25.0
        }
    )
    
    if created:
        # Notifier l'utilisateur de la création du solde
        messages.info(request, f"Votre solde de congés a été initialisé avec {leave_balance.acquired} jours.")
    
    # Récupérer les demandes de congé de l'utilisateur
    leaves = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculer les statistiques
    stats = {
        'total_requests': leaves.count(),
        'pending_requests': leaves.filter(status='pending').count(),
        'approved_requests': leaves.filter(status='approved').count(),
        'rejected_requests': leaves.filter(status='rejected').count(),
        'days_taken_this_year': leaves.filter(
            status='approved',
            start_date__year=datetime.now().year
        ).aggregate(total=Sum('days_requested'))['total'] or 0
    }
    
    context = {
        'leaves': leaves,
        'leave_balance': leave_balance,
        'stats': stats
    }
    
    return render(request, 'rh_management/my_leaves.html', context)

@login_required
@user_is_hr_or_admin
def initialize_leave_balances(request):
    """
    Vue pour initialiser les soldes de congés pour tous les utilisateurs qui n'en ont pas
    """
    if request.method == 'POST':
        default_days = float(request.POST.get('default_days', 25))
        
        # Récupérer tous les utilisateurs actifs sans solde de congés
        users_without_balance = User.objects.filter(
            is_active=True
        ).exclude(
            leavebalance__isnull=False
        )
        
        created_count = 0
        for user in users_without_balance:
            leave_balance, created = LeaveBalance.objects.get_or_create(
                user=user,
                defaults={
                    'acquired': default_days,
                    'taken': 0.0,
                    'available': default_days
                }
            )
            if created:
                created_count += 1
                
                # Créer une notification pour l'utilisateur
                Notification.objects.create(
                    user=user,
                    title="Solde de congés initialisé",
                    message=f"Votre solde de congés a été initialisé avec {default_days} jours.",
                    url="/my-leaves/",
                    icon="fa-calendar-day"
                )
        
        messages.success(request, f"{created_count} solde(s) de congés ont été initialisés.")
        return redirect('manage_leave_balances')
    
    # Compter les utilisateurs sans solde
    users_without_balance_count = User.objects.filter(
        is_active=True
    ).exclude(
        leavebalance__isnull=False
    ).count()
    
    context = {
        'users_without_balance_count': users_without_balance_count
    }
    
    return render(request, 'rh_management/initialize_leave_balances.html', context)

@login_required
@user_passes_test(is_admin_or_hr)
def export_leave_balances(request):
    """
    Exporte les soldes de congés au format CSV
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leave_balances.csv"'
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Employé', 'Email', 'Département', 'Jours acquis', 'Jours pris', 'Solde disponible', 'Dernière mise à jour'])
    
    leave_balances = LeaveBalance.objects.all().select_related('user', 'user__profile')
    
    for balance in leave_balances:
        writer.writerow([
            balance.user.get_full_name() or balance.user.username,
            balance.user.email,
            balance.user.profile.department if hasattr(balance.user, 'profile') and balance.user.profile.department else 'Non défini',
            balance.acquired,
            balance.taken,
            balance.available,
            balance.updated_at.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response

@login_required
@user_is_hr_or_admin
def manage_leaves(request):
    """
    Vue pour gérer les demandes de congés (pour RH et admins)
    """
    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    leave_type = request.GET.get('leave_type', '')
    user_id = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sort_by = request.GET.get('sort_by', 'created_at')
    sort_order = request.GET.get('sort_order', 'desc')

    # Construire la requête de base
    queryset = Leave.objects.all()

    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if leave_type:
        queryset = queryset.filter(leave_type=leave_type)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(start_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(end_date__lte=end_date)

    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if leave_type:
        query_params.append(f'leave_type={leave_type}')
    if user_id:
        query_params.append(f'user={user_id}')
    if start_date:
        query_params.append(f'start_date={start_date}')
    if end_date:
        query_params.append(f'end_date={end_date}')
    if sort_by:
        query_params.append(f'sort_by={sort_by}')
    if sort_order:
        query_params.append(f'sort_order={sort_order}')
    
    query_string = '&'.join(query_params)

    # Appliquer le tri
    order_prefix = '' if sort_order == 'asc' else '-'
    if sort_by == 'user':
        # Tri spécial pour le nom d'utilisateur
        queryset = queryset.order_by(f'{order_prefix}user__first_name', f'{order_prefix}user__last_name')
    else:
        queryset = queryset.order_by(f'{order_prefix}{sort_by}')

    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    all_leaves = paginator.get_page(page_number)

    # Récupérer les demandes en attente
    pending_leaves = queryset.filter(status='pending')

    # Calculer les statistiques
    stats = {
        'total_count': Leave.objects.count(),
        'pending_count': Leave.objects.filter(status='pending').count(),
        'approved_count': Leave.objects.filter(status='approved').count(),
        'rejected_count': Leave.objects.filter(status='rejected').count()
    }

    # Récupérer tous les utilisateurs pour le filtre
    all_users = User.objects.all().order_by('first_name', 'last_name')

    # Vérifier si l'utilisateur est administrateur (pour le bouton de suppression)
    is_admin = request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name='Admin').exists()

    context = {
        'all_leaves': all_leaves,
        'pending_leaves': pending_leaves,
        'stats': stats,
        'filters': {
            'status': status,
            'leave_type': leave_type,
            'user_id': int(user_id) if user_id.isdigit() else None,
            'start_date': start_date,
            'end_date': end_date,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'query_string': query_string
        },
        'all_users': all_users,
        'is_admin': is_admin
    }

    return render(request, 'rh_management/manage_leaves.html', context)

@login_required
def leave_history(request):
    """
    Vue pour afficher l'historique complet des demandes de congé de l'utilisateur.
    Inclut des fonctionnalités de filtrage et de pagination.
    """
    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    leave_type = request.GET.get('leave_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sort_by = request.GET.get('sort_by', '-start_date')  # Par défaut, tri par date de début décroissante
    
    # Récupérer toutes les demandes de congé de l'utilisateur
    queryset = LeaveRequest.objects.filter(user=request.user)
    
    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if leave_type:
        queryset = queryset.filter(leave_type=leave_type)
    if start_date:
        queryset = queryset.filter(start_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(end_date__lte=end_date)
    
    # Appliquer le tri
    queryset = queryset.order_by(sort_by)
    
    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if leave_type:
        query_params.append(f'leave_type={leave_type}')
    if start_date:
        query_params.append(f'start_date={start_date}')
    if end_date:
        query_params.append(f'end_date={end_date}')
    if sort_by != '-start_date':
        query_params.append(f'sort_by={sort_by}')
    
    query_string = '&'.join(query_params)
    
    # Calculer les statistiques
    stats = {
        'total_count': queryset.count(),
        'pending_count': queryset.filter(status='pending').count(),
        'approved_count': queryset.filter(status='approved').count(),
        'rejected_count': queryset.filter(status='rejected').count(),
        'total_days': sum(leave.days_requested for leave in queryset),
        'approved_days': sum(leave.days_requested for leave in queryset.filter(status='approved')),
        'pending_days': sum(leave.days_requested for leave in queryset.filter(status='pending')),
    }
    
    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    leave_requests = paginator.get_page(page_number)
    
    context = {
        'leave_requests': leave_requests,
        'stats': stats,
        'filters': {
            'status': status,
            'leave_type': leave_type,
            'start_date': start_date,
            'end_date': end_date,
            'sort_by': sort_by,
            'query_string': query_string
        }
    }
    
    return render(request, 'rh_management/leave_history.html', context)

@login_required
@user_is_hr_or_admin
def admin_leave_history(request):
    """
    Vue pour afficher l'historique complet des demandes de congé pour tous les utilisateurs.
    Accessible uniquement par les administrateurs et le personnel RH.
    """
    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    leave_type = request.GET.get('leave_type', '')
    user_id = request.GET.get('user', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sort_by = request.GET.get('sort_by', '-start_date')  # Par défaut, tri par date de début décroissante
    
    # Récupérer toutes les demandes de congé
    queryset = LeaveRequest.objects.all()
    
    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if leave_type:
        queryset = queryset.filter(leave_type=leave_type)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if start_date:
        queryset = queryset.filter(start_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(end_date__lte=end_date)
    
    # Appliquer le tri
    queryset = queryset.order_by(sort_by)
    
    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if leave_type:
        query_params.append(f'leave_type={leave_type}')
    if user_id:
        query_params.append(f'user={user_id}')
    if start_date:
        query_params.append(f'start_date={start_date}')
    if end_date:
        query_params.append(f'end_date={end_date}')
    if sort_by != '-start_date':
        query_params.append(f'sort_by={sort_by}')
    
    query_string = '&'.join(query_params)
    
    # Calculer les statistiques
    stats = {
        'total_count': queryset.count(),
        'pending_count': queryset.filter(status='pending').count(),
        'approved_count': queryset.filter(status='approved').count(),
        'rejected_count': queryset.filter(status='rejected').count(),
        'total_days': sum(leave.days_requested for leave in queryset),
        'approved_days': sum(leave.days_requested for leave in queryset.filter(status='approved')),
        'pending_days': sum(leave.days_requested for leave in queryset.filter(status='pending')),
    }
    
    # Récupérer tous les utilisateurs pour le filtre
    all_users = User.objects.all().order_by('first_name', 'last_name')
    
    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    leave_requests = paginator.get_page(page_number)
    
    context = {
        'leave_requests': leave_requests,
        'stats': stats,
        'filters': {
            'status': status,
            'leave_type': leave_type,
            'user_id': int(user_id) if user_id.isdigit() else None,
            'start_date': start_date,
            'end_date': end_date,
            'sort_by': sort_by,
            'query_string': query_string
        },
        'all_users': all_users
    }
    
    return render(request, 'rh_management/admin_leave_history.html', context)

@login_required
@user_passes_test(is_admin_or_hr)
def delete_leave(request, leave_id):
    """
    Vue pour supprimer une demande de congé (pour les admins uniquement)
    """
    # Seuls les super-utilisateurs peuvent supprimer des demandes
    if not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour supprimer une demande de congé.")
        return redirect('manage_leaves')
    
    # Utiliser LeaveRequest au lieu de Leave
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    if request.method == 'POST':
        user_name = leave.user.get_full_name() or leave.user.username
        leave_period = f"{leave.start_date.strftime('%d/%m/%Y')} au {leave.end_date.strftime('%d/%m/%Y')}"
        
        # Notifier l'utilisateur de la suppression
        Notification.objects.create(
            user=leave.user,
            title="Demande de congé supprimée",
            message=f"Votre demande de congé du {leave_period} a été supprimée par l'administration.",
            url="/my-leaves/",
            icon="fa-trash"
        )
        
        leave.delete()
        messages.success(request, f"La demande de congé de {user_name} pour la période du {leave_period} a été supprimée.")
        
    return redirect('manage_leaves')

@login_required
def cancel_leave(request, leave_id):
    """
    Annule une demande de congé (seul l'utilisateur peut annuler sa propre demande en attente)
    """
    leave = get_object_or_404(LeaveRequest, id=leave_id, user=request.user)
    
    # Vérifier que la demande est encore en attente
    if leave.status != 'pending':
        messages.error(request, "Vous ne pouvez annuler que les demandes de congé en attente.")
        return redirect('my_leaves')
    
    if request.method == 'POST':
        leave.delete()
        messages.success(request, "Votre demande de congé a été annulée avec succès.")
        return redirect('my_leaves')
    
    return render(request, 'rh_management/cancel_leave.html', {'leave': leave})