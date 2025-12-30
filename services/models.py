from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from users.models import User
from services.managers import ServiceManager


class UploadImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='service_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Image {self.id}"


class ServiceFieldRequirements(models.Model):
    """Abstract base model for common field requirements"""
    
    # Personal Information
    require_customer_name = models.BooleanField(default=False)
    require_customer_email = models.BooleanField(default=False)
    require_customer_phone = models.BooleanField(default=False)
    require_customer_address = models.BooleanField(default=False)
    
    # Service Specific Fields
    require_mobile_number = models.BooleanField(default=False)
    require_consumer_number = models.BooleanField(default=False)
    require_account_number = models.BooleanField(default=False)
    require_bill_number = models.BooleanField(default=False)
    require_transaction_id = models.BooleanField(default=False)
    require_reference_number = models.BooleanField(default=False)
    
    # Location Fields
    require_state = models.BooleanField(default=False)
    require_city = models.BooleanField(default=False)
    require_pincode = models.BooleanField(default=False)
    
    # Amount Fields
    require_amount = models.BooleanField(default=False)
    require_tax_amount = models.BooleanField(default=False)
    require_total_amount = models.BooleanField(default=False)
    
    # Service Provider Fields
    require_service_provider = models.BooleanField(default=False)
    require_operator = models.BooleanField(default=False)
    require_biller = models.BooleanField(default=False)
    require_bank_name = models.BooleanField(default=False)
    
    # Vehicle Fields
    require_vehicle_number = models.BooleanField(default=False)
    require_vehicle_type = models.BooleanField(default=False)
    require_rc_number = models.BooleanField(default=False)
    
    # Education Fields
    require_student_name = models.BooleanField(default=False)
    require_student_id = models.BooleanField(default=False)
    require_institute_name = models.BooleanField(default=False)
    require_course_name = models.BooleanField(default=False)
    
    # Loan Fields
    require_loan_type = models.BooleanField(default=False)
    require_loan_account_number = models.BooleanField(default=False)
    require_emi_amount = models.BooleanField(default=False)
    
    # OTT/Subscription Fields
    require_ott_platform = models.BooleanField(default=False)
    require_subscription_plan = models.BooleanField(default=False)
    require_validity = models.BooleanField(default=False)
    
    # Utility Fields
    require_meter_number = models.BooleanField(default=False)
    require_connection_type = models.BooleanField(default=False)
    require_usage_amount = models.BooleanField(default=False)
    
    # Payment Fields
    require_payment_method = models.BooleanField(default=False)
    require_card_number = models.BooleanField(default=False)
    require_card_holder_name = models.BooleanField(default=False)
    require_expiry_date = models.BooleanField(default=False)
    require_cvv = models.BooleanField(default=False)
    
    # Additional Fields
    require_due_date = models.BooleanField(default=False)
    require_billing_period = models.BooleanField(default=False)
    require_remarks = models.BooleanField(default=False)
    require_documents = models.BooleanField(default=False)

    # DTH/Cable TV Fields
    require_dth_operator = models.BooleanField(default=False)
    require_dth_plan_amount = models.BooleanField(default=False)
    require_cable_operator = models.BooleanField(default=False)
    require_cable_plan_amount = models.BooleanField(default=False)
    require_subscriber_number = models.BooleanField(default=False)
    require_consumer_id = models.BooleanField(default=False)
    
    # Mobile bbps Fields
    require_bbps_type = models.BooleanField(default=False)
    require_plan_browsing = models.BooleanField(default=False)
    
    # Education Fields
    require_student_unique_id = models.BooleanField(default=False)
    require_student_relation = models.BooleanField(default=False)
    require_institution_name = models.BooleanField(default=False)
    
    # OTT Subscription Fields
    require_ott_plan_selection = models.BooleanField(default=False)
    require_rent_to_mobile = models.BooleanField(default=False)
    require_pan_number = models.BooleanField(default=False)
    
    # Credit Card Bill Payment Fields
    require_payment_option = models.BooleanField(default=False)
    require_full_amount = models.BooleanField(default=False)
    require_minimum_amount = models.BooleanField(default=False)
    require_other_amount = models.BooleanField(default=False)
    
    # Society Maintenance Fields
    require_apartment_number = models.BooleanField(default=False)
    require_building_number = models.BooleanField(default=False)
    
    # Traffic Challan Fields
    require_traffic_authority = models.BooleanField(default=False)
    require_challan_number = models.BooleanField(default=False)
    
    # Municipal Tax Fields
    require_taxpayer_relation = models.BooleanField(default=False)
    require_upic_number = models.BooleanField(default=False)
    
    # Financial Fields
    require_financial_year = models.BooleanField(default=False)
    require_assessment_year = models.BooleanField(default=False)
    
    # Additional Common Fields
    require_bill_due_date = models.BooleanField(default=False)
    require_late_fee = models.BooleanField(default=False)
    require_discount_amount = models.BooleanField(default=False)
    require_payment_date = models.BooleanField(default=False)
    require_service_charge = models.BooleanField(default=False)

    require_browse_plan = models.BooleanField(default=False)
    require_fetch_plan = models.BooleanField(default=False)
    require_plan_selection = models.BooleanField(default=False)

    require_water_board = models.BooleanField(default=False)
    require_broadband_name = models.BooleanField(default=False)
    require_landline_number = models.BooleanField(default=False)
    require_corporation = models.BooleanField(default=False)
    require_flat_number = models.BooleanField(default=False)
    require_upi_id = models.BooleanField(default=False)
    require_confirm_account_number = models.BooleanField(default=False)
    require_ifsc = models.BooleanField(default=False)
    require_adhar_number = models.BooleanField(default=False)
    require_branch_number = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_boolean_field_names(self):
        """Get all boolean field names"""
        return [field.name for field in self._meta.fields if isinstance(field, models.BooleanField)]

    def get_required_fields_mapping(self):
        """Get mapping of boolean fields to field configurations"""
        return [
            # Personal Information
            ('require_customer_name', 'customer_name', 'text', 'Customer Name'),
            ('require_customer_email', 'customer_email', 'email', 'Customer Email'),
            ('require_customer_phone', 'customer_phone', 'phone', 'Customer Phone'),
            ('require_customer_address', 'customer_address', 'textarea', 'Customer Address'),
            
            # Service Specific
            ('require_mobile_number', 'mobile_number', 'phone', 'Mobile Number'),
            ('require_consumer_number', 'consumer_number', 'text', 'Consumer Number'),
            ('require_account_number', 'account_number', 'text', 'Account Number'),
            ('require_bill_number', 'bill_number', 'text', 'Bill Number'),
            ('require_transaction_id', 'transaction_id', 'text', 'Transaction ID'),
            ('require_reference_number', 'reference_number', 'text', 'Reference Number'),
            
            # Location
            ('require_state', 'state', 'select', 'State'),
            ('require_city', 'city', 'select', 'City'),
            ('require_pincode', 'pincode', 'text', 'Pincode'),
            
            # Amount
            ('require_amount', 'amount', 'amount', 'Amount'),
            ('require_tax_amount', 'tax_amount', 'amount', 'Tax Amount'),
            ('require_total_amount', 'total_amount', 'amount', 'Total Amount'),
            
            # Service Provider
            ('require_service_provider', 'service_provider', 'select', 'Service Provider'),
            ('require_operator', 'operator', 'select', 'Operator'),
            ('require_biller', 'biller', 'select', 'Biller'),
            ('require_bank_name', 'bank_name', 'select', 'Bank Name'),
            
            # Vehicle
            ('require_vehicle_number', 'vehicle_number', 'text', 'Vehicle Number'),
            ('require_vehicle_type', 'vehicle_type', 'select', 'Vehicle Type'),
            ('require_rc_number', 'rc_number', 'text', 'RC Number'),
            
            # Education
            ('require_student_name', 'student_name', 'text', 'Student Name'),
            ('require_student_id', 'student_id', 'text', 'Student ID'),
            ('require_institute_name', 'institute_name', 'select', 'Institute Name'),
            ('require_course_name', 'course_name', 'text', 'Course Name'),
            
            # Loan
            ('require_loan_type', 'loan_type', 'select', 'Loan Type'),
            ('require_loan_account_number', 'loan_account_number', 'text', 'Loan Account Number'),
            ('require_emi_amount', 'emi_amount', 'amount', 'EMI Amount'),
            
            # OTT
            ('require_ott_platform', 'ott_platform', 'select', 'OTT Platform'),
            ('require_subscription_plan', 'subscription_plan', 'select', 'Subscription Plan'),
            ('require_validity', 'validity', 'select', 'Validity'),
            
            # Utility
            ('require_meter_number', 'meter_number', 'text', 'Meter Number'),
            ('require_connection_type', 'connection_type', 'select', 'Connection Type'),
            ('require_usage_amount', 'usage_amount', 'amount', 'Usage Amount'),
            
            # Payment
            ('require_payment_method', 'payment_method', 'select', 'Payment Method'),
            ('require_card_number', 'card_number', 'text', 'Card Number'),
            ('require_card_holder_name', 'card_holder_name', 'text', 'Card Holder Name'),
            ('require_expiry_date', 'expiry_date', 'date', 'Expiry Date'),
            ('require_cvv', 'cvv', 'text', 'CVV'),
            
            # Additional
            ('require_due_date', 'due_date', 'date', 'Due Date'),
            ('require_billing_period', 'billing_period', 'text', 'Billing Period'),
            ('require_remarks', 'remarks', 'textarea', 'Remarks'),
            ('require_documents', 'documents', 'file', 'Documents'),

            # DTH/Cable TV Fields
            ('require_dth_operator', 'dth_operator', 'select', 'DTH Operator'),
            ('require_dth_plan_amount', 'dth_plan_amount', 'select', 'DTH Plan/Amount'),
            ('require_cable_operator', 'cable_operator', 'select', 'Cable Operator'),
            ('require_cable_plan_amount', 'cable_plan_amount', 'select', 'Cable Plan/Amount'),
            ('require_subscriber_number', 'subscriber_number', 'text', 'Subscriber Number'),
            ('require_consumer_id', 'consumer_id', 'text', 'Consumer ID'),
            
            # Mobile bbps Fields
            ('require_bbps_type', 'bbps_type', 'select', 'bbps Type'),
            ('require_plan_browsing', 'plan_browsing', 'select', 'Browse Plans'),
            
            # Education Fields
            ('require_student_unique_id', 'student_unique_id', 'text', 'Student Unique ID'),
            ('require_student_relation', 'student_relation', 'select', 'Student Relation'),
            ('require_institution_name', 'institution_name', 'select', 'Institution Name'),
            
            # OTT Subscription Fields
            ('require_ott_plan_selection', 'ott_plan_selection', 'select', 'OTT Plan'),
            ('require_rent_to_mobile', 'rent_to_mobile', 'phone', 'Rent to Mobile Number'),
            ('require_pan_number', 'pan_number', 'text', 'PAN Number'),
            
            # Credit Card Fields
            ('require_payment_option', 'payment_option', 'select', 'Payment Option'),
            ('require_full_amount', 'full_amount', 'amount', 'Full Amount'),
            ('require_minimum_amount', 'minimum_amount', 'amount', 'Minimum Amount'),
            ('require_other_amount', 'other_amount', 'amount', 'Other Amount'),
            
            # Society Maintenance Fields
            ('require_apartment_number', 'apartment_number', 'text', 'Apartment Number'),
            ('require_building_number', 'building_number', 'text', 'Building Number'),
            
            # Traffic Challan Fields
            ('require_traffic_authority', 'traffic_authority', 'select', 'Traffic Authority'),
            ('require_challan_number', 'challan_number', 'text', 'Challan Number'),
            
            # Municipal Tax Fields (REMOVED DUPLICATES)
            ('require_corporation', 'corporation', 'select', 'Municipal Corporation'),
            ('require_taxpayer_relation', 'taxpayer_relation', 'select', 'Taxpayer Relation'),
            ('require_upic_number', 'upic_number', 'text', 'UPIC Number'),
            
            # Financial Fields (REMOVED DUPLICATES)
            ('require_financial_year', 'financial_year', 'select', 'Financial Year'),
            ('require_assessment_year', 'assessment_year', 'select', 'Assessment Year'),
            
            # Additional Common Fields
            ('require_bill_due_date', 'bill_due_date', 'date', 'Bill Due Date'),
            ('require_late_fee', 'late_fee', 'amount', 'Late Fee'),
            ('require_discount_amount', 'discount_amount', 'amount', 'Discount Amount'),
            ('require_payment_date', 'payment_date', 'date', 'Payment Date'),
            ('require_service_charge', 'service_charge', 'amount', 'Service Charge'),
            ('require_browse_plan', 'browse_plan', 'button', 'Browse Plans'),
            ('require_fetch_plan', 'fetch_plan', 'button', 'Fetch Plans'),
            ('require_plan_selection', 'plan_selection', 'select', 'Select Plan'),

            # New Field Mappings (REMOVED DUPLICATES)
            ('require_water_board', 'water_board', 'select', 'Water Board'),
            ('require_broadband_name', 'broadband_name', 'select', 'Broadband Name'),
            ('require_landline_number', 'landline_number', 'phone', 'Landline Number'),
            ('require_flat_number', 'flat_number', 'text', 'Flat Number'),
            ('require_upi_id', 'upi_id', 'text', 'UPI ID'),
            ('require_confirm_account_number', 'confirm_account_number', 'text', 'Confirm Account Number'),
            ('require_ifsc', 'ifsc', 'text', 'IFSC Code'),
            ('require_adhar_number', 'adhar_number', 'text', 'Aadhar Number'),
            ('require_branch_number', 'branch_number', 'text', 'Branch Number'),
        ]

    def get_required_fields(self):
        """Get all required fields with strong deduplication"""
        fields = []
        seen_fields = set()
        
        for bool_field, field_name, field_type, field_label in self.get_required_fields_mapping():
            if getattr(self, bool_field):
                # Create a unique identifier for the field
                field_identifier = f"{field_name}_{field_type}_{field_label}"
                
                if field_identifier not in seen_fields:
                    fields.append({
                        'field_name': field_name,
                        'field_label': field_label,
                        'field_type': field_type,
                        'required': True
                    })
                    seen_fields.add(field_identifier)
        
        return fields

    def copy_boolean_fields_to(self, target_instance):
        """Copy all boolean fields to another instance"""
        for field_name in self.get_boolean_field_names():
            source_value = getattr(self, field_name)
            setattr(target_instance, field_name, source_value)
        target_instance.save()


