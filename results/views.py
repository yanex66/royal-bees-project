import logging
import json
import hashlib
import hmac
import secrets
import uuid
from decimal import Decimal, InvalidOperation

import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.forms import modelformset_factory

from .models import (
    PaymentConfiguration, AcademicSession, Term, ClassLevel, ClassFee,
    Student, Result, Subject, FeePayment, Testimonial
)
from .payment_utils import get_fee_balances

logger = logging.getLogger(__name__)

# --- 1. LANDING PAGE & REVIEWS ---

def home_view(request):
    """
    Displays the landing page with approved testimonials.
    Matches the layout seen in your provided screenshots.
    """
    # Only pull reviews manually approved in the Admin
    approved_reviews = Testimonial.objects.filter(is_approved=True).order_by('-date_submitted')[:6]
    
    context = {
        'testimonials': approved_reviews,
        'current_session': AcademicSession.objects.filter(is_current=True).first()
    }
    return render(request, 'home.html', context)

def submit_review(request):
    """
    Handles the submission of a new parent review from the footer form.
    """
    if request.method == "POST":
        p_name = request.POST.get('parent_name')
        p_designation = request.POST.get('parent_designation')
        p_review = request.POST.get('review_text')

        if p_name and p_review:
            Testimonial.objects.create(
                parent_name=p_name,
                parent_designation=p_designation,
                review_text=p_review
            )
            messages.success(request, "Your review has been submitted for approval. Thank you!")
        else:
            messages.error(request, "Please fill in all fields to submit a review.")
            
    return redirect('home')

# --- 2. HELPER: EMAIL RECEIPT ---

