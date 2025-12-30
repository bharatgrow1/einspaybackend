from rest_framework import serializers
from .models import VendorPayment, VendorBank, VendorPayment

class VendorPaymentSerializer(serializers.Serializer):
    recipient_name = serializers.CharField()
    account = serializers.CharField()
    ifsc = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = serializers.IntegerField()
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)
    purpose = serializers.CharField(required=False, allow_blank=True, default="Vendor Payment")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

class VendorPaymentResponseSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = VendorPayment
        fields = [
            'id', 
            'user',
            'recipient_name',
            'recipient_account',
            'recipient_ifsc',
            'amount',
            'processing_fee',
            'gst',
            'total_fee',
            'total_deduction',
            'status',
            'eko_tid',
            'client_ref_id',
            'bank_ref_num',
            'utr_number',
            'transaction_reference',
            'timestamp',
            'status_message',
            'payment_date',
            'purpose',
            'payment_mode',
            'created_at',
        ]



class VendorMobileVerificationSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)
    
    def validate_mobile(self, value):
        value = value.strip()
        if value.startswith('+91'):
            if len(value) != 13 or not value[1:].isdigit():
                raise serializers.ValidationError("Invalid mobile number with country code")
        elif value.startswith(('9', '8', '7', '6')):
            if len(value) != 10 or not value.isdigit():
                raise serializers.ValidationError("Mobile number must be 10 digits")
        else:
            raise serializers.ValidationError("Invalid mobile number format")
        return value

class VendorOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)
    otp = serializers.CharField(max_length=6, required=True)


class VendorBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorBank
        fields = [
            'id', 'vendor_mobile', 'recipient_name', 
            'account_number', 'ifsc_code', 'bank_name',
            'is_mobile_verified', 'is_bank_verified', 'beneficiary_fee',
            'created_at'
        ]
        read_only_fields = ['is_mobile_verified', 'is_bank_verified', 'beneficiary_fee', 'created_at']


class AddVendorBankSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)
    recipient_name = serializers.CharField(required=True)
    account_number = serializers.CharField(required=True)
    ifsc_code = serializers.CharField(required=True)
    
    def validate_mobile(self, value):
        """Basic mobile validation"""
        value = value.strip()
        # Remove +91 if present
        if value.startswith('+91'):
            value = value[3:]
        
        if len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError("Mobile number must be 10 digits")
        
        return value
    
    def validate_account_number(self, value):
        if len(value) < 9 or len(value) > 18 or not value.isdigit():
            raise serializers.ValidationError("Invalid account number")
        return value
    
    def validate_ifsc_code(self, value):
        if len(value) != 11 or not value[:4].isalpha() or not value[4:].isdigit():
            raise serializers.ValidationError("Invalid IFSC code format")
        return value

class SearchVendorByMobileSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)