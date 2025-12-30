from rest_framework import serializers
from services.models import (UploadImage, ServiceSubCategory, ServiceCategory, FormField, ServiceForm, 
                             FormSubmissionFile, ServiceSubmission, UserServicePermission, RoleServicePermission)
from users.models import User


class UploadImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = UploadImage
        fields = ['id', 'image', 'image_url', 'created_at']
        read_only_fields = ['id', 'image_url', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None

class ServiceSubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    required_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceSubCategory
        fields = [
            'id', 'category', 'category_name', 'name', 'description', 'image', 'is_active', 
            'required_fields', 'created_at',
            # Boolean fields
            'require_customer_name', 'require_customer_email', 'require_customer_phone', 'require_customer_address',
            'require_mobile_number', 'require_consumer_number', 'require_account_number', 'require_bill_number',
            'require_transaction_id', 'require_reference_number', 'require_state', 'require_city', 'require_pincode',
            'require_amount', 'require_tax_amount', 'require_total_amount', 'require_service_provider',
            'require_operator', 'require_biller', 'require_bank_name', 'require_vehicle_number', 'require_vehicle_type',
            'require_rc_number', 'require_student_name', 'require_student_id', 'require_institute_name',
            'require_course_name', 'require_loan_type', 'require_loan_account_number', 'require_emi_amount',
            'require_ott_platform', 'require_subscription_plan', 'require_validity', 'require_meter_number',
            'require_connection_type', 'require_usage_amount', 'require_payment_method', 'require_card_number',
            'require_card_holder_name', 'require_expiry_date', 'require_cvv', 'require_due_date',
            'require_billing_period', 'require_remarks', 'require_documents',
             # New DTH/Cable TV fields
            'require_dth_operator', 'require_dth_plan_amount', 'require_cable_operator',
            'require_cable_plan_amount', 'require_subscriber_number', 'require_consumer_id',
            
            # New Mobile bbps fields
            'require_bbps_type', 'require_plan_browsing',
            
            # New Education fields
            'require_student_unique_id', 'require_student_relation', 'require_institution_name',
            
            # New OTT fields
            'require_ott_plan_selection', 'require_rent_to_mobile', 'require_pan_number',
            
            # New Credit Card fields
            'require_card_number', 'require_card_holder_name', 'require_payment_option',
            'require_full_amount', 'require_minimum_amount', 'require_other_amount',
            
            # New Society Maintenance fields
            'require_apartment_number', 'require_building_number',
            
            # New Traffic Challan fields
            'require_traffic_authority', 'require_challan_number',
            
            # New Municipal Tax fields
            'require_corporation', 'require_taxpayer_relation', 'require_upic_number',
            
            # New Financial fields
            'require_financial_year', 'require_assessment_year',
            
            # New Additional fields
            'require_bill_due_date', 'require_late_fee', 'require_discount_amount',
            'require_payment_date', 'require_service_charge',
            'require_browse_plan', 'require_fetch_plan', 'require_plan_selection',
            'require_water_board',
            'require_broadband_name', 
            'require_landline_number',
            'require_card_number',
            'require_corporation',
            'require_flat_number',
            'require_upi_id',
            'require_confirm_account_number',
            'require_ifsc',
            'require_adhar_number',
            'require_branch_number',
        ]
    
    def get_required_fields(self, obj):
        return obj.get_required_fields()

class ServiceCategorySerializer(serializers.ModelSerializer):
    subcategories = ServiceSubCategorySerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    required_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'icon', 'is_active', 'allow_direct_service',
            'subcategories', 'created_by', 'created_by_username', 'required_fields',
            'created_at', 'updated_at',
            
            # सभी boolean fields include करें
            # Personal Information
            'require_customer_name', 'require_customer_email', 'require_customer_phone', 'require_customer_address',
            # Service Specific
            'require_mobile_number', 'require_consumer_number', 'require_account_number', 'require_bill_number',
            'require_transaction_id', 'require_reference_number',
            # Location
            'require_state', 'require_city', 'require_pincode',
            # Amount
            'require_amount', 'require_tax_amount', 'require_total_amount',
            # Service Provider
            'require_service_provider', 'require_operator', 'require_biller', 'require_bank_name',
            # Vehicle
            'require_vehicle_number', 'require_vehicle_type', 'require_rc_number',
            # Education
            'require_student_name', 'require_student_id', 'require_institute_name', 'require_course_name',
            # Loan
            'require_loan_type', 'require_loan_account_number', 'require_emi_amount',
            # OTT
            'require_ott_platform', 'require_subscription_plan', 'require_validity',
            # Utility
            'require_meter_number', 'require_connection_type', 'require_usage_amount',
            # Payment
            'require_payment_method', 'require_card_number', 'require_card_holder_name', 'require_expiry_date', 'require_cvv',
            # Additional
            'require_due_date', 'require_billing_period', 'require_remarks', 'require_documents',
            # DTH/Cable TV
            'require_dth_operator', 'require_dth_plan_amount', 'require_cable_operator', 'require_cable_plan_amount',
            'require_subscriber_number', 'require_consumer_id',
            # Mobile bbps
            'require_bbps_type', 'require_plan_browsing',
            # Education
            'require_student_unique_id', 'require_student_relation', 'require_institution_name',
            # OTT
            'require_ott_plan_selection', 'require_rent_to_mobile', 'require_pan_number',
            # Credit Card
            'require_payment_option', 'require_full_amount', 'require_minimum_amount', 'require_other_amount',
            # Society Maintenance
            'require_apartment_number', 'require_building_number',
            # Traffic Challan
            'require_traffic_authority', 'require_challan_number',
            # Municipal Tax
            'require_corporation', 'require_taxpayer_relation', 'require_upic_number',
            # Financial
            'require_financial_year', 'require_assessment_year',
            # Additional Common
            'require_bill_due_date', 'require_late_fee', 'require_discount_amount', 'require_payment_date', 'require_service_charge',
            'require_browse_plan', 'require_fetch_plan', 'require_plan_selection'
        ]
    
    def get_required_fields(self, obj):
        return obj.get_required_fields()

