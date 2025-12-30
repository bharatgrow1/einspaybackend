from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from decimal import Decimal
import logging
logger = logging.getLogger(__name__)
import uuid


class DMTTransaction(models.Model):
    STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'OTP Verified'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    EKO_TX_STATUS_CHOICES = (
        ('0', 'Success'),
        ('1', 'Fail'),
        ('2', 'Response Awaited/Initiated'),
        ('3', 'Refund Pending'),
        ('4', 'Refunded'),
        ('5', 'Hold (Transaction Inquiry Required)'),
    )
    
    TRANSACTION_TYPE_CHOICES = (
        ('imps', 'IMPS'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
    )


    eko_tx_status = models.CharField(max_length=1, choices=EKO_TX_STATUS_CHOICES, blank=True, null=True)
    eko_txstatus_desc = models.CharField(max_length=255, blank=True, null=True)
    eko_bank_ref_num = models.CharField(max_length=100, blank=True, null=True)
    eko_tid = models.CharField(max_length=100, blank=True, null=True)
    client_ref_id = models.CharField(max_length=100, blank=True, null=True)
    
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, default='imps')
    
    # Sender Information
    sender_mobile = models.CharField(max_length=15)
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    sender_aadhar = models.CharField(max_length=12, blank=True, null=True)
    
    # Recipient Information
    recipient = models.ForeignKey('DMTRecipient', on_delete=models.CASCADE, related_name='transactions')
    recipient_name = models.CharField(max_length=255)
    recipient_mobile = models.CharField(max_length=15, blank=True, null=True)
    recipient_account = models.CharField(max_length=50)
    recipient_ifsc = models.CharField(max_length=11)
    recipient_bank = models.CharField(max_length=255, blank=True, null=True)
    
    # EKO API References
    eko_customer_id = models.CharField(max_length=100, blank=True, null=True)
    eko_recipient_id = models.IntegerField(blank=True, null=True)
    eko_otp_ref_id = models.CharField(max_length=100, blank=True, null=True)
    eko_kyc_request_id = models.CharField(max_length=100, blank=True, null=True)
    eko_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    otp_sent_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Response Data
    api_response = models.JSONField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'initiated_at']),
            models.Index(fields=['status', 'initiated_at']),
            models.Index(fields=['sender_mobile']),
        ]
    
    def __str__(self):
        return f"DMT-{self.transaction_id} - {self.user.username} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"DMT{uuid.uuid4().hex[:12].upper()}"
        
        # FIX: Ensure total_amount calculation works with Decimal
        if not self.total_amount:
            try:
                # Convert to Decimal if needed
                if isinstance(self.amount, float):
                    amt = Decimal(str(self.amount))
                else:
                    amt = self.amount
                    
                if isinstance(self.service_charge, float):
                    sc = Decimal(str(self.service_charge))
                else:
                    sc = self.service_charge
                    
                self.total_amount = amt + sc
            except:
                # Fallback
                self.total_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    def mark_otp_sent(self, otp_ref_id):
        self.status = 'otp_sent'
        self.eko_otp_ref_id = otp_ref_id
        self.otp_sent_at = timezone.now()
        self.save()
    
    def mark_verified(self, kyc_request_id=None):
        self.status = 'verified'
        self.eko_kyc_request_id = kyc_request_id
        self.verified_at = timezone.now()
        self.save()
    
    def mark_success(self, transaction_ref):
        self.status = 'success'
        self.eko_transaction_ref = transaction_ref
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message, error_details=None):
        self.status = 'failed'
        self.status_message = error_message
        self.error_details = error_details or {}
        self.completed_at = timezone.now()
        self.save()


    def update_from_eko_response(self, eko_response):
        """Update transaction from EKO API response"""
        if eko_response.get('status') == 0:
            data = eko_response.get('data', {})
            
            self.eko_tx_status = data.get('tx_status')
            self.eko_txstatus_desc = data.get('txstatus_desc')
            self.eko_bank_ref_num = data.get('bank_ref_num')
            self.eko_tid = data.get('tid')
            self.client_ref_id = data.get('client_ref_id')
            
            if self.eko_tx_status == '0':
                self.status = 'success'
                if not self.completed_at:
                    self.completed_at = timezone.now()
            elif self.eko_tx_status == '1':
                self.status = 'failed'
                if not self.completed_at:
                    self.completed_at = timezone.now()
            elif self.eko_tx_status == '2':
                self.status = 'processing'
            elif self.eko_tx_status == '5':
                self.status = 'processing'
            
            self.api_response = eko_response
            self.save()
            
            return True
        return False
    