class ServiceCategory(ServiceFieldRequirements):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    allow_direct_service = models.BooleanField(default=False)
    objects = ServiceManager()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['created_at']

    def __str__(self):
        return self.name

    def copy_boolean_fields_to_subcategory(self, subcategory):
        """Copy all boolean fields from category to subcategory"""
        self.copy_boolean_fields_to(subcategory)


class BillFetchConfig(models.Model):
    SERVICE_TYPES = [
        ('electricity', 'Electricity Bill'),
        ('water', 'Water Bill'),
        ('gas', 'Gas Bill'),
        ('broadband', 'Broadband Bill'),
        ('loan_emi', 'Loan EMI'),
        ('fastag', 'Fastag bbps'),
        ('credit_card', 'Credit Card Bill'),
        ('society_maintenance', 'Society Maintenance'),
        ('traffic_challan', 'Traffic Challan'),
        ('education_fee', 'Education Fee'),
        ('rent', 'Rent Payment'),
        ('dth', 'DTH bbps'),
        ('mobile', 'Mobile bbps'),
    ]
    
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, unique=True)
    identifier_field = models.CharField(max_length=100, help_text="Field name used to fetch bill")
    identifier_label = models.CharField(max_length=100, help_text="Label for identifier field")
    fetch_endpoint = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_service_type_display()} - {self.identifier_field}"


