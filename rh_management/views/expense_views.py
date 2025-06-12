from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
from ..models import ExpenseReport, LeaveRequest, KilometricExpense, Expense, Notification
from ..forms import ExpenseReportForm
from .permissions import is_admin_hr_or_encadrant, is_admin, user_is_hr_or_admin
import pandas as pd
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Count
import csv

@login_required
def submit_expense(request):
    """Vue pour soumettre une note de frais."""
    # Initialiser le formulaire au début de la fonction
    form = ExpenseReportForm()
    
    if request.method == "POST":
        try:
            # Récupérer les données du formulaire avec les noms corrects
            date = request.POST.get('date')
            amount = request.POST.get('amount')
            expense_type = request.POST.get('expense_type')
            description = request.POST.get('description')
            vat = request.POST.get('vat', 0)
            project = request.POST.get('project', '')
            location = request.POST.get('location', '')
            comment = request.POST.get('comment', '')
            refacturable = request.POST.get('refacturable') == 'on'
            
            # Validation des données
            if not all([date, amount, expense_type, description]):
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
                return redirect('submit_expense')
                
            # Convertir la date et le montant
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            amount_decimal = Decimal(str(amount).replace(',', '.'))
            
            if amount_decimal <= 0:
                messages.error(request, "Le montant doit être supérieur à zéro.")
                return redirect('submit_expense')
            
            # Créer la note de frais
            expense = ExpenseReport(
                user=request.user,
                date=date_obj,
                amount=amount_decimal,
                expense_type=expense_type,
                description=description,
                vat=Decimal(str(vat).replace(',', '.')),
                project=project,
                location=location,
                comment=comment,
                refacturable=refacturable,
                status='pending'
            )
            
            # Gérer le téléchargement de la pièce justificative
            if 'receipt' in request.FILES:
                receipt = request.FILES['receipt']
                
                # Vérifier la taille du fichier
                if receipt.size > 5 * 1024 * 1024:  # 5 Mo
                    messages.error(request, "La pièce justificative ne doit pas dépasser 5 Mo.")
                    return redirect('submit_expense')
                
                # Vérifier le type de fichier
                allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
                if receipt.content_type not in allowed_types:
                    messages.error(request, "Format de fichier non autorisé. Utilisez PDF, JPEG ou PNG.")
                    return redirect('submit_expense')
                
                expense.receipt = receipt
            
            # Gérer le document complémentaire
            if 'attachment' in request.FILES:
                attachment = request.FILES['attachment']
                
                # Vérifier la taille du fichier
                if attachment.size > 5 * 1024 * 1024:  # 5 Mo
                    messages.error(request, "Le document complémentaire ne doit pas dépasser 5 Mo.")
                    return redirect('submit_expense')
                
                expense.attachment = attachment
            
            # Enregistrer la note de frais
            expense.save()
            
            # Créer une notification pour les RH
            for hr_user in User.objects.filter(is_staff=True):
                Notification.objects.create(
                    user=hr_user,
                    title="Nouvelle note de frais",
                    message=f"{request.user.get_full_name() or request.user.username} a soumis une note de frais de {amount_decimal} €.",
                    notification_type='expense',
                    object_id=expense.id,
                    icon="fa-file-invoice-dollar",
                    color="warning",
                    url="/manage-expenses/"
                )
            
            messages.success(request, "Votre note de frais a été soumise avec succès.")
            return redirect('my_expenses')
        
        except ValueError as e:
            print(f"Erreur de format: {str(e)}")
            messages.error(request, "Format de montant ou de date invalide.")
        except Exception as e:
            print(f"Erreur lors de la soumission: {str(e)}")
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
    
    # Pas besoin de "else:" ici puisque nous avons déjà initialisé form au début
    
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
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/submit_expense.html', context)

@login_required
def my_expenses_view(request):
    """Vue pour afficher les notes de frais de l'utilisateur."""
    expenses = ExpenseReport.objects.filter(user=request.user).order_by('-created_at')
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Initialiser les compteurs
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
        if is_admin or is_rh:
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif is_encadrant:
            team_members = User.objects.filter(team_leader=request.user)
            new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'expenses': expenses,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/my_expenses.html', context)

