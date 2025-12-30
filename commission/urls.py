from django.urls import path, include
from rest_framework.routers import DefaultRouter
from commission.views import (
    OperatorCommissionViewSet,
    CommissionPlanViewSet,
    ServiceCommissionViewSet,
    CommissionTransactionViewSet,
    UserCommissionPlanViewSet,
    CommissionPayoutViewSet,
    CommissionStatsViewSet,
    DealerRetailerCommissionViewSet,
    CommissionDashboardViewSet
)

commission_router = DefaultRouter()
commission_router.register(r'operator-commissions', OperatorCommissionViewSet, basename='operator-commissions')
commission_router.register(r'commission-plans', CommissionPlanViewSet, basename='commission-plans')
commission_router.register(r'service-commissions', ServiceCommissionViewSet, basename='service-commissions')
commission_router.register(r'commission-transactions', CommissionTransactionViewSet, basename='commission-transactions')
commission_router.register(r'user-commission-plans', UserCommissionPlanViewSet, basename='user-commission-plans')
commission_router.register(r'commission-payouts', CommissionPayoutViewSet, basename='commission-payouts')
commission_router.register(r'my-service-commissions', DealerRetailerCommissionViewSet, basename='my-service-commissions')
commission_router.register(r'commission-stats', CommissionStatsViewSet, basename='commission-stats')
commission_router.register(r'commission-dashboard', CommissionDashboardViewSet, basename='commission-dashboard')

urlpatterns = [
    path('', include(commission_router.urls)),
]
