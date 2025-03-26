from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from ..models import LeaveRequest, ExpenseReport, KilometricExpense
from .permissions import is_admin

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
    
    # Ajouter les variables requises pour le template
    is_admin_flag = request.user.is_superuser
    is_rh_flag = request.user.is_staff
    is_encadrant_flag = request.user.groups.filter(name='Encadrant').exists()
    
    # Compteurs de notifications pour la navbar
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin_flag or is_rh_flag:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    elif is_encadrant_flag:
        team_members = User.objects.filter(team_leader=request.user)
        new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    context = {
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'auth/register.html', context)

def logout_view(request):
    """Gère la déconnexion de l'utilisateur."""
    logout(request)
    return redirect('login')
