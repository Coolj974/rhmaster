#!/usr/bin/env python
"""
Script pour créer la table django_session manquante dans la base de données.
"""

import os
import sys
import subprocess

# Configuration de l'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

def apply_session_migrations():
    """Applique spécifiquement les migrations pour l'application sessions."""
    print("Application des migrations pour créer la table django_session...")
    try:
        # Exécuter la commande pour migrer l'application sessions
        result = subprocess.run([sys.executable, 'manage.py', 'migrate', 'sessions'], 
                               capture_output=True, text=True, check=True)
        print("Résultat:")
        print(result.stdout)
        print("La table django_session a été créée avec succès!")
        return True
    except subprocess.CalledProcessError as e:
        print("ERREUR lors de l'application des migrations:")
        print(e.stdout)
        print(e.stderr)
        return False

if __name__ == "__main__":
    success = apply_session_migrations()
    sys.exit(0 if success else 1)