class ServiceSubCategory(ServiceFieldRequirements):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    objects = ServiceManager()
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Sub Categories"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.category.name} - {self.name}"
    

    def get_bill_fetch_config(self):
        """Get bill fetch configuration for this subcategory"""
        try:
            service_type_map = {
                'electricity': 'electricity',
                'water': 'water', 
                'gas': 'gas',
                'broadband': 'broadband',
                'loan': 'loan_emi',
                'fastag': 'fastag',
                'credit card': 'credit_card',
                'society maintenance': 'society_maintenance',
                'traffic challan': 'traffic_challan',
                'education fee': 'education_fee',
                'rent': 'rent',
                'dth': 'dth',
                'mobile_bbps': 'mobile',
            }
            
            service_type = service_type_map.get(self.name.lower())
            if service_type:
                return BillFetchConfig.objects.get(service_type=service_type, is_active=True)
        except BillFetchConfig.DoesNotExist:
            return None
        return None


class ServiceForm(models.Model):
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('email', 'Email Input'),
        ('phone', 'Phone Input'),
        ('textarea', 'Text Area'),
        ('boolean', 'Checkbox'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multiple Select'),
        ('date', 'Date Picker'),
        ('file', 'File Upload'),
        ('radio', 'Radio Buttons'),
        ('amount', 'Amount'),
        ('operator', 'Operator'),
        ('circle', 'Circle'),
        ('plan_type', 'Plan Type'),
        ('bbps_type', 'bbps Type'),
        ('button', 'Button'),
        ('plan_browse', 'Browse Plans'),
        ('plan_fetch', 'Fetch Plans'),
        ('plan_selection', 'Plan Selection'),
    ]

    SERVICE_TYPES = [
        ('mobile_bbps', 'Mobile bbps'),
        ('dtm', 'DTM Service'),
        ('electricity', 'Electricity Bill'),
        ('water', 'Water Bill'),
        ('gas', 'Gas Bill'),
        ('insurance', 'Insurance'),
        ('loan', 'Loan Service'),
        ('booking', 'Booking Service'),
        ('other', 'Other Service'),
        ('direct_category', 'Direct Category Service'), 
        ('direct_submission', 'Direct Submission'), 
    ]

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    service_category = models.ForeignKey(
        'ServiceCategory', 
        on_delete=models.CASCADE,
        related_name='service_forms',
        null=True,  # Direct category forms के लिए
        blank=True
    )
    
    service_subcategory = models.ForeignKey(
        'ServiceSubCategory', 
        on_delete=models.CASCADE,
        related_name='service_forms',
        null=True,  # Direct category forms के लिए  
        blank=True
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Form Configuration
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    max_submissions_per_user = models.IntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Service Form"
        verbose_name_plural = "Service Forms"

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.name}"


