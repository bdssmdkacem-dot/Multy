# Multy — revue de sécurité pré-lancement

Date de revue : 2026-10-21  
Branche examinée : `commercial/morocco-foundation`  
Statut : **bloqué pour les données réelles et l'ouverture publique**.

Cette revue est une inspection de code et des tests CI, pas un audit indépendant ni une certification.

## Contrôles observés dans le code

- JWT vérifié avec une liste d'algorithmes fixe (`HS256`), signature et expiration obligatoires.
- La configuration d'authentification échoue fermée si le secret contient moins de 32 octets UTF-8.
- L'identité vient du claim `sub`, puis l'utilisateur actif est chargé en base à chaque requête.
- Les entreprises et rôles sont lus depuis les relations de base de données; les rôles déclarés dans le token ne sont pas utilisés.
- L'appartenance explicite est requise pour les routes d'entreprise; les tentatives inter-entreprises renvoient 404.
- Les membres `read_only` ne peuvent pas créer d'écritures.
- L'écriture d'une transaction et son événement `transaction.created` sont validés dans la même transaction SQL.
- PostgreSQL bloque UPDATE/DELETE sur `audit_logs` lorsque le trigger append-only est actif.
- Les tests d'intégration PostgreSQL utilisent des identités et données synthétiques.

## Blocages avant toute donnée réelle

1. **JWT / sessions** — aucun émetteur de jetons n'est implémenté. Définir et tester une politique d'émetteur/audience, la durée de vie maximale, la rotation/révocation et les clés par environnement avant de créer un flux de connexion.
2. **Couverture des autorisations** — l'API n'a actuellement que health, liste des entreprises, et lecture/création de transactions. Les rôles complets de cabinet ne sont pas implémentés; la politique dans `backend/access_policy.py` est un module de conception et n'est pas branchée aux routes.
3. **Base de données** — constat bloquant confirmé : `docker-compose.api.yml` crée l'utilisateur `multy` via `POSTGRES_USER`, et l'API réutilise ce même compte pour ses requêtes et ses migrations. Le compte d'initialisation PostgreSQL est superutilisateur; ce fichier est maintenant explicitement marqué développement local uniquement. La production doit créer un rôle runtime non propriétaire à privilèges minimaux, séparer le rôle de migration, limiter l'accès réseau et protéger les secrets. Le rôle qui peut exécuter les migrations ou posséder le schéma peut contourner le trigger d'audit.
4. **Audit externe** — le trigger PostgreSQL empêche les modifications ordinaires mais n'est pas un journal inviolable. Aucune exportation vers un stockage externe append-only/immuable, alerte ou surveillance privilégiée n'est configurée.
5. **Disponibilité et récupération** — pas de limitation de débit, de plan de réponse aux incidents ni de preuve d'exercice de restauration de sauvegarde. Définir aussi les délais de conservation et la suppression des données.
6. **Déploiement** — l'API n'est pas déployée comme service de production et le tableau de bord statique n'est pas connecté à l'API. Le conteneur API a été renforcé pour s'exécuter sous UID/GID non-root `10001`, mais cela ne remplace pas la séparation des rôles SQL ni la configuration de production. GitHub Pages ne fournit pas l'exécution de l'API.
7. **Interface publiée** — le workflow Playwright teste le dépôt local dans Chromium desktop/mobile. Le déploiement Pages est volontairement limité à `main`; le succès des tests de branche ne prouve donc pas que la version publique correspond à ce commit. Faire une vérification visuelle et interactive sur l'URL publiée après un déploiement autorisé.
8. **Écart entre branche et site public (constaté le 2026-10-21)** — la capture Playwright du site public montre encore des montants en euros (€) et l'ancien en-tête « LE PILOTAGE FINANCIER, SANS COMPLEXITÉ », alors que la branche de travail cible le Maroc et le MAD/DH. Le premier test public a aussi échoué sur mobile car le sélecteur choisissait un lien de connexion caché au lieu du bouton visible; ce sélecteur a été corrigé. Le site public reste non conforme tant que la vérification relancée ne confirme pas le bon contenu marocain. Ne pas fusionner pour faire passer le test sans la revue d'acceptation demandée.
9. **Confidentialité et conformité** — valider les obligations marocaines applicables, la résidence/transfert des données, les contrats, la politique de confidentialité et les règles de conservation avec des professionnels compétents.

## Résultats CI à distinguer

Les tests précédents sur le commit `045a2d495056` ont passé 15 tests PostgreSQL et 25 tests Playwright. Ces résultats ne couvrent pas les changements de sécurité faits dans cette revue; attendre les nouvelles exécutions CI sur le nouveau HEAD avant d'accepter ces changements.

## Critères de sortie

- [ ] Tests CI verts sur le HEAD actuel.
- [ ] Tests JWT couvrant secret faible, signature incorrecte, algorithme non autorisé, expiration, issuer/audience incorrects et durée de vie excessive.
- [ ] Matrice d'autorisation exhaustive pour chaque route et chaque rôle.
- [ ] Rôle runtime PostgreSQL à privilèges minimaux et rôle de migration séparé; aucun compte superutilisateur utilisé par l'API.
- [ ] Export d'audit externe immuable, surveillance et procédures d'alerte testées.
- [ ] Sauvegarde/restauration testée et migration/rollback documentés.
- [ ] Vérification visuelle et interactive sur le site réellement publié, y compris devise MAD/DH, absence de montants en euros, navigation mobile et interactions du tableau de bord.
- [ ] Revue indépendante de sécurité et confidentialité terminée.
- [ ] Aucune donnée réelle tant que tous les critères bloquants ne sont pas validés.