@login_required
def my_expenses(request):
    """
    Vue pour afficher les notes de frais de l'utilisateur connecté
    """
    # Récupérer les notes de frais de l'utilisateur connecté
    expenses = ExpenseReport.objects.filter(user=request.user).order_by('-date')
    
    # Calculer les statistiques
    stats = {
        'total_count': expenses.count(),
        'pending_count': expenses.filter(status='pending').count(),
        'approved_count': expenses.filter(status='approved').count(),
        'rejected_count': expenses.filter(status='rejected').count(),
        'total_amount': expenses.aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_amount': expenses.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'approved_amount': expenses.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    return render(request, 'rh_management/my_expenses.html', {
        'expenses': expenses,
        'stats': stats
    })

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def manage_expenses_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists()):
        messages.error(request, "Vous n'avez pas les droits nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrer les dépenses selon le rôle de l'utilisateur
    if request.user.is_superuser or request.user.is_staff:
        pending_expenses = ExpenseReport.objects.filter(status='pending')
    else:  # Encadrant
        team_members = User.objects.filter(team_leader=request.user)
        pending_expenses = ExpenseReport.objects.filter(user__in=team_members, status='pending')
    
    # Calcul des statistiques
    approved_count = ExpenseReport.objects.filter(status='approved').count()
    rejected_count = ExpenseReport.objects.filter(status='rejected').count()
    total_amount = ExpenseReport.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or 0
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    elif is_encadrant:
        team_members = User.objects.filter(team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'pending_expenses': pending_expenses,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': total_amount,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_expenses.html', context)

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def approve_expense(request, expense_id):
    """Approuve une note de frais."""
    expense = get_object_or_404(ExpenseReport, id=expense_id)
    expense.status = 'approved'
    expense.save()

   # send_mail(
   #     subject="Votre note de frais a été approuvée",
   #     message=f"Bonjour {expense.user.username},\n\nVotre note de frais '{expense.description}' a été approuvée.",
   #     from_email="no-reply@cyberun.info",
   #     recipient_list= [expense.user.email]
   #  )

    messages.success(request, "Note de frais approuvée.")
    return redirect('manage_expenses')

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def reject_expense(request, expense_id):
    """Rejette une note de frais."""
    expense = get_object_or_404(ExpenseReport, id=expense_id)
    expense.status = 'rejected'
    expense.save()

   # send_mail(
   #     subject="Votre note de frais a été refusée",
   #     message=f"Bonjour {expense.user.username},\n\nVotre note de frais '{expense.description}' a été refusée.",
   #     from_email="no-reply@cyberun.info",
   #     recipient_list=[expense.user.email]
   # )

    messages.error(request, "Note de frais refusée.")
    return redirect('manage_expenses')

@login_required
def cancel_expense(request, expense_id):
    expense = get_object_or_404(ExpenseReport, id=expense_id, user=request.user)

    if expense.status == "pending":
        expense.delete()
        messages.success(request, "Votre note de frais a été annulée avec succès.")
    else:
        messages.error(request, "Vous ne pouvez annuler qu'une note de frais en attente.")

    return redirect("dashboard")

@login_required
@user_passes_test(is_admin)
def export_expenses(request):
    """Exporte les notes de frais de l'utilisateur en format Excel."""
    expenses = ExpenseReport.objects.filter(user=request.user)

    data = [
        [exp.date, exp.description, exp.amount, exp.get_status_display()]  # Suppression de exp.currency
        for exp in expenses
    ]

    df = pd.DataFrame(data, columns=["Date", "Description", "Montant", "Statut"])  # Ajustement des colonnes

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="notes_de_frais.xlsx"'
    df.to_excel(response, index=False)

    return response

@login_required
def delete_expense(request, id):
    expense = get_object_or_404(ExpenseReport, id=id)
    if request.user.is_superuser:
        expense.delete()
    return redirect('dashboard')

@login_required
def expense_action(request, expense_id):
    """
    Vue pour gérer les actions sur les notes de frais (approbation/rejet avec commentaire).
    Permet d'ajouter un commentaire lors de l'approbation ou du rejet d'une demande.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists()):
        messages.error(request, "Vous n'avez pas les droits nécessaires pour effectuer cette action.")
        return redirect('dashboard')
    
    # Récupérer la note de frais
    try:
        expense = ExpenseReport.objects.get(id=expense_id)
    except ExpenseReport.DoesNotExist:
        messages.error(request, "La note de frais n'existe pas.")
        return redirect('manage_expenses')
    
    # Traiter la demande si c'est un POST
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            # Approuver la note de frais
            expense.status = 'approved'
            expense.comment = comment
            expense.save()
            
            messages.success(request, "La note de frais a été approuvée.")
        elif action == 'reject':
            # Rejeter la note de frais
            expense.status = 'rejected'
            expense.comment = comment
            expense.save()
            messages.success(request, "La note de frais a été rejetée.")
        else:
            messages.error(request, "Action non reconnue.")
            
    return redirect('manage_expenses')

@login_required
@user_is_hr_or_admin
def manage_expenses(request):
    """
    Vue pour gérer les notes de frais (pour RH et admins)
    """
    # Utiliser ExpenseReport au lieu de Expense
    queryset = ExpenseReport.objects.all()

    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    expense_type = request.GET.get('expense_type', '')
    user_id = request.GET.get('user', '')
    project = request.GET.get('project', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sort_by = request.GET.get('sort_by', 'date')
    sort_order = request.GET.get('sort_order', 'desc')

    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if expense_type:
        queryset = queryset.filter(expense_type=expense_type)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if project:
        queryset = queryset.filter(project__icontains=project)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if expense_type:
        query_params.append(f'expense_type={expense_type}')
    if user_id:
        query_params.append(f'user={user_id}')
    if project:
        query_params.append(f'project={project}')
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

    # Récupérer les notes de frais en attente
    pending_expenses = queryset.filter(status='pending')

    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    all_expenses = paginator.get_page(page_number)

    # Calculer les statistiques
    stats = {
        'total_count': ExpenseReport.objects.count(),
        'pending_count': ExpenseReport.objects.filter(status='pending').count(),
        'approved_count': ExpenseReport.objects.filter(status='approved').count(),
        'rejected_count': ExpenseReport.objects.filter(status='rejected').count(),
        'total_amount': ExpenseReport.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_amount': ExpenseReport.objects.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'approved_amount': ExpenseReport.objects.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0,
    }

    # Récupérer tous les utilisateurs pour le filtre
    all_users = User.objects.all().order_by('first_name', 'last_name')

    context = {
        'all_expenses': all_expenses,
        'pending_expenses': pending_expenses,
        'stats': stats,
        'filters': {
            'status': status,
            'expense_type': expense_type,
            'user_id': int(user_id) if user_id.isdigit() else None,
            'project': project,
            'start_date': start_date,
            'end_date': end_date,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'query_string': query_string
        },
        'all_users': all_users
    }

    return render(request, 'rh_management/manage_expenses.html', context)

@login_required
@user_is_hr_or_admin
def export_expenses(request):
    """
    Exporte les notes de frais au format CSV
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Employé', 'Email', 'Date', 'Description', 'Type', 'Montant', 'Projet', 'Statut', 'Date de création'])
    
    # Utiliser ExpenseReport au lieu de Expense
    expenses = ExpenseReport.objects.all().select_related('user')
    
    for expense in expenses:
        writer.writerow([
            expense.user.get_full_name() or expense.user.username,
            expense.user.email,
            expense.date.strftime('%d/%m/%Y'),
            expense.description,
            expense.get_expense_type_display() if hasattr(expense, 'get_expense_type_display') else expense.expense_type,
            expense.amount,
            expense.project or 'N/A',
            expense.get_status_display(),
            expense.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response

@login_required
@user_is_hr_or_admin
def expense_action(request, expense_id):
    """
    Vue pour approuver ou rejeter une note de frais
    """
    # Utiliser ExpenseReport au lieu de Expense
    expense = get_object_or_404(ExpenseReport, id=expense_id)
    
    # CORRECTION: Empêcher l'auto-validation des notes de frais
    if expense.user == request.user:
        messages.error(request, "Vous ne pouvez pas traiter votre propre note de frais.")
        return redirect('manage_expenses')
    
    # Vérifier que la demande est encore en attente
    if expense.status != 'pending':
        messages.error(request, "Cette note de frais a déjà été traitée.")
        return redirect('manage_expenses')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            expense.status = 'approved'
            if hasattr(expense, 'comment'):
                expense.comment = comment
            expense.save()
            
            # Notifier l'utilisateur
            Notification.objects.create(
                user=expense.user,
                title="Note de frais approuvée",
                message=f"Votre note de frais de {expense.amount} € pour '{expense.description}' a été approuvée.",
                url="/my-expenses/",
                icon="fa-receipt"
            )
            
            messages.success(request, f"La note de frais de {expense.user.get_full_name()} a été approuvée.")
            
        elif action == 'reject':
            if not comment:
                messages.error(request, "Un motif de rejet est requis.")
                return redirect('manage_expenses')
                
            expense.status = 'rejected'
            if hasattr(expense, 'comment'):
                expense.comment = comment
            elif hasattr(expense, 'rejection_reason'):
                expense.rejection_reason = comment
            expense.save()
            
            # Notifier l'utilisateur
            Notification.objects.create(
                user=expense.user,
                title="Note de frais rejetée",
                message=f"Votre note de frais de {expense.amount} € pour '{expense.description}' a été rejetée.",
                url="/my-expenses/",
                icon="fa-receipt"
            )
            
            messages.success(request, f"La note de frais de {expense.user.get_full_name()} a été rejetée.")
    
    return redirect('manage_expenses')

@login_required
@user_is_hr_or_admin
def approve_all_expenses(request):
    """
    Approuve toutes les notes de frais en attente
    """
    # Utiliser ExpenseReport au lieu de Expense
    pending_expenses = ExpenseReport.objects.filter(status='pending')
    
    # CORRECTION: Exclure les propres notes de frais de l'utilisateur
    pending_expenses = pending_expenses.exclude(user=request.user)
    
    count = pending_expenses.count()
    
    for expense in pending_expenses:
        expense.status = 'approved'
        expense.save()
        
        # Notifier l'utilisateur
        Notification.objects.create(
            user=expense.user,
            title="Note de frais approuvée",
            message=f"Votre note de frais de {expense.amount} € pour '{expense.description}' a été approuvée.",
            url="/my-expenses/",
            icon="fa-receipt"
        )
    
    if count > 0:
        messages.success(request, f"{count} note(s) de frais ont été approuvées avec succès (vos propres notes ont été exclues).")
    else:
        messages.info(request, "Aucune note de frais à approuver.")
    
    return redirect('manage_expenses')

@login_required
def expense_history(request):
    """
    Vue pour afficher l'historique complet des notes de frais de l'utilisateur.
    Inclut des fonctionnalités de filtrage et de pagination.
    """
    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    expense_type = request.GET.get('expense_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    sort_by = request.GET.get('sort_by', '-date')  # Par défaut, tri par date décroissante
    
    # Récupérer toutes les notes de frais de l'utilisateur
    queryset = ExpenseReport.objects.filter(user=request.user)
    
    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if expense_type:
        queryset = queryset.filter(expense_type=expense_type)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    
    # Appliquer le tri
    queryset = queryset.order_by(sort_by)
    
    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if expense_type:
        query_params.append(f'expense_type={expense_type}')
    if start_date:
        query_params.append(f'start_date={start_date}')
    if end_date:
        query_params.append(f'end_date={end_date}')
    if sort_by != '-date':
        query_params.append(f'sort_by={sort_by}')
    
    query_string = '&'.join(query_params)
    
    # Calculer les statistiques
    stats = {
        'total_count': queryset.count(),
        'pending_count': queryset.filter(status='pending').count(),
        'approved_count': queryset.filter(status='approved').count(),
        'rejected_count': queryset.filter(status='rejected').count(),
        'total_amount': queryset.aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_amount': queryset.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'approved_amount': queryset.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    expenses = paginator.get_page(page_number)
    
    context = {
        'expenses': expenses,
        'stats': stats,
        'filters': {
            'status': status,
            'expense_type': expense_type,
            'start_date': start_date,
            'end_date': end_date,
            'sort_by': sort_by,
            'query_string': query_string
        }
    }
    
    return render(request, 'rh_management/expense_history.html', context)

@login_required
@user_is_hr_or_admin
def admin_expense_history(request):
    """
    Vue pour afficher l'historique complet des notes de frais pour tous les utilisateurs.
    Accessible uniquement par les administrateurs et le personnel RH.
    """
    # Récupérer les filtres de la requête
    status = request.GET.get('status', '')
    expense_type = request.GET.get('expense_type', '')
    user_id = request.GET.get('user', '')
    project = request.GET.get('project', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    refacturable = request.GET.get('refacturable', '')
    sort_by = request.GET.get('sort_by', '-date')  # Par défaut, tri par date décroissante
    
    # Récupérer toutes les notes de frais
    queryset = ExpenseReport.objects.all()
    
    # Appliquer les filtres
    if status:
        queryset = queryset.filter(status=status)
    if expense_type:
        queryset = queryset.filter(expense_type=expense_type)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if project:
        queryset = queryset.filter(project__icontains=project)
    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)
    if refacturable:
        refacturable_bool = refacturable == '1'
        queryset = queryset.filter(refacturable=refacturable_bool)
    
    # Appliquer le tri
    queryset = queryset.order_by(sort_by)
    
    # Construire la chaîne de requête pour la pagination
    query_params = []
    if status:
        query_params.append(f'status={status}')
    if expense_type:
        query_params.append(f'expense_type={expense_type}')
    if user_id:
        query_params.append(f'user={user_id}')
    if project:
        query_params.append(f'project={project}')
    if start_date:
        query_params.append(f'start_date={start_date}')
    if end_date:
        query_params.append(f'end_date={end_date}')
    if refacturable:
        query_params.append(f'refacturable={refacturable}')
    if sort_by != '-date':
        query_params.append(f'sort_by={sort_by}')
    
    query_string = '&'.join(query_params)
    
    # Calculer les statistiques
    stats = {
        'total_count': queryset.count(),
        'pending_count': queryset.filter(status='pending').count(),
        'approved_count': queryset.filter(status='approved').count(),
        'rejected_count': queryset.filter(status='rejected').count(),
        'total_amount': queryset.aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_amount': queryset.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0,
        'approved_amount': queryset.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    # Récupérer tous les utilisateurs pour le filtre
    all_users = User.objects.all().order_by('first_name', 'last_name')
    
    # Paginer les résultats
    paginator = Paginator(queryset, 10)  # 10 items par page
    page_number = request.GET.get('page', 1)
    expenses = paginator.get_page(page_number)
    
    context = {
        'expenses': expenses,
        'stats': stats,
        'filters': {
            'status': status,
            'expense_type': expense_type,
            'user_id': int(user_id) if user_id.isdigit() else None,
            'project': project,
            'start_date': start_date,
            'end_date': end_date,
            'refacturable': refacturable,
            'sort_by': sort_by,
            'query_string': query_string
        },
        'all_users': all_users
    }
    
    return render(request, 'rh_management/admin_expense_history.html', context)

@login_required
def submit_expense_report(request):
    """
    Vue pour soumettre une nouvelle note de frais
    """
    if request.method == 'POST':
        try:
            description = request.POST.get('description', '')
            amount = request.POST.get('amount', '')
            date = request.POST.get('date', '')
            category = request.POST.get('category', '')
            comments = request.POST.get('comments', '')
            
            if description and amount and date and category:
                # Convertir les données
                from datetime import datetime
                from decimal import Decimal
                
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                amount_decimal = Decimal(str(amount).replace(',', '.'))
                
                # Créer une nouvelle note de frais
                expense = ExpenseReport.objects.create(
                    user=request.user,
                    description=description,
                    amount=amount_decimal,
                    date=date_obj,
                    expense_type=category,  # Mapper category à expense_type
                    comment=comments,
                    status='pending'
                )
                
                # Créer une notification pour les RH
                for hr_user in User.objects.filter(is_staff=True):
                    Notification.objects.create(
                        user=hr_user,
                        title="Nouvelle note de frais",
                        message=f"{request.user.get_full_name() or request.user.username} a soumis une note de frais de {amount_decimal} €.",
                        notification_type='expense',
                        object_id=expense.id,
                        icon="fa-file-invoice-dollar",
                        color="warning",
                        url="/manage-expenses/"
                    )
                
                messages.success(request, 'Votre note de frais a été soumise avec succès.')
                return redirect('my_expenses')
            else:
                messages.error(request, 'Veuillez remplir tous les champs requis.')
        except Exception as e:
            messages.error(request, f'Erreur lors de la soumission: {str(e)}')
    
    context = {
        'page_title': 'Nouvelle note de frais'
    }
    return render(request, 'rh_management/submit_expense.html', context)
