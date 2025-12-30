from django.db import models


class ServiceManager(models.Manager):
    def get_available_categories(self, user):
        """Get categories available for user"""
        from .models import ServiceCategory, RoleServicePermission, UserServicePermission
        
        all_categories = ServiceCategory.objects.filter(is_active=True)
        available_categories = []
        
        for category in all_categories:
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=category,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view:
                    available_categories.append(category)
                continue
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=category,
                is_active=True
            ).first()
            
            if role_perm and role_perm.can_view:
                available_categories.append(category)
        
        return available_categories
    
    def get_available_subcategories(self, user, category=None):
        """Get subcategories available for user"""
        from .models import ServiceSubCategory, RoleServicePermission, UserServicePermission
        
        if category:
            subcategories = ServiceSubCategory.objects.filter(
                category=category, 
                is_active=True
            )
        else:
            subcategories = ServiceSubCategory.objects.filter(is_active=True)
        
        available_subcategories = []
        
        for subcategory in subcategories:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view:
                    available_subcategories.append(subcategory)
                continue
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if role_perm and role_perm.can_view:
                available_subcategories.append(subcategory)
        
        return available_subcategories
    
    def get_available_subcategories(self, user, category=None):
        """Get subcategories available for user"""
        from .models import ServiceSubCategory, RoleServicePermission, UserServicePermission
        
        if category:
            subcategories = ServiceSubCategory.objects.filter(
                category=category, 
                is_active=True
            )
        else:
            subcategories = ServiceSubCategory.objects.filter(is_active=True)
        
        available_subcategories = []
        
        for subcategory in subcategories:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                if user_perm.can_view and user_perm.can_use:
                    available_subcategories.append(subcategory)
                continue
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=subcategory,
                is_active=True
            ).first()
            
            if role_perm and role_perm.can_view and role_perm.can_use:
                available_subcategories.append(subcategory)
        
        return available_subcategories
    
    def can_access_service(self, user, service_category=None, service_subcategory=None):
        """Check if user can access specific service"""
        from .models import RoleServicePermission, UserServicePermission
        
        if service_category:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_category=service_category,
                is_active=True
            ).first()
            
            if user_perm:
                return user_perm.can_view and user_perm.can_use
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_category=service_category,
                is_active=True
            ).first()
            
            if role_perm:
                return role_perm.can_view and role_perm.can_use
                
        elif service_subcategory:
            # Check user-specific permissions first
            user_perm = UserServicePermission.objects.filter(
                user=user,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if user_perm:
                return user_perm.can_view and user_perm.can_use
            
            # Check role permissions
            role_perm = RoleServicePermission.objects.filter(
                role=user.role,
                service_subcategory=service_subcategory,
                is_active=True
            ).first()
            
            if role_perm:
                return role_perm.can_view and role_perm.can_use
        
        return False