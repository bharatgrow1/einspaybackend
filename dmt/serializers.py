from rest_framework import serializers
from .models import EkoBank
from decimal import Decimal
from dmt.models import EKOChargeConfig, DMTChargeScheme
from commission.models import CommissionPlan
from commission.serializers import CommissionPlanSerializer


class DMTOnboardSerializer(serializers.Serializer):
    pan_number = serializers.CharField(max_length=10, required=True)
    mobile = serializers.CharField(max_length=15, required=True)
    first_name = serializers.CharField(max_length=100, required=True)
    last_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    residence_address = serializers.DictField(required=True)
    dob = serializers.CharField(max_length=10, required=True)
    shop_name = serializers.CharField(max_length=255, required=True)


class DMTVerifyCustomerSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=10, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)

class DMTResendOTPSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=10, required=True)


class DMTCreateCustomerSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=10, required=True)
    name = serializers.CharField(max_length=200, required=True)
    dob = serializers.CharField(max_length=10, required=True)
    address_line = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=True)
    state = serializers.CharField(max_length=100, required=True)
    pincode = serializers.CharField(max_length=6, required=True)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)
    skip_verification = serializers.BooleanField(default=False, required=False)
    
    def validate_mobile(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Mobile number must be 10 digits")
        if not value.isdigit():
            raise serializers.ValidationError("Mobile number must contain only digits")
        return value
    
    def validate_dob(self, value):
        try:
            from datetime import datetime
            datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            raise serializers.ValidationError("DOB must be in YYYY-MM-DD format")
        return value
    
    def validate_pincode(self, value):
        if len(value) != 6:
            raise serializers.ValidationError("Pincode must be 6 digits")
        if not value.isdigit():
            raise serializers.ValidationError("Pincode must contain only digits")
        return value
    

class DMTGetProfileSerializer(serializers.Serializer):
    customer_mobile = serializers.CharField(max_length=15, required=True)

class DMTBiometricKycSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    aadhar = serializers.CharField(max_length=12, required=True)
    piddata = serializers.CharField(required=True)

class DMTKycOTPVerifySerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    kyc_request_id = serializers.CharField(required=True)

class DMTAddRecipientSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_name = serializers.CharField(max_length=255, required=True)
    recipient_mobile = serializers.CharField(max_length=15, required=False, allow_blank=True)
    account = serializers.CharField(max_length=50, required=True)
    ifsc = serializers.CharField(max_length=11, required=True)
    bank_id = serializers.IntegerField(required=True)
    account_type = serializers.IntegerField(default=1)
    recipient_type = serializers.IntegerField(default=3)

class DMTGetRecipientsSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)

class DMTSendTxnOTPSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)

class DMTInitiateTransactionSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    


class EkoBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = EkoBank
        fields = ["bank_id", "bank_name", "bank_code", "static_ifsc"]


class DMTTransactionInquirySerializer(serializers.Serializer):
    inquiry_id = serializers.CharField(required=True)
    is_client_ref_id = serializers.BooleanField(default=False, required=False)
    
    def validate_inquiry_id(self, value):
        if not value:
            raise serializers.ValidationError("Inquiry ID cannot be empty")
        return value
    

class DMTRefundSerializer(serializers.Serializer):
    tid = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)


class DMTRefundOTPResendSerializer(serializers.Serializer):
    tid = serializers.CharField(required=True)



class DMTWalletTransactionSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=15, required=True)
    recipient_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True,
        coerce_to_string=True
    )
    otp = serializers.CharField(max_length=6, required=True)
    otp_ref_id = serializers.CharField(required=True)
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    recipient_name = serializers.CharField(required=False)
    account = serializers.CharField(required=False)
    ifsc = serializers.CharField(required=False)

    def validate_amount(self, value):
        if isinstance(value, float):
            return Decimal(str(value))
        return value
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value
    


class EKOChargeConfigSerializer(serializers.ModelSerializer):
    amount_range_display = serializers.SerializerMethodField()
    
    class Meta:
        model = EKOChargeConfig
        fields = ['id', 'amount_from', 'amount_to', 'amount_range_display', 
                 'customer_fee_net_gst', 'eko_pricing', 'commission_after_tds']
    
    def get_amount_range_display(self, obj):
        return f"₹{obj.amount_from} - ₹{obj.amount_to}"


