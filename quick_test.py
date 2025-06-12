#!/usr/bin/env python
"""
Test simple et rapide de la correction
"""
import os
import sys
import django

# Ajouter le répertoire du projet au path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from django.contrib.auth.models import User
from rh_management.models import Profile, Department

def quick_test():
    print("🔍 Test rapide de la correction du profil...")
    
    # Récupérer ou créer un utilisateur de test
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@test.com',
            'first_name': 'Admin',
            'last_name': 'Test',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password('admin123')
        user.save()
        print(f"✅ Utilisateur créé: {user.username}")
    else:
        print(f"✅ Utilisateur trouvé: {user.username}")
    
    # Test du profil
    profile, profile_created = Profile.objects.get_or_create(user=user)
    print(f"✅ Profil {'créé' if profile_created else 'trouvé'}: ID {profile.id}")
    
    # Mettre à jour avec des données de test
    profile.phone_number = "+33987654321"
    profile.address = "456 Avenue de la Correction"
    profile.position = "Administrateur Système"
    profile.save()
    
    print(f"✅ Données mises à jour:")
    print(f"   📞 Téléphone: {profile.phone_number}")
    print(f"   🏠 Adresse: {profile.address}")
    print(f"   💼 Position: {profile.position}")
    
    # Vérifier la récupération (comme le fait la vue)
    retrieved_profile = Profile.objects.get(user=user)
    success = (
        retrieved_profile.phone_number == "+33987654321" and
        retrieved_profile.address == "456 Avenue de la Correction" and
        retrieved_profile.position == "Administrateur Système"
    )
    
    if success:
        print("🎉 SUCCESS! Les données sont bien sauvegardées et récupérées.")
        print("   Votre page de profil devrait maintenant afficher les bonnes informations.")
    else:
        print("❌ ÉCHEC: Les données ne sont pas correctement sauvegardées.")
    
    return success

if __name__ == "__main__":
    try:
        quick_test()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
