# royal_bees_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # --- Django Admin ---
    path('admin/', admin.site.urls),
    
    # --- Core Website (Home, About, Contact, Admissions) ---
    # Core should handle the landing page where testimonials are displayed
    path('', include('core.urls')),    
    
    # --- Results & Payments (Student Portal, Paystack, Reviews) ---
    # This handles the result check, fee payments, and testimonial submissions
    path('results/', include('results.urls')),
]

# FOR DEVELOPMENT ONLY: Serve media (photos) and static files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)