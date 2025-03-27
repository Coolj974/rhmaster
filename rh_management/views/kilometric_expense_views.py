from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db.models import Sum, Avg  # Ajout des imports nécessaires
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
            # Nettoyer et récupérer les premières valeurs non vides
            def clean_float(value_list):
                if not isinstance(value_list, list):
                    value_list = [value_list]
                # Prendre la première valeur non vide
                for value in value_list:
                    if value and value.strip():
                        return float(value.replace(',', '.'))
                return 0.0

            # Récupérer les données du POST
            post_data = {
                'departure_lat': clean_float(request.POST.getlist('departure_lat')),
                'departure_lng': clean_float(request.POST.getlist('departure_lng')),
                'arrival_lat': clean_float(request.POST.getlist('arrival_lat')),
                'arrival_lng': clean_float(request.POST.getlist('arrival_lng')),
                'distance': clean_float(request.POST.getlist('distance')),
                'amount': clean_float(request.POST.getlist('amount'))
            }

            # Créer l'objet KilometricExpense
            expense = KilometricExpense(
                user=request.user,
                date=request.POST.get('date'),
                vehicle_type=request.POST.get('vehicle_type'),
                fiscal_power=int(request.POST.get('fiscal_power', 0)),
                departure=request.POST.get('departure', ''),
                departure_lat=post_data['departure_lat'],
                departure_lng=post_data['departure_lng'],
                arrival=request.POST.get('arrival', ''),
                arrival_lat=post_data['arrival_lat'],
                arrival_lng=post_data['arrival_lng'],
                distance=post_data['distance'],
                amount=post_data['amount'],
                project=request.POST.get('project', ''),
                status='pending',
                notification_emails=request.POST.get('notification_emails', '')
            )

            # Debug - afficher les valeurs avant sauvegarde
            print("Debug - Données nettoyées:", {
                'distance': post_data['distance'],
                'amount': post_data['amount'],
                'departure_lat': post_data['departure_lat'],
                'departure_lng': post_data['departure_lng'],
                'arrival_lat': post_data['arrival_lat'],
                'arrival_lng': post_data['arrival_lng']
            })

            expense.save()
            messages.success(request, "Votre demande de remboursement kilométrique a été soumise avec succès.")
            return redirect('dashboard')

        except (ValueError, TypeError) as e:
            print(f"Debug - Erreur : {str(e)}, POST data : {request.POST}")
            messages.error(request, f"Erreur de format dans les données : {str(e)}")
            return redirect('submit_kilometric_expense')

    # Ajout des compteurs de notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    # Si l'utilisateur est admin, RH ou encadrant, calculer les notifications
    if request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='Encadrant').exists():
        from ..models import LeaveRequest, ExpenseReport
        if request.user.is_superuser or request.user.is_staff:
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif request.user.groups.filter(name='Encadrant').exists():
            team_members = User.objects.filter(team_leader=request.user)
            new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()

    # Affichage du formulaire (GET)
    form = KilometricExpenseForm()
    context = {
        'form': form,
        'is_admin': request.user.is_superuser,
        'is_rh': request.user.is_staff,
        'is_encadrant': request.user.groups.filter(name='Encadrant').exists(),
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
    """Affiche tous les frais kilométriques pour validation."""
    expenses = KilometricExpense.objects.all().order_by('-date')
    
    # Forcer le calcul des montants
    for expense in expenses:
        if not expense.amount or expense.amount == 0:
            expense.amount = expense.calculate_amount()
            expense.save()
    
    # Recalculer les totaux
    total_stats = expenses.aggregate(
        total_distance=Sum('distance'),
        total_amount=Sum('amount')
    )
    
    context = {
        'expenses': expenses,
        'pending_count': expenses.filter(status='pending').count(),
        'total_distance': float(total_stats['total_distance'] or 0),
        'total_amount': float(total_stats['total_amount'] or 0),
        'average_distance': float(total_stats['total_distance'] or 0) / expenses.count() if expenses.exists() else 0,
        'new_leave_requests_count': LeaveRequest.objects.filter(status='pending').count(),
        'new_expense_reports_count': ExpenseReport.objects.filter(status='pending').count(),
        'new_kilometric_expenses_count': expenses.filter(status='pending').count(),
        'is_admin': request.user.is_superuser,
        'is_rh': request.user.is_staff,
        'is_encadrant': request.user.groups.filter(name='Encadrant').exists(),
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

@login_required
def cancel_kilometric_expense(request, expense_id):
    """Annule une demande de frais kilométriques."""
    expense = get_object_or_404(KilometricExpense, id=expense_id, user=request.user)
    
    if expense.status == 'pending':
        expense.delete()
        messages.success(request, "Vos frais kilométriques ont été annulés avec succès.")
    else:
        messages.error(request, "Vous ne pouvez annuler que des frais en attente de validation.")
    
    return redirect('dashboard')
