# Multy — Gestion financière pour le marché marocain

Multy est actuellement un site vitrine et un tableau de bord interactif de démonstration. Cette branche prépare l'adaptation du produit aux indépendants, commerçants et petites entreprises au Maroc.

## État actuel — transparence

- Interface de présentation en français.
- Exemples de montants affichés en dirhams (DH / MAD).
- Tableau de bord avec données fictives, recherche, filtre de période, ajout temporaire et export CSV.
- Publication statique possible avec GitHub Pages.
- **Pas encore un logiciel commercial de gestion** : aucune authentification, base de données, sauvegarde durable, gestion multi-entreprise ou intégration bancaire.
- Les chiffres et opérations de démonstration ne doivent pas être utilisés comme comptabilité réelle.

## Cible produit au Maroc

1. Indépendants et auto-entrepreneurs.
2. Commerçants et petites entreprises de services.
3. TPE/PME qui ont besoin de suivre factures, dépenses, paiements et trésorerie.
4. Parcours français et arabe, avec prise en charge correcte du RTL.
5. Devise principale MAD / DH, dates et formats adaptés au contexte marocain.

## Feuille de route commerciale

### Phase 1 — adéquation au marché et UX
- [x] Présenter clairement la cible marocaine et afficher les montants de démonstration en DH.
- [ ] Compléter l'interface bilingue français/arabe et tester RTL sur mobile.
- [ ] Revoir le parcours d'accueil, la navigation mobile et les appels à l'action avec des utilisateurs marocains.
- [ ] Ajouter une page tarifaire transparente et un formulaire de demande de démonstration.

### Phase 2 — fonctions métier
- [ ] Profil d'entreprise et coordonnées configurables.
- [ ] Clients, fournisseurs, produits/services et devis.
- [ ] Création de factures PDF, avoirs, échéances et suivi des paiements.
- [ ] Dépenses, catégories, justificatifs et rapports exportables.
- [ ] Numérotation documentée, journal d'activité et archivage.
- [ ] Règles de TVA configurables selon le régime applicable, sans supposer que tous les clients ont le même régime.

### Phase 3 — plateforme fiable
- [ ] Authentification et récupération de compte.
- [ ] API et base de données persistante.
- [ ] Isolation stricte des données entre entreprises et rôles d'équipe.
- [ ] Validation côté serveur, limitation des tentatives, gestion sécurisée des secrets.
- [ ] Sauvegardes testées, journalisation, supervision et procédure de restauration.
- [ ] Tests d'accessibilité, de sécurité, de charge et d'utilisation sur appareils Android réels.

### Phase 4 — lancement
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

## Développement et tests

```bash
npm install
npx playwright install --with-deps chromium
npm test
```

Les tests actuels valident les principaux parcours du prototype dans Chromium desktop/mobile. Ils ne prouvent ni la sécurité d'une future API, ni la conformité fiscale, ni le bon fonctionnement sur tous les téléphones réels.

## Publication

La branche `main` reste la version publiée. Les travaux de préparation commerciale sont isolés dans `commercial/morocco-foundation` pour revue et tests avant toute fusion.
