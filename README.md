
## Prérequis

- Python 3.9 ou supérieur
- Django 5.1.6
- SQLite (par défaut)

## Installation

1. Clonez le dépôt :

    ```sh
    git clone https://github.com/votre-utilisateur/hr_tool.git
    cd hr_tool
    ```

2. Créez un environnement virtuel et activez-le :

    ```sh
    python -m venv venv
    source venv/bin/activate  # Sur Windows, utilisez `venv\Scripts\activate`
    ```

3. Installez les dépendances :

    ```sh
    pip install -r requirements.txt
    ```

4. Appliquez les migrations de la base de données :

    ```sh
    python manage.py migrate
    ```

5. Créez un superutilisateur pour accéder à l'interface d'administration :

    ```sh
    python manage.py createsuperuser
    ```

6. Démarrez le serveur de développement :

    ```sh
    python manage.py runserver
    ```

7. Accédez à l'application dans votre navigateur à l'adresse `http://127.0.0.1:8000`.

## Fonctionnalités

- **Gestion des utilisateurs** : Inscription, connexion, déconnexion.
- **Gestion des congés** : Demande de congé, approbation, rejet.
- **Gestion des dépenses** : Soumission de dépenses, approbation, rejet.
- **Administration** : Interface d'administration pour gérer les utilisateurs et les données.

## Configuration

Les configurations principales se trouvent dans le fichier [settings.py](http://_vscodecontentref_/4). Vous pouvez y configurer la base de données, les backends d'authentification, les redirections après connexion, et bien plus encore.

## Déploiement

Pour déployer cette application en production, suivez les instructions de la documentation officielle de Django : [Comment déployer Django](https://docs.djangoproject.com/en/5.1/howto/deployment/).

## Contribuer

Les contributions sont les bienvenues ! Veuillez soumettre une pull request ou ouvrir une issue pour discuter des changements que vous souhaitez apporter.

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
