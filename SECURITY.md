# Politique de sécurité

WebGuard est un **projet portfolio académique** réalisé dans le cadre du Master IGOV
(Faculté des Sciences de Rabat, Université Mohammed V). Il n'est **pas exploité comme
un service en production** et n'expose aucune donnée d'utilisateurs réels.

Malgré ce statut, les rapports de vulnérabilités sont les bienvenus : ils contribuent
à la qualité du projet et à l'apprentissage de son auteur.

---

## Versions supportées

Seule la branche `main` est maintenue. Les anciens commits, tags et branches de
fonctionnalités ne reçoivent pas de correctifs de sécurité.

| Version       | Supportée |
| ------------- | --------- |
| `main` (HEAD) | Oui       |
| Autres        | Non       |

---

## Signaler une vulnérabilité

Merci de **ne pas ouvrir d'issue publique GitHub** pour les vulnérabilités de
sécurité. Privilégiez une divulgation responsable par email :

- **Email :** `omarchekroun39@gmail.com`
- **Objet recommandé :** `[WebGuard][SECURITY] <résumé court>`

Merci d'inclure si possible :

1. Une description du problème et de son impact potentiel.
2. Les étapes de reproduction (URL, requête, payload, version/commit concerné).
3. Toute preuve de concept (capture, requête HTTP, extrait de log).
4. Vos coordonnées si vous souhaitez être crédité dans le changelog.

### Engagement de réponse

- Accusé de réception sous **7 jours** maximum.
- Évaluation initiale (gravité, scope) communiquée dans les **14 jours**.
- Un correctif est appliqué sur `main` puis annoncé via le changelog.

### Hors périmètre

Les éléments suivants ne constituent pas, en l'état, des vulnérabilités exploitables :

- Manque de durcissement sur les déploiements de démonstration (Render/Fly.io)
  qui ne traitent pas de données réelles.
- Absence de protections anti-DDoS au niveau infrastructure.
- Résultats d'outils automatisés sans démonstration d'impact.
- Vulnérabilités nécessitant un accès physique ou compte administrateur déjà compromis.

---

## Périmètre couvert

| Composant              | Couvert |
| ---------------------- | ------- |
| Backend FastAPI        | Oui     |
| Worker Celery          | Oui     |
| Frontend React         | Oui     |
| Templates de rapports  | Oui     |
| Configurations Docker  | Oui     |
| Dépendances tierces    | Suivies via Dependabot |

Merci de votre contribution responsable.
