# HapNatt : formules

*Copyright © 2026 A. C. Diagne. Documentation du logiciel libre, distribuée sous licence GNU GPL v3 avec le code.*

Ce document décrit ce que le logiciel sait calculer aujourd'hui : les formules que vous écrivez, et celles que le moteur applique seul.

## 1. Écrire une formule

Une formule s'écrit dans l'onglet 3. Flux, l'onglet 4. Paramètres, la fiche d'un bloc ou l'onglet 7. Post-traitement.

| Élément | Écriture | Exemple |
|---|---|---|
| Variable | `nom[structure]` | `volume_vendu[exploitant]` |
| Valeur commune | `nom[projet]` | `taux_eur_fcfa[projet]` |
| Nombre avec unité | `valeur [unité]` | `12 [FCFA]` |
| Opérations | `+  -  *  /  ^` | `prix[b] * (1 + inflation[projet]) ^ t_an` |
| Comparaisons | `==  !=  <  <=  >  >=` | `t[mois] >= 7` |
| Logique | `et  ou  non` | `t[mois] >= 7 et t[mois] <= 10` |

`Exemple_Simulation.dat` contient une mise en données complète : formules, états initiaux, tables, cadre de simulation. Il s'ouvre au démarrage du logiciel, et il suffit de lancer la simulation.

Le séparateur décimal est le point : `0.05`. Un flux va du payeur au bénéficiaire, et sa variable appartient au bénéficiaire.

Renommer une structure ou un flux, ou changer le bénéficiaire d'un flux, change l'identifiant de sa variable : toutes les formules qui l'écrivent suivent automatiquement (paramètres, valeurs par périmètre, paiements, capacités, post-traitement, corps des fonctions, réglages des tarifs).

## 2. Le temps

**Le temps du modèle est t = t0 + t\*.** t0 est la date de démarrage. t\* s'écrit `t_sim`, vaut 0 au démarrage, puis n fois le pas de temps.

| Variable | Sens | Unité | Pas annuel, démarrage le 01/01/2029 |
|---|---|---|---|
| `t` | temps du modèle | référence | 2029, 2030, 2031 |
| `t0` | date de démarrage | référence | 2029 |
| `t_sim` | t\* = n × pas de temps | référence | 0, 1, 2 |
| `t_jour` | t\* en jours réels | jour | 0, 365, 730 |
| `t_mois` | t\* en mois | mois | 0, 12, 24 |
| `t_an` | t\* en années | an | 0, 1, 2 |
| `t[annee]` ou `annee` | année du calendrier | aucune | 2029, 2030, 2031 |
| `t[mois]` | mois du calendrier, de 1 à 12 | aucune | 1, 1, 1 |
| `t[jour]` | jour du mois, de 1 à 31 | aucune | 1, 1, 1 |
| `tau_t` | durée du pas, en années | temps | 1, 1, 1 |
| `jours_t` | durée du pas, en années | temps | 1, 1, 1 |

- Chaque pas est repéré par sa date de début.
- Dans les formules, ces variables sont de simples nombres, sauf `tau_t` et `jours_t`, qui portent une durée.
- Pour une croissance, utilisez le temps interne : `demande_initiale[usagers] * (1 + croissance[usagers]) ^ t_an`.
- Si le temps de référence n'est pas l'an, `t0` est compté depuis l'année 0 : 24 348 en mois pour 2029.

## Fonctions de l'utilisateur

L'onglet 9. Fonctions définit des fonctions réutilisables. Une fonction a un nom, des arguments et un calcul écrit ligne par ligne : chaque ligne définit un paramètre interne, la dernière s'écrit `résultat = ...`.

```
annuite(montant, taux, duree)
    facteur = si(taux == 0, duree, (1 - (1 + taux) ^ (-duree)) / taux)
    résultat = montant / facteur
```

Elle s'appelle ensuite dans n'importe quelle formule : `annuite(cout_investissement[societe_de_patrimoine, p], 0.08, 15)`.