class FormField(models.Model):
    SERVICE_SPECIFIC_OPTIONS = {
        'operator': [
            'Airtel', 'Jio', 'Vi (Vodafone Idea)', 'BSNL', 'MTNL',
            'Airtel Prepaid', 'Airtel Postpaid', 'Jio Prepaid', 'Jio Postpaid',
            'Vi Prepaid', 'Vi Postpaid', 'BSNL Prepaid', 'BSNL Postpaid'
        ],
        'circle': [
            'Andhra Pradesh', 'Assam', 'Bihar', 'Chennai', 'Delhi NCR',
            'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jammu & Kashmir',
            'Karnataka', 'Kerala', 'Kolkata', 'Maharashtra', 'Mumbai',
            'North East', 'Odisha', 'Punjab', 'Rajasthan', 'Tamil Nadu',
            'Telangana', 'Uttar Pradesh (East)', 'Uttar Pradesh (West)',
            'West Bengal', 'Other'
        ],
        'plan_type': [
            'Full Talktime', 'Top-up', 'Special', 'Data', 'Combo',
            'ROM', 'STV', 'SMS', 'International', 'ISD'
        ],

        'dth_operator': [
        'Dish TV', 'Tata Sky', 'Airtel Digital TV', 'Sun Direct', 'Videocon d2h',
        'Reliance Digital TV', 'Independent TV', 'DD Free Dish'
        ],
        
        'cable_operator': [
            'Hathway', 'DEN Networks', 'Siti Cable', 'In Cable', 'GTPL',
            'Fastway', 'NXT Digital', 'Other Cable Operator'
        ],
        
        'bbps_type': [
            'Prepaid', 'Postpaid', 'Top-up', 'Special bbps', 'Data Pack',
            'Voice Pack', 'SMS Pack', 'International Roaming'
        ],
        
        'student_relation': [
            'Son', 'Daughter', 'Self', 'Ward', 'Brother', 'Sister', 'Other'
        ],
        
        'payment_option': [
            'Pay Full Amount', 'Pay Minimum Amount', 'Pay Other Amount'
        ],
        
        'traffic_authority': [
            'Delhi Traffic Police', 'Mumbai Traffic Police', 'Bangalore Traffic Police',
            'Chennai Traffic Police', 'Kolkata Traffic Police', 'Hyderabad Traffic Police',
            'Pune Traffic Police', 'Ahmedabad Traffic Police', 'State RTO'
        ],
        
        'corporation': [
            'Municipal Corporation of Delhi', 'Agartala Municipal Corporation',
            'Ajmer Municipal Corporation', 'Bicholim Municipal Council',
            'Canacona Municipal Council', 'Greater Mumbai Municipal Corporation',
            'Kolkata Municipal Corporation', 'Chennai Municipal Corporation',
            'Bangalore Municipal Corporation'
        ],
        
        'taxpayer_relation': [
            'Owner', 'Tenant', 'Legal Heir', 'Power of Attorney', 'Other'
        ],
        
        'vehicle_type': [
            'Car', 'Bike', 'Scooter', 'Motorcycle', 'SUV', 'Truck', 'Bus',
            'Auto Rickshaw', 'Commercial Vehicle', 'Other'
        ],
        
        'financial_year': [
            '2023-2024', '2024-2025', '2025-2026', '2026-2027', '2027-2028'
        ],
        
        'assessment_year': [
            '2024-2025', '2025-2026', '2026-2027', '2027-2028', '2028-2029'
        ],

        'plan_types': [
            'Data Plan', 'Voice Plan', 'Combo Plan', 'SMS Plan', 'International Plan',
            'Roaming Plan', 'Special Plan', 'Top-up', 'Full Talktime', 'STV',
            'ROM', '2G Plan', '3G Plan', '4G Plan', '5G Plan', 'Unlimited Plan'
        ],
        
        'plan_categories': [
            'Popular Plans', 'Data Packs', 'Voice Packs', 'Top-up Packs',
            'Special bbps', 'International Roaming', 'SMS Packs',
            'Seasonal Offers', 'Festival Offers'
        ],
        
        'plan_validity': [
            '1 Day', '7 Days', '15 Days', '28 Days', '30 Days', '45 Days', 
            '56 Days', '60 Days', '84 Days', '90 Days', '180 Days', '365 Days'
        ],

        'water_board': [
            'Delhi Jal Board',
            'Mumbai Municipal Corporation Water Department', 
            'Chennai Metro Water',
            'Bangalore Water Supply',
            'Hyderabad Metropolitan Water Supply',
            'Kolkata Municipal Corporation Water',
            'Pune Municipal Corporation Water',
            'Other Water Board'
        ],
        
        'broadband_name': [
            'Airtel Xstream Fiber',
            'JioFiber',
            'ACT Fibernet',
            'Hathway',
            'Spectra',
            'Excitel',
            'Tikona',
            'BSNL Fiber',
            'Other Broadband Provider'
        ],
        
        'corporation': [
            'Municipal Corporation of Delhi (MCD)',
            'Brihanmumbai Municipal Corporation (BMC)',
            'Chennai Municipal Corporation',
            'Kolkata Municipal Corporation',
            'Bangalore Municipal Corporation',
            'Hyderabad Municipal Corporation',
            'Pune Municipal Corporation',
            'Ahmedabad Municipal Corporation',
            'Other Municipal Corporation'
        ],
    }

    form = models.ForeignKey(ServiceForm, on_delete=models.CASCADE, related_name='fields')
    
    # Field Identification
    field_id = models.CharField(max_length=100, unique=True)
    field_name = models.CharField(max_length=100)
    field_label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=ServiceForm.FIELD_TYPES)
    
    # Field Properties
    required = models.BooleanField(default=False)
    readonly = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    
    # UI Properties
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.TextField(blank=True, null=True)
    css_class = models.CharField(max_length=100, blank=True, null=True)
    
    # Validation
    min_value = models.IntegerField(blank=True, null=True)
    max_value = models.IntegerField(blank=True, null=True)
    min_length = models.IntegerField(blank=True, null=True)
    max_length = models.IntegerField(blank=True, null=True)
    validation_regex = models.CharField(max_length=500, blank=True, null=True)
    error_message = models.CharField(max_length=200, blank=True, null=True)
    
    # Options for select fields
    options = models.JSONField(blank=True, null=True)
    use_service_options = models.CharField(max_length=50, blank=True, null=True)
    
    # Order and Grouping
    order = models.IntegerField(default=0)
    group = models.CharField(max_length=100, blank=True, null=True)
    
    # Conditional Logic
    depends_on = models.CharField(max_length=100, blank=True, null=True)
    condition_value = models.CharField(max_length=200, blank=True, null=True)
    condition_type = models.CharField(max_length=20, default='equals', choices=[
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
    ])
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = ['form', 'field_id']

    def save(self, *args, **kwargs):
        if not self.field_id:
            self.field_id = f"{self.form.id}_{self.field_name}_{uuid.uuid4().hex[:8]}"
        
        # Auto-populate options for service-specific fields
        if self.use_service_options and self.use_service_options in self.SERVICE_SPECIFIC_OPTIONS:
            self.options = self.SERVICE_SPECIFIC_OPTIONS[self.use_service_options]
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.form.name} - {self.field_label}"


