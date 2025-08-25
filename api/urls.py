from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PredictView, AccountViewSet, TransactionView, JournalViewSet
from .report_views import income_statement_view, balance_sheet_view, trial_balance_view

router = DefaultRouter()
router.register(r'predict', PredictView, basename='predict')
router.register(r'accounts', AccountViewSet, basename='accounts')
router.register(r'transactions', TransactionView, basename='transactions')
router.register(r'journals', JournalViewSet, basename='journals')
urlpatterns = [
    path('', include(router.urls)),
    path('reports/income-statement/', income_statement_view, name='report-income-statement'),
    path('reports/balance-sheet/', balance_sheet_view, name='report-balance-sheet'),
    path('reports/trial-balance/', trial_balance_view, name='report-trial-balance'),
]
