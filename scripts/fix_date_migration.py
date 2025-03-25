#!/usr/bin/env python
"""
Script pour corriger les problèmes de date dans la base de données
qui empêchent les migrations de s'exécuter correctement.
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

# Ajouter le répertoire parent au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
import django
django.setup()

# Chemin vers la base de données SQLite
db_path = Path(__file__).parents[1] / 'db.sqlite3'

def fix_date_formats():
    """
    Corrige les formats de date et heure invalides dans la base de données.
    """
    print(f"Connexion à la base de données: {db_path}")
    
    # Se connecter à la base de données SQLite
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 1. Obtenir toutes les tables avec des champs de date/heure
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall() if not table[0].startswith('sqlite_')]
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for table in tables:
        # Obtenir les informations sur les colonnes
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        # Identifier les colonnes pouvant être des dates
        date_columns = []
        for col in columns:
            col_name = col[1]
            if any(keyword in col_name.lower() for keyword in ['date', 'time', 'created', 'updated', 'at']):
                date_columns.append(col_name)
        
        if not date_columns:
            continue
        
        print(f"\nVérification de la table {table}, colonnes: {', '.join(date_columns)}")
        
        # Pour chaque colonne de date, vérifier et corriger les valeurs invalides
        for col_name in date_columns:
            try:
                # Vérifier s'il y a des valeurs problématiques
                cursor.execute(f"SELECT rowid, {col_name} FROM {table} WHERE {col_name} IS NOT NULL;")
                rows = cursor.fetchall()
                
                fixed_count = 0
                for row in rows:
                    rowid, date_value = row
                    
                    # Vérifier si la valeur a un format incorrect
                    if isinstance(date_value, str) and ('\xa0' in date_value or not date_value.strip()):
                        # Définir à la date et l'heure actuelles
                        cursor.execute(f"UPDATE {table} SET {col_name} = ? WHERE rowid = ?", 
                                       (current_time, rowid))
                        fixed_count += 1
                
                if fixed_count > 0:
                    print(f"  - Corrigé {fixed_count} valeurs dans la colonne {col_name}")
                    conn.commit()
                
            except sqlite3.OperationalError as e:
                # Cette colonne pourrait ne pas être une colonne de date réelle
                print(f"  - Ignoré {col_name}: {str(e)}")
    
    # 2. Nettoyer les entrées de migration problématiques
    try:
        cursor.execute("DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0026_%';")
        cursor.execute("DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0027_%';")
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"\nSupprimé {deleted_count} entrées de migration problématiques.")
    except sqlite3.OperationalError as e:
        print(f"Erreur lors du nettoyage des migrations: {str(e)}")
    
    # Fermer la connexion
    conn.close()
    
    print("\nCorrection terminée. Vous pouvez maintenant exécuter:")
    print("- python manage.py makemigrations")
    print("- python manage.py migrate")

if __name__ == "__main__":
    fix_date_formats()
