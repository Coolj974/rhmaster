#!/usr/bin/env python
"""
Script pour ajouter la colonne 'updated_at' manquante à la table ExpenseReport.
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

# Configuration de l'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

# Chemin vers la base de données SQLite
db_path = Path(project_dir) / 'db.sqlite3'

def add_updated_at_field():
    """Ajoute la colonne 'updated_at' à la table ExpenseReport."""
    print(f"Connexion à la base de données: {db_path}")
    
    try:
        # Se connecter à la base de données SQLite
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Vérifier si la colonne 'updated_at' existe déjà
        cursor.execute("PRAGMA table_info(rh_management_expensereport);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'updated_at' not in columns:
            print("La colonne 'updated_at' n'existe pas, ajout en cours...")
            
            # Ajouter la colonne updated_at
            cursor.execute("""
                ALTER TABLE rh_management_expensereport
                ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
            """)
            
            # Mettre à jour la colonne avec la même valeur que created_at
            cursor.execute("""
                UPDATE rh_management_expensereport
                SET updated_at = created_at
                WHERE updated_at IS NULL AND created_at IS NOT NULL;
            """)
            
            # Mettre à jour tous les champs updated_at restants à NULL
            cursor.execute("""
                UPDATE rh_management_expensereport
                SET updated_at = CURRENT_TIMESTAMP
                WHERE updated_at IS NULL;
            """)
            
            conn.commit()
            print("Colonne 'updated_at' ajoutée avec succès!")
        else:
            print("La colonne 'updated_at' existe déjà.")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Erreur SQLite: {e}")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_updated_at_field()
    sys.exit(0 if success else 1)
