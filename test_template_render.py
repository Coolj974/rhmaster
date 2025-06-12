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

from django.template.loader import render_to_string
from django.template import Context, Template
from django.contrib.auth.models import User
from rh_management.models import Notification

def test_template_rendering():
    print("=== TEST DU RENDU TEMPLATE ===")
    
    try:
        # Créer ou récupérer un utilisateur
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='testuser', password='testpass')
        print(f"Utilisateur: {user.username}")
        
        # Créer des notifications de test
        if not Notification.objects.filter(user=user).exists():
            Notification.objects.create(
                user=user,
                title="Test Notification 1",
                message="Première notification de test",
                color="primary",
                icon="fa-bell",
                url="#"
            )
            Notification.objects.create(
                user=user,
                title="Test Notification 2", 
                message="Deuxième notification de test",
                color="success",
                icon="fa-check",
                url="#",
                read=True
            )
            print("Notifications de test créées")
        
        # Récupérer les notifications
        notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        unread_count = notifications.filter(read=False).count()
        more_notifications = Notification.objects.filter(user=user).count() > 5
        
        print(f"Notifications trouvées: {notifications.count()}")
        print(f"Non lues: {unread_count}")
        
        # Préparer le contexte
        context = {
            'notifications': notifications,
            'unread_count': unread_count,
            'more_notifications': more_notifications,
        }
        
        # Essayer de rendre le template
        html = render_to_string('rh_management/notification_dropdown.html', context)
        print("✅ Template rendu avec succès")
        print(f"Longueur HTML: {len(html)} caractères")
        
        # Vérifier qu'il n'y a pas d'erreurs dans le HTML
        if "notifications_page" in html:
            print("✅ URL 'notifications_page' trouvée")
        else:
            print("❌ URL 'notifications_page' introuvable")
            
        if "mark_all_read" in html:
            print("✅ URL 'mark_all_read' trouvée")
        else:
            print("❌ URL 'mark_all_read' introuvable")
            
        return html
        
    except Exception as e:
        print(f"❌ Erreur lors du rendu du template: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    html = test_template_rendering()
    if html:
        print("\n=== APERÇU DU HTML GÉNÉRÉ ===")
        print(html[:500] + "..." if len(html) > 500 else html)
