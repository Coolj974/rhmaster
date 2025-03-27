from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.core.mail import send_mail
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
from ..models import ExpenseReport, LeaveRequest, KilometricExpense
from ..forms import ExpenseReportForm
from .permissions import is_admin_hr_or_encadrant, is_admin
import pandas as pd

@login_required
def submit_expense(request):
    """Vue pour soumettre une note de frais."""
    # Initialiser le formulaire au début de la fonction
    form = ExpenseReportForm()
    
    if request.method == "POST":
        try:
            # Récupérer les données du formulaire
            expense_date = request.POST.get('expense_date')
            amount = request.POST.get('amount')
            category = request.POST.get('category')
            description = request.POST.get('description')
            
            # Validation des données
            if not all([expense_date, amount, category]):
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
                return redirect('submit_expense')
                
            # Convertir la date et le montant
            expense_date = datetime.strptime(expense_date, '%Y-%m-%d').date()
            amount = Decimal(str(amount).replace(',', '.'))
            
            if amount <= 0:
                messages.error(request, "Le montant doit être supérieur à zéro.")
                return redirect('submit_expense')
            
            # Créer la note de frais avec les noms de champs corrects du modèle
            expense = ExpenseReport(
                user=request.user,
                date=expense_date,  # Champ corrigé de 'expense_date' à 'date'
                amount=amount,
                expense_type=category,  # Champ corrigé de 'category' à 'expense_type'
                description=description,
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
            
            # Enregistrer la note de frais
            expense.save()
            
            messages.success(request, "Votre note de frais a été soumise avec succès.")
            return redirect('my_expenses')  # Changé de 'my_expenses_view' à 'my_expenses'
        
        except ValueError:
            messages.error(request, "Format de montant ou de date invalide.")
        except Exception as e:
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
            from django.contrib.auth.models import User
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
        from ..models import LeaveRequest, KilometricExpense
        if is_admin or is_rh:
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif is_encadrant:
            from django.contrib.auth.models import User
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
        from django.contrib.auth.models import User
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
        from django.contrib.auth.models import User
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
