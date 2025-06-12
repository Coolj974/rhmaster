#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings
from django.urls import reverse
from django.test import Client

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

def test_url_fix():
    """Tester si l'URL notifications_page fonctionne maintenant"""
    try:
        # Test avec reverse pour vérifier si l'URL existe
        url_notifications = reverse('notifications')
        print(f"✅ URL 'notifications' trouvée: {url_notifications}")
        
        url_notifications_page = reverse('notifications_page')
        print(f"✅ URL 'notifications_page' trouvée: {url_notifications_page}")
        
        # Test avec un client de test
        client = Client()
        
        # Test d'accès sans authentification (devrait rediriger vers login)
        response = client.get('/notifications/')
        print(f"✅ Status code pour /notifications/: {response.status_code}")
        
        if response.status_code == 302:
            print(f"✅ Redirection vers: {response.url}")
        
        print("\n🎉 Toutes les vérifications URL sont passées avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test URL: {e}")
        return False

if __name__ == "__main__":
    test_url_fix()
