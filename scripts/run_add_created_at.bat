@echo off
echo ===============================================
echo =  AJOUT DE LA COLONNE CREATED_AT MANQUANTE  =
echo ===============================================
echo.
echo Ce script va ajouter la colonne created_at manquante
echo à la table ExpenseReport qui cause l'erreur actuelle.
echo.
set /p confirm=Êtes-vous sûr de vouloir continuer? (O/N): 

if /i not "%confirm%"=="O" (
    echo Opération annulée.
    goto :end
)

echo.
echo [1/3] Création d'une sauvegarde de la base de données...
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
echo [2/3] Ajout de la colonne created_at...
python scripts\add_created_at_field.py
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'ajouter la colonne created_at.
    goto :end
)

echo.
echo [3/3] Vérification de l'application...
python manage.py check
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Des problèmes ont été détectés dans le système.
) else (
    echo     - Vérification réussie! Votre application devrait fonctionner correctement.
)

echo.
echo ===============================================
echo =         OPÉRATION TERMINÉE                =
echo ===============================================
echo.
echo Une sauvegarde de votre base de données a été créée: db.sqlite3.backup_%TIMESTAMP%
echo.
echo Redémarrez votre serveur Django pour appliquer les changements.

:end
echo.
pause
