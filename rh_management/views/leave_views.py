from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Sum
from django.core.mail import send_mail
from django.http import HttpResponse
from ..models import LeaveRequest, LeaveBalance
from ..forms import LeaveRequestForm
from .permissions import is_admin_or_hr, is_admin_hr_or_encadrant, can_approve_leaves
from datetime import datetime, timedelta

def calculate_working_days(start_date, end_date):
    """Calculate the number of working days (Monday to Friday) between two dates."""
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # If it's a weekday (0 = Monday, 6 = Sunday)
        if current_date.weekday() < 5:  # 0-4 represents Monday to Friday
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
            from ..models import ExpenseReport, KilometricExpense
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif is_encadrant:
            # Pour les encadrants, montrer uniquement les demandes de leur équipe
            from django.contrib.auth.models import User
            from ..models import ExpenseReport, KilometricExpense
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
@user_passes_test(is_admin_or_hr)
def manage_leave_balances(request):
    """Vue pour gérer les soldes de congés des employés."""
    leave_balances = LeaveBalance.objects.all().select_related('user')
    
    # Statistiques
    from django.contrib.auth.models import User
    employee_count = User.objects.filter(is_active=True).count()
    average_balance = LeaveBalance.objects.filter(acquired__gt=0).aggregate(avg=Avg('acquired'))['avg'] or 0
    currently_on_leave = LeaveRequest.objects.filter(
        status='approved', 
        start_date__lte=timezone.now(), 
        end_date__gte=timezone.now()
    ).count()
    no_balance_count = User.objects.filter(is_active=True).exclude(
        id__in=LeaveBalance.objects.filter(acquired__gt=0).values_list('user_id', flat=True)
    ).count()
    
    return render(request, 'rh_management/manage_leave_balances.html', {
        'leave_balances': leave_balances,
        'employee_count': employee_count,
        'average_balance': round(average_balance, 1),
        'currently_on_leave': currently_on_leave,
        'no_balance_count': no_balance_count
    })

@login_required
@user_passes_test(is_admin_or_hr)
def update_leave_balance(request):
    """Mise à jour du solde de congés d'un employé."""
    if request.method == "POST":
        balance_id = request.POST.get('balance_id')
        acquired_days = float(request.POST.get('acquired_days', 0))
        taken_days = float(request.POST.get('taken_days', 0))
        
        balance = get_object_or_404(LeaveBalance, id=balance_id)
        balance.acquired = acquired_days
        balance.taken = taken_days
        balance.save()
        
        messages.success(request, f"Le solde de congés de {balance.user.get_full_name() or balance.user.username} a été mis à jour.")
        return redirect('manage_leave_balances')
    
    return redirect('manage_leave_balances')

@login_required
@user_passes_test(is_admin_or_hr)
def bulk_update_leave_balance(request):
    """Attribution collective de congés."""
    if request.method == "POST":
        employee_group = request.POST.get('employee_group', 'all')
        days_to_add = float(request.POST.get('days_to_add', 0))
        
        # Filtrer les utilisateurs selon le groupe sélectionné
        from django.contrib.auth.models import User
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
@user_passes_test(is_admin_hr_or_encadrant)
def manage_leaves_view(request):
    """Vue pour gérer les demandes de congés."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    from .permissions import is_encadrant
    is_admin = request.user.is_superuser
    is_hr = request.user.is_staff
    is_encadrant_flag = is_encadrant(request.user)
    
    if not (is_admin or is_hr or is_encadrant_flag):
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrer les demandes de congés selon le rôle de l'utilisateur
    from django.contrib.auth.models import User
    if is_admin or is_hr:
        pending_leaves = LeaveRequest.objects.filter(status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.exclude(status='pending').order_by('-updated_at')
    elif is_encadrant_flag:
        # L'encadrant ne voit que les demandes de son équipe
        team_members = User.objects.filter(team_leader=request.user)
        pending_leaves = LeaveRequest.objects.filter(user__in=team_members, status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.filter(user__in=team_members).exclude(status='pending').order_by('-updated_at')
    else:
        pending_leaves = LeaveRequest.objects.none()
        processed_leaves = LeaveRequest.objects.none()
    
    # Récupérer les demandes de l'utilisateur connecté
    user_leaves = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Ajouter les compteurs de notifications
    from ..models import ExpenseReport, KilometricExpense
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    
    context = {
        'pending_leaves': pending_leaves,
        'user_leaves': user_leaves,
        'processed_leaves': processed_leaves,
        'is_admin': is_admin,
        'is_hr': is_hr,
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

   # send_mail(
   #     subject="Votre demande de congé a été approuvée",
   #     message=f"Bonjour {leave.user.username},\n\nVotre demande de congé du {leave.start_date} au {leave.end_date} a été approuvée.",
   #     from_email="no-reply@cyberun.info",
   #     recipient_list=[leave.user.email]
   # )

    messages.success(request, f"Congé approuvé pour {leave.user.username}.")
    return redirect('manage_leaves')

@login_required
@user_passes_test(can_approve_leaves)
def reject_leave(request, leave_id):
    """Rejette une demande de congé."""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    leave.status = 'rejected'
    leave.save()

   # send_mail(
   #     subject="Votre demande de congé a été refusée",
   #     message=f"Bonjour {leave.user.username},\n\nVotre demande de congé du {leave.start_date} au {leave.end_date} a été refusée.",
   #     from_email="no-reply@cyberun.info",
   #     recipient_list=[leave.user.email]
   # )

    messages.error(request, f"Congé refusé pour {leave.user.username}.")
    return redirect('manage_leaves')

@login_required
def leave_action(request, leave_id):
    """
    Vue pour gérer les actions sur les demandes de congés (approbation/rejet avec commentaire).
    Permet d'ajouter un commentaire lors de l'approbation ou du rejet d'une demande.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists()):
        messages.error(request, "Vous n'avez pas les droits nécessaires pour effectuer cette action.")
        return redirect('dashboard')
    
    # Récupérer la demande de congé
    try:
        leave_request = LeaveRequest.objects.get(id=leave_id)
    except LeaveRequest.DoesNotExist:
        messages.error(request, "La demande de congé n'existe pas.")
        return redirect('manage_leaves')
    
    # Traiter la demande si c'est un POST
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            # Approuver la demande
            leave_request.status = 'approved'
            leave_request.comment = comment
            leave_request.save()
            
            # Mettre à jour le solde de congés de l'utilisateur
            update_leave_balance(leave_request.user, leave_request)
            
            messages.success(request, "La demande de congé a été approuvée.")
        elif action == 'reject':
            # Rejeter la demande
            leave_request.status = 'rejected'
            leave_request.comment = comment
            leave_request.save()
            messages.success(request, "La demande de congé a été rejetée.")
        else:
            messages.error(request, "Action non reconnue.")
            
    return redirect('manage_leaves')

@login_required
def delete_leave(request, id):
    leave = get_object_or_404(LeaveRequest, id=id)
    if request.user.is_superuser:
        leave.delete()
    return redirect('dashboard')

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
