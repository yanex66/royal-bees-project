import requests
import uuid
import logging
import json
import hashlib
import hmac
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.forms import modelformset_factory

from .models import (
    AcademicSession, Term, ClassLevel, ClassFee, 
    Student, Result, Subject, FeePayment, Testimonial
)

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
        - Amount Paid: NGN {payment.amount_paid}
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
        email = request.POST.get('email')
        student_id = request.POST.get('student_id')
        class_id = request.POST.get('student_class')
        term_id = request.POST.get('term')

        if not all([student_id, class_id, term_id, email]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('results:pay_fees')

        student = Student.objects.filter(student_id=student_id).first()
        if not student:
            messages.error(request, f"No student found with ID: {student_id}.")
            return redirect('results:pay_fees')

        fee_config = ClassFee.objects.filter(
            class_level_id=class_id, term_id=term_id, session__is_current=True
        ).first()
        
        if not fee_config:
            messages.error(request, "Fees for this class/term have not been set.")
            return redirect('results:pay_fees')
        
        current_amount = fee_config.total_amount
        arrears_amount = 0

        # Calculate arrears for previous terms in the same session
        previous_terms = Term.objects.filter(order__lt=fee_config.term.order).order_by('-order')[:2]
        for p_term in previous_terms:
            paid = FeePayment.objects.filter(
                student=student, fee_config__term=p_term, 
                fee_config__session=fee_config.session, status='Successful'
            ).exists()
            if not paid:
                p_config = ClassFee.objects.filter(class_level=fee_config.class_level, term=p_term, session=fee_config.session).first()
                if p_config: arrears_amount += p_config.total_amount

        total_amount = current_amount + arrears_amount
        reference = str(uuid.uuid4())

        FeePayment.objects.create(
            student=student, fee_config=fee_config, amount_paid=total_amount,
            arrears_cleared=arrears_amount, email=email,
            paystack_reference=reference, status='Pending'
        )

        url = "https://api.paystack.co/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
        data = {"email": email, "amount": int(total_amount * 100), "reference": reference,
                "callback_url": f"{request.scheme}://{request.get_host()}/results/verify-payment/"}

        try:
            response = requests.post(url, headers=headers, json=data)
            res_data = response.json()
            if res_data['status']: return redirect(res_data['data']['authorization_url'])
            else: messages.error(request, f"Paystack Error: {res_data['message']}")
        except Exception as e:
            logger.error(f"Paystack Init Exception: {e}")
            messages.error(request, "Connection to Paystack failed.")
            
    context = {
        'classes': ClassLevel.objects.all(),
        'terms': Term.objects.all(),
        'current_session': AcademicSession.objects.filter(is_current=True).first()
    }
    return render(request, 'results/pay_fees.html', context)

def verify_payment(request):
    reference = request.GET.get('reference')
    if not reference:
        return render(request, 'results/payment_failed.html', {'error': 'No reference provided.'})

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response_data['status'] and response_data['data']['status'] == 'success':
            payment = get_object_or_404(FeePayment, paystack_reference=reference)
            if payment.status != 'Successful':
                payment.status = 'Successful'
                payment.save()
                send_payment_receipt(payment)
            return render(request, 'results/payment_success.html', {'payment': payment})
        else:
            reason = response_data.get('data', {}).get('gateway_response', 'Unknown Error')
            return render(request, 'results/payment_failed.html', {'reason': reason})
    except Exception as e:
        return render(request, 'results/payment_failed.html', {'error': str(e)})

@csrf_exempt
def paystack_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    
    if not signature:
        return HttpResponse(status=400)

    computed_hmac = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if computed_hmac != signature:
        return HttpResponse(status=401)

    data = json.loads(payload)
    if data['event'] == 'charge.success':
        reference = data['data']['reference']
        payment = FeePayment.objects.filter(paystack_reference=reference).first()
        
        if payment and payment.status != 'Successful':
            payment.status = 'Successful'
            payment.save()
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