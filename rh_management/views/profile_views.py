from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from ..models import UserProfile, LeaveRequest, ExpenseReport, KilometricExpense
from .permissions import is_admin, is_rh, is_encadrant
from rh_management.models import Profile, LeaveBalance, Department

@login_required
def profile(request):
    """
    Affiche le profil de l'utilisateur connecté
    """
    # Récupérer ou créer le profil de l'utilisateur
    user_profile, created = Profile.objects.get_or_create(user=request.user)
      # Récupérer le solde de congés
    leave_balance = LeaveBalance.objects.filter(user=request.user).first()
    
    # Récupérer les départements pour le formulaire de mise à jour
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'profile': user_profile,
        'leave_balance': leave_balance,
        'departments': departments
    }
    
    return render(request, 'rh_management/profile.html', context)

@login_required
def profile_view(request):
    """Affiche la page de profil de l'utilisateur."""
    # S'assurer que l'utilisateur a un profil (utiliser le modèle Profile)
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'update_picture' in request.POST and request.FILES.get('profile_picture'):
            # Gérer l'upload de la photo de profil
            profile_picture = request.FILES['profile_picture']
            
            # Vérifier la taille et le type du fichier
            if profile_picture.size > 5 * 1024 * 1024:  # 5 Mo
                messages.error(request, "L'image est trop volumineuse. Taille maximale : 5 Mo")
            elif not profile_picture.content_type.startswith('image/'):
                messages.error(request, "Le fichier doit être une image (JPEG, PNG, etc.)")
            else:
                profile.profile_picture = profile_picture
                profile.save()
                messages.success(request, "Photo de profil mise à jour avec succès.")
        
        return redirect('profile')

    # Ajout des compteurs de notifications au contexte
    is_admin_flag = request.user.is_superuser
    is_rh_flag = request.user.is_staff or request.user.groups.filter(name='RH').exists()
    is_encadrant_flag = request.user.groups.filter(name='Encadrant').exists()
    is_stp_flag = request.user.groups.filter(name='STP').exists()
    
    # Initialiser les compteurs
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin_flag or is_rh_flag or is_encadrant_flag:
        from ..models import LeaveRequest, ExpenseReport, KilometricExpense
        if is_admin_flag or is_rh_flag:
            new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
        elif is_encadrant_flag:
            from django.contrib.auth.models import User
            team_members = User.objects.filter(team_leader=request.user)
            new_leave_requests_count = LeaveRequest.objects.filter(user__in=team_members, status='pending').count()
            new_expense_reports_count = ExpenseReport.objects.filter(user__in=team_members, status='pending').count()
            new_kilometric_expenses_count = KilometricExpense.objects.filter(user__in=team_members, status='pending').count()
    
    # Récupérer les départements pour le formulaire de mise à jour
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'profile': profile,
        'departments': departments,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'is_stp': is_stp_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/profile.html', context)

@login_required
def update_profile(request):
    """
    Mise à jour du profil utilisateur
    """
    if request.method == 'POST':
        # Mettre à jour les informations de l'utilisateur
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
          # Récupérer ou créer le profil
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Mettre à jour les informations du profil
        profile.phone_number = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.position = request.POST.get('position', '')
          # Gérer le département (le template envoie maintenant l'ID)
        department_id = request.POST.get('department', '').strip()
        if department_id and department_id.isdigit():
            try:
                department = Department.objects.get(id=department_id)
                profile.department = department
            except Department.DoesNotExist:
                pass
        elif not department_id:
            # Si aucun département n'est sélectionné, on met à None
            profile.department = None
        
        # Gérer les préférences si c'est le bon type de formulaire
        form_type = request.POST.get('form_type', 'profile')
        if form_type == 'preferences':
            profile.theme_preference = request.POST.get('theme', 'light')
            profile.language_preference = request.POST.get('language', 'fr')
            profile.notifications_enabled = 'notifications_enabled' in request.POST
            profile.email_notifications = 'email_notifications' in request.POST
        
        # Gérer l'upload de photo de profil
        if 'profile_picture' in request.FILES:
            profile_picture = request.FILES['profile_picture']
            # Vérifier la taille et le type du fichier
            if profile_picture.size > 5 * 1024 * 1024:  # 5MB
                messages.error(request, "L'image est trop volumineuse. La limite est de 5Mo.")
            else:
                allowed_types = ['image/jpeg', 'image/png']
                if profile_picture.content_type in allowed_types:
                    profile.profile_picture = profile_picture
                else:
                    messages.error(request, "Format d'image non accepté. Veuillez utiliser JPEG ou PNG.")
        
        profile.save()
        messages.success(request, "Votre profil a été mis à jour avec succès.")
        
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

@login_required
def view_user_profile(request, user_id):
    """Vue pour voir le profil d'un autre utilisateur (admins, RH, encadrants)."""
    # Vérifier les permissions
    if not (request.user.is_superuser or request.user.is_staff or 
            request.user.groups.filter(name='Encadrant').exists() or 
            request.user.id == user_id):
        messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
        return redirect('dashboard')
    
    target_user = get_object_or_404(User, id=user_id)
      # Récupérer le profil utilisateur
    try:
        user_profile = target_user.profile
    except Profile.DoesNotExist:
        user_profile = None
    
    # Récupérer des statistiques pertinentes
    leave_count = LeaveRequest.objects.filter(user=target_user).count()
    expense_count = ExpenseReport.objects.filter(user=target_user).count()
    kilometric_count = KilometricExpense.objects.filter(user=target_user).count()
    
    # Ajouter les compteurs de notifications au contexte
    is_admin = request.user.is_superuser
    is_rh = request.user.is_staff
    is_encadrant = request.user.groups.filter(name='Encadrant').exists()
    
    new_leave_requests_count = 0
    new_expense_reports_count = 0
    new_kilometric_expenses_count = 0
    
    if is_admin or is_rh:
        new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
        new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
        new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()
    
    context = {
        'viewed_user': target_user,
        'user_profile': user_profile,
        'leave_count': leave_count,
        'expense_count': expense_count,
        'kilometric_count': kilometric_count,
        'is_admin': is_admin,
        'is_rh': is_rh,
        'is_encadrant': is_encadrant,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/view_user_profile.html', context)

@login_required
def edit_preferences(request):
    """Permet à l'utilisateur de modifier ses préférences."""
    if request.method == 'POST':
        # Récupérer les préférences
        theme = request.POST.get('theme', 'light')
        notifications_enabled = request.POST.get('notifications_enabled') == 'on'
        email_notifications = request.POST.get('email_notifications') == 'on'
        language = request.POST.get('language', 'fr')
          # Récupérer ou créer le profil utilisateur
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        # Mettre à jour les préférences
        profile.theme_preference = theme
        profile.notifications_enabled = notifications_enabled
        profile.email_notifications = email_notifications
        profile.language_preference = language
        profile.save()
        
        messages.success(request, "Vos préférences ont été mises à jour avec succès.")
        return redirect('profile')
      # Récupérer les préférences actuelles
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
        'is_admin': request.user.is_superuser,
        'is_rh': request.user.is_staff,
        'is_encadrant': request.user.groups.filter(name='Encadrant').exists(),
    }
    
    return render(request, 'rh_management/edit_preferences.html', context)