- **Ce qu'une fonction peut lire :** ses arguments, ses paramètres internes et les valeurs communes `[projet]`. Toute autre variable doit lui être passée en argument.
- **Ce qu'elle ne peut pas utiliser :** `lag`, `lead`, `cumul`, les cumuls par période, les agrégations par périmètre et les fonctions de post-traitement. Ils s'écrivent dans la formule qui appelle la fonction.
- **Appels entre fonctions :** une fonction peut en appeler une autre, mais jamais elle-même, même par un détour.
- **Calcul :** au lancement, chaque appel est remplacé par le calcul de la fonction. Les unités sont donc contrôlées comme dans une formule ordinaire.
- **Test :** le bouton Tester calcule un appel avec des valeurs d'essai, par exemple `1000000000 [FCFA], 0.08, 15`.
- **Protection :** une fonction utilisée dans une formule ne peut être ni supprimée ni renommée.

**Bibliothèque de départ**

| Fonction | Calcul |
|---|---|
| `annuite(montant, taux, duree)` | montant × taux / (1 − (1 + taux)^(−durée)) ; montant / durée si le taux est nul |
| `amortissement_lineaire(montant, duree)` | montant / durée |
| `tarif_tranches(volume, prix_social, prix_normal, seuil)` | min(volume, seuil) × prix social + max(volume − seuil, 0) × prix normal |
| `indexation(prix, taux, annees)` | prix × (1 + taux)^années |
| `cout_ouvrage(type, taille, taille_reference, cout_reference)` | coût de référence × (taille / taille de référence)^exposant |

Pour `cout_ouvrage`, le type s'écrit entre guillemets et fixe l'exposant d'économie d'échelle : `"usine"` 0,7 ; `"forage"` 0,8 ; `"reservoir"` 0,6 ; `"conduite"` 1 ; `"pompage"` 0,65 ; autre type 1. Ces exposants sont indicatifs : adaptez-les dans la fonction. La taille et la taille de référence doivent avoir la même unité.

## Périmètres

L'onglet 2. Périmètres contient la table des périmètres : une ligne par périmètre p, une colonne par groupe (centre, région, zone…). Elle se modifie dans le logiciel ou s'importe depuis un fichier .csv ou .txt (première colonne : le périmètre ; colonnes suivantes : les groupes ; séparateur point-virgule, tabulation ou virgule).

La ligne Global est toujours présente : elle regroupe tous les périmètres, et sans périmètre tout le modèle est Global. Le nom « Global » est réservé.

Coordonnées : une colonne nommée X (ou Longitude) et une colonne Y (ou Latitude), en degrés décimaux WGS 84, placent chaque périmètre sur la carte de la nouvelle interface. Ces deux colonnes ne sont pas des groupes. Le fond de carte (constante FOND_DE_CARTE, un nom xyzservices) est mis en cache dans le dossier cache_carte ; sans connexion, la carte garde les tuiles déjà vues ou un quadrillage en degrés.

| Écriture | Sens |
|---|---|
| `demande[usagers, p]` | variable par périmètre ; dans sa formule, `p` est le périmètre courant |
| `demande[usagers, Thiès]` | la valeur d'un périmètre précis |
| `somme_p(demande[usagers, p])` | somme sur tous les périmètres |
| `somme_p(demande[usagers, p], "Région:Thiès")` | somme sur un groupe ; `"Thiès"` suffit si ce nom n'est pas ambigu |
| `moyenne_p`, `max_p`, `min_p` | mêmes règles |

- **Formule commune :** une variable par périmètre a une formule commune, valable pour tout p.
- **Valeurs propres :** dans l'onglet 4, le choix « Valeur pour » donne à un périmètre sa propre formule ou sa propre table. Dans l'onglet 5, chaque périmètre peut avoir sa propre valeur initiale.
- **Flux, charges et postes :** un flux, une charge ou un poste dont la formule utilise `p` est calculé pour chaque périmètre, puis additionné. Son montant reste celui de la structure ; le détail par périmètre sert aux résultats.
- **Autres paramètres :** un paramètre sans `p` dans son nom ne peut utiliser une variable par périmètre qu'à travers `somme_p`, `moyenne_p`, `max_p` ou `min_p`.

