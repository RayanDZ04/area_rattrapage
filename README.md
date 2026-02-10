# AREA (rattrapage) — Web Front/Back

Projet AREA type IFTTT : un **backend FastAPI** + un **front statique** qui permet :
- Authentification **Register/Login** (JWT)
- Connexion à un service externe (**Google OAuth**) gérée côté backend
- Création d’**applets** (action → réaction)
- Consultation d’un **historique** d’exécution (logs)

## Stack

- Backend : FastAPI + Uvicorn + SQLAlchemy (SQLite)
- Auth : JWT (python-jose) + hash mdp (passlib/bcrypt)
- OAuth : Authlib (Google OpenID) + Google APIs (gmail / calendar)
- Front : HTML/CSS/JS + `python -m http.server`

## Fonctionnalités

### Auth
- `POST /auth/register` : création de compte
- `POST /auth/login` : connexion → renvoie un JWT
- `GET /auth/me` : infos utilisateur (JWT requis)

### Connexion Google (OAuth)
- `GET /auth/google/login` : démarre le flow OAuth
- `GET /auth/google/callback` : callback OAuth, stockage token en base, redirection vers le front avec un JWT

Les **tokens Google** (access/refresh) sont stockés en base dans `service_tokens` et **ne passent pas par le front**.

### Applets
- `POST /applets` : créer une applet
- `GET /applets` : lister
- `DELETE /applets/{id}` : supprimer
- `PATCH /applets/{id}/active` : activer/désactiver (persisté en DB)
- `POST /applets/run` : exécuter les applets de l’utilisateur
- `GET /applets/logs` : historique (100 derniers)

Applets Google disponibles :
- Actions
  - Gmail : `gmail_new_mail` (détecte un mail non lu)
  - Agenda : `agenda_new_event` (dernier évènement modifié)
- Réactions
  - Gmail : `gmail_send_mail` (envoi d’un mail, et marque le mail action comme lu)
  - Agenda : `agenda_create_event` (création d’évènement)

Le backend lance aussi un scheduler (toutes les 30s) qui exécute les applets.
Le front déclenche également `POST /applets/run` toutes les 30s quand l’utilisateur est connecté.

Si une applet est désactivée (`is_active=false`), elle est ignorée (scheduler + exécution manuelle).

#### Activer / Désactiver (persistance)

- Le bouton “Activé / Désactivé” côté UI appelle `PATCH /applets/{id}/active`.
- L’état est stocké en DB (colonne `applets.is_active`).
- Au rechargement, `GET /applets` renvoie `is_active` et le front rend l’état correctement.

Si tu vois l’état revenir “Activé” après rechargement, c’est souvent un **cache navigateur** : fais un hard refresh (`Ctrl+Shift+R`).

## Prérequis

- Python 3
- `make`
- `lsof` (utilisé par `make stop`)

## Démarrage rapide

Depuis la racine :

```bash
make web
```

Ça fait :
- stop (libère les ports 8080/5173)
- crée `back/.env` si absent
- crée `.venv` et installe les deps depuis `back/requirements.txt`
- lance backend + front

URLs :
- Front : http://127.0.0.1:5173/
- Back : http://127.0.0.1:8080/ (Swagger : `/docs`)

Arrêt : `Ctrl+C` (puis `make stop` si besoin).

### Commandes utiles

- `make backend` : lance seulement le backend
- `make backend-dev` : backend avec `--reload`
- `make front` : lance seulement le front
- `make stop` : tue les process sur 8080/5173
- `make fclean` : supprime venv + DB sqlite + `.env`

## Configuration (.env)

Le fichier de config est : `back/.env`.

Variables attendues :

```dotenv
# JWT / sessions
SECRET_KEY=change-me
SESSION_SECRET=change-me

# DB
DATABASE_URL=sqlite:///./app.db

# URLs
BACKEND_URL=http://localhost:8080
FRONTEND_URL=http://localhost:5173

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Notes :
- Si tu changes `SECRET_KEY`, les JWT existants deviennent invalides (il faut se reconnecter).
- Le backend charge explicitement `back/.env` via `python-dotenv`.

## Configuration Google Cloud

1) Créer un projet sur Google Cloud
2) Activer les APIs nécessaires :
- **Gmail API**
- **Google Calendar API** (si tu utilises l’action/réaction agenda)

3) Configurer l’écran de consentement OAuth
4) Créer des identifiants OAuth (type **Web application**) et renseigner :

- **Authorized JavaScript origins** :
  - `http://127.0.0.1:5173`
  - `http://localhost:5173`

- **Authorized redirect URIs** :
  - `http://127.0.0.1:8080/auth/google/callback`
  - `http://localhost:8080/auth/google/callback`

5) Mettre `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` dans `back/.env`

## Front : URL API

Le front appelle l’API via une constante :
- `API_URL` dans [front/app.js](front/app.js)

Par défaut : `http://localhost:8080`.
Si tu changes le port/host backend, adapte cette valeur.

## Dépannage rapide

- Port déjà utilisé :
  - `make stop` puis relance `make web`

- Erreur Google `accessNotConfigured` / “API has not been used in project” :
  - activer l’API Gmail/Calendar dans Google Cloud Console, attendre quelques minutes, puis reconnecter Google.

- OAuth `redirect_uri_mismatch` :
  - vérifier que l’URL (localhost vs 127.0.0.1) correspond exactement à ce que tu utilises.

## Critères rattrapage (mapping)

- Web Front/Back : OK
- Login/Register : OK (`/auth/register`, `/auth/login`)
- Connexion service : OK (Google OAuth)
- Voir les dernières actions : OK via historique `GET /applets/logs` (exécutions)
- Réaction sur le service : OK (envoi mail / création évènement)
- Tokens gérés côté backend : OK (tokens Google stockés/refresh côté serveur)

---

Backend quick README initial disponible aussi dans [back/README.md](back/README.md).
