import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

try:
    from django.urls import reverse
    url = reverse('notifications_page')
    print(f"SUCCESS: URL notifications_page found: {url}")
except Exception as e:
    print(f"ERROR: {e}")
