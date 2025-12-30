from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (DMTOnboardViewSet, DMTProfileViewSet, DMTKYCViewSet, 
                   DMTRecipientViewSet, DMTTransactionViewSet, DMTCustomerViewSet, DMTChargeAdminViewSet,
                   DMTCustomerVerificationViewSet, BankViewSet, DMTTransactionInquiryViewSet, DMTRefundViewSet)

router = DefaultRouter()
router.register(r'onboard', DMTOnboardViewSet, basename='dmt-onboard')
router.register(r'customer', DMTCustomerViewSet, basename='dmt-customer')
router.register(r'profile', DMTProfileViewSet, basename='dmt-profile')
router.register(r'kyc', DMTKYCViewSet, basename='dmt-kyc')
router.register(r'recipient', DMTRecipientViewSet, basename='dmt-recipient')
router.register(r'transaction', DMTTransactionViewSet, basename='dmt-transaction')
router.register(r'verification', DMTCustomerVerificationViewSet, basename='dmt-verification')
router.register(r"banks", BankViewSet, basename="ekobank")
router.register(r'inquiry', DMTTransactionInquiryViewSet, basename='dmt-inquiry')
router.register(r'refund', DMTRefundViewSet, basename='dmt-refund')
router.register(r'charge-admin', DMTChargeAdminViewSet, basename='dmt-charge-admin')

urlpatterns = [
    path('', include(router.urls)),
]