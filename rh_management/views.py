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
from django.utils import timezone
from django.db.models import Avg, Sum
from .models import LeaveBalance, LeaveRequest
from .models import PasswordManager
from .forms import PasswordManagerForm
from django.contrib.auth.models import User, Group
from .models import PasswordShare
from datetime import datetime
from django.core.paginator import Paginator

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

# Ajouter ces fonctions après les fonctions d'autorisation existantes

def can_approve_leaves(user):
    """Vérifie si l'utilisateur peut approuver des congés."""
    return (is_admin_hr_or_encadrant(user) or 
            user.groups.filter(name="CanApproveLeaves").exists())

def can_edit_profiles(user):
    """Vérifie si l'utilisateur peut modifier des profils."""
    return (is_admin(user) or 
            user.groups.filter(name="CanEditProfiles").exists())

### 🌟 AUTHENTIFICATION ###

# ✅ Page d'accueil
def home_view(request):
    """Vue de la page d'accueil."""
    
    # Ajouter les compteurs des notifications manquants
    context = {
        'new_expense_reports_count': 0,
        'new_leave_requests_count': 0,
        'new_kilometric_expenses_count': 0,
    }
    
    # Si l'utilisateur est authentifié, calculer les compteurs réels
    if request.user.is_authenticated:
        # Vérifier si l'utilisateur est administrateur, RH ou encadrant
        is_admin = request.user.is_superuser
        is_rh = request.user.is_staff
        is_encadrant = request.user.groups.filter(name='Encadrant').exists()
        
        if is_admin or is_rh or is_encadrant:
            # Compter les nouvelles demandes de congé
            context['new_leave_requests_count'] = LeaveRequest.objects.filter(status='pending').count()
            
            # Compter les nouvelles notes de frais
            context['new_expense_reports_count'] = ExpenseReport.objects.filter(status='pending').count()
            
            # Compter les nouveaux frais kilométriques
            context['new_kilometric_expenses_count'] = KilometricExpense.objects.filter(status='pending').count()
            
        # Ajouter les flags de rôle au contexte pour les conditions dans le template
        context['is_admin'] = is_admin
        context['is_rh'] = is_rh
        context['is_encadrant'] = is_encadrant
    
    return render(request, 'rh_management/home.html', context)

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

    # Initialiser les variables de comptage des notifications à 0 pour les pages de connexion
    context = {
        'new_leave_requests_count': 0,
        'new_expense_reports_count': 0,
        'new_kilometric_expenses_count': 0,
        'is_admin': False,
        'is_rh': False,
        'is_encadrant': False,
    }
    
    return render(request, 'auth/login.html', context)

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
    user_to_edit = get_object_or_404(User, id=user_id)
    from django.contrib.auth.models import Group
    
    # Récupérer tous les groupes disponibles
    all_groups = Group.objects.all().order_by('name')
    
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        user_role = request.POST.get('user_role')
        
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
        user_to_edit.first_name = first_name
        user_to_edit.last_name = last_name
        
        # Gestion des rôles basée sur la sélection dans le formulaire
        user_to_edit.is_staff = False
        user_to_edit.is_superuser = False
        
        if user_role == 'admin':
            user_to_edit.is_staff = True
            user_to_edit.is_superuser = True
        elif user_role == 'rh':
            user_to_edit.is_staff = True
        
        user_to_edit.save()
        
        # Gérer les groupes basés sur le rôle
        user_to_edit.groups.clear()
        
        if user_role == 'rh':
            hr_group, _ = Group.objects.get_or_create(name='HR')
            user_to_edit.groups.add(hr_group)
        elif user_role == 'encadrant':
            encadrant_group, _ = Group.objects.get_or_create(name='Encadrant')
            user_to_edit.groups.add(encadrant_group)
        elif user_role == 'stp':
            stp_group, _ = Group.objects.get_or_create(name='STP')
            user_to_edit.groups.add(stp_group)
        elif user_role == 'user':
            employee_group, _ = Group.objects.get_or_create(name='Employé')
            user_to_edit.groups.add(employee_group)
        
        # Gestion des permissions spéciales
        if request.POST.get('can_approve_leaves') == 'on':
            can_approve_group, _ = Group.objects.get_or_create(name='CanApproveLeaves')
            user_to_edit.groups.add(can_approve_group)
            
        if request.POST.get('can_edit_profiles') == 'on':
            can_edit_group, _ = Group.objects.get_or_create(name='CanEditProfiles')
            user_to_edit.groups.add(can_edit_group)
        
        messages.success(request, f"L'utilisateur {username} a été mis à jour avec succès.")
        return redirect('manage_users')
    
    # Détermination du rôle actuel pour l'affichage
    current_role = 'user'
    if user_to_edit.is_superuser:
        current_role = 'admin'
    elif user_to_edit.is_staff:
        current_role = 'rh'
    elif user_to_edit.groups.filter(name="Encadrant").exists():
        current_role = 'encadrant'
    elif user_to_edit.groups.filter(name="STP").exists():
        current_role = 'stp'
    
    # Permissions spéciales
    has_approve_leaves = user_to_edit.groups.filter(name="CanApproveLeaves").exists()
    has_edit_profiles = user_to_edit.groups.filter(name="CanEditProfiles").exists()
    
    context = {
        'user': user_to_edit,
        'all_groups': all_groups,
        'user_groups': user_to_edit.groups.all(),
        'current_role': current_role,
        'user_permissions': {
            'can_approve_leaves': has_approve_leaves,
            'can_edit_profiles': has_edit_profiles
        }
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
    """Vue pour soumettre une demande de congé."""
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
@user_passes_test(is_admin_or_hr)
def manage_leave_balances(request):
    """Vue pour gérer les soldes de congés des employés."""
    leave_balances = LeaveBalance.objects.all().select_related('user')
    
    # Statistiques
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

# ✅ Gérer les congés en attente (RH et Encadrants)
@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
def manage_leaves_view(request):
    """Vue pour gérer les demandes de congés."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Vérifier les permissions
    is_admin = request.user.is_superuser
    is_hr = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    if not (is_admin or is_hr or is_encadrant):
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrer les demandes de congés selon le rôle de l'utilisateur
    if is_admin or is_hr:
        pending_leaves = LeaveRequest.objects.filter(status='pending').order_by('-created_at')
        processed_leaves = LeaveRequest.objects.exclude(status='pending').order_by('-updated_at')
    elif is_encadrant:
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
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    
    context = {
        'pending_leaves': pending_leaves,
        'user_leaves': user_leaves,
        'processed_leaves': processed_leaves,
        'is_admin': is_admin,
        'is_hr': is_hr,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_leaves.html', context)

@login_required
@user_passes_test(is_admin_hr_or_encadrant)  # Mise à jour pour inclure les encadrants
def manage_kilometric_expenses_view(request):
    """Gère l'affichage des notes de frais kilométriques en attente pour les RH et encadrants."""
    pending_count = KilometricExpense.objects.filter(status='pending')
    approved_count = KilometricExpense.objects.filter(status='approved').count()
    rejected_count = KilometricExpense.objects.filter(status='rejected').count()
    total_distance = sum(expense.distance for expense in pending_count)

    return render(request, 'rh_management/manage_kilometric_expenses.html', {'pending_count': pending_count, 'approved_count': approved_count, 'rejected_count': rejected_count, 'total_distance': total_distance})

# ✅ Approuver un congé
@login_required
@user_passes_test(can_approve_leaves)  # Utiliser la fonction can_approve_leaves au lieu de is_admin_hr_or_encadrant
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
@user_passes_test(can_approve_leaves)  # Utiliser la fonction can_approve_leaves au lieu de is_admin_hr_or_encadrant
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

### 🌟 GESTION DES NOTES DE FRAIS ###

# ✅ Soumettre une note de frais
@login_required
def submit_expense(request):
    """Vue pour soumettre une note de frais."""
    if request.method == 'POST':
        form = ExpenseReportForm(request.POST, request.FILES)
        if form.is_valid():
            # S'assurer que la pièce justificative est fournie
            if not request.FILES.get('attachment'):
                form.add_error('attachment', 'Une pièce justificative est requise.')
                return render(request, 'rh_management/submit_expense.html', {'form': form})
                
            # Vérifier la taille du fichier
            if request.FILES.get('attachment').size > 25 * 1024 * 1024:  # 25 Mo
                form.add_error('attachment', 'La taille du fichier ne doit pas dépasser 25 Mo.')
                return render(request, 'rh_management/submit_expense.html', {'form': form})
            
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            
            # Traiter les notifications
            notification_emails = request.POST.get('notification_emails', '').split(',')
            cc_emails = []
            bcc_emails = []
            
            for email in notification_emails:
                if email.startswith('bcc:'):
                    bcc_emails.append(email[4:])  # Enlever le préfixe 'bcc:'
                else:
                    cc_emails.append(email)
            
            # Envoyer l'email de notification
            if cc_emails or bcc_emails:
                subject = f"Nouvelle note de frais soumise par {request.user.get_full_name() or request.user.username}"
                message = f"""
                Une nouvelle note de frais a été soumise:
                
                Date: {expense.date}
                Description: {expense.description}
                Montant: {expense.amount} €
                Projet: {expense.project}
                Localisation: {expense.location}
                
                Veuillez vous connecter à l'application pour l'examiner.
                """
                
                send_mail(
                    subject,
                    message,
                    'noreply@rhcyber.com',
                    cc_emails,
                    bcc=bcc_emails
                )
            
            messages.success(request, "Votre note de frais a été soumise avec succès.")
            return redirect('dashboard')
    else:
        form = ExpenseReportForm()
    
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
@user_passes_test(is_admin)
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
@user_passes_test(is_admin)
def manage_users_view(request):
    """Vue pour la gestion des utilisateurs (administrateurs uniquement)."""
    if not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    # Filtrage des utilisateurs
    users = User.objects.all()
    
    # Filtres appliqués si présents dans la requête
    if 'q' in request.GET and request.GET['q']:
        query = request.GET['q']
        users = users.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        )
    
    if 'role' in request.GET and request.GET['role']:
        role = request.GET['role']
        if role == 'admin':
            users = users.filter(is_superuser=True)
        elif role == 'hr':
            users = users.filter(is_staff=True, is_superuser=False)
        elif role == 'encadrant':
            users = users.filter(groups__name='Encadrant')
        elif role == 'stp':
            users = users.filter(groups__name='STP')
        elif role == 'employee':
            # Filtrer les employés simples (pas d'autre rôle)
            users = users.exclude(is_superuser=True).exclude(is_staff=True).exclude(groups__name__in=['Encadrant', 'STP'])
    
    if 'status' in request.GET and request.GET['status']:
        status = request.GET['status']
        users = users.filter(is_active=(status == 'active'))
    
    # Pagination
    paginator = Paginator(users, 10)  # 10 utilisateurs par page
    page_number = request.GET.get('page', 1)
    users_page = paginator.get_page(page_number)
    
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
        'users': users_page,
        'all_groups': Group.objects.all(),
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_users.html', context)

