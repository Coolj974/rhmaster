#!/usr/bin/env python
"""
Script de validation automatique des corrections de la fenêtre d'actions rapides
Ce script vérifie que toutes les corrections ont été appliquées correctement
"""
import os
import re

def check_dashboard_file():
    """Vérifie les corrections dans le fichier dashboard.html"""
    print("🔍 Vérification du fichier dashboard.html...")
    
    file_path = "templates/rh_management/dashboard.html"
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tests de vérification
    checks = [
        # Vérification des éléments DOM
        (r'if \(!quickActionsCard \|\| !quickActionsBody', 
         "✅ Validation des éléments DOM"),
        
        # Gestion d'erreur localStorage
        (r'try\s*\{\s*cardPosition = JSON\.parse',
         "✅ Gestion d'erreur localStorage"),
        
        # Calcul de position amélioré
        (r'getBoundingClientRect\(\)',
         "✅ Calcul de position amélioré"),
        
        # preventDefault ajouté
        (r'e\.preventDefault\(\)',
         "✅ preventDefault ajouté"),
        
        # Gestion du redimensionnement
        (r'window\.addEventListener\([\'"]resize[\'"]',
         "✅ Gestion du redimensionnement"),
        
        # Styles CSS dragging
        (r'\.quick-actions-floating\.dragging',
         "✅ Styles CSS dragging"),
        
        # État pinned
        (r'quickActionsCard\.classList\.add\([\'"]pinned[\'"]',
         "✅ Gestion état pinned"),
        
        # Try-catch sur les événements
        (r'try\s*\{\s*quickActionsBody\.style\.display',
         "✅ Try-catch sur événements"),
    ]
    
    results = []
    for pattern, description in checks:
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"  {description}")
            results.append(True)
        else:
            print(f"  ❌ Manquant: {description}")
            results.append(False)
    
    return all(results)

def check_urls_exist():
    """Vérifie que les URLs des actions rapides existent"""
    print("\n🔍 Vérification des URLs...")
    
    import sys
    sys.path.insert(0, '.')
    
    try:
        import os
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_tool.settings')
        django.setup()
        
        from django.urls import reverse
        
        urls_to_check = [
            'leave_request',
            'submit_expense',
            'submit_kilometric_expense',
            'profile'
        ]
        
        all_good = True
        for url_name in urls_to_check:
            try:
                url = reverse(url_name)
                print(f"  ✅ {url_name}: {url}")
            except Exception as e:
                print(f"  ❌ {url_name}: {e}")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"  ❌ Erreur Django: {e}")
        return False

def check_javascript_syntax():
    """Vérification basique de la syntaxe JavaScript"""
    print("\n🔍 Vérification syntaxe JavaScript...")
    
    file_path = "templates/rh_management/dashboard.html"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraire le JavaScript
    js_blocks = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
    
    if not js_blocks:
        print("  ❌ Aucun bloc JavaScript trouvé")
        return False
    
    # Vérifications syntaxiques basiques
    js_content = '\n'.join(js_blocks)
    
    syntax_checks = [
        (r'function\s+\w+\s*\([^)]*\)\s*\{', "Déclarations de fonctions"),
        (r'addEventListener\s*\([^)]+\)', "Event listeners"),
        (r'localStorage\.(get|set)Item', "Utilisation localStorage"),
        (r'try\s*\{[^}]+\}\s*catch', "Blocs try-catch"),
    ]
    
    for pattern, description in syntax_checks:
        if re.search(pattern, js_content):
            print(f"  ✅ {description}")
        else:
            print(f"  ⚠️  {description} non trouvé")
    
    # Vérifier les accolades équilibrées (basique)
    open_braces = js_content.count('{')
    close_braces = js_content.count('}')
    
    if open_braces == close_braces:
        print(f"  ✅ Accolades équilibrées ({open_braces}/{close_braces})")
        return True
    else:
        print(f"  ❌ Accolades déséquilibrées ({open_braces}/{close_braces})")
        return False

def main():
    print("=" * 60)
    print("🧪 VALIDATION DES CORRECTIONS - FENÊTRE D'ACTIONS RAPIDES")
    print("=" * 60)
    
    # Tests
    dashboard_ok = check_dashboard_file()
    urls_ok = check_urls_exist()
    js_ok = check_javascript_syntax()
    
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS DE LA VALIDATION")
    print("=" * 60)
    
    print(f"Dashboard HTML: {'✅ OK' if dashboard_ok else '❌ ÉCHEC'}")
    print(f"URLs Django:    {'✅ OK' if urls_ok else '❌ ÉCHEC'}")
    print(f"JavaScript:     {'✅ OK' if js_ok else '❌ ÉCHEC'}")
    
    if dashboard_ok and urls_ok and js_ok:
        print("\n🎉 SUCCÈS ! Toutes les corrections sont en place")
        print("\n📝 Actions suivantes recommandées:")
        print("1. Démarrer le serveur: python manage.py runserver")
        print("2. Ouvrir le dashboard dans le navigateur")
        print("3. Tester la fenêtre d'actions rapides")
        print("4. Suivre le guide de test: GUIDE_TEST_QUICK_ACTIONS.md")
        return True
    else:
        print("\n❌ DES PROBLÈMES PERSISTENT")
        print("Consultez les détails ci-dessus pour identifier les corrections manquantes")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
