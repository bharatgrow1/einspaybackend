from rest_framework.permissions import BasePermission
from django.apps import apps

class IsSuperAdmin(BasePermission):
    """Allows access only to superadmin users"""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'superadmin'
        )

class IsAdminUser(BasePermission):
    """Allows access to admin, superadmin, master users"""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'superadmin', 'master']
        )

class IsMasterUser(BasePermission):
    """Allows access only to master users"""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'master'
        )

class IsRetailer(BasePermission):
    """Allows access only to retailers"""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'retailer'
        )

class HasPermission(BasePermission):
    """Dynamic permission check based on permission codename"""
    def __init__(self, permission_codename):
        self.permission_codename = permission_codename

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Super admin ko sab permissions
        if request.user.role == 'superadmin':
            return True
            
        return request.user.has_permission(self.permission_codename)

class ModelViewPermission(BasePermission):
    """
    Dynamic permission for model CRUD operations
    Maps view actions to Django permission system
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Super admin and master have all permissions
        if request.user.role in ['superadmin', 'master']:
            return True
            
        # Get the model from viewset
        if not hasattr(view, 'queryset') or view.queryset is None:
            return False
            
        model = view.queryset.model
        
        # Map view actions to permission types
        action_map = {
            'list': 'view',
            'retrieve': 'view',
            'create': 'add',
            'update': 'change',
            'partial_update': 'change',
            'destroy': 'delete',
        }
        
        action = action_map.get(view.action)
        if not action:
            return True  # Allow other custom actions by default
            
        return request.user.has_model_permission(model, action)

class HasModelPermission(BasePermission):
    """Check if user has specific model permission"""
    def __init__(self, model, action):
        self.model = model
        self.action = action

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.role in ['superadmin', 'master']:
            return True
            
        return request.user.has_model_permission(self.model, self.action)
    

class CanApproveFundRequest(BasePermission):
    """Check if user can approve fund requests"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow specific actions for all authenticated users
        if view.action in ['create', 'my_requests', 'list']:
            return True
            
        # Approval actions require admin or onboarder permissions
        if view.action in ['approve', 'reject', 'pending_requests']:
            return request.user.role in ['superadmin', 'admin', 'master', 'dealer']
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if view.action in ['approve', 'reject']:
            return obj.can_approve(request.user)
        return True
    

class AllowBasicActions(BasePermission):
    """Allow basic actions without requiring specific permissions"""
    def has_permission(self, request, view):
        basic_actions = [
            'login', 'verify_otp', 'forgot_password', 'verify_forgot_password_otp', 
            'reset_password', 'balance', 'transaction_history', 'my_requests',
            'my_profile', 'change_password', 'request_pin_otp', 'verify_pin_otp',
            'set_pin_with_otp', 'reset_pin_with_otp', 'verify_pin', 'bank_list',
            'bank_options', 'complete_first_time_setup'
        ]
        
        if hasattr(view, 'action') and view.action in basic_actions:
            if view.action in ['login', 'verify_otp', 'forgot_password', 'verify_forgot_password_otp', 'reset_password']:
                return True
            return bool(request.user and request.user.is_authenticated)
        
        return True 