from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import random
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction as db_transaction
from django.core.validators import MinValueValidator
import hashlib
import secrets
from decimal import Decimal
from django.db.models.signals import post_save, pre_save  
from django.dispatch import receiver

import random

def generate_5_digit():
    return f"{random.randint(0, 99999):05d}"



class MobileOTP(models.Model):
    mobile = models.CharField(max_length=15, unique=True)
    otp = models.CharField(max_length=6)
    otp_token = models.CharField(max_length=100, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    provider = models.CharField(max_length=20, default='database', blank=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.otp_token = secrets.token_urlsafe(32)
        self.expires_at = timezone.now() + timedelta(minutes=10)
        self.is_verified = False
        self.save()
        return self.otp, self.otp_token

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_verified(self):
        self.is_verified = True
        self.save()

    @classmethod
    def get_valid_otp(cls, mobile, otp, otp_token):
        try:
            otp_obj = cls.objects.get(
                mobile=mobile,
                otp=otp,
                otp_token=otp_token,
                is_verified=False
            )
            if not otp_obj.is_expired():
                return otp_obj
        except cls.DoesNotExist:
            return None
        return None

class User(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('master', 'Master'),
        ('dealer', 'Dealer'),
        ('retailer', 'Retailer'),
    )

    ROLE_PREFIX = {
        'superadmin': 'spw',
        'admin': 'adw',
        'master': 'maw',
        'dealer': 'dew',
        'retailer': 'rtw',
    }


    @property
    def role_based_id(self):
        prefix = self.ROLE_PREFIX.get(self.role, 'uid')
        return f"{prefix}{self.id}"

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    )
    
    BUSINESS_OWNERSHIP_CHOICES = (
        ('private', 'Private'),
        ('private_limited', 'Private Limited'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('public_limited', 'Public Limited'),
        ('other', 'Other'),
    )
    
    BUSINESS_NATURE_CHOICES = (
        ('retail_shop', 'Retail Shop'),
        ('wholesale', 'Wholesale'),
        ('service_provider', 'Service Provider'),
        ('manufacturer', 'Manufacturer'),
        ('distributor', 'Distributor'),
        ('franchise', 'Franchise'),
        ('other', 'Other'),
    )

    role_uid = models.CharField(max_length=20, unique=True, blank=True, null=True, db_index=True)
    email = models.EmailField(unique=True,null=True,blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='retailer')
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,related_name='created_users')
    parent_user = models.ForeignKey( 'self',on_delete=models.SET_NULL, null=True, blank=True, related_name='child_users')
    profile_picture = models.CharField(max_length=500, null=True, blank=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=15,unique=True, blank=True, null=True)
    alternative_phone = models.CharField(max_length=15, blank=True, null=True)
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    has_completed_first_time_setup = models.BooleanField(default=False)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    services = models.ManyToManyField('services.ServiceSubCategory', through='UserService',related_name='users',blank=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_nature = models.CharField(max_length=50, choices=BUSINESS_NATURE_CHOICES, blank=True, null=True)
    business_registration_number = models.CharField(max_length=50, blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    business_ownership_type = models.CharField(max_length=20, choices=BUSINESS_OWNERSHIP_CHOICES, blank=True, null=True)
    allow_passwordless_login = models.BooleanField(default=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11, blank=True, null=True)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    
    pan_card = models.CharField(max_length=500, blank=True, null=True)
    aadhar_card = models.CharField(max_length=500, blank=True, null=True)
    passport_photo = models.CharField(max_length=500, blank=True, null=True)
    shop_photo = models.CharField(max_length=500, blank=True, null=True)
    store_photo = models.CharField(max_length=500, blank=True, null=True)
    other_documents = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def is_admin_user(self):
        """Check if user is admin, superadmin or master"""
        return self.role in ["admin", "superadmin", "master"]
    
    def has_perm(self, perm, obj=None):
        """Override has_perm to use our permission system"""
        if self.role == 'superadmin':
            return True
        return self.has_permission(perm)
    
    def has_module_perms(self, app_label):
        """Override has_module_perms"""
        if self.role == 'superadmin':
            return True
        return super().has_module_perms(app_label)
    
    def has_permission(self, perm_codename):
        """Check if user has specific permission"""
        if self.role in ['superadmin', 'master']:
            return True
            
        return self.user_permissions.filter(codename=perm_codename).exists()
    
    def has_model_permission(self, model, action):
        """Check if user has specific model permission (view, add, change, delete)"""
        if self.role in ['superadmin', 'master']:
            return True
            
        permission_codename = f"{action}_{model._meta.model_name}"
        return self.has_permission(permission_codename)
    
    def get_model_permissions(self, model):
        """Get all permissions user has for a specific model"""
        if self.role in ['superadmin', 'master']:
            return {'view': True, 'add': True, 'change': True, 'delete': True}
        
        model_name = model._meta.model_name
        user_permissions = self.user_permissions.filter(
            content_type__app_label=model._meta.app_label,
            content_type__model=model_name
        ).values_list('codename', flat=True)
        
        return {
            'view': f'view_{model_name}' in user_permissions,
            'add': f'add_{model_name}' in user_permissions,
            'change': f'change_{model_name}' in user_permissions,
            'delete': f'delete_{model_name}' in user_permissions,
        }
    
    def can_view_model(self, model):
        return self.has_model_permission(model, 'view')
    
    def can_add_model(self, model):
        return self.has_model_permission(model, 'add')
    
    def can_change_model(self, model):
        return self.has_model_permission(model, 'change')
    
    def can_delete_model(self, model):
        return self.has_model_permission(model, 'delete')
    
    def can_manage_users(self):
        return self.role in ['superadmin', 'master', 'admin']
    
    def can_manage_balance_requests(self):
        return self.role in ['superadmin', 'master', 'admin', 'dealer']
    

    def can_create_user_with_role(self, target_role):
        """Check if user can create another user with specific role"""
        role_hierarchy = {
            'superadmin': ['superadmin', 'admin', 'master', 'dealer', 'retailer'],
            'admin': ['admin', 'master', 'dealer', 'retailer'],
            'master': ['master', 'dealer', 'retailer'],
            'dealer': ['retailer'],
            'retailer': []
        }
        
        if self.role not in role_hierarchy:
            return False
            
        return target_role in role_hierarchy[self.role]
    

    def get_onboarder(self):
        """Get the user who created this user"""
        return self.created_by
    


    def can_transfer_to_user(self, target_user):
        if self.role == 'superadmin':
            return True

        if self.role == 'admin':
            return target_user.role in ['admin', 'master', 'dealer', 'retailer']

        if self.role == 'master':
            return (
                target_user.role in ['dealer', 'retailer']
                and target_user.is_in_downline_of(self)
            )

        if self.role == 'dealer':
            return (
                target_user.role == 'retailer'
                and target_user.is_in_downline_of(self)
            )

        return False



    def is_in_downline_of(self, parent):
        """
        Check whether this user is in downline of given parent user
        """
        current = self.parent_user
        while current:
            if current == parent:
                return True
            current = current.parent_user
        return False

    

class UserBank(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='banks')
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'account_number']

    def __str__(self):
        return f"{self.user.username} - {self.bank_name}"


class ForgotPasswordOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_used = False
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def mark_used(self):
        self.is_used = True
        self.save()


class UserService(models.Model):
    """Model to store user selected services"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_services')
    service = models.ForeignKey('services.ServiceSubCategory', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'service']
        ordering = ['-created_at']

    def __str__(self):
        service_name = self.service.name if self.service else "Deleted Service"
        return f"{self.user.username} - {service_name}"
    

class State(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    district_code = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class RolePermission(models.Model):
    """Permissions assigned to specific roles"""
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='granted_role_permissions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['role', 'permission']

    def __str__(self):
        return f"{self.role} - {self.permission.codename}"

class EmailOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    pin_hash = models.CharField(max_length=255, blank=True, null=True)
    is_pin_set = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ₹{self.balance}"

    # def set_pin(self, pin):
    #     """Set wallet PIN"""
    #     if len(pin) != 4 or not pin.isdigit():
    #         raise ValueError("PIN must be 4 digits")
        
    #     self.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    #     self.is_pin_set = True
    #     self.save()


    def set_pin(self, pin):
        """Set wallet PIN with validation"""
        if len(pin) != 4 or not pin.isdigit():
            raise ValueError("PIN must be 4 digits")
        
        if self.is_sequential(pin):
            raise ValueError("PIN cannot be sequential numbers")
        
        if self.is_repeated(pin):
            raise ValueError("PIN cannot have repeated digits")
        
        if self.is_common_pattern(pin):
            raise ValueError("PIN is too common. Choose a different one.")
        
        if self.is_recent_pin(pin):
            raise ValueError("You cannot reuse a recent PIN")
        
        self.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        self.is_pin_set = True
        self.save()

    
    def is_sequential(self, pin):
        """Check if PIN is sequential numbers"""
        if all(int(pin[i]) + 1 == int(pin[i+1]) for i in range(len(pin)-1)):
            return True
        
        if all(int(pin[i]) - 1 == int(pin[i+1]) for i in range(len(pin)-1)):
            return True
        
        return False
    
    def is_repeated(self, pin):
        """Check if PIN has repeated digits"""
        return len(set(pin)) == 1
    
    def is_common_pattern(self, pin):
        """Check for common weak PINs"""
        common_pins = {
            '1234', '1111', '0000', '1212', '1004', 
            '2000', '4444', '2222', '6969', '9999',
            '3333', '5555', '6666', '1122', '1313',
            '7777', '8888', '2001', '4321', '1010'
        }
        return pin in common_pins
    
    def is_recent_pin(self, pin):
        """Check if PIN was used recently (if implementing PIN history)"""
        return False

    def verify_pin(self, pin):
        """Verify wallet PIN"""
        if not self.is_pin_set:
            return False
        return self.pin_hash == hashlib.sha256(pin.encode()).hexdigest()

    def reset_pin(self, old_pin, new_pin):
        """Reset wallet PIN"""
        if not self.verify_pin(old_pin):
            raise ValueError("Invalid current PIN")
        self.set_pin(new_pin)

    def has_sufficient_balance(self, amount, service_charge=0):
        """Check if wallet has sufficient balance including service charge"""
        # Convert both amount and service_charge to Decimal
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        if isinstance(service_charge, float):
            service_charge = Decimal(str(service_charge))
        
        total_amount = amount + service_charge
        return self.balance >= total_amount

    def add_amount(self, amount):
        """Add amount to wallet"""
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        elif isinstance(amount, int):
            amount = Decimal(amount)
        self.balance += amount
        self.save()

    def deduct_amount(self, amount, service_charge=0, pin=None):
        """Deduct amount from wallet with PIN verification"""
        if self.is_pin_set and not pin:
            raise ValueError("PIN is required for this transaction")
        
        if self.is_pin_set and not self.verify_pin(pin):
            raise ValueError("Invalid PIN")
        
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        elif isinstance(amount, int):
            amount = Decimal(amount)
        
        if isinstance(service_charge, float):
            service_charge = Decimal(str(service_charge))
        elif isinstance(service_charge, int):
            service_charge = Decimal(service_charge)
        
        total_amount = amount + service_charge
        
        if not self.has_sufficient_balance(amount, service_charge):
            raise ValueError("Insufficient balance")
        
        self.balance -= total_amount
        self.save()
        return total_amount


    def deduct_fee_without_pin(self, fee_amount):
        """
        Deduct fee without PIN verification
        Only for beneficiary verification fee
        """
        if isinstance(fee_amount, float):
            fee_amount = Decimal(str(fee_amount))
        
        if fee_amount <= 0:
            raise ValueError("Fee amount must be greater than zero")
        
        if self.balance < fee_amount:
            raise ValueError("Insufficient balance")
        
        self.balance -= fee_amount
        self.save()
        return fee_amount
    

    def system_deduct_amount(self, amount):
        """
        Deduct amount WITHOUT PIN
        Only for admin/system initiated transactions
        """
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        elif isinstance(amount, int):
            amount = Decimal(amount)

        if amount <= 0:
            raise ValueError("Invalid amount")

        if self.balance < amount:
            raise ValueError("Insufficient balance")

        self.balance -= amount
        self.save()


class PinHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pin_hash = models.CharField(max_length=255)
    set_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-set_at']
        indexes = [
            models.Index(fields=['user', 'set_at']),
        ]

@receiver(pre_save, sender=Wallet)
def track_pin_history(sender, instance, **kwargs):
    """Track PIN history when PIN is changed"""
    if instance.pk:
        try:
            old_wallet = Wallet.objects.get(pk=instance.pk)
            if (old_wallet.pin_hash and instance.pin_hash and 
                old_wallet.pin_hash != instance.pin_hash):
                PinHistory.objects.create(
                    user=instance.user,
                    pin_hash=old_wallet.pin_hash
                )
                
                pin_history = PinHistory.objects.filter(user=instance.user)
                if pin_history.count() > 5:
                    old_records = pin_history.order_by('set_at')[0:pin_history.count()-5]
                    old_records.delete()
        except Wallet.DoesNotExist:
            pass


class ForgetPinOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_used = False
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def mark_used(self):
        self.is_used = True
        self.save()


class WalletPinOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=[
        ('set_pin', 'Set PIN'),
        ('reset_pin', 'Reset PIN')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.is_used = False
        self.save()
        return self.otp

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def mark_used(self):
        self.is_used = True
        self.save()
        

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    
    TRANSACTION_CATEGORIES = (
        ('fund_request', 'Fund Request'),
        ('money_transfer', 'Money Transfer'),
        ('bill_payment', 'Bill Payment'),
        ('bbps', 'bbps'),
        ('service_charge', 'Service Charge'),
        ('cashback', 'Cashback'),
        ('refund', 'Refund'),
        ('commission', 'Commission'),
        ('service_payment', 'Service Payment'),
        ('beneficiary_verification', 'Beneficiary Verification'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    service_charge = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    transaction_category = models.CharField(max_length=30, choices=TRANSACTION_CATEGORIES, default='other')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    description = models.CharField(max_length=255)
    refund_status = models.CharField(max_length=20,default="not_refunded")
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='received_transactions'
    )
    opening_balance = models.DecimalField(
        max_digits=50, decimal_places=2, null=True, blank=True
    )
    closing_balance = models.DecimalField(
        max_digits=50, decimal_places=2, null=True, blank=True
    )
    # Service-related fields (for service payments)
    service_submission = models.ForeignKey(
        'services.ServiceSubmission',  # Your service app model
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    service_name = models.CharField(max_length=255, blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional fields for filtering
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['transaction_category', 'created_at']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['service_submission']),  # New index
        ]

    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.wallet.user.username}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        if not self.net_amount:
            self.net_amount = self.amount
        super().save(*args, **kwargs)

    def generate_reference_number(self):
        """Generate unique reference number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = str(random.randint(1000, 9999))
        return f"TXN{timestamp}{random_str}"



class ServiceCharge(models.Model):
    """Model to manage service charges for different transaction types"""
    TRANSACTION_CATEGORIES = Transaction.TRANSACTION_CATEGORIES
    
    transaction_category = models.CharField(max_length=30, choices=TRANSACTION_CATEGORIES, unique=True)
    charge_type = models.CharField(max_length=10, choices=[('fixed', 'Fixed'), ('percentage', 'Percentage')])
    charge_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_category} - {self.charge_type} - {self.charge_value}"

    def calculate_charge(self, amount):
        """Calculate service charge for given amount"""
        if not self.is_active:
            return Decimal('0.00')
        
        # Ensure amount is Decimal
        if isinstance(amount, float):
            amount = Decimal(str(amount))
        
        if self.charge_type == 'fixed':
            charge = self.charge_value
        else:  # percentage
            charge = (amount * self.charge_value) / Decimal('100')
        
        # Apply min/max limits
        if self.min_charge and charge < self.min_charge:
            charge = self.min_charge
        if self.max_charge and charge > self.max_charge:
            charge = self.max_charge
        
        return charge

 
    def save(self, *args, **kwargs):
        """Auto-create beneficiary verification charge if not exists"""
        super().save(*args, **kwargs)
        
        if not ServiceCharge.objects.filter(transaction_category='beneficiary_verification').exists():
            ServiceCharge.objects.create(
                transaction_category='beneficiary_verification',
                charge_type='fixed',
                charge_value=Decimal('2.90'),
                min_charge=Decimal('2.90'),
                max_charge=Decimal('2.90'),
                is_active=True
            )


class FundRequest(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cash_deposit', 'Cash Deposit'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fund_requests'
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    txn_date = models.DateTimeField(null=True, blank=True,help_text="Transaction / Deposit Date provided by user")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    deposit_bank = models.CharField(max_length=300)
    Your_Bank = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    utr_number = models.CharField(max_length=100,blank=True,null=True,help_text="UTR / Bank Reference Number provided by user")
    reference_number = models.CharField(max_length=100, unique=True)
    service_charge = models.DecimalField(max_digits=15,decimal_places=2,default=0.00)
    wallet_credit = models.DecimalField(max_digits=15,decimal_places=2,default=0.00)
    remarks = models.TextField(blank=True, null=True)
    screenshot = models.FileField(upload_to='fund_requests/screenshots/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_fund_requests'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Fund Request #{self.reference_number} - {self.user.username} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        """Generate unique reference number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = str(random.randint(1000, 9999))
        return f"FR{timestamp}{random_str}"
    
    def get_onboarder(self):
        """Get the user who onboarded this user"""
        return self.user.get_onboarder()
    
    def can_approve(self, user):
        """Check if user can approve this request"""
        if user.role in ['superadmin', 'admin']:
            return True
        onboarder = self.get_onboarder()
        return onboarder and onboarder == user
    

    
    def approve(self, approved_by, notes=""):

        if self.status != 'pending':
            return False, "Request already processed"

        try:
            with db_transaction.atomic():

                charge = (self.amount * Decimal("0.0001")).quantize(Decimal("0.01"))
                if charge < Decimal("0.01"):
                    charge = Decimal("0.01")

                net_amount = self.amount - charge

                user_wallet, _ = Wallet.objects.get_or_create(user=self.user)
                admin_wallet, _ = Wallet.objects.get_or_create(user=approved_by)

                if admin_wallet.balance < net_amount:
                    raise ValueError("Admin wallet has insufficient balance")

                admin_wallet.balance -= net_amount
                admin_wallet.save(update_fields=["balance"])

                Transaction.objects.create(
                    wallet=admin_wallet,
                    amount=net_amount,
                    service_charge=Decimal("0.00"),
                    transaction_type='debit',
                    transaction_category='fund_request',
                    description=(
                        f"Fund request approved for {self.user.username}: "
                        f"{self.reference_number}"
                    ),
                    created_by=approved_by,
                    status='success'
                )

                Transaction.objects.create(
                    wallet=user_wallet,
                    amount=net_amount,
                    service_charge=charge,
                    transaction_type='credit',
                    transaction_category='fund_request',
                    description=(
                        f"Fund request approved: {self.reference_number} "
                        f"(0.01% charge ₹{charge})"
                    ),
                    created_by=approved_by,
                    status='success'
                )

                user_wallet.balance += net_amount
                user_wallet.save(update_fields=["balance"])

                self.status = 'approved'
                self.processed_by = approved_by
                self.processed_at = timezone.now()
                self.admin_notes = notes
                self.service_charge = charge
                self.wallet_credit = net_amount
                self.save(update_fields=[
                    "status",
                    "processed_by",
                    "processed_at",
                    "admin_notes",
                    "service_charge",
                    "wallet_credit"
                ])

                return True, "Fund request approved successfully"

        except Exception as e:
            return False, str(e)




    def reject(self, rejected_by, notes=""):
        """Reject the fund request"""
        if self.status != 'pending':
            return False, "Request already processed"
        
        self.status = 'rejected'
        self.processed_by = rejected_by
        self.processed_at = timezone.now()
        self.admin_notes = notes
        self.save()
        
        return True, "Fund request rejected"
    
    
    

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Automatically create wallet when new user is created
    """
    if created:
        Wallet.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def ensure_wallet_exists(sender, instance, **kwargs):
    """
    Ensure wallet exists for all users (safety net)
    """
    if not hasattr(instance, 'wallet'):
        Wallet.objects.get_or_create(user=instance)



@receiver(pre_save, sender=Transaction)
def set_transaction_balances(sender, instance, **kwargs):
    """Automatically set opening and closing balances"""
    if not instance.pk:
        wallet = instance.wallet
        
        if isinstance(instance.amount, float):
            instance.amount = Decimal(str(instance.amount))
        elif isinstance(instance.amount, int):
            instance.amount = Decimal(instance.amount)
        
        if isinstance(instance.service_charge, float):
            instance.service_charge = Decimal(str(instance.service_charge))
        elif isinstance(instance.service_charge, int):
            instance.service_charge = Decimal(instance.service_charge)
        
        if instance.transaction_type == 'credit':
            instance.opening_balance = wallet.balance
            instance.closing_balance = wallet.balance + instance.amount
        else:
            total_deduction = instance.amount + instance.service_charge
            instance.opening_balance = wallet.balance + total_deduction
            instance.closing_balance = wallet.balance


@receiver(pre_save, sender=User)
def generate_role_uid(sender, instance, **kwargs):
    if instance.role_uid:
        return

    prefix = User.ROLE_PREFIX.get(instance.role, 'uid')

    while True:
        uid = f"{prefix}-{generate_5_digit()}"
        if not User.objects.filter(role_uid=uid).exists():
            instance.role_uid = uid
            break



class RefundRequest(models.Model):

    STATUS = [
        ('initiated', 'Initiated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)

    refund_transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="refund_credit"
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    eko_response = models.JSONField(default=dict)

    status = models.CharField(max_length=20, choices=STATUS, default='initiated')

    # 🔥 ADD THESE 3 FIELDS
    admin_note = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_refunds'
    )

    created_at = models.DateTimeField(auto_now_add=True)

