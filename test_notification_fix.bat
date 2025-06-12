@echo off
echo ===============================================
echo Test de la correction URL notifications_page
echo ===============================================
echo.

echo Etape 1: Verification de la syntaxe Django...
python manage.py check
if errorlevel 1 (
    echo ERREUR: Probleme de configuration Django
    pause
    exit /b 1
)
echo ✅ Configuration Django valide

echo.
echo Etape 2: Test de l'URL notifications_page...
python -c "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings'); django.setup(); from django.urls import reverse; print('✅ URL notifications_page:', reverse('notifications_page'))"
if errorlevel 1 (
    echo ERREUR: URL notifications_page non trouvee
    pause
    exit /b 1
)

echo.
echo Etape 3: Demarrage du serveur de test...
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.
python manage.py runserver 8000

pause
