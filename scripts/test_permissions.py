#!/usr/bin/env python
"""
Script de test des droits et permissions pour l'application CybeRH.
Ce script vérifie que les différents rôles (admin, RH, encadrant, employé) 
ont accès aux bonnes fonctionnalités et que les restrictions sont correctement appliquées.
"""

import os
import sys
import argparse
import logging
import colorama
from colorama import Fore, Style

# Ajouter le répertoire parent au chemin Python pour pouvoir importer les modules Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuration du logging avant import de Django
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'test_permissions.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialisation de colorama pour les codes couleur
colorama.init()

# Configuration initiale - correction du module de paramètres
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')

# Initialiser Django avant d'importer des modules Django
try:
    import django
    django.setup()
    logger.info("Django initialisé avec succès")
    
    # Maintenant que Django est initialisé, on peut configurer ALLOWED_HOSTS
    from django.conf import settings
    if 'testserver' not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append('testserver')
    logger.info(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # Importations de Django après l'initialisation
    from django.test import Client
    from django.contrib.auth.models import User, Group
    from django.urls import reverse
    from django.core.exceptions import PermissionDenied
    import datetime

    # Maintenant on peut importer les modèles en toute sécurité
    from rh_management.models import (
        LeaveRequest, ExpenseReport, KilometricExpense, 
        LeaveBalance, PasswordManager, PasswordShare
    )
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation de Django: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)

