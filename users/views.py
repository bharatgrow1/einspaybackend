from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.db import transaction as db_transaction
from django.db.models import Q, Sum, Count, F
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from services.models import ServiceSubmission
from .utils.twilio_service import twilio_service
from .email_utils import send_otp_email
from decimal import Decimal


from users.models import (Wallet, Transaction,  ServiceCharge, FundRequest, UserService, User, 
                          RolePermission, State, City, FundRequest, EmailOTP, ForgotPasswordOTP, 
                           MobileOTP, ForgetPinOTP, WalletPinOTP )

from services.models import ServiceSubCategory
from users.permissions import (IsSuperAdmin, IsAdminUser)
from users.serializers import (LoginSerializer, OTPVerifySerializer, WalletSerializer, SetWalletPinSerializer,
        ResetWalletPinSerializer, VerifyWalletPinSerializer, TransactionCreateSerializer, TransactionSerializer,
        TransactionFilterSerializer, ServiceChargeSerializer, WalletBalanceResponseSerializer, FundRequestHistorySerializer,
        ServiceSubCategorySerializer, UserServiceSerializer, UserCreateSerializer, UserSerializer, PermissionSerializer,
        UserPermissionsSerializer, ContentTypeSerializer, GrantRolePermissionSerializer, ModelPermissionSerializer,
        RolePermissionSerializer, ForgotPasswordSerializer, VerifyForgotPasswordOTPSerializer, ResetPasswordSerializer,
        StateSerializer, CitySerializer, FundRequestCreateSerializer, FundRequestUpdateSerializer, FundRequestApproveSerializer,
        FundRequestStatsSerializer, RequestWalletPinOTPSerializer, VerifyWalletPinOTPSerializer, SetWalletPinWithOTPSerializer,
        ForgetPinRequestOTPSerializer, VerifyForgetPinOTPSerializer, ResetPinWithForgetOTPSerializer, UserProfileUpdateSerializer,
        UserKYCSerializer, MobileOTPLoginSerializer, MobileOTPVerifySerializer, UserPermissionSerializer, ResetWalletPinWithOTPSerializer)

from commission.models import CommissionTransaction

import logging

logger = logging.getLogger(__name__)


