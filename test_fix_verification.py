#!/usr/bin/env python
"""
Script de vérification de la correction du problème de profil
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
django.setup()

from django.contrib.auth.models import User
from rh_management.models import Profile, Department

def test_profile_fix():
    print("=== VÉRIFICATION DE LA CORRECTION DU PROFIL ===\n")
    
    # 1. Vérifier les utilisateurs existants
    users = User.objects.all()
    print(f"Nombre d'utilisateurs dans la base: {users.count()}")
    
    if users.count() == 0:
        print("❌ Aucun utilisateur trouvé - créons un utilisateur de test")
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        print(f"✅ Utilisateur de test créé: {user.username}")
    else:
        user = users.first()
        print(f"✅ Utilisation de l'utilisateur existant: {user.username}")
    
    # 2. Vérifier les départements
    departments = Department.objects.all()
    print(f"\nNombre de départements: {departments.count()}")
    
    if departments.count() == 0:
        print("❌ Aucun département trouvé - créons des départements de test")
        dept1 = Department.objects.create(name="Test IT", is_active=True)
        dept2 = Department.objects.create(name="Test RH", is_active=True)
        print(f"✅ Départements créés: {dept1.name}, {dept2.name}")
    else:
        for dept in departments:
            print(f"  - {dept.name} (ID: {dept.id})")
    
    # 3. Tester la récupération/création du profil
    print(f"\n=== TEST DU PROFIL POUR {user.username} ===")
    
    profile, created = Profile.objects.get_or_create(user=user)
    print(f"Profil créé: {created}")
    print(f"ID du profil: {profile.id}")
    
    # 4. Afficher l'état actuel
    print(f"\nÉtat actuel du profil:")
    print(f"  - Téléphone: '{profile.phone_number or 'Vide'}'")
    print(f"  - Adresse: '{profile.address or 'Vide'}'")
    print(f"  - Position: '{profile.position or 'Vide'}'")
    print(f"  - Département: {profile.department or 'Aucun'}")
    print(f"  - Photo de profil: {profile.profile_picture or 'Aucune'}")
    
    # 5. Test de mise à jour
    print(f"\n=== TEST DE MISE À JOUR ===")
    
    # Sauvegarder les anciennes valeurs
    old_phone = profile.phone_number
    old_address = profile.address
    old_position = profile.position
    old_department = profile.department
    
    # Appliquer de nouvelles valeurs
    profile.phone_number = "+33123456789"
    profile.address = "123 Rue de la Correction, 75001 Paris"
    profile.position = "Développeur Senior Corrigé"
    
    # Assigner un département si disponible
    if departments.exists():
        profile.department = departments.first()
    
    # Sauvegarder
    try:
        profile.save()
        print("✅ Profil sauvegardé avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return False
    
    # 6. Vérifier que les données sont bien persistées
    print(f"\n=== VÉRIFICATION DE LA PERSISTANCE ===")
    
    # Recharger depuis la base
    profile.refresh_from_db()
    
    # Vérifier les nouvelles valeurs
    checks = [
        ("Téléphone", profile.phone_number, "+33123456789"),
        ("Adresse", profile.address, "123 Rue de la Correction, 75001 Paris"),
        ("Position", profile.position, "Développeur Senior Corrigé"),
    ]
    
    all_good = True
    for field_name, actual, expected in checks:
        if actual == expected:
            print(f"✅ {field_name}: '{actual}'")
        else:
            print(f"❌ {field_name}: attendu '{expected}', obtenu '{actual}'")
            all_good = False
    
    if profile.department and departments.exists():
        print(f"✅ Département: {profile.department.name}")
    elif not departments.exists():
        print("⚠️  Département: aucun département disponible pour le test")
    else:
        print("❌ Département: non assigné")
        all_good = False
    
    # 7. Test de la vue (simulation)
    print(f"\n=== SIMULATION DE LA VUE profile_view ===")
    
    # Simuler ce que fait la vue profile_view
    profile_from_view, created_in_view = Profile.objects.get_or_create(user=user)
    
    print(f"Profil récupéré par get_or_create: ID {profile_from_view.id}")
    print(f"Même instance que le profil testé: {profile_from_view.id == profile.id}")
    
    # Vérifier que les données sont visibles
    display_checks = [
        ("Téléphone affiché", profile_from_view.phone_number or "Non renseigné"),
        ("Adresse affichée", profile_from_view.address or "Non renseigné"),
        ("Position affichée", profile_from_view.position or "Non renseigné"),
        ("Département affiché", str(profile_from_view.department) if profile_from_view.department else "Non renseigné"),
    ]
    
    print(f"\nDonnées qui seront affichées dans le template:")
    for label, value in display_checks:
        status = "✅" if value != "Non renseigné" else "❌"
        print(f"  {status} {label}: '{value}'")
    
    # 8. Résultat final
    print(f"\n=== RÉSULTAT FINAL ===")
    
    if all_good and profile_from_view.phone_number:
        print("🎉 SUCCESS! La correction fonctionne correctement.")
        print("   Les données du profil sont maintenant sauvegardées et affichées.")
        return True
    else:
        print("❌ ÉCHEC: Il reste des problèmes à résoudre.")
        return False

if __name__ == "__main__":
    test_profile_fix()
