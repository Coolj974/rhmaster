#!/usr/bin/env python
"""
Script Python pour exécuter les corrections SQL directement sur la base de données SQLite
sans nécessiter l'installation de l'utilitaire en ligne de commande sqlite3.
"""

import os
import sys
import sqlite3
from pathlib import Path

# Chemin vers la base de données SQLite
db_path = Path(__file__).parents[1] / 'db.sqlite3'

def fix_database():
    """
    Corrige les formats de date et heure invalides dans la base de données.
    """
    print(f"Connexion à la base de données: {db_path}")
    
    # Se connecter à la base de données SQLite
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Désactiver les contraintes de clés étrangères
    cursor.execute("PRAGMA foreign_keys=off;")
    
    # Démarrer une transaction
    cursor.execute("BEGIN TRANSACTION;")
    
    try:
        # Vérifier quelles tables existent
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'rh_management_%';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables trouvées: {tables}")
        
        # Pour chaque table, vérifier les colonnes et mettre à jour si nécessaire
        for table in tables:
            # Vérifier les colonnes existantes
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [column[1] for column in cursor.fetchall()]
            print(f"Table {table}: Colonnes trouvées = {columns}")
            
            # Mettre à jour uniquement si les colonnes existent
            if 'created_at' in columns:
                print(f"Mise à jour de la colonne created_at dans {table}")
                cursor.execute(f"""
                UPDATE {table} 
                SET created_at = CURRENT_TIMESTAMP 
                WHERE created_at LIKE '%' || char(160) || '%' OR created_at IS NULL;
                """)
            
            if 'updated_at' in columns:
                print(f"Mise à jour de la colonne updated_at dans {table}")
                cursor.execute(f"""
                UPDATE {table} 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE updated_at LIKE '%' || char(160) || '%' OR updated_at IS NULL;
                """)
        
        # Vérifier si la table django_migrations existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations';")
        if cursor.fetchone():
            print("Nettoyage des migrations problématiques")
            cursor.execute("DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0026_%';")
            cursor.execute("DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0027_%';")
        else:
            print("Table django_migrations non trouvée, impossible de nettoyer les migrations")
        
        # Valider les modifications
        cursor.execute("COMMIT;")
        
        # Réactiver les contraintes de clés étrangères
        cursor.execute("PRAGMA foreign_keys=on;")
        
        print("Corrections SQL appliquées avec succès.")
        
    except sqlite3.Error as e:
        # En cas d'erreur, annuler la transaction
        cursor.execute("ROLLBACK;")
        print(f"Erreur lors de l'exécution des corrections SQL: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Fermer la connexion dans tous les cas
        conn.close()
    
    return True

if __name__ == "__main__":
    success = fix_database()
    sys.exit(0 if success else 1)