if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class PermissionViewSet(viewsets.ViewSet):
    """Manage permissions - Super Admin and Master only"""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['all_permissions', 'model_permissions', 'user_permissions', 'role_permissions']:
            return [IsAdminUser()]
        return [IsSuperAdmin()]

    def list(self, request):
        """Default list view"""
        return Response({
            "message": "Permission management endpoints",
            "available_actions": [
                "all_permissions",
                "model_permissions", 
                "assign_user_permissions",
                "user_permissions",
                "available_models",
                "grant_role_permissions",
                "role_permissions"
            ]
        })
        

    @action(detail=False, methods=['get'])
    def all_permissions(self, request):
        """Get all available permissions in system"""
        permissions = Permission.objects.all().select_related('content_type')
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def model_permissions(self, request):
        """Get permissions for specific model"""
        model_name = request.query_params.get('model')
        app_label = request.query_params.get('app_label')
        
        if not model_name or not app_label:
            return Response(
                {'error': 'Both model and app_label parameters are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            permissions = Permission.objects.filter(content_type=content_type)
            serializer = PermissionSerializer(permissions, many=True)
            return Response(serializer.data)
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Model not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def assign_user_permissions(self, request):
        """Assign permissions to specific user"""
        serializer = UserPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        permission_ids = serializer.validated_data['permission_ids']
        
        try:
            user = User.objects.get(id=user_id)
            permissions = Permission.objects.filter(id__in=permission_ids)
            
            # Clear existing permissions and assign new ones
            user.user_permissions.clear()
            user.user_permissions.add(*permissions)
            
            return Response({
                'message': f'Assigned {permissions.count()} permissions to {user.username}',
                'user': UserPermissionsSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def user_permissions(self, request):
        """Get permissions for specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            serializer = UserPermissionsSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def available_models(self, request):
        """Get all available models in the system"""
        models_list = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                # Skip Django internal models
                if app_config.label in ['auth', 'contenttypes', 'sessions', 'admin']:
                    continue
                    
                content_type = ContentType.objects.get_for_model(model)
                permissions = Permission.objects.filter(content_type=content_type)
                
                models_list.append({
                    'app_label': app_config.label,
                    'model_name': model._meta.model_name,
                    'verbose_name': model._meta.verbose_name,
                    'verbose_name_plural': model._meta.verbose_name_plural,
                    'content_type_id': content_type.id,
                    'permissions_count': permissions.count()
                })
        
        return Response(models_list)

    @action(detail=False, methods=['post'])
    def grant_role_permissions(self, request):
        """Grant permissions to a role"""
        serializer = GrantRolePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        role = serializer.validated_data['role']
        permission_ids = serializer.validated_data['permission_ids']
        
        permissions = Permission.objects.filter(id__in=permission_ids)
        granted_count = 0
        
        for permission in permissions:
            role_perm, created = RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
                defaults={'granted_by': request.user}
            )
            if created:
                granted_count += 1
        
        return Response({
            'message': f'Granted {granted_count} permissions to {role} role',
            'role': role,
            'granted_permissions': PermissionSerializer(permissions, many=True).data
        })

    @action(detail=False, methods=['get'])
    def role_permissions(self, request):
        """Get all permissions for a specific role"""
        role = request.query_params.get('role')
        if not role:
            return Response(
                {'error': 'role parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role_permissions = RolePermission.objects.filter(role=role).select_related('permission')
        serializer = RolePermissionSerializer(role_permissions, many=True)
        
        return Response({
            'role': role,
            'permissions': serializer.data
        })

class AuthViewSet(viewsets.ViewSet):
    """Handles login with password + OTP verification"""

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Step 1: Verify username/password and send OTP"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp = otp_obj.generate_otp()
        send_otp_email(user.email, otp, is_password_reset=False)

        return Response({'message': 'OTP sent to your email'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verify_otp(self, request):
        """Step 2: Verify OTP and return JWT tokens"""
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(username=username)
            otp_obj = EmailOTP.objects.get(user=user, otp=otp)
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({'error': 'Invalid OTP or username'}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.delete()

        try:
            wallet = user.wallet
        except Wallet.DoesNotExist:
            wallet = Wallet.objects.create(user=user, balance=0.00)

        refresh = RefreshToken.for_user(user)
        
        needs_pin_setup = not wallet.is_pin_set
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'user_id': user.id,
            'username': user.username,
            'needs_pin_setup': needs_pin_setup, 
            'is_pin_set': wallet.is_pin_set,
            'permissions': list(user.get_all_permissions())
        }, status=status.HTTP_200_OK)
        


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_first_time_setup(self, request):
        """Mark user as completed first time setup"""
        user = request.user
        user.has_completed_first_time_setup = True
        user.save()
        
        return Response({
            'message': 'First time setup completed successfully',
            'has_completed_first_time_setup': user.has_completed_first_time_setup
        })

    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        """Step 1: Request OTP for password reset"""
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']

        try:
            user = User.objects.get(username=username)
            otp_obj, _ = ForgotPasswordOTP.objects.get_or_create(user=user)
            otp = otp_obj.generate_otp()
            
            send_otp_email(user.email, otp, is_password_reset=True)

            return Response({
                'message': 'OTP sent to your email for password reset',
                'username': username
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def verify_forgot_password_otp(self, request):
        """Step 2: Verify OTP for password reset"""
        serializer = VerifyForgotPasswordOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(username=username)
            otp_obj = ForgotPasswordOTP.objects.get(user=user, otp=otp, is_used=False)
        except (User.DoesNotExist, ForgotPasswordOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'OTP verified successfully',
            'username': username,
            'otp': otp
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """Step 3: Reset password with verified OTP"""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(username=username)
            otp_obj = ForgotPasswordOTP.objects.get(user=user, otp=otp, is_used=False)
        except (User.DoesNotExist, ForgotPasswordOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or username'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        otp_obj.mark_used()

        ForgotPasswordOTP.objects.filter(user=user).delete()

        return Response({
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def send_mobile_otp(self, request):
        """Send OTP to mobile number with proper Twilio integration"""
        serializer = MobileOTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        
        # Check if user exists
        try:
            user = User.objects.get(phone_number=mobile)
            logger.info(f"✅ User found: {user.username} for mobile: {mobile}")
        except User.DoesNotExist:
            logger.error(f"❌ User not found for mobile: {mobile}")
            return Response(
                {'error': 'No account found with this mobile number'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # DEBUG: Log Twilio service status
        logger.info(f"🔧 Twilio Service Status - Client: {twilio_service.client}")
        logger.info(f"🔧 Twilio Service SID: {twilio_service.verify_service_sid}")
        
        # Try Twilio first
        if twilio_service and twilio_service.client:
            logger.info(f"🔧 Trying Twilio for: {mobile}")
            result = twilio_service.send_otp_sms(mobile)
            
            logger.info(f"🔧 Twilio Result: {result}")
            
            if result['success']:
                logger.info(f"✅ Twilio OTP sent successfully")
                # Also create database entry as backup
                otp_obj, created = MobileOTP.objects.get_or_create(
                    mobile=mobile,
                    defaults={'expires_at': timezone.now() + timedelta(minutes=10)}
                )
                if created:
                    otp_obj.generate_otp()
                
                return Response({
                    'message': 'OTP sent successfully to your mobile',
                    'mobile': mobile,
                    'method': 'twilio',
                    'status': result['status']
                })
            else:
                logger.warning(f"⚠️ Twilio failed: {result.get('error')}")
                return Response({
                    'error': f"Failed to send OTP via Twilio: {result.get('error')}",
                    'mobile': mobile
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Fallback to database OTP
        logger.info(f"🔧 Using database OTP fallback for: {mobile}")
        try:
            otp_obj, created = MobileOTP.objects.get_or_create(
                mobile=mobile,
                defaults={'expires_at': timezone.now() + timedelta(minutes=10)}
            )
            otp, token = otp_obj.generate_otp()
            
            # In development, you might want to log the OTP
            if settings.DEBUG:
                logger.info(f"📱 Database OTP for {mobile}: {otp}")
            
            return Response({
                'message': 'OTP generated successfully',
                'mobile': mobile,
                'method': 'database_fallback',
                'note': 'Twilio service unavailable, using database OTP'
            })
        except Exception as e:
            logger.error(f"❌ Database OTP creation failed: {e}")
            return Response(
                {'error': 'Failed to generate OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify_mobile_otp(self, request):
        """Verify mobile OTP with both Twilio and database fallback"""
        serializer = MobileOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        otp = serializer.validated_data['otp']
        
        verification_method = None
        is_verified = False

        # First try Twilio verification
        if twilio_service and twilio_service.client:
            formatted_mobile = mobile
            if not mobile.startswith('+'):
                formatted_mobile = '+91' + mobile
                
            result = twilio_service.verify_otp(formatted_mobile, otp)
            if result['success'] and result['valid']:
                verification_method = 'twilio'
                is_verified = True
                logger.info(f"✅ Twilio OTP verification successful for: {mobile}")

        # If Twilio fails or not available, try database verification
        if not is_verified:
            logger.info(f"🔧 Trying database OTP verification for: {mobile}")
            try:
                otp_obj = MobileOTP.objects.get(
                    mobile=mobile,
                    otp=otp,
                    is_verified=False
                )
                
                if otp_obj.is_expired():
                    return Response(
                        {'error': 'OTP has expired. Please request a new one.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Mark OTP as verified
                otp_obj.mark_verified()
                verification_method = 'database'
                is_verified = True
                logger.info(f"✅ Database OTP verification successful for: {mobile}")
                
            except MobileOTP.DoesNotExist:
                logger.error(f"❌ Invalid OTP for mobile: {mobile}")
                return Response(
                    {'error': 'Invalid OTP. Please check and try again.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not is_verified:
            return Response(
                {'error': 'OTP verification failed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get user and generate tokens
        try:
            user = User.objects.get(phone_number=mobile)
            
            # Get or create wallet
            wallet, created = Wallet.objects.get_or_create(user=user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'role': user.role,
                'user_id': user.id,
                'username': user.username,
                'needs_pin_setup': not wallet.is_pin_set,
                'is_pin_set': wallet.is_pin_set,
                'permissions': list(user.get_all_permissions()),
                'message': 'Login successful',
                'verification_method': verification_method
            })

        except User.DoesNotExist:
            logger.error(f"❌ User not found after OTP verification for mobile: {mobile}")
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def resend_mobile_otp(self, request):
        """Resend OTP to mobile number"""
        serializer = MobileOTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        
        try:
            user = User.objects.get(phone_number=mobile)
        except User.DoesNotExist:
            return Response(
                {'error': 'No account found with this mobile number'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        result = twilio_service.send_otp_sms(mobile)
        
        if not result['success']:
            return Response(
                {'error': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'message': 'OTP resent successfully',
            'mobile': mobile,
            'status': result['status']
        })



class DynamicModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically handles model permissions
    Extend this for any model that needs permission control
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_admin_user():
            return queryset
            
        if hasattr(self.queryset.model, 'user'):
            return queryset.filter(user=user)
        if hasattr(self.queryset.model, 'wallet'):
            return queryset.filter(wallet__user=user)
        if hasattr(self.queryset.model, 'created_by'):
            return queryset.filter(created_by=user)
            
        return queryset.none()

class UserViewSet(DynamicModelViewSet):
    """CRUD for Users with dynamic permissions"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated] 


    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """Simplify permissions"""
        if self.action in ['my_profile', 'change_password', 'available_services']:
            return [IsAuthenticated()]
        elif self.action in ['all_users', 'change_role']:
            return [IsAdminUser()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    


    @action(detail=False, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update user profile information"""
        user = request.user
        serializer = UserProfileUpdateSerializer(
            user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'user': UserSerializer(user, context={'request': request}).data
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_profile_picture(self, request):
        """Upload or update profile picture"""
        user = request.user
        
        if 'profile_picture' not in request.FILES:
            return Response(
                {'error': 'Profile picture file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.profile_picture:
            pass
        
        user.profile_picture = request.FILES['profile_picture']
        user.save()
        
        return Response({
            'message': 'Profile picture uploaded successfully',
            'profile_picture': user.profile_picture.url if user.profile_picture else None
        })

    @action(detail=False, methods=['get', 'post', 'put', 'patch'], permission_classes=[IsAuthenticated])
    def kyc(self, request):
        """Handle KYC submission and retrieval"""
        user = request.user
        
        if request.method == 'GET':
            serializer = UserKYCSerializer(user)
            return Response(serializer.data)
        
        elif request.method in ['POST', 'PUT', 'PATCH']:
            serializer = UserKYCSerializer(
                user, 
                data=request.data, 
                partial=True, 
                context={'request': request}
            )
            
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return Response({
                'message': 'KYC information saved successfully',
                'kyc_data': serializer.data
            })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_kyc_document(self, request):
        """Upload specific KYC documents using URL (like profile picture)"""
        user = request.user
        document_type = request.data.get('document_type')
        
        if not document_type or document_type not in [
            'pan_card', 'aadhar_card', 'passport_photo', 
            'shop_photo', 'store_photo', 'other_documents'
        ]:
            return Response(
                {'error': 'Valid document type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document_url = request.data.get('document_url')
        
        if not document_url:
            return Response(
                {'error': 'Document URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        setattr(user, document_type, document_url)
        user.save()
        
        return Response({
            'message': f'{document_type.replace("_", " ").title()} uploaded successfully',
            'document_url': document_url
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def kyc_status(self, request):
        """Get KYC completion status"""
        user = request.user
        
        required_fields = [
            'first_name', 'last_name', 'phone_number', 'aadhar_number', 'pan_number',
            'date_of_birth', 'address', 'city', 'state', 'pincode',
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name'
        ]
        
        completed_fields = []
        missing_fields = []
        
        for field in required_fields:
            value = getattr(user, field)
            if value and str(value).strip():
                completed_fields.append(field)
            else:
                missing_fields.append(field)
        
        completion_percentage = int((len(completed_fields) / len(required_fields)) * 100)
        
        required_documents = ['pan_card', 'aadhar_card', 'passport_photo']
        uploaded_documents = []
        missing_documents = []
        
        for doc in required_documents:
            if getattr(user, doc):
                uploaded_documents.append(doc)
            else:
                missing_documents.append(doc)
        
        document_completion_percentage = int((len(uploaded_documents) / len(required_documents)) * 100)
        
        overall_completion = int((completion_percentage + document_completion_percentage) / 2)
        
        return Response({
            'kyc_status': {
                'overall_completion': overall_completion,
                'personal_info_completion': completion_percentage,
                'document_completion': document_completion_percentage,
                'is_kyc_completed': overall_completion >= 80,
                'completed_fields': completed_fields,
                'missing_fields': missing_fields,
                'uploaded_documents': uploaded_documents,
                'missing_documents': missing_documents
            }
        })

    def create(self, request, *args, **kwargs):
        """Create user with role-based permissions"""
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        current_user = request.user


        if current_user.role == 'retailer':
            return Response(
                {'error': 'You do not have permission to create users'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        
        serializer.validated_data['created_by'] = request.user
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'superadmin':
            return User.objects.all()
        elif user.role == 'admin':
            return User.objects.exclude(role='superadmin')
        elif user.role == 'master':
            return User.objects.filter(role__in=['master', 'dealer', 'retailer'])
        elif user.role == 'dealer':
            return User.objects.filter(role='retailer', created_by=user)
        else:
            return User.objects.filter(id=user.id)
    

    def destroy(self, request, *args, **kwargs):
        user_to_delete = self.get_object()
        current_user = request.user
        
        if user_to_delete == current_user:
            return Response(
                {'error': 'You cannot delete your own account'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'superadmin' and current_user.role != 'superadmin':
            return Response(
                {'error': 'Only Super Admin can delete Super Admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'admin' and current_user.role not in ['superadmin', 'admin']:
            return Response(
                {'error': 'Only Admin and Super Admin can delete Admin users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'master' and current_user.role not in ['superadmin', 'admin']:
            return Response(
                {'error': 'Only Admin and Super Admin can delete Master users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if user_to_delete.role == 'retailer' and current_user.role == 'dealer':
            if user_to_delete.created_by != current_user:
                return Response(
                    {'error': 'You can only delete retailers created by you'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_profile(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change current user's password"""
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def all_users(self, request):
        users = User.objects.all()
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in dict(User.ROLE_CHOICES):
            return Response(
                {'error': 'Invalid role'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = new_role
        user.save()
        
        return Response({
            'message': f'User {user.username} role changed to {new_role}',
            'user': UserSerializer(user).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_services(self, request, pk=None):
        """Update user services"""
        user = self.get_object()
        service_ids = request.data.get('service_ids', [])
        
        try:
            UserService.objects.filter(user=user).delete()
            
            for service_id in service_ids:
                try:
                    service = ServiceSubCategory.objects.get(id=service_id, is_active=True)
                    UserService.objects.create(user=user, service=service)
                except ServiceSubCategory.DoesNotExist:
                    continue
            
            return Response({
                'message': f'Updated {len(service_ids)} services for user {user.username}',
                'services': UserServiceSerializer(user.user_services.all(), many=True).data
            })
        except Exception as e:
            return Response({'error': f'Service update failed: {str(e)}'}, status=400)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available_services(self, request):
        """Get all available services for user creation"""
        try:
            services = ServiceSubCategory.objects.filter(is_active=True).select_related('category')
            serializer = ServiceSubCategorySerializer(services, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': f'Service fetch failed: {str(e)}'}, status=400)
        

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_onboarder_banks(self, request):
        """Get bank details of the user who created current user"""
        user = request.user
        onboarder = user.created_by
        
        if not onboarder:
            return Response({
                'message': 'No onboarder found',
                'banks': []
            })
        
        bank_data = {
            'id': onboarder.id,
            'bank_name': onboarder.bank_name,
            'account_number': onboarder.account_number,
            'ifsc_code': onboarder.ifsc_code,
            'account_holder_name': onboarder.account_holder_name
        }
        
        return Response({
            'onboarder': {
                'id': onboarder.id,
                'username': onboarder.username,
                'role': onboarder.role
            },
            'bank_details': bank_data
        })


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_bank_details(self, request):
        """Get current user's bank details"""
        user = request.user
        
        bank_data = {
            'id': user.id,
            'bank_name': user.bank_name,
            'account_number': user.account_number,
            'ifsc_code': user.ifsc_code,
            'account_holder_name': user.account_holder_name
        }
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            },
            'bank_details': bank_data
        })

class WalletViewSet(DynamicModelViewSet):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user():
            return Wallet.objects.all()
        return Wallet.objects.filter(user=user)
    
    def get_permissions(self):
        """Custom permissions for wallet"""
        if self.action in ['request_pin_otp', 'verify_pin_otp', 'reset_pin_with_otp']:
            return [AllowAny()]
        elif self.action in ['balance', 'transaction_history', 'set_pin_with_otp', 
                          'verify_pin', 'set_pin', 'reset_pin']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    


    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def forget_pin_request_otp(self, request):
        """Step 1: Request OTP for forget PIN - NO AUTH REQUIRED"""
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User with this email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has a wallet
        if not hasattr(user, 'wallet'):
            return Response(
                {'error': 'Wallet not found for this user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete any existing OTPs
        ForgetPinOTP.objects.filter(user=user).delete()
        
        # Create new OTP
        otp_obj = ForgetPinOTP.objects.create(user=user)
        otp = otp_obj.generate_otp()
        
        try:
            send_otp_email(
                user.email, 
                otp, 
                is_password_reset=False,
                purpose='forget_pin'
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': 'OTP sent to your email for PIN reset',
            'email': email
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])  # ✅ Important: AllowAny
    def verify_forget_pin_otp(self, request):
        """Step 2: Verify OTP for forget PIN - NO AUTH REQUIRED"""
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email or not otp:
            return Response(
                {'error': 'Email and OTP are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            otp_obj = ForgetPinOTP.objects.get(
                user=user, 
                otp=otp, 
                is_used=False
            )
        except (User.DoesNotExist, ForgetPinOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as used
        otp_obj.mark_used()
        
        return Response({
            'message': 'OTP verified successfully',
            'email': email,
            'user_id': user.id
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])  # ✅ Important: AllowAny
    def reset_pin_with_forget_otp(self, request):
        """Step 3: Reset PIN after OTP verification - NO AUTH REQUIRED"""
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_pin = request.data.get('new_pin')
        confirm_pin = request.data.get('confirm_pin')
        
        if not all([email, otp, new_pin, confirm_pin]):
            return Response(
                {'error': 'All fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_pin != confirm_pin:
            return Response(
                {'error': 'PINs do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_pin) != 4 or not new_pin.isdigit():
            return Response(
                {'error': 'PIN must be exactly 4 digits'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            wallet = user.wallet
            
            # Verify OTP again for security
            otp_obj = ForgetPinOTP.objects.get(
                user=user, 
                otp=otp, 
                is_used=True  # Should be marked as used from previous step
            )
            
            if otp_obj.is_expired():
                return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
                
        except (User.DoesNotExist, ForgetPinOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Set new PIN directly (no old PIN verification needed in forget PIN flow)
            wallet.set_pin(new_pin)
            
            # Delete all OTPs for this user
            ForgetPinOTP.objects.filter(user=user).delete()
            
            return Response({'message': 'PIN reset successfully'})
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Failed to reset PIN: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def request_pin_otp(self, request):
        """Request OTP for wallet PIN operation - No auth required"""
        serializer = RequestWalletPinOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        purpose = serializer.validated_data['purpose']
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User with this email not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        WalletPinOTP.objects.filter(user=user, purpose=purpose).delete()
        
        otp_obj = WalletPinOTP.objects.create(user=user, purpose=purpose)
        otp = otp_obj.generate_otp()
        
        try:
            send_otp_email(
                user.email, 
                otp, 
                is_password_reset=False,
                purpose=f"wallet_{purpose}"
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': f'OTP sent to your email for {purpose.replace("_", " ")}',
            'purpose': purpose
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify_pin_otp(self, request):
        """Verify OTP for wallet PIN operation - No auth required"""
        serializer = VerifyWalletPinOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp = serializer.validated_data['otp']
        purpose = serializer.validated_data['purpose']
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            otp_obj = WalletPinOTP.objects.get(
                user=user, 
                purpose=purpose, 
                otp=otp, 
                is_used=False
            )
        except (User.DoesNotExist, WalletPinOTP.DoesNotExist):
            return Response(
                {'error': 'Invalid OTP or email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_obj.mark_used()
        
        return Response({
            'message': 'OTP verified successfully',
            'purpose': purpose,
            'user_id': user.id
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_pin_with_otp(self, request):
        """Set wallet PIN with OTP verification"""
        serializer = SetWalletPinWithOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet = request.user.wallet
        otp = serializer.validated_data['otp']
        pin = serializer.validated_data['pin']
        
        if wallet.is_pin_set:
            return Response(
                {'error': 'PIN is already set. Use reset-pin to change it.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            otp_obj = WalletPinOTP.objects.get(
                user=request.user, 
                purpose='set_pin', 
                otp=otp, 
                is_used=False
            )
        except WalletPinOTP.DoesNotExist:
            return Response(
                {'error': 'Invalid OTP or OTP already used'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wallet.set_pin(pin)
            otp_obj.mark_used()
            
            return Response({'message': 'PIN set successfully'})
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def reset_pin_with_otp(self, request):
        """Reset wallet PIN with OTP verification - No auth required"""
        serializer = ResetWalletPinWithOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp = serializer.validated_data['otp']
        new_pin = serializer.validated_data['new_pin']
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
            wallet = user.wallet
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            otp_obj = WalletPinOTP.objects.get(
                user=user, 
                purpose='reset_pin', 
                otp=otp, 
                is_used=False
            )
        except WalletPinOTP.DoesNotExist:
            return Response(
                {'error': 'Invalid OTP or OTP already used'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if otp_obj.is_expired():
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wallet.set_pin(new_pin)
            otp_obj.mark_used()
            
            return Response({'message': 'PIN reset successfully'})
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def set_pin(self, request):
        """OLD: Set wallet PIN without OTP (for backward compatibility)"""
        wallet = request.user.wallet
        
        if wallet.is_pin_set:
            return Response(
                {'error': 'PIN is already set. Use reset-pin to change it.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SetWalletPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            wallet.set_pin(serializer.validated_data['pin'])
            return Response({'message': 'PIN set successfully'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reset_pin(self, request):
        """OLD: Reset wallet PIN without OTP (for backward compatibility)"""
        wallet = request.user.wallet
        
        if not wallet.is_pin_set:
            return Response(
                {'error': 'PIN is not set. Use set-pin to set it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ResetWalletPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            wallet.reset_pin(
                serializer.validated_data['old_pin'],
                serializer.validated_data['new_pin']
            )
            return Response({'message': 'PIN reset successfully'})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_pin(self, request):
        """Verify wallet PIN"""
        wallet = request.user.wallet
        
        if not wallet.is_pin_set:
            return Response(
                {'error': 'PIN is not set'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VerifyWalletPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if wallet.verify_pin(serializer.validated_data['pin']):
            return Response({'message': 'PIN verified successfully'})
        else:
            return Response({'error': 'Invalid PIN'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def balance(self, request):
        """Get wallet balance - NO PIN REQUIRED"""
        wallet = request.user.wallet
        return Response({
            'balance': wallet.balance,
            'currency': 'INR',
            'is_pin_set': wallet.is_pin_set,
            'username': request.user.username 
        })

    @action(detail=False, methods=['get'],  permission_classes=[IsAuthenticated])
    def transaction_history(self, request):
        """Get complete transaction history with fund requests - NO PIN REQUIRED"""
        user = request.user
        
        transactions = Transaction.objects.filter(wallet__user=user).select_related(
            'wallet__user', 'created_by', 'recipient_user', 'service_submission'
        ).order_by('-created_at')
        
        fund_requests = FundRequest.objects.filter(user=user).order_by('-created_at')
        
        total_credit = transactions.filter(transaction_type='credit').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_debit = transactions.filter(transaction_type='debit').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        transaction_serializer = TransactionSerializer(transactions, many=True)
        fund_request_serializer = FundRequestHistorySerializer(fund_requests, many=True)
        
        return Response({
            'transactions': transaction_serializer.data,
            'fund_requests': fund_request_serializer.data,
            'total_count': transactions.count() + fund_requests.count(),
            'total_credit': total_credit,
            'total_debit': total_debit,
            'current_balance': user.wallet.balance
        })
    

class TransactionViewSet(DynamicModelViewSet):
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'transaction_category', 'status']
    search_fields = ['reference_number', 'description', 'recipient_user__username', 'service_name']
    ordering_fields = ['created_at', 'amount', 'net_amount']
    ordering = ['-created_at']


    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_admin_user():
            return queryset
            
        if hasattr(self.queryset.model, 'user'):
            return queryset.filter(user=user)
        if hasattr(self.queryset.model, 'wallet'):
            return queryset.filter(wallet__user=user)
        if hasattr(self.queryset.model, 'created_by'):
            return queryset.filter(created_by=user)
            
        return queryset.none()

    def create(self, request, *args, **kwargs):
        """Create a new transaction with PIN verification and service charges"""
        serializer = TransactionCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        wallet = request.user.wallet
        
        if data['transaction_type'] == 'debit':
            pin = data.get('pin')
            if not pin:
                return Response({'error': 'PIN required for debit transactions'}, status=400)
            
            if not wallet.verify_pin(pin):
                return Response({'error': 'Invalid PIN'}, status=400)
        
        pin = data.get('pin')
        amount = data['amount']
        service_charge = data['service_charge']
        service_submission_id = data.get('service_submission_id')
        
        try:
            with db_transaction.atomic():
                opening_balance = wallet.balance

                if data['transaction_type'] == 'debit':
                    total_deducted = wallet.deduct_amount(amount, service_charge, pin)
                else:
                    # For credit transactions, just add amount
                    wallet.add_amount(amount)
                    total_deducted = 0


                closing_balance = wallet.balance
                
                # Get service submission if provided
                service_submission = None
                if service_submission_id:
                    try:
                        service_submission = ServiceSubmission.objects.get(id=service_submission_id)
                    except ServiceSubmission.DoesNotExist:
                        pass
                
                # Create transaction record
                transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    net_amount=amount,
                    service_charge=service_charge,
                    transaction_type=data['transaction_type'],
                    transaction_category=data.get('transaction_category', 'other'),
                    description=data['description'],
                    created_by=request.user,
                    recipient_user=data.get('recipient_user'),
                    service_submission=service_submission,
                    service_name=data.get('service_name'),
                    status='success',
                    opening_balance=opening_balance,
                    closing_balance=closing_balance
                )
                
                # If there's a recipient for money transfer, add amount to their wallet
                recipient_user = data.get('recipient_user')
                if recipient_user and data['transaction_type'] == 'debit' and data.get('transaction_category') == 'money_transfer':
                    recipient_wallet = recipient_user.wallet

                    recipient_opening_balance = recipient_wallet.balance
                
                    recipient_wallet.add_amount(amount)
                    
                    recipient_closing_balance = recipient_wallet.balance
                    
                    # Create credit transaction for recipient
                    Transaction.objects.create(
                        wallet=recipient_wallet,
                        amount=amount,
                        net_amount=amount,
                        service_charge=0.00,
                        transaction_type='credit',
                        transaction_category='money_transfer',
                        description=f"Received from {request.user.username}",
                        created_by=request.user,
                        recipient_user=recipient_user,
                        status='success',
                        opening_balance=recipient_opening_balance,
                        closing_balance=recipient_closing_balance,
                        metadata={'sender_transaction_id': transaction.id}
                    )
                
                response_serializer = TransactionSerializer(transaction)
                return Response({
                    'message': 'Transaction completed successfully',
                    'data': response_serializer.data,
                    'service_charge': service_charge,
                    'total_deducted': total_deducted if data['transaction_type'] == 'debit' else 0,
                    'new_balance': wallet.balance
                }, status=status.HTTP_201_CREATED)
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Transaction failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def pay_for_service(self, request):
        """Special endpoint to pay for services with PIN verification"""
        serializer = TransactionCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        wallet = request.user.wallet
        pin = data.get('pin')
        amount = data['amount']
        service_charge = data['service_charge']
        service_submission_id = data.get('service_submission_id')
        
        # Validate service submission
        if not service_submission_id:
            return Response(
                {'error': 'service_submission_id is required for service payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service_submission = ServiceSubmission.objects.get(id=service_submission_id)
        except ServiceSubmission.DoesNotExist:
            return Response(
                {'error': 'Service submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            with db_transaction.atomic():
                opening_balance = wallet.balance
                total_deducted = wallet.deduct_amount(amount, service_charge, pin)
                closing_balance = wallet.balance
                if isinstance(amount, float):
                    amount = Decimal(str(amount))
                if isinstance(service_charge, float):
                    service_charge = Decimal(str(service_charge))
                
                # Deduct amount including service charge
                total_deducted = wallet.deduct_amount(amount, service_charge, pin)
                
                # Create transaction record
                transaction = Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    net_amount=amount,
                    service_charge=service_charge,
                    transaction_type='debit',
                    transaction_category='service_payment',
                    description=f"Payment for {service_submission.service_form.name if service_submission.service_form else 'Service'}",
                    created_by=request.user,
                    service_submission=service_submission,
                    service_name=service_submission.service_form.name if service_submission.service_form else 'Service Payment',
                    status='success',
                    opening_balance=opening_balance,
                    closing_balance=closing_balance  
                )
                
                # Update service submission payment status
                service_submission.payment_status = 'paid'
                service_submission.transaction_id = transaction.reference_number
                service_submission.save()
                
                response_serializer = TransactionSerializer(transaction)
                return Response({
                    'message': 'Service payment completed successfully',
                    'data': response_serializer.data,
                    'service_charge': service_charge,
                    'total_deducted': total_deducted,
                    'new_balance': wallet.balance,
                    'service_submission': {
                        'id': service_submission.id,
                        'submission_id': service_submission.submission_id,
                        'payment_status': 'paid'
                    }
                }, status=status.HTTP_201_CREATED)
                
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Service payment failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def filter_transactions(self, request):
        """Advanced transaction filtering"""
        filter_serializer = TransactionFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        
        filters_data = filter_serializer.validated_data
        queryset = self.get_queryset()
        
        # Apply filters
        if filters_data.get('transaction_type'):
            queryset = queryset.filter(transaction_type=filters_data['transaction_type'])
        
        if filters_data.get('transaction_category'):
            queryset = queryset.filter(transaction_category=filters_data['transaction_category'])
        
        if filters_data.get('status'):
            queryset = queryset.filter(status=filters_data['status'])
        
        if filters_data.get('start_date'):
            start_date = timezone.make_aware(
                datetime.combine(filters_data['start_date'], datetime.min.time())
            )
            queryset = queryset.filter(created_at__gte=start_date)
        
        if filters_data.get('end_date'):
            end_date = timezone.make_aware(
                datetime.combine(filters_data['end_date'], datetime.max.time())
            )
            queryset = queryset.filter(created_at__lte=end_date)
        
        if filters_data.get('min_amount'):
            queryset = queryset.filter(amount__gte=filters_data['min_amount'])
        
        if filters_data.get('max_amount'):
            queryset = queryset.filter(amount__lte=filters_data['max_amount'])
        
        if filters_data.get('user_id') and request.user.is_admin_user():
            queryset = queryset.filter(wallet__user_id=filters_data['user_id'])
        
        if filters_data.get('reference_number'):
            queryset = queryset.filter(reference_number__icontains=filters_data['reference_number'])
        
        if filters_data.get('service_submission_id'):
            queryset = queryset.filter(service_submission_id=filters_data['service_submission_id'])
        
        # Paginate and return results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get transaction statistics"""
        user = request.user
        queryset = self.get_queryset()
        
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(created_at__gte=start_date)
        
        stats = {
            'total_transactions': queryset.count(),
            'total_credit': queryset.filter(transaction_type='credit').aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'total_debit': queryset.filter(transaction_type='debit').aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'total_service_charges': queryset.aggregate(
                total=Sum('service_charge')
            )['total'] or 0,
            'transactions_by_category': queryset.values('transaction_category').annotate(
                count=Count('id'),
                total_amount=Sum('amount')
            ),
            'transactions_by_status': queryset.values('status').annotate(
                count=Count('id')
            ),
            'recent_transactions': TransactionSerializer(
                queryset[:10], many=True
            ).data
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def user_transactions(self, request):
        """Get transactions for specific user (admin only)"""
        if not request.user.is_admin_user():
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            transactions = Transaction.objects.filter(wallet__user=user)
            
            page = self.paginate_queryset(transactions)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def service_payments(self, request):
        """Get all service payment transactions - ONLY AVAILABLE FIELDS USE KARO"""
        # Base queryset
        queryset = Transaction.objects.filter(transaction_category='service_payment')
        
        # User-based filtering
        user = self.request.user
        if not user.is_admin_user():
            queryset = queryset.filter(wallet__user=user)
        
        # Filters apply karo
        service_name = request.query_params.get('service_name')
        if service_name:
            queryset = queryset.filter(
                Q(service_name__icontains=service_name) |
                Q(service_submission__service_form__name__icontains=service_name)
            )

        service_id = request.query_params.get('service_id')
        if service_id:
            queryset = queryset.filter(
                Q(service_submission__service_form_id=service_id)
            )

        # ✅ CORRECT: ONLY AVAILABLE FIELDS USE KARO
        queryset = queryset.select_related(
            'wallet__user', 
            'created_by', 
            'recipient_user', 
            'service_submission',                      # ✅ Available
            'service_submission__service_form',        # ✅ Available  
            'service_submission__service_subcategory', # ✅ Available
            'service_submission__submitted_by',        # ✅ Available (yeh created_by ki jagah hai)
        ).prefetch_related(
            'service_submission__service_form__fields'  # ✅ Available
        ).order_by('-created_at')

        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        


class ServiceChargeViewSet(DynamicModelViewSet):
    """Manage service charges"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = ServiceCharge.objects.all()
    serializer_class = ServiceChargeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['transaction_category', 'is_active']
    search_fields = ['transaction_category']

    @action(detail=False, methods=['post'])
    def calculate_charge(self, request):
        """Calculate service charge for a transaction"""
        amount = request.data.get('amount')
        transaction_category = request.data.get('transaction_category', 'other')
        
        if not amount:
            return Response(
                {'error': 'Amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            service_charge_config = ServiceCharge.objects.get(
                transaction_category=transaction_category, 
                is_active=True
            )
            service_charge = service_charge_config.calculate_charge(amount)
            
            return Response({
                'amount': amount,
                'transaction_category': transaction_category,
                'service_charge': service_charge,
                'total_amount': amount + service_charge,
                'charge_config': ServiceChargeSerializer(service_charge_config).data
            })
            
        except ServiceCharge.DoesNotExist:
            return Response({
                'amount': amount,
                'transaction_category': transaction_category,
                'service_charge': 0.00,
                'total_amount': amount,
                'charge_config': None
            })
        except ValueError:
            return Response(
                {'error': 'Invalid amount'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


# Add these ViewSets to your views.py
class OnBoardServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """API for services to be used in user onboarding"""
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceSubCategorySerializer
    
    def get_queryset(self):
        try:
            return ServiceSubCategory.objects.filter(is_active=True).select_related('category')
        except Exception as e:
            print(f"Service fetch error: {e}")
            return ServiceSubCategory.objects.none()
        

class StateViewSet(viewsets.ReadOnlyModelViewSet):
    """API for states"""
    permission_classes = [IsAuthenticated]
    queryset = State.objects.all()
    serializer_class = StateSerializer

class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """API for cities"""
    permission_classes = [IsAuthenticated]
    serializer_class = CitySerializer
    
    def get_queryset(self):
        queryset = City.objects.all()
        state_id = self.request.query_params.get('state')
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        return queryset 
    

class FundRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]


    def get_permissions(self):
        """Custom permissions for fund requests"""
        if self.action in ['create', 'my_requests', 'bank_list', 'bank_options', 'stats']:
            return [IsAuthenticated()]
        elif self.action in ['approve', 'reject', 'pending_requests']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference_number', 'remarks', 'user__username']
    ordering_fields = ['created_at', 'amount', 'updated_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FundRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FundRequestUpdateSerializer
        return FundRequestCreateSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['superadmin', 'admin']:
            return FundRequest.objects.all().select_related('user', 'processed_by')
        
        elif user.role in ['master', 'dealer']:
            onboarded_users = User.objects.filter(created_by=user)
            return FundRequest.objects.filter(user__in=onboarded_users).select_related('user', 'processed_by')
        
        else:
            return FundRequest.objects.filter(user=user).select_related('user', 'processed_by')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve fund request"""
        fund_request = self.get_object()
        
        if not fund_request.can_approve(request.user):
            return Response(
                {'error': 'You do not have permission to approve this request'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = FundRequestApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        admin_notes = serializer.validated_data.get('admin_notes', '')
        
        success, message = fund_request.approve(
            approved_by=request.user,
            notes=admin_notes
        )
        
        if success:
            fund_request.refresh_from_db()
            response_serializer = self.get_serializer(fund_request)
            return Response({
                'message': message,
                'data': response_serializer.data,
                'new_balance': fund_request.user.wallet.balance
            })
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_requests(self, request):
        """Get current user's fund requests"""
        fund_requests = FundRequest.objects.filter(user=request.user)
        page = self.paginate_queryset(fund_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(fund_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_requests(self, request):
        """Get pending requests for approvers"""
        user = request.user
        
        if user.role in ['superadmin', 'admin']:
            pending_requests = FundRequest.objects.filter(status='pending')
        elif user.role in ['master', 'dealer']:
            onboarded_users = User.objects.filter(created_by=user)
            pending_requests = FundRequest.objects.filter(
                user__in=onboarded_users, 
                status='pending'
            )
        else:
            return Response(
                {'error': 'You do not have permission to view pending requests'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        page = self.paginate_queryset(pending_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get fund request statistics"""
        user = request.user
        queryset = self.get_queryset()
        
        stats = {
            'total_requests': queryset.count(),
            'pending_requests': queryset.filter(status='pending').count(),
            'approved_requests': queryset.filter(status='approved').count(),
            'rejected_requests': queryset.filter(status='rejected').count(),
            'total_amount': queryset.aggregate(total=Sum('amount'))['total'] or 0,
            'pending_amount': queryset.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bank_list(self, request):
        """Get list of available banks"""
        banks = FundRequest.BANKS 
        bank_choices = [{'value': bank[0], 'display_name': bank[1]} for bank in banks]
        return Response({'banks': bank_choices})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bank_options(self, request):
        """Get bank options for dropdown"""
        banks = FundRequest.BANKS
        return Response({
            'deposit_banks': [{'value': bank[0], 'label': bank[1]} for bank in banks],
            'your_banks': [{'value': bank[0], 'label': bank[1]} for bank in banks]
        })
    


class UserHierarchyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_hierarchy(self, request):
        """Get current user's hierarchy - who created them and who they created"""
        user = request.user
        
        creator = user.created_by
        
        created_users = User.objects.filter(created_by=user).select_related('wallet')
        
        hierarchy_stats = {
            'total_downline': created_users.count(),
            'downline_by_role': created_users.values('role').annotate(count=Count('id')),
            'total_commission_earned': CommissionTransaction.objects.filter(
                user=user, status='success', transaction_type='credit'
            ).aggregate(total=Sum('commission_amount'))['total'] or 0
        }
        
        creator_data = None
        if creator:
            creator_data = {
                'id': creator.id,
                'username': creator.username,
                'role': creator.role,
                'phone_number': creator.phone_number,
                'created_at': creator.date_joined
            }
        
        created_users_data = []
        for created_user in created_users:
            user_data = {
                'id': created_user.id,
                'username': created_user.username,
                'role': created_user.role,
                'phone_number': created_user.phone_number,
                'created_at': created_user.date_joined,
                'wallet_balance': created_user.wallet.balance if hasattr(created_user, 'wallet') else 0,
                'services_count': created_user.user_services.count()
            }
            created_users_data.append(user_data)
        
        return Response({
            'current_user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'created_at': user.date_joined
            },
            'creator': creator_data,
            'created_users': created_users_data,
            'hierarchy_stats': hierarchy_stats
        })
    
    @action(detail=False, methods=['get'])
    def full_hierarchy(self, request):
        """Get full hierarchy tree for admin users"""
        if not request.user.is_admin_user():
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        def get_user_hierarchy(user, depth=0):
            """Recursively get user hierarchy"""
            created_users = User.objects.filter(created_by=user)
            
            user_data = {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'depth': depth,
                'created_at': user.date_joined,
                'wallet_balance': user.wallet.balance if hasattr(user, 'wallet') else 0,
                'total_commission_earned': CommissionTransaction.objects.filter(
                    user=user, status='success', transaction_type='credit'
                ).aggregate(total=Sum('commission_amount'))['total'] or 0,
                'downline': []
            }
            
            for created_user in created_users:
                user_data['downline'].append(get_user_hierarchy(created_user, depth + 1))
            
            return user_data
        
        # Start from superadmin users
        superadmins = User.objects.filter(role='superadmin')
        hierarchy_tree = []
        
        for superadmin in superadmins:
            hierarchy_tree.append(get_user_hierarchy(superadmin))
        
        return Response({
            'hierarchy_tree': hierarchy_tree,
            'total_users': User.objects.count(),
            'users_by_role': User.objects.values('role').annotate(count=Count('id'))
        })