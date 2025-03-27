from django.contrib.auth.models import User, Group
from django.shortcuts import redirect
from django.contrib import messages

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
    # Amélioration pour détecter les RH soit par is_staff soit par appartenance au groupe HR
    return user.is_staff or user.groups.filter(name="HR").exists()

def is_encadrant(user):
    """Vérifie si l'utilisateur est encadrant."""
    return user.groups.filter(name="Encadrant").exists()

def is_stp(user):
    """Vérifie si l'utilisateur est STP."""
    return user.groups.filter(name="STP").exists()

def is_admin_hr_or_encadrant(user):
    """Vérifie si l'utilisateur est un admin, un RH ou un encadrant."""
    return user.is_superuser or user.is_staff or user.groups.filter(name='Encadrant').exists()

def can_approve_leaves(user):
    """Vérifie si l'utilisateur peut approuver des congés."""
    return is_admin_hr_or_encadrant(user)

def can_edit_profiles(user):
    """Vérifie si l'utilisateur peut modifier des profils."""
    return (is_admin(user) or 
            user.groups.filter(name="CanEditProfiles").exists())
