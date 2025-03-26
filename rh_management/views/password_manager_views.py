from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from ..models import PasswordManager, PasswordShare, LeaveRequest, ExpenseReport, KilometricExpense
from ..forms import PasswordManagerForm
from .permissions import is_admin, is_rh, is_encadrant
from cryptography.fernet import Fernet

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
    
    # Récupérer les compteurs de notifications
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
    
    context = {
        'categories': categories,
        'shared_categories': shared_categories,
        'password_count': owned_passwords.count(),
        'shared_count': shared_passwords.count(),
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
        # Ajout des variables compatibles avec le template
        'user_passwords': owned_passwords,
        'shared_passwords': shared_passwords,
    }
    
    return render(request, 'rh_management/password_manager.html', context)

@login_required
def password_manager_add(request):
    """View to add a new password entry."""
    if request.method == 'POST':
        form = PasswordManagerForm(request.POST, user=request.user)
        if form.is_valid():
            password_entry = form.save(commit=False)
            password_entry.user = request.user
            
            # Si la génération de mot de passe est activée, on génère un mot de passe
            if request.POST.get('generate_password') == 'on':
                length = int(request.POST.get('password_length', 16))
                password_entry.password = password_entry.generate_password(length)
            
            # Générer une clé de chiffrement si nécessaire
            if not password_entry.encryption_key:
                encryption_key = Fernet.generate_key()
                password_entry.encryption_key = encryption_key.decode('utf-8')
                
            password_entry.save()
            messages.success(request, "Mot de passe ajouté avec succès.")
            return redirect('password_manager_list')
    else:
        form = PasswordManagerForm(user=request.user)
    
    # Compteurs de notifications
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
    
    context = {
        'form': form,
        'title': 'Ajouter un mot de passe',
        'is_add': True,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_form.html', context)

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
    
    # Compteurs de notifications
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
    
    context = {
        'form': form,
        'title': 'Modifier un mot de passe',
        'is_add': False,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
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
    
    # Compteurs de notifications
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
    
    context = {
        'password_entry': password_entry,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
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
            messages.error(request, "Vous n'avez pas accès à ce mot de passe.")
            return redirect('password_manager_list')
    
    # Déchiffrer le mot de passe pour l'affichage
    try:
        decrypted_password = password_entry.decrypt_password()
    except Exception as e:
        messages.error(request, f"Erreur lors du déchiffrement du mot de passe: {str(e)}")
        decrypted_password = "**Erreur de déchiffrement**"
    
    # Récupérer les partages pour ce mot de passe (pour le propriétaire uniquement)
    shares = []
    if is_owner:
        shares = PasswordShare.objects.filter(password_entry=password_entry)
    
    # Compteurs de notifications
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
    
    context = {
        'password_entry': password_entry,
        'decrypted_password': decrypted_password,
        'is_owner': is_owner,
        'can_edit': can_edit,
        'shares': shares,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
    return render(request, 'rh_management/password_view.html', context)

@login_required
def password_share(request, pk):
    """Vue pour partager un mot de passe avec d'autres utilisateurs."""
    # Vérifier que l'utilisateur est propriétaire du mot de passe
    password_entry = get_object_or_404(PasswordManager, pk=pk, user=request.user)
    
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
    
    # Compteurs de notifications
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
    
    context = {
        'password_entry': password_entry,
        'existing_shares': existing_shares,
        'available_users': available_users,
        'is_admin': is_admin_flag,
        'is_rh': is_rh_flag,
        'is_encadrant': is_encadrant_flag,
        'new_leave_requests_count': new_leave_requests_count,
        'new_expense_reports_count': new_expense_reports_count,
        'new_kilometric_expenses_count': new_kilometric_expenses_count,
    }
    
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
def password_manager(request):
    """Vue pour afficher la liste des mots de passe de l'utilisateur."""
    return password_manager_list(request)

@login_required
def password_add(request):
    """Vue pour ajouter un nouveau mot de passe."""
    return password_manager_add(request)

@login_required
def password_view(request, pk):
    """Vue pour voir les détails d'un mot de passe."""
    return password_manager_view(request, pk)

@login_required
def password_edit(request, pk):
    """Vue pour modifier un mot de passe existant."""
    return password_manager_edit(request, pk)

@login_required
def password_delete(request, pk):
    """Vue pour supprimer un mot de passe."""
    return password_manager_delete(request, pk)

@login_required
def generate_strong_password(request):
    """API pour générer un mot de passe fort."""
    from django.http import JsonResponse
    import random
    import string
    
    length = int(request.GET.get('length', 16))
    
    # Limiter la longueur entre 8 et 64 caractères
    if length < 8:
        length = 8
    elif length > 64:
        length = 64
    
    # Caractères à utiliser
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()-_=+[]{}|;:,.<>?/"
    
    # S'assurer qu'il y a au moins un caractère de chaque type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    # Remplir le reste du mot de passe
    all_chars = lowercase + uppercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(length - 4))
    
    # Mélanger le mot de passe
    random.shuffle(password)
    password = ''.join(password)
    
    return JsonResponse({'password': password})
