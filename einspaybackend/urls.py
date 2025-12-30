from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .routers import router

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/services/', include('services.urls')),
    path('apis/', include(router.urls)),
    path('apis/dmt/', include('dmt.urls')),
    path('apis/bbps/', include('bbps.urls')),
    path('apis/vendorpayment/', include('vendorpayment.urls')),
    path('apis/commission/', include('commission.urls')), 
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)