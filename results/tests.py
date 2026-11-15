import json
import hashlib
import hmac
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import StudentAdmin
from .models import (
    AcademicSession,
    ClassFee,
    ClassLevel,
    FeePayment,
    PaymentConfiguration,
    Student,
    Term,
)


class FeePaymentPageTests(TestCase):
    def test_payment_configuration_is_available_and_editable_in_admin(self):
        configuration = PaymentConfiguration.objects.get(pk=1)
        self.assertEqual(configuration.minimum_payment_amount, 2000)
        self.assertEqual(configuration.processing_fee, 250)

        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(admin_user)
        response = self.client.get(
            reverse('admin:results_paymentconfiguration_change', args=[configuration.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'minimum_payment_amount')
        self.assertContains(response, 'processing_fee')
        response = self.client.post(
            reverse('admin:results_paymentconfiguration_change', args=[configuration.pk]),
            {
                'minimum_payment_amount': '2500.00',
                'processing_fee': '300.00',
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 302)
        configuration.refresh_from_db()
        self.assertEqual(configuration.minimum_payment_amount, 2500)
        self.assertEqual(configuration.processing_fee, 300)

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
        self.assertContains(response, 'name="amount"')
        self.assertContains(response, 'min="2000.00"')
        self.assertContains(response, 'NGN 250.00 charge')
        self.assertContains(response, 'aria-label="Paystack"')
        self.assertNotContains(response, 'paystack.com/assets/img/badge.png')
        self.assertNotContains(response, 'current academic session or fee schedule has not been configured')

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_admin_payment_status_distinguishes_partial_and_paid_balances(self):
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
            student_id='RBS005',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        payment_status = StudentAdmin(Student, None).payment_status

        self.assertIn('OWING', payment_status(student))
        FeePayment.objects.create(
            student=student,
            fee_config=fee,
            amount_paid=40,
            email='parent@example.com',
            paystack_reference='partial-admin-status',
            status='Successful',
        )
        self.assertIn('PARTIAL', payment_status(student))
        FeePayment.objects.create(
            student=student,
            fee_config=fee,
            amount_paid=60,
            email='parent@example.com',
            paystack_reference='paid-admin-status',
            status='Successful',
        )
        self.assertIn('PAID', payment_status(student))

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
            tuition_fee=5000,
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
                'amount': '2000',
            },
            follow=True,
        )

        self.assertContains(response, 'The selected class does not match the student')
        self.assertEqual(FeePayment.objects.count(), 0)

    @override_settings(
        PAYSTACK_PUBLIC_KEY='pk_test_example',
        PAYSTACK_SECRET_KEY='sk_test_example',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_partial_amount_is_sent_to_paystack_and_applied_to_oldest_balance_first(self):
        PaymentConfiguration.objects.filter(pk=1).update(minimum_payment_amount=1)
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        first_term = Term.objects.create(name='First Term', order=1)
        second_term = Term.objects.create(name='Second Term', order=2)
        class_level = ClassLevel.objects.create(name='Primary 1')
        first_fee = ClassFee.objects.create(
            class_level=class_level,
            term=first_term,
            session=session,
            tuition_fee=100,
        )
        ClassFee.objects.create(
            class_level=class_level,
            term=second_term,
            session=session,
            tuition_fee=200,
        )
        student = Student.objects.create(
            student_id='RBS003',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        FeePayment.objects.create(
            student=student,
            fee_config=first_fee,
            amount_paid=40,
            email='parent@example.com',
            paystack_reference='previous-partial-payment',
            status='Successful',
        )
        paystack_response = Mock()
        paystack_response.raise_for_status.return_value = None
        paystack_response.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://paystack.test/checkout'},
        }

        with patch('results.views.requests.post', return_value=paystack_response) as post:
            response = self.client.post(
                reverse('results:pay_fees'),
                {
                    'student_id': student.student_id,
                    'student_class': str(class_level.pk),
                    'term': str(second_term.pk),
                    'email': 'parent@example.com',
                    'amount': '50.25',
                },
            )

        self.assertRedirects(
            response,
            'https://paystack.test/checkout',
            fetch_redirect_response=False,
        )
        payment = FeePayment.objects.exclude(
            paystack_reference='previous-partial-payment'
        ).get()
        self.assertEqual(payment.amount_paid, 50.25)
        self.assertEqual(payment.processing_fee, 250)
        self.assertEqual(payment.arrears_cleared, 50.25)
        self.assertEqual(post.call_args.kwargs['json']['amount'], 30025)

        verification_response = Mock()
        verification_response.raise_for_status.return_value = None
        verification_response.json.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': payment.paystack_reference,
                'amount': 30025,
                'currency': 'NGN',
            },
        }
        with patch('results.views.requests.get', return_value=verification_response):
            verification = self.client.get(
                reverse('results:verify_payment'),
                {'reference': payment.paystack_reference},
            )
        self.assertEqual(verification.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'Successful')
        self.assertContains(verification, 'Processing charge')
        self.assertContains(verification, 'Total charged')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Processing charge: NGN 250.00', mail.outbox[0].body)
        self.assertIn('Total charged: NGN 300.25', mail.outbox[0].body)

        with patch('results.views.requests.post') as post:
            response = self.client.post(
                reverse('results:pay_fees'),
                {
                    'student_id': student.student_id,
                    'student_class': str(class_level.pk),
                    'term': str(second_term.pk),
                    'email': 'parent@example.com',
                    'amount': '209.76',
                },
                follow=True,
            )

        self.assertContains(response, 'outstanding balance of NGN 209.75')
        self.assertEqual(FeePayment.objects.count(), 2)
        post.assert_not_called()

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_payment_amount_must_be_within_balance_and_meet_configured_minimum(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        class_level = ClassLevel.objects.create(name='Primary 1')
        ClassFee.objects.create(
            class_level=class_level,
            term=term,
            session=session,
            tuition_fee=5000,
        )
        student = Student.objects.create(
            student_id='RBS004',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        form_data = {
            'student_id': student.student_id,
            'student_class': str(class_level.pk),
            'term': str(term.pk),
            'email': 'parent@example.com',
        }

        invalid_amounts = (
            ('5000.01', 'outstanding balance of NGN 5000.00'),
            ('1999.99', 'at least NGN 2000.00'),
            ('2000.001', 'at least NGN 2000.00'),
            ('NaN', 'at least NGN 2000.00'),
        )
        with patch('results.views.requests.post') as post:
            for amount, expected_message in invalid_amounts:
                with self.subTest(amount=amount):
                    response = self.client.post(
                        reverse('results:pay_fees'),
                        {**form_data, 'amount': amount},
                        follow=True,
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(FeePayment.objects.count(), 0)
                    self.assertContains(response, expected_message)
                    post.assert_not_called()

    @override_settings(PAYSTACK_PUBLIC_KEY='pk_test_example', PAYSTACK_SECRET_KEY='sk_test_example')
    def test_minimum_fee_payment_adds_configured_charge_to_paystack_amount(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        class_level = ClassLevel.objects.create(name='Primary 1')
        fee = ClassFee.objects.create(
            class_level=class_level,
            term=term,
            session=session,
            tuition_fee=3000,
        )
        student = Student.objects.create(
            student_id='RBS006',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        paystack_response = Mock()
        paystack_response.raise_for_status.return_value = None
        paystack_response.json.return_value = {
            'status': True,
            'data': {'authorization_url': 'https://paystack.test/checkout'},
        }

        with patch('results.views.requests.post', return_value=paystack_response) as post:
            response = self.client.post(
                reverse('results:pay_fees'),
                {
                    'student_id': student.student_id,
                    'student_class': str(class_level.pk),
                    'term': str(term.pk),
                    'email': 'parent@example.com',
                    'amount': '2000.00',
                },
            )

        self.assertRedirects(response, 'https://paystack.test/checkout', fetch_redirect_response=False)
        payment = FeePayment.objects.get()
        self.assertEqual(payment.amount_paid, 2000)
        self.assertEqual(payment.processing_fee, 250)
        self.assertEqual(payment.total_transaction_amount, 2250)
        self.assertEqual(post.call_args.kwargs['json']['amount'], 225000)

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

    @override_settings(
        PAYSTACK_PUBLIC_KEY='pk_test_example',
        PAYSTACK_SECRET_KEY='sk_test_example',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_webhook_verifies_the_saved_fee_and_processing_charge_total(self):
        session = AcademicSession.objects.create(year='2026/2027', is_current=True)
        term = Term.objects.create(name='First Term', order=1)
        class_level = ClassLevel.objects.create(name='Primary 1')
        fee = ClassFee.objects.create(
            class_level=class_level,
            term=term,
            session=session,
            tuition_fee=3000,
        )
        student = Student.objects.create(
            student_id='RBS007',
            first_name='Test',
            last_name='Student',
            current_class=class_level,
        )
        payment = FeePayment.objects.create(
            student=student,
            fee_config=fee,
            amount_paid=2000,
            processing_fee=250,
            email='parent@example.com',
            paystack_reference='webhook-charge-reference',
        )

        for amount, expected_status in ((200000, 'Pending'), (225000, 'Successful')):
            payload = json.dumps({
                'event': 'charge.success',
                'data': {
                    'reference': payment.paystack_reference,
                    'status': 'success',
                    'amount': amount,
                    'currency': 'NGN',
                },
            }).encode()
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

            self.assertEqual(response.status_code, 200)
            payment.refresh_from_db()
            self.assertEqual(payment.status, expected_status)
