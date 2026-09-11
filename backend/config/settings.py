import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('Set DJANGO_SECRET_KEY, or DJANGO_DEBUG=true for local development.')
    SECRET_KEY = 'local-only-repopilot-development'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'corsheaders', 'rest_framework', 'repositories', 'coding_tasks', 'execution']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': dj_database_url.parse(os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}'), conn_max_age=0)}
if not DEBUG and DATABASES['default']['ENGINE'].endswith('sqlite3'):
    raise RuntimeError('Production requires PostgreSQL DATABASE_URL.')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.SessionAuthentication'], 'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'], 'DEFAULT_THROTTLE_CLASSES':['rest_framework.throttling.UserRateThrottle'], 'DEFAULT_THROTTLE_RATES':{'user':'120/min', 'login':'10/min'}}
CORS_ALLOWED_ORIGINS = os.getenv('FRONTEND_ORIGINS','http://localhost:3000').split(',')
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
CELERY_BROKER_URL = os.getenv('REDIS_URL','redis://localhost:6379/0')
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = 1000
CELERY_TASK_TIME_LIMIT = 1100
CELERY_BROKER_TRANSPORT_OPTIONS = {'visibility_timeout':1200}
AI_API_KEY = os.getenv('AI_API_KEY','')
AI_BASE_URL = os.getenv('AI_BASE_URL','https://api.deepseek.com')
AI_MODEL = os.getenv('AI_MODEL','deepseek-flash')
AI_PRICE_INPUT = os.getenv('AI_PRICE_INPUT','0.30')
AI_PRICE_CACHED = os.getenv('AI_PRICE_CACHED','0.006')
AI_PRICE_OUTPUT = os.getenv('AI_PRICE_OUTPUT','1.20')
E2B_API_KEY = os.getenv('E2B_API_KEY','')
E2B_TEMPLATE = os.getenv('E2B_TEMPLATE','')
LIVE_EXECUTION_ENABLED = os.getenv('LIVE_EXECUTION_ENABLED','false').lower() == 'true'
GITHUB_APP_ID = os.getenv('GITHUB_APP_ID','')
GITHUB_APP_PRIVATE_KEY = os.getenv('GITHUB_APP_PRIVATE_KEY','').replace('\\n','\n')
GITHUB_INSTALLATION_ID = os.getenv('GITHUB_INSTALLATION_ID','')
PUBLISH_ENABLED = os.getenv('PUBLISH_ENABLED','false').lower() == 'true'

# Cumulative recorded API estimate per local account; no automatic reset.
AI_ACCOUNT_BUDGET = os.getenv("AI_ACCOUNT_BUDGET", "4.00")
AI_MAX_OUTPUT_TOKENS = 2048
