# 👤 Personne 2 — DevOps & Infra Master

## 🎯 Mission Générale
La Personne 2 est **responsable de toute la couche DevOps** du projet. Son rôle est de garantir que la plateforme est :
- **automatisée** (zéro action manuelle),
- **reproductible** (Infrastructure as Code),
- **observable** (monitoring & métriques SRE),
- **sécurisée** (secrets, containers),
- **déployable comme en production** via un **CI/CD professionnel**.

👉 Dans ce hackathon, la Personne 2 porte **30 points DevOps Implementation** (et influence indirectement le reste).

---

## 🧱 1. Infrastructure as Code (IaC)

### 🎯 Objectif
Permettre à n’importe qui (jury inclus) de lancer **toute la plateforme avec une seule commande** :

```bash
docker compose up -d
```

### 📌 Tâches
- Créer et maintenir un **`docker-compose.yml` unique** décrivant toute l’infrastructure.
- Définir les services suivants :
  - alert-ingestion
  - incident-management
  - oncall-service
  - web-ui
  - postgres
  - prometheus
  - grafana
- Configurer :
  - un **réseau Docker commun**
  - des **volumes nommés** (DB, Prometheus, Grafana)
  - des **variables d’environnement** via `.env`
  - des **healthchecks** pour chaque service
  - des `depends_on` basés sur la santé

### ✅ Critère de réussite
- `docker compose down -v && docker compose up -d` fonctionne sans erreur.
- Tous les containers sont **UP & healthy**.

---

## 🐳 2. Containerization Professionnelle

### 🎯 Objectif
Chaque microservice doit être **léger, sécurisé et isolé**, comme en production.

### 📌 Tâches (pour chaque service)
- Écrire un **Dockerfile multi-stage**.
- Utiliser une image de base `alpine` ou `slim`.
- Exécuter le container avec un **USER non-root**.
- Ajouter un **HEALTHCHECK** pointant sur `/health`.
- Fournir un `.dockerignore`.
- Garantir une taille d’image < **500 MB**.

### ✅ Critère de réussite
- `docker images` montre des images légères.
- `docker ps` affiche des containers **healthy**.

---

## 🔁 3. Orchestration avec Docker Compose

### 🎯 Objectif
Prouver la maîtrise de l’orchestration d’un système distribué.

### 📌 Tâches
- Communication inter-services via **noms de services Docker** (pas `localhost`).
- Exposition minimale des ports (uniquement ceux nécessaires au jury).
- Définition de `restart: unless-stopped`.
- Utilisation correcte de `depends_on` + healthchecks.

### ✅ Critère de réussite
- `docker compose ps` montre tous les services actifs.
- Les services communiquent correctement entre eux.

---

## 📊 4. Monitoring & Observabilité (SRE)

### 🎯 Objectif
Rendre le système **observable** et mesurable via des métriques métier.

### 🔹 4.1 Prometheus

#### 📌 Tâches
- Créer `monitoring/prometheus.yml`.
- Configurer le scraping des endpoints `/metrics` pour :
  - alert-ingestion
  - incident-management
  - oncall-service
  - web-ui
- Vérifier que chaque service expose des métriques Prometheus valides.

#### ✅ Critère de réussite
- Tous les targets sont **UP** sur `http://localhost:9090/targets`.

---

### 🔹 4.2 Grafana

#### 📌 Tâches
- Déployer Grafana via Docker Compose.
- Provisionner automatiquement les dashboards (pas de création manuelle).
- Créer **au minimum 2 dashboards** :
  1. **Incident Overview** (incidents ouverts, sévérité, MTTA, MTTR)
  2. **SRE Metrics** (tendances MTTA/MTTR, volume d’incidents)

#### ✅ Critère de réussite
- Dashboards visibles dès le premier lancement de Grafana.

---

## 🔄 5. CI/CD Pipeline Professionnel

### 🎯 Objectif
Automatiser **tout le cycle de vie** du projet avec un pipeline **réellement professionnel**.

### 📌 Structure recommandée
```
ci/
├── pipeline.sh
├── quality.sh
├── security.sh
├── test.sh
├── build.sh
├── deploy.sh
└── verify.sh
```

### 🔹 Stages obligatoires

#### 1️⃣ Code Quality
- Lint (ruff / flake8)
- Format (black)
- Échec immédiat si erreur

#### 2️⃣ Security Scan (Secrets)
- Gitleaks ou TruffleHog
- Pre-commit hook
- Échec si secret détecté

#### 3️⃣ Tests & Coverage
- pytest
- Coverage ≥ **60%**

#### 4️⃣ Build
- `docker compose build`
- Tag des images

#### 5️⃣ Image Security Scan (bonus)
- Trivy ou Grype
- Échec uniquement si vulnérabilité **CRITICAL**

#### 6️⃣ Deploy
- `docker compose down --remove-orphans`
- `docker compose up -d`

#### 7️⃣ Post-Deployment Verification
- Vérification des endpoints `/health`
- Test d’un flux réel (alert → incident)

### ✅ Critère de réussite
- `./ci/pipeline.sh` s’exécute **sans intervention humaine**.

---

## 🔐 6. Sécurité DevOps (Shift-Left)

### 🎯 Objectif
Intégrer la sécurité dès le début du cycle de développement.

### 📌 Tâches
- Aucune clé ou mot de passe en dur dans le code.
- `.env` ignoré par Git.
- Fournir `.env.example`.
- Containers exécutés sans privilèges root.
- Scans de secrets intégrés au pipeline.

---

## 📄 7. Documentation DevOps

### 🎯 Objectif
Permettre au jury de **comprendre et reproduire** le travail DevOps.

### 📌 Tâches
Dans le `README.md` :
- Description de l’architecture DevOps.
- Schéma simple (ASCII ou image).
- Explication des étapes du pipeline CI/CD.
- Commandes exactes pour lancer le projet et le pipeline.

---

## 🧠 Ordre de Travail Recommandé
1. Docker Compose minimal fonctionnel
2. Healthchecks OK
3. Prometheus targets UP
4. Pipeline CI/CD minimal
5. Sécurité et tests
6. Dashboards Grafana
7. Polissage final

---

## 🏁 Conclusion
La Personne 2 joue le rôle d’un **DevOps / SRE professionnel**.
Si toutes ces tâches sont exécutées correctement, l’équipe peut prétendre à **30/30 en DevOps Implementation** et à un avantage décisif sur les autres équipes.

