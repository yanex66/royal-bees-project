# royal_bees_project/urls.py
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
from core.sitemaps import EventSitemap, NewsSitemap, StaticSitemap

sitemaps = {
    'pages': StaticSitemap,
    'news': NewsSitemap,
    'events': EventSitemap,
}

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

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