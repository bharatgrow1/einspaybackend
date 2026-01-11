from django.utils import timezone
from datetime import timedelta
from users.models import Transaction

def auto_resolve_transactions():
    now = timezone.now()

    qs = Transaction.objects.filter(
        status__in=['processing', 'pending'],
        refund_status='none',
        created_at__lt=now - timedelta(minutes=10)
    )

    count = 0
    for tx in qs:
        tx.status = 'failed'
        tx.metadata = tx.metadata or {}
        tx.metadata['auto_resolved'] = True
        tx.metadata['auto_resolved_at'] = now.isoformat()
        tx.save(update_fields=['status', 'metadata'])
        count += 1

    print(f"✅ Auto-resolved {count} transactions")