@login_required
@user_passes_test(is_admin)
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
    """Vue pour changer le mot de passe."""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, "Le mot de passe actuel est incorrect.")
            return redirect('profile')
        
        if new_password != confirm_password:
            messages.error(request, "Les nouveaux mots de passe ne correspondent pas.")
            return redirect('profile')
        
        # Vérifier la complexité du mot de passe
        if len(new_password) < 8:
            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
            return redirect('profile')
            
        if not any(c.isupper() for c in new_password):
            messages.error(request, "Le mot de passe doit contenir au moins une lettre majuscule.")
            return redirect('profile')
            
        if not any(c.islower() for c in new_password):
            messages.error(request, "Le mot de passe doit contenir au moins une lettre minuscule.")
            return redirect('profile')
            
        if not any(c.isdigit() for c in new_password):
            messages.error(request, "Le mot de passe doit contenir au moins un chiffre.")
            return redirect('profile')
            
        if not any(not c.isalnum() for c in new_password):
            messages.error(request, "Le mot de passe doit contenir au moins un caractère spécial.")
            return redirect('profile')
        
        request.user.set_password(new_password)
        request.user.save()
        
        # Mettre à jour la session pour éviter la déconnexion
        update_session_auth_hash(request, request.user)
        
        messages.success(request, "Votre mot de passe a été modifié avec succès.")
        return redirect('profile')
    
    return redirect('profile')

