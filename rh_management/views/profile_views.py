from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from ..models import UserProfile, LeaveRequest, ExpenseReport, KilometricExpense
from .permissions import is_admin, is_rh, is_encadrant

@login_required
def profile_view(request):
    """Affiche la page de profil de l'utilisateur."""
    # S'assurer que l'utilisateur a un profil
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=request.user)
        profile.save()

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
    
    context = {
        'profile': profile,
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
    """Met à jour les informations de profil de l'utilisateur."""
    if request.method == "POST":
        # Vérifier si c'est un formulaire de préférences
        if request.POST.get('form_type') == 'preferences':
            # Récupérer les préférences
            theme = request.POST.get('theme', 'light')
            notifications_enabled = request.POST.get('notifications_enabled') == 'on'
            email_notifications = request.POST.get('email_notifications') == 'on'
            language = request.POST.get('language', 'fr')
            
            # Récupérer ou créer le profil utilisateur - Correction ici
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Mettre à jour les préférences
            profile.theme_preference = theme
            profile.notifications_enabled = notifications_enabled
            profile.email_notifications = email_notifications
            profile.language_preference = language
            profile.save()
            
            messages.success(request, "Vos préférences ont été mises à jour avec succès.")
            return redirect('profile')
        
        # Sinon, c'est un formulaire de profil standard
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        position = request.POST.get('position')
        department = request.POST.get('department')
        
        user = request.user
        
        # Vérifier si des restrictions s'appliquent pour la modification des champs sensibles
        can_edit_username_email = user.is_superuser or user.is_staff
        
        if can_edit_username_email:
            # Vérifier si le nom d'utilisateur existe déjà pour un autre utilisateur
            if User.objects.exclude(id=user.id).filter(username=username).exists():
                messages.error(request, "Ce nom d'utilisateur est déjà pris.")
                return redirect('profile')
                
            # Vérifier si l'email existe déjà pour un autre utilisateur
            if User.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, "Cette adresse email est déjà utilisée.")
                return redirect('profile')
            
            user.username = username
            user.email = email
        
        # Ces champs peuvent être modifiés par tous les utilisateurs
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Mettre à jour ou créer le profil utilisateur - Correction ici
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        profile.phone = phone
        profile.address = address
        profile.position = position
        profile.department = department
        
        # Gérer l'upload de photo de profil si fourni
        if 'profile_picture' in request.FILES:
            profile_picture = request.FILES['profile_picture']
            # Vérifier la taille et le type de fichier
            if profile_picture.size > 5 * 1024 * 1024:  # Limite à 5Mo
                messages.error(request, "La photo de profil ne doit pas dépasser 5Mo.")
                return redirect('profile')
            
            # Vérifier le type de fichier
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if profile_picture.content_type not in allowed_types:
                messages.error(request, "Seuls les formats JPEG, PNG et GIF sont acceptés.")
                return redirect('profile')
                
            profile.profile_picture = profile_picture
        
        profile.save()
        
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
        user_profile = target_user.userprofile
    except UserProfile.DoesNotExist:
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
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = UserProfile(user=request.user)
        
        # Mettre à jour les préférences
        profile.theme_preference = theme
        profile.notifications_enabled = notifications_enabled
        profile.email_notifications = email_notifications
        profile.language_preference = language
        profile.save()
        
        messages.success(request, "Vos préférences ont été mises à jour avec succès.")
        return redirect('profile')
    
    # Récupérer les préférences actuelles
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=request.user)
        profile.save()
    
    context = {
        'profile': profile,
        'is_admin': request.user.is_superuser,
        'is_rh': request.user.is_staff,
        'is_encadrant': request.user.groups.filter(name='Encadrant').exists(),
    }
    
    return render(request, 'rh_management/edit_preferences.html', context)