class DMTChargeSchemeCreateSerializer(serializers.ModelSerializer):
    amount_from = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_to = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = DMTChargeScheme
        fields = [
            'name', 'plan', 'amount_from', 'amount_to',
            'charge_type', 'percentage_charge', 'flat_charge',
            'retailer_percentage', 'dealer_percentage', 
            'master_percentage', 'admin_percentage', 'superadmin_percentage'
        ]
    
    def validate(self, data):

        instance = self.instance

        admin = data.get(
            "admin_percentage",
            instance.admin_percentage if instance else 0
        )

        master = data.get(
            "master_percentage",
            instance.master_percentage if instance else 0
        )

        dealer = data.get(
            "dealer_percentage",
            instance.dealer_percentage if instance else 0
        )

        retailer = data.get(
            "retailer_percentage",
            instance.retailer_percentage if instance else 0
        )

        superadmin = data.get(
            "superadmin_percentage",
            instance.superadmin_percentage if instance else 0
        )

        request = self.context.get("request")

        if not request:
            return data

        role = request.user.role

        # =========================
        # SUPERADMIN RULE
        # =========================
        if role == "superadmin":

            if admin > superadmin:
                raise serializers.ValidationError(
                    "Admin cannot exceed Superadmin"
                )

        # =========================
        # ADMIN RULE
        # =========================
        if role == "admin":

            if master > admin:
                raise serializers.ValidationError(
                    "Master cannot exceed Admin"
                )

        # =========================
        # MASTER RULE
        # =========================
        if role == "master":

            if dealer > master:
                raise serializers.ValidationError(
                    "Dealer cannot exceed Master"
                )

        # =========================
        # DEALER RULE
        # =========================
        if role == "dealer":

            if retailer > dealer:
                raise serializers.ValidationError(
                    "Retailer cannot exceed Dealer"
                )

        return data
    
    def create(self, validated_data):
        validated_data['amount_range'] = f"{validated_data['amount_from']}-{validated_data['amount_to']}"
        return super().create(validated_data)


class DMTChargeSchemeSerializer(serializers.ModelSerializer):
    plan = CommissionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=CommissionPlan.objects.filter(is_active=True),
        write_only=True,
        source='plan'
    )
    eko_commission_display = serializers.SerializerMethodField()
    total_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = DMTChargeScheme
        fields = [
            'id', 'name', 'plan', 'plan_id', 'amount_range', 'amount_from', 'amount_to',
            'eko_commission', 'eko_commission_display',
            'charge_type', 'percentage_charge', 'flat_charge',
            'retailer_percentage', 'dealer_percentage', 
            'master_percentage', 'admin_percentage', 'superadmin_percentage',
            'total_percentage', 'is_active', 'created_at'
        ]
    
    def get_eko_commission_display(self, obj):
        return f"₹{obj.eko_commission}"
    
    def get_total_percentage(self, obj):
        return obj.retailer_percentage + obj.dealer_percentage + obj.master_percentage + obj.admin_percentage + obj.superadmin_percentage


    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")

        if not request:
            return data

        role = request.user.role

        if role == "admin":
            data.pop("superadmin_percentage", None)

        if role == "master":
            data.pop("superadmin_percentage", None)
            data.pop("admin_percentage", None)

        if role == "dealer":
            data.pop("superadmin_percentage", None)
            data.pop("admin_percentage", None)
            data.pop("master_percentage", None)

        if role == "retailer":
            data.pop("superadmin_percentage", None)
            data.pop("admin_percentage", None)
            data.pop("master_percentage", None)
            data.pop("dealer_percentage", None)

        return data
    

class ChargePreviewSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    plan_id = serializers.IntegerField(required=False)
    
    def validate(self, data):
        amount = data['amount']
        
        plan_id = data.get('plan_id')
        
        if plan_id:
            schemes = DMTChargeScheme.objects.filter(
                plan_id=plan_id,
                amount_from__lte=amount,
                amount_to__gte=amount,
                is_active=True
            )
        else:
            schemes = DMTChargeScheme.objects.filter(
                amount_from__lte=amount,
                amount_to__gte=amount,
                is_active=True
            )
        
        if not schemes.exists():
            raise serializers.ValidationError("No charge scheme found for this amount")
        
        data['schemes'] = schemes
        return data
