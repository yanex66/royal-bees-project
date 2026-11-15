from .models import ClassFee, FeePayment


def get_fee_balances(student, session, through_term_order=None):
    fee_configs = list(
        ClassFee.objects.filter(
            class_level_id=student.current_class_id,
            session=session,
        )
        .select_related('term')
        .order_by('term__order', 'pk')
    )
    if through_term_order is not None:
        fee_configs = [
            fee_config for fee_config in fee_configs
            if fee_config.term.order <= through_term_order
        ]

    balances = {
        fee_config.pk: fee_config.total_amount
        for fee_config in fee_configs
    }
    successful_payments = (
        FeePayment.objects.filter(
            student=student,
            fee_config__class_level_id=student.current_class_id,
            fee_config__session=session,
            status='Successful',
        )
        .select_related('fee_config__term')
        .order_by('created_at', 'pk')
    )

    for payment in successful_payments:
        amount_remaining = payment.amount_paid
        for fee_config in fee_configs:
            if fee_config.term.order > payment.fee_config.term.order:
                break
            if balances[fee_config.pk] <= 0:
                continue
            applied_amount = min(amount_remaining, balances[fee_config.pk])
            balances[fee_config.pk] -= applied_amount
            amount_remaining -= applied_amount
            if amount_remaining <= 0:
                break

    return fee_configs, balances
