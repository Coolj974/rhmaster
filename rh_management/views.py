from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
import pandas as pd
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import LeaveRequest, ExpenseReport, KilometricExpense
from .forms import ExpenseReportForm, KilometricExpenseForm, ExpenseForm
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.mail import send_mail  # Ajoutez cette ligne

### 🌟 MAIL RH ###
mailrh = ['oti@cyberun.info']


# Vérifie si l'utilisateur est un admin ou un RH
def is_admin_or_hr(user):
    return user.is_staff or user.groups.filter(name="HR").exists()

# Vérifie si l'utilisateur est un employé
def is_employee(user):
    return user.groups.filter(name='Employé').exists()

### 🌟 AUTHENTIFICATION ###

# ✅ Page d'accueil
def home_view(request):
    """Affiche la page d'accueil."""
    return render(request, 'rh_management/home.html')

# ✅ Connexion
def login_view(request):
    """Gère la connexion de l'utilisateur."""
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, 'auth/login.html')

# ✅ Inscription
def register_view(request):
    """Gère l'inscription de l'utilisateur."""
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Inscription réussie. Vous pouvez maintenant vous connecter.")
            return redirect('login')

    return render(request, 'auth/register.html')


# ✅ Déconnexion
def logout_view(request):
    """Gère la déconnexion de l'utilisateur."""
    logout(request)
    return redirect('login')

### 🌟 TABLEAU DE BORD ###
@login_required
def dashboard_view(request):
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()

    context = {
        "is_admin": request.user.is_superuser,
        "is_hr": request.user.groups.filter(name='HR').exists(),
        "is_employee": request.user.groups.filter(name='Employé').exists(),
        "leave_requests": LeaveRequest.objects.all(),
        "expense_reports": ExpenseReport.objects.all(),
        "kilometric_expenses": KilometricExpense.objects.all(),
        "new_leave_requests_count": new_leave_requests_count,
        "new_expense_reports_count": new_expense_reports_count,
        "new_kilometric_expenses_count": new_kilometric_expenses_count,
    }
    return render(request, 'rh_management/dashboard.html', context)

from django.http import JsonResponse
from django.template.loader import render_to_string

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
            'leave_requests': render_to_string('rh_management/partials/leave_requests.html', {'leave_requests': leave_requests}),
            'expense_reports': render_to_string('rh_management/partials/expense_reports.html', {'expense_reports': expense_reports}),
            'kilometric_expense_reports': render_to_string('rh_management/partials/kilometric_expense_reports.html', {'kilometric_expenses': kilometric_expenses}),
        })

    return render(request, 'rh_management/dashboard.html', {
        'leave_requests': leave_requests,
        'expense_reports': expense_reports,
        'kilometric_expenses': kilometric_expenses,
        'is_hr': request.user.groups.filter(name='HR').exists(),
        'is_admin': request.user.is_superuser,
    })
    
def is_hr(user):
    """Vérifie si l'utilisateur est RH."""
    return user.is_staff  # Seuls les RH peuvent approuver les congés

### 🌟 GESTION DES CONGÉS ###
    return user.is_staff  # Seuls les RH peuvent approuver les congés

# ✅ Demande de congé
@login_required
def leave_request_view(request):
    """Gère la demande de congé."""
    if request.method == "POST":
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        reason = request.POST['reason']
        leave_type = request.POST['leave_type']

        leave_request = LeaveRequest.objects.create(
            user=request.user,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            leave_type=leave_type
        )

        # Envoi d'un email de notification pour validation
       # send_mail(
       #     subject="Nouvelle demande de congé soumise",
       #     message=f"Bonjour,\n\nUne nouvelle demande de congé a été soumise par {leave_request.user.username}. Veuillez la valider.",
       #     from_email=[leave.user.email],
       #     recipient_list=["rh@cyberun.info"]  # Remplacez par l'email du service RH
       # )

        messages.success(request, "Votre demande de congé a été soumise avec succès.")
        return redirect('dashboard')

    return render(request, 'rh_management/leave_request.html')

# ✅ Gérer les congés en attente (RH)
@login_required
@user_passes_test(is_hr)
def manage_leaves_view(request):
    """Gère l'affichage des congés en attente pour les RH."""
    pending_leaves = LeaveRequest.objects.filter(status='pending')
    return render(request, 'rh_management/manage_leaves.html', {'pending_leaves': pending_leaves})

# ✅ Approuver un congé
@login_required
@user_passes_test(is_hr)
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

# ✅ Rejeter un congé
@login_required
@user_passes_test(is_hr)
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

### 🌟 GESTION DES NOTES DE FRAIS ###

# ✅ Soumettre une note de frais
@login_required
def submit_expense(request):
    """Permet à un utilisateur de soumettre une note de frais."""
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            
            # Envoi d'un email de notification pour validation
           # send_mail(
           #     subject="Nouvelle note de frais soumise",
           #     message=f"Bonjour,\n\nUne nouvelle note de frais a été soumise par {expense.user.username}. Veuillez la valider.",
           #     from_email= expense.user.email,
           #     recipient_list= mailrh  # Remplacez par l'email du service RH
           # )
            
            messages.success(request, "Note de frais enregistrée avec succès.")
            return redirect("dashboard")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ExpenseReportForm()

    return render(request, "rh_management/submit_expense.html", {"form": form})

# ✅ Voir ses notes de frais
@login_required
def my_expenses_view(request):
    """Affiche les notes de frais de l'utilisateur connecté."""
    expenses = ExpenseReport.objects.filter(user=request.user)
    return render(request, 'rh_management/my_expenses.html', {'expenses': expenses})

