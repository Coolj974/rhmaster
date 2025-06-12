@echo off
echo ===========================
echo TEST DE LA CORRECTION DES NOTIFICATIONS
echo ===========================

cd /d "c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster"

echo.
echo 1. Test des URLs Django...
python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()
from django.urls import reverse
try:
    url1 = reverse('notifications_page')
    print('✅ notifications_page:', url1)
except Exception as e:
    print('❌ notifications_page:', e)
try:
    url2 = reverse('mark_all_read')
    print('✅ mark_all_read:', url2)
except Exception as e:
    print('❌ mark_all_read:', e)
"

echo.
echo 2. Test du rendu du template...
python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()
from django.template.loader import render_to_string
try:
    context = {'notifications': [], 'unread_count': 0, 'more_notifications': False}
    html = render_to_string('rh_management/notification_dropdown.html', context)
    print('✅ Template rendu avec succès')
    print('   Longueur HTML:', len(html), 'caractères')
    if 'notifications_page' in html:
        print('✅ URL notifications_page trouvée')
    else:
        print('⚠️  URL notifications_page non trouvée')
except Exception as e:
    print('❌ Erreur template:', e)
    import traceback
    traceback.print_exc()
"

echo.
echo 3. Test de l'API avec simulation...
python -c "
import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()
from django.test import RequestFactory
from django.contrib.auth.models import User
from rh_management.views.notification_views import get_notifications_dropdown
import json
try:
    user, created = User.objects.get_or_create(username='test_user')
    factory = RequestFactory()
    request = factory.get('/api/notifications/dropdown/')
    request.user = user
    response = get_notifications_dropdown(request)
    if response.status_code == 200:
        data = json.loads(response.content.decode('utf-8'))
        print('✅ API fonctionne - Status:', response.status_code)
        print('   Count:', data.get('count', 'N/A'))
        print('   HTML length:', len(data.get('html', '')))
    else:
        print('❌ API erreur - Status:', response.status_code)
except Exception as e:
    print('❌ Erreur API:', e)
"

echo.
echo ===========================
echo TEST TERMINÉ
echo ===========================
pause