### 🌟 GESTION DES RÔLES (ADMIN) ###
@login_required
@user_passes_test(is_admin)
def manage_roles_view(request):
    """Gère l'affichage et la création de rôles (Admin)."""
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    
    # Récupération de tous les groupes
    roles = Group.objects.all().order_by('name')
    
    # Récupération des permissions disponibles pour l'affichage
    available_permissions = Permission.objects.filter(
        content_type__app_label='rh_management'
    ).order_by('name')
    
    if request.method == "POST":
        role_name = request.POST.get('role_name')
        if role_name:
            # Vérifier que le rôle n'existe pas déjà
            if Group.objects.filter(name=role_name).exists():
                messages.error(request, f"Le rôle '{role_name}' existe déjà.")
            else:
                # Créer le nouveau rôle
                new_role = Group.objects.create(name=role_name)
                
                # Ajouter les permissions sélectionnées
                for permission_id in request.POST.getlist('permissions'):
                    permission = Permission.objects.get(id=permission_id)
                    new_role.permissions.add(permission)
                
                messages.success(request, f"Le rôle '{role_name}' a été créé avec succès.")
                return redirect('manage_roles')
        else:
            messages.error(request, "Le nom du rôle ne peut pas être vide.")
    
    return render(request, 'rh_management/manage_roles.html', {
        'roles': roles,
        'available_permissions': available_permissions
    })