class DMTRecipient(models.Model):
    ACCOUNT_TYPE_CHOICES = (
        (1, 'Savings Account'),
        (2, 'Current Account'),
        (3, 'Salary Account'),
    )
    
    RECIPIENT_TYPE_CHOICES = (
        (1, 'Individual'),
        (2, 'Corporate'),
        (3, 'Other'),
    )
    
    # Basic Information
    recipient_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_recipients')
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    
    # Bank Account Details
    account_number = models.CharField(max_length=50)
    confirm_account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_id = models.IntegerField(blank=True, null=True)
    account_type = models.IntegerField(choices=ACCOUNT_TYPE_CHOICES, default=1)
    recipient_type = models.IntegerField(choices=RECIPIENT_TYPE_CHOICES, default=1)
    
    # EKO API Reference
    eko_recipient_id = models.IntegerField(blank=True, null=True)
    eko_verification_status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ))
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Additional Info
    verification_response = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'account_number', 'ifsc_code']
        indexes = [
            models.Index(fields=['recipient_id']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['eko_recipient_id']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.account_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.recipient_id:
            self.recipient_id = f"REC{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
    
    def mark_verified(self, eko_recipient_id, response_data=None):
        self.eko_recipient_id = eko_recipient_id
        self.is_verified = True
        self.eko_verification_status = 'verified'
        self.verified_at = timezone.now()
        self.verification_response = response_data or {}
        self.save()
    
    def mark_verification_failed(self, response_data=None):
        self.is_verified = False
        self.eko_verification_status = 'failed'
        self.verification_response = response_data or {}
        self.save()

class DMTSenderProfile(models.Model):
    KYC_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dmt_sender_profile')
    mobile = models.CharField(max_length=15, unique=True)
    aadhar_number = models.CharField(max_length=12, blank=True, null=True)
    
    # KYC Information
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='pending')
    kyc_verified_at = models.DateTimeField(blank=True, null=True)
    kyc_method = models.CharField(max_length=20, blank=True, null=True, choices=(
        ('biometric', 'Biometric'),
        ('otp', 'OTP'),
        ('manual', 'Manual'),
    ))
    
    # EKO API Data
    eko_customer_id = models.CharField(max_length=100, blank=True, null=True)
    eko_profile_data = models.JSONField(blank=True, null=True)
    
    # Limits
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=50000.00)
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2, default=200000.00)
    per_transaction_limit = models.DecimalField(max_digits=10, decimal_places=2, default=25000.00)
    
    # Usage Tracking
    daily_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_transaction_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['kyc_status']),
            models.Index(fields=['eko_customer_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.mobile} - {self.kyc_status}"
    
    def reset_limits(self):
        """Reset daily usage (to be called via cron job)"""
        self.daily_usage = Decimal('0.00')
        self.save()
    
    def reset_monthly_usage(self):
        """Reset monthly usage (to be called via cron job)"""
        self.monthly_usage = Decimal('0.00')
        self.save()
    
    def can_transact(self, amount):
        """Check if sender can perform transaction with given amount"""
        if self.kyc_status != 'verified':
            return False, "KYC not verified"
        
        if amount > self.per_transaction_limit:
            return False, f"Amount exceeds per transaction limit of ₹{self.per_transaction_limit}"
        
        if (self.daily_usage + amount) > self.daily_limit:
            return False, f"Amount exceeds daily limit of ₹{self.daily_limit}"
        
        if (self.monthly_usage + amount) > self.monthly_limit:
            return False, f"Amount exceeds monthly limit of ₹{self.monthly_limit}"
        
        return True, "OK"
    
    def update_usage(self, amount):
        """Update usage after successful transaction"""
        self.daily_usage += amount
        self.monthly_usage += amount
        self.last_transaction_at = timezone.now()
        self.save()

class DMTServiceCharge(models.Model):
    AMOUNT_RANGE_CHOICES = (
        ('0-1000', '₹0 - ₹1,000'),
        ('1001-10000', '₹1,001 - ₹10,000'),
        ('10001-25000', '₹10,001 - ₹25,000'),
        ('25001-50000', '₹25,001 - ₹50,000'),
        ('50001-100000', '₹50,001 - ₹1,00,000'),
    )
    
    amount_range = models.CharField(max_length=20, choices=AMOUNT_RANGE_CHOICES, unique=True)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2)
    charge_type = models.CharField(max_length=10, choices=(
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage'),
    ), default='fixed')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['min_amount']
    
    def __str__(self):
        return f"{self.amount_range} - ₹{self.service_charge}"
    
    @classmethod
    def calculate_charge(cls, amount):
        """Calculate service charge for given amount"""
        try:
            charge_config = cls.objects.filter(
                min_amount__lte=amount,
                max_amount__gte=amount,
                is_active=True
            ).first()
            
            if charge_config:
                if charge_config.charge_type == 'percentage':
                    return (amount * charge_config.service_charge) / 100
                return charge_config.service_charge
            return Decimal('0.00')
        except cls.DoesNotExist:
            return Decimal('0.00')

class DMTBank(models.Model):
    bank_id = models.IntegerField(unique=True)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=50, blank=True, null=True)
    ifsc_prefix = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['bank_name']
        indexes = [
            models.Index(fields=['bank_name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.bank_name} ({self.bank_id})"
    


class EkoBank(models.Model):
    bank_id = models.IntegerField(primary_key=True)
    bank_name = models.CharField(max_length=255)
    bank_code = models.CharField(max_length=50)
    imps_status = models.CharField(max_length=50)
    neft_status = models.CharField(max_length=50)
    verification_status = models.CharField(max_length=50)
    ifsc_status = models.CharField(max_length=255)
    static_ifsc = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.bank_name
    


class TransactionStatusManager:
    @staticmethod
    def check_and_update_status(tid=None, client_ref_id=None):
        """Check transaction status from EKO and update local record"""
        try:
            if tid:
                transaction = DMTTransaction.objects.filter(eko_tid=tid).first()
                inquiry_id = tid
                is_client_ref_id = False
            elif client_ref_id:
                transaction = DMTTransaction.objects.filter(client_ref_id=client_ref_id).first()
                inquiry_id = client_ref_id
                is_client_ref_id = True
            else:
                return {"status": 1, "message": "Either tid or client_ref_id is required"}
            
            if not transaction:
                return {"status": 1, "message": "Transaction not found"}
            
            # Use DMTManager to check status
            from .services.dmt_manager import dmt_manager
            response = dmt_manager.transaction_inquiry(inquiry_id, is_client_ref_id)
            
            if response.get('status') == 0:
                # Update transaction
                transaction.update_from_eko_response(response)
                return {
                    "status": 0,
                    "message": "Status updated successfully",
                    "transaction_status": transaction.status,
                    "eko_tx_status": transaction.eko_tx_status
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Status update error: {str(e)}")
            return {"status": 1, "message": str(e)}
    
    @staticmethod
    def get_eligible_refund_transactions(user=None):
        """Get transactions eligible for refund"""
        try:
            queryset = DMTTransaction.objects.filter(
                status__in=['failed', 'processing'],
                eko_tx_status__in=['1', '2', '5'] 
            )
            
            if user:
                queryset = queryset.filter(user=user)
            
            return queryset.order_by('-initiated_at')
        except Exception as e:
            logger.error(f"Error getting refund eligible transactions: {str(e)}")
            return DMTTransaction.objects.none()
        

class DMTPlan(models.Model):
    """Platinum, Gold, Silver plans"""
    PLAN_TYPES = (
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('basic', 'Basic'),
    )
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.plan_type})"


class EKOChargeConfig(models.Model):
    """EKO charges configuration from your table"""
    amount_from = models.DecimalField(max_digits=10, decimal_places=2)
    amount_to = models.DecimalField(max_digits=10, decimal_places=2)
    customer_fee_net_gst = models.DecimalField(max_digits=10, decimal_places=2) 
    eko_pricing = models.DecimalField(max_digits=10, decimal_places=2)  
    commission_after_tds = models.DecimalField(max_digits=10, decimal_places=2) 
    
    class Meta:
        ordering = ['amount_from']
    
    def __str__(self):
        return f"₹{self.amount_from} - ₹{self.amount_to}: ₹{self.commission_after_tds}"


class DMTChargeScheme(models.Model):
    """Super admin creates charges scheme"""
    CHARGE_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('flat', 'Flat Amount'),
        ('both', 'Both Percentage and Flat'),
    )
    
    name = models.CharField(max_length=100)
    plan = models.ForeignKey(DMTPlan, on_delete=models.CASCADE, related_name='charge_schemes')
    
    amount_range = models.CharField(max_length=50)
    amount_from = models.DecimalField(max_digits=10, decimal_places=2)
    amount_to = models.DecimalField(max_digits=10, decimal_places=2)
    eko_commission = models.DecimalField(max_digits=10, decimal_places=2)
    
    charge_type = models.CharField(max_length=20, choices=CHARGE_TYPE_CHOICES, default='percentage')
    percentage_charge = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    flat_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    
    retailer_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00) 
    dealer_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00) 
    master_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00) 
    admin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  
    superadmin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['amount_from']
        unique_together = ['plan', 'amount_from', 'amount_to']
    
    def __str__(self):
        return f"{self.name} - {self.plan.name} - ₹{self.amount_from}-₹{self.amount_to}"
    
    def save(self, *args, **kwargs):
        if not self.amount_range:
            self.amount_range = f"{self.amount_from}-{self.amount_to}"
        super().save(*args, **kwargs)
    
    def calculate_charges(self, transaction_amount):
        """Calculate total charges for a transaction"""
        eko_commission = self.eko_commission
        
        extra_charge = Decimal('0.00')
        
        if self.charge_type in ['percentage', 'both']:
            extra_charge += (eko_commission * self.percentage_charge) / 100
        
        if self.charge_type in ['flat', 'both']:
            extra_charge += self.flat_charge
        
        total_charges = eko_commission + extra_charge
        
        distribution = {
            'total_charges': total_charges,
            'eko_commission': eko_commission,
            'superadmin_extra': extra_charge,
            'retailer_amount': (total_charges * self.retailer_percentage) / 100,
            'dealer_amount': (total_charges * self.dealer_percentage) / 100,
            'master_amount': (total_charges * self.master_percentage) / 100,
            'admin_amount': (total_charges * self.admin_percentage) / 100,
            'superadmin_amount': (total_charges * self.superadmin_percentage) / 100,
        }
        
        return distribution
    
    def validate_percentages(self):
        """Validate that percentages add up to 100%"""
        total = (
            self.retailer_percentage + 
            self.dealer_percentage + 
            self.master_percentage + 
            self.admin_percentage + 
            self.superadmin_percentage
        )
        return total == 100


