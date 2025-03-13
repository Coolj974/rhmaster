"""
Django settings for hr_tool project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os  # ✅ Ajoute cet import
from pathlib import Path
LOGOUT_REDIRECT_URL = "/login/"

# Définition de BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# ... autres configurations ...
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ... autres configurations ...

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))  # ⚠️ Si 465, on active SSL

# Assurez-vous que la bonne variable d'environnement est utilisée
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True').lower() == 'true'  # Correction

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'cyberun.rh@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'mkhw lmiw wbyw vokl')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-(ldbt*&5n8)v_qai_-tlay1r-ini25nloi2cb(sgnv#$kl*k$#'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"  # Mettre "http" si en local

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',  # Ajoutez cette ligne
    'crispy_bootstrap4',


    # Ajoutez ici votre application
    'rh_management',
    'rh_management.templatetags',  # Ajoutez cette ligne pour reconnaître les templatetags
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hr_tool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = 'hr_tool.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.mysql',
#        'NAME': os.getenv('MYSQL_DATABASE', 'your_database_name'),
#        'USER': os.getenv('MYSQL_USER', 'your_database_user'),
#        'PASSWORD': os.getenv('MYSQL_PASSWORD', 'your_database_password'),
#        'HOST': os.getenv('MYSQL_HOST', 'localhost'),
#        'PORT': os.getenv('MYSQL_PORT', '3306'),
#    }
#}


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Redirections après connexion
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = "/login/"

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'Indian/Reunion'

USE_I18N = True

USE_TZ = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB (si tu gères des fichiers volumineux)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuration des pages d'erreurs personnalisées
ERROR_404_TEMPLATE = 'errors/404.html'
ERROR_500_TEMPLATE = 'errors/500.html'
ERROR_403_TEMPLATE = 'errors/403.html'
ERROR_400_TEMPLATE = 'errors/400.html'

# Configurer Django pour rediriger automatiquement vers les URLs avec slash final
APPEND_SLASH = True
