#!/usr/bin/env python
"""
Script pour ajouter la colonne 'attachment' manquante à la table ExpenseReport.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Configuration de l'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
os.chdir(project_dir)

# Chemin vers la base de données SQLite
db_path = Path(project_dir) / 'db.sqlite3'

def add_attachment_field():
    """Ajoute la colonne 'attachment' à la table ExpenseReport."""
    print(f"Connexion à la base de données: {db_path}")
    
    try:
        # Se connecter à la base de données SQLite
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Vérifier si la colonne 'attachment' existe déjà
        cursor.execute("PRAGMA table_info(rh_management_expensereport);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'attachment' not in columns:
            print("La colonne 'attachment' n'existe pas, ajout en cours...")
            
            # Ajouter la colonne attachment
            cursor.execute("""
                ALTER TABLE rh_management_expensereport
                ADD COLUMN attachment VARCHAR(100) NULL;
            """)
            
            conn.commit()
            print("Colonne 'attachment' ajoutée avec succès!")
        else:
            print("La colonne 'attachment' existe déjà.")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Erreur SQLite: {e}")
        return False
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    success = add_attachment_field()
    sys.exit(0 if success else 1)
