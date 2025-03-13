from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import pandas as pd
from django.contrib.auth.models import User
from .forms import LeaveRequestForm, ExpenseReportForm, KilometricExpenseForm
from .models import LeaveRequest, ExpenseReport, KilometricExpense, UserProfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db.models import Q
from django.template.loader import render_to_string
import json
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password

# Vérifie si l'utilisateur est un admin ou un RH
def is_admin_or_hr(user):
    return user.is_staff or user.groups.filter(name="HR").exists()

# Vérifie si l'utilisateur est un employé
def is_employee(user):
    return user.groups.filter(name='Employé').exists()

# Nouvelles fonctions d'autorisation
def is_admin(user):
    return user.is_superuser

def is_rh(user):
    """Vérifie si l'utilisateur est RH."""
    # Amélioration pour détecter les RH soit par is_staff soit par appartenance au groupe HR
    return user.is_staff or user.groups.filter(name="HR").exists()

def is_encadrant(user):
    return user.groups.filter(name="Encadrant").exists()

def is_stp(user):
    return user.groups.filter(name="STP").exists()

# Fonctions d'autorisation améliorées
def is_admin_or_hr(user):
    """Vérifie si l'utilisateur est un admin ou un RH."""
    return user.is_superuser or user.is_staff or user.groups.filter(name="HR").exists()

def is_admin_hr_or_encadrant(user):
    """Vérifie si l'utilisateur est un admin, un RH ou un encadrant."""
    # Utiliser la fonction is_rh pour plus de cohérence
    return (user.is_superuser or 
            is_rh(user) or  # Utilisation de la fonction is_rh au lieu de la duplication de sa logique
            user.groups.filter(name__in=["HR", "Encadrant"]).exists())

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

# Restreindre la création de comptes aux administrateurs
@login_required
@user_passes_test(is_admin)
def register_view(request):
    """Gère l'inscription de l'utilisateur. Seuls les admins peuvent créer des comptes."""
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST.get('role', 'employe')  # Récupère le rôle sélectionné
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            from django.contrib.auth.models import Group
            if role == 'admin':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'rh':
                user.is_staff = True
                hr_group, _ = Group.objects.get_or_create(name='HR')
                user.groups.add(hr_group)
            elif role == 'encadrant':
                encadrant_group, _ = Group.objects.get_or_create(name='Encadrant')
                user.groups.add(encadrant_group)
            elif role == 'stp':
                stp_group, _ = Group.objects.get_or_create(name='STP')
                user.groups.add(stp_group)
            else:  # employé
                employe_group, _ = Group.objects.get_or_create(name='Employé')
                user.groups.add(employe_group)
            user.save()
            messages.success(request, "Inscription réussie. Le compte a été créé.")
            return redirect('manage_users')
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

    # Déterminer clairement les rôles de l'utilisateur
    is_superuser = request.user.is_superuser
    is_hr = is_rh(request.user)  # Utilisation de la fonction is_rh
    
    is_admin_flag = request.user.is_superuser
    is_rh_flag = is_rh(request.user)  # Utilisation cohérente de la même fonction
    is_encadrant_flag = is_encadrant(request.user)
    is_stp_flag = is_stp(request.user)
    is_employee_flag = (request.user.groups.filter(name="Employé").exists() or 
                       not (is_admin_flag or is_rh_flag or is_encadrant_flag or is_stp_flag))
    
    # Correction de la logique de détermination des demandes à afficher
    if is_admin_flag or is_rh_flag or is_encadrant_flag:  # Ajout explicite de is_encadrant_flag
        # Logique pour admins, RH et encadrants
        leave_requests = LeaveRequest.objects.all().order_by('-created_at')[:10]
        expense_reports = ExpenseReport.objects.all().order_by('-date')[:10]
        kilometric_expenses = KilometricExpense.objects.all().order_by('-date')[:10]
    else:
        # Logique pour employés
        leave_requests = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
        expense_reports = ExpenseReport.objects.filter(user=request.user).order_by('-date')
        kilometric_expenses = KilometricExpense.objects.filter(user=request.user).order_by('-date')

    context = {
        "is_admin": is_admin_flag,
        "is_rh": is_rh_flag,
        "is_encadrant": is_encadrant_flag,
        "is_stp": is_stp_flag,
        "is_employee": is_employee_flag,
        "leave_requests": leave_requests,
        "expense_reports": expense_reports,
        "kilometric_expenses": kilometric_expenses,
        "new_leave_requests_count": new_leave_requests_count,
        "new_expense_reports_count": new_expense_reports_count,
        "new_kilometric_expenses_count": new_kilometric_expenses_count,
    }
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
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Mise à jour des champs standard de User
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        
        # Mise à jour des champs de rôles standards
        user.is_staff = 'is_staff' in request.POST
        user.is_superuser = 'is_superuser' in request.POST
        user.save()
        
        # Mise à jour des rôles personnalisés
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.is_employee = 'is_employee' in request.POST
        profile.is_stp = 'is_stp' in request.POST
        profile.is_supervisor = 'is_supervisor' in request.POST
        profile.save()
        
        messages.success(request, "Utilisateur modifié avec succès.")
        return redirect('manage_users')
    
    # Pour l'affichage du formulaire
    try:
        profile = user.profile
        is_employee = profile.is_employee
        is_stp = profile.is_stp
        is_supervisor = profile.is_supervisor
    except UserProfile.DoesNotExist:
        is_employee = False
        is_stp = False
        is_supervisor = False
    
    context = {
        'user': user,
        'is_employee': is_employee,
        'is_stp': is_stp,
        'is_supervisor': is_supervisor,
        'is_in_hr': user.is_staff,
    }
    
    return render(request, 'rh_management/edit_user.html', context)

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
    