**Résultats par périmètre (onglet 8, vue Périmètres) :** pour chaque structure, recettes dues, recettes encaissées, charges payées, investissements et entrées moins sorties, par périmètre ou regroupés par une colonne de groupes. Le payé d'un flux est réparti entre périmètres comme son dû. Les flux sans `p` vont dans « Non réparti ». Les variables par périmètre suivent : quantités, débits et montants sont additionnés, prix et taux sont moyennés.

**Niveau Global :** il est toujours proposé, et c'est le seul quand le modèle n'a pas de périmètres. Il donne le projet entier sur une seule colonne.

**Filtre de la vue Répartition :** limitée à un périmètre ou à un groupe, elle ne compte que les flux et charges écrits avec `p`, pour leur part dans ce périmètre.

## 3. Fonctions de calcul

| Fonction | Résultat |
|---|---|
| `si(condition, a, b)` | `a` si la condition est vraie, sinon `b` |
| `min(a, b, ...)` / `max(a, b, ...)` | plus petite ou plus grande valeur |
| `abs(x)` | valeur absolue |
| `racine(x)` | racine carrée |
| `exp(x)` / `log(x)` | exponentielle, logarithme népérien (x sans unité) |
| `arrondi(x)` / `arrondi(x, n)` | arrondi à n décimales |
| `plancher(x)` / `plafond(x)` | arrondi vers le bas, vers le haut |
| `lag(x)` / `lag(x, n)` | valeur de x il y a 1 ou n pas ; avant le démarrage, sa valeur initiale |
| `lead(x)` / `lead(x, n)` | valeur de x dans 1 ou n pas |
| `cumul(x)` | somme de x depuis le démarrage, pas en cours compris |

Exemple de tarif par tranches : `si(volume[usagers] <= 20 [m3], 200 [FCFA/m3], 450 [FCFA/m3])`.

Les zones de formule acceptent plusieurs lignes. Les conditions peuvent s'imbriquer, et les retours à la ligne ne changent pas le calcul :

```
si(volume[usagers] <= 20 [m3],
    200 [FCFA/m3],
    si(volume[usagers] <= 40 [m3],
        450 [FCFA/m3],
        900 [FCFA/m3]
    )
)
```

La touche Entrée va à la ligne et garde le retrait. La touche Tab passe au champ suivant.

## 4. Cumuls par jour, par mois et par année

| Fonction | Résultat |
|---|---|
| `somme_mois(x)` | cumul du mois en cours, jusqu'au pas en cours |
| `somme_mois(x, n)` | total du mois d'il y a n mois |
| `moyenne_mois(x)` / `moyenne_mois(x, n)` | moyenne sur les mêmes périodes |
| `somme_jour`, `moyenne_jour` | même principe par jour |
| `somme_annee`, `moyenne_annee` | même principe par année civile |

Exemple de facture mensuelle : `somme_mois(conso[usagers], 1) * tarif[exploitant]`.

- **Période en cours :** le cumul s'arrête au pas en cours. Le calcul ne regarde jamais l'avenir.
- **Moyenne :** c'est une moyenne simple, avec le même poids pour chaque pas.
- **Avant le démarrage :** le logiciel prend la valeur initiale de x et affiche une alerte.
- **Démarrage en cours de période :** la période ne compte que les pas simulés. Avec un démarrage le 01/07/2029, `somme_annee(x, 1)` donne en 2030 le total de juillet à décembre 2029.
- **Pas de temps :** il doit être au plus égal à la période cumulée. `somme_mois` avec un pas annuel est refusée.
- **Unités :** ces fonctions additionnent les valeurs de chaque pas sans les multiplier par la durée du pas. Faites-les porter sur une quantité par pas, pas sur un débit.

## 5. Tables

Une table relie une variable 1 à une variable 2, le paramètre.

- **Variable 1 :** le temps en années, `t`, `t_sim`, `t_jour`, `t_mois`, `t_an`, `t[annee]`, `t[mois]`, `t[jour]` ou un autre paramètre.
- **Lecture par paliers :** la valeur reste constante jusqu'à la ligne suivante.
- **Lecture par interpolation :** y = y1 + (y2 − y1) × (x − x1) / (x2 − x1).
- **Hors de la table :** le logiciel garde la valeur connue la plus proche et affiche une alerte.

