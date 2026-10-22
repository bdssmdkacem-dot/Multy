# Multy — Pilotage financier

Site vitrine responsive et prototype de tableau de bord financier pour petites entreprises.

## Pages

- `index.html` : page d'accueil produit, fonctionnalités, aperçu du tableau de bord et FAQ.
- `app.html` : tableau de bord interactif avec transactions, connexion Supabase facultative et devise MAD.
- `facturation.html` : première interface de brouillons de factures, disponible après configuration Supabase et connexion.
- `depenses.html` : suivi des dépenses en MAD dans le registre commun des transactions.

## Fonctionnalités de la démo

- Interface française et mise en page adaptée au mobile.
- Recherche instantanée dans les transactions.
- Export CSV des transactions visibles.
- Ajout local d'une opération de démonstration.
- Préparation de brouillons de factures avec lignes, ICE/IF client, échéance et calculs HT/TVA/TTC en MAD quand Supabase est configuré.
- Enregistrement des dépenses fournisseur par date et catégorie, visibles aussi dans le registre global quand Supabase est configuré.
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

## Supabase setup (optional live mode)

The default dashboard remains a fictitious demo. To enable authenticated MAD transactions:

1. Create a Supabase project and apply the SQL files in `supabase/migrations/` in filename order.
2. Apply every migration in filename order, then enable email/password sign-in in Supabase Auth. Configure email confirmation as desired.
3. The project URL and public publishable key are configured in `supabase-config.js`. This key is intended for browser clients; never put a `service_role` key in the site. Open `/app.html?mode=live` to use Supabase; `/app.html` keeps the interactive demo available.
4. Serve the site over HTTP(S), open `/app.html`, create an account, then enter a cabinet and company name.

The initial firm, membership, company and audit event are created in one database transaction. Live transaction rows use MAD and are isolated by row-level security. The invoice draft RPC stores customer details and line totals atomically and limits writes to firm administrators and accountants. Drafts are deliberately unnumbered. They cannot be issued, sent, or treated as compliant invoices. VAT settings and mandatory invoice details must be validated with a Moroccan accountant and current official requirements before issuing real documents. Expense entries are written to the same transaction ledger and included in the net transaction balance. The live balance does not represent bank balances; this prototype has no bank feed, receipt capture, approvals, reconciliation, or complete accounting ledger.

## Existing Supabase project — required preflight

Before applying any SQL to an existing project, run the **read-only** catalog inspection in `supabase/diagnostics/20261022_live_schema_preflight.sql` and review all result sets. Follow `docs/supabase-existing-project-preflight.md` to compare current tables, columns, RLS policies, grants, functions and constraints with the intended schema.

Do not blindly replay the base migration in SQL Editor: named policies can cause duplicate-policy errors if that migration has already succeeded. The CI migration test uses a fresh temporary PostgreSQL database and does not establish whether replaying the SQL is safe against an existing project. No live migration should be considered applied until it succeeds against that target. No live-project migration is run by CI.

## Important

Multy est un prototype original inspiré des usages courants des logiciels de gestion financière. Il ne reproduit pas le code, la marque, les textes propriétaires ou les ressources graphiques de Pennylane. Les données sont fictives : aucune banque, facture réelle ou API comptable n'est connectée. Les opérations ajoutées dans le prototype restent dans la session du navigateur et ne sont pas un registre comptable durable.

## Avant une utilisation commerciale

1. Revue visuelle sur appareils réels et correction des défauts constatés.
2. Authentification, stockage durable, modèle de données et permissions.
3. Gestion réelle des factures, dépenses, rapprochement bancaire et journal d'audit.
4. API sécurisée, tests de sécurité, sauvegardes, conformité et politique de confidentialité.

Le prototype ne doit pas être utilisé pour stocker ou traiter des données financières réelles.
