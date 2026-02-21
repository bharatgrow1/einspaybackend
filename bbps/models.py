from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class bbpsTransaction(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    OPERATOR_TYPES = [
        ('prepaid', 'Mobile Prepaid'),
        ('postpaid', 'Mobile Postpaid'),
        ('dth', 'DTH'),
        ('broadband', 'Broadband'),
        ('electricity', 'Electricity'),
        ('gas', 'Gas'),
        ('water', 'Water'),
        ('landline', 'Landline'),
        ('tax', 'Tax'),
        ('credit', 'Credit Card'),
        ('society', 'Housing Society'),
        ('ott', 'OTT Subscription'),
        ('education', 'Education Fees'),
        ('municipal_tax', 'Municipal Tax'),
        ('clubs', 'Clubs & Associations'),
        ('cable', 'Cable TV'),
        ('lpg', 'LPG Cylinder'),
        ('hospital', 'Hospital'),
        ('insurance', 'Insurance'),
        ('loan', 'Loan EMI'),
        ('fastag', 'FASTag'),
        ('municipal_services', 'Municipal Services'),
        ('subscription_2', 'Subscription 2'),
    ]

    
    # Transaction Information
    transaction_id = models.CharField(max_length=100, unique=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bbps_transactions')
    
    # Service Details
    operator_id = models.CharField(max_length=50)
    operator_name = models.CharField(max_length=100, blank=True, null=True)
    operator_type = models.CharField(max_length=20, choices=OPERATOR_TYPES, default='prepaid')
    circle = models.CharField(max_length=100, blank=True, null=True)
    wallet_transaction = models.OneToOneField("users.Transaction",on_delete=models.SET_NULL,null=True,blank=True,related_name="bbps_transaction")

    # Customer Details
    mobile_number = models.CharField(max_length=15)
    consumer_number = models.CharField(max_length=50, blank=True, null=True)  # For electricity, water bills
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Amount Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # EKO API References
    client_ref_id = models.CharField(max_length=100)
    eko_transaction_ref = models.CharField(max_length=100, blank=True, null=True)
    eko_message = models.TextField(blank=True, null=True)
    eko_txstatus_desc = models.CharField(max_length=100, blank=True, null=True)
    eko_response_status = models.IntegerField(blank=True, null=True)
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    status_message = models.TextField(blank=True, null=True)
    
    # Payment Information
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], default='pending')
    
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Response Data
    api_request = models.JSONField(blank=True, null=True)
    api_response = models.JSONField(blank=True, null=True)
    error_details = models.JSONField(blank=True, null=True)
    
    # Additional Info
    is_plan_bbps = models.BooleanField(default=False)
    plan_details = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', 'initiated_at']),
            models.Index(fields=['mobile_number']),
            models.Index(fields=['status', 'initiated_at']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"bbps-{self.transaction_id} - {self.mobile_number} - ₹{self.amount}"
    
    # def save(self, *args, **kwargs):
    #     if not self.transaction_id:
    #         self.transaction_id = f"RECH{uuid.uuid4().hex[:12].upper()}"
    #     if not self.total_amount:
    #         self.total_amount = self.amount + self.service_charge
    #     super().save(*args, **kwargs)



    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"RECH{uuid.uuid4().hex[:12].upper()}"

        if self.amount is not None and self.service_charge is not None:
            self.total_amount = self.amount + self.service_charge

        if not self.operator_name and self.operator_id:
            try:
                from .models import Operator
                operator = Operator.objects.get(operator_id=self.operator_id)
                self.operator_name = operator.operator_name
            except Operator.DoesNotExist:
                pass 

        super().save(*args, **kwargs)

    
    def mark_processing(self):
        self.status = 'processing'
        self.save()
    
    def mark_success(self, eko_response=None):
        self.status = 'success'
        self.completed_at = timezone.now()
        if eko_response:
            self.eko_transaction_ref = eko_response.get('transaction_ref')
            self.eko_message = eko_response.get('message')
            self.eko_txstatus_desc = eko_response.get('txstatus_desc')
        self.save()
    
    def mark_failed(self, error_message, error_details=None):
        self.status = 'failed'
        self.status_message = error_message
        self.error_details = error_details or {}
        self.completed_at = timezone.now()
        self.save()

class Operator(models.Model):
    """Store operator information from EKO API"""
    operator_id = models.CharField(max_length=50, unique=True)
    operator_name = models.CharField(max_length=255)
    operator_type = models.CharField(max_length=20, choices=bbpsTransaction.OPERATOR_TYPES)
    category_id = models.IntegerField(blank=True, null=True)  # EKO category ID
    is_active = models.BooleanField(default=True)
    
    # Additional Info
    circle = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # Commission Info
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    flat_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['operator_name']
        indexes = [
            models.Index(fields=['operator_type', 'is_active']),
            models.Index(fields=['circle']),
        ]
    
    def __str__(self):
        return f"{self.operator_name} ({self.operator_id})"

class Plan(models.Model):
    """Mobile/DTH plans"""
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name='plans')
    plan_id = models.CharField(max_length=100, unique=True)
    plan_name = models.CharField(max_length=255)
    plan_description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    validity = models.CharField(max_length=100, blank=True, null=True)  # e.g., 28 days, 30 days
    data_allowance = models.CharField(max_length=100, blank=True, null=True)  # e.g., 1.5GB/day
    talktime = models.CharField(max_length=100, blank=True, null=True)
    sms_allowance = models.CharField(max_length=100, blank=True, null=True)
    
    # Plan Type
    plan_type = models.CharField(max_length=50, choices=[
        ('data', 'Data Plan'),
        ('combo', 'Combo Plan'),
        ('voice', 'Voice Plan'),
        ('topup', 'Top-up'),
        ('special', 'Special bbps'),
        ('dth', 'DTH Plan'),
    ], default='combo')
    
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # EKO Specific
    eko_plan_code = models.CharField(max_length=100, blank=True, null=True)
    eko_plan_category = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['amount']
        indexes = [
            models.Index(fields=['operator', 'is_active']),
            models.Index(fields=['amount', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.plan_name} - ₹{self.amount}"

class bbpsServiceCharge(models.Model):
    """Service charges for different amount ranges"""
    AMOUNT_RANGE_CHOICES = [
        ('0-100', '₹0 - ₹100'),
        ('101-500', '₹101 - ₹500'),
        ('501-1000', '₹501 - ₹1,000'),
        ('1001-5000', '₹1,001 - ₹5,000'),
        ('5001-10000', '₹5,001 - ₹10,000'),
    ]
    
    amount_range = models.CharField(max_length=20, choices=AMOUNT_RANGE_CHOICES, unique=True)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2)
    charge_type = models.CharField(max_length=10, choices=[
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage'),
    ], default='fixed')
    
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
            return 0.00
        except cls.DoesNotExist:
            return 0.00