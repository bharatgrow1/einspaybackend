def auto_process_commission(service_submission):
    """Automatically process commission when payment is successful"""
    try:
        from commission.views import CommissionManager
        from users.models import Transaction
        
        transaction = Transaction.objects.filter(
            service_submission=service_submission,
            status='success'
        ).first()
        
        if transaction:
            success, message = CommissionManager.process_service_commission(
                service_submission, transaction
            )
            
            if success:
                print(f"✅ Auto commission processed for submission {service_submission.id}")
            else:
                print(f"❌ Auto commission failed: {message}")
                
        return success, message
        
    except Exception as e:
        print(f"❌ Auto commission error: {e}")
        return False, str(e)