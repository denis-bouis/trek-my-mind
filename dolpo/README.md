# Série Dolpo — structure d'accueil des visuels

Convention identique à `../3-cols-khumbu/` (cf. vault :
`10-PROJETS/2026-Trek-My-Mind/Réalisation/Outillage-Publication-Instagram.md`).

```
dolpo/
├── manifest.json          # manifest /masque-photos GLOBAL — titre/lieu/stat/gpx/citation par DATE de prise de vue
├── gpx/                    # traces Garmin .gpx (rapprochées par date via --init-manifest)
├── 00-manifeste/          # post ÉPINGLÉ « À propos » (hors série, hors chronologie) — présentation du compte
│   ├── photos/originaux/
│   ├── publication.json
│   └── shotlist.md         # shot-list images : A. « À propos »  ·  B. ouverture série Dolpo
├── 01-ouverture-dolpo/    # OUVERTURE de la série (cold open, arc émotionnel) — distinct de 02-l-approche
│   ├── photos/originaux/
│   └── publication.json
├── 02-l-approche/
│   └── ...
└── 24-le-sas-de-recompression/
```

## 1 épinglé + 1 ouverture + 23 posts (28 récits de `Récits-du-Dolpo.md`, deux fusions)
- **`00-manifeste`** (`ordre_publication: 0`) = post épinglé « À propos », présentation du **compte** (trajectoire
  du rêve d'Everest repris + thèse psychologique). Aligné sur la bio. Hors série, sans date.
- **`01-ouverture-dolpo`** (`ordre_publication: 1`) = ouverture de la **série Dolpo**, cold open : l'arc
  émotionnel (« parti pour en chier / revenu émerveillé » + triple basculement). Distinct de l'approche
  chronologique. Hors date. Texte `pret`.
- **`02-l-approche`** = récits 1→5 fusionnés (Istanbul, Kathmandou, Bhaktapur, trek urbain, Nepalgunj), 30/07→03/08.
- **`24-le-sas-de-recompression`** = récits 27→28 fusionnés (Pokhara, retour Kathmandou), 27/08→31/08.
- Les 21 autres posts = un récit chacun. Préfixe `NN` = ordre chronologique (à partir de `03`).

`publication.json` pré-rempli : `titre`, `lieu`, `acte`, `date_evenement`, `legende` (brouillon = proposition
littéraire du récit ; brouillon *fusionné* pour les deux montages ; texte validé pour `01`), + `dates_couvertes`
/ `notes` sur les posts multi-jours (`02`, `07-ringmo`, `10-shey-sumdho-gompa`, `24`).

## À compléter (Denis)
1. `python ~/Dev/masque-photos/masque_photos.py --serie . --init-manifest` : rapproche les .gpx par date,
   complète les dates manquantes du manifest.
2. `stat` (manifest) + `stats` (publication.json) : durée / distance / D+ / D- / altitude.
3. `couleur` du manifest : `#B44A1E` est un PLACEHOLDER — à caler sur la charte Trek My Mind.
4. `citation` par jour (cf. `Plan-de-publication-Dolpo.md`, les 6 actes).
5. `ordre_publication` : aujourd'hui = chronologie (sauf `00`/`01`). À revoir (effet cold open comme Khumbu).
6. `format` par post : carrousel N slides / photo unique / reel.
7. Photos dans chaque `photos/`, puis `--serie` : rendu + remplissage auto de `slides`.
8. `statut` → `pret` post par post une fois légende + slides validés.

## Posts multi-jours / sans date et `--serie`
`--serie` exige qu'un post ne porte qu'une seule date de photos. `00-manifeste`, `01-ouverture-dolpo`, les 2
montages (`02-l-approche`, `24-le-sas-de-recompression`) et les 2 jours doubles (`07-ringmo`,
`10-shey-sumdho-gompa`) se préparent hors `--serie` (masque-photos date par date, ou une seule date
stampée), puis `slides` rempli à la main.
