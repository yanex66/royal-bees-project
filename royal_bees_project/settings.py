import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file (Make sure you create this file on PythonAnywhere)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- SECURITY ---
DEBUG = os.getenv('DJANGO_DEBUG', 'True').strip().lower() in {'true', '1', 'yes'}
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be configured when DEBUG is disabled.')
    SECRET_KEY = 'django-insecure-development-key'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
else:
    CSRF_TRUSTED_ORIGINS = []


# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'jazzmin',
    'templatetags',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'whitenoise.runserver_nostatic', 
    'core',
    'results',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'royal_bees_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'royal_bees_project.wsgi.application'


# --- DATABASE ---
# SQLite is convenient for local development and a temporary Render demo.
# Render's free filesystem is ephemeral; use a persistent database for production.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# --- EMAIL SETTINGS ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_USER') 
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD') 
DEFAULT_FROM_EMAIL = f"Royal Bees International School <{EMAIL_HOST_USER}>"


# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True


# --- STATIC FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# For PythonAnywhere, Whitenoise works best with this setting:
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- MEDIA FILES ---
# GREAT NEWS: On PythonAnywhere, these files are NEVER deleted.
# You don't need Cloudinary yet!
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# --- PAYSTACK API KEYS ---
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_placeholder')
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_placeholder')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


JAZZMIN_SETTINGS = {
    "site_title": "Royal Bees Admin",
    "site_header": "Royal Bees",
    "site_brand": "Royal Bees School",
    "site_logo": "core/images/logos/r_logo.png",
    "welcome_sign": "Royal Bees Management Portal",
    "copyright": "Royal Bees International School",
    "user_avatar": None,

    # This organizes the sidebar into logical groups
    "topmenu_links": [
        {"name": "Home",  "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Website", "url": "/", "new_window": True},
    ],

    "show_sidebar": True,
    "navigation_expanded": True,

    # Custom icons for a friendly look
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        "results.Student": "fas fa-user-graduate",
        "results.ClassLevel": "fas fa-school",
        "results.Result": "fas fa-poll-h",
        "results.Subject": "fas fa-book-open",
        "results.FeePayment": "fas fa-credit-card",
        "results.ClassFee": "fas fa-coins",
        "results.AcademicSession": "fas fa-calendar-alt",
        "results.Term": "fas fa-clock",
    },

    # The order makes sure the most used items (Students/Results) are at the top
    "order_with_respect_to": [
        "results.Student", 
        "results.ClassLevel", 
        "results.Result", 
        "results.FeePayment", 
        "results.Subject",
        "auth"
    ],
}

JAZZMIN_UI_CONFIG = {
    "theme": "flatly",
    "dark_mode_theme": None, # Keep it light and professional
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary", # Dark sidebar with white main area
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# settings.py (Bottom of the file)

import django.utils.html
from django.utils.safestring import mark_safe

original_format_html = django.utils.html.format_html

def patched_format_html(format_string, *args, **kwargs):
    if not args and not kwargs:
        return mark_safe(format_string)
    return original_format_html(format_string, *args, **kwargs)

django.utils.html.format_html = patched_format_html