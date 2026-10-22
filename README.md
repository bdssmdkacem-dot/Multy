# Multy — Gestion financière pour le marché marocain

Multy est actuellement un site vitrine et un tableau de bord interactif de démonstration. Cette branche prépare l'adaptation du produit aux indépendants, commerçants et petites entreprises au Maroc.

## État actuel — transparence

- Interface de présentation en français.
- Exemples de montants affichés en dirhams (DH / MAD).
- Tableau de bord avec données fictives, recherche, filtre de période, ajout temporaire et export CSV.
- Publication statique possible avec GitHub Pages.
- **Pas encore un logiciel commercial de gestion** : aucune authentification, base de données, sauvegarde durable, gestion multi-entreprise ou intégration bancaire.
- Les chiffres et opérations de démonstration ne doivent pas être utilisés comme comptabilité réelle.

## Supabase — intégration en préparation\n\n- [x] Ajouter une page d’inscription/connexion et un modèle initial PostgreSQL avec RLS sur la branche de travail.\n- [ ] Renseigner l’URL Supabase et la clé publishable du projet de test dans `supabase-config.js`.\n- [ ] Appliquer `supabase/migrations/20261022110000_multy_auth_rls.sql` et vérifier les politiques avec deux utilisateurs de test.\n- [ ] Finaliser confirmation e-mail, récupération de compte, SMTP et tests d’isolation.\n- [ ] Connecter le tableau de bord aux données persistantes avant toute utilisation réelle.\n\nLa page d’authentification ne fonctionne pas tant que le projet Supabase n’est pas configuré. Ne jamais placer une clé `service_role` dans le site statique. Détails : `docs/supabase-setup.md`.\n\n## Cible produit au Maroc

1. Indépendants et auto-entrepreneurs.
2. Commerçants et petites entreprises de services.
3. TPE/PME qui ont besoin de suivre factures, dépenses, paiements et trésorerie.
4. **Comptables indépendants et cabinets fiduciaires**, considérés comme une cible principale dès la conception.
5. Parcours français et arabe, avec prise en charge correcte du RTL.
6. Devise principale MAD / DH, dates et formats adaptés au contexte marocain.

## Feuille de route commerciale

### Phase 1 — adéquation au marché et UX
- [x] Présenter clairement la cible marocaine et afficher les montants de démonstration en DH.
- [ ] Compléter l'interface bilingue français/arabe et tester RTL sur mobile.
- [ ] Revoir le parcours d'accueil, la navigation mobile et les appels à l'action avec des utilisateurs marocains.
- [ ] Ajouter une page tarifaire transparente et un formulaire de demande de démonstration.

### Phase 2 — première priorité : espace comptable multi-entreprises
- [x] Ajouter un premier parcours visuel de portefeuille multi-entreprises dans la démo, avec sélection, recherche et ajout temporaire d'une entreprise fictive.
- [x] Ajouter un flux de revue documentaire de démonstration : liste de pièces fictives, filtre par statut, validation et demande de pièce, sans téléversement ni sauvegarde durable.
- [ ] Construire l'espace de cabinet comptable persistant, capable de gérer plusieurs entreprises clientes depuis un compte professionnel.
- [x] Documenter le modèle d'autorisation cible et les critères d'acceptation d'isolation côté serveur (`docs/security-and-multitenancy.md`). Ce document est une spécification, pas une sécurité déjà implémentée.
- [ ] Séparer strictement les données et documents de chaque entreprise côté serveur ; aucune donnée ne doit être visible d'un autre client sans autorisation explicite.
- [ ] Ajouter l'invitation des collaborateurs, des rôles minimaux (administrateur du cabinet, collaborateur, lecture seule) et des autorisations par entreprise.
- [ ] Prévoir une boîte de réception des pièces, leur classement, leur statut de revue et les demandes de documents manquants. Le panneau de démonstration actuel n'est pas un stockage documentaire.
- [ ] Ajouter un journal d'audit consultable pour les accès et modifications importantes.
- [ ] Tester les parcours avec au moins un comptable marocain avant de considérer le flux métier validé.

