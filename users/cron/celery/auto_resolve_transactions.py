from django.utils import timezone
from datetime import timedelta
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from users.models import Transaction


def auto_resolve_transactions():
    now = timezone.now()
    
    qs = Transaction.objects.filter(
        status__in=['processing', 'pending'],
        refund_status='none',
        created_at__lt=now - timedelta(minutes=10)
    )
    
    count = qs.count()
    
    if count > 0:
        qs.update(status='failed')
        
        for tx in qs:
            meta = tx.metadata or {}
            meta['auto_resolved'] = True
            meta['resolved_at'] = now.isoformat()
            tx.metadata = meta
            tx.save(update_fields=['metadata'])
    
    print(f"Auto resolved {count} transactions")
    return count