class ServiceCategoryWithFormsSerializer(serializers.ModelSerializer):
    subcategories = ServiceSubCategorySerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    can_create_direct_form = serializers.BooleanField(source='allow_direct_service', read_only=True)
    required_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'icon', 'is_active', 
            'allow_direct_service', 'can_create_direct_form',
            'subcategories', 'created_by', 'created_by_username', 
            'required_fields', 'created_at', 'updated_at'
        ]
    
    def get_required_fields(self, obj):
        return obj.get_required_fields()

class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = [
            'id', 'field_id', 'field_name', 'field_label', 'field_type', 
            'required', 'readonly', 'hidden', 'placeholder', 'help_text',
            'css_class', 'min_value', 'max_value', 'min_length', 'max_length',
            'validation_regex', 'error_message', 'options', 'use_service_options',
            'order', 'group', 'depends_on', 'condition_value', 'condition_type',
            'is_active'
        ]

class ServiceFormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    service_category_name = serializers.CharField(source='service_subcategory.category.name', read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = [
            'id', 'service_type', 'service_subcategory', 'service_subcategory_name',
            'service_category_name', 'name', 'description', 'is_active',
            'requires_approval', 'max_submissions_per_user', 'fields',
            'created_at', 'updated_at'
        ]

class FormSubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormSubmissionFile
        fields = ['id', 'field_name', 'file', 'original_filename', 'file_size', 'uploaded_at']

class ServiceSubmissionSerializer(serializers.ModelSerializer):
    service_form_name = serializers.CharField(source='service_form.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    files = FormSubmissionFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceSubmission
        fields = [
            'id', 'submission_id', 'service_form', 'service_form_name',
            'service_subcategory', 'service_subcategory_name', 'submitted_by',
            'submitted_by_username', 'customer_name', 'customer_email',
            'customer_phone', 'form_data', 'status', 'payment_status',
            'amount', 'transaction_id', 'service_response',
            'service_reference_id', 'notes', 'files', 'submitted_at',
            'processed_at', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['submission_id', 'submitted_at', 'processed_at', 'completed_at']

class DynamicFormSubmissionSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.form_fields = kwargs.pop('form_fields', [])
        super().__init__(*args, **kwargs)
        
        # Dynamically add fields based on form configuration
        for field in self.form_fields:
            field_name = field.field_name
            
            if field.field_type == 'text':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    max_length=field.max_length,
                    help_text=field.help_text
                )
            elif field.field_type == 'number':
                self.fields[field_name] = serializers.IntegerField(
                    required=field.required,
                    min_value=field.min_value,
                    max_value=field.max_value,
                    help_text=field.help_text
                )
            elif field.field_type == 'email':
                self.fields[field_name] = serializers.EmailField(
                    required=field.required,
                    allow_blank=not field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'phone':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    max_length=15,
                    help_text=field.help_text
                )
            elif field.field_type == 'boolean':
                self.fields[field_name] = serializers.BooleanField(
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type in ['select', 'radio']:
                choices = [(opt, opt) for opt in (field.options or [])]
                self.fields[field_name] = serializers.ChoiceField(
                    choices=choices,
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'multiselect':
                choices = [(opt, opt) for opt in (field.options or [])]
                self.fields[field_name] = serializers.MultipleChoiceField(
                    choices=choices,
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'date':
                self.fields[field_name] = serializers.DateField(
                    required=field.required,
                    help_text=field.help_text
                )
            elif field.field_type == 'textarea':
                self.fields[field_name] = serializers.CharField(
                    required=field.required,
                    allow_blank=not field.required,
                    help_text=field.help_text,
                    style={'base_template': 'textarea.html'}
                )
            elif field.field_type == 'amount':
                self.fields[field_name] = serializers.DecimalField(
                    required=field.required,
                    max_digits=10,
                    decimal_places=2,
                    min_value=field.min_value,
                    max_value=field.max_value,
                    help_text=field.help_text
                )

            elif field.field_type in ['button', 'plan_browse', 'plan_fetch']:
                # Button fields don't need validation as they don't submit data
                self.fields[field_name] = serializers.CharField(
                    required=False,
                    allow_blank=True,
                    help_text=field.help_text
                )
            elif field.field_type == 'plan_selection':
                choices = [(opt, opt) for opt in (field.options or [])]
                self.fields[field_name] = serializers.ChoiceField(
                    choices=choices,
                    required=field.required,
                    help_text=field.help_text
                )

class ServiceFormWithFieldsSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = ['id', 'name', 'description', 'service_type', 'fields']

class DirectServiceFormSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    
    class Meta:
        model = ServiceForm
        fields = [
            'id', 'service_type', 'service_category', 'service_category_name',
            'name', 'description', 'is_active', 'requires_approval',
            'max_submissions_per_user', 'created_at', 'updated_at'
        ]


class RoleServicePermissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    category_id = serializers.IntegerField(source='service_category.id', read_only=True)
    subcategory_id = serializers.IntegerField(source='service_subcategory.id', read_only=True)
    
    class Meta:
        model = RoleServicePermission
        fields = [
            'id', 'role', 'service_category', 'service_category_name', 
            'service_subcategory', 'service_subcategory_name', 'category_id',
            'subcategory_id', 'is_active', 'can_view', 'can_use',
            'created_at', 'updated_at'
        ]

class UserServicePermissionSerializer(serializers.ModelSerializer):
    service_category_name = serializers.CharField(source='service_category.name', read_only=True)
    service_subcategory_name = serializers.CharField(source='service_subcategory.name', read_only=True)
    category_id = serializers.IntegerField(source='service_category.id', read_only=True)
    subcategory_id = serializers.IntegerField(source='service_subcategory.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserServicePermission
        fields = [
            'id', 'user', 'username', 'service_category', 'service_category_name',
            'service_subcategory', 'service_subcategory_name', 'category_id',
            'subcategory_id', 'is_active', 'can_view', 'can_use',
            'created_at', 'updated_at'
        ]

class BulkRolePermissionSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    permissions = serializers.ListField(
        child=serializers.DictField()
    )

class BulkUserPermissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    permissions = serializers.ListField(
        child=serializers.DictField()
    )

class AvailableServicesSerializer(serializers.Serializer):
    categories = ServiceCategorySerializer(many=True)
    subcategories = ServiceSubCategorySerializer(many=True)