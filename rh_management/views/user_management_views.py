from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.core.paginator import Paginator
import random
import string
from ..models import LeaveRequest, ExpenseReport, KilometricExpense
from .permissions import is_admin, is_admin_or_hr, can_edit_profiles, is_rh, is_encadrant

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
    is_admin_flag = request.user.is_superuser
    is_rh_flag = request.user.is_staff
    is_encadrant_flag = request.user.groups.filter(name='Encadrant').exists()
    
    # Compter les notifications
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
        'users': users_page,
        'all_groups': Group.objects.all(),
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/manage_users.html', context)

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Gère la suppression d'un utilisateur (Admin)."""
    user = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"L'utilisateur {username} a été supprimé avec succès.")
        return redirect('manage_users')

    return render(request, 'rh_management/delete_user.html', {'user': user})

@login_required
def edit_user(request, user_id):
    """Vue pour modifier un utilisateur existant."""
    user = get_object_or_404(User, id=user_id)
    is_owner = request.user == user
    
    # Groupes dont l'utilisateur fait partie
    user_groups = user.groups.all()
    
    # Tous les groupes disponibles
    all_groups = Group.objects.all()
    
    # Déterminer le rôle actuel
    current_role = 'employee'  # Par défaut
    if user.is_superuser:
        current_role = 'admin'
    elif user.is_staff:
        current_role = 'rh'
    elif user.groups.filter(name='Encadrant').exists():
        current_role = 'encadrant'
    elif user.groups.filter(name='STP').exists():
        current_role = 'stp'
    
    # Permissions spécifiques
    user_permissions = {
        'can_approve_leaves': user.has_perm('rh_management.approve_leave'),
        'can_edit_profiles': user.has_perm('rh_management.change_userprofile'),
    }
    
    # Ajouter les compteurs de notifications
    is_admin_flag = request.user.is_superuser
    is_rh_flag = is_rh(request.user)
    is_encadrant_flag = is_encadrant(request.user)
    
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
    
    if request.method == 'POST':
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
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        
        # Seuls les admins peuvent modifier les rôles de superuser et staff
        if request.user.is_superuser:
            # Gestion des rôles basée sur la sélection dans le formulaire
            user.is_staff = False
            user.is_superuser = False
            
            if user_role == 'admin':
                user.is_staff = True
                user.is_superuser = True
            elif user_role == 'rh':
                user.is_staff = True
        
        user.save()
        
        # Seuls les admins peuvent modifier les groupes
        if request.user.is_superuser:
            # Gérer les groupes basés sur le rôle
            user.groups.clear()
            
            if user_role == 'rh':
                hr_group, _ = Group.objects.get_or_create(name='HR')
                user.groups.add(hr_group)
            elif user_role == 'encadrant':
                encadrant_group, _ = Group.objects.get_or_create(name='Encadrant')
                user.groups.add(encadrant_group)
            elif user_role == 'stp':
                stp_group, _ = Group.objects.get_or_create(name='STP')
                user.groups.add(stp_group)
            elif user_role == 'user':
                employee_group, _ = Group.objects.get_or_create(name='Employé')
                user.groups.add(employee_group)
            
            # Gestion des permissions spéciales
            if request.POST.get('can_approve_leaves') == 'on':
                can_approve_group, _ = Group.objects.get_or_create(name='CanApproveLeaves')
                user.groups.add(can_approve_group)
                
            if request.POST.get('can_edit_profiles') == 'on':
                can_edit_group, _ = Group.objects.get_or_create(name='CanEditProfiles')
                user.groups.add(can_edit_group)
        
        messages.success(request, f"L'utilisateur {username} a été mis à jour avec succès.")
        
        # Rediriger vers la liste des utilisateurs pour les admins, ou vers le profil pour les autres
        if request.user.is_superuser:
            return redirect('manage_users')
        else:
            return redirect('profile')
    
    context = {
        'user': user,
        'all_groups': all_groups,
        'user_groups': user_groups,
        'current_role': current_role,
        'user_permissions': user_permissions,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'is_owner': is_owner,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/edit_user.html', context)

@login_required
@user_passes_test(is_admin_or_hr)
def reset_password(request, user_id):
    """Reset a user's password to a default value and notify them."""
    user = get_object_or_404(User, id=user_id)
    
    # Empêcher la réinitialisation pour les superusers par des non-superusers
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas l'autorisation de réinitialiser le mot de passe d'un administrateur.")
        return redirect('manage_users')
    
    # Générer un mot de passe aléatoire temporaire
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
    user_to_modify.save()
    
    status_text = "activé" if user_to_modify.is_active else "désactivé"
    messages.success(request, f"L'utilisateur {user_to_modify.username} a été {status_text} avec succès.")
    
    return redirect('manage_users')

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
            
            # Exclude current user
            users = users.exclude(id=request.user.id)
            
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
@user_passes_test(is_admin)
def manage_roles_view(request):
    """Gère l'affichage et la création de rôles (Admin)."""
    from django.contrib.auth.models import Permission
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
    
    # Ajouter les compteurs de notifications au contexte
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    
    context = {
        'roles': roles,
        'available_permissions': available_permissions,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
        'is_admin': True  # Comme on est dans une vue qui nécessite is_admin, on peut mettre True directement
    }
    
    return render(request, 'rh_management/manage_roles.html', context)

@login_required
@user_passes_test(is_admin)
def delete_role(request, role_id):
    """Supprime un rôle existant (Admin)."""
    role = get_object_or_404(Group, id=role_id)
    
    if request.method == "POST":
        role_name = role.name
        
        # Vérifier si le rôle est un rôle système qu'on ne veut pas supprimer
        system_roles = ['HR', 'Encadrant', 'STP', 'Employé', 'CanApproveLeaves', 'CanEditProfiles']
        if role_name in system_roles:
            messages.error(request, f"Le rôle '{role_name}' est un rôle système et ne peut pas être supprimé.")
            return redirect('manage_roles')
        
        # Supprimer le rôle
        role.delete()
        messages.success(request, f"Le rôle '{role_name}' a été supprimé avec succès.")
        return redirect('manage_roles')
    
    return render(request, 'rh_management/delete_role.html', {'role': role})
