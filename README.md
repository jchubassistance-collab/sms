# SMS Flow

Application Django de gestion de contacts, campagnes SMS et e-mail, forfaits, paiements, historique et support client.

## Prérequis

- Python 3.14 (version utilisée pour valider ce projet)
- Microsoft SQL Server accessible depuis la machine
- Microsoft ODBC Driver 18 for SQL Server
- Un compte et un jeton chez le fournisseur SMS pour envoyer des SMS

Les paiements MTN MoMo et Airtel Money sont configurés par défaut sur leurs environnements de test. Leurs identifiants sont facultatifs pour lancer l’application, mais nécessaires pour tester ces paiements.

## Installation locale (Windows / PowerShell)

Depuis le dossier du projet :

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Ouvrez `.env` et renseignez au minimum :

- `DJANGO_SECRET_KEY` : créez une clé avec `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- `SQLSERVER_HOST`, `SQLSERVER_NAME`, `SQLSERVER_USER`, `SQLSERVER_PASSWORD` et `SQLSERVER_PORT` : paramètres de votre instance SQL Server.
- `SMS_API_TOKEN` et `SMS_SENDER` : identifiants fournis par votre prestataire SMS.
- `SMTP_ENCRYPTION_KEY` : clé aléatoire à définir avant d’enregistrer des identifiants SMTP dans les profils. Conservez-la en lieu sûr et ne la changez pas après avoir chiffré des mots de passe SMTP.

Pour créer une clé SMTP, vous pouvez utiliser `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

Les variables MTN MoMo (`MOMO_*`) et Airtel Money (`AIRTEL_*`) se configurent dans le même fichier. Gardez les environnements de test jusqu’à la validation des comptes marchands de production.

## Initialiser la base et lancer l’application

Vérifiez que SQL Server fonctionne et que le compte défini dans `.env` peut accéder à la base. Puis exécutez :

```powershell
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8001
```

Ouvrez ensuite <http://127.0.0.1:8001/>. L’application utilise SQL Server ; le fichier `db.sqlite3` éventuellement présent n’est pas la base configurée par Django.

Pour lancer la suite de tests :

```powershell
python manage.py test
```

Les tests Django doivent pouvoir créer leur base de test sur SQL Server.

## Langue et fuseau horaire

L’interface et Django utilisent le français (`fr-fr`). Les dates sont configurées sur le fuseau `Africa/Brazzaville`.
Après 10 minutes sans requête, la session utilisateur expire et une nouvelle connexion est requise. Toute requête effectuée pendant l’utilisation renouvelle ce délai.

## Mise en production

Avant le déploiement :

1. Définissez `DJANGO_DEBUG=False` et `DJANGO_ALLOWED_HOSTS` avec les noms de domaine réellement utilisés.
2. Renseignez `CSRF_TRUSTED_ORIGINS` avec les origines HTTPS autorisées, par exemple `https://sms.exemple.com`.
3. Servez le site derrière HTTPS et configurez le proxy TLS conformément à votre hébergeur.
4. Remplacez les identifiants de développement par des secrets renouvelés et des comptes à privilèges limités. Ne copiez pas les secrets de `.env` dans le dépôt.
5. Lancez `python manage.py check --deploy` avec la configuration de production.

Le fichier `.env` est ignoré par Git. `.env.example` ne contient que les noms des paramètres et des valeurs d’exemple non secrètes.

## Documentation API

Le document de référence fourni avec le projet est [202609250949api_document.pdf](202609250949api_document.pdf). Les routes API Django sont déclarées sous `/api/users/`, `/api/contacts/`, `/api/campaigns/`, `/api/billing/` et `/api/support/`.
