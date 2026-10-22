# Configuration Supabase — Multy

## État et limites
Cette branche prépare l'intégration Supabase Auth et le schéma PostgreSQL avec Row Level Security (RLS). Aucun projet Supabase n'est encore connecté à ce dépôt et aucune clé réelle n'est enregistrée. L'inscription ne fonctionnera qu'après configuration du projet et application de la migration. Le tableau de bord `app.html` reste une démo locale : il n'est pas encore connecté aux tables Supabase et ses opérations ne sont pas persistantes.

## 1. Créer le projet
1. Créez un projet Supabase dédié à l'environnement de développement/test.
2. Gardez les paramètres régionaux et la résidence des données à l'esprit avant de choisir la région ; vérifiez les implications applicables au Maroc avec un professionnel compétent.
3. Dans Project Settings / API, copiez uniquement l'URL du projet et la clé **publishable** (ou la clé anon legacy). Ne partagez jamais la clé `service_role` ni une clé secrète.

## 2. Appliquer le schéma et les politiques
Dans SQL Editor, exécutez `supabase/migrations/20261022110000_multy_auth_rls.sql`.
La migration ajoute les profils, cabinets, membres, entreprises, transactions, journal d'audit, RLS et la fonction `create_initial_firm`. Vérifiez le résultat dans Database / Tables et Authentication / Policies avant tout test.

La première version n'autorise pas les utilisateurs à ajouter eux-mêmes des membres ni à modifier les rôles. Les invitations, la révocation, la gestion complète des entreprises et les documents nécessitent des flux serveur supplémentaires. Le journal d'audit de cette migration n'est pas un archivage externe inviolable ; configurez un export externe surveillé avant la production.

## 3. Configurer le site statique
Modifiez `supabase-config.js` en remplaçant les chaînes vides par l'URL et la clé publishable. Ces deux valeurs sont prévues pour être visibles dans le navigateur ; RLS est donc obligatoire. N'y placez aucun mot de passe ni clé secrète.
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