@login_required
@user_passes_test(is_admin)
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

@login_required
def password_manager_list(request):
    """View to display all password entries for the logged-in user."""
    # Obtenir les mots de passe de l'utilisateur
    owned_passwords = PasswordManager.objects.filter(user=request.user).order_by('title')
    
    # Obtenir les mots de passe partagés avec l'utilisateur
    shared_passwords = PasswordManager.objects.filter(
        shares__shared_with=request.user
    ).order_by('title')
    
    # Regrouper par catégorie (mots de passe de l'utilisateur)
    categories = {}
    for pwd in owned_passwords:
        cat = pwd.category or "Non classé"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(pwd)
    
    # Regrouper les mots de passe partagés
    shared_categories = {}
    for pwd in shared_passwords:
        cat = pwd.category or "Non classé"
        if cat not in shared_categories:
            shared_categories[cat] = []
        shared_categories[cat].append(pwd)
    
    context = {
        'categories': categories,
        'shared_categories': shared_categories,
        'password_count': owned_passwords.count(),
        'shared_count': shared_passwords.count(),
    }
    return render(request, 'rh_management/password_manager.html', context)

@login_required
def password_manager_add(request):
    """View to add a new password entry."""
    if request.method == 'POST':
        form = PasswordManagerForm(request.POST, user=request.user)
        if form.is_valid():
            password_entry = form.save(commit=False)
            
            # Si la génération de mot de passe est activée, on génère un mot de passe
            if request.POST.get('generate_password') == 'on':
                length = int(request.POST.get('password_length', 16))
                password_entry.password = password_entry.generate_password(length)
            
            password_entry.save()
            messages.success(request, "Mot de passe ajouté avec succès.")
            return redirect('password_manager_list')
    else:
        form = PasswordManagerForm(user=request.user)
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
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
        'title': 'Ajouter un mot de passe',
        'is_add': True,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_form.html', context)  # Ajout du return manquant ici

