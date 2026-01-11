from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction
from django.utils import timezone
from users.models import Transaction
from decimal import Decimal
import logging
from vendorpayment.models import VendorPayment 
from vendorpayment.serializers import VendorPaymentSerializer, VendorPaymentResponseSerializer
from vendorpayment.services.vendor_manager import vendor_manager
from .services.receipt_generator import VendorReceiptGenerator
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from users.models import User
from datetime import timedelta


logger = logging.getLogger(__name__)

class VendorPaymentViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"])
    @db_transaction.atomic
    def pay(self, request):
        serializer = VendorPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        data = serializer.validated_data
        
        pin = request.data.get('pin')
        if not pin:
            return Response({
                'status': 1,
                'message': 'Wallet PIN is required'
            })
        
        try:
            wallet = user.wallet
            
            if not wallet.verify_pin(pin):
                return Response({
                    'status': 1,
                    'message': 'Invalid wallet PIN'
                })
            
            amount = Decimal(str(data['amount']))
            fee = Decimal('42.59')
            gst = Decimal('7.67')
            total_fee = fee + gst
            total_deduction = amount + total_fee
            
            logger.info(f"   Payment Calculation:")
            logger.info(f"   Transfer Amount: ₹{amount}")
            logger.info(f"   Processing Fee: ₹{fee}")
            logger.info(f"   GST: ₹{gst}")
            logger.info(f"   Total Fee: ₹{total_fee}")
            logger.info(f"   Total Deduction: ₹{total_deduction}")
            logger.info(f"   Wallet Balance: ₹{wallet.balance}")
            
            if wallet.balance < total_deduction:
                return Response({
                    'status': 1,
                    'message': f'Insufficient wallet balance. Required: ₹{total_deduction} (₹{amount} transfer + ₹{total_fee} fees), Available: ₹{wallet.balance}'
                })
            
            vendor_payment = VendorPayment.objects.create(
                user=user,
                recipient_name=data['recipient_name'],
                recipient_account=data['account'],
                recipient_ifsc=data['ifsc'],
                amount=amount,
                processing_fee=fee,
                gst=gst,
                total_fee=total_fee,
                total_deduction=total_deduction,
                purpose=data.get('purpose', 'Vendor Payment'),
                remarks=data.get('remarks', ''),
                payment_mode=data['payment_mode'],
                status='initiated'
            )
            
            wallet.deduct_amount(amount, total_fee, pin)
            
            Transaction.objects.create(
                wallet=wallet,
                service_charge=total_fee,
                amount=amount,
                net_amount=amount,
                transaction_type='debit',
                transaction_category='vendor_payment',
                description=f"Vendor payment to {data['recipient_name']} - Account: {data['account'][-4:]}",
                created_by=user,
                status='success',
                metadata={
                    'vendor_payment_id': vendor_payment.id,
                    'recipient_name': data['recipient_name'],
                    'recipient_account': data['account'][-4:],
                    'ifsc': data['ifsc'],
                    'transfer_amount': str(amount),
                    'processing_fee': str(fee),
                    'gst': str(gst), 
                    'total_fee': str(total_fee),
                    'total_deduction': str(total_deduction)
                }
            )
            
            logger.info(f"✅ Wallet deduction successful: ₹{total_deduction} deducted from wallet")
            logger.info(f"✅ New wallet balance: ₹{wallet.balance}")
            
        except Exception as e:
            logger.error(f"❌ Wallet deduction failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return Response({
                'status': 1,
                'message': f'Payment failed: {str(e)}'
            })
        
        try:
            eko_data = data.copy()
            eko_data['amount'] = str(amount)
            
            logger.info(f"📤 Sending to EKO: Transfer Amount = ₹{amount}")
            eko_result = vendor_manager.initiate_payment(eko_data, vendor_payment.id)
            
            logger.info(f"✅ EKO vendor payment response: {eko_result}")
            
            eko_status = eko_result.get('status', 1)
            eko_message = eko_result.get('message', '')
            eko_data_response = eko_result.get('data', {})
            
            vendor_payment.refresh_from_db()
            eko_data = eko_result.get("data", {})

            vendor_payment.eko_tid = eko_data.get("tid")
            vendor_payment.client_ref_id = eko_data.get("client_ref_id", vendor_payment.client_ref_id)
            vendor_payment.bank_ref_num = eko_data.get("bank_ref_num")
            vendor_payment.utr_number = eko_data.get("utr")
            vendor_payment.transaction_reference = eko_data.get("tracking_number")
            vendor_payment.timestamp = eko_data.get("timestamp")
            vendor_payment.status_message = eko_data.get("txstatus_desc")

            # Status update from EKO
            tx_desc = (
                eko_data.get("txstatus_desc") or
                eko_data.get("tx_status")
            )

            tx_desc = str(tx_desc).upper()

            if tx_desc in ["INITIATED", "SUCCESS", "SUCCESSFUL", "2"]:
                vendor_payment.status = "success"
            elif tx_desc in ["FAILED", "FAILURE", "1"]:
                vendor_payment.status = "failed"
            else:
                vendor_payment.status = "processing"


            vendor_payment.save()

            try:
                wallet_transaction = Transaction.objects.filter(
                    wallet=wallet,
                    description__contains=f"Vendor payment to {data['recipient_name']}",
                    created_at__gte=timezone.now() - timedelta(minutes=5)
                ).order_by('-created_at').first()
                
                if wallet_transaction and eko_data.get('tid'):
                    wallet_transaction.eko_tid = eko_data['tid']
                    wallet_transaction.eko_client_ref_id = eko_data.get('client_ref_id')
                    wallet_transaction.save()
                    logger.info(f" Vendor EKO TID saved: {eko_data['tid']}")
            except Exception as e:
                logger.error(f" Failed to save vendor EKO TID: {str(e)}")

            
            if vendor_payment.status == "failed":
                vendor_payment.status = 'failed'
                vendor_payment.status_message = eko_message
                vendor_payment.save()
                
                wallet.add_amount(total_deduction) 
                Transaction.objects.create(
                    wallet=wallet,
                    amount=total_deduction, 
                    transaction_type='credit',
                    transaction_category='refund',
                    description=f"Refund for failed vendor payment to {data['recipient_name']}",
                    created_by=user,
                    status='success',
                    metadata={'vendor_payment_id': vendor_payment.id}
                )
                
                return Response({
                    'status': 1,
                    'message': f'Vendor payment failed: {eko_message}. ₹{total_deduction} refunded to wallet.',
                    'payment_id': vendor_payment.id
                })
            
            if not vendor_payment.receipt_number:
                vendor_payment.receipt_number = f"VP{vendor_payment.id:08d}"
                vendor_payment.save(update_fields=['receipt_number'])
            
            response_data = {
                'status': 0,
                'message': 'Vendor payment initiated successfully',
                'payment_id': vendor_payment.id,
                'receipt_number': vendor_payment.receipt_number,
                'data': {
                    'transfer_amount': str(amount),
                    'fee': str(fee),
                    'gst': str(gst),
                    'total_fee': str(total_fee),
                    'total_deduction': str(total_deduction),
                    'balance': str(wallet.balance),
                    'recipient_name': data['recipient_name'],
                    'account': data['account'][-4:],
                    'ifsc': data['ifsc'],
                    'bank_ref_num': eko_data_response.get('bank_ref_num', ''),
                    'status': eko_data_response.get('txstatus_desc', 'Initiated'),
                    'transaction_id': eko_data_response.get('tid', ''),
                    'timestamp': eko_data_response.get('timestamp', ''),
                    'purpose': data.get('purpose', 'Vendor Payment'),
                    'payment_mode': data['payment_mode']
                }
            }
            
            logger.info(f"✅ Final response: {response_data}")
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"❌ EKO payment failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            vendor_payment.status = 'failed'
            vendor_payment.status_message = str(e)
            vendor_payment.save()
            
            wallet.add_amount(total_deduction)
            Transaction.objects.create(
                wallet=wallet,
                amount=total_deduction,
                transaction_type='credit',
                transaction_category='refund',
                description=f"Refund for failed vendor payment (EKO error) to {data['recipient_name']}",
                created_by=user,
                status='success',
                metadata={'vendor_payment_id': vendor_payment.id}
            )
            
            return Response({
                'status': 1,
                'message': f'Vendor payment failed: {str(e)}. ₹{total_deduction} refunded.',
                'payment_id': vendor_payment.id
            })
        


    @staticmethod
    def get_all_child_users(user):
        role = user.role

        if role == "superadmin":
            return User.objects.all()

        if role == "admin":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(created_by__created_by__created_by=user) |
                Q(id=user.id)
            )

        if role == "master":
            return User.objects.filter(
                Q(created_by=user) |
                Q(created_by__created_by=user) |
                Q(id=user.id)
            )

        if role == "dealer":
            return User.objects.filter(
                Q(created_by=user) |
                Q(id=user.id)
            )

        return User.objects.filter(id=user.id)
        
    
    @action(detail=False, methods=["get"])
    def history(self, request):

        allowed_users = self.get_all_child_users(request.user)

        queryset = VendorPayment.objects.filter(
            user__in=allowed_users
        ).order_by('-created_at')

        # ----- filters remain same -----
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        min_amount = request.GET.get('min_amount')
        max_amount = request.GET.get('max_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)

        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(recipient_name__icontains=search) |
                Q(recipient_account__icontains=search) |
                Q(recipient_ifsc__icontains=search) |
                Q(receipt_number__icontains=search)
            )

        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_qs = paginator.paginate_queryset(queryset, request)

        serializer = VendorPaymentResponseSerializer(paginated_qs, many=True)
        return paginator.get_paginated_response(serializer.data)

        

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_vendor_receipt(request, payment_id):
    """
    Download vendor payment receipt as PDF
    Supports both: 
    - payment_id (numeric ID)
    - client_ref_id (VP format)
    """
    try:
        # Try to find by payment_id (numeric ID)
        try:
            payment_id_int = int(payment_id)
            vendor_payment = get_object_or_404(
                VendorPayment, 
                id=payment_id_int, 
                user=request.user
            )
        except ValueError:
            # If not numeric, try to find by client_ref_id
            vendor_payment = get_object_or_404(
                VendorPayment, 
                client_ref_id=payment_id,
                user=request.user
            )
        
        # Check if receipt already generated
        if not vendor_payment.is_receipt_generated:
            vendor_payment.is_receipt_generated = True
            vendor_payment.receipt_generated_at = timezone.now()
            vendor_payment.save()
        
        # Generate receipt data
        receipt_data = vendor_payment.generate_receipt_data()
        
        # Generate PDF
        generator = VendorReceiptGenerator(receipt_data)
        pdf_buffer = generator.generate_pdf()
        
        # Create HTTP response
        filename = f"vendor_receipt_{vendor_payment.receipt_number}.pdf"
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        
        logger.info(f"✅ Receipt downloaded: {filename} for {payment_id}")
        return response
        
    except Exception as e:
        logger.error(f"❌ Receipt download error for {payment_id}: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to generate receipt: {str(e)}'
        }, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_vendor_receipt(request, payment_id):
    """
    View vendor payment receipt in browser
    """
    try:
        # Try to find by payment_id (numeric ID)
        try:
            payment_id_int = int(payment_id)
            vendor_payment = get_object_or_404(
                VendorPayment, 
                id=payment_id_int, 
                user=request.user
            )
        except ValueError:
            # If not numeric, try to find by client_ref_id
            vendor_payment = get_object_or_404(
                VendorPayment, 
                client_ref_id=payment_id,
                user=request.user
            )
        
        # Generate receipt data
        receipt_data = vendor_payment.generate_receipt_data()
        
        # Generate PDF for view
        generator = VendorReceiptGenerator(receipt_data)
        pdf_buffer = generator.generate_pdf()
        
        filename = f"vendor_receipt_{vendor_payment.receipt_number}.pdf"
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Receipt view error: {str(e)}")
        return Response({
            'status': 1,
            'message': f'Failed to view receipt: {str(e)}'
        }, status=400)
    
    