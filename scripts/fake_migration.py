#!/usr/bin/env python
"""
Script pour marquer une migration problématique comme "fake" 
et ajouter manuellement les champs nécessaires à la base de données.
Cette approche contourne le mécanisme de migration standard de Django
qui échoue à cause des problèmes de format de date.
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

# Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialiser Django pour pouvoir utiliser ses modèles si nécessaire
import django
django.setup()

# Chemin vers la base de données SQLite
db_path = Path(__file__).parents[1] / 'db.sqlite3'

def fake_migration():
    """
    Applique manuellement les modifications de la migration 0026 et la marque comme appliquée
    """
    print(f"Connexion à la base de données SQLite: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Désactiver les contraintes de clés étrangères
    cursor.execute("PRAGMA foreign_keys=off;")
    
    try:
        # Démarrer une transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Ajouter le champ refacturable à la table ExpenseReport s'il n'existe pas déjà
        # D'abord vérifier si la colonne existe
        cursor.execute("PRAGMA table_info(rh_management_expensereport);")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'refacturable' not in columns:
            print("Ajout du champ 'refacturable' à la table ExpenseReport...")
            cursor.execute("""
                ALTER TABLE rh_management_expensereport 
                ADD COLUMN refacturable BOOLEAN DEFAULT 0;
            """)
            print("Champ ajouté avec succès.")
        else:
            print("Le champ 'refacturable' existe déjà dans la table ExpenseReport.")
            
        # 2. Ajouter les champs half_day et half_day_period à LeaveRequest s'ils n'existent pas déjà
        cursor.execute("PRAGMA table_info(rh_management_leaverequest);")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'half_day' not in columns:
            print("Ajout du champ 'half_day' à la table LeaveRequest...")
            cursor.execute("""
                ALTER TABLE rh_management_leaverequest
                ADD COLUMN half_day BOOLEAN DEFAULT 0;
            """)
            print("Champ ajouté avec succès.")
        else:
            print("Le champ 'half_day' existe déjà dans la table LeaveRequest.")
        
        if 'half_day_period' not in columns:
            print("Ajout du champ 'half_day_period' à la table LeaveRequest...")
            cursor.execute("""
                ALTER TABLE rh_management_leaverequest
                ADD COLUMN half_day_period VARCHAR(10) DEFAULT 'morning';
            """)
            print("Champ ajouté avec succès.")
        else:
            print("Le champ 'half_day_period' existe déjà dans la table LeaveRequest.")
            
        # 3. Marquer les migrations concernées comme appliquées
        print("Vérification des migrations déjà enregistrées...")
        cursor.execute("SELECT name FROM django_migrations WHERE app='rh_management';")
        applied_migrations = [row[0] for row in cursor.fetchall()]
        
        migrations_to_fake = [
            '0026_alter_expensereport_options_and_more',
            '0027_fix_datetime_values'
        ]
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for migration in migrations_to_fake:
            if migration not in applied_migrations:
                print(f"Marquage de la migration '{migration}' comme appliquée...")
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES (?, ?, ?);
                """, ('rh_management', migration, current_time))
                print(f"Migration '{migration}' marquée avec succès.")
            else:
                print(f"La migration '{migration}' est déjà marquée comme appliquée.")
                
        # Valider les modifications
        cursor.execute("COMMIT;")
        print("Toutes les modifications ont été validées avec succès.")
        
    except sqlite3.Error as e:
        # En cas d'erreur, annuler la transaction
        cursor.execute("ROLLBACK;")
        print(f"ERREUR: {e}")
        print("Toutes les modifications ont été annulées.")
        return False
    finally:
        # Réactiver les contraintes de clés étrangères
        cursor.execute("PRAGMA foreign_keys=on;")
        conn.close()
    
    return True

if __name__ == "__main__":
    success = fake_migration()
    
    if success:
        print("\n=== MIGRATION SIMULÉE AVEC SUCCÈS ===")
        print("Vous pouvez maintenant exécuter:")
        print("python manage.py migrate --fake")
        print("pour terminer le processus de migration.")
    else:
        print("\n=== ÉCHEC DE LA SIMULATION DE MIGRATION ===")
        print("Veuillez vérifier les erreurs ci-dessus.")
    
    sys.exit(0 if success else 1)