@login_required
def password_manager_edit(request, pk):
    """View to edit an existing password entry."""
    # Vérifier si l'utilisateur est propriétaire ou a les droits d'édition
    try:
        password_entry = PasswordManager.objects.get(pk=pk, user=request.user)
        is_owner = True
    except PasswordManager.DoesNotExist:
        # Vérifier si partagé avec droits d'édition
        try:
            share = PasswordShare.objects.get(password_entry_id=pk, shared_with=request.user, can_edit=True)
            password_entry = share.password_entry
            is_owner = False
        except PasswordShare.DoesNotExist:
            messages.error(request, "Vous n'avez pas l'autorisation de modifier ce mot de passe.")
            return redirect('password_manager_list')
    
    if request.method == 'POST':
        form = PasswordManagerForm(request.POST, instance=password_entry, user=request.user)
        if form.is_valid():
            password_entry = form.save(commit=False)
            
            # Si la génération de mot de passe est activée, on génère un mot de passe
            if request.POST.get('generate_password') == 'on':
                length = int(request.POST.get('password_length', 16))
                password_entry.password = password_entry.generate_password(length)
            
            password_entry.save()
            messages.success(request, "Mot de passe mis à jour avec succès.")
            return redirect('password_manager_view', pk=pk)
    else:
        form = PasswordManagerForm(instance=password_entry, user=request.user)
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
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
        'title': 'Modifier un mot de passe',
        'is_add': False,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_form.html', context)

