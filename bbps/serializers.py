from rest_framework import serializers
from .models import bbpsTransaction, Operator, Plan, bbpsServiceCharge

class OperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operator
        fields = [
            'id', 'operator_id', 'operator_name', 'operator_type',
            'category_id', 'is_active', 'circle', 'state', 'location',
            'commission_percentage', 'flat_commission'
        ]

class PlanSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.operator_name', read_only=True)
    
    class Meta:
        model = Plan
        fields = [
            'id', 'plan_id', 'plan_name', 'plan_description',
            'amount', 'validity', 'data_allowance', 'talktime',
            'sms_allowance', 'plan_type', 'is_popular', 'is_active',
            'eko_plan_code', 'eko_plan_category', 'operator', 'operator_name'
        ]

class bbpsTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    operator_name = serializers.CharField(source='operator.operator_name', read_only=True)
    
    class Meta:
        model = bbpsTransaction
        fields = [
            'id', 'transaction_id', 'user', 'user_username',
            'operator_id', 'operator_name', 'operator_type',
            'circle', 'mobile_number', 'consumer_number',
            'customer_name', 'amount', 'service_charge',
            'total_amount', 'client_ref_id', 'eko_transaction_ref',
            'eko_message', 'eko_txstatus_desc', 'eko_response_status',
            'status', 'status_message', 'payment_status',
            'transaction_reference', 'initiated_at', 'processed_at',
            'completed_at', 'api_request', 'api_response',
            'error_details', 'is_plan_bbps', 'plan_details'
        ]
        read_only_fields = [
            'transaction_id', 'user_username', 'operator_name',
            'initiated_at', 'processed_at', 'completed_at'
        ]

class bbpsRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15, required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    operator_id = serializers.CharField(max_length=50, required=True)
    operator_type = serializers.ChoiceField(
        choices=bbpsTransaction.OPERATOR_TYPES,
        default='prepaid'
    )
    circle = serializers.CharField(max_length=100, required=False, allow_null=True)
    consumer_number = serializers.CharField(max_length=50, required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=255, required=False, allow_null=True)
    is_plan_bbps = serializers.BooleanField(default=False)
    plan_id = serializers.CharField(max_length=100, required=False, allow_null=True)
    pin = serializers.CharField(max_length=4, min_length=4, write_only=True, required=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        if len(value) != 4:
            raise serializers.ValidationError("PIN must be exactly 4 digits")
        return value

class BillFetchRequestSerializer(serializers.Serializer):
    operator_id = serializers.CharField(max_length=50, required=True)
    mobile_no = serializers.CharField(max_length=15, required=True)
    utility_acc_no = serializers.CharField(max_length=50, required=False, allow_null=True)
    sender_name = serializers.CharField(max_length=255, default="Customer")
    dob7 = serializers.CharField(required=False, allow_null=True)

class EKOOperatorResponseSerializer(serializers.Serializer):
    operator_id = serializers.CharField()
    operator_name = serializers.CharField()
    category_id = serializers.IntegerField()
    is_active = serializers.BooleanField()
    circle = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True)

class EKOBillFetchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    client_ref_id = serializers.CharField()
    data = serializers.DictField()

class EKObbpsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    transaction_id = serializers.CharField()
    client_ref_id = serializers.CharField()
    message = serializers.CharField(allow_null=True)
    eko_transaction_ref = serializers.CharField(allow_null=True)
    txstatus_desc = serializers.CharField(allow_null=True)
    eko_response = serializers.DictField()