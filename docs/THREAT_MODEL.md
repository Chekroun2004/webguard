# Modèle de menaces — WebGuard

WebGuard est un scanner de vulnérabilités web. Par nature, il **émet du trafic
potentiellement intrusif** vers la cible que l'utilisateur soumet : crawl,
détection de fichiers sensibles, injections XSS et SQL réfléchies, sondes
TRACE/PUT/DELETE, etc. Cette capacité crée une surface d'attaque spécifique
qui doit être maîtrisée, sous peine de transformer le service en arme contre
des tiers depuis l'IP du worker.

Ce document recense les adversaires, les actifs à protéger, les vecteurs
d'attaque considérés et les mitigations associées.

---

## 1. Actifs

| Actif                                  | Sensibilité |
| -------------------------------------- | ----------- |
| Comptes utilisateurs (email + hash)    | Élevée      |
| Tokens JWT (access + refresh)          | Élevée      |
| IP / réputation du worker Celery       | Élevée      |
| Rapports de scan (vulns sur cibles)    | Moyenne     |
| Code source et templates de rapports   | Faible      |

## 2. Adversaires et motivations

| Adversaire                        | Motivation                                     |
| --------------------------------- | ---------------------------------------------- |
| Utilisateur authentifié malveillant | Détourner le scanner pour attaquer des cibles tierces depuis l'IP de WebGuard |
| Attaquant non authentifié         | Force brute / enumeration de comptes, abus de l'inscription |
| Propriétaire d'un site scanné     | Identifier l'origine du scan, riposter via le crawl |
| Attaquant supply-chain            | Compromettre une dépendance Python/npm         |
| Attaquant local (dev)             | Lire `.env`, intercepter le trafic local       |

---

## 3. Surface d'attaque

### 3.1 Détournement du scanner (menace principale)

Le risque structurel est qu'un utilisateur authentifié soumette des URLs ciblant
des sites qu'il ne possède pas. Le worker WebGuard générerait alors du trafic
intrusif (XSS, SQLi error-based, énumération de fichiers, OPTIONS TRACE)
depuis son IP, ce qui peut :

- engager la responsabilité juridique de l'opérateur ;
- aboutir au blacklistage de l'IP ;
- servir d'amplificateur (SSRF indirect) pour pivoter vers des cibles internes
  si le worker est déployé dans un VPC.

### 3.2 SSRF via la cible

Un utilisateur peut soumettre `http://169.254.169.254/...` (metadata cloud),
`http://localhost/...`, `http://127.0.0.1:6379` (Redis interne) etc.
Le worker effectuerait alors des requêtes vers des endpoints sensibles.

### 3.3 Authentification

- Force brute sur `/auth/login`.
- Vol de token JWT (XSS sur le frontend, fuite via logs).
- Réutilisation de refresh tokens compromis.

### 3.4 Rapports et templates

- Injection HTML dans le template Jinja2 de rapport PDF (XSS rendue en PDF).
- Lecture de rapports d'un autre utilisateur (IDOR sur `/scans/{id}`).

### 3.5 Supply chain

- Dépendances Python/npm avec CVE non patchées.
- Compromission d'une action GitHub.

---

## 4. Mitigations en place

| Menace                                      | Mitigation                                                                 |
| ------------------------------------------- | -------------------------------------------------------------------------- |
| Détournement du scanner                     | **Domain ownership verification** (fichier ou DNS TXT) — Étape 5           |
| Détournement du scanner                     | **Rate limiting** : 5 scans/h/user + 100 req/min/IP (slowapi) — Étape 9    |
| Détournement du scanner                     | **Pas de déploiement public ouvert** : projet portfolio, démo uniquement   |
| Force brute auth                            | Rate limiting global 100 req/min par IP                                    |
| Force brute auth                            | Hash argon2 (passlib) — coût CPU élevé                                     |
| IDOR sur scans                              | Filtrage `user_id` systématique dans les repositories                      |
| Vol JWT                                     | Durée de vie courte des access tokens + refresh rotation                   |
| Injection HTML en rapport                   | Jinja2 autoescape activé par défaut sur les templates                      |
| Scans bloqués / DoS interne                 | Watchdog Celery Beat (re-dispatch toutes les 5 min)                        |
| Supply chain                                | **Dependabot** (`.github/dependabot.yml`) — PRs hebdo                      |
| Qualité du code introduit                   | CI : ruff + black + eslint + tsc + pytest sur chaque PR                    |
| Hooks pré-commit                            | `.pre-commit-config.yaml` : ruff, black, end-of-file, trailing whitespace  |

---

## 5. Risques résiduels

1. **SSRF non bloqué** : aucune allowlist d'IP/CIDR n'est appliquée côté worker.
   Un utilisateur peut soumettre `http://169.254.169.254` ou `http://10.0.0.1`.
   *Atténuation partielle* : ownership verification empêche le scan sans preuve
   de contrôle du domaine, mais pas les IPs nues.

2. **Crédibilité de l'ownership par fichier** : si la cible héberge un proxy
   open redirect, l'attaquant peut servir le fichier de vérification depuis
   un autre serveur.

3. **Absence de WAF / antivirus** sur les payloads stockés (evidence) :
   les valeurs `evidence` JSON peuvent contenir du HTML/JS d'attaquant.
   L'affichage frontend doit échapper (React le fait par défaut).

4. **Pas de signature des rapports PDF** : un rapport peut être altéré
   après téléchargement. Hors scope pour un projet portfolio.

5. **Logs non centralisés** : pas de SIEM, pas de détection d'anomalie sur
   les volumes de scans. Le rate limiting est la seule barrière.

6. **Secrets en `.env`** : si le repo est cloné sur un poste partagé, la
   `SECRET_KEY` peut fuiter. Le `.env.example` ne contient que des placeholders.

---

## 6. Améliorations futures envisagées

- Allowlist d'IPs / blocklist RFC1918 + métadonnées cloud côté `httpx` client.
- Headless captcha à l'inscription.
- 2FA TOTP pour les comptes admin.
- Signature détachée (PGP) des rapports PDF.
- Audit log immuable des scans déclenchés (qui, quand, vers quelle cible).
