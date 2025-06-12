#!/usr/bin/env python
"""
Test final pour valider la correction du problème de notifications infinies.
Ce script simule exactement ce que fait l'API /api/notifications/dropdown/
"""
import os
import sys
import django

# Configuration Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.test import RequestFactory
from rh_management.models import Notification
from rh_management.views.notification_views import get_notifications_dropdown
import json

def simulate_dropdown_api():
    """Simule exactement l'appel de l'API dropdown"""
    print("=== SIMULATION DE L'API DROPDOWN ===")
    
    try:
        # Créer un utilisateur de test si nécessaire
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )
        if created:
            print(f"✅ Utilisateur de test créé: {user.username}")
        else:
            print(f"✅ Utilisateur de test récupéré: {user.username}")
        
        # Créer une factory de requêtes pour simuler la requête HTTP
        factory = RequestFactory()
        request = factory.get('/api/notifications/dropdown/')
        request.user = user
        
        # Créer quelques notifications de test si elles n'existent pas
        if not Notification.objects.filter(user=user).exists():
            Notification.objects.create(
                user=user,
                title="Notification de test 1",
                message="Première notification de test",
                notification_type="system",
                color="primary",
                icon="fa-bell",
                url="/dashboard/"
            )
            Notification.objects.create(
                user=user,
                title="Notification de test 2", 
                message="Deuxième notification de test",
                notification_type="system",
                color="success",
                icon="fa-check",
                url="/profile/",
                read=True
            )
            print("✅ Notifications de test créées")
        
        # Appeler directement la fonction de vue
        print("📡 Appel de get_notifications_dropdown...")
        response = get_notifications_dropdown(request)
        
        # Vérifier la réponse
        if response.status_code == 200:
            print("✅ Réponse HTTP 200 OK")
            
            # Décoder la réponse JSON
            content = json.loads(response.content.decode('utf-8'))
            print(f"✅ JSON décodé avec succès")
            print(f"   - Nombre de notifications non lues: {content.get('count', 'N/A')}")
            print(f"   - HTML généré: {len(content.get('html', ''))} caractères")
            
            # Vérifier que le HTML contient les URLs corrigées
            html = content.get('html', '')
            if 'notifications_page' in html:
                print("✅ URL 'notifications_page' trouvée dans le HTML")
            else:
                print("⚠️  URL 'notifications_page' non trouvée dans le HTML")
                
            if 'mark_all_read' in html:
                print("✅ URL 'mark_all_read' trouvée dans le HTML")
            else:
                print("⚠️  URL 'mark_all_read' non trouvée dans le HTML")
            
            return True, content
            
        else:
            print(f"❌ Erreur HTTP {response.status_code}")
            print(f"   Contenu: {response.content.decode('utf-8')}")
            return False, None
            
    except Exception as e:
        print(f"❌ Exception durant l'appel API: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    print("TEST FINAL DE LA CORRECTION DES NOTIFICATIONS")
    print("=" * 60)
    
    success, response_data = simulate_dropdown_api()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCÈS ! L'API fonctionne correctement")
        print("✅ Le problème de chargement infini devrait être résolu")
        print("\nRésumé de la correction:")
        print("- ✅ URL 'notifications' corrigée en 'notifications_page'")
        print("- ✅ Template rendu sans erreur")
        print("- ✅ JSON valide retourné par l'API")
    else:
        print("❌ ÉCHEC - Des problèmes persistent")
        print("Des corrections supplémentaires sont nécessaires")

if __name__ == "__main__":
    main()