def send_payment_receipt(payment):
    """Sends a professional email receipt to the parent/guardian."""
    try:
        subject = f"Payment Receipt: {payment.student.get_full_name()} ({payment.paystack_reference})"
        message = f"""
        Dear Parent/Guardian,

        This is a formal confirmation of school fee payment for {payment.student.get_full_name()}.

        Details:
        - Reference: {payment.paystack_reference}
        - Fee amount: NGN {payment.amount_paid:.2f}
        - Processing charge: NGN {payment.processing_fee:.2f}
        - Total charged: NGN {payment.total_transaction_amount:.2f}
        - Term: {payment.fee_config.term.name}
        - Date: {payment.created_at.strftime('%Y-%m-%d %H:%M')}

        Thank you for choosing Royal Bees International School.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [payment.email],
            fail_silently=False,
        )
        logger.info(f"Receipt sent to {payment.email} for ref {payment.paystack_reference}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# --- 3. PAYSTACK PAYMENT VIEWS ---

def initialize_payment(request):
    if request.method == "POST":
        if not settings.PAYSTACK_PUBLIC_KEY or not settings.PAYSTACK_SECRET_KEY:
            messages.error(request, "Online payments are not configured yet. Please contact the school office.")
            return redirect('results:pay_fees')

        email = request.POST.get('email', '').strip()
        student_id = request.POST.get('student_id', '').strip()
        class_id = request.POST.get('student_class')
        term_id = request.POST.get('term')
        amount_raw = request.POST.get('amount', '').strip()
        payment_configuration = PaymentConfiguration.objects.get(pk=1)

        if not all([student_id, class_id, term_id, email, amount_raw]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('results:pay_fees')
        try:
            validate_email(email)
            class_id = int(class_id)
            term_id = int(term_id)
            amount_to_pay = Decimal(amount_raw)
            amount_to_pay_cents = amount_to_pay.quantize(Decimal('0.01'))
        except (ValidationError, TypeError, ValueError, OverflowError):
            messages.error(request, "Please enter a valid email address and select a valid class and term.")
            return redirect('results:pay_fees')
        except InvalidOperation:
            messages.error(request, "Please enter a valid payment amount.")
            return redirect('results:pay_fees')

        if (
            not amount_to_pay.is_finite()
            or amount_to_pay < payment_configuration.minimum_payment_amount
            or amount_to_pay != amount_to_pay_cents
        ):
            messages.error(
                request,
                f"Enter an amount of at least NGN {payment_configuration.minimum_payment_amount:.2f} "
                "with no more than two decimal places.",
            )
            return redirect('results:pay_fees')

        student = Student.objects.filter(student_id=student_id).first()
        if not student:
            messages.error(request, f"No student found with ID: {student_id}.")
            return redirect('results:pay_fees')

        if not student.active or not student.current_class_id:
            messages.error(request, "This student is not currently assigned to an active class. Please contact the school office.")
            return redirect('results:pay_fees')

        if str(student.current_class_id) != str(class_id):
            messages.error(request, "The selected class does not match the student's current class.")
            return redirect('results:pay_fees')

        current_session = AcademicSession.objects.filter(is_current=True).first()
        fee_config = ClassFee.objects.filter(
            class_level_id=student.current_class_id,
            term_id=term_id,
            session=current_session,
        ).first()
        
        if not current_session or not fee_config:
            messages.error(request, "Fees for this class/term have not been set.")
            return redirect('results:pay_fees')
        
        if fee_config.total_amount <= 0:
            messages.error(request, "The fee amount for this class/term is not configured. Please contact the school office.")
            return redirect('results:pay_fees')

        fee_configs, fee_balances = get_fee_balances(
            student,
            current_session,
            through_term_order=fee_config.term.order,
        )
        arrears_amount = sum(
            fee_balances[config.pk]
            for config in fee_configs
            if config.term.order < fee_config.term.order
        )
        amount_due = sum(fee_balances.values())
        if amount_due <= 0:
            messages.error(request, "There is no outstanding balance for the selected term.")
            return redirect('results:pay_fees')
        if amount_to_pay > amount_due:
            messages.error(
                request,
                f"The amount cannot exceed the outstanding balance of NGN {amount_due:.2f}.",
            )
            return redirect('results:pay_fees')

        arrears_cleared = min(amount_to_pay, arrears_amount)
        reference = str(uuid.uuid4())

        payment = FeePayment.objects.create(
            student=student, fee_config=fee_config, amount_paid=amount_to_pay,
            processing_fee=payment_configuration.processing_fee,
            arrears_cleared=arrears_cleared, email=email,
            paystack_reference=reference, status='Pending'
        )
        total_transaction_amount = payment.total_transaction_amount

        url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        data = {"email": email, "amount": int(total_transaction_amount * 100), "reference": reference,
                "callback_url": f"{request.scheme}://{request.get_host()}/results/verify-payment/"}

        try:
            response = requests.post(url, headers=headers, json=data, timeout=15)
            response.raise_for_status()
            res_data = response.json()
        except (requests.RequestException, ValueError):
            payment.status = 'Failed'
            payment.save(update_fields=['status'])
            logger.exception("Paystack payment initialization failed.")
            messages.error(request, "Connection to Paystack failed.")
            return redirect('results:pay_fees')

        if res_data.get('status') and res_data.get('data', {}).get('authorization_url'):
            return redirect(res_data['data']['authorization_url'])

        payment.status = 'Failed'
        payment.save(update_fields=['status'])
        messages.error(request, f"Paystack Error: {res_data.get('message', 'Payment could not be initialized.')}")

    current_session = AcademicSession.objects.filter(is_current=True).first()
    if current_session:
        classes = ClassLevel.objects.filter(fees__session=current_session).distinct()
        terms = Term.objects.filter(classfee__session=current_session).distinct()
    else:
        classes = ClassLevel.objects.none()
        terms = Term.objects.none()
    payments_configured = bool(settings.PAYSTACK_PUBLIC_KEY and settings.PAYSTACK_SECRET_KEY)

    context = {
        'classes': classes,
        'terms': terms,
        'current_session': current_session,
        'payment_configuration': PaymentConfiguration.objects.get(pk=1),
        'fee_options_available': classes.exists() and terms.exists(),
        'payments_configured': payments_configured,
    }
    return render(request, 'results/pay_fees.html', context)

def verify_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'results/payment_failed.html', {'error': 'No reference provided.'})

    payment = FeePayment.objects.filter(paystack_reference=reference).first()
    if not payment:
        return render(
            request,
            'results/payment_failed.html',
            {'error': 'This payment reference could not be found.'},
            status=404,
        )
    if not settings.PAYSTACK_SECRET_KEY:
        return render(
            request,
            'results/payment_failed.html',
            {'error': 'Payment verification is temporarily unavailable. Please contact the school office.'},
            status=503,
        )

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()

    except (requests.RequestException, ValueError):
        logger.exception("Paystack payment verification failed for reference %s.", reference)
        return render(
            request,
            'results/payment_failed.html',
            {'error': 'Payment verification could not be completed. Please contact the school office.'},
            status=502,
        )

    transaction = response_data.get('data', {})
    payment_matches = (
        transaction.get('status') == 'success'
        and transaction.get('amount') == int(payment.total_transaction_amount * 100)
        and transaction.get('currency') == 'NGN'
        and transaction.get('reference') == reference
    )
    if response_data.get('status') and payment_matches:
        if payment.status != 'Successful':
            payment.status = 'Successful'
            payment.save(update_fields=['status'])
            send_payment_receipt(payment)
        return render(request, 'results/payment_success.html', {'payment': payment})

    reason = transaction.get('gateway_response', 'Payment was not confirmed.')
    return render(request, 'results/payment_failed.html', {'reason': reason})

@csrf_exempt
def paystack_webhook(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not settings.PAYSTACK_SECRET_KEY:
        return HttpResponse(status=503)

    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    
    if not signature:
        return HttpResponse(status=400)

    computed_hmac = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not secrets.compare_digest(computed_hmac, signature):
        return HttpResponse(status=401)

    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)
    if not isinstance(data, dict):
        return HttpResponse(status=400)

    if data.get('event') == 'charge.success':
        transaction = data.get('data', {})
        if not isinstance(transaction, dict):
            return HttpResponse(status=400)
        reference = transaction.get('reference')
        payment = FeePayment.objects.filter(paystack_reference=reference).first()
        payment_matches = (
            payment
            and transaction.get('status') == 'success'
            and transaction.get('amount') == int(payment.total_transaction_amount * 100)
            and transaction.get('currency') == 'NGN'
        )

        if payment_matches and payment.status != 'Successful':
            payment.status = 'Successful'
            payment.save(update_fields=['status'])
            send_payment_receipt(payment)

    return HttpResponse(status=200)

# --- 4. TEACHER & STUDENT FUNCTIONALITY ---

def check_result_view(request):
    if request.method == 'POST':
        sid, pin = request.POST.get('student_id', '').strip(), request.POST.get('pin', '').strip()
        try:
            s = Student.objects.get(student_id=sid) 
            if s.pin == pin:
                r = s.results.all().select_related('subject', 'academic_session', 'term')
                return render(request, 'results/display_results.html', {'student': s, 'results': r})
            messages.error(request, "Incorrect PIN.")
        except Student.DoesNotExist: messages.error(request, "Invalid Student ID.")
    return render(request, 'results/check_result_form.html')

def teacher_search_student_view(request):
    if not request.session.get('is_teacher'): return redirect('teacher_gate')
    query = request.POST.get('search_query', '').strip()
    found = Student.objects.filter(Q(student_id__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)).filter(active=True) if query else None
    return render(request, 'results/teacher_student_search.html', {'students_found': found, 'search_query': query})

def teacher_select_session_term_view(request, student_id):
    if not request.session.get('is_teacher'): return redirect('teacher_gate')
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        session_id = request.POST.get('academic_session')
        term_id = request.POST.get('term')
        if session_id and term_id:
            return redirect('results:teacher_score_sheet', student_id=student.id, session_id=session_id, term_id=term_id)
        else:
            messages.warning(request, "Please select both a Session and a Term.")
    context = {
        'student': student, 
        'sessions': AcademicSession.objects.all(), 
        'terms': Term.objects.all(),
        'current_session': AcademicSession.objects.filter(is_current=True).first()
    }
    return render(request, 'results/teacher_select_session_term.html', context)

def teacher_score_sheet_view(request, student_id, session_id, term_id):
    if not request.session.get('is_teacher'): return redirect('teacher_gate')
    student = get_object_or_404(Student, pk=student_id)
    selected_session = get_object_or_404(AcademicSession, pk=session_id)
    selected_term = get_object_or_404(Term, pk=term_id)
    
    ResultFormSet = modelformset_factory(
        Result,
        fields=('test_score_1', 'test_score_2', 'exam_score', 'remarks'),
        extra=0
    )

    # Auto-create results for all subjects if they don't exist
    subjects = Subject.objects.all()
    for sub in subjects:
        Result.objects.get_or_create(
            student=student,
            academic_session=selected_session,
            term=selected_term,
            subject=sub
        )

    if request.method == 'POST':
        formset = ResultFormSet(request.POST, queryset=Result.objects.filter(
            student=student, academic_session=selected_session, term=selected_term
        ))
        if formset.is_valid():
            formset.save()
            messages.success(request, f"Scores for {student.get_full_name()} saved successfully!")
            return redirect('results:teacher_score_sheet', student_id=student.id, 
                            session_id=selected_session.id, term_id=selected_term.id)
    else:
        results_qs = Result.objects.filter(
            student=student, academic_session=selected_session, term=selected_term
        ).select_related('subject').order_by('subject__name')
        formset = ResultFormSet(queryset=results_qs)
        for form, res in zip(formset, results_qs):
            form.initial['subject_name_display'] = res.subject.name

    context = {
        'student': student,
        'selected_session': selected_session,
        'selected_term': selected_term,
        'score_formset': formset,
    }
    return render(request, 'results/teacher_score_sheet.html', context)