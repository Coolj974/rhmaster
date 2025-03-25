@echo off
echo ===============================================
echo =     CORRECTION DE LA TABLE DE SESSIONS     =
echo ===============================================
echo.
echo Ce script va créer la table django_session manquante
echo qui est nécessaire pour l'authentification et la navigation.
echo.

cd c:\Users\Cyberun 002\OneDrive\RHCYBER\hr_tool\rhmaster

echo Exécution du script de correction...
python scripts\fix_sessions.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Impossible de créer la table de sessions.
    echo.
    echo Essai alternatif avec la commande migrate directe...
    python manage.py migrate sessions
    
    if %errorlevel% neq 0 (
        echo.
        echo ERREUR CRITIQUE: Impossible de créer la table de sessions.
        echo Essayez de réinitialiser complètement votre base de données avec:
        echo scripts\reset_database.bat
    ) else (
        echo.
        echo Table de sessions créée avec succès!
    )
) else (
    echo.
    echo Correction terminée avec succès!
)

echo.
echo Redémarrez votre serveur Django pour appliquer les changements.
echo.
pause
