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
from django.conf.urls import handler404, handler500, handler403, handler400
from django.shortcuts import render

from rh_management.views import (
    home_view, dashboard_view,
    submit_expense, manage_expenses_view, approve_expense, reject_expense,
    submit_kilometric_expense, my_kilometric_expenses, manage_kilometric_expenses,
    approve_kilometric_expense, reject_kilometric_expense, edit_kilometric_expense,
    export_expenses_excel, export_expenses_pdf, approve_leave, reject_leave, cancel_expense,
    profile_view, update_profile, change_password,
)

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
    # Administration
    path("admin/", admin.site.urls),  # Admin site
    path("login/", login_view, name="login"),  # Login page
    path("register/", register_view, name="register"),  # Registration page
    path("logout/", LogoutView.as_view(), name="logout"),  # Logout page
    path('accounts/login/', login_view, name="login"),  # Add this

# User Profile Management
    path("profile/", profile_view, name="profile"),  # Page de profil
    path("profile/update/", update_profile, name="update_profile"),  # Mise à jour du profil
    path("profile/change-password/", change_password, name="change_password"),  # Changement de mot de passe

    # Home and Dashboard
    path("", home_view, name="home"),  # Home page
    path("dashboard/", dashboard_view, name="dashboard"),  # Dashboard page

    # Leave Management
    path("leave-request/", leave_request_view, name="leave_request"),  # Leave request page
    path("manage-leaves/", manage_leaves_view, name="manage_leaves"),  # Manage leaves
    path("approve-leave/<int:leave_id>/", approve_leave, name="approve_leave"),  # Approve leave
    path("reject-leave/<int:leave_id>/", reject_leave, name="reject_leave"),  # Reject leave
    path('delete_leave/<int:id>/', views.delete_leave, name='delete_leave'),

    # Expense Management
    path("submit-expense/", submit_expense, name="submit_expense"),  # Submit expense
    path("manage-expenses/", manage_expenses_view, name="manage_expenses"),  # Manage expenses
    path("approve-expense/<int:expense_id>/", approve_expense, name="approve_expense"),  # Approve expense
    path("reject-expense/<int:expense_id>/", reject_expense, name="reject_expense"),  # Reject expense
    path("export-expenses-excel/", export_expenses_excel, name="export_expenses_excel"),  # Export expenses to Excel
    path("export-expenses-pdf/", export_expenses_pdf, name="export_expenses_pdf"),  # Export expenses to PDF
    path("export-expenses/", export_expenses, name="export_expenses"),  # Export expenses
    path("cancel-expense/<int:expense_id>/", cancel_expense, name="cancel_expense"),
    path('delete_expense/<int:id>/', views.delete_expense, name='delete_expense'),


    # Kilometric Expense Management
    path("submit-kilometric-expense/", submit_kilometric_expense, name="submit_kilometric_expense"),  # Submit kilometric expense
    path("my-kilometric-expenses/", my_kilometric_expenses, name="my_kilometric_expenses"),  # View my kilometric expenses
    path("manage-kilometric-expenses/", manage_kilometric_expenses, name="manage_kilometric_expenses"),  # Manage kilometric expenses
    path("approve-kilometric-expense/<int:expense_id>/", approve_kilometric_expense, name="approve_kilometric_expense"),  # Approve kilometric expense
    path("reject-kilometric-expense/<int:expense_id>/", reject_kilometric_expense, name="reject_kilometric_expense"),  # Reject kilometric expense
    path("edit-kilometric-expense/<int:expense_id>/", edit_kilometric_expense, name="edit_kilometric_expense"),  # Edit kilometric expense
    path('delete_kilometric_expense/<int:id>/', views.delete_kilometric_expense, name='delete_kilometric_expense'),

    # Other URLs
    path('dashboard_filtered/', views.dashboard_filtered, name='dashboard_filtered'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)