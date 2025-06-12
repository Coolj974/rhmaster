@echo off
echo ===============================================
echo    NETTOYAGE AUTOMATIQUE DU PROJET DJANGO
echo ===============================================
echo.

echo [1/5] Suppression des fichiers cache Python...
powershell -Command "Get-ChildItem -Path . -Recurse -Name '__pycache__' | ForEach-Object { Remove-Item -Path $_ -Recurse -Force }"
powershell -Command "Get-ChildItem -Path . -Recurse -Filter '*.pyc' | Remove-Item -Force"
echo    - Cache Python nettoyé

echo.
echo [2/5] Suppression des logs...
if exist "*.log" del /q "*.log"
if exist "scripts\*.log" del /q "scripts\*.log"
echo    - Logs supprimés

echo.
echo [3/5] Suppression des fichiers temporaires...
if exist "debug_*.py" del /q "debug_*.py"
if exist "test_*.py" del /q "test_*.py"
if exist "test_*.bat" del /q "test_*.bat"
if exist "validate_*.py" del /q "validate_*.py"
if exist "quick_test.py" del /q "quick_test.py"
echo    - Fichiers temporaires supprimés

echo.
echo [4/5] Nettoyage des fichiers statiques...
if exist "staticfiles" rmdir /s /q "staticfiles"
echo    - Staticfiles supprimés (seront régénérés)

echo.
echo [5/5] Régénération des fichiers statiques...
python manage.py collectstatic --noinput --clear
if %errorlevel% neq 0 (
    echo    - Avertissement: Impossible de régénérer les staticfiles
) else (
    echo    - Staticfiles régénérés avec succès
)

echo.
echo ===============================================
echo           NETTOYAGE TERMINÉ
echo ===============================================
echo.
echo Votre projet Django a été nettoyé !
echo.
pause
