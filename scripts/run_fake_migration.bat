@echo off
echo ===============================================
echo =       RÉSOLUTION DES MIGRATIONS BLOQUÉES       =
echo ===============================================
echo.
echo Cette solution va contourner le problème de migration
echo en appliquant manuellement les changements nécessaires
echo et en marquant les migrations comme appliquées.
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
echo [2/4] Application manuelle des modifications...
python scripts\fake_migration.py
if %errorlevel% neq 0 (
    echo ERREUR: Impossible d'appliquer les modifications manuellement.
    goto :restore
)

echo.
echo [3/4] Finition des migrations avec l'option --fake...
python manage.py migrate --fake
if %errorlevel% neq 0 (
    echo AVERTISSEMENT: Des problèmes sont survenus lors de la finalisation des migrations.
)

echo.
echo [4/4] Test de vérification...
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
goto :end

:restore
echo.
echo Restauration de la base de données depuis la sauvegarde...
copy "db.sqlite3.backup_%TIMESTAMP%" "db.sqlite3" /y
echo Base de données restaurée.

:end
echo.
pause
