from rest_framework import serializers
from commission.models import (CommissionPlan, UserCommissionPlan, ServiceCommission, CommissionTransaction,
                               CommissionPayout, OperatorCommission)
from users.models import User
from services.models import ServiceCategory, ServiceSubCategory

class CommissionPlanSerializer(serializers.ModelSerializer):
    assigned_users_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CommissionPlan
        fields = [
            'id', 'name', 'plan_type', 'description', 'is_active',
            'assigned_users_count', 'created_at', 'updated_at'
        ]
    
    def get_assigned_users_count(self, obj):
        return UserCommissionPlan.objects.filter(commission_plan=obj, is_active=True).count()

class ServiceCommissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    superadmin_commission = serializers.SerializerMethodField()
    total_distributed = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCommission
        fields = [
            'id', 'service_category', 'service_category_name', 'service_subcategory', 
            'service_subcategory_name', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 'admin_commission', 'master_commission',
            'dealer_commission', 'retailer_commission', 'superadmin_commission', 'total_distributed',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['superadmin_commission', 'total_distributed']
    
    def get_superadmin_commission(self, obj):
        """Calculate superadmin commission percentage"""
        total_distributed = (
            obj.admin_commission + 
            obj.master_commission + 
            obj.dealer_commission + 
            obj.retailer_commission
        )
        return 100 - total_distributed
    
    def get_total_distributed(self, obj):
        """Get total distributed percentage"""
        return (
            obj.admin_commission + 
            obj.master_commission + 
            obj.dealer_commission + 
            obj.retailer_commission
        )
    
    def validate(self, data):
        """Validate commission distribution doesn't exceed 100% for percentage type"""
        request = self.context.get('request')
        user = request.user if request else None
        
        if data.get('commission_type') == 'percentage':
            total_commission = (
                data.get('admin_commission', 0) +
                data.get('master_commission', 0) +
                data.get('dealer_commission', 0) +
                data.get('retailer_commission', 0)
            )
            if total_commission > 100:
                raise serializers.ValidationError(
                    "Total commission distribution cannot exceed 100%"
                )
            
            # Role-based validation
            if user:
                user_role = user.role
                if user_role == 'superadmin' and data.get('admin_commission', 0) > 100:
                    raise serializers.ValidationError("Admin commission cannot exceed 100%")
                elif user_role == 'admin' and data.get('master_commission', 0) > 100:
                    raise serializers.ValidationError("Master commission cannot exceed 100%")
                elif user_role == 'master' and data.get('dealer_commission', 0) > 100:
                    raise serializers.ValidationError("Dealer commission cannot exceed 100%")
                elif user_role == 'dealer' and data.get('retailer_commission', 0) > 100:
                    raise serializers.ValidationError("Retailer commission cannot exceed 100%")
        
        return data
    


class RoleBasedServiceCommissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    superadmin_commission = serializers.SerializerMethodField()
    
    # Show only what user can see based on role
    admin_commission = serializers.SerializerMethodField()
    master_commission = serializers.SerializerMethodField()
    dealer_commission = serializers.SerializerMethodField()
    retailer_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCommission
        fields = [
            'id', 'service_category', 'service_category_name', 'service_subcategory', 
            'service_subcategory_name', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 
            'admin_commission', 'master_commission', 'dealer_commission', 'retailer_commission',
            'superadmin_commission', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['superadmin_commission']
    
    def get_admin_commission(self, obj):
        """Only show admin commission to superadmin and admin"""
        request = self.context.get('request')
        if request and request.user.role in ['superadmin', 'admin']:
            return obj.admin_commission
        return None
    
    def get_master_commission(self, obj):
        """Show master commission to superadmin, admin, and master"""
        request = self.context.get('request')
        if request and request.user.role in ['superadmin', 'admin', 'master']:
            return obj.master_commission
        return None
    
    def get_dealer_commission(self, obj):
        """Show dealer commission to superadmin, admin, master, and dealer"""
        request = self.context.get('request')
        if request and request.user.role in ['superadmin', 'admin', 'master', 'dealer']:
            return obj.dealer_commission
        return None
    
    def get_retailer_commission(self, obj):
        """Show retailer commission to all roles"""
        request = self.context.get('request')
        if request:
            return obj.retailer_commission
        return None
    
    def get_superadmin_commission(self, obj):
        """Calculate superadmin commission percentage"""
        total_distributed = (
            obj.admin_commission + 
            obj.master_commission + 
            obj.dealer_commission + 
            obj.retailer_commission
        )
        return 100 - total_distributed



class CommissionTransactionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    retailer_username = serializers.CharField(source='retailer_user.username', read_only=True)
    service_name = serializers.SerializerMethodField()
    transaction_reference = serializers.CharField(source='main_transaction.reference_number', read_only=True)
    operator_name = serializers.SerializerMethodField() 
    
    class Meta:
        model = CommissionTransaction
        fields = [
            'id', 'reference_number', 'user', 'user_username', 'role', 
            'commission_amount', 'retailer_user', 'retailer_username',
            'original_transaction_amount', 'main_transaction', 'transaction_reference',
            'service_submission', 'service_name', 'commission_config', 'commission_plan',
            'operator_commission', 'operator_name',
            'transaction_type', 'status', 'description', 'created_at'
        ]
    
    def get_service_name(self, obj):
        if obj.service_submission:
            return obj.service_submission.service_form.name
        elif obj.operator_commission:
            return obj.operator_commission.operator_name
        return "N/A"
    
    def get_operator_name(self, obj):
        if obj.operator_commission:
            return obj.operator_commission.operator_name
        return None

class UserCommissionPlanSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    commission_plan_type = serializers.CharField(source='commission_plan.plan_type', read_only=True)
    assigned_by_username = serializers.CharField(source='assigned_by.username', read_only=True)
    
    class Meta:
        model = UserCommissionPlan
        fields = [
            'id', 'user', 'user_username', 'user_role', 'commission_plan', 
            'commission_plan_name', 'commission_plan_type', 'is_active',
            'assigned_by', 'assigned_by_username', 'assigned_at', 'updated_at'
        ]


class CommissionPayoutSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)
    
    class Meta:
        model = CommissionPayout
        fields = [
            'id', 'user', 'user_username', 'user_role', 'total_amount',
            'commission_period_start', 'commission_period_end', 'status',
            'reference_number', 'payout_method', 'payout_reference',
            'processed_by', 'processed_by_username', 'processed_at',
            'created_at', 'updated_at'
        ]


class CommissionStatsSerializer(serializers.Serializer):
    total_commission = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_payouts = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payouts = serializers.DecimalField(max_digits=15, decimal_places=2)
    commission_by_role = serializers.DictField()
    top_services = serializers.ListField()

class AssignCommissionPlanSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField())
    commission_plan_id = serializers.IntegerField()

