# Multy — Pilotage financier

Prototype web responsive d'un tableau de bord financier pour petites entreprises, développé dans le dépôt **Multy**.

## Aperçu

- Interface en français avec navigation latérale et adaptation mobile.
- Indicateurs de trésorerie, entrées, sorties et factures en attente.
- Graphique SVG de flux de trésorerie et comptes de démonstration.
- Tableau de transactions avec recherche instantanée.
- Export CSV des transactions visibles.
- Ajout local d'une opération de démonstration.
- Filtres de période et interactions de navigation.

## Lancer le projet

Aucune dépendance ni compilation n'est nécessaire : ouvrez `index.html` dans un navigateur moderne. Pour servir les fichiers localement, utilisez par exemple :

```bash
python -m http.server 8000
```

Puis ouvrez http://localhost:8000.

## Vérification

Le workflow GitHub Actions vérifie à chaque push et pull request la structure HTML essentielle et la présence des éléments interactifs attendus.

## Important

Ce dépôt contient un **prototype original inspiré des usages courants des logiciels de gestion financière**. Il ne reproduit pas le code, la marque, les textes propriétaires ou les ressources graphiques de Pennylane. Les données sont fictives : aucune banque, facture réelle ou API comptable n'est connectée. Les opérations ajoutées dans le prototype restent dans la session du navigateur.

## Suite recommandée

1. Captures visuelles et tests manuels sur mobile et ordinateur.
2. Authentification, stockage durable et modèle de données.
3. Gestion réelle des factures, dépenses, rapprochement bancaire et permissions.
4. API sécurisée, tests automatisés et conformité avant toute utilisation commerciale.