# ✅ Gérer les notes de frais (RH)
@login_required
@user_passes_test(is_hr)
def manage_expenses_view(request):
    """Gère l'affichage des notes de frais en attente pour les RH."""
    pending_expenses = ExpenseReport.objects.filter(status='pending')
    return render(request, 'rh_management/manage_expenses.html', {'pending_expenses': pending_expenses})

# ✅ Approuver une note de frais
@login_required
@user_passes_test(is_hr)
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

# ✅ Rejeter une note de frais
@login_required
@user_passes_test(is_hr)
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

# ✅ Annuler note de frais
@login_required
def cancel_expense(request, expense_id):
    expense = get_object_or_404(ExpenseReport, id=expense_id, user=request.user)

    if expense.status == "pending":
        expense.delete()
        messages.success(request, "Votre note de frais a été annulée avec succès.")
    else:
        messages.error(request, "Vous ne pouvez annuler qu'une note de frais en attente.")

    return redirect("dashboard")

# ✅ Exporter les notes de frais en Excel
@login_required
@user_passes_test(lambda user: user.is_superuser)
def export_expenses(request):
    """Exporte les notes de frais de l'utilisateur en format Excel."""
    expenses = ExpenseReport.objects.filter(user=request.user)

    data = [
        [exp.date, exp.description, exp.amount, exp.currency, exp.get_status_display()]
        for exp in expenses
    ]

    df = pd.DataFrame(data, columns=["Date", "Description", "Montant", "Devise", "Statut"])

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="notes_de_frais.xlsx"'
    df.to_excel(response, index=False)

    return response

### 🌟 GESTION DES UTILISATEURS (ADMIN) ###
@login_required
@user_passes_test(lambda user: user.is_superuser)
def manage_users_view(request):
    """Gère l'affichage de tous les utilisateurs (Admin)."""
    users = User.objects.all()
    return render(request, 'rh_management/manage_users.html', {'users': users})

@login_required
@user_passes_test(lambda user: user.is_superuser)
def edit_user_view(request, user_id):
    """Gère la modification d'un utilisateur (Admin)."""
    user = User.objects.get(id=user_id)

    if request.method == "POST":
        user.username = request.POST['username']
        user.email = request.POST['email']
        user.is_staff = 'is_staff' in request.POST
        user.is_superuser = 'is_superuser' in request.POST
        user.save()
        return redirect('manage_users')

    return render(request, 'rh_management/edit_user.html', {'user': user})

@login_required
@user_passes_test(lambda user: user.is_superuser)
def delete_user_view(request, user_id):
    """Gère la suppression d'un utilisateur (Admin)."""
    user = User.objects.get(id=user_id)
    if request.method == "POST":
        user.delete()
        return redirect('manage_users')

    return render(request, 'rh_management/delete_user.html', {'user': user})

### 🌟 GESTION DES FRAIS KILOMÉTRIQUES ###
@login_required
def submit_kilometric_expense(request):
    """Soumet une note de frais kilométrique."""
    if request.method == "POST":
        form = KilometricExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            
            # Vérifier si l'utilisateur a coché "Aller-retour"
            aller_retour = request.POST.get("aller_retour", "off") == "on"
            if aller_retour:
                expense.distance *= 2  # Double la distance
            
            expense.save()
            
            # Envoi d'un email de notification pour validation
           # send_mail(
           #     subject="Nouvelle note de frais kilométrique soumise",
           #     message=f"Bonjour,\n\nUne nouvelle note de frais kilométrique a été soumise par {expense.user.username}. Veuillez la valider.",
           #     from_email="enkai@outlook.fr",
           #     recipient_list=["rh@cyberun.info"]  # Remplacez par l'email du service RH
           # )
            
            messages.success(request, "Frais kilométrique enregistré avec succès !")
            return redirect("my_kilometric_expenses")
    else:
        form = KilometricExpenseForm()

    return render(request, 'rh_management/submit_kilometric_expense.html', {'form': form})

@login_required
def my_kilometric_expenses(request):
    """Affiche les frais kilométriques de l'utilisateur."""
    expenses = KilometricExpense.objects.filter(user=request.user).order_by("-date")
    return render(request, "rh_management/my_kilometric_expenses.html", {"expenses": expenses})

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
@user_passes_test(is_admin_or_hr)
def manage_kilometric_expenses(request):
    """Affiche tous les frais kilométriques pour validation (Admin/RH)."""
    expenses = KilometricExpense.objects.all().order_by("-date")
    return render(request, "rh_management/manage_kilometric_expenses.html", {"expenses": expenses})

@login_required
@user_passes_test(is_admin_or_hr)
def approve_kilometric_expense(request, expense_id):
    """Approuve un frais kilométrique (Admin/RH)."""
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
@user_passes_test(is_admin_or_hr)
def reject_kilometric_expense(request, expense_id):
    """Rejette un frais kilométrique (Admin/RH)."""
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
@user_passes_test(is_admin_or_hr)
def edit_kilometric_expense(request, expense_id):
    """Modifie un frais kilométrique (Admin/RH)."""
    expense = get_object_or_404(KilometricExpense, id=expense_id)

    if request.method == "POST":
        form = KilometricExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect("manage_kilometric_expenses")
    else:
        form = KilometricExpenseForm(instance=expense)

    return render(request, "rh_management/edit_kilometric_expense.html", {"form": form, "expense": expense})