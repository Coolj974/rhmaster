# 🧪 GUIDE DE TEST - FENÊTRE D'ACTIONS RAPIDES

## Tests à effectuer pour valider les corrections

### 🎯 **Test 1 : Affichage initial**
1. Ouvrir le dashboard (`/dashboard/`)
2. ✅ Vérifier que la fenêtre d'actions rapides apparaît en bas à droite
3. ✅ Vérifier qu'elle contient 4 boutons : Congé, Frais, Trajet, Profil
4. ✅ Vérifier la présence des boutons Épingler et Réduire

### 🎯 **Test 2 : Minimisation/Expansion**
1. Cliquer sur le bouton "Réduire" (icône minus)
2. ✅ La fenêtre doit se réduire à un petit bouton
3. Cliquer sur "Actions rapides" (bouton réduit)
4. ✅ La fenêtre doit se réexpandre

### 🎯 **Test 3 : Épinglage**
1. Cliquer sur le bouton "Épingler" (icône punaise)
2. ✅ L'icône doit devenir orange
3. ✅ Le header ne doit plus être déplaçable (curseur normal)
4. Cliquer à nouveau pour dépingler
5. ✅ L'icône redevient blanche, le drag redevient possible

### 🎯 **Test 4 : Drag & Drop**
1. S'assurer que la fenêtre n'est pas épinglée
2. Faire glisser la fenêtre par son header
3. ✅ Le curseur doit changer en "grabbing"
4. ✅ La fenêtre doit avoir une légère rotation pendant le déplacement
5. ✅ La fenêtre doit rester dans les limites de l'écran
6. Relâcher la souris
7. ✅ La position doit être sauvegardée

### 🎯 **Test 5 : Persistance**
1. Déplacer la fenêtre à un nouvel endroit
2. Recharger la page (F5)
3. ✅ La fenêtre doit réapparaître au même endroit
4. Minimiser la fenêtre
5. Recharger la page
6. ✅ La fenêtre doit rester minimisée

### 🎯 **Test 6 : Redimensionnement**
1. Déplacer la fenêtre vers un coin de l'écran
2. Redimensionner la fenêtre du navigateur pour la faire plus petite
3. ✅ La fenêtre d'actions doit se repositionner automatiquement
4. ✅ Elle doit rester visible dans la nouvelle taille d'écran

### 🎯 **Test 7 : Fonctionnalité des boutons**
1. Cliquer sur chaque bouton d'action :
   - **Congé** → `/leave-request/`
   - **Frais** → `/submit-expense/`
   - **Trajet** → `/submit-kilometric-expense/`
   - **Profil** → `/profile/`
2. ✅ Chaque lien doit fonctionner correctement

### 🎯 **Test 8 : Console JavaScript**
1. Ouvrir les outils de développement (F12)
2. Aller dans l'onglet Console
3. Recharger la page
4. ✅ Aucune erreur JavaScript ne doit apparaître
5. Tester le drag & drop
6. ✅ Aucune erreur ne doit s'afficher pendant le déplacement

### 🎯 **Test 9 : Écrans mobiles/petits**
1. Réduire la fenêtre du navigateur à une taille mobile
2. ✅ La fenêtre d'actions doit rester utilisable
3. ✅ Les boutons doivent rester cliquables
4. ✅ Le drag & drop doit fonctionner même sur petit écran

### 🎯 **Test 10 : localStorage corrompu**
1. Ouvrir les outils de développement (F12)
2. Aller dans l'onglet Application/Storage
3. Trouver localStorage et ajouter une clé corrompue :
   - Clé: `quickActionsPosition`
   - Valeur: `{invalid json`
4. Recharger la page
5. ✅ La fenêtre doit se charger normalement à la position par défaut
6. ✅ Aucune erreur dans la console

## 🔍 **Indicateurs de succès**

### ✅ **Fonctionnement normal :**
- Fenêtre visible en bas à droite
- Drag & drop fluide avec animation
- Boutons réactifs et fonctionnels
- Sauvegarde de position
- Aucune erreur JavaScript

### ❌ **Signes de problème :**
- Fenêtre invisible ou mal positionnée
- Erreurs JavaScript dans la console
- Drag & drop qui ne fonctionne pas
- Position non sauvegardée
- Boutons non cliquables

## 🛠️ **En cas de problème**

Si des bugs persistent :

1. **Vérifier la console JavaScript** pour des erreurs
2. **Vider le cache** du navigateur (Ctrl+F5)
3. **Supprimer localStorage** dans les outils de développement
4. **Vérifier les URLs** des actions rapides dans `urls.py`
5. **Contrôler les permissions** utilisateur

---
**Dernière mise à jour :** 28 mai 2025  
**Version testée :** Django 5.1.6
