#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

# Ajouter le répertoire du projet au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from rh_management.views.notification_views import get_notifications_dropdown
from rh_management.models import Notification

def test_notification_api():
    print("=== TEST DE L'API NOTIFICATIONS ===")
    
    # Créer une factory de requêtes
    factory = RequestFactory()
    
    # Créer ou récupérer un utilisateur
    try:
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='testuser', password='testpass')
        print(f"Utilisateur: {user.username}")
    except Exception as e:
        print(f"Erreur lors de la création de l'utilisateur: {e}")
        return
    
    # Créer une notification de test si aucune n'existe
    try:
        if not Notification.objects.filter(user=user).exists():
            Notification.objects.create(
                user=user,
                title="Test Notification",
                message="Ceci est une notification de test",
                color="primary",
                icon="fa-bell",
                url="#"
            )
            print("Notification de test créée")
        else:
            print(f"Notifications existantes: {Notification.objects.filter(user=user).count()}")
    except Exception as e:
        print(f"Erreur lors de la création de la notification: {e}")
        return
    
    # Créer une requête simulée
    request = factory.get('/api/notifications/dropdown/')
    request.user = user
    
    try:
        # Appeler la vue
        response = get_notifications_dropdown(request)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            import json
            content = json.loads(response.content.decode('utf-8'))
            print(f"Réponse JSON: {content}")
            print("✅ L'API fonctionne correctement")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(f"Contenu: {response.content.decode('utf-8')}")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'appel de l'API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_notification_api()
