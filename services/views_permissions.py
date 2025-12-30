from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth import get_user_model

from services.models import RoleServicePermission, UserServicePermission, ServiceCategory, ServiceSubCategory
from services.serializers import (
    RoleServicePermissionSerializer, UserServicePermissionSerializer,
    BulkRolePermissionSerializer, BulkUserPermissionSerializer,
    AvailableServicesSerializer, ServiceCategorySerializer, ServiceSubCategorySerializer
)

User = get_user_model()

class ServicePermissionViewSet(viewsets.ViewSet):
    """Manage service permissions for roles and users"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RoleServicePermission.objects.all()
    
    # Role Permissions Management
    
    @action(detail=False, methods=['get'])
    def role_permissions(self, request):
        """Get all role permissions"""
        role = request.query_params.get('role')
        
        if not role:
            return Response(
                {'error': 'role parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permissions = RoleServicePermission.objects.filter(role=role)
        serializer = RoleServicePermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    
    
    @action(detail=False, methods=['post'])
    def bulk_role_permissions(self, request):
        """Bulk update role permissions"""
        serializer = BulkRolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        role = serializer.validated_data['role']
        permissions_data = serializer.validated_data['permissions']
        
        created_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for perm_data in permissions_data:
                service_category_id = perm_data.get('service_category_id')
                service_subcategory_id = perm_data.get('service_subcategory_id')
                
                # Validate that either category or subcategory is provided, not both
                if not service_category_id and not service_subcategory_id:
                    errors.append(f"Permission must have either category or subcategory: {perm_data}")
                    continue
                
                if service_category_id and service_subcategory_id:
                    errors.append(f"Permission cannot have both category and subcategory: {perm_data}")
                    continue
                
                try:
                    # Find existing permission
                    if service_category_id:
                        existing_perm = RoleServicePermission.objects.filter(
                            role=role,
                            service_category_id=service_category_id
                        ).first()
                    else:
                        existing_perm = RoleServicePermission.objects.filter(
                            role=role,
                            service_subcategory_id=service_subcategory_id
                        ).first()
                    
                    if existing_perm:
                        # Update existing permission
                        existing_perm.is_active = bool(perm_data.get('is_active', True))
                        existing_perm.can_view = bool(perm_data.get('can_view', True))
                        existing_perm.can_use = bool(perm_data.get('can_use', True))
                        existing_perm.save()
                        updated_count += 1
                    else:
                        # Create new permission
                        RoleServicePermission.objects.create(
                            role=role,
                            service_category_id=service_category_id,
                            service_subcategory_id=service_subcategory_id,
                            is_active=bool(perm_data.get('is_active', True)),
                            can_view=bool(perm_data.get('can_view', True)),
                            can_use=bool(perm_data.get('can_use', True)),
                            created_by=request.user
                        )
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing permission {perm_data}: {str(e)}")
        
        response_data = {
            'message': f'Created {created_count}, updated {updated_count} permissions',
            'role': role,
            'total_processed': len(permissions_data),
            'errors': errors if errors else None
        }
        
        return Response(response_data, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)
    
    # User Permissions Management
    
    @action(detail=False, methods=['get'])
    def user_permissions(self, request):
        """Get user permissions"""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            permissions = UserServicePermission.objects.filter(user=user)
            serializer = UserServicePermissionSerializer(permissions, many=True)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def bulk_user_permissions(self, request):
        """Bulk update user permissions"""
        serializer = BulkUserPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        permissions_data = serializer.validated_data['permissions']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        created_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for perm_data in permissions_data:
                service_category_id = perm_data.get('service_category_id')
                service_subcategory_id = perm_data.get('service_subcategory_id')
                
                # Validate that either category or subcategory is provided, not both
                if not service_category_id and not service_subcategory_id:
                    errors.append(f"Permission must have either category or subcategory: {perm_data}")
                    continue
                
                if service_category_id and service_subcategory_id:
                    errors.append(f"Permission cannot have both category and subcategory: {perm_data}")
                    continue
                
                try:
                    # Find existing permission
                    existing_perm = UserServicePermission.objects.filter(
                        user=user,
                        service_category_id=service_category_id,
                        service_subcategory_id=service_subcategory_id
                    ).first()
                    
                    if existing_perm:
                        # Update existing permission
                        for field in ['is_active', 'can_view', 'can_use']:
                            if field in perm_data:
                                setattr(existing_perm, field, bool(perm_data[field]))
                        existing_perm.save()
                        updated_count += 1
                    else:
                        # Create new permission
                        UserServicePermission.objects.create(
                            user=user,
                            service_category_id=service_category_id,
                            service_subcategory_id=service_subcategory_id,
                            is_active=bool(perm_data.get('is_active', True)),
                            can_view=bool(perm_data.get('can_view', True)),
                            can_use=bool(perm_data.get('can_use', True)),
                            created_by=request.user
                        )
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing permission {perm_data}: {str(e)}")
        
        response_data = {
            'message': f'Created {created_count}, updated {updated_count} permissions for {user.username}',
            'user_id': user_id,
            'total_processed': len(permissions_data),
            'errors': errors if errors else None
        }
        
        return Response(response_data, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)
    
    # Available Services
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_services(self, request):
        """Get services available for current user"""
        user = request.user
        
        categories = ServiceCategory.objects.get_available_categories(user)
        subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
        serializer = AvailableServicesSerializer({
            'categories': categories,
            'subcategories': subcategories
        })
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available_services(self, request):
        """Get services available for specific user"""
        user_id = request.query_params.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            user = request.user
        
        categories = ServiceCategory.objects.get_available_categories(user)
        subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
        response_data = {
            'categories': ServiceCategorySerializer(categories, many=True).data,
            'subcategories': ServiceSubCategorySerializer(subcategories, many=True).data,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }
        
        return Response(response_data)
    


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available_services_detailed(self, request):
        """Get services available for specific user with detailed permission info"""
        user_id = request.query_params.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            user = request.user
        
        categories = ServiceCategory.objects.get_available_categories(user)
        subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
        user_permissions = UserServicePermission.objects.filter(user=user, is_active=True)
        role_permissions = RoleServicePermission.objects.filter(role=user.role, is_active=True)
        
        response_data = {
            'categories': ServiceCategorySerializer(categories, many=True).data,
            'subcategories': ServiceSubCategorySerializer(subcategories, many=True).data,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            },
            'permissions': {
                'user_permissions': UserServicePermissionSerializer(user_permissions, many=True).data,
                'role_permissions': RoleServicePermissionSerializer(role_permissions, many=True).data
            }
        }
        
        return Response(response_data)