### Phase 3 — fonctions de gestion et comptabilité
- [ ] Profil d'entreprise et coordonnées configurables.
- [ ] Clients, fournisseurs, produits/services et devis.
- [ ] Création de factures PDF, avoirs, échéances et suivi des paiements.
- [ ] Dépenses, catégories, justificatifs et rapports exportables.
- [ ] Imports contrôlés CSV/Excel pour relevés et écritures, avec prévisualisation, détection des doublons et rapport d'erreurs.
- [ ] Exports par entreprise et période pour faciliter le travail du comptable ; tout export doit respecter les permissions et être traçable.
- [ ] Numérotation documentée, journal d'activité et archivage.
- [ ] Règles de TVA configurables selon le régime applicable, sans supposer que tous les clients ont le même régime.

### Phase 4 — infrastructure et fiabilité (avant d'ouvrir les inscriptions)
- [ ] API et base de données persistante, d'abord sur un environnement de test.
- [ ] Modèle de données multi-entreprises et séparation vérifiable des données.
- [ ] Validation côté serveur, gestion sécurisée des secrets, journalisation et sauvegardes.
- [ ] Tests d'autorisation et de sécurité sur les scénarios d'accès inter-entreprises.
- [ ] Tests d'accessibilité, de charge et d'utilisation sur appareils Android réels.

### Phase 5 — inscription et ouverture des comptes (dernière grande étape produit)
- [ ] Concevoir puis tester l'inscription, la connexion, la vérification de l'adresse e-mail et la récupération de compte.
- [ ] Activer les rôles et autorisations côté serveur avant toute utilisation de données réelles.
- [ ] Tester les parcours d'inscription et de connexion sur mobile, les erreurs, les sessions et la récupération de compte.
- [ ] Ouvrir les inscriptions uniquement après revue de sécurité, confidentialité et restauration des sauvegardes.

### Phase 6 — lancement
- [ ] Revue juridique et fiscale au Maroc avec un professionnel qualifié avant de présenter les documents comme conformes.
- [ ] Évaluer les formalités applicables auprès de la CNDP au titre de la loi 09-08, notamment si des données personnelles sont traitées ou hébergées à l'étranger.
- [ ] Conditions d'utilisation, politique de confidentialité, politique de conservation et suppression des données.
- [ ] Choix du prestataire de paiement et validation des moyens de paiement disponibles au Maroc.
- [ ] Offre d'essai, abonnements, facturation de l'abonnement et support client.
- [ ] Pilote avec un petit groupe de professionnels marocains avant commercialisation publique.

## Conformité — points à vérifier, pas une certification

La configuration fiscale varie selon le statut et l'activité. Ne pas imposer un taux de TVA par défaut à tous les utilisateurs. La génération de factures destinées à un usage réel doit faire l'objet d'une validation fiscale et juridique locale. La loi marocaine 09-08 et les démarches CNDP applicables doivent être examinées avant de collecter des données personnelles en production.

Références officielles de départ :
- CNDP — loi 09-08 et obligations : https://www.cndp.ma/conditions/
- CNDP — textes et lois : https://www.cndp.ma/textes-et-lois/
- Ministère de l'Industrie et du Commerce — statut auto-entrepreneur : https://www.mcinet.gov.ma/fr/content/auto-entrepreneur

## Private pilot API foundation (not production-ready)

A first API slice now exists under `backend/main.py` using FastAPI and SQLAlchemy, with PostgreSQL schema in `backend/schema.sql`. It provides health, assigned-company listing, and tenant-scoped transaction list/create endpoints. The server checks a signed bearer JWT using a fixed HS256 allowlist, requires `sub`, `iat`, `exp`, `iss=multy-api`, and `aud=multy-client`, rejects lifetimes over 15 minutes, and fails closed when the configured secret is shorter than 32 UTF-8 bytes. It then loads the active user and company membership from the database for each request; role claims from the token are not trusted. A user with `read_only` membership cannot create transactions. Registration and token issuance are deliberately not implemented.

### Request-tampering and append-only audit controls

The API's company scope is derived from the authorized URL and the caller's current database membership, not a client-supplied `company_id` field. The API test suites include forged-body scope attempts, an unassigned company within the same firm, invalid currency/amount/description inputs, membership revocation, role changes, and inactive-user token rejection.

Migration `0003_append_only_audit` removes cascading foreign-key behavior from historical actor/company references and installs a PostgreSQL trigger that rejects UPDATE and DELETE on `audit_logs`. Audit events intentionally avoid storing transaction descriptions and amounts. This protects against ordinary application/database-role mutation while the trigger is active; a database owner or superuser can still alter schema or disable triggers, so production needs restricted database roles, monitored privileged access, backups, and external log retention. The test workflow verifies the trigger on PostgreSQL; SQLite unit tests do not prove this database-specific control.