def is_hr(user):
    """Vérifie si l'utilisateur est RH (responsable des congés)."""
    return user.is_staff  # Seuls les RH peuvent approuver les congés

### 🌟 GESTION DES CONGÉS ###

# ✅ Demande de congé

@login_required
def leave_request_view(request):
    """Gère la demande de congé."""
    if request.method == "POST":
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.user = request.user
            leave_request.notification_emails = json.dumps([email.email for email in form.cleaned_data['notification_emails']])
            leave_request.save()
            
            # Envoi d'un email de notification pour validation
            notification_emails = form.cleaned_data['notification_emails']
            #if notification_emails:
            #    emails = [email.email for email in notification_emails]
            #    subject = "Nouvelle demande de congé soumise"
            #    message = f"Bonjour,\n\nUne nouvelle demande de congé a été soumise par {leave_request.user.username}. Veuillez la valider."
            #    send_mail(subject, message, 'no-reply@cyberun.info', emails)
            
            messages.success(request, "Votre demande de congé a été soumise avec succès.")
            return redirect('dashboard')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = LeaveRequestForm()

    return render(request, 'rh_management/leave_request.html', {'form': form})

# ✅ Gérer les congés en attente (RH et Encadrants)
@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
def manage_leaves_view(request):
    """Gère l'affichage des congés en attente pour les RH et encadrants."""
    pending_leaves = LeaveRequest.objects.filter(status='pending')
    return render(request, 'rh_management/manage_leaves.html', {'pending_leaves': pending_leaves})

# ✅ Approuver un congé
@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
        form = ExpenseReportForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.notification_emails = json.dumps([email.email for email in form.cleaned_data['notification_emails']])
            expense.save()
            
            # Envoi d'un email de notification pour validation
            notification_emails = form.cleaned_data['notification_emails']
            # if notification_emails:
            #    emails = [email.email for email in notification_emails]
            #    subject = "Nouvelle note de frais soumise"
            #    message = f"Bonjour,\n\nUne nouvelle note de frais a été soumise par {expense.user.username}. Veuillez la valider."
            #    send_mail(subject, message, 'no-reply@cyberun.info', emails)
            
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

