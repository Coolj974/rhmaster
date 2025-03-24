@echo off
echo Exécution des tests de permissions...

REM Définir le chemin Python correct
set PYTHONPATH=%~dp0..

REM Se déplacer dans le répertoire du projet Django
cd %~dp0..

echo Vérification de l'environnement...
if not exist hr_tool\settings.py (
    echo Erreur: Fichier settings.py non trouvé. Vérifiez le chemin.
    goto :end
)

REM Par défaut, exécuter tous les tests
set TEST_TARGET=all

REM Si un argument a été fourni, l'utiliser comme cible de test
if not "%~1"=="" set TEST_TARGET=%~1

REM Exécuter le script de test
echo Exécution des tests de permissions (cible: %TEST_TARGET%)...
python scripts\test_permissions.py -v --target=%TEST_TARGET%

:end
echo.
echo Tests terminés. Consultez le fichier scripts\test_permissions.log pour plus de détails.
pause
