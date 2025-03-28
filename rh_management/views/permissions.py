from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from functools import wraps
from ..models import CustomPermission, PermissionGroup

# Fonctions de vérification des permissions
def is_admin_or_hr(user):
    """Vérifie si l'utilisateur est un admin ou un RH."""
    return user.is_superuser or user.is_staff

def is_employee(user):
    """Vérifie si l'utilisateur est un employé."""
    return user.groups.filter(name='Employé').exists()

def is_admin(user):
    """Vérifie si l'utilisateur est un administrateur."""
    return user.is_superuser

def is_rh(user):
    """Vérifie si l'utilisateur est RH."""
    return user.is_staff or user.groups.filter(name="RH").exists()

def is_encadrant(user):
    """Vérifie si l'utilisateur est encadrant."""
    return user.groups.filter(name="Encadrant").exists()

def is_stp(user):
    """Vérifie si l'utilisateur est STP."""
    return user.groups.filter(name="STP").exists()

# Cette fonction manquante était utilisée par leave_views.py
def is_admin_hr_or_encadrant(user):
    """Vérifie si l'utilisateur est un admin, un RH ou un encadrant."""
    return user.is_superuser or user.is_staff or user.groups.filter(name='Encadrant').exists()

def can_approve_leaves(user):
    """Vérifie si l'utilisateur peut approuver des congés."""
    return is_admin_hr_or_encadrant(user)

def can_approve_request(approver, requester):
    """
    Vérifie si un utilisateur peut approuver la demande d'un autre utilisateur
    selon les règles métier :
    - RH peut approuver les demandes des Employés
    - Encadrant peut approuver les demandes des STP
    - Admin peut tout approuver
    """
    if is_admin(approver):
        return True
        
    if is_rh(approver) and is_employee(requester):
        return True
        
    if is_encadrant(approver) and is_stp(requester):
        return True
        
    return False

def can_approve_leave(user, leave_request):
    """Vérifie si l'utilisateur peut approuver cette demande de congés."""
    return can_approve_request(user, leave_request.user)

def can_approve_expense(user, expense):
    """Vérifie si l'utilisateur peut approuver cette note de frais."""
    return can_approve_request(user, expense.user)

def can_approve_kilometric_expense(user, expense):
    """Vérifie si l'utilisateur peut approuver ces frais kilométriques."""
    return can_approve_request(user, expense.user)

def can_edit_profiles(user):
    """Vérifie si l'utilisateur peut modifier des profils."""
    # Les administrateurs, RH et encadrants peuvent modifier les profils
    return (is_admin(user) or 
            is_rh(user) or 
            is_encadrant(user) or
            user.groups.filter(name="CanEditProfiles").exists())

def has_permission(user, codename):
    """Vérifie si l'utilisateur a une permission spécifique."""
    # Vérifier si l'utilisateur est superuser
    if user.is_superuser:
        return True
        
    # Vérifier les groupes personnalisés
    user_groups = PermissionGroup.objects.filter(users=user)
    return CustomPermission.objects.filter(
        permissiongroup__in=user_groups,
        codename=codename
    ).exists()

def get_user_permissions(user):
    """Récupère toutes les permissions d'un utilisateur."""
    if user.is_superuser:
        return CustomPermission.objects.all()
        
    return CustomPermission.objects.filter(
        permissiongroup__users=user
    ).distinct()

def user_is_hr_or_admin(view_func):
    """
    Décorateur pour restreindre l'accès aux utilisateurs RH ou administrateurs.
    Redirige vers la page d'accueil si l'utilisateur n'a pas les droits.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Vérifier si l'utilisateur est admin ou appartient au groupe RH
        is_admin = request.user.is_staff or request.user.is_superuser
        is_hr = request.user.groups.filter(name='RH').exists()
        
        if is_admin or is_hr:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
            return redirect('dashboard')
    
    return _wrapped_view