# ✅ Gérer les notes de frais (RH et Encadrants)
@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
def manage_expenses_view(request):
    """Gère l'affichage des notes de frais en attente pour les RH et encadrants."""
    pending_expenses = ExpenseReport.objects.filter(status='pending')
    return render(request, 'rh_management/manage_expenses.html', {'pending_expenses': pending_expenses})

# ✅ Approuver une note de frais
@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
def edit_user(request, user_id):
    user_to_edit = get_object_or_404(User, id=user_id)
    from django.contrib.auth.models import Group
    
    # Récupérer tous les groupes disponibles
    all_groups = Group.objects.all().order_by('name')
    
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        
        # Vérifier si le nom d'utilisateur existe déjà pour un autre utilisateur
        if User.objects.exclude(id=user_id).filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà utilisé.")
            return redirect('edit_user', user_id=user_id)
        # Vérifier si l'email existe déjà pour un autre utilisateur
        if User.objects.exclude(id=user_id).filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return redirect('edit_user', user_id=user_id)
            
        # Mettre à jour l'utilisateur
        user_to_edit.username = username
        user_to_edit.email = email
        user_to_edit.is_staff = is_staff
        user_to_edit.is_superuser = is_superuser
        user_to_edit.save()
        
        # Gestion des groupes dynamique
        # D'abord, supprimer tous les groupes existants
        user_to_edit.groups.clear()
        
        # Ensuite, ajouter les groupes sélectionnés
        for group in all_groups:
            group_field = f"group_{group.id}"
            if request.POST.get(group_field) == 'on':
                user_to_edit.groups.add(group)
                print(f"DEBUG - Added {user_to_edit.username} to {group.name} group")
        
        # Gestion spéciale pour HR si is_staff est activé
        if is_staff:
            hr_group, _ = Group.objects.get_or_create(name='HR')
            user_to_edit.groups.add(hr_group)
        
        messages.success(request, f"L'utilisateur {username} a été mis à jour avec succès.")
        return redirect('manage_users')
    
    # Passage des informations de groupe au template
    user_groups = user_to_edit.groups.all()
    
    context = {
        'user': user_to_edit,
        'all_groups': all_groups,
        'user_groups': user_groups,
        'is_in_hr': user_to_edit.groups.filter(name="HR").exists(),
        'is_stp': user_to_edit.groups.filter(name="STP").exists(),
        'is_encadrant': user_to_edit.groups.filter(name="Encadrant").exists(),
    }
    return render(request, 'rh_management/edit_user.html', context)

@login_required
@user_passes_test(lambda user: user.is_superuser)
def delete_user(request, user_id):  # Renommé de delete_user_view à delete_user pour correspondre à l'import dans urls.py
    """Gère la suppression d'un utilisateur (Admin)."""
    user = User.objects.get(id=user_id)
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"L'utilisateur {username} a été supprimé avec succès.")
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
            
            expense.notification_emails = json.dumps([email.email for email in form.cleaned_data['notification_emails']])
            expense.save()
            
            # Envoi d'un email de notification pour validation
            notification_emails = form.cleaned_data['notification_emails']
            #if notification_emails:
            #    emails = [email.email for email in notification_emails]
            #    subject = "Nouvelle note de frais kilométrique soumise"
            #    message = f"Bonjour,\n\nUne nouvelle note de frais kilométrique a été soumise par {expense.user.username}. Veuillez la valider."
            #    send_mail(subject, message, 'no-reply@cyberun.info', emails)
            
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
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
def manage_kilometric_expenses(request):
    """Affiche tous les frais kilométriques pour validation (Admin/RH/Encadrants)."""
    expenses = KilometricExpense.objects.all().order_by("-date")
    return render(request, "rh_management/manage_kilometric_expenses.html", {"expenses": expenses})

@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
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
def delete_leave(request, id):
    leave = get_object_or_404(LeaveRequest, id=id)
    if request.user.is_superuser:
        leave.delete()
    return redirect('dashboard')

@login_required
def delete_expense(request, id):
    expense = get_object_or_404(ExpenseReport, id=id)
    if request.user.is_superuser:
        expense.delete()
    return redirect('dashboard')

