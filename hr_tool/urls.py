from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.contrib.auth.views import LogoutView  # Ajout de l'import manquant

# Import all views directly to ensure they're available
from rh_management.views import (
    home_view, login_view, register_view, logout_view, dashboard_view,
    leave_request_view, manage_leaves_view, approve_leave, reject_leave, cancel_leave,
    submit_expense, manage_expenses_view, approve_expense, reject_expense, cancel_expense,
    profile_view, update_profile, change_password, edit_preferences,
    manage_users_view, edit_user, delete_user, toggle_user_status, mass_action, 
    reset_password,
    submit_kilometric_expense, my_kilometric_expenses, manage_kilometric_expenses,
    approve_kilometric_expense, reject_kilometric_expense, edit_kilometric_expense,
    cancel_kilometric_expense, approve_all_kilometric_expenses,
    export_expenses, export_expenses_excel, export_expenses_pdf, export_leaves,
    delete_leave, delete_expense, delete_kilometric_expense,
    dashboard_filtered, my_leaves, my_expenses_view, approve_all_expenses,
    # Important - explicitly import these two views
    manage_roles_view, delete_role,
    # Password Manager views
    password_manager_list, password_manager_add, password_manager_edit, 
    password_manager_delete, password_manager_view, password_share, password_share_remove,
    api_leaves,
    password_manager, password_add, password_view, password_edit, password_delete,
    leave_action, expense_action, kilometric_expense_action, manage_leave_balances,
    update_leave_balance, dashboard_stats_api,
    export_leave_balances, get_leave_balance_history, adjust_leave_balance, adjust_collective_leave_balance
)

# Import les nouvelles vues d'historique
from rh_management.views.expense_views import expense_history, admin_expense_history
from rh_management.views.leave_views import leave_history, admin_leave_history

# Import les nouvelles vues de notification
from rh_management.views.notification_views import (
    notifications_view, mark_notification_read, mark_all_read,
    delete_notification, delete_all_read, get_notifications_count,
    get_notifications_dropdown,
    get_notifications, mark_notification_as_read, mark_all_as_read, notifications_page
)

# Import pour la nouvelle vue
from rh_management.views.leave_views import (
    leave_request_view, cancel_leave, manage_leaves_view, 
    approve_leave, reject_leave, delete_leave, leave_action, 
    export_leaves, manage_leave_balances, update_leave_balance, 
    my_leaves, approve_all_leaves
)

# Import pour la gestion des rôles et utilisateurs
from rh_management.views.user_management_views import (
    manage_roles_view, create_role, edit_role, 
    assign_permissions, assign_users, delete_role
)

# Import pour les vues de frais kilométriques
from rh_management.views.kilometric_expense_views import export_kilometric_expenses

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

# Personnalisation de l'interface d'administration
from rh_management import admin_views

# Ne pas remplacer l'instance admin.site
admin.site.site_header = "CybeRH Administration"
admin.site.site_title = "CybeRH Admin"
admin.site.index_title = "Tableau de bord d'administration"