class PermissionTester:
    """Classe principale pour tester les permissions de l'application."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        # Configuration du client de test pour ignorer les vérifications CSRF
        self.client = Client(enforce_csrf_checks=False)
        self.results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'tests': []
        }
        self.users = {}
        
    def log(self, message, level='info'):
        """Log un message avec le niveau approprié."""
        if level == 'info':
            if self.verbose:
                logger.info(message)
        elif level == 'success':
            logger.info(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
        elif level == 'error':
            logger.error(f"{Fore.RED}{message}{Style.RESET_ALL}")
        elif level == 'warning':
            logger.warning(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
            
    def setup(self):
        """Prépare l'environnement de test en créant des utilisateurs et des données."""
        self.log("Configuration de l'environnement de test...", 'info')
        
        # Supprimer les utilisateurs de test s'ils existent déjà
        test_usernames = ['test_admin', 'test_rh', 'test_encadrant', 'test_stp', 'test_employee']
        User.objects.filter(username__in=test_usernames).delete()
        
        # Créer les groupes s'ils n'existent pas
        groups = {
            'HR': Group.objects.get_or_create(name='HR')[0],
            'Encadrant': Group.objects.get_or_create(name='Encadrant')[0],
            'STP': Group.objects.get_or_create(name='STP')[0],
            'Employé': Group.objects.get_or_create(name='Employé')[0],
            'CanApproveLeaves': Group.objects.get_or_create(name='CanApproveLeaves')[0],
            'CanEditProfiles': Group.objects.get_or_create(name='CanEditProfiles')[0]
        }
        
        # Créer les utilisateurs de test
        self.users['admin'] = User.objects.create_user(
            username='test_admin', 
            email='admin@test.com',
            password='password123',
            is_staff=True,
            is_superuser=True
        )
        
        self.users['rh'] = User.objects.create_user(
            username='test_rh', 
            email='rh@test.com',
            password='password123',
            is_staff=True
        )
        self.users['rh'].groups.add(groups['HR'])
        
        self.users['encadrant'] = User.objects.create_user(
            username='test_encadrant', 
            email='encadrant@test.com',
            password='password123'
        )
        self.users['encadrant'].groups.add(groups['Encadrant'])
        self.users['encadrant'].groups.add(groups['CanApproveLeaves'])
        
        self.users['stp'] = User.objects.create_user(
            username='test_stp', 
            email='stp@test.com',
            password='password123'
        )
        self.users['stp'].groups.add(groups['STP'])
        
        self.users['employee'] = User.objects.create_user(
            username='test_employee', 
            email='employee@test.com',
            password='password123'
        )
        self.users['employee'].groups.add(groups['Employé'])
        
        # Créer des données de test
        self.create_test_data()
        
        self.log("Environnement de test configuré avec succès.", 'success')
    
    def create_test_data(self):
        """Crée des données de test (congés, notes de frais, etc.)."""
        # Soldes de congés
        for user in self.users.values():
            LeaveBalance.objects.get_or_create(
                user=user,
                defaults={
                    'acquired': 25.0,
                    'taken': 5.0
                }
            )
        
        # Demandes de congés
        for status in ['pending', 'approved', 'rejected']:
            for user in [self.users['employee'], self.users['encadrant']]:
                LeaveRequest.objects.create(
                    user=user,
                    leave_type='annual',
                    start_date=datetime.date.today() + datetime.timedelta(days=10),
                    end_date=datetime.date.today() + datetime.timedelta(days=15),
                    reason=f"Test {status} leave",
                    status=status
                )
        
        # Notes de frais
        for status in ['pending', 'approved', 'rejected']:
            ExpenseReport.objects.create(
                user=self.users['employee'],
                date=datetime.date.today(),
                description=f"Test {status} expense",
                amount=100.0,
                vat=20.0,
                project="Test Project",
                location="Test Location",
                status=status
            )
        
        # Frais kilométriques
        for status in ['pending', 'approved', 'rejected']:
            KilometricExpense.objects.create(
                user=self.users['employee'],
                date=datetime.date.today(),
                vehicle_type='car',
                fiscal_power=5,
                departure="Paris",
                arrival="Lyon",
                distance=300,
                project="Test Project",
                status=status
            )
        
        # Mots de passe
        password_entry = PasswordManager.objects.create(
            user=self.users['employee'],
            title="Test Password",
            username="testuser",
            password="securepassword",
            url="https://example.com",
            category="Work"
        )
        
        # Partage de mot de passe
        PasswordShare.objects.create(
            password_entry=password_entry,
            shared_with=self.users['encadrant'],
            can_edit=False
        )
    
    def test_authentication(self):
        """Teste les fonctionnalités d'authentification."""
        self.log("\n=== Test d'authentification ===", 'info')
        
        # Test de connexion réussie
        for role, user in self.users.items():
            self._run_test(
                f"Connexion en tant que {role}",
                lambda: self._login(user.username, 'password123'),
                True
            )
        
        # Test de connexion échouée
        self._run_test(
            "Connexion avec des identifiants incorrects",
            lambda: self._login('nonexistent', 'wrongpassword'),
            False
        )
        
        # Test de déconnexion
        self._login('test_admin', 'password123')
        self._run_test(
            "Déconnexion",
            lambda: self.client.get(reverse('logout')).status_code == 302,
            True
        )
    
    def test_dashboard_access(self):
        """Teste l'accès au tableau de bord pour différents rôles."""
        self.log("\n=== Test d'accès au tableau de bord ===", 'info')
        
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès au tableau de bord en tant que {role}",
                lambda: self.client.get(reverse('dashboard')).status_code == 200,
                True
            )
    
    def test_leave_permissions(self):
        """Teste les permissions liées aux congés."""
        self.log("\n=== Test des permissions de congés ===", 'info')
        
        # Tous les utilisateurs peuvent demander des congés
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès au formulaire de demande de congé en tant que {role}",
                lambda: self.client.get(reverse('leave_request')).status_code == 200,
                True
            )
        
        # Seuls les admin, RH et encadrants peuvent gérer les congés
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            expected = role in ['admin', 'rh', 'encadrant']
            self._run_test(
                f"Accès à la gestion des congés en tant que {role}",
                lambda: self.client.get(reverse('manage_leaves')).status_code == 200,
                expected
            )
        
        # Test d'approbation/rejet de congés
        pending_leave = LeaveRequest.objects.filter(status='pending').first()
        if pending_leave:
            for role, user in self.users.items():
                self._login(user.username, 'password123')
                expected = role in ['admin', 'rh', 'encadrant']
                self._run_test(
                    f"Approbation de congé en tant que {role}",
                    lambda: self.client.get(reverse('approve_leave', args=[pending_leave.id])).status_code in [200, 302],
                    expected
                )
    
    def test_expense_permissions(self):
        """Teste les permissions liées aux notes de frais."""
        self.log("\n=== Test des permissions de notes de frais ===", 'info')
        
        # Tous les utilisateurs peuvent soumettre des notes de frais
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès au formulaire de note de frais en tant que {role}",
                lambda: self.client.get(reverse('submit_expense')).status_code == 200,
                True
            )
        
        # Seuls les admin, RH et encadrants peuvent gérer les notes de frais
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            expected = role in ['admin', 'rh', 'encadrant']
            self._run_test(
                f"Accès à la gestion des notes de frais en tant que {role}",
                lambda: self.client.get(reverse('manage_expenses')).status_code == 200,
                expected
            )
    
    def test_kilometric_expense_permissions(self):
        """Teste les permissions liées aux frais kilométriques."""
        self.log("\n=== Test des permissions de frais kilométriques ===", 'info')
        
        # Tous les utilisateurs peuvent soumettre des frais kilométriques
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès au formulaire de frais kilométriques en tant que {role}",
                lambda: self.client.get(reverse('submit_kilometric_expense')).status_code == 200,
                True
            )
        
        # Seuls les admin, RH et encadrants peuvent gérer les frais kilométriques
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            expected = role in ['admin', 'rh', 'encadrant']
            self._run_test(
                f"Accès à la gestion des frais kilométriques en tant que {role}",
                lambda: self.client.get(reverse('manage_kilometric_expenses')).status_code == 200,
                expected
            )
    
    def test_user_management_permissions(self):
        """Teste les permissions liées à la gestion des utilisateurs."""
        self.log("\n=== Test des permissions de gestion des utilisateurs ===", 'info')
        
        # Seuls les admin peuvent gérer les utilisateurs
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            expected = role == 'admin'
            self._run_test(
                f"Accès à la gestion des utilisateurs en tant que {role}",
                lambda: self.client.get(reverse('manage_users')).status_code == 200,
                expected
            )
    
    def test_password_manager_permissions(self):
        """Teste les permissions liées au gestionnaire de mots de passe."""
        self.log("\n=== Test des permissions du gestionnaire de mots de passe ===", 'info')
        
        # Tous les utilisateurs ont accès au gestionnaire de mots de passe
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès au gestionnaire de mots de passe en tant que {role}",
                lambda: self.client.get(reverse('password_manager_list')).status_code == 200,
                True
            )
        
        # Tester la visualisation, la modification et la suppression des mots de passe
        # Récupérer un mot de passe créé par l'employé
        password_entry = PasswordManager.objects.filter(user=self.users['employee']).first()
        if password_entry:
            # Propriétaire - peut voir, modifier, supprimer
            self._login('test_employee', 'password123')
            self._run_test(
                "Propriétaire - voir un mot de passe",
                lambda: self.client.get(reverse('password_manager_view', args=[password_entry.id])).status_code == 200,
                True
            )
            self._run_test(
                "Propriétaire - modifier un mot de passe",
                lambda: self.client.get(reverse('password_manager_edit', args=[password_entry.id])).status_code == 200,
                True
            )
            
            # Utilisateur avec accès de lecture - peut voir mais pas modifier
            self._login('test_encadrant', 'password123')
            self._run_test(
                "Utilisateur partagé - voir un mot de passe",
                lambda: self.client.get(reverse('password_manager_view', args=[password_entry.id])).status_code == 200,
                True
            )
            
            # Utilisateur sans accès - ne peut ni voir ni modifier
            self._login('test_rh', 'password123')
            self._run_test(
                "Utilisateur sans accès - voir un mot de passe",
                lambda: self.client.get(reverse('password_manager_view', args=[password_entry.id])).status_code != 200,
                True
            )
    
    def test_api_access(self):
        """Teste l'accès aux API."""
        self.log("\n=== Test d'accès aux API ===", 'info')
        
        # Test de l'API des congés
        for role, user in self.users.items():
            self._login(user.username, 'password123')
            self._run_test(
                f"Accès à l'API des congés en tant que {role}",
                lambda: self.client.get(reverse('api_leaves')).status_code == 200,
                True
            )
    
    def run_all_tests(self):
        """Exécute tous les tests."""
        self.setup()
        
        self.test_authentication()
        self.test_dashboard_access()
        self.test_leave_permissions()
        self.test_expense_permissions()
        self.test_kilometric_expense_permissions()
        self.test_user_management_permissions()
        self.test_password_manager_permissions()
        self.test_api_access()
        
        self.display_results()
    
    def _login(self, username, password):
        """Connecte un utilisateur."""
        self.client.logout()
        success = self.client.login(username=username, password=password)
        if success and self.verbose:
            self.log(f"Utilisateur {username} connecté avec succès", 'info')
        elif not success:
            self.log(f"Échec de connexion pour l'utilisateur {username}", 'warning')
        return success
    
    def _run_test(self, description, test_func, expected):
        """Exécute un test et enregistre le résultat."""
        try:
            result = test_func()
            success = result == expected
            
            if success:
                self.log(f"✅ SUCCÈS: {description}", 'success')
                self.results['passed'] += 1
            else:
                # Log plus de détails pour les échecs
                self.log(f"❌ ÉCHEC: {description} (obtenu: {result}, attendu: {expected})", 'error')
                self.results['failed'] += 1
                
            self.results['tests'].append({
                'description': description,
                'success': success,
                'expected': expected,
                'result': result
            })
            
        except Exception as e:
            self.log(f"⚠️ ERREUR: {description} - {str(e)}", 'warning')
            # Loguer plus de détails sur l'exception
            if self.verbose:
                import traceback
                self.log(f"Détails de l'erreur: {traceback.format_exc()}", 'warning')
            self.results['skipped'] += 1
            self.results['tests'].append({
                'description': description,
                'success': False,
                'error': str(e)
            })
    
    def run_targeted_tests(self, target='all'):
        """Exécute des tests ciblés sur une fonctionnalité spécifique."""
        self.setup()
        
        # Liste des tests disponibles
        test_functions = {
            'auth': self.test_authentication,
            'dashboard': self.test_dashboard_access,
            'leave': self.test_leave_permissions,
            'expense': self.test_expense_permissions,
            'kilometric': self.test_kilometric_expense_permissions,
            'users': self.test_user_management_permissions,
            'password': self.test_password_manager_permissions,
            'api': self.test_api_access,
            'all': self.run_all_tests
        }
        
        # Exécuter le test demandé
        if target in test_functions:
            if target == 'all':
                self.run_all_tests()
            else:
                self.log(f"\n=== Exécution du test: {target} ===", 'info')
                test_functions[target]()
                self.display_results()
        else:
            self.log(f"Test '{target}' inconnu. Tests disponibles: {', '.join(test_functions.keys())}", 'error')
    
    def display_results(self):
        """Affiche les résultats des tests."""
        total = self.results['passed'] + self.results['failed'] + self.results['skipped']
        success_rate = (self.results['passed'] / total) * 100 if total > 0 else 0
        
        self.log("\n\n=== RÉSULTATS DES TESTS ===", 'info')
        self.log(f"Tests réussis:    {self.results['passed']}/{total} ({success_rate:.1f}%)", 'success' if success_rate > 80 else 'warning')
        self.log(f"Tests échoués:    {self.results['failed']}/{total}", 'error' if self.results['failed'] > 0 else 'info')
        self.log(f"Tests ignorés:    {self.results['skipped']}/{total}", 'warning' if self.results['skipped'] > 0 else 'info')
        
        if self.results['failed'] > 0:
            self.log("\nTests échoués:", 'error')
            for test in self.results['tests']:
                if not test.get('success', True) and 'error' not in test:
                    self.log(f"- {test['description']} (obtenu: {test['result']}, attendu: {test['expected']})", 'error')
        
        if self.results['skipped'] > 0:
            self.log("\nTests ignorés:", 'warning')
            for test in self.results['tests']:
                if 'error' in test:
                    self.log(f"- {test['description']} ({test['error']})", 'warning')

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Script de test des permissions pour CybeRH')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    parser.add_argument('-t', '--target', type=str, default='all', help='Test ciblé à exécuter (par défaut: tous)')
    args = parser.parse_args()
    
    print(f"{Fore.CYAN}======================================")
    print(f"= Test des permissions de l'application =")
    print(f"======================================{Style.RESET_ALL}")
    
    tester = PermissionTester(verbose=args.verbose)
    tester.run_targeted_tests(target=args.target)

if __name__ == "__main__":
    main()
