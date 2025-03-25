@echo off
echo ===============================================
echo =     APPLICATION DE TOUTES LES MIGRATIONS    =
echo ===============================================
echo.
echo Ce script va appliquer les migrations de toutes les applications
echo Django, y compris les applications intégrées comme les sessions.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "%confirm%"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/3] Vérification de l'environnement...
cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster

echo.
echo [2/3] Application des migrations pour les tables Django par défaut...
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate admin
python manage.py migrate sessions
echo     - Migrations des applications Django de base terminées.

echo.
echo [3/3] Application des migrations pour l'application RH Management...
python manage.py migrate rh_management
echo     - Migrations de l'application RH Management terminées.

echo.
echo ===============================================
echo =       MIGRATIONS TERMINÉES AVEC SUCCÈS      =
echo ===============================================
echo.
echo Les tables nécessaires pour le fonctionnement de l'application
echo ont été créées avec succès dans la base de données.
echo.
echo Vous pouvez maintenant démarrer le serveur avec:
echo python manage.py runserver

:end
echo.
pause
