@echo off
echo Exécution des tests de permissions...
cd %~dp0..
python scripts\test_permissions.py %*
echo.
echo Tests terminés. Consultez le fichier scripts\test_permissions.log pour plus de détails.
pause
