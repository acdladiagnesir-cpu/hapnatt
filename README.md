# HapNatt

**Modélisation ouverte des partenariats public-privé.** Modéliser un contrat ou un secteur de bout en bout, sans tableur.
*Open modelling for public-private partnerships. Model a contract or a whole sector end to end, without spreadsheets.* — [English below](#english)

Logiciel libre de modélisation technico-financière des partenariats public-privé (PPP), tous secteurs : eau, assainissement, énergie, déchets, transport… On décrit les acteurs (autorité, société de patrimoine, exploitant, usagers, bailleurs) et les flux qui les relient. Le moteur calcule, période après période, les recettes, les charges, les comptes, la trésorerie et les tarifs de chacun.

**Le nom.** *Hap*, en sérère, veut dire estimer, évaluer ; *natt*, en wolof, veut dire mesurer. HapNatt évalue et mesure, avant de décider.

Copyright © 2026 A. C. Diagne. Distribué sous licence **GNU GPL v3 ou ultérieure** (voir [LICENSE](LICENSE)).

---

## Ce que fait le logiciel

- **Schéma du projet** : structures et flux (financiers ou physiques), dessinés et modifiés à la souris.
- **Formules lisibles** : `[volume_vendu] * [tarif]`, conditions, tables, fonctions personnelles. Les boucles (un intéressement qui dépend du résultat, par exemple) sont résolues automatiquement, avec un contrôle de convergence.
- **Périmètres** : le même modèle calculé par centre, par région ou par zone, avec une carte (OpenStreetMap) et une ligne Global.
- **Paiements réalistes** : taux de recouvrement, rattrapage des impayés, moratoires.
- **Tarifs** : trois scénarios comparés (tarifs actuels, tarifs de maintien du service, tarifs de financement des investissements), avec plafonds de hausse et tarifs sociaux fixes.
- **Résultats** : flux par périmètre avec les montants sur les flèches, synthèse, comptes, répartition de l'argent payé par les usagers, courbes, contrôles.
- **Sensibilité** : comparaison du calcul courant avec un calcul de référence (courbes en tirets, tableau des écarts).
- **Exports ouverts** : fichiers `.dat` en texte tabulé, CSV, PDF, PNG ; impression des schémas.
- **Interface en français et en anglais.**

## Installation

**Sous Windows, sans Python :** téléchargez l'archive `HapNatt-<version>-windows.zip` dans la page *Releases* du dépôt, décompressez-la et lancez `HapNatt.exe`. Vos modèles et les exemples sont rangés dans *Documents/HapNatt*.

**Depuis le code source :** Python 3.10 ou plus récent, puis une seule fois :

```
pip install -r requirements.txt
```

## Lancement

Ouvrir `ppp_interface.py` dans IDLE et appuyer sur **F5**, ou en ligne de commande :

```
python ppp_interface.py
```

Les réglages (fichier ouvert au démarrage, langue, fond de carte) sont des constantes en tête de `ppp_interface.py`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `ppp_interface.py` | Interface graphique (PySide6) |
| `ppp_moteur.py` | Moteur de simulation, résultats et exports |
| `ppp_prototype.py` | Modèle de données, lecture et écriture des `.dat`, analyse des formules |
| `ppp_langues.py` | Traductions français / anglais |
| `Exemple_Simulation.dat` | Exemple : concession d'eau (données fictives) |
| `Exemple_Perimetres.dat` | Exemple : même concession découpée en trois périmètres (données fictives) |
| `README_Formules.md` | Référence des formules et des calculs du moteur |
| `construire_exe.py` | Construction de l'exécutable Windows (F5 dans IDLE) ; fait aussi automatiquement sur GitHub à chaque version |

Toutes les données des exemples sont **fictives**.

## Données et vie privée

Le logiciel fonctionne sur l'ordinateur de l'utilisateur. Il ne collecte, n'envoie ni ne stocke **aucune donnée personnelle**. Les modèles sont de simples fichiers texte qui restent chez l'utilisateur. Seule exception : l'affichage de la carte télécharge des tuiles OpenStreetMap (voir [CONFIDENTIALITE.md](CONFIDENTIALITE.md)).

## Carte

Fond de carte © [contributeurs d'OpenStreetMap](https://www.openstreetmap.org/copyright), données sous licence ODbL. Les tuiles sont gardées en cache sur le disque, conformément à la [politique d'usage des tuiles](https://operations.osmfoundation.org/policies/tiles/). Un autre fond libre peut être choisi avec la constante `FOND_DE_CARTE`.

## Contribuer

Les signalements de bugs, propositions et contributions sont bienvenus : voir [CONTRIBUTING.md](CONTRIBUTING.md) et le [code de conduite](CODE_OF_CONDUCT.md).

## Formation et accompagnement

Formations à la modélisation PPP, modèles sectoriels prêts à l'emploi, études et accompagnement : écrire à **diagne.amicolle@gmail.com**.

## Contact

diagne.amicolle@gmail.com — questions, signalements (y compris au titre du [code de conduite](CODE_OF_CONDUCT.md)), propositions de partenariat.

## Objectifs de développement durable

ODD 6 (eau propre et assainissement), ODD 7 (énergie), ODD 9 (infrastructures), ODD 11 (villes durables) et cible **17.17** (partenariats public-privé efficaces).

---

<a id="english"></a>
## English

**HapNatt** is free software for the technical and financial modelling of public-private partnerships in any sector (water, sanitation, energy, waste, transport…). You describe the entities (authority, asset-holding company, operator, users, lenders) and the flows between them; the engine computes, period by period, each entity's revenue, costs, accounts, cash and tariffs.

- Project diagram edited with the mouse; readable formulas with automatic resolution of loops and a convergence check.
- Perimeters (by centre, region or zone) with an OpenStreetMap map and a Global line.
- Collection rates, arrears and moratoria; three tariff scenarios compared (current, service continuity, investment financing).
- Results: flows per perimeter, summary, accounts, where the users' money goes, curves, checks.
- Sensitivity: comparison with a reference run.
- Open exports: tab-separated `.dat` text files, CSV, PDF, PNG; diagram printing.
- French and English interface.

**Install:** on Windows, download `HapNatt-<version>-windows.zip` from the *Releases* page, unzip it and run `HapNatt.exe` (models are kept in *Documents/HapNatt*). From source: `pip install -r requirements.txt` (Python 3.10+). **Run:** open `ppp_interface.py` in IDLE and press F5, or `python ppp_interface.py`. Set `LANGUE_INTERFACE = "en"` at the top of the file for English.

**Contact:** diagne.amicolle@gmail.com

**Privacy:** the software runs locally and collects no personal data; only map tiles are downloaded from OpenStreetMap.

**The name:** *hap* means to estimate, to assess in Serer; *natt* means to measure in Wolof. HapNatt assesses and measures before deciding.

**Licence:** GNU GPL v3 or later. Copyright © 2026 A. C. Diagne. All example data are fictitious.

**SDGs:** 6, 7, 9, 11 and target 17.17 (effective public-private partnerships).
