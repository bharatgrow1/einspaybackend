from rest_framework import serializers
from .models import AEPSMerchant

class AEPSMerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AEPSMerchant
        fields = '__all__'
        read_only_fields = ['user_code', 'created_at']


class OnboardMerchantSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    middle_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    pan_number = serializers.CharField(max_length=10)
    shop_name = serializers.CharField(max_length=255)
    dob = serializers.DateField(format='%Y-%m-%d')

    address_line = serializers.CharField()
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    pincode = serializers.CharField(max_length=10)
    district = serializers.CharField(max_length=100, required=False, allow_blank=True)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True)



class AEPSActivationSerializer(serializers.Serializer):
    user_code = serializers.CharField()
    shop_type = serializers.CharField()
    modelname = serializers.CharField()
    devicenumber = serializers.CharField()
    latlong = serializers.CharField()
    aadhar = serializers.CharField()
    account = serializers.CharField()
    ifsc = serializers.CharField()
    address_as_per_proof = serializers.JSONField()
    office_address = serializers.JSONField()

    pan_card = serializers.FileField()
    aadhar_front = serializers.FileField()
    aadhar_back = serializers.FileField()


class OTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)


class OTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=10)


class UserServiceEnquirySerializer(serializers.Serializer):
    user_code = serializers.CharField()


class WalletBalanceSerializer(serializers.Serializer):
    customer_id_type = serializers.CharField()
    customer_id = serializers.CharField()
    user_code = serializers.CharField(required=False)


class MCCCategorySerializer(serializers.Serializer):
    user_code = serializers.CharField()


class StateRequestSerializer(serializers.Serializer):
    user_code = serializers.CharField()


