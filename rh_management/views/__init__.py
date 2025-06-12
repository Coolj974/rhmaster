"""
Package des vues pour l'application RH Management.
Ce fichier rend les vues accessibles depuis le package views.
"""

# Importation des vues d'authentification
from .auth_views import (
    home_view,
    login_view,
    register_view,
    logout_view
)

# Importation des vues du tableau de bord
from .dashboard_views import (
    dashboard_view,
    some_view,
    dashboard_filtered,
    dashboard_stats_api,
    dashboard,
    index
)

# Importation des vues de gestion des congés
from .leave_views import (
    leave_request_view,
    leave_request,
    manage_leave_balances,
    update_leave_balance,
    bulk_update_leave_balance,
    manage_leaves_view,
    manage_leaves,
    approve_leave,
    reject_leave,
    leave_action,
    approve_all_leaves,
    delete_leave,
    export_leaves,  # Ajout de l'import
    my_leaves,
    cancel_leave,  # Ajout de cette ligne
    export_leave_balances,  # Ajout de export_leave_balances
    adjust_leave_balance,
    adjust_collective_leave_balance,
    get_leave_balance_history
)

# Importation des vues de gestion des notes de frais
from .expense_views import (
    submit_expense,
    my_expenses_view,
    my_expenses,
    manage_expenses_view,
    manage_expenses,
    approve_expense,
    reject_expense,
    cancel_expense,
    export_expenses,
    delete_expense,
    expense_action,
    approve_all_expenses
)

# Importation des vues de gestion des frais kilométriques
from .kilometric_expense_views import (
    manage_kilometric_expenses_view,
    submit_kilometric_expense,
    my_kilometric_expenses,
    export_expenses_excel,
    export_expenses_pdf,
    export_kilometric_expenses,
    manage_kilometric_expenses,
    approve_kilometric_expense,
    reject_kilometric_expense,
    approve_all_kilometric_expenses,
    edit_kilometric_expense,
    delete_kilometric_expense,
    kilometric_expense_action,
    cancel_kilometric_expense  # Ajout de cette ligne
)

# Importation des vues de gestion des utilisateurs
from .user_management_views import (
    manage_users_view,
    delete_user,
    edit_user,
    reset_password,
    toggle_user_status,
    mass_action,
    manage_roles_view,
    create_role,
    edit_role,
    assign_permissions,
    assign_users,
    delete_role
)

# Importation des vues de gestion des profils
from .profile_views import (
    profile_view,
    profile,
    update_profile,
    change_password,
    view_user_profile,
    edit_preferences
)

# Importation des vues du gestionnaire de mots de passe
from .password_manager_views import (
    password_manager_list,
    password_manager_add,
    password_manager_edit,
    password_manager_delete,
    password_manager_view,
    password_share,
    password_share_remove,
    password_manager,
    password_add,
    password_view,
    password_edit,
    password_delete,
    generate_strong_password
)

# Importation des API
from .api_views import (
    api_leaves,
    api_expense_stats,
    api_kilometric_stats,
    api_notifications,
    generate_password_api,
    search_api
)

# Importation des vues de notification
from .notification_views import (
    notifications_view,
    mark_notification_read,
    mark_all_read,
    delete_notification,
    delete_all_read,
    get_notifications_count, 
    get_notifications_dropdown
)