urlpatterns = [
    # Admin standard
    path("admin/", admin.site.urls),
    
    # Tableau de bord admin personnalisé - utiliser un chemin différent que celui sous /admin/
    path("admin-dashboard/", admin_views.admin_dashboard, name='admin_dashboard'),
    
    # Utilisation directe de la vue sans passer par admin.site.admin_view
    path("admin/dashboard/", admin_views.admin_dashboard, name='admin_dashboard'),
    # Version sans slash final pour la compatibilité
    path("admin/dashboard", admin_views.admin_dashboard),
    
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
    path('profile/preferences/', edit_preferences, name='edit_preferences'),
    
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
    path('roles/create/', create_role, name='create_role'),
    path('roles/<int:role_id>/edit/', edit_role, name='edit_role'),
    path('roles/<int:role_id>/permissions/', assign_permissions, name='assign_permissions'),
    path('roles/<int:role_id>/users/', assign_users, name='assign_users'),
    
    # Leave Management
    path("leave-request/", leave_request_view, name="leave_request"),  # Leave request page
    path("cancel-leave/<int:id>/", cancel_leave, name="cancel_leave"),
    path("manage-leaves/", manage_leaves_view, name="manage_leaves"),
    path("approve-leave/<int:leave_id>/", approve_leave, name="approve_leave"),
    path("reject-leave/<int:leave_id>/", reject_leave, name="reject_leave"),
    path('delete_leave/<int:id>/', delete_leave, name='delete_leave'),
    path('leave-action/<int:leave_id>/', leave_action, name='leave_action'),
    path('export/', export_leaves, name='export_leaves'),
    path('leave-balance/', manage_leave_balances, name='manage_leave_balances'),
    path('update-leave-balance/<int:user_id>/', update_leave_balance, name='update_leave_balance'),
    path('my-leaves/', my_leaves, name='my_leaves'),
    path('approve-all-leaves/', approve_all_leaves, name='approve_all_leaves'),  # Nouvelle URL
    path('export-leave-balances/', export_leave_balances, name='export_leave_balances'),
    path('leave-balance-history/<int:user_id>/', get_leave_balance_history, name='leave_balance_history'),
    path('adjust-leave-balance/', adjust_leave_balance, name='adjust_leave_balance'),
    path('adjust-collective-leave-balance/', adjust_collective_leave_balance, name='adjust_collective_leave_balance'),

    # Expense Management
    path("submit-expense/", submit_expense, name="submit_expense"),  # Submit expense
    path("my-expenses/", my_expenses_view, name="my_expenses"),  # Modification de l'URL name
    path("manage-expenses/", manage_expenses_view, name="manage_expenses"),  # Manage expenses
    path("approve-expense/<int:expense_id>/", approve_expense, name="approve_expense"),  # Approve expense
    path("reject-expense/<int:expense_id>/", reject_expense, name="reject_expense"),  # Reject expense
    path("export-expenses-excel/", export_expenses_excel, name="export_expenses_excel"),  # Export expenses to Excel
    path("export-expenses-pdf/", export_expenses_pdf, name="export_expenses_pdf"),  # Export expenses to PDF
    path("export-expenses/", export_expenses, name="export_expenses"),  # Export expenses
    path("cancel-expense/<int:expense_id>/", cancel_expense, name="cancel_expense"),
    path('delete_expense/<int:id>/', delete_expense, name='delete_expense'),
    path('expense-action/<int:expense_id>/', expense_action, name='expense_action'),
    path('approve-all-expenses/', approve_all_expenses, name='approve_all_expenses'),  # Approuver toutes les notes de frais

    # Kilometric Expense Management
    path("submit-kilometric-expense/", submit_kilometric_expense, name="submit_kilometric_expense"),  # Submit kilometric expense
    path("my-kilometric-expenses/", my_kilometric_expenses, name="my_kilometric_expenses"),  # View my kilometric expenses
    path("manage-kilometric-expenses/", manage_kilometric_expenses, name="manage_kilometric_expenses"),  # Manage kilometric expenses
    path("approve-kilometric-expense/<int:expense_id>/", approve_kilometric_expense, name="approve_kilometric_expense"),  # Approve kilometric expense
    path("reject-kilometric-expense/<int:expense_id>/", reject_kilometric_expense, name="reject_kilometric_expense"),  # Reject kilometric expense
    path("edit-kilometric-expense/<int:expense_id>/", edit_kilometric_expense, name="edit_kilometric_expense"),  # Edit kilometric expense
    path("cancel-kilometric-expense/<int:expense_id>/", cancel_kilometric_expense, name="cancel_kilometric_expense"),  # Ajout de cette ligne
    path('delete_kilometric_expense/<int:id>/', delete_kilometric_expense, name='delete_kilometric_expense'),
    path('kilometric-expense-action/<int:expense_id>/', kilometric_expense_action, name='kilometric_expense_action'),
    path('approve-all-kilometric-expenses/', approve_all_kilometric_expenses, name='approve_all_kilometric_expenses'),  # Approuver tous les frais kilométriques
    path('export-kilometric-expenses/', export_kilometric_expenses, name='export_kilometric_expenses'),  # Nouvelle URL pour exporter les frais kilométriques
    
    # Password Manager
    path("password-manager/", password_manager_list, name="password_manager_list"),
    path("password-manager/add/", password_manager_add, name="password_manager_add"),
    path("password-manager/<int:pk>/edit/", password_manager_edit, name="password_manager_edit"),
    path("password-manager/<int:pk>/delete/", password_manager_delete, name="password_manager_delete"),
    path("password-manager/<int:pk>/view/", password_manager_view, name="password_manager_view"),
    path("password-manager/<int:pk>/share/", password_share, name="password_share"),
    path("password-manager/share/<int:share_id>/remove/", password_share_remove, name="password_share_remove"),
    path('password-manager/', password_manager_list, name='password_manager'),  # Alias pour compatibilité
    path('passwords/', password_manager, name='password_manager'),
    path('passwords/add/', password_add, name='password_add'),
    path('passwords/view/<int:pk>/', password_view, name='password_view'),
    path('passwords/edit/<int:pk>/', password_edit, name='password_edit'),
    path('passwords/delete/<int:pk>/', password_delete, name='password_delete'),
    path('passwords/share/<int:pk>/', password_share, name='password_share'),
    
    # Notifications
    path("notifications/", notifications_view, name="notifications"),
    path("notifications/mark-read/<int:notification_id>/", mark_notification_read, name="mark_notification_read"),
    path("notifications/mark-all-read/", mark_all_read, name="mark_all_read"),
    path("notifications/delete/<int:notification_id>/", delete_notification, name="delete_notification"),
    path("notifications/delete-all-read/", delete_all_read, name="delete_all_read"),
    path("api/notifications/count/", get_notifications_count, name="get_notifications_count"),
    path("api/notifications/dropdown/", get_notifications_dropdown, name="get_notifications_dropdown"),
    path('notifications/get/', get_notifications, name='get_notifications'),
    path('notifications/count/', get_notifications_count, name='get_notifications_count'),
    path('notifications/mark-read/<int:notification_id>/', mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark-all-read/', mark_all_as_read, name='mark_all_as_read'),
    path('notifications/', notifications_page, name='notifications_page'),

    # API
    path("api/leaves/", api_leaves, name="api_leaves"),
    path('api/dashboard-stats/', dashboard_stats_api, name='dashboard_stats_api'),    # Historiques
    path("expense-history/", expense_history, name="expense_history"),  # Historique des notes de frais
    path("leave-history/", leave_history, name="leave_history"),  # Historique des demandes de congé
    path("admin-leave-history/", admin_leave_history, name="admin_leave_history"),  # Historique admin des congés
    path("admin-expense-history/", admin_expense_history, name="admin_expense_history"),  # Historique admin des notes de frais
]

# Add static and media URL patterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)