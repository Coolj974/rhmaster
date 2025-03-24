from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.contrib.auth.views import LogoutView  # Ajout de l'import manquant

# Import all views directly to ensure they're available
from rh_management.views import (
    home_view, login_view, register_view, logout_view, dashboard_view,
    leave_request_view, manage_leaves_view, approve_leave, reject_leave,
    submit_expense, manage_expenses_view, approve_expense, reject_expense, cancel_expense,
    profile_view, update_profile, change_password,
    manage_users_view, edit_user, delete_user, toggle_user_status, mass_action, 
    reset_password,
    submit_kilometric_expense, my_kilometric_expenses, manage_kilometric_expenses,
    approve_kilometric_expense, reject_kilometric_expense, edit_kilometric_expense,
    export_expenses, export_expenses_excel, export_expenses_pdf,
    delete_leave, delete_expense, delete_kilometric_expense,
    dashboard_filtered,
    # Important - explicitly import these two views
    manage_roles_view, delete_role,
    # Password Manager views
    password_manager_list, password_manager_add, password_manager_edit, 
    password_manager_delete, password_manager_view, password_share, password_share_remove,
    api_leaves,
)

# Error handlers
def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)

def error_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def error_400(request, exception):
    return render(request, 'errors/400.html', status=400)

handler404 = error_404
handler500 = error_500
handler403 = error_403
handler400 = error_400

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    # Utiliser soit la vue basée sur classe, soit la vue personnalisée, pas les deux
    # Option 1: Utiliser la vue personnalisée
    path("logout/", logout_view, name="logout"),  
    # Option 2: Ou utiliser la vue basée sur classe (décommenter si vous préférez cette option)
    # path("logout/", LogoutView.as_view(next_page='login'), name="logout"),
    
    path('accounts/login/', login_view, name="login"),
    
    # Main pages
    path("", home_view, name="home"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path('dashboard_filtered/', dashboard_filtered, name='dashboard_filtered'),
    
    # User profile management - Ajout de l'URL profile manquante
    path("profile/", profile_view, name="profile"),
    path("profile/update/", update_profile, name="update_profile"),
    path("profile/change-password/", change_password, name="change_password"),
    
    # User management
    path("manage-users/", manage_users_view, name="manage_users"),
    path("edit-user/<int:user_id>/", edit_user, name="edit_user"),
    path("delete-user/<int:user_id>/", delete_user, name="delete_user"),
    path("toggle-user-status/<int:user_id>/", toggle_user_status, name="toggle_user_status"),
    path("reset-password/<int:user_id>/", reset_password, name="reset_password"),
    path("mass-action/", mass_action, name="mass_action"),  # Nouvelle URL pour les actions en masse
    
    # Role management - explicitly define these paths
    path("manage-roles/", manage_roles_view, name="manage_roles"),
    path("delete-role/<int:role_id>/", delete_role, name="delete_role"),
    
    # Leave Management
    path("leave-request/", leave_request_view, name="leave_request"),  # Leave request page
    path("manage-leaves/", manage_leaves_view, name="manage_leaves"),  # Manage leaves
    path("approve-leave/<int:leave_id>/", approve_leave, name="approve_leave"),  # Approve leave
    path("reject-leave/<int:leave_id>/", reject_leave, name="reject_leave"),  # Reject leave
    path('delete_leave/<int:id>/', delete_leave, name='delete_leave'),

    # Expense Management
    path("submit-expense/", submit_expense, name="submit_expense"),  # Submit expense
    path("manage-expenses/", manage_expenses_view, name="manage_expenses"),  # Manage expenses
    path("approve-expense/<int:expense_id>/", approve_expense, name="approve_expense"),  # Approve expense
    path("reject-expense/<int:expense_id>/", reject_expense, name="reject_expense"),  # Reject expense
    path("export-expenses-excel/", export_expenses_excel, name="export_expenses_excel"),  # Export expenses to Excel
    path("export-expenses-pdf/", export_expenses_pdf, name="export_expenses_pdf"),  # Export expenses to PDF
    path("export-expenses/", export_expenses, name="export_expenses"),  # Export expenses
    path("cancel-expense/<int:expense_id>/", cancel_expense, name="cancel_expense"),
    path('delete_expense/<int:id>/', delete_expense, name='delete_expense'),

    # Kilometric Expense Management
    path("submit-kilometric-expense/", submit_kilometric_expense, name="submit_kilometric_expense"),  # Submit kilometric expense
    path("my-kilometric-expenses/", my_kilometric_expenses, name="my_kilometric_expenses"),  # View my kilometric expenses
    path("manage-kilometric-expenses/", manage_kilometric_expenses, name="manage_kilometric_expenses"),  # Manage kilometric expenses
    path("approve-kilometric-expense/<int:expense_id>/", approve_kilometric_expense, name="approve_kilometric_expense"),  # Approve kilometric expense
    path("reject-kilometric-expense/<int:expense_id>/", reject_kilometric_expense, name="reject_kilometric_expense"),  # Reject kilometric expense
    path("edit-kilometric-expense/<int:expense_id>/", edit_kilometric_expense, name="edit_kilometric_expense"),  # Edit kilometric expense
    path('delete_kilometric_expense/<int:id>/', delete_kilometric_expense, name='delete_kilometric_expense'),
    
    # Password Manager
    path("password-manager/", password_manager_list, name="password_manager_list"),
    path("password-manager/add/", password_manager_add, name="password_manager_add"),
    path("password-manager/<int:pk>/edit/", password_manager_edit, name="password_manager_edit"),
    path("password-manager/<int:pk>/delete/", password_manager_delete, name="password_manager_delete"),
    path("password-manager/<int:pk>/view/", password_manager_view, name="password_manager_view"),
    path("password-manager/<int:pk>/share/", password_share, name="password_share"),
    path("password-manager/share/<int:share_id>/remove/", password_share_remove, name="password_share_remove"),
    
    # API
    path("api/leaves/", api_leaves, name="api_leaves"),
]

# Add static and media URL patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)