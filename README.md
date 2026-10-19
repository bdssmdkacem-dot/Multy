# Multy — Pilotage financier

Site vitrine responsive et prototype de tableau de bord financier pour petites entreprises.

## Pages

- `index.html` : page d'accueil produit, fonctionnalités, aperçu du tableau de bord et FAQ.
- `app.html` : tableau de bord interactif avec indicateurs, graphique SVG, comptes fictifs et dernières transactions.

## Fonctionnalités de la démo

- Interface française et mise en page adaptée au mobile.
- Recherche instantanée dans les transactions.
- Export CSV des transactions visibles.
- Ajout local d'une opération de démonstration.
- Sélection d'une période et navigation entre sections.

## Lancer le projet

Aucune dépendance applicative ni compilation n'est nécessaire pour le site lui-même. Pour le servir localement :

```bash
python3 -m http.server 8000
```

Puis ouvrez http://localhost:8000. Le tableau de bord est accessible à `/app.html`.

## Tests automatisés

- `.github/workflows/validate.yml` vérifie la structure HTML, les titres, la langue et les identifiants.
- `.github/workflows/browser-and-pages.yml` lance Playwright sur Chromium desktop et mobile : navigation, recherche, période, ajout local, export CSV, menu mobile et débordement horizontal.
- Les rapports de workflow sont disponibles dans l'onglet Actions du dépôt.

## Publication avec Vercel

1. Connectez-vous à Vercel et choisissez **Add New → Project**.
2. Importez le dépôt GitHub `bdssmdkacem-dot/Multy` et sélectionnez la branche `main`.
3. Choisissez **Other** comme framework. Laissez la commande de build vide et le répertoire de sortie à la racine du dépôt (`.`) si ces paramètres sont demandés.
4. Cliquez sur **Deploy**. Vercel doit publier `index.html` à la racine et le tableau de bord à `/app.html`.
5. Après la première publication, les pushes sur `main` déclencheront normalement un nouveau déploiement. Les tests Playwright desktop/mobile restent exécutés par GitHub Actions, indépendamment de Vercel.

L'importation initiale et les autorisations GitHub doivent être confirmés dans votre session Vercel. Le déploiement n'est confirmé que lorsque Vercel affiche **Ready** et fournit une URL.

## Important

Multy est un prototype original inspiré des usages courants des logiciels de gestion financière. Il ne reproduit pas le code, la marque, les textes propriétaires ou les ressources graphiques de Pennylane. Les données sont fictives : aucune banque, facture réelle ou API comptable n'est connectée. Les opérations ajoutées dans le prototype restent dans la session du navigateur et ne sont pas un registre comptable durable.

## Avant une utilisation commerciale

1. Revue visuelle sur appareils réels et correction des défauts constatés.
2. Authentification, stockage durable, modèle de données et permissions.
3. Gestion réelle des factures, dépenses, rapprochement bancaire et journal d'audit.
4. API sécurisée, tests de sécurité, sauvegardes, conformité et politique de confidentialité.

Le prototype ne doit pas être utilisé pour stocker ou traiter des données financières réelles.