class ServiceSubmission(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    # Submission Info
    submission_id = models.CharField(max_length=50, unique=True, blank=True)
    service_form = models.ForeignKey(ServiceForm, on_delete=models.CASCADE)
    service_subcategory = models.ForeignKey('ServiceSubCategory', on_delete=models.CASCADE)
    
    # User Information
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Form Data
    form_data = models.JSONField()  # Store all form field values
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Amount and Payment
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_gateway_response = models.JSONField(blank=True, null=True)
    
    # Service Response
    service_response = models.JSONField(blank=True, null=True)
    service_reference_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional Info
    notes = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submission_id']),
            models.Index(fields=['status']),
            models.Index(fields=['submitted_by', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.submission_id:
            self.submission_id = f"SUB{uuid.uuid4().hex[:12].upper()}"
        
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        
        # ✅ AUTO COMMISSION: When payment status changes to paid
        if self.pk:  # Only for existing instances
            old_instance = ServiceSubmission.objects.get(pk=self.pk)
            if (old_instance.payment_status != 'paid' and 
                self.payment_status == 'paid' and 
                self.amount > 0):
                
                # Trigger commission processing
                from commission.utils import auto_process_commission
                auto_process_commission(self)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.submission_id} - {self.service_form.name}"


class FormSubmissionFile(models.Model):
    submission = models.ForeignKey(ServiceSubmission, on_delete=models.CASCADE, related_name='files')
    field_name = models.CharField(max_length=100)
    file = models.FileField(upload_to='service_submissions/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.submission.submission_id} - {self.field_name}"
    

class RoleServicePermission(models.Model):
    """Role-wise service permissions"""
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES)
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, null=True, blank=True)
    service_subcategory = models.ForeignKey(ServiceSubCategory, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_view = models.BooleanField(default=True)
    can_use = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ['role', 'service_category'],
            ['role', 'service_subcategory']
        ]
        verbose_name_plural = "Role Service Permissions"
    
    def __str__(self):
        if self.service_category:
            return f"{self.role} - {self.service_category.name}"
        elif self.service_subcategory:
            return f"{self.role} - {self.service_subcategory.name}"
        return f"{self.role} - Permission"

class UserServicePermission(models.Model):
    """User-wise service permissions (overrides role permissions)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, null=True, blank=True)
    service_subcategory = models.ForeignKey(ServiceSubCategory, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_view = models.BooleanField(default=True)
    can_use = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_user_permissions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ['user', 'service_category'],
            ['user', 'service_subcategory']
        ]
        verbose_name_plural = "User Service Permissions"
    
    def __str__(self):
        if self.service_category:
            return f"{self.user.username} - {self.service_category.name}"
        elif self.service_subcategory:
            return f"{self.user.username} - {self.service_subcategory.name}"
        return f"{self.user.username} - Permission"