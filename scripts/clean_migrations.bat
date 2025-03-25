@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo =       NETTOYAGE DES MIGRATIONS PROBLÉMATIQUES       =
echo ===============================================
echo.
echo ATTENTION: Cette opération va réinitialiser les migrations de l'application rh_management.
echo C'est une solution aux erreurs de migration liées aux dates.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "!confirm!"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/6] Suppression des fichiers de migration problématiques...
cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster
if exist "rh_management\migrations\0026_*.py" (
    del /q "rh_management\migrations\0026_*.py"
    echo     - Fichiers 0026_*.py supprimés.
)
if exist "rh_management\migrations\0027_*.py" (
    del /q "rh_management\migrations\0027_*.py"
    echo     - Fichiers 0027_*.py supprimés.
)
if exist "rh_management\migrations\__pycache__\0026_*.pyc" (
    del /q "rh_management\migrations\__pycache__\0026_*.pyc"
    echo     - Cache 0026_*.pyc supprimé.
)
if exist "rh_management\migrations\__pycache__\0027_*.pyc" (
    del /q "rh_management\migrations\__pycache__\0027_*.pyc"
    echo     - Cache 0027_*.pyc supprimé.
)

echo.
echo [2/6] Création d'un fichier de sauvegarde pour la base de données...
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
if exist "db.sqlite3" (
    copy "db.sqlite3" "db.sqlite3.bak_%TIMESTAMP%"
    echo     - Sauvegarde créée: db.sqlite3.bak_%TIMESTAMP%
)

echo.
echo [3/6] Suppression des entrées de migration problématiques...
echo PRAGMA foreign_keys=off; > temp_fix.sql
echo BEGIN TRANSACTION; >> temp_fix.sql
echo DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0026_%%'; >> temp_fix.sql
echo DELETE FROM django_migrations WHERE app='rh_management' AND name LIKE '0027_%%'; >> temp_fix.sql
echo COMMIT; >> temp_fix.sql
echo PRAGMA foreign_keys=on; >> temp_fix.sql

sqlite3 db.sqlite3 < temp_fix.sql
del temp_fix.sql
echo     - Entrées de migration problématiques supprimées de la base de données.

echo.
echo [4/6] Création d'une nouvelle migration pour ajouter les champs manquants...
python -m django shell -c "
from django.core.management import call_command
call_command('makemigrations', 'rh_management', '--name', 'add_missing_fields')
"
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de créer la nouvelle migration.
    goto :end
)
echo     - Nouvelle migration créée avec succès.

echo.
echo [5/6] Application de la nouvelle migration...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'appliquer la migration.
    echo     - Restauration de la base de données depuis la sauvegarde...
    if exist "db.sqlite3.bak_%TIMESTAMP%" (
        copy "db.sqlite3.bak_%TIMESTAMP%" "db.sqlite3" /y
        echo     - Base de données restaurée.
    )
    goto :end
)
echo     - Migration appliquée avec succès.

echo.
echo [6/6] Nettoyage...
python manage.py makemigrations rh_management --merge
python manage.py migrate

echo.
echo ===============================================
echo =      NETTOYAGE TERMINÉ AVEC SUCCÈS      =
echo ===============================================
echo.
echo Les opérations suivantes ont été effectuées:
echo  - Suppression des migrations problématiques
echo  - Sauvegarde de la base de données
echo  - Suppression des entrées de migration problématiques
echo  - Création d'une nouvelle migration propre
echo  - Application de la nouvelle migration
echo.
echo Une sauvegarde de votre base de données a été créée: db.sqlite3.bak_%TIMESTAMP%

:end
echo.
pause
