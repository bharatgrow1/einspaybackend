from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import bbpsViewSet, OperatorViewSet, PlanViewSet

router = DefaultRouter()
router.register(r'bbps', bbpsViewSet, basename='bbps')
router.register(r'operators', OperatorViewSet, basename='operators')
router.register(r'plans', PlanViewSet, basename='plans')

urlpatterns = [
    path('', include(router.urls)),
]
