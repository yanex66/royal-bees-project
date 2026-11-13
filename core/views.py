# royal_bees_project/core/views.py

import secrets

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import NewsItem, Event, AdmissionApplication, ContactMessage, GalleryImage
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

# --- Existing Views ---
def home_view(request):
    latest_news = NewsItem.objects.all().order_by('-published_date')[:3]
    upcoming_events = Event.objects.filter(start_datetime__gte=timezone.now()).order_by('start_datetime')[:3]

    context = {
        'latest_news': latest_news,
        'upcoming_events': upcoming_events,
        'page_title': 'Home'
    }
    return render(request, 'core/index.html', context)

def about_view(request):
    return render(request, 'core/about.html')

# --- CONTACT US VIEW (Updated with Email) ---
def contact_us_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Save to Database
        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message
        )

        # Send Email Notification
        try:
            subject = f"New Website Contact: {name}"
            email_body = f"You have a new message from the school website contact form:\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"
            send_mail(
                subject,
                email_body,
                settings.EMAIL_HOST_USER,
                ['help.royalbees@gmail.com'], # Recipient
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email failed: {e}")

        messages.success(request, "Thank you! Your message has been sent. We will reply shortly.")
        return redirect('contact_us')

    return render(request, 'core/contact.html', {'page_title': 'Contact Us'})

# --- News Views ---
def news_list_view(request):
    news_items = NewsItem.objects.all().order_by('-published_date')
    context = {
        'news_items': news_items,
        'page_title': 'News & Announcements'
    }
    return render(request, 'core/news_list.html', context)

def news_detail_view(request, year, month, day, slug):
    news_item = get_object_or_404(NewsItem,
                                   slug=slug,
                                   published_date__year=year,
                                   published_date__month=month,
                                   published_date__day=day)
    context = {
        'news_item': news_item,
        'page_title': news_item.title
    }
    return render(request, 'core/news_detail.html', context)

# --- Event Views ---
def event_list_view(request):
    upcoming_events = Event.objects.filter(start_datetime__gte=timezone.now()).order_by('start_datetime')
    past_events = Event.objects.filter(start_datetime__lt=timezone.now()).order_by('-start_datetime')

    context = {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'page_title': 'School Events'
    }
    return render(request, 'core/event_list.html', context)

def event_detail_view(request, year, month, day, slug):
    event = get_object_or_404(Event,
                               slug=slug,
                               start_datetime__year=year,
                               start_datetime__month=month,
                               start_datetime__day=day)
    context = {
        'event': event,
        'page_title': event.title
    }
    return render(request, 'core/event_detail.html', context)

# --- Academics Views ---
def academics_overview_view(request):
    context = {
        'page_title': 'Academics Overview'
    }
    return render(request, 'core/academics_overview.html', context)

def curriculum_view(request):
    context = {
        'page_title': 'Our Curriculum'
    }
    return render(request, 'core/curriculum.html', context)

def departments_view(request):
    departments_list = [
        {'name': 'Science Department', 'head': 'Dr. B. Adebayo', 'description': 'Focusing on Physics, Chemistry, Biology and Integrated Science.'},
        {'name': 'Mathematics Department', 'head': 'Mrs. C. Eze', 'description': 'Covering all aspects of Mathematics from Basic to Advanced.'},
        {'name': 'Languages Department', 'head': 'Mr. A. Okoro', 'description': 'English, Yoruba, Igbo, Hausa, French and Literature.'},
        {'name': 'Humanities & Social Sciences', 'head': 'Ms. F. Bello', 'description': 'History, Government, Economics, Geography, Social Studies.'},
    ]
    context = {
        'page_title': 'Academic Departments',
        'departments': departments_list
    }
    return render(request, 'core/departments.html', context)


# --- Admissions View (Updated with Email) ---
def admissions_view(request):
    if request.method == 'POST':
        applicant_name = request.POST.get('applicant_name')
        date_of_birth = request.POST.get('date_of_birth')
        applying_grade = request.POST.get('applying_grade')
        parent_name = request.POST.get('parent_name')
        parent_phone = request.POST.get('parent_phone')
        parent_email = request.POST.get('parent_email')
        address = request.POST.get('address')
        terms_agreed = request.POST.get('terms_agreed') == 'on' 

        # Save to Database
        AdmissionApplication.objects.create(
            applicant_name=applicant_name,
            date_of_birth=date_of_birth,
            applying_grade=applying_grade,
            parent_name=parent_name,
            parent_phone=parent_phone,
            parent_email=parent_email,
            address=address,
            terms_agreed=terms_agreed
        )

        # Send Email Notification
        try:
            subject = f"New Admission Inquiry: {applicant_name}"
            email_body = (
                f"New admission inquiry received for {applicant_name}.\n\n"
                f"Grade Applying For: {applying_grade}\n"
                f"Parent Name: {parent_name}\n"
                f"Parent Phone: {parent_phone}\n"
                f"Parent Email: {parent_email}\n"
                f"Address: {address}"
            )
            send_mail(
                subject,
                email_body,
                settings.EMAIL_HOST_USER,
                ['help.royalbees@gmail.com'], # Recipient
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email failed: {e}")
        
        messages.success(request, 'Your application has been submitted successfully! We will contact you soon.')
        return redirect('admissions')

    context = {
        'page_title': 'Admissions Information'
    }
    return render(request, 'core/admissions.html', context)

# --- CORRECTED GALLERY VIEW ---
def gallery_view(request):
    images = GalleryImage.objects.all()
    context = {
        'page_title': 'School Gallery',
        'images': images,
    }
    return render(request, 'core/gallery.html', context)

def academic_calendar_view(request):
    context = {
        'page_title': 'Academic Calendar',
    }
    return render(request, 'core/academic_calendar.html', context)

# --- TEACHER LOCK SCREEN VIEW ---
def teacher_gate_view(request):
    portal_password = settings.TEACHER_PORTAL_PASSWORD
    if request.method == 'POST':
        password = request.POST.get('admin_password')
        if not portal_password:
            messages.error(request, 'Teacher access is not configured. Please contact the school administrator.')
            return redirect('teacher_gate')
        if password and secrets.compare_digest(password, portal_password):
            request.session.cycle_key()
            request.session['is_teacher'] = True
            messages.success(request, 'Access Granted. Welcome to the Teacher Portal.')
            return redirect('results:teacher_search_student')
        else:
            messages.error(request, 'Incorrect Admin Password! Access Denied.')
            return redirect('teacher_gate')

    context = {
        'page_title': 'Teacher Authentication',
        'password_configured': bool(portal_password),
    }
    return render(request, 'core/teacher_gate.html', context)