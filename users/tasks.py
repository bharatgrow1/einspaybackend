from celery import shared_task
from users.cron.celery.auto_resolve_transactions import auto_resolve_transactions

@shared_task
def auto_resolve_transactions_task():
    return auto_resolve_transactions()
