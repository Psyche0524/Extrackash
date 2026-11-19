from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from expenses import views as v
from expenses.forms import EmailLoginForm

urlpatterns = [
    # welcome & accounts
    path('welcome/', v.welcome, name='welcome'),
    path('signup/', v.signup, name='signup'),
    path('setup/', v.setup, name='setup'),
    path('ready/', v.ready, name='ready'),
    path('login/', auth_views.LoginView.as_view(
        template_name='expenses/login.html', authentication_form=EmailLoginForm, redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # home & activity
    path('', v.home, name='home'),
    path('activity/', v.activity, name='activity'),
    path('activity/<int:pk>/', v.transaction_detail, name='transaction'),
    path('activity/<int:pk>/edit/', v.transaction_edit, name='transaction_edit'),
    path('activity/<int:pk>/delete/', v.transaction_delete, name='transaction_delete'),
    path('activity/<int:pk>/photo/', v.transaction_photo, name='transaction_photo'),
    path('add/', v.add_transaction, name='add'),
    path('transfer/', v.transfer, name='transfer'),

    # plan
    path('plan/', v.plan, name='plan'),
    path('plan/budgets/', v.budgets, name='budgets'),
    path('plan/budgets/new/', v.budget_new, name='budget_new'),
    path('plan/planned/', v.planned, name='planned'),
    path('plan/planned/new/', v.planned_new, name='planned_new'),
    path('plan/planned/<int:pk>/edit/', v.planned_edit, name='planned_edit'),
    path('plan/planned/<int:pk>/done/', v.planned_done, name='planned_done'),
    path('plan/planned/<int:pk>/delete/', v.planned_delete, name='planned_delete'),
    path('plan/travel/', v.trips, name='trips'),
    path('plan/travel/new/', v.trip_new, name='trip_new'),
    path('plan/travel/<int:pk>/edit/', v.trip_edit, name='trip_edit'),
    path('plan/travel/<int:pk>/delete/', v.trip_delete, name='trip_delete'),
    path('plan/tags/', v.tags, name='tags'),
    path('plan/budgets/<int:pk>/', v.budget_detail, name='budget'),
    path('plan/budgets/<int:pk>/edit/', v.budget_edit, name='budget_edit'),
    path('plan/budgets/<int:pk>/delete/', v.budget_delete, name='budget_delete'),
    path('plan/goals/', v.goals, name='goals'),
    path('plan/goals/new/', v.goal_new, name='goal_new'),
    path('plan/goals/<int:pk>/', v.goal_detail, name='goal'),
    path('plan/goals/<int:pk>/edit/', v.goal_edit, name='goal_edit'),
    path('plan/goals/<int:pk>/add/', v.goal_add_money, name='goal_add'),
    path('plan/goals/<int:pk>/delete/', v.goal_delete, name='goal_delete'),
    path('plan/cashflow/', v.cashflow, name='cashflow'),

    # explore
    path('explore/', v.explore, name='explore'),
    path('explore/accounts/', v.accounts, name='accounts'),
    path('explore/accounts/new/', v.account_new, name='account_new'),
    path('explore/accounts/<int:pk>/edit/', v.account_edit, name='account_edit'),
    path('explore/accounts/<int:pk>/delete/', v.account_delete, name='account_delete'),
    path('explore/cards/', v.cards, name='cards'),
    path('explore/installments/', v.debts, {'kind': 'installment'}, name='installments'),
    path('explore/loans/', v.debts, {'kind': 'loan'}, name='loans'),
    path('explore/receivables/', v.debts, {'kind': 'receivable'}, name='receivables'),
    path('explore/debts/new/', v.debt_new, name='debt_new'),
    path('explore/debts/<int:pk>/edit/', v.debt_edit, name='debt_edit'),
    path('explore/debts/<int:pk>/pay/', v.debt_pay, name='debt_pay'),
    path('explore/debts/<int:pk>/delete/', v.debt_delete, name='debt_delete'),
    path('explore/investments/', v.investments, name='investments'),
    path('explore/investments/new/', v.investment_new, name='investment_new'),
    path('explore/investments/<int:pk>/edit/', v.investment_edit, name='investment_edit'),
    path('explore/investments/<int:pk>/delete/', v.investment_delete, name='investment_delete'),
    path('explore/reports/', v.reports, name='reports'),
    path('explore/reports/export.csv', v.export_csv, name='export'),
    path('explore/shared/', v.shared, name='shared'),
    path('explore/shared/new/', v.household_new, name='household_new'),
    path('explore/shared/invite/', v.household_invite, name='household_invite'),
    path('explore/shared/leave/', v.household_leave, name='household_leave'),
    path('settings/', v.settings_page, name='settings'),
    path('settings/profile/', v.profile_edit, name='profile_edit'),
    path('settings/delete/', v.delete_account, name='delete_account'),

    path('admin/', admin.site.urls),
]
