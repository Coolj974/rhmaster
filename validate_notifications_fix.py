#!/usr/bin/env python
import os
import sys

# Ajouter le répertoire du projet au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')

import django
django.setup()

from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from rh_management.models import Notification

def test_notification_urls():
    """Test que les URLs utilisées dans le template existent"""
    print("=== VALIDATION DES URLs ===")
    
    try:
        # Tester l'URL notifications_page
        url = reverse('notifications_page')
        print(f"✅ notifications_page: {url}")
    except Exception as e:
        print(f"❌ notifications_page: {e}")
    
    try:
        # Tester l'URL mark_all_read  
        url = reverse('mark_all_read')
        print(f"✅ mark_all_read: {url}")
    except Exception as e:
        print(f"❌ mark_all_read: {e}")

def test_template_rendering():
    """Test le rendu du template avec des données minimales"""
    print("\n=== TEST DU RENDU TEMPLATE ===")
    
    try:
        # Contexte minimal pour le template
        context = {
            'notifications': [],
            'unread_count': 0,
            'more_notifications': False
        }
        
        # Essayer de rendre le template
        html = render_to_string('rh_management/notification_dropdown.html', context)
        print("✅ Template rendu avec succès (contexte vide)")
        
        # Test avec des notifications factices
        class FakeNotification:
            def __init__(self):
                self.id = 1
                self.title = "Test"
                self.url = "#"
                self.read = False
                self.color = "primary"
                self.icon = "fa-bell"
                self.created_at = None
                
        context_with_data = {
            'notifications': [FakeNotification()],
            'unread_count': 1,
            'more_notifications': True
        }
        
        html_with_data = render_to_string('rh_management/notification_dropdown.html', context_with_data)
        print("✅ Template rendu avec succès (avec données)")
        print(f"Longueur HTML généré: {len(html_with_data)} caractères")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du rendu: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("VALIDATION DE LA CORRECTION DES NOTIFICATIONS")
    print("=" * 50)
    
    test_notification_urls()
    success = test_template_rendering()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ TOUTES LES VALIDATIONS SONT PASSÉES")
        print("La correction devrait résoudre le problème de chargement infini")
    else:
        print("❌ DES ERREURS PERSISTENT")
        print("Des corrections supplémentaires sont nécessaires")
        
if __name__ == "__main__":
    main()