### Authorization freshness and audit events

- Every authenticated API request resolves the user from the database and rejects an inactive user, so disabling a user affects already-issued bearer tokens on the next request.
- Company membership and role are read from the database for each company-scoped request. Removing membership denies the next request; changing a member to `read_only` blocks the next write without requiring a new token.
- Creating a transaction and its `transaction.created` audit event happen in the same database transaction. The audit row stores actor, company, action, entity reference, currency metadata, and timestamp; it deliberately does not copy the transaction description or amount into the audit details.
- The API currently has no endpoints for managing memberships or roles. Tests change those records directly in the test database to verify enforcement, not to claim a complete administration workflow. Audit rows are not exposed through an API, and external immutable log retention is not implemented; production database privileges, retention, monitoring, and tamper-resistance still need a separate hardening review.

### PostgreSQL and live-container integration

The `Multy PostgreSQL integration` workflow starts PostgreSQL 16, applies `backend/schema.sql`, runs the tenant-isolation suite against the real PostgreSQL engine, builds the API container, then launches it and tests the HTTP endpoints with a signed test token and seeded synthetic tenants. It verifies that the live API only lists the assigned company and returns 404 when the same user attempts to read another tenant. This is CI integration evidence, not a production deployment or an independent security audit.

### Run API tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests/test_api.py
python -m unittest discover -s tests -p 'test_access_policy.py' -v
```

### Run a local PostgreSQL/API environment

Set a strong, unique `POSTGRES_PASSWORD` and a separate random `MULTY_JWT_SECRET` in your shell environment, then run:

```bash
docker compose -f docker-compose.api.yml up --build
```

The local database port is bound to loopback only. **This Compose setup is development-only:** its bootstrap `multy` PostgreSQL account is a superuser and is currently reused by the API for queries and migrations. Do not deploy this configuration. Production must split a non-owner, least-privilege runtime role from a migration role. The API container now runs as non-root UID/GID `10001`. Alembic revisions under `migrations/` are the canonical versioned schema path; the API container runs `alembic upgrade head` before starting. Existing databases previously initialized directly from `backend/schema.sql` need a reviewed baseline/adoption procedure before switching to Alembic. Do not use the sample environment for production.

**Security boundary:** this is a backend foundation, not yet a production service. There is no login/token issuer, no account provisioning workflow, no production HTTPS/reverse-proxy configuration, no rate limiting, no external/immutable audit-log retention, no verified backup/restore drill, and the static dashboard is not connected to this API. The API container runs Alembic migrations at startup in the current prototype, but production migration ownership, least-privilege database roles, and rollout/rollback procedures are not yet established. JWT authentication now requires `iss=multy-api`, `aud=multy-client`, `iat`, `exp`, and a lifetime no longer than 15 minutes, and fails closed if the configured secret is shorter than 32 UTF-8 bytes; use a unique cryptographically random secret and never reuse CI values. No token issuer exists yet, so any future issuer must follow this exact claim policy. Keep public registration closed and do not enter real customer or accounting data until deployment hardening and independent authorization/security tests pass.

## Développement et tests

```bash
npm install
npx playwright install --with-deps chromium
npm test
```

Les tests actuels valident les principaux parcours du prototype dans Chromium desktop/mobile, dont la recherche et la sélection d'entreprises (avec assertion de l'état sélectionné pour éviter la régression du sélecteur) ainsi que la revue temporaire de documents fictifs. Ils ne prouvent ni la sécurité d'une future API, ni la conformité fiscale, ni le bon fonctionnement sur tous les téléphones réels.

**Ordre de livraison convenu :** avancer phase par phase, valider chaque étape avant de passer à la suivante et réserver les écrans d'inscription et d'ouverture des comptes à la dernière étape. هذا لا يعني تأجيل تصميم الأمان: يجب بناء صلاحيات وعزل بيانات آمنين قبل السماح بأي حسابات أو بيانات حقيقية.

## Publication

La branche `main` reste la version publiée. Les travaux de préparation commerciale sont isolés dans `commercial/morocco-foundation` pour revue et tests avant toute fusion.
