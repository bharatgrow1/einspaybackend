from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.db import transaction
import uuid
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import BasePermission

from rest_framework.permissions import IsAuthenticated
from bbps.models import Operator

from services.models import (UploadImage, ServiceCategory, ServiceSubCategory, 
                             ServiceForm, FormField, ServiceSubmission, FormSubmissionFile)
from services.serializers import (DirectServiceFormSerializer, ServiceFormWithFieldsSerializer, 
        ServiceCategoryWithFormsSerializer, ServiceFormSerializer, ServiceSubmissionSerializer, 
        DynamicFormSubmissionSerializer, UploadImageSerializer, ServiceFormWithFieldsSerializer, 
        ServiceSubmissionSerializer)

from commission.views import (ServiceCategorySerializer, ServiceSubCategorySerializer, ServiceSubCategorySerializer)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        return ServiceCategory.objects.all().order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)



class DirectServiceFormViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceForm.objects.filter(service_subcategory__isnull=True)
    serializer_class = DirectServiceFormSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_category_form_config(request, category_id):
    """Get form configuration based on category boolean fields"""
    try:
        category = ServiceCategory.objects.get(id=category_id)
        
        config = {
            'name': category.name,
            'description': category.description,
            'allow_direct_service': category.allow_direct_service,
            'fields': category.get_required_fields()
        }
        
        return Response(config)
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def copy_category_fields_to_subcategory(request):
    """Copy all boolean fields from category to subcategory"""
    category_id = request.data.get('category_id')
    subcategory_id = request.data.get('subcategory_id')
    
    if not category_id or not subcategory_id:
        return Response({'error': 'category_id and subcategory_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        category = ServiceCategory.objects.get(id=category_id)
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        category.copy_boolean_fields_to_subcategory(subcategory)
        
        serializer = ServiceSubCategorySerializer(subcategory)
        return Response({
            'message': 'Boolean fields copied successfully',
            'subcategory': serializer.data
        })
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_direct_category_form(request):
    """Create form directly for service category using its boolean fields"""
    category_id = request.data.get('category_id')
    form_name = request.data.get('name')
    form_description = request.data.get('description', '')
    
    if not category_id or not form_name:
        return Response({'error': 'category_id and name are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        category = ServiceCategory.objects.get(id=category_id)
        
        if not category.allow_direct_service:
            return Response({'error': 'This category does not allow direct services'}, status=status.HTTP_400_BAD_REQUEST)
        
        service_form = ServiceForm.objects.create(
            service_type='direct_category',
            service_category=category,
            service_subcategory=None,
            name=form_name,
            description=form_description,
            created_by=request.user
        )
        
        required_fields = category.get_required_fields()
        for index, field_config in enumerate(required_fields):
            FormField.objects.create(
                form=service_form,
                field_id=f"category_{category.id}_{field_config['field_name']}_{uuid.uuid4().hex[:8]}",
                field_name=field_config['field_name'],
                field_label=field_config['field_label'],
                field_type=field_config['field_type'],
                required=field_config.get('required', True),
                order=index,
                is_active=True
            )
        
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except ServiceCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories_with_direct_services(request):
    """Get all categories that allow direct services"""
    categories = ServiceCategory.objects.filter(allow_direct_service=True, is_active=True)
    serializer = ServiceCategoryWithFormsSerializer(categories, many=True)
    return Response(serializer.data)



class ServiceSubCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer

    def get_queryset(self):
        queryset = ServiceSubCategory.objects.all().order_by('created_at')
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response({'error': 'category_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        subcategories = ServiceSubCategory.objects.filter(category_id=category_id)
        serializer = self.get_serializer(subcategories, many=True)
        return Response(serializer.data)


class ServiceFormViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceForm.objects.all()
    serializer_class = ServiceFormSerializer

    def get_queryset(self):
        queryset = ServiceForm.objects.all()
        service_type = self.request.query_params.get('service_type')
        subcategory_id = self.request.query_params.get('subcategory_id')
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        if subcategory_id:
            queryset = queryset.filter(service_subcategory_id=subcategory_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def form_config(self, request, pk=None):
        service_form = self.get_object()
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_service_type(self, request):
        service_type = request.query_params.get('service_type')
        if not service_type:
            return Response({'error': 'service_type parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        forms = self.get_queryset().filter(service_type=service_type)
        serializer = self.get_serializer(forms, many=True)
        return Response(serializer.data)


class ServiceSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = ServiceSubmission.objects.all()
    serializer_class = ServiceSubmissionSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = ServiceSubmission.objects.all()
        form_id = self.request.query_params.get('form_id')
        service_type = self.request.query_params.get('service_type')
        if form_id:
            queryset = queryset.filter(service_form_id=form_id)
        if service_type:
            queryset = queryset.filter(service_form__service_type=service_type)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        form_id = request.data.get('service_form')
        service_form = get_object_or_404(ServiceForm, id=form_id)

        # Get form fields
        form_fields = service_form.fields.all().order_by('order')
        form_data = {}
        files_to_save = {}

        for field in form_fields:
            if field.field_name in request.data:
                form_data[field.field_name] = request.data[field.field_name]
            elif field.field_name in request.FILES:
                files_to_save[field.field_name] = request.FILES[field.field_name]

        dynamic_serializer = DynamicFormSubmissionSerializer(data=form_data, form_fields=form_fields)
        if not dynamic_serializer.is_valid():
            return Response({'errors': dynamic_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        submission_data = {
            'service_form': service_form.id,
            'service_subcategory': service_form.service_subcategory.id,
            'form_data': dynamic_serializer.validated_data,
            'status': 'submitted',
            'amount': request.data.get('amount', 0),
            'customer_name': request.data.get('customer_name'),
            'customer_email': request.data.get('customer_email'),
            'customer_phone': request.data.get('customer_phone'),
            'notes': request.data.get('notes')
        }

        if request.user.is_authenticated:
            submission_data['submitted_by'] = request.user.id

        serializer = self.get_serializer(data=submission_data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()

        for field_name, file_obj in files_to_save.items():
            FormSubmissionFile.objects.create(
                submission=submission,
                field_name=field_name,
                file=file_obj,
                original_filename=file_obj.name,
                file_size=file_obj.size
            )

        if submission.status == 'submitted' and submission.amount > 0:
            try:
                from commission.views import CommissionManager
                from users.models import Transaction
                
                main_transaction = Transaction.objects.filter(
                    service_submission=submission,
                    status='success'
                ).first()
                
                if main_transaction:
                    success, message = CommissionManager.process_service_commission(
                        submission, main_transaction
                    )
                    if not success:
                        print(f"Commission processing failed: {message}")
                else:
                    print(f"No successful transaction found for submission {submission.id}")
                    
            except ImportError:
                print("Commission app not available")
            except Exception as e:
                print(f"Error in commission processing: {str(e)}")

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        submission = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(ServiceSubmission.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        submission.status = new_status
        submission.save()
        
        if new_status == 'success' and submission.amount > 0:
            try:
                from commission.views import CommissionManager
                from users.models import Transaction
                
                main_transaction = Transaction.objects.filter(
                    service_submission=submission,
                    status='success'
                ).first()
                
                if main_transaction:
                    success, message = CommissionManager.process_service_commission(
                        submission, main_transaction
                    )
                    if not success:
                        print(f"Commission processing failed: {message}")
                else:
                    print(f"No transaction found for successful submission {submission.id}")
                    
            except Exception as e:
                print(f"Error in commission processing: {str(e)}")
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for service submission and trigger commission distribution"""
        submission = self.get_object()
        payment_amount = request.data.get('amount', submission.amount)
        pin = request.data.get('pin')
        
        if not pin:
            return Response({'error': 'Wallet PIN is required'}, status=400)
        
        try:
            wallet = request.user.wallet
            
            if not wallet.verify_pin(pin):
                return Response({'error': 'Invalid PIN'}, status=400)
            
            total_deducted = wallet.deduct_amount(payment_amount, 0, pin)
            
            # ✅ Create transaction record
            transaction_obj = Transaction.objects.create(
                wallet=wallet,
                amount=payment_amount,
                transaction_type='debit',
                transaction_category='service_payment',
                description=f"Payment for {submission.service_form.name}",
                created_by=request.user,
                service_submission=submission,
                status='success'
            )
            
            # ✅ Update submission status
            submission.payment_status = 'paid'
            submission.transaction_id = transaction_obj.reference_number
            submission.status = 'success'
            submission.amount = payment_amount
            submission.save()
            
            # ✅ CRITICAL FIX: Force commission processing
            print(f"🔄 Starting commission processing for submission {submission.id}")
            
            from commission.views import CommissionManager
            success, message = CommissionManager.process_service_commission(
                submission, transaction_obj
            )
            
            print(f"🔄 Commission processing result: {success} - {message}")
            
            # ✅ Get commission details to verify
            commission_transactions = []
            wallet_updates = []
            
            if success:
                from commission.models import CommissionTransaction
                commission_transactions = CommissionTransaction.objects.filter(
                    service_submission=submission
                )
                
                # Check wallet balances
                for ct in commission_transactions:
                    user_wallet = ct.user.wallet
                    wallet_updates.append({
                        'user': ct.user.username,
                        'role': ct.role,
                        'commission_amount': ct.commission_amount,
                        'wallet_balance': user_wallet.balance,
                        'commission_added': True
                    })
            
            return Response({
                'message': 'Payment successful',
                'commission_processed': success,
                'commission_message': message,
                'commission_details': CommissionTransactionSerializer(commission_transactions, many=True).data if success else [],
                'wallet_updates': wallet_updates,
                'transaction_reference': transaction_obj.reference_number,
                'total_deducted': total_deducted,
                'new_balance': wallet.balance
            })
            
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
    

class ServiceImageViewSet(viewsets.ModelViewSet):
    queryset = UploadImage.objects.all()
    serializer_class = UploadImageSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_subcategory_form_config(request, subcategory_id):
    """Get form configuration based on boolean fields"""
    try:
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        config = {
            'name': subcategory.name,
            'description': subcategory.description,
            'fields': subcategory.get_required_fields()
        }
        
        return Response(config)
        
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_form_from_boolean_fields(request):
    """Create form based on boolean field configuration"""
    subcategory_id = request.data.get('subcategory_id')
    
    if not subcategory_id:
        return Response({'error': 'subcategory_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        service_form = ServiceForm.objects.create(
            service_type='custom',
            service_subcategory=subcategory,
            name=subcategory.name,
            description=subcategory.description or f"Form for {subcategory.name}",
            created_by=request.user
        )
        
        required_fields = subcategory.get_required_fields()
        for field_config in required_fields:
            FormField.objects.create(
                form=service_form,
                field_id=f"{subcategory.id}_{field_config['field_name']}",
                field_name=field_config['field_name'],
                field_label=field_config['field_label'],
                field_type=field_config['field_type'],
                required=field_config.get('required', True),
                order=len(required_fields) - required_fields.index(field_config),
                is_active=True
            )
        
        serializer = ServiceFormWithFieldsSerializer(service_form)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def create_service_submission_direct(request):
    """Create service submission directly without needing ServiceForm"""
    try:
        subcategory_id = request.data.get('service_subcategory')
        
        if not subcategory_id:
            return Response({'error': 'service_subcategory is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        form_data = {}
        for key, value in request.data.items():
            if key not in ['service_subcategory', 'customer_name', 'customer_email', 
                          'customer_phone', 'amount', 'notes', 'status']:
                form_data[key] = value
        
        service_form = ServiceForm.objects.create(
            service_type='direct_submission',
            service_subcategory=subcategory,
            name=f"Direct Form - {subcategory.name}",
            description=f"Auto-generated form for {subcategory.name}",
            created_by=request.user if request.user.is_authenticated else None
        )
        
        submission_data = {
            'service_form': service_form.id,
            'service_subcategory': subcategory.id,
            'form_data': form_data,
            'status': 'submitted',
            'amount': request.data.get('amount', 0),
            'customer_name': request.data.get('customer_name', ''),
            'customer_email': request.data.get('customer_email', ''),
            'customer_phone': request.data.get('customer_phone', ''),
            'notes': request.data.get('notes', ''),
        }
        
        serializer = ServiceSubmissionSerializer(data=submission_data)
        if serializer.is_valid():
            submission = serializer.save(submitted_by=request.user if request.user.is_authenticated else None)
            
            if submission.amount > 0:
                try:
                    from commission.views import CommissionManager
                    from users.models import Transaction
                    
                    main_transaction = Transaction.objects.filter(
                        service_submission=submission,
                        status='success'
                    ).first()
                    
                    if main_transaction:
                        success, message = CommissionManager.process_service_commission(
                            submission, main_transaction
                        )
                        print(f"Commission processing: {success} - {message}")
                except Exception as e:
                    print(f"Commission processing error: {e}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            service_form.delete()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except ServiceSubCategory.DoesNotExist:
        return Response({'error': 'Subcategory not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([AllowAny])
def fetch_bill_details(request):
    """
    Fetch bill details based on consumer number or other identifiers
    """
    consumer_number = request.data.get('consumer_number')
    service_type = request.data.get('service_type')
    
    if not consumer_number:
        return JsonResponse({'error': 'Consumer number is required'}, status=400)
    
    # Static bill data for testing - Replace with actual API integration
    static_bills = {
        '1234567890': {
            'consumer_name': 'Rajesh Kumar',
            'consumer_number': '1234567890',
            'bill_amount': 1250.00,
            'due_date': '2024-12-25',
            'billing_period': 'Nov 2024',
            'service_provider': 'BSES Yamuna',
            'state': 'Delhi',
            'city': 'Delhi',
            'outstanding_amount': 1250.00,
            'late_fee': 0.00,
            'tax_amount': 150.00,
            'base_amount': 1100.00
        },
        '9876543210': {
            'consumer_name': 'Priya Sharma',
            'consumer_number': '9876543210',
            'bill_amount': 1850.50,
            'due_date': '2024-12-28',
            'billing_period': 'Nov 2024',
            'service_provider': 'Tata Power',
            'state': 'Maharashtra',
            'city': 'Mumbai',
            'outstanding_amount': 1850.50,
            'late_fee': 50.00,
            'tax_amount': 200.50,
            'base_amount': 1600.00
        }
    }
    
    bill_data = static_bills.get(consumer_number)
    
    if not bill_data:
        return JsonResponse({
            'error': f'No bill found for consumer number: {consumer_number}',
            'suggestions': ['Check consumer number', 'Ensure service is active']
        }, status=404)
    
    return JsonResponse({
        'success': True,
        'bill_details': bill_data
    })



# services/views.py
@api_view(['POST'])
@permission_classes([AllowAny])
def process_service_payment(request):
    """
    Process payment for service with commission distribution
    """
    try:
        submission_id = request.data.get('submission_id')
        payment_method = request.data.get('payment_method', 'wallet')
        pin = request.data.get('pin')
        card_details = request.data.get('card_details', {})
        
        if not submission_id:
            return Response({'error': 'Submission ID is required'}, status=400)
        
        submission = ServiceSubmission.objects.get(id=submission_id)
        
        if payment_method == 'wallet':
            if not pin:
                return Response({'error': 'Wallet PIN is required'}, status=400)
            
            # Process wallet payment
            wallet = request.user.wallet
            
            if not wallet.verify_pin(pin):
                return Response({'error': 'Invalid PIN'}, status=400)
            
            total_amount = submission.amount
            total_deducted = wallet.deduct_amount(total_amount, 0, pin)
            
            # Create transaction record
            transaction_obj = Transaction.objects.create(
                wallet=wallet,
                amount=total_amount,
                transaction_type='debit',
                transaction_category='service_payment',
                description=f"Payment for {submission.service_form.name}",
                created_by=request.user,
                service_submission=submission,
                status='success'
            )
            
        elif payment_method == 'card':
            # Process card payment (simulated)
            # In production, integrate with payment gateway
            card_number = card_details.get('card_number')
            expiry = card_details.get('expiry')
            cvv = card_details.get('cvv')
            
            if not all([card_number, expiry, cvv]):
                return Response({'error': 'Card details incomplete'}, status=400)
            
            # Simulate successful card payment
            transaction_obj = Transaction.objects.create(
                wallet=request.user.wallet,
                amount=submission.amount,
                transaction_type='debit',
                transaction_category='service_payment',
                description=f"Card Payment for {submission.service_form.name}",
                created_by=request.user,
                service_submission=submission,
                status='success',
                payment_method='card'
            )
        
        # Update submission status
        submission.payment_status = 'paid'
        submission.transaction_id = transaction_obj.reference_number
        submission.status = 'success'
        submission.save()
        
        # Process commission
        commission_result = handle_commission_processing(submission, transaction_obj)
        
        return Response({
            'success': True,
            'message': 'Payment successful',
            'transaction_id': transaction_obj.reference_number,
            'submission_id': submission.id,
            'amount': submission.amount,
            'commission_processed': commission_result.get('success', False),
            'commission_message': commission_result.get('message', '')
        })
        
    except ServiceSubmission.DoesNotExist:
        return Response({'error': 'Submission not found'}, status=404)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': f'Payment failed: {str(e)}'}, status=500)

def handle_commission_processing(submission, transaction):
    """
    Handle commission distribution for service payment
    """
    try:
        from commission.views import CommissionManager
        success, message = CommissionManager.process_service_commission(
            submission, transaction
        )
        
        return {
            'success': success,
            'message': message
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Commission processing error: {str(e)}'
        }
    


@api_view(['POST'])
@permission_classes([AllowAny])
def fetch_bill_details_enhanced(request):
    """
    Enhanced bill fetching for all service types
    """
    identifier = request.data.get('identifier')
    service_type = request.data.get('service_type')
    subcategory_id = request.data.get('subcategory_id')
    
    if not identifier:
        return Response({'error': 'Identifier is required'}, status=400)
    
    # Static bill data for all service types
    static_bills = {
        # Electricity Bills
        '1234567890': {
            'service_type': 'electricity bill',
            'consumer_name': 'Rajesh Kumar',
            'consumer_number': '1234567890',
            'bill_amount': 1250.00,
            'due_date': '2024-12-25',
            'billing_period': 'Nov 2024',
            'service_provider': 'BSES Yamuna',
            'outstanding_amount': 1250.00,
            'late_fee': 0.00,
            'tax_amount': 150.00,
            'base_amount': 1100.00
        },
       
        # Water Bills
        'WB123456': {
            'service_type': 'water',
            'consumer_name': 'Amit Singh',
            'consumer_number': 'WB123456',
            'bill_amount': 850.00,
            'due_date': '2024-12-20',
            'billing_period': 'Nov 2024',
            'service_provider': 'Delhi Jal Board',
            'outstanding_amount': 850.00,
            'late_fee': 25.00,
            'usage_charge': 700.00,
            'sewage_charge': 150.00
        },
        
        # Broadband Bills
        'BB789012': {
            'service_type': 'broadband',
            'account_number': 'BB789012',
            'customer_name': 'Neha Gupta',
            'bill_amount': 899.00,
            'due_date': '2024-12-15',
            'billing_period': 'Nov 2024',
            'service_provider': 'Airtel Xstream',
            'plan_name': '100 Mbps Unlimited',
            'gst_amount': 162.00,
            'base_plan_amount': 737.00
        },
        
        # Loan EMI 
        'LN551237': {
            'service_type': 'loan_emi',
            'loan_account': 'LN551237',
            'customer_name': 'Rohit Verma',
            'emi_amount': 15250.00,
            'due_date': '2024-12-05',
            'principal_amount': 12500.00,
            'interest_amount': 2750.00,
            'outstanding_principal': 485000.00,
            'bank_name': 'HDFC Bank'
        },
        
        # Fastag bbps
        'DL01AB1234': {
            'service_type': 'fastag',
            'vehicle_number': 'DL01AB1234',
            'vehicle_type': 'Car',
            'current_balance': 125.50,
            'bbps_amount': 500.00,
            'customer_name': 'Sanjay Mehta',
            'fastag_provider': 'ICICI Bank'
        },
        
        # Credit Card Bill
        '4123456789012345': {
            'service_type': 'credit_card',
            'card_number': '4123456789012345',
            'customer_name': 'Anjali Patel',
            'total_amount': 25480.00,
            'due_date': '2024-12-10',
            'minimum_amount': 2548.00,
            'credit_limit': 100000.00,
            'available_limit': 74520.00,
            'bank_name': 'SBI Card'
        },
        
        # Society Maintenance
        'A504': {
            'service_type': 'society_maintenance',
            'flat_number': 'A504',
            'customer_name': 'Kiran Desai',
            'maintenance_amount': 3500.00,
            'due_date': '2024-12-03',
            'society_name': 'Shanti Apartments',
            'water_charges': 500.00,
            'electricity_common': 800.00,
            'sinking_fund': 300.00,
            'other_charges': 1900.00
        },
        
        # Traffic Challan
        'CH12345678': {
            'service_type': 'traffic_challan',
            'challan_number': 'CH12345678',
            'vehicle_number': 'DL02CD5678',
            'violation_date': '2024-11-15',
            'violation_type': 'Signal Jumping',
            'challan_amount': 500.00,
            'late_fee': 100.00,
            'total_amount': 600.00,
            'traffic_authority': 'Delhi Traffic Police'
        },
        
        # Education Fee
        'STU2024001': {
            'service_type': 'education_fee',
            'student_id': 'STU2024001',
            'student_name': 'Rahul Sharma',
            'total_fee': 25000.00,
            'due_date': '2024-12-20',
            'tuition_fee': 18000.00,
            'examination_fee': 2000.00,
            'library_fee': 1000.00,
            'other_charges': 4000.00,
            'institute_name': 'Delhi Public School'
        },
        
        # Mobile bbps
        '9876543210': {
            'service_type': 'mobile',
            'mobile_number': '9876543210',
            'operator': 'Jio',
            'current_balance': 15.50,
            'validity': '2024-11-30',
            'plan_type': 'Prepaid'
        },
        
        # DTH bbps
        'DTH123456789': {
            'service_type': 'dth',
            'subscriber_id': 'DTH123456789',
            'customer_name': 'Vikram Joshi',
            'due_amount': 349.00,
            'due_date': '2024-12-25',
            'plan_name': 'South Family Pack',
            'operator': 'Tata Play'
        }
    }
    
    # Find bill data by identifier
    bill_data = None
    for key, data in static_bills.items():
        if key == identifier:
            bill_data = data
            break
    
    if not bill_data:
        return Response({
            'error': f'No bill found for identifier: {identifier}',
            'suggestions': [
                'Check the identifier number',
                'Ensure the service is active',
                'Contact customer support if issue persists'
            ]
        }, status=404)
    
    return Response({
        'success': True,
        'bill_details': bill_data,
        'service_type': service_type
    })


class CanManageServicePermissions(BasePermission):
    """Check if user can manage service permissions"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superadmin, admin, master can manage all permissions
        if request.user.role in ['superadmin', 'admin', 'master']:
            return True
        
        # Dealers can manage permissions for their retailers only
        if request.user.role == 'dealer':
            if view.action in ['user_permissions', 'update_user_permission', 'bulk_user_permissions']:
                return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.role in ['superadmin', 'admin', 'master']:
            return True
        
        # Dealers can only manage their retailers
        if user.role == 'dealer':
            if hasattr(obj, 'user'):
                return obj.user.created_by == user
            elif hasattr(obj, 'created_by'):
                return obj.created_by == user
        
        return False
    



# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def available_services_detailed(request):
#     """Get available services with detailed permissions - FIXED VERSION"""
#     user = request.user
    
#     try:
#         # Get available categories and subcategories using ServiceManager
#         available_categories = ServiceCategory.objects.get_available_categories(user)
#         available_subcategories = ServiceCategory.objects.get_available_subcategories(user)
        
#         # Get user and role permissions
#         user_permissions = UserServicePermission.objects.filter(user=user, is_active=True)
#         role_permissions = RoleServicePermission.objects.filter(role=user.role, is_active=True)
        
#         # Serialize data
#         category_serializer = ServiceCategorySerializer(available_categories, many=True)
#         subcategory_serializer = ServiceSubCategorySerializer(available_subcategories, many=True)
#         user_permission_serializer = UserServicePermissionSerializer(user_permissions, many=True)
#         role_permission_serializer = RoleServicePermissionSerializer(role_permissions, many=True)
        
#         response_data = {
#             'categories': category_serializer.data,
#             'subcategories': subcategory_serializer.data,
#             'permissions': {
#                 'user_permissions': user_permission_serializer.data,
#                 'role_permissions': role_permission_serializer.data
#             }
#         }
        
#         return Response(response_data)
        
#     except Exception as e:
#         logger.error(f"Error in available_services_detailed: {str(e)}")
#         return Response(
#             {'error': 'Failed to fetch services'}, 
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_operators_for_subcategory(request, subcategory_id):
    """Get operators for specific service subcategory"""
    try:
        from services.models import ServiceSubCategory
        
        subcategory = ServiceSubCategory.objects.get(id=subcategory_id)
        
        # Service name से operator type mapping
        service_to_operator_map = {
            'mobile_bbps': 'prepaid',
            'mobile prepaid': 'prepaid',
            'mobile postpaid': 'postpaid',
            'dth': 'dth',
            'dth bbps': 'dth',
            'electricity': 'electricity',
            'electricity bill': 'electricity',
            'water': 'water',
            'water bill': 'water',
            'gas': 'gas',
            'gas bill': 'gas',
            'broadband': 'broadband',
            'broadband bill': 'broadband',
            'landline': 'landline',
            'fastag': 'fastag',
            'credit card': 'credit',
            'insurance': 'insurance',
            'loan': 'loan',
            'education': 'education',
            'municipal tax': 'municipal_tax',
            'society maintenance': 'society',
            'traffic challan': 'tax',
            'cable tv': 'cable',
            'lpg': 'lpg',
            'hospital': 'hospital',
            'ott': 'ott',
        }
        
        # Subcategory name के आधार पर operator type identify करें
        subcategory_name_lower = subcategory.name.lower()
        operator_type = None
        
        for keyword, op_type in service_to_operator_map.items():
            if keyword in subcategory_name_lower:
                operator_type = op_type
                break
        
        if operator_type:
            # Specific operator type के operators fetch करें
            operators = Operator.objects.filter(
                operator_type=operator_type,
                is_active=True
            ).order_by('operator_name')
        else:
            # Default: सभी operators fetch करें
            operators = Operator.objects.filter(
                is_active=True
            ).order_by('operator_name')
        
        # Serialize operators
        from bbps.serializers import OperatorSerializer
        serializer = OperatorSerializer(operators, many=True)
        
        return Response({
            'subcategory': {
                'id': subcategory.id,
                'name': subcategory.name,
                'category_name': subcategory.category.name if subcategory.category else ''
            },
            'operator_type_filter': operator_type,
            'operators': serializer.data,
            'count': operators.count()
        })
        
    except ServiceSubCategory.DoesNotExist:
        return Response(
            {'error': 'Subcategory not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )