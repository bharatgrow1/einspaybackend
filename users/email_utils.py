from django.core.mail import send_mail
from users.models import ServiceCharge, Transaction

def send_otp_email(email, otp, is_password_reset=False, purpose=None):
    if is_password_reset:
        subject = 'Your OTP for Password Reset'
        message = f'Your OTP for password reset is: {otp}. This OTP is valid for 10 minutes.'
    elif purpose == 'wallet_set_pin':
        subject = 'Your OTP for Wallet PIN Setup'
        message = f'Your OTP for wallet PIN setup is: {otp}. This OTP is valid for 10 minutes.'
    elif purpose == 'wallet_reset_pin':
        subject = 'Your OTP for Wallet PIN Reset'
        message = f'Your OTP for wallet PIN reset is: {otp}. This OTP is valid for 10 minutes.'
    else:
        subject = 'Your OTP for Login'
        message = f'Your OTP for login is: {otp}. This OTP is valid for 5 minutes.'
    
    send_mail(
        subject=subject,
        message=message,
        from_email='priteshbharatgrow@gmail.com',
        recipient_list=[email],
        fail_silently=False,
    )

def calculate_service_charge(amount, transaction_category):
    """Calculate service charge for a transaction"""
    try:
        service_charge_config = ServiceCharge.objects.get(
            transaction_category=transaction_category, 
            is_active=True
        )
        return service_charge_config.calculate_charge(amount)
    except ServiceCharge.DoesNotExist:
        return 0.00

def create_transaction_record(wallet, amount, transaction_type, category, description, 
                            recipient_user=None, service_charge=0, status='success',
                            opening_balance=None, closing_balance=None):
    """Helper function to create transaction record with opening/closing balances"""
    transaction = Transaction.objects.create(
        wallet=wallet,
        amount=amount,
        net_amount=amount,
        service_charge=service_charge,
        transaction_type=transaction_type,
        transaction_category=category,
        description=description,
        recipient_user=recipient_user,
        created_by=wallet.user,
        status=status
    )
    
    if opening_balance is not None:
        transaction.opening_balance = opening_balance
    if closing_balance is not None:
        transaction.closing_balance = closing_balance
    transaction.save()
    
    return transaction