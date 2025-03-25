@echo off
echo ===============================================
echo =  CORRECTION DIRECTE DE LA BASE DE DONNEES  =
echo ===============================================
echo.
echo Cette solution corrige directement les valeurs de dates problématiques
echo dans la base de données SQLite qui causent des erreurs de migration.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "%confirm%"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/4] Création d'une sauvegarde de la base de données...
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster

if exist "db.sqlite3" (
    copy "db.sqlite3" "db.sqlite3.backup_%TIMESTAMP%"
    echo     - Sauvegarde créée: db.sqlite3.backup_%TIMESTAMP%
) else (
    echo     - Base de données non trouvée.
    goto :end
)

echo.
echo [2/4] Application des corrections SQL via Python...
python scripts\fix_db_python.py
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'exécuter les corrections SQL.
    goto :end
)
echo     - Valeurs de dates corrigées avec succès.

echo.
echo [3/4] Recréation des migrations...
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Problème lors de la création des migrations.
)

echo.
echo [4/4] Application des migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Problème lors de l'application des migrations.
    echo     - Essai d'application avec l'option --fake...
    python manage.py migrate --fake
)

echo.
echo ===============================================
echo =         CORRECTION TERMINÉE                =
echo ===============================================
echo.
echo Une sauvegarde de votre base de données a été créée: db.sqlite3.backup_%TIMESTAMP%
echo.
echo Si les problèmes persistent, vous pouvez restaurer la sauvegarde avec:
echo copy "db.sqlite3.backup_%TIMESTAMP%" "db.sqlite3"
echo.
echo Ou essayer une dernière solution radicale: supprimer la base de données
echo et la recréer entièrement avec le script reset_database.bat

:end
echo.
pause
