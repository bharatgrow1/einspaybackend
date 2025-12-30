from django.urls import path
from vendorpayment.views import download_vendor_receipt, view_vendor_receipt
from vendorpayment.views_vendor import VendorManagerViewSet


urlpatterns = [
    path('receipt/download/<int:payment_id>/', download_vendor_receipt, name='download_vendor_receipt'),
    path('receipt/view/<int:payment_id>/', view_vendor_receipt, name='view_vendor_receipt'),
    path('vendor/send-otp/', VendorManagerViewSet.as_view({'post': 'send_mobile_otp'}), name='vendor-send-otp'),
    path('vendor/verify-otp/', VendorManagerViewSet.as_view({'post': 'verify_mobile_otp'}), name='vendor-verify-otp'),
    path('vendor/verified-banks/', VendorManagerViewSet.as_view({'post': 'get_verified_banks'}), name='vendor-verified-banks'),
    path('vendor/add-bank/', VendorManagerViewSet.as_view({'post': 'add_vendor_bank'}), name='vendor-add-bank'),
    path('vendor/search/', VendorManagerViewSet.as_view({'post': 'search_vendor_by_mobile'}), name='vendor-search'),
    path('vendor/my-banks/', VendorManagerViewSet.as_view({'get': 'my_vendor_banks'}), name='my-vendor-banks'),
]