from rest_framework import serializers
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from services.models import ServiceSubCategory
from django.core.validators import MinValueValidator
import re

from users.models import (Wallet, Transaction,  ServiceCharge, FundRequest, UserService, User, 
                          RolePermission, State, City, FundRequest)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class OTPVerifySerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)
 
class WalletSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    is_pin_set = serializers.BooleanField(read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'username', 'balance', 'is_pin_set', 'created_at', 'updated_at']
        read_only_fields = ['balance', 'created_at', 'updated_at']


class SetWalletPinSerializer(serializers.Serializer):
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    confirm_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

    def validate(self, data):
        if data['pin'] != data['confirm_pin']:
            raise serializers.ValidationError("PINs do not match")
        return data



class ResetWalletPinSerializer(serializers.Serializer):
    old_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    new_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    confirm_new_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_new_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

    def validate(self, data):
        if data['new_pin'] != data['confirm_new_pin']:
            raise serializers.ValidationError("New PINs do not match")
        return data


class VerifyWalletPinSerializer(serializers.Serializer):
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value



class TransactionCreateSerializer(serializers.ModelSerializer):
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=False)
    recipient_username = serializers.CharField(write_only=True, required=False)
    service_charge = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    service_submission_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'transaction_type', 'transaction_category', 
            'description', 'recipient_username', 'pin', 'service_charge', 
            'net_amount', 'service_submission_id', 'service_name'
        ]

    def validate(self, data):
        request = self.context.get('request')
        wallet = request.user.wallet
        
        # Check if PIN is required (only for debit transactions, not for balance check)
        if (data.get('transaction_type') == 'debit' and 
            wallet.is_pin_set and not data.get('pin')):
            raise serializers.ValidationError("PIN is required for debit transactions")
        
        # Validate amount
        amount = data.get('amount')
        if amount <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        
        # Calculate service charge for debit transactions
        transaction_category = data.get('transaction_category', 'other')
        service_charge = 0.00
        
        if data.get('transaction_type') == 'debit':
            try:
                service_charge_config = ServiceCharge.objects.get(
                    transaction_category=transaction_category, 
                    is_active=True
                )
                service_charge = service_charge_config.calculate_charge(amount)
            except ServiceCharge.DoesNotExist:
                service_charge = 0.00
        
        # Check sufficient balance including service charge for debit transactions
        if (data.get('transaction_type') == 'debit' and 
            not wallet.has_sufficient_balance(amount, service_charge)):
            raise serializers.ValidationError("Insufficient balance including service charges")
        
        data['service_charge'] = service_charge
        data['net_amount'] = amount
        
        return data

