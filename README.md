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

Aucune dépendance ni compilation n'est nécessaire : ouvrez `index.html` dans un navigateur moderne. Pour servir le site localement :

```bash
python -m http.server 8000
```

Puis ouvrez http://localhost:8000. Le tableau de bord est accessible à `/app.html`.

## Vérification

GitHub Actions vérifie les fichiers HTML essentiels et la présence des éléments interactifs attendus à chaque push et pull request.

## Important

Multy est un prototype original inspiré des usages courants des logiciels de gestion financière. Il ne reproduit pas le code, la marque, les textes propriétaires ou les ressources graphiques de Pennylane. Les données sont fictives : aucune banque, facture réelle ou API comptable n'est connectée. Les opérations ajoutées dans le prototype restent dans la session du navigateur.

## Suite recommandée

1. Captures visuelles et tests manuels sur mobile et ordinateur.
2. Authentification, stockage durable et modèle de données.
3. Gestion réelle des factures, dépenses, rapprochement bancaire et permissions.
4. API sécurisée, tests automatisés et conformité avant toute utilisation commerciale.