class CommissionCalculatorSerializer(serializers.Serializer):
    service_subcategory_id = serializers.IntegerField()
    transaction_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    user_id = serializers.IntegerField(required=False)
    

class RoleFilteredServiceCommissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    
    # Only show the filtered role's commission
    role_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCommission
        fields = [
            'id', 'service_category', 'service_category_name', 'service_subcategory', 
            'service_subcategory_name', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 'role_commission', 'is_active', 
            'created_at', 'updated_at'
        ]
    
    def get_role_commission(self, obj):
        """Get commission percentage for the filtered role only"""
        request = self.context.get('request')
        if request:
            role = request.query_params.get('role')
            if role:
                distribution_percentages = obj.get_distribution_percentages()
                return distribution_percentages.get(role, 0)
        return 0



class DealerRetailerServiceCommissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    
    # Only show the user's role commission
    my_commission_percentage = serializers.SerializerMethodField()
    example_commission = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCommission
        fields = [
            'id', 'service_category', 'service_category_name', 'service_subcategory', 
            'service_subcategory_name', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 'my_commission_percentage', 
            'example_commission', 'is_active'
        ]
    
    def get_my_commission_percentage(self, obj):
        """Get commission percentage for the current user's role"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_role = request.user.role
            distribution_percentages = obj.get_distribution_percentages()
            return distribution_percentages.get(user_role, 0)
        return 0
    
    def get_example_commission(self, obj):
        """Calculate example commission for ₹1000 transaction"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_role = request.user.role
            distribution_percentages = obj.get_distribution_percentages()
            role_percentage = distribution_percentages.get(user_role, 0)
            
            if role_percentage > 0:
                example_amount = 1000
                total_commission = obj.calculate_commission(example_amount)
                role_commission = (total_commission * role_percentage) / 100
                
                return {
                    'transaction_amount': example_amount,
                    'your_commission': role_commission,
                    'description': f"You earn ₹{role_commission} from ₹{example_amount} transaction"
                }
        return None



class BulkServiceCommissionCreateSerializer(serializers.Serializer):
    commissions = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    
    def validate(self, data):
        for commission_data in data['commissions']:
            if commission_data.get('commission_type') == 'percentage':
                total_commission = (
                    commission_data.get('admin_commission', 0) +
                    commission_data.get('master_commission', 0) +
                    commission_data.get('dealer_commission', 0) +
                    commission_data.get('retailer_commission', 0)
                )
                if total_commission > 100:
                    raise serializers.ValidationError(
                        f"Total commission distribution cannot exceed 100% for service {commission_data.get('service_subcategory')}"
                    )
        return data
    


class OperatorCommissionSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.operator_name', read_only=True)
    operator_type = serializers.CharField(source='operator.operator_type', read_only=True)
    operator_id = serializers.CharField(source='operator.operator_id', read_only=True)
    commission_plan_name = serializers.CharField(source='commission_plan.name', read_only=True)
    service_subcategory_name = serializers.CharField(
        source='service_subcategory.name',
        read_only=True
    )
    superadmin_commission = serializers.SerializerMethodField()
    total_distributed = serializers.SerializerMethodField()
    
    class Meta:
        model = OperatorCommission
        fields = [
            'id', 'operator', 'operator_id', 'operator_name', 'operator_type','service_subcategory',
            'service_subcategory_name',
            'operator_circle', 'commission_plan', 'commission_plan_name',
            'commission_type', 'commission_value', 'admin_commission', 
            'master_commission', 'dealer_commission', 'retailer_commission',
            'superadmin_commission', 'total_distributed', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'operator_id', 'operator_name', 'operator_type', 
            'commission_plan_name', 'superadmin_commission', 'total_distributed'
        ]  # इसे update करें
    
    def get_superadmin_commission(self, obj):
        """Calculate superadmin commission percentage"""
        total_distributed = (
            (obj.admin_commission or 0) + 
            (obj.master_commission or 0) + 
            (obj.dealer_commission or 0) + 
            (obj.retailer_commission or 0)
        )
        return 100 - total_distributed
    
    def get_total_distributed(self, obj):
        """Get total distributed percentage"""
        return (
            (obj.admin_commission or 0) + 
            (obj.master_commission or 0) + 
            (obj.dealer_commission or 0) + 
            (obj.retailer_commission or 0)
        )