Pour un profil saisonnier, créez une table sur `t[mois]`, une table sur `t[annee]`, puis multipliez-les dans une formule.

## 6. Post-traitement

Ces fonctions ne s'utilisent que dans l'onglet 7. Post-traitement. Les résultats n'influencent jamais le calcul.

| Fonction | Résultat |
|---|---|
| `total(x)` | somme sur toute la simulation |
| `moyenne(x)` | moyenne simple sur toute la simulation |
| `minimum(x)` / `maximum(x)` | plus petite ou plus grande valeur |
| `van(x, taux)` | VAN = Σ x / (1 + taux)^d, avec d la durée en années entre le démarrage et la fin du pas (365 jours par an) |
| `tri(x)` | taux pour lequel VAN = 0 ; erreur si aucun taux n'est trouvé entre −99 % et 1 000 % |

## 7. Unités

- Le moteur convertit les unités pendant le calcul et contrôle les dimensions.
- On n'additionne que des grandeurs de même dimension. Seul 0 passe sans unité.
- Une formule réduite à un nombre prend l'unité du paramètre.
- Un paramètre sans unité échappe au contrôle.
- **Débit vers quantité :** quantité = débit × durée du pas en années. En janvier d'une année bissextile, la durée vaut 31/366.
- **Durée du pas :** elle suit le calendrier réel. Un pas de 12 mois vaut exactement 1 an.
- **Devises :** elles se convertissent avec les taux de la partie Base, par exemple `taux_eur_fcfa[projet]`, prérempli à 655,957.

## 8. Comptes de chaque entité

Ces calculs sont faits par le moteur, à chaque pas. Les postes de la fiche d'un bloc (actifs, dettes, créances, provisions, etc.) restent des formules que vous écrivez.

| Grandeur | Formule |
|---|---|
| Recettes | flux financiers dus reçus, classés au compte Résultat, et dividendes reçus |
| Charges | flux dus et charges classés au compte Résultat + amortissements + dotation aux provisions |
| Dotation aux provisions | provisions du pas − provisions du pas précédent |
| **Résultat** | recettes − charges + intérêts moratoires et abandons (net) |
| **Entrées moins sorties** | tous les flux financiers reçus − tous les flux financiers payés − toutes les charges |
| Capital | postes Capital + apports reçus cumulés |
| Fonds propres | capital + résultats cumulés − dividendes versés cumulés |
| Trésorerie | trésorerie initiale + cumul des entrées moins sorties (montants payés) − créances + dettes fournisseurs |
| **Contrôle du bilan** | actifs + créances + à recevoir + trésorerie = fonds propres + dettes + dettes fournisseurs + à payer + provisions |

- Un écart de bilan supérieur à 1 déclenche une alerte.
- Les réserves et les garanties sont affichées sans entrer dans ce contrôle.
- Les comptes ne peuvent pas encore alimenter les formules.

### Dû, payé, impayés et moratoires

Le bouton « Paiement : impayés et moratoire » de l'onglet 3 règle chaque transaction financière. Sans réglage, elle est payée à 100 %. Les taux s'écrivent comme des formules, mais ne peuvent pas dépendre des montants payés. Les charges propres, sans structure en face, sont toujours payées à 100 %.

