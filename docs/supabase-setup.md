# Configuration Supabase — Multy

## État et limites
Supabase Auth et PostgreSQL avec Row Level Security (RLS) sont le chemin retenu pour les nouveaux modules de données. Le projet est configuré dans `supabase-config.js` avec une URL et une clé publishable publique ; cela ne prouve pas que les migrations ont été appliquées ni que le projet est prêt pour des données réelles. Aucun secret serveur n'est stocké dans le dépôt. La page `facturation.html` utilise Supabase pour charger et enregistrer des brouillons après connexion, si les migrations sont présentes. Les visiteurs déconnectés voient toujours une démo. `app.html` et les autres modules ne sont pas encore reliés à Supabase.

## 1. Créer le projet
1. Créez un projet Supabase dédié à l'environnement de développement/test.
2. Gardez les paramètres régionaux et la résidence des données à l'esprit avant de choisir la région ; vérifiez les implications applicables au Maroc avec un professionnel compétent.
3. Dans Project Settings / API, copiez uniquement l'URL du projet et la clé **publishable** (ou la clé anon legacy). Ne partagez jamais la clé `service_role` ni une clé secrète.

## 2. Appliquer le schéma et les politiques
Dans SQL Editor ou avec Supabase CLI, appliquez les migrations dans l'ordre uniquement après avoir confirmé l'état du projet :

1. `supabase/migrations/20261022110000_multy_auth_rls.sql` ajoute profils, cabinets, membres, entreprises, transactions, journal d'audit, RLS et `create_initial_firm`.
2. `supabase/migrations/20261029120000_multy_invoicing.sql` ajoute les clients et brouillons de facture avec isolation par entreprise, règles d'accès par rôle et totaux calculés depuis les lignes.
3. `supabase/migrations/20261030120000_multy_transactions.sql` ajoute la date opérationnelle et la catégorie au registre des transactions.

La deuxième migration n'a pas été appliquée au projet Supabase réel. Elle doit d'abord réussir les tests PostgreSQL isolés (`tests/test_supabase_migrations.py`) et faire l'objet d'une revue de sécurité avant tout déploiement. Vérifiez le résultat dans Database / Tables et Authentication / Policies avant tout test.

La page Facturation utilise les migrations pour gérer les clients et brouillons, via une fonction transactionnelle soumise aux politiques RLS. Le tableau Transactions de `app.html` peut lire et créer des opérations datées et catégorisées via les politiques RLS existantes. Les indicateurs, prévisions, dépenses, comptabilité et autres modules du tableau de bord restent des exemples; aucune banque n'est connectée. La facturation ne permet que les brouillons ; numérotation, émission, avoirs, export PDF et paiements réels ne sont pas encore implémentés. La première version n'autorise pas les utilisateurs à ajouter eux-mêmes des membres ni à modifier les rôles. Les invitations, la révocation, les paiements et les documents nécessitent des flux supplémentaires. Les taux de TVA des lignes sont fournis par l'utilisateur sans taux par défaut ; leur traitement fiscal et les mentions légales doivent être validés par un professionnel marocain. Le journal d'audit évite de copier les coordonnées clients, descriptions de lignes et montants. Ses références sont volontairement sans clés étrangères pour éviter la réécriture de l'historique lors d'une suppression. Ce journal n'est pas un archivage externe inviolable ; configurez un export externe surveillé avant la production.

## 3. Configurer le site statique
`supabase-config.js` contient déjà l'URL et la clé publishable communiquées pour le projet. Ces deux valeurs sont prévues pour être visibles dans le navigateur ; RLS est donc obligatoire. N'y placez aucun mot de passe ni clé secrète.
Dans Authentication / URL Configuration, configurez :
- Site URL : l'URL du site de test/publication.
- Redirect URLs : l'URL exacte du site suivie de `/app.html`, et l'URL locale de développement utilisée pendant les tests.

La page `auth.html` fournit le formulaire d'inscription et de connexion, avec confirmation e-mail prise en charge par Supabase Auth. Elle appelle `create_initial_firm` uniquement si Supabase retourne une session immédiatement après l'inscription. Si la confirmation e-mail est activée, le compte est créé d'abord et le cabinet initial doit encore être provisionné après confirmation/connexion ; ce parcours doit être finalisé avant ouverture publique.

## 4. Paramètres Auth obligatoires avant toute ouverture
- Activer la confirmation e-mail.
- Configurer SMTP fiable pour les messages de confirmation et de récupération ; ne pas dépendre des limites d'envoi du service par défaut.
- Configurer les URL autorisées et tester les liens de confirmation et de récupération.
- Définir une politique de mot de passe, limitation des tentatives, CAPTCHA/anti-bot selon le risque, et alertes d'abus.
- Configurer récupération/réinitialisation de compte et tester l'expiration des sessions.
- Garder les inscriptions en mode pilote privé jusqu'à la revue complète.
- Ne jamais désactiver RLS pour « faire fonctionner » une requête.

## 5. Critères d'acceptation avant production
- Inscription avec confirmation e-mail, connexion, déconnexion et récupération du compte testées sur Android/mobile.
- Vérification que l'utilisateur A ne peut lire/modifier les cabinets, entreprises et transactions de l'utilisateur B, y compris via requêtes directes REST.
- Tests négatifs pour rôle lecture seule, entreprise inconnue, identifiant falsifié et utilisateur non authentifié.
- Les clés secrètes restent côté serveur ; la clé publishable n'est utilisée qu'avec des politiques RLS testées.
- Sauvegarde/restauration, surveillance, audit externe, politique de confidentialité et revue juridique terminées.
- Connexion du tableau de bord à une API/données persistantes et suppression des données fictives clairement validée avant toute utilisation comptable réelle.

## 6. Publication
GitHub Pages est statique : il ne fournit pas de serveur privé. La page d'authentification peut utiliser Supabase depuis le navigateur uniquement grâce à la clé publishable et aux politiques RLS. Toute opération privilégiée, intégration sensible ou clé secrète doit passer par un environnement serveur sécurisé.
