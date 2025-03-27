from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from ..models import LeaveRequest, ExpenseReport, KilometricExpense, UserProfile, PasswordManager
from .permissions import is_rh, is_encadrant, is_stp, is_admin_or_hr

@login_required
def dashboard_view(request):
    new_leave_requests_count = LeaveRequest.objects.filter(status='pending').count()
    new_expense_reports_count = ExpenseReport.objects.filter(status='pending').count()
    new_kilometric_expenses_count = KilometricExpense.objects.filter(status='pending').count()

    # Déterminer clairement les rôles de l'utilisateur
    is_superuser = request.user.is_superuser
    is_hr = is_rh(request.user)
    
    is_admin_flag = request.user.is_superuser
    is_rh_flag = is_rh(request.user)
    is_encadrant_flag = is_encadrant(request.user)
    is_stp_flag = is_stp(request.user)
    is_employee_flag = (request.user.groups.filter(name="Employé").exists() or 
                       not (is_admin_flag or is_rh_flag or is_encadrant_flag or is_stp_flag))
    
    # Correction de la logique de détermination des demandes à afficher
    if is_admin_flag or is_rh_flag or is_encadrant_flag:
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

@login_required
def dashboard_stats_api(request):
    """API endpoint pour les statistiques du tableau de bord."""
    try:
        user = request.user
        stats = {
            'leave_count': LeaveRequest.objects.filter(user=user).count(),
            'expense_count': ExpenseReport.objects.filter(user=user).count(),
            'km_expense_count': KilometricExpense.objects.filter(user=user).count(),
            'password_count': PasswordManager.objects.filter(user=user).count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
