from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PredictView, TransactionView, AccountViewSet

router = DefaultRouter()
router.register(r'predict', PredictView, basename='predict')          # POST /api/predict/
router.register(r'transactions', TransactionView, basename='tx')      # POST /api/transactions/
router.register(r'accounts', AccountViewSet, basename='accounts')     # GET  /api/accounts/

urlpatterns = [path('', include(router.urls))]
