import hashlib
import hmac
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    AcademicSession,
    ClassFee,
    ClassLevel,
    FeePayment,
    Student,
    Term,
)


class FeePaymentPageTests(TestCase):
    @override_settings(PAYSTACK_PUBLIC_KEY='', PAYSTACK_SECRET_KEY='')
    def test_payment_page_disables_checkout_without_configuration(self):
        response = self.client.get(reverse('results:pay_fees'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'current academic session or fee schedule has not been configured')
        self.assertContains(response, 'disabled')

    @override_settings(PAYSTACK_PUBLIC_KEY='', PAYSTACK_SECRET_KEY='')
    def test_payment_submission_does_not_create_payment_without_keys(self):
        response = self.client.post(reverse('results:pay_fees'), {})

        self.assertRedirects(response, reverse('results:pay_fees'), fetch_redirect_response=False)
        self.assertEqual(FeePayment.objects.count(), 0)

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_payment_options_require_current_fee_configuration(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        class_level = ClassLevel.objects.create(name='Primary 1')
        ClassFee.objects.create(
            class_level=class_level,
            term=term,
            session=session,
            tuition_fee=100,
        )

        response = self.client.get(reverse('results:pay_fees'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Primary 1')
        self.assertContains(response, 'First Term')
        self.assertNotContains(response, 'current academic session or fee schedule has not been configured')

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_student_cannot_submit_another_class_for_payment(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        assigned_class = ClassLevel.objects.create(name='Primary 1')
        other_class = ClassLevel.objects.create(name='Primary 2')
        ClassFee.objects.create(
            class_level=other_class,
            term=term,
            session=session,
            tuition_fee=100,
        )
        Student.objects.create(
            student_id='RBS001',
            first_name='Test',
            last_name='Student',
            current_class=assigned_class,
        )

        response = self.client.post(
            reverse('results:pay_fees'),
            {
                'student_id': 'RBS001',
                'student_class': str(other_class.pk),
                'term': str(term.pk),
                'email': 'parent@example.com',
            },
            follow=True,
        )

        self.assertContains(response, 'The selected class does not match the student')
        self.assertEqual(FeePayment.objects.count(), 0)

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_unknown_payment_reference_is_not_sent_to_paystack(self):
        response = self.client.get(
            reverse('results:verify_payment'),
            {'reference': 'not-a-local-payment'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'This payment reference could not be found.', status_code=404)

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_verification_does_not_confirm_a_mismatched_amount(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        class_level = ClassLevel.objects.create(name='Primary 1')
        fee = ClassFee.objects.create(
            class_level=class_level,
            term=term,
            session=session,
            tuition_fee=100,
        )
        student = Student.objects.create(
            student_id='RBS002',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        payment = FeePayment.objects.create(
            student=student,
            fee_config=fee,
            amount_paid=fee.total_amount,
            email='parent@example.com',
            paystack_reference='test-reference',
        )
        paystack_response = Mock()
        paystack_response.raise_for_status.return_value = None
        paystack_response.json.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': payment.paystack_reference,
                'amount': 1,
                'currency': 'NGN',
            },
        }

        with patch('results.views.requests.get', return_value=paystack_response):
            response = self.client.get(
                reverse('results:verify_payment'),
                {'reference': payment.paystack_reference},
            )

        payment.refresh_from_db()
        self.assertEqual(payment.status, 'Pending')
        self.assertContains(response, 'Payment Failed')

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_webhook_rejects_invalid_json_even_with_a_valid_signature(self):
        payload = b'{'
        signature = hmac.new(
            b'sk_test_example',
            payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            reverse('results:paystack_webhook'),
            data=payload,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 400)