@login_required
def password_manager_delete(request, pk):
    """View to delete a password entry."""
    # Seulement le propriétaire peut supprimer
    password_entry = get_object_or_404(PasswordManager, pk=pk, user=request.user)
    
    if request.method == 'POST':
        password_entry.delete()
        messages.success(request, "Mot de passe supprimé avec succès.")
        return redirect('password_manager_list')
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    elif is_encadrant:
        team_members = User.objects.filter(team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'password_entry': password_entry,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_confirm_delete.html', context)

@login_required
def password_manager_view(request, pk):
    """View to see details of a password entry."""
    # Vérifier si c'est un mot de passe appartenant à l'utilisateur
    try:
        password_entry = PasswordManager.objects.get(pk=pk, user=request.user)
        is_owner = True
        can_edit = True
    except PasswordManager.DoesNotExist:
        # Vérifier si c'est un mot de passe partagé avec l'utilisateur
        try:
            share = PasswordShare.objects.get(password_entry_id=pk, shared_with=request.user)
            password_entry = share.password_entry
            is_owner = False
            can_edit = share.can_edit
        except PasswordShare.DoesNotExist:
            # Ni propriétaire ni partagé
            return redirect('password_manager_list')
    
    decrypted_password = password_entry.decrypt_password()
    
    # Récupérer les partages pour ce mot de passe (pour le propriétaire uniquement)
    shares = []
    if is_owner:
        shares = PasswordShare.objects.filter(password_entry=password_entry)
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh or is_encadrant:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    elif is_encadrant:
        team_members = User.objects.filter(team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'password_entry': password_entry,
        'decrypted_password': decrypted_password,
        'is_owner': is_owner,
        'can_edit': can_edit,
        'shares': shares,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_view.html', context)

@login_required
def password_share(request, pk):
    """Vue pour partager un mot de passe avec d'autres utilisateurs."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Récupérer le mot de passe
    try:
        password_entry = PasswordManager.objects.get(pk=pk)
        if password_entry.user != request.user and not request.user.is_superuser:
            messages.error(request, "Vous n'avez pas la permission de partager ce mot de passe.")
            return redirect('password_manager')
    except PasswordManager.DoesNotExist:
        messages.error(request, "Ce mot de passe n'existe pas.")
        return redirect('password_manager')
    
    # Liste des partages existants
    existing_shares = password_entry.shares.all()
    
    # Liste des utilisateurs disponibles pour le partage (exclure ceux qui ont déjà un partage)
    shared_users = existing_shares.values_list('shared_with', flat=True)
    available_users = User.objects.exclude(id__in=shared_users).exclude(id=request.user.id)
    
    if request.method == 'POST':
        # Traiter le formulaire de partage
        user_id = request.POST.get('user_id')
        can_edit = request.POST.get('permission') == 'edit'
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                PasswordShare.objects.create(
                    password_entry=password_entry,
                    shared_with=user,
                    can_edit=can_edit
                )
                messages.success(request, f"Mot de passe partagé avec {user.get_full_name() or user.username}.")
            except User.DoesNotExist:
                messages.error(request, "Utilisateur invalide.")
        
        # Traiter les suppressions de partage
        for key in request.POST:
            if key.startswith('delete_share_'):
                share_id = key.replace('delete_share_', '')
                try:
                    share = PasswordShare.objects.get(id=share_id, password_entry=password_entry)
                    share.delete()
                    messages.success(request, f"Partage supprimé pour {share.shared_with.get_full_name() or share.shared_with.username}.")
                except PasswordShare.DoesNotExist:
                    pass
        
        return redirect('password_share', pk=pk)
    
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
        # Assuming we're looking for users in the same team or department
        team_members = User.objects.filter(groups__in=request.user.groups.all())
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'password_entry': password_entry,
        'existing_shares': existing_shares,
        'available_users': available_users,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    # Assurez-vous que cette ligne est bien présente à la fin de la fonction
    return render(request, 'rh_management/password_share.html', context)

@login_required
def password_share_remove(request, share_id):
    """Remove a password share."""
    share = get_object_or_404(PasswordShare, pk=share_id, password_entry__user=request.user)
    password_id = share.password_entry.id
    user_name = share.shared_with.username
    
    share.delete()
    messages.success(request, f"Partage supprimé pour l'utilisateur {user_name}.")
    
    return redirect('password_manager_view', pk=password_id)

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
@user_passes_test(is_admin_or_hr)
def mass_action(request):
    """Handle mass actions on users like activate, deactivate, add to group, remove from group."""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')
        group_id = request.POST.get('group')
        
        if not user_ids:
            messages.error(request, "Aucun utilisateur sélectionné.")
            return redirect('manage_users')
        
        users = User.objects.filter(id__in=user_ids)
        
        if action == 'activate':
            users.update(is_active=True)
            messages.success(request, f"{len(users)} utilisateur(s) activé(s) avec succès.")
        
        elif action == 'deactivate':
            # Don't deactivate superusers unless the current user is a superuser
            if not request.user.is_superuser:
                users = users.exclude(is_superuser=True)
            users.update(is_active=False)
            messages.success(request, f"{len(users)} utilisateur(s) désactivé(s) avec succès.")
        elif action in ['add_group', 'remove_group'] and group_id:
            try:
                group = Group.objects.get(id=group_id)
                count = 0
                
                for user in users:
                    # Skip superusers for non-superuser admins
                    if user.is_superuser and not request.user.is_superuser:
                        continue
                        
                    if action == 'add_group':
                        user.groups.add(group)
                    else:  # remove_group
                        user.groups.remove(group)
                    
                    count += 1
                
                action_text = "ajouté au" if action == 'add_group' else "retiré du"
                messages.success(request, f"{count} utilisateur(s) {action_text} groupe '{group.name}' avec succès.")
            
            except Group.DoesNotExist:
                messages.error(request, "Le groupe spécifié n'existe pas.")
        
        else:
            messages.error(request, "Action non valide.")
    
    return redirect('manage_users')

@login_required
@user_passes_test(is_admin_or_hr)
def reset_password(request, user_id):
    """Reset a user's password to a default value and notify them."""
    user = get_object_or_404(User, id=user_id)
    
    # Générer un mot de passe aléatoire temporaire
    import random
    import string
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    # Définir le nouveau mot de passe
    user.set_password(temp_password)
    user.save()
    
    # Notifier l'utilisateur par message (dans une application réelle, envoyer un email)
    messages.success(request, f"Le mot de passe de {user.username} a été réinitialisé. Mot de passe temporaire: {temp_password}")
    
    # Redirection vers la page de gestion des utilisateurs
    return redirect('manage_users')

@login_required
@user_passes_test(is_admin_or_hr)
def toggle_user_status(request, user_id):
    """Active ou désactive un utilisateur."""
    user_to_modify = get_object_or_404(User, id=user_id)
    # Empêcher la désactivation d'un super-utilisateur par un non-super-utilisateur
    if user_to_modify.is_superuser and not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier le statut d'un administrateur.")
        return redirect('manage_users')
    
    # Empêcher la désactivation de son propre compte
    if user_to_modify == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        return redirect('manage_users')
    
    # Basculer le statut de l'utilisateur
    user_to_modify.is_active = not user_to_modify.is_active
    # Basculer le statut de l'utilisateur
    user_to_modify.is_active = not user_to_modify.is_active
    status_text = "activé" if user_to_modify.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user_to_modify.username} a été {status_text} avec succès.")
    
    return redirect('manage_users')

def password_manager(request):
    """Vue pour afficher la liste des mots de passe de l'utilisateur."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Récupérer les mots de passe propres à l'utilisateur
    user_passwords = PasswordManager.objects.filter(user=request.user)
    
    # Récupérer les mots de passe partagés avec l'utilisateur
    # Utiliser la relation "shares" au lieu de "passwordshare"
    shared_passwords = PasswordManager.objects.filter(
        shares__shared_with=request.user
    )
    
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
        # Filter users who have this user as their manager (adjust field name as per your model)
        team_members = User.objects.filter(userprofile__team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()

    context = {
        'user_passwords': user_passwords,
        'shared_passwords': shared_passwords,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_manager.html', context)

@login_required
def password_add(request):
    """Vue pour ajouter un nouveau mot de passe."""
    if request.method == 'POST':
        form = PasswordManagerForm(request.POST)
        if form.is_valid():
            password_entry = form.save(commit=False)
            password_entry.user = request.user
            
            # Générer une clé de chiffrement
            from cryptography.fernet import Fernet
            encryption_key = Fernet.generate_key()
            password_entry.encryption_key = encryption_key.decode('utf-8')
            
            password_entry.save()
            messages.success(request, "Mot de passe ajouté avec succès.")
            return redirect('password_manager')
    else:
        form = PasswordManagerForm()
    
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
        team_members = User.objects.filter(userprofile__team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'form': form,
        'title': 'Ajouter un mot de passe',
        'is_add': True,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_form.html', context)  # Ajout du return manquant ici

def password_view(request, pk):
    """Vue pour voir les détails d'un mot de passe."""
    if not request.user.is_authenticated:
        return redirect('login')
    # Récupérer le mot de passe
    try:
        password_entry = PasswordManager.objects.get(pk=pk)
        if password_entry.user != request.user and not request.user.is_superuser:
            # Vérifier si l'utilisateur a accès (partagé)
            shared = password_entry.shares.filter(shared_with=request.user).exists()
            if not shared:
                messages.error(request, "Vous n'avez pas la permission de voir ce mot de passe.")
                return redirect('password_manager')
    except PasswordManager.DoesNotExist:
        messages.error(request, "Ce mot de passe n'existe pas.")
        return redirect('password_manager')
    
    # Vérifier si l'utilisateur peut modifier (propriétaire, admin ou partagé avec droits d'édition)
    can_edit = (password_entry.user == request.user) or request.user.is_superuser
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
    elif is_encadrant:
        team_members = User.objects.filter(userprofile__team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'password_entry': password_entry,
        'can_edit': can_edit,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_view.html', context)  # Ajout du return manquant ici

def password_edit(request, pk):
    """Vue pour modifier un mot de passe existant."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Récupérer le mot de passe
    try:
        password_entry = PasswordManager.objects.get(pk=pk)
        if password_entry.user != request.user and not request.user.is_superuser:
            # Vérifier si l'utilisateur peut modifier (partagé avec droits d'édition)
            shared = password_entry.shares.filter(shared_with=request.user, can_edit=True).exists()
            if not shared:
                messages.error(request, "Vous n'avez pas la permission de modifier ce mot de passe.")
                return redirect('password_manager')
    except PasswordManager.DoesNotExist:
        messages.error(request, "Ce mot de passe n'existe pas.")
        return redirect('password_manager')
    
    if request.method == 'POST':
        form = PasswordManagerForm(request.POST, instance=password_entry)
        if form.is_valid():
            form.save()
            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect('password_manager')
    else:
        form = PasswordManagerForm(instance=password_entry)
    
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
        team_members = User.objects.filter(userprofile__team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'form': form,
        'title': 'Modifier un mot de passe',
        'is_add': False,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_form.html', context)

def password_delete(request, pk):
    """Vue pour supprimer un mot de passe."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Code pour supprimer un mot de passe
    # Ajouter les compteurs de notification au contexte
    # ...

def password_share(request, pk):
    """Vue pour partager un mot de passe avec d'autres utilisateurs."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Code pour partager un mot de passe
    # Ajouter les compteurs de notification au contexte
    # ...

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
