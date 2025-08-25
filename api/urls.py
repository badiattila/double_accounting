from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PredictView, AccountViewSet, TransactionView
from .report_views import income_statement_view, balance_sheet_view

router = DefaultRouter()
router.register(r'predict', PredictView, basename='predict')
router.register(r'accounts', AccountViewSet, basename='accounts')
router.register(r'transactions', TransactionView, basename='transactions')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/income-statement/', income_statement_view, name='report-income-statement'),
    path('reports/balance-sheet/', balance_sheet_view, name='report-balance-sheet'),
]
