@echo off
echo ===============================================
echo =      CORRECTION DES PROBLÈMES DE DATE      =
echo ===============================================
echo.
echo Ce script va corriger les problèmes de format de date
echo qui empêchent les migrations de s'exécuter correctement.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "%confirm%"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/3] Exécution du script de correction des dates...
cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster
python scripts\fix_date_migration.py
if %errorlevel% neq 0 (
    echo ERREUR: Échec de la correction des dates.
    goto :end
)

echo.
echo [2/3] Création des migrations...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de créer les migrations.
    goto :end
)

echo.
echo [3/3] Application des migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'appliquer les migrations.
    goto :end
)

echo.
echo ===============================================
echo =      CORRECTION TERMINÉE AVEC SUCCÈS       =
echo ===============================================
echo.
echo Les opérations suivantes ont été effectuées:
echo  - Correction des formats de date invalides dans la base de données
echo  - Suppression des migrations problématiques
echo  - Création et application de nouvelles migrations

:end
echo.
pause