| Calcul, à chaque pas | Formule |
|---|---|
| Dû | valeur du flux |
| Part suspendue | dû × part suspendue, pendant le moratoire ; sinon 0 |
| Exigible | dû − part suspendue |
| Recouvré sur la période | exigible × taux de recouvrement |
| Impayé | exigible − recouvré sur la période |
| Rattrapage | stock d'impayés précédent × taux de rattrapage |
| Abandon | (stock d'impayés précédent − rattrapage) × taux d'abandon |
| Stock d'impayés | stock précédent + impayé − rattrapage − abandon |
| Intérêt moratoire | stock sous moratoire précédent × taux annuel × durée du pas |
| Reprise | (stock sous moratoire + intérêt) / nombre de pas de reprise restants, après le moratoire |
| Stock sous moratoire | stock précédent + intérêt + part suspendue − reprise |
| **Payé** | recouvré sur la période + rattrapage + reprise |

- Le résultat suit le dû, la trésorerie suit le payé.
- Les stocks apparaissent en « à recevoir » chez le bénéficiaire et en « à payer » chez le payeur.
- L'intérêt moratoire est une recette pour le bénéficiaire et une charge pour le payeur.
- L'abandon est une perte pour le bénéficiaire et un gain pour le payeur.

### Écritures automatiques

| Flux | Effet |
|---|---|
| Apport en capital versé | crée un actif (participation) |
| Prêt versé au compte Dette | crée un actif (prêt accordé), réduit par les remboursements reçus |
| Argent reçu au compte Dette, sans poste Dette | crée la dette de l'emprunteur |
| Dividende reçu | compte dans les recettes et le résultat |

La vue Synthèse de l'onglet 8 compare les structures par nature, sur toute la simulation ou sur une année :

| Nature | Formule |
|---|---|
| Entrées d'argent | recettes encaissées + apports en capital reçus + dette reçue + dividendes reçus + autres entrées |
| Sorties d'argent | charges payées + investissements + dette versée + dividendes versés + apports en capital versés |
| Autres entrées | flux reçus classés au compte Investissement |
| Lignes de flux | somme de la période |
| Lignes de bilan | valeur à la fin de la période |
| Flux physiques | somme de la période, reçu en positif, fourni en négatif ; un débit est multiplié par la durée de chaque pas |

Dans la Synthèse, une flèche déplie une ligne pour voir chaque flux, charge ou poste qui la compose. Les montants détaillés sont ceux des postes, flux et charges saisis ; les écritures automatiques n'y figurent pas.

**Grandeurs physiques :** ce sont les paramètres dont l'unité n'est pas monétaire. Un débit est multiplié par la durée de chaque pas ; une autre valeur est additionnée sur les pas.

| Indicateur | Formule |
|---|---|
| Marge | résultat / recettes dues |
| Taux de recouvrement constaté | somme payée à la structure / somme due à la structure |
| Couverture des remboursements de dette | (recettes encaissées − charges payées) / dette versée |
| Trésorerie la plus basse | plus petite trésorerie de la période |
| VAN des entrées moins sorties | avec le taux d'actualisation de l'onglet 6, sur toute la simulation |
| TRI des entrées moins sorties | taux pour lequel cette VAN est nulle, sur toute la simulation |

Les intérêts comptés au compte Résultat font partie des charges payées. La couverture n'est donc pas le DSCR classique. Une case reste vide si l'indicateur n'a pas de sens pour la structure.

### Capacité d'investissement

Ces calculs se règlent dans l'onglet Capacité d'investissement de la fiche d'un bloc et se font à chaque pas. Seule la CAF est calculée pour toutes les structures.

| Calcul | Formule |
|---|---|
| Capacité d'autofinancement (CAF) | résultat + amortissements + dotations aux provisions |
| Fonds propres mobilisables | trésorerie − trésorerie minimale à garder |
| Service de la dette existante | remboursements dus sur les flux payés au compte Dette, hors prêts accordés |
| Annuité supportable (par an) | CAF annualisée / couverture minimale exigée − service de la dette annualisé |
| Facteur d'annuité | (1 − (1 + taux)^(−durée)) / taux ; durée si le taux est nul |
| Capacité d'emprunt | annuité supportable × facteur d'annuité ; 0 si l'annuité est négative |
| Capacité d'investissement | fonds propres mobilisables + capacité d'emprunt |
| Marge ou déficit | capacité d'investissement − besoin d'investissement du pas |

La CAF de la Synthèse est la somme de la période. Les autres lignes sont les valeurs du dernier pas. Les intérêts comptés au compte Résultat réduisent déjà la CAF. Ce calcul est un constat : il ne modifie pas les investissements du modèle.

### Optimisation des tarifs

Un paramètre coché « Tarif optimisable » (onglet 4) est multiplié par un coefficient que le moteur cherche, puis plafonné par son tarif maximal. Un tarif non coché, comme un tarif social, reste fixe. Les réglages communs sont dans l'onglet 6.

| Option | Coefficient cherché | Condition, pour chaque structure à équilibrer |
|---|---|---|
| Tarifs actuels | 1 | aucune |
| Maintien du service | un par année, le plus petit possible | recettes encaissées − charges payées de l'année ≥ 0 (investissements et dette exclus) |
| Financement des investissements | un seul, le plus petit possible | somme des entrées moins sorties sur la simulation ≥ 0 ; trésorerie ≥ trésorerie minimale si elle est fixée ; TRI de la structure choisie ≥ TRI cible si il est fixé |

- **Hausse maximale par an :** maintien, coefficient de l'année ≤ coefficient précédent × (1 + hausse) ; financement, montée progressive (1 + hausse)^n jusqu'au tarif cible.
- **Recherche :** par dichotomie entre 0 et 100 fois le tarif saisi. Si aucune valeur ne respecte les contraintes, la simulation finit sur Échec et indique la structure et la contrainte en cause.
- **TRI :** une structure dont les entrées moins sorties ne sont jamais négatives n'a pas de TRI ; la condition est alors considérée comme remplie.
- On peut cocher une, deux ou trois options (ligne `option_tarifs` du .dat, par exemple `actuels,maintien,financement`). Chaque option cochée est simulée entièrement et gardée : l'écran Résultats passe d'un scénario à l'autre sans relancer. `option_principale` donne le scénario affiché d'abord. Dans la vue Tarifs, les écarts sont calculés par rapport à la première option cochée.
- Les résultats peuvent porter sur toute la durée, une année ou une plage d'années (de… à…). VAN et TRI ne sont calculés que sur toute la durée.

La vue Répartition de l'onglet 8 suit l'argent entre les structures :

| Ligne | Formule |
|---|---|
| Encaissé | somme des montants réellement payés à la structure |
| Reste à la structure | encaissé − payé aux autres structures − charges propres − investissements propres |
| Argent apporté | somme des restes négatifs, en valeur absolue |
| Part de l'argent apporté | reste à la structure / argent apporté |
| Part des charges propres | charges propres / argent apporté |
| Part des investissements propres | investissements propres / argent apporté |

Les restes positifs, les charges propres et les investissements propres totalisent 100 % de l'argent apporté. Une flèche déplie chaque ligne de dépense.

La section `[SOLDES]` de `Resultat.dat` donne, sans classement par compte : recettes = flux reçus, charges = flux payés + charges, solde = recettes − charges.

## 9. Résolution des calculs

1. Le moteur classe les variables selon leurs dépendances. `lag` et les cumuls de périodes passées n'en créent pas.
2. Il calcule pas par pas, dans cet ordre.
3. Si des variables dépendent les unes des autres, il itère jusqu'à ce que l'écart passe sous la convergence de chaque paramètre (par défaut 1e-3).
4. En cas de divergence ou de stagnation, il passe à la méthode de Newton.
5. Vérification finale : une fois les itérations sous le seuil, le moteur fait deux passages de plus (écarts e1 puis e2). Le rythme r = e2 / e1 permet d'estimer la distance restante à la vraie solution, e2 × r / (1 − r). Cette distance doit être sous la convergence de chaque variable. Sinon (convergence lente : les itérations bougent peu mais la solution est encore loin), le moteur poursuit avec Newton depuis la valeur atteinte, puis revérifie. Si c'est toujours insuffisant au bout du nombre maximal d'itérations, la simulation est en Échec avec le message « Vérification finale non satisfaite », la variable et les dates concernées.
5. Il s'arrête au nombre d'itérations maximal par pas de temps (par défaut 200) et le signale dans `Resultat.dat`.
6. Il calcule ensuite les comptes, puis le post-traitement.

La fenêtre de simulation affiche l'avancement dans le temps (pas en cours et sa date) et, pour le dernier pas calculé, l'écart |S(n, p) − S(n−1, p)| à la dernière itération, pour la variable la plus éloignée de son critère, avec ce critère. La simulation finit par Réussite, ou par Échec si un contrôle bloque, si une boucle ne converge pas, si un calcul est impossible ou si l'utilisateur l'arrête.
