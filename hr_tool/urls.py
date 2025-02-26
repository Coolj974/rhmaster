from rh_management.views import register_view
from django.contrib.auth.views import LogoutView
from django.urls import path, include
from rh_management.views import login_view
from django.contrib import admin
from rh_management import views
from rh_management.views import leave_request_view
from rh_management.views import manage_leaves_view
from rh_management.views import export_expenses
from django.conf.urls.static import static
from django.conf import settings

from rh_management.views import (
    home_view, dashboard_view,
    submit_expense, manage_expenses_view, approve_expense, reject_expense,
    submit_kilometric_expense, my_kilometric_expenses, manage_kilometric_expenses,
    approve_kilometric_expense, reject_kilometric_expense, edit_kilometric_expense,
    export_expenses_excel, export_expenses_pdf, approve_leave, reject_leave, cancel_expense,
)

urlpatterns = [
    # Administration
    path("admin/", admin.site.urls),  # Admin site
    path('accounts/', include('allauth.urls')),  # Ajoute les URLs d'authentification
    path("login/", login_view, name="login"),  # Login page
    path("register/", register_view, name="register"),  # Registration page
    path("logout/", LogoutView.as_view(), name="logout"),  # Logout page

    # Home and Dashboard
    path("", home_view, name="home"),  # Home page
    path("dashboard/", dashboard_view, name="dashboard"),  # Dashboard page

    # Leave Management
    path("leave-request/", leave_request_view, name="leave_request"),  # Leave request page
    path("manage-leaves/", manage_leaves_view, name="manage_leaves"),  # Manage leaves
    path("approve-leave/<int:leave_id>/", approve_leave, name="approve_leave"),  # Approve leave
    path("reject-leave/<int:leave_id>/", reject_leave, name="reject_leave"),  # Reject leave

    # Expense Management
    path("submit-expense/", submit_expense, name="submit_expense"),  # Submit expense
    path("manage-expenses/", manage_expenses_view, name="manage_expenses"),  # Manage expenses
    path("approve-expense/<int:expense_id>/", approve_expense, name="approve_expense"),  # Approve expense
    path("reject-expense/<int:expense_id>/", reject_expense, name="reject_expense"),  # Reject expense
    path("export-expenses-excel/", export_expenses_excel, name="export_expenses_excel"),  # Export expenses to Excel
    path("export-expenses-pdf/", export_expenses_pdf, name="export_expenses_pdf"),  # Export expenses to PDF
    path("export-expenses/", export_expenses, name="export_expenses"),  # Export expenses
    path("cancel-expense/<int:expense_id>/", cancel_expense, name="cancel_expense"),
    


    # Kilometric Expense Management
    path("submit-kilometric-expense/", submit_kilometric_expense, name="submit_kilometric_expense"),  # Submit kilometric expense
    path("my-kilometric-expenses/", my_kilometric_expenses, name="my_kilometric_expenses"),  # View my kilometric expenses
    path("manage-kilometric-expenses/", manage_kilometric_expenses, name="manage_kilometric_expenses"),  # Manage kilometric expenses
    path("approve-kilometric-expense/<int:expense_id>/", approve_kilometric_expense, name="approve_kilometric_expense"),  # Approve kilometric expense
    path("reject-kilometric-expense/<int:expense_id>/", reject_kilometric_expense, name="reject_kilometric_expense"),  # Reject kilometric expense
    path("edit-kilometric-expense/<int:expense_id>/", edit_kilometric_expense, name="edit_kilometric_expense"),  # Edit kilometric expense
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
