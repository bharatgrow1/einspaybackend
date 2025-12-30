from rest_framework.routers import DefaultRouter
from rest_framework import routers
from api.views import SignUPRequestViewSet
from services.views import (ServiceCategoryViewSet, DirectServiceFormViewSet, ServiceSubCategoryViewSet,
    ServiceFormViewSet, ServiceSubmissionViewSet, ServiceImageViewSet)
from users.views import (PermissionViewSet, AuthViewSet, UserViewSet, WalletViewSet,
        TransactionViewSet, UserHierarchyViewSet, OnBoardServiceViewSet, FundRequestViewSet, ServiceChargeViewSet,
        StateViewSet, CityViewSet)
from commission.views import (CommissionPlanViewSet, ServiceCommissionViewSet, CommissionTransactionViewSet,
        UserCommissionPlanViewSet, CommissionPayoutViewSet, CommissionStatsViewSet, DealerRetailerCommissionViewSet, 
        CommissionDashboardViewSet, OperatorCommissionViewSet)
from services.views_permissions import ServicePermissionViewSet
from vendorpayment.views import VendorPaymentViewSet
from vendorpayment.views_vendor import VendorManagerViewSet
from aeps.views import AEPSMerchantViewSet

router = DefaultRouter()



# Users
router.register(r'upload-images', ServiceImageViewSet)

router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'user-hierarchy', UserHierarchyViewSet, basename='user-hierarchy')
router.register(r'singup-request', SignUPRequestViewSet)
router.register(r'onboardservices', OnBoardServiceViewSet, basename='services')
router.register(r'permissions', PermissionViewSet, basename='permissions')
router.register(r'service-permissions', ServicePermissionViewSet, basename='service-permissions')


# Wallet and Transaction
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'fund-requests', FundRequestViewSet, basename='fund-requests')
router.register(r'service-charges', ServiceChargeViewSet, basename='service-charges')

# Locations
router.register(r'states', StateViewSet, basename='states')
router.register(r'cities', CityViewSet, basename='cities')

#services
router.register(r'categories', ServiceCategoryViewSet)
router.register(r'subcategories', ServiceSubCategoryViewSet)
router.register(r'service-forms', ServiceFormViewSet)
router.register(r'direct-service-forms', DirectServiceFormViewSet, basename='direct-service-form')
router.register(r'service-submissions', ServiceSubmissionViewSet)

#commission
router.register(r'commission-plans', CommissionPlanViewSet, basename='commission-plans')
router.register(r'service-commissions', ServiceCommissionViewSet, basename='service-commissions')
router.register(r'commission-transactions', CommissionTransactionViewSet, basename='commission-transactions')
router.register(r'user-commission-plans', UserCommissionPlanViewSet, basename='user-commission-plans')
router.register(r'commission-payouts', CommissionPayoutViewSet, basename='commission-payouts')
router.register(r'my-service-commissions', DealerRetailerCommissionViewSet, basename='my-service-commissions')
router.register(r'commission-stats', CommissionStatsViewSet, basename='commission-stats')
router.register(r'commission-dashboard', CommissionDashboardViewSet, basename='commission-dashboard')
router.register(r'operator-commissions', OperatorCommissionViewSet, basename='operator-commissions')

router.register(r'vendor-payment', VendorPaymentViewSet, basename='vendor-payment')
router.register(r'vendor-manager', VendorManagerViewSet, basename='vendor-manager')



# aeps
router.register(r'merchants', AEPSMerchantViewSet, basename='aeps-merchant')

