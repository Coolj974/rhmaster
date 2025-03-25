@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo =       RÉINITIALISATION DE LA BASE DE DONNÉES        =
echo ===============================================
echo.
echo ATTENTION: Cette opération va supprimer toutes les données!
echo Assurez-vous d'avoir une sauvegarde si nécessaire.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "!confirm!"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/5] Détection du fichier de base de données...

set DB_FILE=c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster\db.sqlite3
if exist "%DB_FILE%" (
    echo     - Base de données trouvée: %DB_FILE%
) else (
    echo     - Aucune base de données SQLite trouvée.
)

echo.
echo [2/5] Suppression de la base de données...
if exist "%DB_FILE%" (
    del "%DB_FILE%"
    echo     - Base de données supprimée.
) else (
    echo     - Aucune base de données à supprimer.
)

echo.
echo [3/5] Création d'un nouveau fichier de migrations...
cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster
python manage.py makemigrations
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de créer les migrations.
    goto :end
)

echo.
echo [4/5] Application des migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'appliquer les migrations.
    goto :end
)

echo.
echo [5/5] Création du superutilisateur...
echo Veuillez créer un compte administrateur:
python manage.py createsuperuser
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Impossible de créer le superutilisateur.
)

echo.
echo ===============================================
echo =      BASE DE DONNÉES RÉINITIALISÉE AVEC SUCCÈS      =
echo ===============================================
echo.
echo Les opérations suivantes ont été effectuées:
echo  - Suppression de l'ancienne base de données
echo  - Création de nouvelles migrations
echo  - Application des migrations
echo  - Création d'un nouveau superutilisateur

:end
echo.
pause
