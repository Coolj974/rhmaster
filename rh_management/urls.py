from django.urls import path
from . import views as expense_views

urlpatterns = [
    # ...existing urls...

    # Expense URLs
    path('submit-expense/', expense_views.submit_expense, name='submit_expense'),
    path('my-expenses/', expense_views.my_expenses_view, name='my_expenses'),
    path('submit-expense-report/', expense_views.submit_expense_report, name='submit_expense_report'),
    path('manage-expenses/', expense_views.manage_expenses_view, name='manage_expenses'),
    path('approve-expense/<int:expense_id>/', expense_views.approve_expense, name='approve_expense'),
    path('reject-expense/<int:expense_id>/', expense_views.reject_expense, name='reject_expense'),
    path('cancel-expense/<int:expense_id>/', expense_views.cancel_expense, name='cancel_expense'),
    path('export-expenses/', expense_views.export_expenses, name='export_expenses'),
]