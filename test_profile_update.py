#!/usr/bin/env python
"""
Script de test pour vérifier la mise à jour du profil utilisateur
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from rh_management.models import Profile, Department

def test_profile_update():
    """Test de mise à jour du profil utilisateur"""
    print("🧪 Test de mise à jour du profil utilisateur")
    print("=" * 50)
    
    # Créer un utilisateur de test
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    # Créer ou récupérer le profil
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Créer un département de test
    dept, created = Department.objects.get_or_create(
        name='Test Département',
        defaults={'is_active': True}
    )
    
    print(f"✅ Utilisateur: {user.username}")
    print(f"✅ Profil créé: {created}")
    print(f"✅ Département: {dept.name}")
    
    # Valeurs avant mise à jour
    print("\n📋 Valeurs AVANT mise à jour:")
    print(f"   Téléphone: {profile.phone_number or 'Non défini'}")
    print(f"   Adresse: {profile.address or 'Non défini'}")
    print(f"   Poste: {profile.position or 'Non défini'}")
    print(f"   Département: {profile.department or 'Non défini'}")
    print(f"   Thème: {profile.theme_preference}")
    print(f"   Notifications: {profile.notifications_enabled}")
    
    # Simuler une mise à jour
    client = Client()
    client.force_login(user)
    
    # Données de test
    update_data = {
        'username': user.username,
        'email': user.email,
        'first_name': 'TestUpdated',
        'last_name': 'UserUpdated',
        'phone': '+33123456789',
        'address': '123 Rue de Test, 75001 Paris',
        'position': 'Développeur Senior',
        'department': str(dept.id),
    }
    
    # Effectuer la mise à jour
    response = client.post('/profile/update/', update_data)
    
    # Recharger le profil depuis la base
    profile.refresh_from_db()
    user.refresh_from_db()
    
    print(f"\n🔄 Réponse HTTP: {response.status_code}")
    print(f"🔄 Redirection vers: {response.get('Location', 'Aucune')}")
    
    # Valeurs après mise à jour
    print("\n📋 Valeurs APRÈS mise à jour:")
    print(f"   Nom: {user.first_name} {user.last_name}")
    print(f"   Téléphone: {profile.phone_number or 'Non défini'}")
    print(f"   Adresse: {profile.address or 'Non défini'}")
    print(f"   Poste: {profile.position or 'Non défini'}")
    print(f"   Département: {profile.department or 'Non défini'}")
    
    # Vérifications
    print("\n✅ RÉSULTATS DES TESTS:")
    tests = [
        ('Prénom mis à jour', user.first_name == 'TestUpdated'),
        ('Nom mis à jour', user.last_name == 'UserUpdated'),
        ('Téléphone mis à jour', profile.phone_number == '+33123456789'),
        ('Adresse mise à jour', profile.address == '123 Rue de Test, 75001 Paris'),
        ('Poste mis à jour', profile.position == 'Développeur Senior'),
        ('Département mis à jour', profile.department == dept),
        ('Redirection correcte', response.status_code == 302),
    ]
    
    all_passed = True
    for test_name, result in tests:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n🎯 RÉSULTAT GLOBAL: {'✅ TOUS LES TESTS PASSÉS' if all_passed else '❌ CERTAINS TESTS ONT ÉCHOUÉ'}")
    
    return all_passed

if __name__ == '__main__':
    try:
        success = test_profile_update()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ ERREUR LORS DU TEST: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
