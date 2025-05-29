from pathlib import Path
from decouple import config
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# OpenSolar and Odoo API configuration from the .env file
OPENSOLAR_API_TOKEN = config('OPENSOLAR_API_TOKEN')
ODOO_URL = config('ODOO_URL')
ODOO_DB = config('ODOO_DB')
ODOO_API_TOKEN = config("ODOO_API_TOKEN")

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     config('DATABASE_NAME'),
        'USER':     config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST':     config('DATABASE_HOST', default='localhost'),
        'PORT':     config('DATABASE_PORT', default='5432'),
    }
}

# Django security settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-3$eaxf5sd$_$e$&7lo1!=2q0x$%z^fkibbut2+ikjea2hfiny(')

# Debugging
DEBUG = config('DEBUG', default=True, cast=bool)

# Allowed Hosts
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=[], cast=list)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.api',  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'opensolar_sync.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'opensolar_sync.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

CRONJOBS = [
    # every hour on the hour, run your sync_projects_to_odoo command
    (
        '0 * * * *',
        'django.core.management.call_command',
        ['sync_projects_to_odoo'],
        {
            # if you have a custom settings module for staging/prod, point to it:
            # 'settings': 'your_project.settings.production'
        }
    ),
]

# Localization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SYNC_SECRET = os.getenv("SYNC_SECRET", "")

