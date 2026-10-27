# Sécurité et isolation multi-entreprises — critères de conception

## Statut actuel

Ce document fixe les critères à satisfaire avant de transformer le portefeuille comptable de démonstration en service multi-entreprises. Il ne constitue pas une preuve de sécurité ni une implémentation serveur.

Le produit actuel est un site statique : les entreprises et documents affichés sont des données fictives embarquées dans le navigateur. Il n'y a ni authentification, ni API, ni stockage persistant, ni contrôle d'accès côté serveur. **Ne jamais y déposer des données personnelles, comptables ou des documents réels.**

## Premier jalon de code (non déployable)

Le module `backend/access_policy.py` formalise une politique pure d'autorisation (administrateur de cabinet, comptable attribué à une entreprise, lecture seule) et `tests/test_access_policy.py` couvre notamment le refus inter-cabinets, les rôles inconnus et les mutations interdites. La CI exécute ces tests. Ce module n'est pas encore appelé par une API, ne charge pas d'identités depuis une base et ne protège donc pas les pages statiques. Il ne faut pas le présenter comme un contrôle d'accès actif.

## Modèle d'autorisation visé

Les identifiants et relations sont générés et vérifiés côté serveur. Le navigateur ne peut jamais définir lui-même son identité, son rôle, son cabinet ou les entreprises auxquelles il a accès.

Entités minimales proposées :

- `User` : compte utilisateur, état et identifiants d'authentification.
- `Firm` : cabinet comptable ou organisation.
- `Membership` : association utilisateur-cabinet avec rôle.
- `Company` : entreprise cliente, rattachée au cabinet ou à une relation de mandat explicite.
- `CompanyAccess` : autorisation explicite d'un utilisateur sur une entreprise si les rôles du cabinet ne suffisent pas.
- `Document` et `Transaction` : chaque enregistrement appartient à une entreprise.
- `AuditEvent` : acteur, action, cible, entreprise, horodatage et résultat, sans secrets ni contenu sensible inutile.

Toute lecture ou mutation de transaction, document, export ou rapport doit être autorisée côté serveur à partir de l'utilisateur authentifié et de l'entreprise cible. Un identifiant d'entreprise transmis par le client n'est jamais une preuve d'autorisation.

## Matrice de départ

| Action | Admin du cabinet | Collaborateur autorisé | Lecture seule |
|---|---:|---:|---:|
| Voir les entreprises attribuées | Oui | Oui | Oui |
| Voir documents et écritures autorisés | Oui | Oui | Oui |
| Ajouter/modifier des données | Oui | Selon autorisation | Non |
| Valider ou demander une pièce | Oui | Selon autorisation | Non |
| Inviter/révoquer des membres | Oui | Non par défaut | Non |
| Changer les rôles et accès | Oui | Non | Non |
| Exporter des données | Oui, journalisé | Selon autorisation | Non par défaut |
| Lire le journal d'audit | Oui, limité au cabinet | Non par défaut | Non |

Cette matrice est un point de départ à valider avec les utilisateurs et les obligations applicables, pas une politique déjà active.

## Tests d'acceptation obligatoires pour l'API

1. Un utilisateur sans session ne peut lire ni modifier aucune donnée privée.
2. Un utilisateur du cabinet A ne peut pas lire, modifier, supprimer, rechercher ou exporter une entreprise du cabinet B, même en remplaçant l'identifiant dans l'URL, le corps ou les paramètres.
3. Un collaborateur ne peut accéder qu'aux entreprises explicitement attribuées et aux actions permises par son rôle.
4. Un rôle lecture seule ne peut créer, modifier, supprimer, valider ou demander une pièce ; tester chaque endpoint, pas seulement les boutons UI.
5. Les requêtes en lot, recherches, téléchargements de fichiers, rapports, exports et routes secondaires appliquent les mêmes contrôles d'accès.
6. Les tests d'isolation couvrent les réponses positives autorisées et les réponses négatives inter-cabinets/inter-entreprises. Une réponse interdite ne révèle pas le contenu de la ressource.
7. Une révocation de membre ou d'accès prend effet côté serveur, y compris pour les sessions existantes selon la politique de session retenue.
8. Les opérations sensibles produisent un événement d'audit, sans mot de passe, jeton, clé ou contenu de document dans les journaux.
9. Les tests vérifient aussi les ID prévisibles, les ID inexistants, les changements de rôle, les exports et les erreurs.
10. Les migrations, sauvegardes et procédures de restauration sont testées avant d'accepter des données réelles.

## Conditions de passage à une vraie implémentation

- Choisir et documenter l'hébergement de l'API et de la base de données ; GitHub Pages ne peut héberger que la partie statique.
- Définir les secrets exclusivement dans l'environnement serveur, jamais dans le dépôt ou le navigateur.
- Ajouter des migrations, validation des entrées, gestion des sessions, limitation des tentatives et stratégie de sauvegarde/restauration.
- Mettre en place les tests d'autorisation dans la CI et exiger leur succès avant fusion.
- Vérifier la politique de conservation, les droits d'accès, la gestion des pièces et les obligations locales de protection des données avec un professionnel compétent.
- N'activer les inscriptions qu'après réussite des tests de sécurité et revue de confidentialité.

## Limites de ce jalon

Aucun backend ni contrôle de sécurité de production n'est ajouté par ce document. L'interface de démonstration ne doit pas être présentée comme une comptabilité en production. Le choix de la pile serveur reste ouvert et doit être validé avant d'ajouter des services exécutables et leurs dépendances.
