from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from datetime import datetime
import json
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from ..models import KilometricExpense, LeaveRequest, ExpenseReport
from ..forms import KilometricExpenseForm
from .permissions import is_admin_or_hr, is_admin_hr_or_encadrant

def get_kilometric_rate(vehicle_type):
    """Return the kilometric rate based on the vehicle type."""
    rates = {
        'car': 0.603,  # Standard rate for cars
        'motorcycle': 0.368,  # Rate for motorcycles
        'bicycle': 0.25,  # Rate for bicycles
        # Add more vehicle types and rates as needed
    }
    return rates.get(vehicle_type.lower(), 0.0)  # Default to 0.0 if vehicle type not found

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def manage_kilometric_expenses_view(request):
    """Gère l'affichage des notes de frais kilométriques en attente pour les RH et encadrants."""
    pending_count = KilometricExpense.objects.filter(status='pending')
    approved_count = KilometricExpense.objects.filter(status='approved').count()
    rejected_count = KilometricExpense.objects.filter(status='rejected').count()
    total_distance = sum(expense.distance for expense in pending_count)

    return render(request, 'rh_management/manage_kilometric_expenses.html', {'pending_count': pending_count, 'approved_count': approved_count, 'rejected_count': rejected_count, 'total_distance': total_distance})

@login_required
def submit_kilometric_expense(request):
    """Vue pour soumettre un frais kilométrique."""
    if request.method == "POST":
        try:
            # Récupérer les données du formulaire
            travel_date = request.POST.get('travel_date')
            kilometers = request.POST.get('kilometers')
            origin = request.POST.get('origin')
            destination = request.POST.get('destination')
            purpose = request.POST.get('purpose')
            vehicle_type = request.POST.get('vehicle_type')
            
            # Validation des données
            if not all([travel_date, kilometers, origin, destination, vehicle_type]):
                messages.error(request, "Veuillez remplir tous les champs obligatoires.")
                return redirect('submit_kilometric_expense')
            
            # Conversion des valeurs
            travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
            kilometers = float(str(kilometers).replace(',', '.'))
            
            if kilometers <= 0:
                messages.error(request, "Le kilométrage doit être supérieur à zéro.")
                return redirect('submit_kilometric_expense')
            
            # Calculer le montant en fonction du type de véhicule et du kilométrage
            rate = get_kilometric_rate(vehicle_type)
            amount = kilometers * rate
            
            # Créer le frais kilométrique
            kilometric = KilometricExpense(
                user=request.user,
                travel_date=travel_date,
                kilometers=kilometers,
                origin=origin,
                destination=destination,
                purpose=purpose,
                vehicle_type=vehicle_type,
                amount=amount,
                status='pending'
            )
            
            # Gérer le téléchargement du justificatif
            if 'proof' in request.FILES:
                proof = request.FILES['proof']
                
                # Vérifier la taille du fichier
                if proof.size > 5 * 1024 * 1024:  # 5 Mo
                    messages.error(request, "Le justificatif ne doit pas dépasser 5 Mo.")
                    return redirect('submit_kilometric_expense')
                
                # Vérifier le type de fichier
                allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
                if proof.content_type not in allowed_types:
                    messages.error(request, "Format de fichier non autorisé. Utilisez PDF, JPEG ou PNG.")
                    return redirect('submit_kilometric_expense')
                
                kilometric.proof = proof
            
            # Enregistrer le frais kilométrique
            kilometric.save()
            
            messages.success(request, "Votre frais kilométrique a été soumis avec succès.")
            return redirect('my_kilometric_expenses')
            
        except ValueError:
            messages.error(request, "Format de kilométrage ou de date invalide.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
    
    # Create an instance of the form for GET requests
    form = KilometricExpenseForm()
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
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
        'form': form,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/submit_kilometric_expense.html', context)

@login_required
def my_kilometric_expenses(request):
    """Affiche les frais kilométriques de l'utilisateur."""
    expenses = KilometricExpense.objects.filter(user=request.user).order_by("-date")
    return render(request, "rh_management/my_kilometric_expenses.html", {"expenses": expenses})

@login_required
@user_passes_test(is_admin_or_hr)
def export_expenses_excel(request):
    """Exporte les frais kilométriques en Excel (Admin/RH)."""
    expenses = KilometricExpense.objects.all().values(
        "user__username", "date", "vehicle_type", "fiscal_power",
        "departure", "arrival", "distance", "amount", "project", "status"
    )

    df = pd.DataFrame(expenses)
    df.rename(columns={
        "user__username": "Employé",
        "date": "Date",
        "vehicle_type": "Type de véhicule",
        "fiscal_power": "Puissance fiscale",
        "departure": "Départ",
        "arrival": "Arrivée",
        "distance": "Distance (km)",
        "amount": "Montant (€)",
        "project": "Projet",
        "status": "Statut"
    }, inplace=True)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=frais_kilométriques.xlsx"

    df.to_excel(response, index=False, engine="openpyxl")
    return response

@login_required
@user_passes_test(is_admin_or_hr)
def export_expenses_pdf(request):
    """Exporte les frais kilométriques en PDF (Admin/RH)."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=frais_kilométriques.pdf"

    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica", 12)

    p.drawString(100, 750, "Rapport des Frais Kilométriques")
    p.drawString(100, 730, "-----------------------------------")

    y = 710
    expenses = KilometricExpense.objects.all()

    for expense in expenses:
        p.drawString(100, y,
                     f"{expense.date} | {expense.user.username} | {expense.project} | {expense.distance} km | {expense.amount} € | {expense.status}")
        y -= 20

        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 750

    p.save()
    return response

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def manage_kilometric_expenses(request):
    """Affiche tous les frais kilométriques pour validation (Admin/RH/Encadrants)."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists()):
        messages.error(request, "Vous n'avez pas les droits nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrer les dépenses en fonction du rôle de l'utilisateur
    if request.user.is_superuser or request.user.is_staff:
        expenses = KilometricExpense.objects.all().order_by('-date')
    else:  # Encadrant
        team_members = User.objects.filter(team_leader=request.user)
        expenses = KilometricExpense.objects.filter(user__in=team_members).order_by('-date')
    
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
        'expenses': expenses,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_kilometric_expenses.html', context)

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def approve_kilometric_expense(request, expense_id):
    """Approuve un frais kilométrique (Admin/RH/Encadrants)."""
    expense = get_object_or_404(KilometricExpense, id=expense_id)
    expense.status = "approved"
    expense.save()

   # send_mail(
   #     subject="Votre frais kilométrique a été approuvé",
   #     message=f"Bonjour {expense.user.username},\n\nVotre frais kilométrique de {expense.distance} km a été approuvé.",
   #     from_email="no-reply@cyberun.info",
   #     recipient_list=[expense.user.email]
   # )

    return redirect("manage_kilometric_expenses")

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def reject_kilometric_expense(request, expense_id):
    """Rejette un frais kilométrique (Admin/RH/Encadrants)."""
    expense = get_object_or_404(KilometricExpense, id=expense_id)
    expense.status = "rejected"
    expense.save()

   # send_mail(
   #     subject="Votre frais kilométrique a été refusé",
   #     message=f"Bonjour {expense.user.username},\n\nVotre frais kilométrique de {expense.distance} km a été refusé.",
   #     from_email="enkai@outlook.fr",
   #     recipient_list=[expense.user.email]
   # )

    return redirect("manage_kilometric_expenses")

@login_required
@user_passes_test(is_admin_hr_or_encadrant)
def edit_kilometric_expense(request, expense_id):
    """Modifie un frais kilométrique (Admin/RH/Encadrants)."""
    expense = get_object_or_404(KilometricExpense, id=expense_id)

    if request.method == "POST":
        form = KilometricExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect("manage_kilometric_expenses")
    else:
        form = KilometricExpenseForm(instance=expense)

    return render(request, "rh_management/edit_kilometric_expense.html", {"form": form, "expense": expense})

@login_required
def delete_kilometric_expense(request, id):
    expense = get_object_or_404(KilometricExpense, id=id)
    if request.user.is_superuser:
        expense.delete()
    return redirect('dashboard')

@login_required
def kilometric_expense_action(request, expense_id):
    """
    Vue pour gérer les actions sur les frais kilométriques (approbation/rejet avec commentaire).
    Permet d'ajouter un commentaire lors de l'approbation ou du rejet d'une demande.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists()):
        messages.error(request, "Vous n'avez pas les droits nécessaires pour effectuer cette action.")
        return redirect('dashboard')
    
    # Récupérer la demande de frais kilométriques
    try:
        expense = KilometricExpense.objects.get(id=expense_id)
    except KilometricExpense.DoesNotExist:
        messages.error(request, "La demande de frais kilométriques n'existe pas.")
        return redirect('manage_kilometric_expenses')
    
    # Traiter la demande si c'est un POST
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            # Approuver la demande
            expense.status = 'approved'
            expense.comment = comment
            expense.save()
            
            messages.success(request, "La demande de frais kilométriques a été approuvée.")
        elif action == 'reject':
            # Rejeter la demande
            expense.status = 'rejected'
            expense.comment = comment
            expense.save()
            messages.success(request, "La demande de frais kilométriques a été rejetée.")
        else:
            messages.error(request, "Action non reconnue.")
            
    return redirect('manage_kilometric_expenses')
