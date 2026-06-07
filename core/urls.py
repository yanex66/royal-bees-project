# royal_bees_project/core/urls.py

from django.urls import path
from . import views # Make sure views is imported

# It's good practice to define app_name for namespacing, especially in larger projects.
# If you uncomment this, remember to change {% url 'name' %} to {% url 'core:name' %} in your templates.
# For now, I'll assume you prefer non-namespaced URLs for simplicity as per your existing usage.
# app_name = 'core' # <--- Keep this commented if you want to use just 'gallery' instead of 'core:gallery'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),

    # Modified: Using 'contact' as the URL name to match existing, but 'contact_us' was used in template
    # Best to stick to one name. I'll make it 'contact_us' here to match the template, assuming
    # you'll rename your contact_view in views.py accordingly.
    path('contact-us/', views.contact_us_view, name='contact_us'), # Renamed for clarity and template consistency

    # News & Events paths (your existing ones)
    path('news/', views.news_list_view, name='news_list'),
    path('news/<int:year>/<int:month>/<int:day>/<slug:slug>/',
         views.news_detail_view, name='news_detail'),

    path('events/', views.event_list_view, name='event_list'),
    path('events/<int:year>/<int:month>/<int:day>/<slug:slug>/',
         views.event_detail_view, name='event_detail'),

    # Added: The missing 'academic_calendar' URL
    path('academic-calendar/', views.academic_calendar_view, name='academic_calendar'),

    # Academic sub-pages (your existing ones)
    path('academics/', views.academics_overview_view, name='academics_overview'),
    path('academics/curriculum/', views.curriculum_view, name='curriculum'),
    path('academics/departments/', views.departments_view, name='departments'),

    # Admissions & Gallery (your existing ones, confirm names match template)
    path('admissions/', views.admissions_view, name='admissions'),

    # CRITICAL: This line is present and correct as you noted!
    path('gallery/', views.gallery_view, name='gallery'),
    path('teacher-access/', views.teacher_gate_view, name='teacher_gate'),
]