from django.db import transaction as db_transaction
from users.models import RefundRequest, Transaction

class RefundService:

    @classmethod
    @db_transaction.atomic
    def auto_initiate(cls, wallet_transaction, eko_response):

        wallet_transaction = (
            Transaction.objects
            .select_for_update()
            .get(id=wallet_transaction.id)
        )

        # 🔒 Double safety check
        if wallet_transaction.refund_status != "not_refunded":
            return None

        if RefundRequest.objects.filter(
            original_transaction=wallet_transaction
        ).exists():
            return None

        refund = RefundRequest.objects.create(
            user=wallet_transaction.wallet.user,
            original_transaction=wallet_transaction,
            amount=wallet_transaction.amount,
            eko_response=eko_response
        )

        wallet_transaction.refund_status = "refund_initiated"
        wallet_transaction.save(update_fields=["refund_status"])

        return refund