@login_required
def delete_kilometric_expense(request, id):
    expense = get_object_or_404(KilometricExpense, id=id)
    if request.user.is_superuser:
        expense.delete()
    return redirect('dashboard')

### 🌟 GESTION DU PROFIL UTILISATEUR ###
@login_required
def profile_view(request):
    """Affiche la page de profil de l'utilisateur."""
    return render(request, 'rh_management/profile.html')

@login_required
def update_profile(request):
    """Met à jour les informations de profil de l'utilisateur."""
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        
        user = request.user
        
        # Pour les utilisateurs non-admin et non-RH, le nom d'utilisateur et l'email ne peuvent pas être modifiés
        if not user.is_superuser and not user.is_staff:
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour modifier ces informations.")
            return redirect('profile')
        
        # Vérifier si le nom d'utilisateur existe déjà
        if User.objects.exclude(id=user.id).filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà pris.")
            return redirect('profile')
            
        # Vérifier si l'email existe déjà
        if User.objects.exclude(id=user.id).filter(email=email).exists():
            messages.error(request, "Cette adresse email est déjà utilisée.")
            return redirect('profile')
        
        user.username = username
        user.email = email
        user.save()
        
        messages.success(request, "Votre profil a été mis à jour avec succès!")
        return redirect('profile')
    
    return redirect('profile')

@login_required
def change_password(request):
    """Permet à l'utilisateur de changer son mot de passe."""
    if request.method == "POST":
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        # Vérification du mot de passe actuel
        if not user.check_password(current_password):
            messages.error(request, "Le mot de passe actuel est incorrect.")
            return redirect('profile')
            
        # Vérification que les nouveaux mots de passe correspondent
        if new_password != confirm_password:
            messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            return redirect('profile')
            
        # Mettre à jour le mot de passe
        user.set_password(new_password)
        user.save()
        
        # Mettre à jour la session pour éviter la déconnexion
        update_session_auth_hash(request, user)
        
        messages.success(request, "Votre mot de passe a été changé avec succès!")
        return redirect('profile')
    
    return redirect('profile')

### 🌟 GESTION DES RÔLES (ADMIN) ###
@login_required
@user_passes_test(lambda user: user.is_superuser)
def manage_roles_view(request):
    """Gère l'affichage et la création de rôles (Admin)."""
    from django.contrib.auth.models import Group
    
    # Récupération de tous les groupes
    roles = Group.objects.all().order_by('name')
    
    if request.method == "POST":
        role_name = request.POST.get('role_name')
        if role_name:
            # Vérifier que le rôle n'existe pas déjà
            if Group.objects.filter(name=role_name).exists():
                messages.error(request, f"Le rôle '{role_name}' existe déjà.")
            else:
                # Créer le nouveau rôle
                Group.objects.create(name=role_name)
                messages.success(request, f"Le rôle '{role_name}' a été créé avec succès.")
                return redirect('manage_roles')
        else:
            messages.error(request, "Le nom du rôle ne peut pas être vide.")
    
    return render(request, 'rh_management/manage_roles.html', {'roles': roles})

@login_required
@user_passes_test(lambda user: user.is_superuser)
def delete_role(request, role_id):
    """Supprime un rôle existant (Admin)."""
    from django.contrib.auth.models import Group
    
    role = get_object_or_404(Group, id=role_id)
    
    if request.method == "POST":
        role_name = role.name
        
        # Vérifier si le rôle est un rôle système qu'on ne veut pas supprimer
        system_roles = ['HR', 'Encadrant', 'STP', 'Employé']
        if role_name in system_roles:
            messages.error(request, f"Le rôle '{role_name}' est un rôle système et ne peut pas être supprimé.")
            return redirect('manage_roles')
        
        # Supprimer le rôle
        role.delete()
        messages.success(request, f"Le rôle '{role_name}' a été supprimé avec succès.")
        return redirect('manage_roles')
    
    return render(request, 'rh_management/delete_role.html', {'role': role})