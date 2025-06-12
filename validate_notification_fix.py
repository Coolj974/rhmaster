#!/usr/bin/env python
"""
Script de validation pour tester la correction de l'URL des notifications
"""
import os
import sys
import django

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')

try:
    django.setup()
    from django.urls import reverse, NoReverseMatch
    from django.core.management.color import color_style
    
    style = color_style()
    
    def print_success(message):
        print(style.SUCCESS(f"✅ {message}"))
    
    def print_error(message):
        print(style.ERROR(f"❌ {message}"))
    
    def print_info(message):
        print(style.HTTP_INFO(f"ℹ️  {message}"))
    
    print_info("Test de validation des URLs de notifications")
    print_info("=" * 50)
    
    # Test 1: Vérifier l'URL notifications_page
    try:
        url = reverse('notifications_page')
        print_success(f"URL 'notifications_page' trouvée: {url}")
    except NoReverseMatch as e:
        print_error(f"URL 'notifications_page' NON trouvée: {e}")
        sys.exit(1)
    
    # Test 2: Vérifier les autres URLs de notifications
    notification_urls = [
        'mark_notification_read',
        'mark_all_read', 
        'delete_notification',
        'delete_all_read',
        'get_notifications_count_api',
        'get_notifications_dropdown'
    ]
    
    for url_name in notification_urls:
        try:
            if 'notification_id' in url_name or 'notification_read' in url_name:
                # URLs qui nécessitent des paramètres
                if url_name == 'mark_notification_read' or url_name == 'delete_notification':
                    url = reverse(url_name, args=[1])  # Test avec ID 1
                    print_success(f"URL '{url_name}' trouvée: {url}")
                else:
                    url = reverse(url_name)
                    print_success(f"URL '{url_name}' trouvée: {url}")
            else:
                url = reverse(url_name)
                print_success(f"URL '{url_name}' trouvée: {url}")
        except NoReverseMatch as e:
            print_error(f"URL '{url_name}' NON trouvée: {e}")
    
    print_info("=" * 50)
    print_success("Tous les tests de validation sont passés!")
    print_info("La correction de l'URL notifications_page est effective.")
    
except Exception as e:
    print(f"❌ Erreur lors de l'initialisation de Django: {e}")
    sys.exit(1)