class TransactionSerializer(serializers.ModelSerializer):
    wallet_user = serializers.CharField(source='wallet.user.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    recipient_username = serializers.CharField(source='recipient_user.username', read_only=True)
    service_submission_details = serializers.SerializerMethodField()
    opening_balance = serializers.DecimalField(
        max_digits=50, 
        decimal_places=2, 
        read_only=True
    )
    closing_balance = serializers.DecimalField(
        max_digits=50, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'wallet', 'wallet_user', 'amount', 'net_amount', 'service_charge',
            'transaction_type', 'transaction_category', 'status', 'description',
            'reference_number', 'recipient_user', 'recipient_username',
            'service_submission', 'service_submission_details', 'service_name',
            'created_by', 'created_by_username', 'created_at', 'metadata','opening_balance', 'closing_balance'
        ]
        read_only_fields = ['created_at']

    def get_service_submission_details(self, obj):
        """Service submission details - ONLY AVAILABLE FIELDS USE KARO"""
        if not obj.service_submission:
            return {
                "service_name": obj.service_name,
                "application_id": None,
                "service_id": None
            }
            
        try:
            ss = obj.service_submission
            
            # Basic details - ONLY AVAILABLE FIELDS
            details = {
                "application_id": ss.submission_id,
                "service_id": ss.service_form.id if ss.service_form else None,
                "service_name": ss.service_form.name if ss.service_form else obj.service_name,
                "applied_date": ss.created_at.isoformat() if ss.created_at else None,
            }
            
            # ✅ AVAILABLE FIELDS ADD KARO
            available_fields = [
                'customer_name', 'customer_email', 'customer_phone',
                'amount', 'transaction_id', 'notes', 'status', 'payment_status',
                'service_reference_id', 'submitted_at', 'processed_at'
            ]
            
            for field in available_fields:
                value = getattr(ss, field, None)
                if value:  # Only add if value exists and is not empty
                    details[field] = value
            
            # Form data se additional fields (JSON field mein stored)
            if ss.form_data and isinstance(ss.form_data, dict):
                # Common form data fields extract karo
                form_fields_to_extract = [
                    'consumer_name', 'consumer_number', 'consumer_mobile',
                    'loan_amount', 'loan_type', 'income_source', 'remarks',
                    'dependency', 'mobile_number', 'account_number', 'bill_number'
                ]
                
                for field in form_fields_to_extract:
                    if field in ss.form_data and ss.form_data[field]:
                        details[field] = ss.form_data[field]
            
            # Relationships - ONLY AVAILABLE ONES
            if ss.submitted_by:
                details['applied_by'] = ss.submitted_by.username
            
            # Service form details
            if ss.service_form:
                details['service_form_name'] = ss.service_form.name
                details['service_type'] = ss.service_form.service_type
            
            # Service subcategory details
            if ss.service_subcategory:
                details['service_category'] = ss.service_subcategory.category.name
                details['service_subcategory'] = ss.service_subcategory.name
            
            return details
            
        except Exception as e:
            print(f"Error in service_submission_details: {str(e)}")
            return {
                "service_name": obj.service_name,
                "application_id": f"SUB{obj.service_submission.id}" if obj.service_submission else None,
                "error": "Could not load full details"
            }


class TransactionFilterSerializer(serializers.Serializer):
    transaction_type = serializers.ChoiceField(choices=Transaction.TRANSACTION_TYPES, required=False)
    transaction_category = serializers.ChoiceField(choices=Transaction.TRANSACTION_CATEGORIES, required=False)
    status = serializers.ChoiceField(choices=Transaction.STATUS_CHOICES, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    min_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    max_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    user_id = serializers.IntegerField(required=False)
    reference_number = serializers.CharField(required=False)
    service_submission_id = serializers.IntegerField(required=False)


class ServiceChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCharge
        fields = [
            'id', 'transaction_category', 'charge_type', 'charge_value',
            'min_charge', 'max_charge', 'is_active', 'created_at', 'updated_at'
        ]


class WalletBalanceResponseSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(default='INR')
    is_pin_set = serializers.BooleanField()
    username = serializers.CharField(source='user.username', read_only=True)


class FundRequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FundRequest
        fields = [
            'id', 'reference_number', 'amount', 'status', 'transaction_type',
            'deposit_bank', 'Your_Bank', 'created_at', 'processed_at'
        ]



class TransactionHistoryResponseSerializer(serializers.Serializer):
    transactions = TransactionSerializer(many=True)
    fund_requests = FundRequestHistorySerializer(many=True)
    total_count = serializers.IntegerField()
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=2)


class ServiceSubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = ServiceSubCategory
        fields = ['id', 'name', 'category_name', 'description', 'image', 'is_active']


class UserServiceSerializer(serializers.ModelSerializer):
    service_details = ServiceSubCategorySerializer(source='service', read_only=True)
    
    class Meta:
        model = UserService
        fields = ['id', 'service', 'service_details', 'is_active', 'created_at']



class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    created_by_role = serializers.CharField(source='created_by.role', read_only=True)
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'role', 'created_by', 'created_by_role',
            # Personal Information
            'first_name', 'last_name', 'phone_number', 'alternative_phone', 
            'aadhar_number', 'pan_number', 'date_of_birth', 'gender',
            # Business Information
            'business_name', 'business_nature', 'business_registration_number',
            'gst_number', 'business_ownership_type',
            # Address Information
            'address', 'city', 'state', 'pincode', 'landmark',
            # Bank Information
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            # Services
            'service_ids'
        ]
        read_only_fields = ['created_by']

    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError("Request context is required")
        
        current_user = request.user
        target_role = value
        
        role_hierarchy = {
            'superadmin': ['superadmin', 'admin', 'master', 'dealer', 'retailer'],
            'admin': ['admin', 'master', 'dealer', 'retailer'],
            'master': ['master', 'dealer', 'retailer'],
            'dealer': ['retailer'],
            'retailer': []
        }
        
        if current_user.role not in role_hierarchy:
            raise serializers.ValidationError("Invalid current user role")
        
        if target_role not in role_hierarchy[current_user.role]:
            raise serializers.ValidationError(f"You cannot create users with {target_role} role")
        
        return value

    def create(self, validated_data):
        service_ids = validated_data.pop('service_ids', [])
        
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            role=validated_data['role'],
            created_by=self.context['request'].user,
            # Personal Information
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            phone_number=validated_data.get('phone_number'),
            alternative_phone=validated_data.get('alternative_phone'),
            aadhar_number=validated_data.get('aadhar_number'),
            pan_number=validated_data.get('pan_number'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            # Business Information
            business_name=validated_data.get('business_name'),
            business_nature=validated_data.get('business_nature'),
            business_registration_number=validated_data.get('business_registration_number'),
            gst_number=validated_data.get('gst_number'),
            business_ownership_type=validated_data.get('business_ownership_type'),
            # Address Information
            address=validated_data.get('address'),
            city=validated_data.get('city'),
            state=validated_data.get('state'),
            pincode=validated_data.get('pincode'),
            landmark=validated_data.get('landmark'),
            # Bank Information
            bank_name=validated_data.get('bank_name'),
            account_number=validated_data.get('account_number'),
            ifsc_code=validated_data.get('ifsc_code'),
            account_holder_name=validated_data.get('account_holder_name'),
        )
        user.set_password(validated_data['password'])
        user.save()
        
        # Create wallet
        Wallet.objects.create(user=user)
        
        try:
            for service_id in service_ids:
                try:
                    service = ServiceSubCategory.objects.get(id=service_id, is_active=True)
                    UserService.objects.create(user=user, service=service)
                except ServiceSubCategory.DoesNotExist:
                    continue
        except Exception as e:
            print(f"Service assignment failed: {e}")
        
        return user
    

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    wallet = WalletSerializer(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    services = UserServiceSerializer(many=True, read_only=True, source='user_services')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'profile_picture', 'email', 'password', 'role', 'wallet', 'created_by', 
            'created_by_username', 'date_joined', 'services',
            # Personal Information
            'first_name', 'last_name', 'phone_number', 'alternative_phone', 
            'aadhar_number', 'pan_number', 'date_of_birth', 'gender',
            # Business Information
            'business_name', 'business_nature', 'business_registration_number',
            'gst_number', 'business_ownership_type',
            # Address Information
            'address', 'city', 'state', 'pincode', 'landmark',
            # Bank Information
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
        ]
        read_only_fields = ['created_by', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Wallet.objects.create(user=user)
        return user

class PermissionSerializer(serializers.ModelSerializer):
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)
    app_label = serializers.CharField(source='content_type.app_label', read_only=True)
    
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'content_type_name', 'app_label']

class UserPermissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    permission_ids = serializers.ListField(child=serializers.IntegerField())

class UserPermissionsSerializer(serializers.ModelSerializer):
    user_permissions = PermissionSerializer(many=True, read_only=True)
    model_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'user_permissions', 'model_permissions']
    
    def get_model_permissions(self, obj):
        """Get permissions grouped by model"""
        from django.apps import apps
        models_list = []
        
        for model in apps.get_models():
            if model._meta.app_label in ['auth', 'contenttypes', 'sessions']:
                continue
                
            permissions = obj.get_model_permissions(model)
            if any(permissions.values()):
                models_list.append({
                    'model': model._meta.model_name,
                    'app_label': model._meta.app_label,
                    'verbose_name': model._meta.verbose_name,
                    'permissions': permissions
                })
        
        return models_list

class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']

class GrantRolePermissionSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    permission_ids = serializers.ListField(child=serializers.IntegerField())

class ModelPermissionSerializer(serializers.Serializer):
    model = serializers.CharField()
    app_label = serializers.CharField()
    permissions = serializers.DictField()

class RolePermissionSerializer(serializers.ModelSerializer):
    permission_details = PermissionSerializer(source='permission', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True)
    
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission', 'permission_details', 'granted_by', 'granted_by_username', 'created_at']




class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()

class VerifyForgotPasswordOTPSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name', 'code']

class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'state', 'state_name']



class FundRequestCreateSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    onboarder_username = serializers.SerializerMethodField()
    
    class Meta:
        model = FundRequest
        fields = [
            'id', 'user', 'user_username', 'user_role', 'amount', 
            'transaction_type', 'deposit_bank', 'Your_Bank', 'account_number', 
            'reference_number', 'remarks', 'screenshot', 'status',
            'created_at', 'onboarder_username'
        ]
        read_only_fields = ['reference_number', 'status', 'created_at']
    
    def get_onboarder_username(self, obj):
        onboarder = obj.get_onboarder()
        return onboarder.username if onboarder else None
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        if value > 1000000:  # Example limit of 10,00,000
            raise serializers.ValidationError("Amount exceeds maximum limit")
        return value
    
    def validate(self, data):
        # Ensure user is creating request for themselves
        request = self.context.get('request')
        if request and 'user' not in data:
            data['user'] = request.user
        return data

class FundRequestUpdateSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)
    onboarder_username = serializers.SerializerMethodField()
    
    class Meta:
        model = FundRequest
        fields = [
            'id', 'user', 'user_username', 'amount', 'transaction_type',
            'deposit_bank', 'Your_Bank', 'account_number', 'reference_number', 'remarks',
            'screenshot', 'status', 'admin_notes', 'processed_by',
            'processed_by_username', 'processed_at', 'created_at',
            'updated_at', 'onboarder_username'
        ]
        read_only_fields = [
            'user', 'amount', 'transaction_type', 'deposit_bank', 'Your_Bank',
            'account_number', 'reference_number', 'remarks', 'screenshot',
            'created_at', 'updated_at', 'processed_at'
        ]
    
    def get_onboarder_username(self, obj):
        onboarder = obj.get_onboarder()
        return onboarder.username if onboarder else None


class FundRequestApproveSerializer(serializers.Serializer):
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_admin_notes(self, value):
        if len(value) > 1000:
            raise serializers.ValidationError("Notes too long")
        return value

class FundRequestStatsSerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    rejected_requests = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class RequestWalletPinOTPSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=[('set_pin', 'Set PIN'), ('reset_pin', 'Reset PIN')])

class VerifyWalletPinOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=[('set_pin', 'Set PIN'), ('reset_pin', 'Reset PIN')])

class SetWalletPinWithOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    confirm_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

    def validate(self, data):
        if data['pin'] != data['confirm_pin']:
            raise serializers.ValidationError("PINs do not match")
        return data

class ResetWalletPinWithOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6)
    old_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    new_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    confirm_new_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_new_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

    def validate(self, data):
        if data['new_pin'] != data['confirm_new_pin']:
            raise serializers.ValidationError("New PINs do not match")
        return data
    


class ForgetPinRequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyForgetPinOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPinWithForgetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)
    confirm_pin = serializers.CharField(max_length=4, min_length=4, write_only=True)

    def validate_new_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

    def validate(self, data):
        if data['new_pin'] != data['confirm_pin']:
            raise serializers.ValidationError("PINs do not match")
        return data
    

class ResetPinWithForgetOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'profile_picture', 'first_name', 'last_name', 'phone_number', 
            'alternative_phone', 'date_of_birth', 'gender', 'address', 
            'city', 'state', 'pincode', 'landmark'
        ]
        extra_kwargs = {
            'profile_picture': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }



class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'profile_picture', 'first_name', 'last_name', 'phone_number', 
            'alternative_phone', 'date_of_birth', 'gender', 'address', 
            'city', 'state', 'pincode', 'landmark'
        ]
        extra_kwargs = {
            'profile_picture': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }


class UserKYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'alternative_phone',
            'aadhar_number', 'pan_number', 'date_of_birth', 'gender',
            
            'business_name', 'business_nature', 'business_registration_number',
            'gst_number', 'business_ownership_type',
            
            'address', 'city', 'state', 'pincode', 'landmark',
            
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name',
            
            'pan_card', 'aadhar_card', 'passport_photo', 'shop_photo', 
            'store_photo', 'other_documents'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'phone_number': {'required': True},
            'aadhar_number': {'required': True},
            'pan_number': {'required': True},
            'pan_card': {'required': False},
            'aadhar_card': {'required': False},
            'passport_photo': {'required': False},
        }

    def validate_aadhar_number(self, value):
        if value and (len(value) != 12 or not value.isdigit()):
            raise serializers.ValidationError("Aadhar number must be 12 digits")
        return value

    def validate_pan_number(self, value):
        if value and (len(value) != 10 or not value[:5].isalpha() or not value[5:9].isdigit() or not value[9].isalpha()):
            raise serializers.ValidationError("Invalid PAN number format")
        return value

    def validate_account_number(self, value):
        if value and (len(value) < 9 or len(value) > 18 or not value.isdigit()):
            raise serializers.ValidationError("Invalid account number")
        return value

    def validate_ifsc_code(self, value):
        if value and (len(value) != 11 or not value[:4].isalpha() or not value[4:].isdigit()):
            raise serializers.ValidationError("Invalid IFSC code format")
        return value
    

class MobileOTPLoginSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)

    def validate_mobile(self, value):
        value = value.strip()
        if value.startswith('+91'):
            if len(value) != 13:
                raise serializers.ValidationError("Invalid mobile number format with country code")
            if not value[1:].isdigit():
                raise serializers.ValidationError("Mobile number must contain only digits after country code")
        elif value.startswith(('9', '8', '7', '6')):
            if len(value) != 10:
                raise serializers.ValidationError("Mobile number must be 10 digits")
            if not value.isdigit():
                raise serializers.ValidationError("Mobile number must contain only digits")
        else:
            raise serializers.ValidationError("Invalid mobile number format")
        
        return value
    
    

class MobileOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)