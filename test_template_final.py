import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from django.template.loader import render_to_string
from django.contrib.auth.models import User
from rh_management.models import Notification

print("=== TEST COMPLET DU TEMPLATE ===")

# Test 1: Template vide
print("\n1. Test avec contexte vide:")
context_empty = {'notifications': [], 'unread_count': 0, 'more_notifications': False}
html_empty = render_to_string('rh_management/notification_dropdown.html', context_empty)
print(f"✅ Rendu réussi - {len(html_empty)} caractères")

# Test 2: Template avec données factices
print("\n2. Test avec données factices:")

class FakeNotification:
    def __init__(self):
        self.id = 1
        self.title = "Test Notification"
        self.url = "/test/"
        self.read = False
        self.color = "primary"
        self.icon = "fa-bell"
        self.created_at = None

context_with_data = {
    'notifications': [FakeNotification()],
    'unread_count': 1,
    'more_notifications': True
}

try:
    html_with_data = render_to_string('rh_management/notification_dropdown.html', context_with_data)
    print(f"✅ Rendu réussi - {len(html_with_data)} caractères")
    
    # Vérifier les URLs
    if 'notifications_page' in html_with_data:
        print("✅ URL 'notifications_page' trouvée")
    else:
        print("❌ URL 'notifications_page' non trouvée")
        
    if 'mark_all_read' in html_with_data:
        print("✅ URL 'mark_all_read' trouvée")
    else:
        print("❌ URL 'mark_all_read' non trouvée")
        
    print("\nHTML généré (extrait):")
    print(html_with_data[:300] + "..." if len(html_with_data) > 300 else html_with_data)
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST TERMINÉ ===")