class DMTTransactionCharge(models.Model):
    """Track charges for each DMT transaction"""
    dmt_transaction = models.OneToOneField('DMTTransaction', on_delete=models.CASCADE, related_name='charge_details')
    charge_scheme = models.ForeignKey(DMTChargeScheme, on_delete=models.CASCADE)
    
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    eko_commission = models.DecimalField(max_digits=10, decimal_places=2)
    superadmin_extra_charge = models.DecimalField(max_digits=10, decimal_places=2)
    total_charges = models.DecimalField(max_digits=10, decimal_places=2)
    
    retailer_amount = models.DecimalField(max_digits=10, decimal_places=2)
    dealer_amount = models.DecimalField(max_digits=10, decimal_places=2)
    master_amount = models.DecimalField(max_digits=10, decimal_places=2)
    admin_amount = models.DecimalField(max_digits=10, decimal_places=2)
    superadmin_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    is_distributed = models.BooleanField(default=False)
    distributed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Charges for {self.dmt_transaction.transaction_id}"
    
    def distribute_to_wallets(self):
        """Distribute amounts to all wallets in hierarchy"""
        try:
            from django.db import transaction as db_transaction
            from users.models import Transaction
            
            with db_transaction.atomic():
                chain = self.get_hierarchy_chain()
                
                for user_info in chain:
                    role = user_info['role']
                    amount_field = f"{role}_amount"
                    amount = getattr(self, amount_field, Decimal('0.00'))
                    
                    if amount > 0:
                        wallet = user_info['user'].wallet
                        
                        wallet.balance += amount
                        wallet.save()
                        
                        Transaction.objects.create(
                            wallet=wallet,
                            amount=amount,
                            transaction_type='credit',
                            transaction_category='dmt_commission',
                            description=f"DMT commission - {self.dmt_transaction.transaction_id}",
                            created_by=user_info['user'],
                            status='success',
                            metadata={
                                'dmt_transaction_id': self.dmt_transaction.id,
                                'role': role,
                                'charge_scheme_id': self.charge_scheme.id
                            }
                        )
                
                self.is_distributed = True
                self.distributed_at = timezone.now()
                self.save()
                
                return True
                
        except Exception as e:
            logger.error(f"Distribution failed: {str(e)}")
            return False
    
    def get_hierarchy_chain(self):
        """Get all users in hierarchy for this transaction"""
        from users.models import User
        
        chain = []
        current_user = self.dmt_transaction.user
        
        while current_user:
            chain.append({
                'user': current_user,
                'role': current_user.role
            })
            current_user = current_user.created_by
        
        roles_needed = ['retailer', 'dealer', 'master', 'admin', 'superadmin']
        existing_roles = [u['role'] for u in chain]
        
        if 'superadmin' not in existing_roles:
            superadmin = User.objects.filter(role='superadmin').first()
            if superadmin:
                chain.append({
                    'user': superadmin,
                    'role': 'superadmin'
                })
        
        return chain
