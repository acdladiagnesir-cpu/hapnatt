# -*- coding: utf-8 -*-
"""
HapNatt - Prototype

Copyright © 2026 A. C. Diagne.

Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
modifier selon les termes de la Licence publique générale GNU (GNU GPL)
publiée par la Free Software Foundation, version 3 de la licence, ou (à votre
choix) toute version ultérieure.
Ce programme est distribué dans l'espoir qu'il sera utile, mais SANS AUCUNE
GARANTIE, sans même la garantie implicite de QUALITÉ MARCHANDE ou
d'ADÉQUATION À UN USAGE PARTICULIER. Voir le fichier LICENSE pour le texte
complet de la licence (https://www.gnu.org/licenses/gpl-3.0.html).
SPDX-License-Identifier: GPL-3.0-or-later
Structures -> Flux -> Paramètres -> Simulation -> Post-traitement -> Résultats

Lancement : ouvrir ce fichier dans IDLE, puis appuyer sur F5.
Les courbes demandent matplotlib (pip install matplotlib). Sans lui, les
autres onglets et l'export des tables fonctionnent normalement.
"""

# ============================ CONFIGURATION ============================
FICHIER_SIMULATION = "Simulation.dat"   # nom proposé pour la mise en données
CHARGER_EXEMPLE = True            # True : ouvre Exemple_Simulation.dat au démarrage
FICHIER_EXEMPLE = "Exemple_Simulation.dat"
LANGUE_INTERFACE = "fr"           # "fr" pour français, "en" pour anglais
# =======================================================================

import ast
import calendar
import datetime
import math
import os
import random
import re
import time
import unicodedata

from ppp_langues import LANGUE, LANGUES, T, definir_langue, origine


UNITES = [
    "", "sans unité", "%", "FCFA", "MFCFA", "EUR", "USD",
    "FCFA/an", "MFCFA/an", "FCFA/m3", "FCFA/kWh", "FCFA/(km·an)",
    "m", "km", "m2", "ha", "km2", "m3", "litre", "kg", "tonne", "tonne/an",
    "s", "h", "jour", "mois", "an",
    "m3/s", "m3/h", "m3/j", "m3/an", "m/s", "km/h",
    "W", "kW", "MW", "kWh", "MWh", "GWh", "kWh/m3",
    "Pa", "bar", "°C", "K",
    "équipement", "client", "lit", "unité",
]

TYPES_STRUCTURE = [
    "Autorité", "Société de patrimoine", "Exploitant", "Vendeur",
    "Société de projet", "Bailleur de fonds", "Prêteur", "Actionnaire", "Fournisseur", "Usager",
]

FONCTIONS = {
    "si", "min", "max", "abs", "racine", "exp", "log", "arrondi",
    "plancher", "plafond", "lag", "lead", "cumul", "unite_lit",
    "somme_jour", "moyenne_jour", "somme_mois", "moyenne_mois",
    "somme_annee", "moyenne_annee",
    "somme_p", "moyenne_p", "max_p", "min_p",
}
AGREGATIONS_P = ("somme_p", "moyenne_p", "max_p", "min_p")
FONCTIONS_UTILISATEUR = {}        # fonctions du modèle ouvert : nom -> fiche
INTERDITES_DANS_FONCTION = {"lag", "lead", "cumul"} | set(AGREGATIONS_P)
RESULTAT_FONCTION = ("resultat", "résultat")
PERIMETRE_COURANT = "p"           # dans x[structure, p] : le périmètre courant
# Colonnes de la table des périmètres lues comme coordonnées (WGS 84).
COLONNES_X = ("x", "longitude", "lon")
COLONNES_Y = ("y", "latitude", "lat")
FONCTIONS_POST = {"total", "moyenne", "minimum", "maximum", "van", "tri"}
TEMPS_FIXES = {"t_jour": "jour", "t_mois": "mois", "t_an": "an"}
TEMPS_MODELE = ("t0", "t_sim")    # t = t0 + t_sim, dans l'unité de référence
ATTRIBUTS_TEMPS = ("annee", "mois", "jour")   # t[mois] : mois du calendrier
TEMPS_CALENDRIER = tuple("t[%s]" % a for a in ATTRIBUTS_TEMPS)
VARIABLES_SYSTEME = {"annee", "t", "jours_t", "tau_t"} | set(TEMPS_FIXES) \
    | set(TEMPS_MODELE) | set(TEMPS_CALENDRIER) \
    | {"t_cal_" + a for a in ATTRIBUTS_TEMPS}
VARIABLE_TEMPS = "annee"          # variable 1 par défaut d'une table
MOIS_ANCIENS_PAS = {"annee": 12, "semestre": 6, "trimestre": 3, "mois": 1}
PERIODES_MAX = 200000
ANNEES_PAR_UNITE = {"s": 1 / 31536000, "min": 1 / 525600, "h": 1 / 8760,
                    "j": 1 / 365, "jour": 1 / 365, "mois": 1 / 12, "an": 1}
COULEURS_TYPES = {                 # type : (fond, couleur d'accent)
    "Autorité": ("#E9ECF8", "#4356B8"),
    "Société de patrimoine": ("#DFF3F0", "#0E8C7F"),
    "Exploitant": ("#FDF0E1", "#E08A2E"),
    "Vendeur": ("#FBE7EE", "#C93F73"),
    "Société de projet": ("#EEE9F8", "#6E52B8"),
    "Bailleur de fonds": ("#E2F0FB", "#2583C9"),
    "Prêteur": ("#E7F4E8", "#46994B"),
    "Actionnaire": ("#FBF4DA", "#B8920F"),
    "Fournisseur": ("#F4E8F6", "#94409F"),
    "Usager": ("#EBEFF2", "#5F7482"),
}
COULEUR_AUTRE_TYPE = ("#F0F1F3", "#7C8590")
PAIEMENT_DEFAUT = {          # réglages d'une transaction : payée à 100 %
    "recouvrement": "1", "rattrapage": "0", "abandon": "0",
    "moratoire_debut": "", "moratoire_fin": "", "part_suspendue": "1",
    "reprise_pas": "1", "taux_moratoire": "0",
}
PAIEMENT_FORMULES = ("recouvrement", "rattrapage", "abandon", "part_suspendue",
                     "taux_moratoire")
CAPACITE_CHAMPS = ("tresorerie_minimale", "couverture", "taux", "duree",
                   "besoin")
MARQUE_JEU_DE_DONNEES = "[JEU_DE_DONNEES]"
CLES_TARIFS = ("option_tarifs", "structures_equilibre", "hausse_max",
               "tri_cible", "structure_tri", "tresorerie_min",
               "option_principale")
# option_tarifs peut lister plusieurs options (« actuels,maintien ») : elles
# sont toutes simulées et comparées ; option_principale donne les résultats
# détaillés (la première cochée par défaut).
OPTIONS_TARIFS_UI = {"actuels": "Tarifs actuels",
                     "maintien": "Maintien du service",
                     "financement": "Financement des investissements"}
CONVERGENCE_DEFAUT = "1e-3"
ONGLET_RESULTATS = 7
ITERATIONS_MAX_DEFAUT = "200"
REGLE_HORS_TABLE = "derniere_valeur_avec_alerte"
NATURES_FLUX = ("Financier", "Physique")
COMPTES_FLUX = ("Résultat", "Capital", "Dette", "Investissement", "Dividende")
CATEGORIES_POSTES = (
    "Trésorerie initiale", "Capital", "Actif", "Amortissement", "Créance",
    "Dette", "Dette fournisseur", "Réserve", "Provision", "Garantie",
)
EFFETS_FLUX = ("Capacité", "Qualité", "Sécurité", "Autre")

# Unités par dimension : facteur vers une base commune à la dimension.
DIMENSIONS = {
    "Temps": {"s": None, "min": None, "h": None, "j": None, "jour": None,
              "mois": None, "an": None},
    "Longueur": {"m": 1, "km": 1000},
    "Surface": {"m2": 1, "ha": 1e4, "km2": 1e6},
    "Volume": {"m3": 1, "litre": 0.001},
    "Masse": {"kg": 1, "tonne": 1000},
    "Puissance": {"W": 1, "kW": 1e3, "MW": 1e6},
    "Énergie": {"kWh": 1, "MWh": 1e3, "GWh": 1e6},
    "Pression": {"Pa": 1, "bar": 1e5},
    "Température": {"K": None, "°C": None},
    "Monnaie": {"FCFA": None, "EUR": None, "USD": None},
}
REFERENCES_DEFAUT = {
    "Temps": "an", "Longueur": "m", "Surface": "m2", "Volume": "m3",
    "Masse": "kg", "Puissance": "kW", "Énergie": "kWh", "Pression": "Pa",
    "Température": "K", "Monnaie": "FCFA",
}
MULTIPLES_MONNAIE = {"MFCFA": ("FCFA", 1e6)}
TAUX_CONNUS = {("EUR", "FCFA"): "655.957", ("FCFA", "EUR"): "1 / 655.957"}


def dimension_de(unite):
    for dimension, unites in DIMENSIONS.items():
        if unite in unites:
            return dimension
    return None


def atomes_unite(unite):
    """Découpe FCFA/(km·an) en FCFA, km et an."""
    return [a for a in re.split(r"[/*·() ]+", unite)
            if a and a not in ("%", "sans", "unité")]
LECTURES_TABLE = {"Par paliers": "paliers", "Interpolation": "interpolation"}
RE_JETON = re.compile(
    r'"[^"]*"|\[[^\]]*\]|\d+\.?\d*(?:[eE][+-]?\d+)?|\w+|==|!=|<=|>=|\S'
)
CLES_ETIQUETTES = ("etiquette", "etiquette_resultat")   # décalages [dx, dy]
STRUCTURE_COMMUNE = "projet"      # pour une valeur commune à toutes les structures
MOTS_CLES = {"et", "ou", "non"}
NOEUDS_AUTORISES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call,
    ast.Name, ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.Pow, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Lt, ast.LtE,
    ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)


class ErreurModele(Exception):
    """Erreur compréhensible par l'utilisateur."""


def creer_id(texte):
    """Transforme un nom en identifiant stable."""
    t = unicodedata.normalize("NFKD", texte.strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    if not t:
        raise ErreurModele("Le nom est vide.")
    if t[0].isdigit():
        t = "x_" + t
    return t


def composer_id(nom, structure):
    """Identifiant complet : redevance[societe_1]."""
    return "%s[%s]" % (nom, structure)


def decomposer_id(identifiant):
    """Retourne (nom, structure) à partir de redevance[societe_1].

    Pour x[structure,p], la structure est rendue sans le périmètre.
    """
    nom, structure = identifiant[:-1].split("[", 1)
    return nom, structure.split(",")[0]


def perimetre_id(identifiant):
    """Périmètre d'un identifiant x[structure,p] ; None s'il n'en a pas."""
    if "[" not in identifiant:
        return None
    contenu = identifiant[:-1].split("[", 1)[1]
    return contenu.split(",", 1)[1] if "," in contenu else None


def est_indexe(identifiant):
    return perimetre_id(identifiant) == PERIMETRE_COURANT


def indexee(identifiant):
    """x[s,dakar] -> x[s,p] ; les autres identifiants sont inchangés."""
    perimetre = perimetre_id(identifiant)
    if perimetre is None or perimetre == PERIMETRE_COURANT:
        return identifiant
    nom, structure = decomposer_id(identifiant)
    return composer_id(nom, structure + "," + PERIMETRE_COURANT)


def analyser_expression(expression, structure=None, structures=None,
                        post=False):
    """Vérifie une expression et retourne les variables qu'elle utilise.

    Toute variable s'écrit avec sa structure : nom[structure].
    """
    return compiler_expression(expression, structures, post)[1]


def compiler_expression(expression, structures=None, post=False,
                        locaux=None):
    """Retourne (arbre, variables utilisées, table des noms qualifiés).

    locaux : noms admis sans crochets (arguments et paramètres internes
    d'une fonction) ; seules les valeurs [projet] sont alors permises.
    """
    texte = expression.strip()
    if not texte:
        raise ErreurModele("L'expression est vide.")
    morceaux, qualifies = [], {}
    for jeton in RE_JETON.findall(texte):
        if jeton.startswith("["):
            precedent = morceaux[-1] if morceaux else ""
            if precedent[:1].isdigit():    # 12 [FCFA] : unité d'un nombre
                morceaux[-1] = 'unite_lit(%s, "%s")' % (precedent,
                                                        jeton[1:-1].strip())
                continue
            attribut = creer_id(jeton[1:-1])
            if precedent == "t" and attribut in ATTRIBUTS_TEMPS:
                morceaux[-1] = "t_cal_" + attribut
                continue
            if not re.fullmatch(r"[^\W\d]\w*", precedent) \
                    or precedent in MOTS_CLES or precedent in ("and", "or",
                                                               "not"):
                raise ErreurModele(
                    "Les crochets doivent suivre un nombre ou un paramètre.")
            # Majuscules et accents admis : Tarif[Exploitant] = tarif[exploitant].
            precedent = creer_id(precedent)
            morceaux_id = jeton[1:-1].split(",")
            if len(morceaux_id) > 2:
                raise ErreurModele("Écriture attendue : nom[structure] ou "
                                   "nom[structure, p].")
            cible = creer_id(morceaux_id[0])
            if structures is not None and cible != STRUCTURE_COMMUNE \
                    and cible not in structures:
                raise ErreurModele("Structure inconnue : " + morceaux_id[0])
            if len(morceaux_id) == 2:
                cible += "," + creer_id(morceaux_id[1])
            alias = "%s_q%d" % (precedent, len(qualifies))
            qualifies[alias] = composer_id(precedent, cible)
            morceaux[-1] = alias
            continue
        if jeton == "^":
            jeton = "**"
        elif jeton == "et":
            jeton = "and"
        elif jeton == "ou":
            jeton = "or"
        elif jeton == "non":
            jeton = "not"
        morceaux.append(jeton)
    python = " ".join(morceaux)
    try:
        arbre = ast.parse(python, mode="eval")
    except SyntaxError:
        raise ErreurModele("Écriture incorrecte : " + expression)

    appelees, noms = set(), set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, NOEUDS_AUTORISES):
            raise ErreurModele("Élément non autorisé dans : " + expression)
        if isinstance(noeud, ast.Call):
            if not isinstance(noeud.func, ast.Name):
                raise ErreurModele("Appel de fonction incorrect.")
            nom = noeud.func.id
            if nom in FONCTIONS_POST and not post:
                raise ErreurModele("Fonction réservée au post-traitement : "
                                   + nom)
            if nom not in FONCTIONS and nom not in FONCTIONS_POST \
                    and nom not in FONCTIONS_UTILISATEUR:
                raise ErreurModele("Fonction inconnue : " + nom)
            if locaux is not None and (
                    nom in INTERDITES_DANS_FONCTION or nom in FONCTIONS_POST
                    or nom.startswith(("somme_", "moyenne_"))):
                raise ErreurModele("%s n'est pas permise dans une fonction : "
                                   "utilisez-la dans la formule qui "
                                   "l'appelle." % nom)
            if nom in FONCTIONS_UTILISATEUR and len(noeud.args) != len(
                    FONCTIONS_UTILISATEUR[nom]["arguments"]):
                raise ErreurModele("%s attend %d argument(s) : %s(%s)." % (
                    nom, len(FONCTIONS_UTILISATEUR[nom]["arguments"]), nom,
                    ", ".join(FONCTIONS_UTILISATEUR[nom]["arguments"])))
            if noeud.keywords:
                raise ErreurModele("Argument nommé non autorisé.")
            if nom == "si" and len(noeud.args) != 3:
                raise ErreurModele("si attend 3 éléments : si(condition, a, b).")
            if nom in AGREGATIONS_P:
                if not 1 <= len(noeud.args) <= 2 or (
                        len(noeud.args) == 2 and not (
                            isinstance(noeud.args[1], ast.Constant)
                            and isinstance(noeud.args[1].value, str))):
                    raise ErreurModele(
                        '%s attend (variable[structure, p]) ou '
                        '(variable[structure, p], "groupe").' % nom)
            elif nom.startswith(("somme_", "moyenne_")):
                arguments = noeud.args
                if not 1 <= len(arguments) <= 2 or (
                        len(arguments) == 2 and not (
                            isinstance(arguments[1], ast.Constant)
                            and isinstance(arguments[1].value, int)
                            and arguments[1].value >= 0)):
                    raise ErreurModele(
                        "%s attend (variable) ou (variable, n), avec n entier "
                        "positif ou nul." % nom)
            appelees.add(id(noeud.func))
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Name) and id(noeud) not in appelees:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", noeud.id):
                raise ErreurModele(
                    "Nom incorrect : %s. Utilisez des minuscules sans accent."
                    % noeud.id)
            if noeud.id in FONCTIONS:
                raise ErreurModele("Nom réservé : " + noeud.id)
            if noeud.id in qualifies:
                noms.add(qualifies[noeud.id])
                if locaux is not None and not qualifies[noeud.id].endswith(
                        "[%s]" % STRUCTURE_COMMUNE):
                    raise ErreurModele(
                        "Une fonction ne lit que ses arguments et les valeurs "
                        "[projet] : passez %s en argument." % qualifies[noeud.id])
            elif locaux is not None and noeud.id in locaux:
                continue
            elif noeud.id not in VARIABLES_SYSTEME:
                raise ErreurModele(
                    "Précisez la structure entre crochets : %s[structure]."
                    % noeud.id)
    return arbre, noms, qualifies


# ------------------------- Fonctions de l'utilisateur -------------------------
def lire_corps(corps):
    """Découpe le corps en [(nom, expression)] ; une ligne sans « = » prolonge
    la précédente."""
    lignes = []
    for brute in corps.splitlines():
        if not brute.strip():
            continue
        trouve = re.match(r"\s*([^\W\d]\w*)\s*=(?!=)(.*)$", brute)
        if trouve:
            lignes.append([trouve.group(1), trouve.group(2)])
        elif lignes:
            lignes[-1][1] += "\n" + brute
        else:
            raise ErreurModele("Chaque calcul s'écrit : nom = formule.")
    if not lignes or lignes[-1][0] not in RESULTAT_FONCTION:
        raise ErreurModele("La dernière ligne doit être : résultat = ...")
    return [(n, e.strip()) for n, e in lignes]


def remplacer_noms(texte, valeurs):
    """Remplace des noms simples par (leur texte), hors crochets et appels."""
    jetons = RE_JETON.findall(texte)
    sortie = []
    for rang, jeton in enumerate(jetons):
        suivant = jetons[rang + 1] if rang + 1 < len(jetons) else ""
        if jeton in valeurs and not suivant.startswith(("[", "(")):
            sortie.append("(" + valeurs[jeton] + ")")
        else:
            sortie.append(jeton)
    return " ".join(sortie)


def corps_deplie(nom, arguments):
    """Expression d'un appel, ses arguments et paramètres internes remplacés."""
    fiche = FONCTIONS_UTILISATEUR[nom]
    valeurs = dict(zip(fiche["arguments"], arguments))
    expression = ""
    for interne, formule in lire_corps(fiche["corps"]):
        expression = remplacer_noms(formule, valeurs)
        valeurs[interne] = expression
    return expression


def decouper_appel(texte, debut):
    """Arguments de l'appel dont la parenthèse ouvrante est à debut."""
    profondeur, morceau, arguments, rang = 0, "", [], debut + 1
    chaine = False
    while rang < len(texte):
        car = texte[rang]
        if car == '"':
            chaine = not chaine
        elif not chaine and car in "([":
            profondeur += 1
        elif not chaine and car in ")]":
            if profondeur == 0 and car == ")":
                arguments.append(morceau.strip())
                return [a for a in arguments if a] if arguments != [""] \
                    else [], rang
            profondeur -= 1
        elif not chaine and car == "," and profondeur == 0:
            arguments.append(morceau.strip())
            morceau = ""
            rang += 1
            continue
        morceau += car
        rang += 1
    raise ErreurModele("Parenthèse non fermée dans : " + texte)


def deplier_fonctions(texte):
    """Remplace chaque appel d'une fonction de l'utilisateur par son corps."""
    if not FONCTIONS_UTILISATEUR or not texte:
        return texte
    motif = re.compile(r"(?<![\w\]])(%s)\s*\(" % "|".join(
        sorted(map(re.escape, FONCTIONS_UTILISATEUR), key=len, reverse=True)))
    for _ in range(100):
        trouve = motif.search(texte)
        if not trouve:
            return texte
        arguments, fin = decouper_appel(texte, trouve.end() - 1)
        texte = texte[:trouve.start()] + "(" + corps_deplie(
            trouve.group(1), arguments) + ")" + texte[fin + 1:]
    raise ErreurModele("Fonctions trop imbriquées : vérifiez qu'aucune ne "
                       "s'appelle elle-même.")


def bibliotheque_fonctions():
    """Fonctions de départ ; les coefficients sont à adapter au projet."""
    return {
        "annuite": {
            "arguments": ["montant", "taux", "duree"],
            "description": "Remboursement annuel constant d'un emprunt.",
            "corps": "facteur = si(taux == 0, duree,\n"
                     "    (1 - (1 + taux) ^ (-duree)) / taux)\n"
                     "résultat = montant / facteur"},
        "amortissement_lineaire": {
            "arguments": ["montant", "duree"],
            "description": "Part annuelle d'un investissement amorti sur sa "
                           "durée.",
            "corps": "résultat = montant / duree"},
        "tarif_tranches": {
            "arguments": ["volume", "prix_social", "prix_normal", "seuil"],
            "description": "Facture avec une tranche sociale jusqu'au seuil, "
                           "puis une tranche normale.",
            "corps": "volume_social = min(volume, seuil)\n"
                     "volume_normal = max(volume - seuil, 0 * volume)\n"
                     "résultat = volume_social * prix_social\n"
                     "    + volume_normal * prix_normal"},
        "indexation": {
            "arguments": ["prix", "taux", "annees"],
            "description": "Prix augmenté d'un taux constant chaque année.",
            "corps": "résultat = prix * (1 + taux) ^ annees"},
        "cout_ouvrage": {
            "arguments": ["type", "taille", "taille_reference",
                          "cout_reference"],
            "description": "Coût d'un ouvrage selon sa taille, avec économies "
                           "d'échelle selon le type : \"usine\", \"forage\", "
                           "\"reservoir\", \"conduite\", \"pompage\". "
                           "Exposants indicatifs, à ajuster.",
            "corps": "exposant = si(type == \"usine\", 0.7,\n"
                     "    si(type == \"forage\", 0.8,\n"
                     "    si(type == \"reservoir\", 0.6,\n"
                     "    si(type == \"conduite\", 1,\n"
                     "    si(type == \"pompage\", 0.65, 1)))))\n"
                     "résultat = cout_reference\n"
                     "    * (taille / taille_reference) ^ exposant"},
    }


def eval_taux(texte):
    """Valeur d'un taux connu, écrit sous forme a ou 1 / a."""
    if "/" in texte:
        numerateur, denominateur = texte.split("/")
        return float(numerateur) / float(denominateur)
    return float(texte)


def vers_fichier(expression):
    """Garde une formule sur une ligne du fichier, sans perdre sa présentation."""
    return expression.replace("\t", "    ").replace("\n", "\\n")


def depuis_fichier(expression):
    return expression.replace("\\n", "\n")


def lire_date(texte):
    """Lit une date JJ/MM/AAAA ou AAAA-MM-JJ."""
    texte = texte.strip()
    for motif in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(texte, motif).date()
        except ValueError:
            pass
    raise ValueError(texte)


def ajouter_mois(date, nombre):
    """Avance d'un nombre de mois, sans dépasser la fin du mois visé."""
    rang = date.month - 1 + nombre
    annee, mois = date.year + rang // 12, rang % 12 + 1
    return date.replace(year=annee, month=mois, day=min(
        date.day, calendar.monthrange(annee, mois)[1]))


def lire_table(lignes):
    """Lit des lignes (variable 1, variable 2) et retourne une liste triée."""
    points = {}
    for numero, (brut_1, brut_2) in enumerate(lignes, 1):
        if not str(brut_1).strip() and not str(brut_2).strip():
            continue
        try:
            valeur_1 = float(str(brut_1).strip().replace(",", "."))
            valeur_2 = float(str(brut_2).strip().replace(",", "."))
        except ValueError:
            raise ErreurModele("Ligne %d : un nombre est attendu dans chaque "
                               "colonne." % numero)
        if valeur_1 in points:
            raise ErreurModele("La valeur %g est saisie deux fois dans la "
                               "variable 1." % valeur_1)
        points[valeur_1] = valeur_2
    if not points:
        raise ErreurModele("La table est vide.")
    return sorted(points.items())


class Modele:
    """Données du modèle, indépendantes de l'interface."""

    def __init__(self):
        self.structures = {}   # id -> nom, type, missions, x, y
        self.flux = {}         # id -> nom, payeur, beneficiaire, structure
        self.charges = {}      # id -> nom, structure, compte
        self.postes = {}       # id -> nom, structure, categorie
        self.post = {}         # id -> nom, structure, expression, unite
        self.parametres = {}   # id -> fiche du paramètre
        self.simulation = {"date_debut": "", "pas": "1", "date_fin": "",
                           "taux_actualisation": "",
                           **dict.fromkeys(CLES_TARIFS, ""),
                           "iterations_max": ITERATIONS_MAX_DEFAUT,
                           "conserver_convergence": "non"}
        self.references_unites = dict(REFERENCES_DEFAUT)
        self.fonctions = {}            # nom -> arguments, corps, description
        self.perimetres = []           # [{"nom", "groupes": {colonne: valeur}}]
        self.colonnes_groupes = []     # par exemple ["Centre", "Région"]

    def conversions(self):
        """Conversions fixes et taux de change requis par les unités utilisées.

        Retourne (lignes fixes, dictionnaire devise -> identifiant du taux).
        """
        fixes, taux = {}, {}
        for p in self.parametres.values():
            for atome in atomes_unite(p["unite"]):
                if atome in MULTIPLES_MONNAIE:
                    devise, facteur = MULTIPLES_MONNAIE[atome]
                    fixes[atome] = (atome, devise, "%g" % facteur)
                    atome = devise
                dimension = dimension_de(atome)
                if dimension is None:
                    continue
                reference = self.references_unites[dimension]
                if atome == reference:
                    continue
                if dimension == "Monnaie":
                    taux[atome] = composer_id(
                        "taux_%s_%s" % (atome.lower(), reference.lower()),
                        STRUCTURE_COMMUNE)
                elif dimension == "Temps":
                    fixes[atome] = (atome, reference, "selon le calendrier")
                elif dimension == "Température":
                    fixes[atome] = (atome, reference, "K = °C + 273,15")
                else:
                    unites = DIMENSIONS[dimension]
                    fixes[atome] = (atome, reference,
                                    "%g" % (unites[atome] / unites[reference]))
        return sorted(fixes.values()), taux

    def definir_reference(self, dimension, unite):
        if unite not in DIMENSIONS[dimension]:
            raise ErreurModele("Cette unité n'appartient pas à la dimension.")
        ancienne = self.references_unites[dimension]
        self.references_unites[dimension] = unite
        if dimension == "Temps" and ancienne != unite:
            self.adapter_temps(ancienne, unite)
        self.synchroniser()

    def adapter_temps(self, ancienne, nouvelle):
        """Garde la durée du pas quand l'unité de référence change."""
        try:
            pas = float(self.simulation["pas"].replace(",", "."))
            self.simulation["pas"] = "%.10g" % (
                pas * ANNEES_PAR_UNITE[ancienne] / ANNEES_PAR_UNITE[nouvelle])
        except ValueError:
            pass

    def synchroniser_conversions(self):
        reference = self.references_unites["Monnaie"]
        _fixes, taux = self.conversions()
        for devise, identifiant in taux.items():
            if identifiant not in self.parametres:
                fiche = self.fiche_vide(identifiant)
                fiche["conversion"] = True
                fiche["unite"] = "%s/%s" % (reference, devise)
                connu = TAUX_CONNUS.get((devise, reference))
                if connu:
                    fiche["expression"] = connu
                    fiche["valeur_initiale"] = "%.12g" % eval_taux(connu)
                self.parametres[identifiant] = fiche
        attendus = set(taux.values())
        for identifiant, fiche in list(self.parametres.items()):
            if fiche.get("conversion") and identifiant not in attendus:
                del self.parametres[identifiant]

    @staticmethod
    def fiche_vide(identifiant):
        return {"id": identifiant, "mode": "formule", "expression": "",
                "table": [], "variable_table": VARIABLE_TEMPS,
                "lecture_table": "paliers", "conversion": False, "unite": "",
                "valeur_initiale": "", "convergence": CONVERGENCE_DEFAUT,
                "suivi": False}

    def renommer_structure(self, ancien, nouveau):
        def corriger_id(identifiant):
            if "[" not in identifiant:
                return identifiant
            nom, structure = decomposer_id(identifiant)
            suite = "," + perimetre_id(identifiant) \
                if perimetre_id(identifiant) else ""
            return composer_id(nom, nouveau + suite) if structure == ancien \
                else identifiant

        def corriger_expression(texte):
            def remplacer(trouve):
                contenu = trouve.group(1).strip()
                tete, _, suite = contenu.partition(",")
                try:
                    if creer_id(tete) != ancien:
                        return trouve.group(0)
                    return "[%s%s]" % (nouveau, ", " + suite.strip()
                                       if suite else "")
                except ErreurModele:
                    return trouve.group(0)
            return re.sub(r"\[([^\]]*)\]", remplacer, texte)

        for identifiant, f in list(self.flux.items()):
            for champ in ("payeur", "beneficiaire", "structure"):
                if f[champ] == ancien:
                    f[champ] = nouveau
            del self.flux[identifiant]
            self.flux[corriger_id(identifiant)] = f
        for identifiant, c in list(self.charges.items()):
            if c["structure"] == ancien:
                c["structure"] = nouveau
            del self.charges[identifiant]
            self.charges[corriger_id(identifiant)] = c
        for identifiant, c in list(self.postes.items()):
            if c["structure"] == ancien:
                c["structure"] = nouveau
            del self.postes[identifiant]
            self.postes[corriger_id(identifiant)] = c
        for f in self.flux.values():
            if "paiement" in f:
                for cle in PAIEMENT_FORMULES:
                    f["paiement"][cle] = corriger_expression(f["paiement"][cle])
        for fiche in self.structures.values():
            if "capacite" in fiche:
                fiche["capacite"] = {
                    k: corriger_expression(v)
                    for k, v in fiche["capacite"].items()}
        for identifiant, q in list(self.post.items()):
            if q["structure"] == ancien:
                q["structure"] = nouveau
            q["expression"] = corriger_expression(q["expression"])
            del self.post[identifiant]
            self.post[corriger_id(identifiant)] = q
        for identifiant, p in list(self.parametres.items()):
            del self.parametres[identifiant]
            p["id"] = corriger_id(identifiant)
            p["expression"] = corriger_expression(p["expression"])
            p["variable_table"] = corriger_id(p["variable_table"])
            self.parametres[p["id"]] = p
        # Réglages de simulation qui nomment des structures.
        equilibre = self.simulation.get("structures_equilibre", "")
        if equilibre:
            self.simulation["structures_equilibre"] = ",".join(
                nouveau if e == ancien else e for e in equilibre.split(","))
        if self.simulation.get("structure_tri") == ancien:
            self.simulation["structure_tri"] = nouveau

    def renommer_reference(self, ancien, nouveau):
        """Une variable change d'identifiant (flux renommé, bénéficiaire
        changé) : toutes les formules qui l'écrivent suivent."""
        nom_a, structure_a = decomposer_id(ancien)
        nom_n, structure_n = decomposer_id(nouveau)

        def remplacer(trouve):
            try:
                tete, _, suite = trouve.group(2).partition(",")
                if creer_id(trouve.group(1)) != nom_a or \
                        creer_id(tete) != structure_a:
                    return trouve.group(0)
            except ErreurModele:
                return trouve.group(0)
            return "%s[%s%s]" % (nom_n, structure_n,
                                 ", " + suite.strip() if suite else "")

        def corriger(texte):
            return re.sub(r"([A-Za-z_]\w*)\s*\[([^\]]*)\]", remplacer,
                          texte or "")

        for p in self.parametres.values():
            p["expression"] = corriger(p["expression"])
            if p.get("variable_table") == ancien:
                p["variable_table"] = nouveau
            for valeurs in p.get("perimetres", {}).values():
                if valeurs.get("expression"):
                    valeurs["expression"] = corriger(valeurs["expression"])
        for f in self.flux.values():
            for cle in PAIEMENT_FORMULES:
                if "paiement" in f:
                    f["paiement"][cle] = corriger(f["paiement"][cle])
        for fiche in self.structures.values():
            if "capacite" in fiche:
                fiche["capacite"] = {k: corriger(v)
                                     for k, v in fiche["capacite"].items()}
        for q in self.post.values():
            q["expression"] = corriger(q["expression"])
        for fonction in self.fonctions.values():
            fonction["corps"] = corriger(fonction["corps"])
        self.synchroniser()

    def ajouter_structure(self, nom, type_structure, ancien_id=None):
        identifiant = creer_id(nom)
        if identifiant == STRUCTURE_COMMUNE:
            raise ErreurModele("Le nom « projet » est réservé.")
        if identifiant != ancien_id and identifiant in self.structures:
            raise ErreurModele("Cette structure existe déjà.")
        fiche = {"missions": [], "x": None, "y": None}
        if ancien_id:
            fiche = self.structures[ancien_id]
        if ancien_id and ancien_id != identifiant:
            # Même place dans la liste : seul le nom change.
            self.structures = {(identifiant if k == ancien_id else k): v
                               for k, v in self.structures.items()}
            self.renommer_structure(ancien_id, identifiant)
        fiche.update({"nom": nom.strip(), "type": type_structure.strip()})
        self.structures[identifiant] = fiche
        return identifiant

    def definir_missions(self, identifiant, texte):
        self.structures[identifiant]["missions"] = [
            ligne.strip() for ligne in texte.splitlines() if ligne.strip()]

    def consequences_suppression(self, identifiant):
        """Retourne ce qui disparaît avec une structure et ce qui reste à revoir."""
        flux = [f for f, v in self.flux.items()
                if identifiant in (v["payeur"], v["beneficiaire"])]
        retires = set(flux) | {p for p in self.parametres
                               if decomposer_id(p)[1] == identifiant}
        retires |= {p for p in self.post if decomposer_id(p)[1] == identifiant}
        a_revoir = []
        for p in self.parametres:
            if p not in retires and self.references(p) & retires:
                a_revoir.append(p)
        for p, q in self.post.items():
            if p not in retires and retires & analyser_expression(
                    q["expression"], q["structure"], post=True):
                a_revoir.append(p)
        return sorted(retires), sorted(a_revoir)

    def supprimer_structure(self, identifiant):
        """Supprime la structure et tout ce qui lui appartient.

        Les formules des autres structures restent telles quelles : si elles
        utilisaient une variable supprimée, la vérification le signale.
        """
        for f, v in list(self.flux.items()):
            if identifiant in (v["payeur"], v["beneficiaire"]):
                del self.flux[f]
                self.parametres[f]["expression"] = ""
                self.parametres[f]["table"] = []
        for ensemble in (self.charges, self.postes, self.post):
            for i, v in list(ensemble.items()):
                if v["structure"] == identifiant:
                    del ensemble[i]
        for p in list(self.parametres):
            if decomposer_id(p)[1] == identifiant:
                del self.parametres[p]
        del self.structures[identifiant]
        self.synchroniser()

    def ajouter_flux(self, nom, payeur, beneficiaire, expression,
                     ancien_id=None, nature="Financier", effet="Capacité",
                     compte="Résultat"):
        if payeur not in self.structures or beneficiaire not in self.structures:
            raise ErreurModele("Choisissez un payeur et un bénéficiaire.")
        if payeur == beneficiaire:
            raise ErreurModele("Le payeur et le bénéficiaire doivent différer.")
        structure = beneficiaire      # la variable appartient au bénéficiaire
        identifiant = composer_id(creer_id(nom), structure)
        if identifiant in self.charges or identifiant in self.postes:
            raise ErreurModele("Une charge porte déjà ce nom : " + identifiant)
        if identifiant != ancien_id and identifiant in self.flux:
            raise ErreurModele(
                "Le flux %s existe déjà. Donnez un autre nom à ce flux."
                % identifiant)
        self.controler_calcul(expression, structure)
        ancienne = None
        paiement = self.flux[ancien_id].get("paiement") if ancien_id else None
        etiquettes = {k: v for k, v in self.flux[ancien_id].items()
                      if k in CLES_ETIQUETTES} if ancien_id else {}
        if ancien_id and ancien_id != identifiant:
            # Même place dans la liste : seul l'identifiant change.
            self.flux = {(identifiant if k == ancien_id else k): v
                         for k, v in self.flux.items()}
            ancienne = self.parametres.pop(ancien_id, None)
        self.flux[identifiant] = {"nom": nom.strip(), "payeur": payeur,
                                  "beneficiaire": beneficiaire,
                                  "structure": structure, "nature": nature,
                                  "effet": effet, "compte": compte}
        if paiement and nature == "Financier":
            self.flux[identifiant]["paiement"] = paiement
        self.flux[identifiant].update(etiquettes)
        fiche = self.parametres.get(identifiant) or ancienne \
            or self.fiche_vide(identifiant)
        fiche["id"] = identifiant
        fiche["mode"] = "formule"
        fiche["expression"] = expression.strip()
        fiche["table"] = []
        self.parametres[identifiant] = fiche
        if ancien_id and ancien_id != identifiant:
            self.renommer_reference(ancien_id, identifiant)
        self.synchroniser()
        return identifiant

    def supprimer_flux(self, identifiant):
        del self.flux[identifiant]
        self.parametres[identifiant]["expression"] = ""
        self.parametres[identifiant]["table"] = []
        self.synchroniser()

    def definir_paiement(self, identifiant, reglages):
        """Règle les impayés et le moratoire d'une transaction."""
        flux = self.flux[identifiant]
        if flux["nature"] != "Financier":
            raise ErreurModele("Un flux physique n'a pas de paiement.")
        valeurs = dict(PAIEMENT_DEFAUT)
        valeurs.update({k: v.strip() for k, v in reglages.items()})
        for cle in PAIEMENT_FORMULES:
            valeurs[cle] = valeurs[cle] or PAIEMENT_DEFAUT[cle]
            self.controler_calcul(valeurs[cle], flux["structure"])
        dates = [valeurs["moratoire_debut"], valeurs["moratoire_fin"]]
        if any(dates):
            try:
                if lire_date(dates[0]) > lire_date(dates[1]):
                    raise ValueError
            except ValueError:
                raise ErreurModele("Moratoire : dates de début et de fin "
                                   "attendues, au format JJ/MM/AAAA.")
        try:
            if int(valeurs["reprise_pas"]) < 1:
                raise ValueError
        except ValueError:
            raise ErreurModele("Reprise : nombre entier de pas attendu.")
        if valeurs == PAIEMENT_DEFAUT:
            flux.pop("paiement", None)
        else:
            flux["paiement"] = valeurs
        self.synchroniser()

    def references_paiements(self):
        noms = set()
        for f in self.flux.values():
            for cle in PAIEMENT_FORMULES:
                if "paiement" in f:
                    noms |= analyser_expression(f["paiement"][cle])
        for fiche in self.structures.values():
            for texte in fiche.get("capacite", {}).values():
                noms |= analyser_expression(texte)
        for fiche in self.parametres.values():
            for valeurs in fiche.get("perimetres", {}).values():
                if valeurs.get("expression"):
                    noms |= analyser_expression(valeurs["expression"])
        noms |= self.references_fonctions()
        return {indexee(n) for n in noms}

    def definir_capacite(self, identifiant, reglages):
        """Hypothèses de capacité d'investissement d'une structure."""
        valeurs = {k: reglages.get(k, "").strip() for k in CAPACITE_CHAMPS}
        if not any(valeurs.values()):
            self.structures[identifiant].pop("capacite", None)
            self.synchroniser()
            return
        if not all(valeurs[k] for k in ("couverture", "taux", "duree")):
            raise ErreurModele("Capacité : renseignez la couverture, le taux "
                               "et la durée.")
        valeurs["tresorerie_minimale"] = valeurs["tresorerie_minimale"] or "0"
        valeurs["besoin"] = valeurs["besoin"] or "0"
        for texte in valeurs.values():
            self.controler_calcul(texte, identifiant)
        self.structures[identifiant]["capacite"] = valeurs
        self.synchroniser()

    def controler_calcul(self, expression, structure):
        """Refuse qu'un calcul dépende d'un paramètre de post-traitement."""
        lies = analyser_expression(expression, structure,
                                   self.structures) & set(self.post)
        if lies:
            raise ErreurModele("Variable de post-traitement interdite dans "
                               "un calcul : " + ", ".join(sorted(lies)))

    def ajouter_post(self, nom, structure, expression, unite, ancien_id=None):
        """Paramètre calculé après la simulation, sans effet sur le calcul."""
        identifiant = composer_id(creer_id(nom), structure)
        if identifiant in self.parametres or (identifiant != ancien_id
                                              and identifiant in self.post):
            raise ErreurModele("Cette variable existe déjà : " + identifiant)
        if structure != STRUCTURE_COMMUNE and structure not in self.structures:
            raise ErreurModele("Choisissez une structure.")
        utilises = {indexee(n) for n in analyser_expression(
            expression, structure, self.structures, post=True)}
        connus = set(self.parametres) | set(self.post)
        inconnus = sorted(utilises - connus)
        if inconnus:
            raise ErreurModele("Variable inconnue : " + ", ".join(inconnus))
        if ancien_id:
            del self.post[ancien_id]
        self.post[identifiant] = {"nom": nom.strip(), "structure": structure,
                                  "expression": expression.strip(),
                                  "unite": unite}
        return identifiant

    def supprimer_post(self, identifiant):
        lies = [i for i, q in self.post.items() if i != identifiant
                and identifiant in analyser_expression(q["expression"],
                                                       post=True)]
        if lies:
            raise ErreurModele("Variable utilisée par : " + ", ".join(lies))
        del self.post[identifiant]

    def ajouter_poste(self, nom, structure, categorie, expression):
        """Élément du compte d'une entité : capital, actif, dette, etc."""
        if categorie not in CATEGORIES_POSTES:
            raise ErreurModele("Catégorie inconnue.")
        identifiant = composer_id(creer_id(nom), structure)
        if identifiant in self.postes or identifiant in self.charges \
                or identifiant in self.flux or identifiant in self.post:
            raise ErreurModele("Cette variable existe déjà : " + identifiant)
        self.controler_calcul(expression, structure)
        self.postes[identifiant] = {"nom": nom.strip(), "structure": structure,
                                    "categorie": categorie}
        fiche = self.parametres.get(identifiant) or \
            self.fiche_vide(identifiant)
        fiche.update({"mode": "formule", "expression": expression.strip(),
                      "table": []})
        self.parametres[identifiant] = fiche
        self.synchroniser()
        return identifiant

    def supprimer_poste(self, identifiant):
        del self.postes[identifiant]
        self.parametres[identifiant]["expression"] = ""
        self.parametres[identifiant]["table"] = []
        self.synchroniser()

    def ajouter_charge(self, nom, structure, expression, compte="Résultat"):
        """Charge propre à une structure, sans autre structure en face."""
        identifiant = composer_id(creer_id(nom), structure)
        if identifiant in self.charges or identifiant in self.flux \
                or identifiant in self.postes:
            raise ErreurModele("Cette variable existe déjà : " + identifiant)
        self.controler_calcul(expression, structure)
        self.charges[identifiant] = {"nom": nom.strip(),
                                     "structure": structure, "compte": compte}
        fiche = self.parametres.get(identifiant) or \
            self.fiche_vide(identifiant)
        fiche.update({"mode": "formule", "expression": expression.strip(),
                      "table": []})
        self.parametres[identifiant] = fiche
        self.synchroniser()
        return identifiant

    def supprimer_charge(self, identifiant):
        del self.charges[identifiant]
        self.parametres[identifiant]["expression"] = ""
        self.parametres[identifiant]["table"] = []
        self.synchroniser()

    def references(self, identifiant):
        """Variables utilisées ; x[s,Dakar] renvoie à la variable x[s,p]."""
        return {indexee(n) for n in self.references_brutes(identifiant)}

    def references_brutes(self, identifiant):
        fiche = self.parametres[identifiant]
        if fiche["mode"] == "table":
            if fiche["table"] \
                    and fiche["variable_table"] not in VARIABLES_SYSTEME:
                return {fiche["variable_table"]}
            return set()
        if not fiche["expression"]:
            return set()
        return analyser_expression(fiche["expression"],
                                   decomposer_id(identifiant)[1])

    def synchroniser(self):
        """Ajoute tout paramètre utilisé et retire ceux devenus inutiles."""
        for identifiant in list(self.parametres):
            for nom in self.references(identifiant):
                if nom not in self.parametres:
                    self.parametres[nom] = self.fiche_vide(nom)
        for nom in self.references_paiements():
            if nom not in self.parametres:
                self.parametres[nom] = self.fiche_vide(nom)
        for identifiant in list(self.parametres):
            fiche = self.parametres[identifiant]
            for valeurs in fiche.get("perimetres", {}).values():
                if valeurs.get("mode") == "formule" \
                        and valeurs.get("expression"):
                    for nom in map(indexee, analyser_expression(
                            valeurs["expression"])):
                        if nom not in self.parametres:
                            self.parametres[nom] = self.fiche_vide(nom)
        changement = True
        while changement:
            changement = False
            utilises = set(self.flux) | set(self.charges) | set(self.postes) \
                | self.references_paiements()
            for identifiant in self.parametres:
                utilises |= self.references(identifiant)
            for identifiant, fiche in list(self.parametres.items()):
                if (identifiant not in utilises and not fiche["expression"]
                        and not fiche["table"]
                        and not fiche.get("perimetres")):
                    del self.parametres[identifiant]
                    changement = True
        # Une nouvelle boucle peut être nécessaire après une suppression.
        for identifiant in list(self.parametres):
            for nom in self.references(identifiant):
                if nom not in self.parametres:
                    self.parametres[nom] = self.fiche_vide(nom)
        self.synchroniser_conversions()

    def definir_parametre(self, identifiant, mode, expression, lignes, unite,
                          valeur_initiale, convergence=CONVERGENCE_DEFAUT,
                          suivi=False, variable_table=VARIABLE_TEMPS,
                          lecture_table="paliers"):
        points = []
        if lecture_table not in LECTURES_TABLE.values():
            raise ErreurModele("Mode de lecture de la table inconnu.")
        if mode == "formule":
            self.controler_calcul(expression, decomposer_id(identifiant)[1])
        else:
            points = lire_table(lignes)
            if variable_table == identifiant:
                raise ErreurModele("La variable 1 doit être différente de la "
                                   "variable 2.")
            if variable_table not in VARIABLES_SYSTEME \
                    and variable_table not in self.parametres:
                raise ErreurModele("Variable 1 inconnue : " + variable_table)
        convergence = convergence.strip().replace(",", ".") \
            or CONVERGENCE_DEFAUT
        if valeur_initiale.strip():
            try:
                float(valeur_initiale.replace(",", "."))
            except ValueError:
                raise ErreurModele("Valeur initiale : nombre attendu.")
        try:
            if float(convergence) <= 0:
                raise ValueError
        except ValueError:
            raise ErreurModele("Convergence : nombre positif attendu.")
        self.parametres[identifiant].update({
            "mode": mode,
            "expression": expression.strip() if mode == "formule" else "",
            "table": points,
            "variable_table": variable_table,
            "lecture_table": lecture_table,
            "unite": unite,
            "valeur_initiale": valeur_initiale.strip().replace(",", "."),
            "convergence": convergence,
            "suivi": bool(suivi),
        })
        self.synchroniser()

    def cycles(self):
        """Retourne les paramètres qui dépendent d'eux-mêmes."""
        circulaires = set()
        for depart in self.parametres:
            pile, vus = list(self.references(depart)), set()
            while pile:
                courant = pile.pop()
                if courant == depart:
                    circulaires.add(depart)
                    break
                if courant not in vus and courant in self.parametres:
                    vus.add(courant)
                    pile.extend(self.references(courant))
        return circulaires

    def etat(self, identifiant, circulaires=None):
        fiche = self.parametres[identifiant]
        if circulaires is None:
            circulaires = self.cycles()
        if not fiche["expression"] and not fiche["table"]:
            return "À définir"
        if identifiant in circulaires:
            return "Circulaire"
        return "Défini"

    def definir_valeur_initiale(self, identifiant, texte):
        texte = texte.strip().replace(",", ".")
        if texte:
            try:
                float(texte)
            except ValueError:
                raise ErreurModele("Valeur initiale : nombre attendu.")
        self.parametres[identifiant]["valeur_initiale"] = texte

    def definir_simulation(self, date_debut, pas, date_fin,
                           iterations_max=ITERATIONS_MAX_DEFAUT,
                           conserver_convergence="non",
                           taux_actualisation=""):
        self.simulation.update({
            "date_debut": date_debut.strip(), "pas": pas.strip(),
            "date_fin": date_fin.strip(),
            "iterations_max": iterations_max.strip(),
            "conserver_convergence": conserver_convergence,
            "taux_actualisation": taux_actualisation.strip()})

    def definir_tarifs(self, option, structures, hausse_max, tri_cible,
                       structure_tri, tresorerie_min):
        """Réglages communs de l'optimisation des tarifs."""
        for nom, texte in (("Hausse maximale par an", hausse_max),
                           ("TRI cible", tri_cible),
                           ("Trésorerie minimale", tresorerie_min)):
            if texte.strip():
                try:
                    float(texte.replace(",", "."))
                except ValueError:
                    raise ErreurModele(nom + " : nombre attendu.")
        if tri_cible.strip() and structure_tri not in self.structures:
            raise ErreurModele("TRI cible : choisissez la structure.")
        options = [o.strip() for o in str(option).split(",") if o.strip()]
        if not options:
            raise ErreurModele("Cochez au moins une option de tarifs.")
        if any(o not in OPTIONS_TARIFS_UI for o in options):
            raise ErreurModele("Option de tarifs inconnue.")
        principale = self.simulation.get("option_principale", "")
        self.simulation.update({
            "option_principale": principale if principale in options
            else options[0],
            "option_tarifs": ",".join(options), "structures_equilibre":
            ",".join(s for s in structures if s in self.structures),
            "hausse_max": hausse_max.strip(), "tri_cible": tri_cible.strip(),
            "structure_tri": structure_tri if tri_cible.strip() else "",
            "tresorerie_min": tresorerie_min.strip()})

    # ------------------------ Fonctions de l'utilisateur ------------------------
    def activer_fonctions(self):
        FONCTIONS_UTILISATEUR.clear()
        FONCTIONS_UTILISATEUR.update(self.fonctions)

    def definir_fonction(self, nom, arguments, corps, description="",
                         ancien=None):
        nom = nom.strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", nom):
            raise ErreurModele("Nom de fonction : minuscules, chiffres et _, "
                               "sans accent.")
        if nom in FONCTIONS or nom in FONCTIONS_POST or nom in MOTS_CLES \
                or nom in VARIABLES_SYSTEME:
            raise ErreurModele("Nom réservé : " + nom)
        if nom != ancien and nom in self.fonctions:
            raise ErreurModele("Cette fonction existe déjà : " + nom)
        if ancien and nom != ancien and self.appels(ancien):
            raise ErreurModele("Renommage impossible, %s est utilisée par : %s"
                               % (ancien, ", ".join(self.appels(ancien))))
        noms = [a.strip() for a in arguments.split(",") if a.strip()] \
            if isinstance(arguments, str) else list(arguments)
        for argument in noms:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", argument) \
                    or argument in FONCTIONS or argument in MOTS_CLES:
                raise ErreurModele("Argument incorrect : " + argument)
        if len(set(noms)) != len(noms):
            raise ErreurModele("Deux arguments portent le même nom.")
        lignes = lire_corps(corps)
        essai = dict(self.fonctions)
        essai.pop(ancien, None)
        essai[nom] = {"arguments": noms, "corps": corps.strip(),
                      "description": description.strip()}
        sauvegarde = dict(FONCTIONS_UTILISATEUR)
        FONCTIONS_UTILISATEUR.clear()
        FONCTIONS_UTILISATEUR.update(essai)
        try:
            locaux = set(noms)
            for interne, formule in lignes:
                compiler_expression(formule, self.structures, locaux=locaux)
                locaux.add(interne)
            deplier_fonctions("%s(%s)" % (nom, ", ".join(noms)))
        except ErreurModele:
            FONCTIONS_UTILISATEUR.clear()
            FONCTIONS_UTILISATEUR.update(sauvegarde)
            raise
        self.fonctions = essai
        self.activer_fonctions()
        self.synchroniser()

    def appels(self, nom):
        """Formules qui appellent une fonction."""
        motif = re.compile(r"(?<![\w\]])%s\s*\(" % re.escape(nom))
        textes = [(i, f["expression"]) for i, f in self.parametres.items()]
        textes += [(i, q["expression"]) for i, q in self.post.items()]
        textes += [(n, f["corps"]) for n, f in self.fonctions.items()
                   if n != nom]
        for i, f in self.parametres.items():
            for valeurs in f.get("perimetres", {}).values():
                textes.append((i, valeurs.get("expression", "")))
        return sorted({i for i, texte in textes if motif.search(texte or "")})

    def supprimer_fonction(self, nom):
        if self.appels(nom):
            raise ErreurModele("%s est utilisée par : %s"
                               % (nom, ", ".join(self.appels(nom))))
        del self.fonctions[nom]
        self.activer_fonctions()

    def ajouter_bibliotheque(self):
        ajoutees = []
        for nom, fiche in bibliotheque_fonctions().items():
            if nom not in self.fonctions:
                self.definir_fonction(nom, fiche["arguments"], fiche["corps"],
                                      fiche["description"])
                ajoutees.append(nom)
        return ajoutees

    def references_fonctions(self):
        """Valeurs [projet] lues dans le corps des fonctions."""
        noms = set()
        for fiche in self.fonctions.values():
            locaux = set(fiche["arguments"])
            for interne, formule in lire_corps(fiche["corps"]):
                noms |= compiler_expression(formule, locaux=locaux)[1]
                locaux.add(interne)
        return noms

    # --------------------------- Périmètres ---------------------------
    def definir_perimetres(self, colonnes, lignes):
        """Table des périmètres : une ligne par p, une colonne par groupe."""
        colonnes = [c.strip() for c in colonnes if c.strip()]
        if len({creer_id(c) for c in colonnes}) != len(colonnes):
            raise ErreurModele("Deux colonnes de groupes portent le même nom.")
        perimetres, vus = [], set()
        for ligne in lignes:
            nom = str(ligne[0]).strip()
            if not nom:
                continue
            identifiant = creer_id(nom)
            if identifiant == PERIMETRE_COURANT:
                raise ErreurModele("« p » est réservé au périmètre courant.")
            if identifiant == "global":
                raise ErreurModele("« Global » est réservé à l'ensemble "
                                   "des périmètres.")
            if identifiant in vus:
                raise ErreurModele("Périmètre en double : " + nom)
            vus.add(identifiant)
            groupes, fiche = fiche_perimetre(colonnes, ligne)
            perimetres.append(fiche)
        self.colonnes_groupes = [c for c in colonnes if creer_id(c)
                                 not in COLONNES_X + COLONNES_Y]
        self.perimetres = perimetres

    def a_coordonnees(self):
        return any(p.get("x") is not None for p in self.perimetres)

    def colonnes_table(self):
        """Colonnes de la table affichée : groupes, puis X et Y."""
        return list(self.colonnes_groupes) + (
            ["X", "Y"] if self.a_coordonnees() else [])

    def lignes_table(self):
        lignes = []
        for p in self.perimetres:
            ligne = [p["nom"]] + [p["groupes"].get(c, "")
                                  for c in self.colonnes_groupes]
            if self.a_coordonnees():
                ligne += ["" if p.get(k) is None else "%g" % p[k]
                          for k in ("x", "y")]
            lignes.append(ligne)
        return lignes

    def ids_perimetres(self):
        return [creer_id(p["nom"]) for p in self.perimetres]

    def groupes(self):
        """Clé de groupe -> périmètres ; « Colonne:Valeur » ou « Valeur »."""
        complets, simples = {}, {}
        for p in self.perimetres:
            pid = creer_id(p["nom"])
            simples.setdefault(pid, set()).add(("", pid))
            for colonne, valeur in p["groupes"].items():
                if not valeur:
                    continue
                cle = creer_id(colonne) + ":" + creer_id(valeur)
                complets.setdefault(cle, []).append(pid)
                simples.setdefault(creer_id(valeur), set()).add(
                    (creer_id(colonne), creer_id(valeur)))
        return complets, simples

    def membres(self, texte):
        """Périmètres d'un groupe écrit "Région:Thiès", "Thiès" ou ""."""
        ids = self.ids_perimetres()
        if not texte.strip():
            return ids
        complets, simples = self.groupes()
        if ":" in texte:
            colonne, valeur = texte.split(":", 1)
            cle = creer_id(colonne) + ":" + creer_id(valeur)
            if cle not in complets:
                raise ErreurModele("Groupe inconnu : " + texte)
            return complets[cle]
        cle = creer_id(texte)
        if cle in ids:
            return [cle]
        trouves = simples.get(cle, set())
        if len(trouves) > 1:
            raise ErreurModele("Groupe ambigu : %s ; précisez "
                               "\"Colonne:%s\"." % (texte, texte))
        if not trouves:
            raise ErreurModele("Groupe ou périmètre inconnu : " + texte)
        colonne, valeur = next(iter(trouves))
        return complets[colonne + ":" + valeur]

    def definir_valeur_perimetre(self, identifiant, perimetre, valeurs):
        """Valeur propre d'un périmètre pour une variable x[structure,p].

        valeurs : mode, expression, table, valeur_initiale ; une clé absente
        ou vide reprend la valeur commune.
        """
        fiche = self.parametres[identifiant]
        propres = dict(fiche.setdefault("perimetres", {}).get(perimetre, {}))
        if "valeur_initiale" in valeurs:
            texte = valeurs["valeur_initiale"].strip().replace(",", ".")
            if texte:
                try:
                    float(texte)
                except ValueError:
                    raise ErreurModele("Valeur initiale : nombre attendu.")
                propres["valeur_initiale"] = texte
            else:
                propres.pop("valeur_initiale", None)
        if "mode" in valeurs:
            if valeurs["mode"] is None:
                for cle in ("mode", "expression", "table"):
                    propres.pop(cle, None)
            elif valeurs["mode"] == "formule":
                self.controler_calcul(valeurs["expression"],
                                      decomposer_id(identifiant)[1])
                propres.update({"mode": "formule", "table": [],
                                "expression": valeurs["expression"].strip()})
            else:
                propres.update({"mode": "table", "expression": "",
                                "table": lire_table(valeurs["table"])})
        if propres:
            fiche["perimetres"][perimetre] = propres
        else:
            fiche["perimetres"].pop(perimetre, None)
        self.synchroniser()

    def a_developper(self):
        return bool(self.perimetres or self.fonctions
                    or any(est_indexe(i) for i in self.parametres))

    def developper(self):
        """Modèle de calcul : chaque variable x[s,p] devient une par périmètre.

        Retourne une copie sans périmètres, plus la correspondance dans
        l'attribut « developpement ».
        """
        import copy
        ids = self.ids_perimetres()
        noms = {creer_id(p["nom"]): p["nom"] for p in self.perimetres}
        self.activer_fonctions()
        modele = copy.deepcopy(self)
        modele.perimetres, modele.colonnes_groupes = [], []
        reference = re.compile(r"\[\s*([^\[\],]+?)\s*,\s*([^\[\]]+?)\s*\]")
        agregation = re.compile(
            r"\b(%s)\(\s*([a-z][a-z0-9_]*)\s*\[\s*([^\[\],]+?)\s*,\s*p\s*\]"
            r"\s*(?:,\s*\"([^\"]*)\"\s*)?\)" % "|".join(AGREGATIONS_P))

        def deplier(texte):
            texte = deplier_fonctions(texte)

            def remplacer(trouve):
                fonction, nom, structure, groupe = trouve.groups()
                membres = self.membres(groupe or "")
                termes = ["%s[%s, %s]" % (nom, structure.strip(), m)
                          for m in membres]
                if not termes:
                    raise ErreurModele("La table des périmètres est vide.")
                if fonction == "somme_p":
                    return "(" + " + ".join(termes) + ")"
                if fonction == "moyenne_p":
                    return "((%s) / %d)" % (" + ".join(termes), len(termes))
                return "%s(%s)" % (fonction[:3], ", ".join(termes))
            return agregation.sub(remplacer, texte)

        def utilise_p(texte):
            return any(creer_id(t.group(2)) == PERIMETRE_COURANT
                       for t in reference.finditer(texte))

        def instancier(texte, perimetre):
            def remplacer(trouve):
                structure, cible = trouve.group(1).strip(), trouve.group(2)
                cible = creer_id(cible)
                if cible == PERIMETRE_COURANT:
                    cible = perimetre
                elif cible not in ids:
                    raise ErreurModele("Périmètre inconnu : "
                                       + trouve.group(2))
                return "[%s, %s]" % (structure, cible)
            return reference.sub(remplacer, texte)

        def nom_instance(identifiant, perimetre):
            nom, structure = decomposer_id(identifiant)
            return composer_id(nom, structure + "," + perimetre)

        nouveaux, indexes, details = {}, {}, {}
        for identifiant, fiche in self.parametres.items():
            if est_indexe(identifiant):
                if not ids:
                    raise ErreurModele("%s : remplissez la table des "
                                       "périmètres." % identifiant)
                indexes[identifiant] = []
                for pid in ids:
                    copie = copy.deepcopy(fiche)
                    copie.pop("perimetres", None)
                    propres = fiche.get("perimetres", {}).get(pid, {})
                    for cle in ("mode", "expression", "table"):
                        if cle in propres:
                            copie[cle] = copy.deepcopy(propres[cle])
                    if propres.get("valeur_initiale"):
                        copie["valeur_initiale"] = propres["valeur_initiale"]
                    copie["expression"] = instancier(
                        deplier(copie["expression"]), pid)
                    if copie["mode"] == "table":
                        copie["expression"] = ""
                    if est_indexe(copie["variable_table"]):
                        copie["variable_table"] = nom_instance(
                            copie["variable_table"], pid)
                    copie["id"] = nom_instance(identifiant, pid)
                    nouveaux[copie["id"]] = copie
                    indexes[identifiant].append(copie["id"])
                continue
            copie = copy.deepcopy(fiche)
            copie["expression"] = deplier(copie["expression"])
            if est_indexe(copie.get("variable_table", "")):
                raise ErreurModele("%s : une table non indexée ne peut pas "
                                   "lire une variable par périmètre."
                                   % identifiant)
            if utilise_p(copie["expression"]):
                if identifiant not in self.flux and \
                        identifiant not in self.charges and \
                        identifiant not in self.postes:
                    raise ErreurModele(
                        "%s utilise p : écrivez-le %s ou utilisez somme_p."
                        % (identifiant, nom_instance(identifiant, "p")))
                details[identifiant] = []
                for pid in ids:
                    detail = copy.deepcopy(fiche)
                    detail["expression"] = instancier(copie["expression"],
                                                      pid)
                    detail["id"] = nom_instance(identifiant, pid)
                    nouveaux[detail["id"]] = detail
                    details[identifiant].append(detail["id"])
                copie["expression"] = " + ".join(details[identifiant])
            nouveaux[identifiant] = copie
        modele.parametres = nouveaux
        for q in modele.post.values():
            q["expression"] = deplier(q["expression"])
            if utilise_p(q["expression"]):
                raise ErreurModele("Post-traitement : utilisez somme_p pour "
                                   "un paramètre par périmètre.")
        for f in modele.flux.values():
            for cle in PAIEMENT_FORMULES:
                if "paiement" in f:
                    f["paiement"][cle] = deplier(f["paiement"][cle])
        for fiche in modele.structures.values():
            if "capacite" in fiche:
                fiche["capacite"] = {k: deplier(v)
                                     for k, v in fiche["capacite"].items()}
        modele.fonctions = {}
        modele.developpement = {"perimetres": ids, "noms": noms,
                                "indexes": indexes, "details": details,
                                "colonnes": list(self.colonnes_groupes),
                                "table": copy.deepcopy(self.perimetres)}
        return modele

    def definir_tarif(self, identifiant, optimisable, tarif_max):
        if tarif_max.strip():
            try:
                float(tarif_max.replace(",", "."))
            except ValueError:
                raise ErreurModele("Tarif maximal : nombre attendu.")
        self.parametres[identifiant]["optimisable"] = bool(optimisable)
        self.parametres[identifiant]["tarif_max"] = \
            tarif_max.strip().replace(",", ".") if optimisable else ""

    def verifier(self):
        """Retourne (erreurs bloquantes, alertes) avant la simulation."""
        erreurs, alertes = [], []
        if self.a_developper():
            try:
                self.developper()
            except ErreurModele as erreur:
                erreurs.append(str(erreur))
        debut, fin, pas = None, None, None
        unite_temps = self.references_unites["Temps"]
        try:
            debut = lire_date(self.simulation["date_debut"])
        except ValueError:
            erreurs.append("Date de démarrage : date attendue au format "
                           "JJ/MM/AAAA.")
        try:
            fin = lire_date(self.simulation["date_fin"])
        except ValueError:
            erreurs.append("Date de fin : date attendue au format JJ/MM/AAAA.")
        try:
            float((self.simulation["taux_actualisation"] or "0")
                  .replace(",", "."))
        except ValueError:
            erreurs.append("Taux d'actualisation : nombre attendu, 0.08 pour "
                           "8 %.")
        if debut and fin and fin < debut:
            erreurs.append("La date de fin doit suivre la date de démarrage.")
        try:
            pas = float(self.simulation["pas"].replace(",", "."))
            if pas <= 0:
                raise ValueError
        except ValueError:
            pas = None
            erreurs.append("Pas de temps : nombre positif attendu, en %s."
                           % unite_temps)
        if debut and fin and pas and fin >= debut:
            nombre = ((fin - debut).days + 1) / (
                pas * ANNEES_PAR_UNITE[unite_temps] * 365)
            if nombre > PERIODES_MAX:
                erreurs.append("Pas de temps trop petit : environ %d pas, "
                               "pour un maximum de %d."
                               % (nombre, PERIODES_MAX))
        try:
            if int(self.simulation["iterations_max"]) <= 0:
                raise ValueError
        except ValueError:
            erreurs.append("Itérations max par pas de temps : nombre entier "
                           "positif attendu.")
        connus = set(self.parametres) | set(self.post)
        for i, q in sorted(self.post.items()):
            try:
                inconnus = {indexee(n) if self.perimetres else n
                            for n in analyser_expression(
                                q["expression"], post=True)} - connus
            except ErreurModele as erreur:
                erreurs.append("%s : %s" % (i, erreur))
                continue
            if inconnus:
                erreurs.append("Variable inconnue : "
                               + ", ".join(sorted(inconnus)))
        if not self.parametres:
            erreurs.append("Le modèle ne contient aucun paramètre.")
        circulaires = self.cycles()
        for i, p in sorted(self.parametres.items()):
            if self.etat(i, circulaires) == "À définir":
                erreurs.append(i + " : formule ou table à définir.")
            if not p["valeur_initiale"]:
                erreurs.append(i + " : valeur initiale manquante.")
            if not p["unite"]:
                alertes.append(i + " : unité non renseignée.")
            if p["mode"] == "table" and p["table"] and debut and fin \
                    and p["variable_table"] == VARIABLE_TEMPS:
                if p["table"][0][0] > debut.year \
                        or p["table"][-1][0] < fin.year:
                    alertes.append(
                        "%s : la table ne couvre pas %d-%d ; la valeur connue "
                        "la plus proche sera gardée."
                        % (i, debut.year, fin.year))
        return erreurs, alertes

    def convertir_ancien_cadre(self, anciens):
        """Reprend un fichier écrit avec l'année de démarrage et l'horizon."""
        if not anciens.get("annee_debut"):
            return
        unite = self.references_unites["Temps"]
        annee = int(anciens["annee_debut"])
        duree = float(anciens.get("horizon", "1").replace(",", ".")) \
            * ANNEES_PAR_UNITE[unite]
        ancien_pas = self.simulation["pas"]
        annees_pas = MOIS_ANCIENS_PAS[ancien_pas] / 12 \
            if ancien_pas in MOIS_ANCIENS_PAS else 1 / 365
        self.simulation["date_debut"] = "01/01/%d" % annee
        self.simulation["date_fin"] = "31/12/%d" % (
            annee + math.ceil(duree - 1e-9) - 1)
        self.simulation["pas"] = "%.10g" % (
            annees_pas / ANNEES_PAR_UNITE[unite])

    def ecrire(self, chemin):
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write("\n".join(self.texte()) + "\n")

    def texte(self):
        """Toute la mise en données : formules, états initiaux et calcul."""
        lignes = ["# HapNatt - jeu de données", "", "[SIMULATION]",
                  "cle\tvaleur",
                  "date_debut\t" + self.simulation["date_debut"],
                  "pas\t" + self.simulation["pas"],
                  "pas_unite\t" + self.references_unites["Temps"],
                  "date_fin\t" + self.simulation["date_fin"],
                  "taux_actualisation\t"
                  + self.simulation["taux_actualisation"],
                  "iterations_max\t" + self.simulation["iterations_max"],
                  "conserver_convergence\t"
                  + self.simulation["conserver_convergence"],
                  "hors_table\t" + REGLE_HORS_TABLE] + [
                      cle + "\t" + self.simulation.get(cle, "")
                      for cle in CLES_TARIFS] + [
                  "", "[FONCTIONS]", "nom\targuments\tcorps\tdescription"] + [
                      "\t".join((n, ", ".join(f["arguments"]),
                                 vers_fichier(f["corps"]),
                                 f.get("description", "")))
                      for n, f in self.fonctions.items()] + [
                  "", "[REFERENCES]", "dimension\tunite"]
        for dimension, unite in self.references_unites.items():
            lignes.append(dimension + "\t" + unite)
        lignes += ["", "[CONVERSIONS]", "unite\treference\tfacteur"]
        for ligne in self.conversions()[0]:
            lignes.append("\t".join(ligne))
        lignes += ["", "[STRUCTURES]",
                  "id\tnom\ttype\tx\ty\tmissions"]
        for i, s in self.structures.items():
            lignes.append("\t".join((
                i, s["nom"], s["type"],
                "" if s["x"] is None else "%d" % s["x"],
                "" if s["y"] is None else "%d" % s["y"],
                " | ".join(s["missions"]))))
        lignes += ["", "[FLUX]",
                   "id\tnom\tde\tvers\tstructure\tnature\teffet\tcompte\t"
                   "etiquette_dx\tetiquette_dy\tetiquette_resultat_dx\t"
                   "etiquette_resultat_dy"]
        for i, f in self.flux.items():
            decalages = []
            for cle in CLES_ETIQUETTES:
                decalages += ["%d" % v if v else ""
                              for v in f.get(cle) or (0, 0)]
            lignes.append("\t".join((i, f["nom"], f["payeur"],
                                     f["beneficiaire"], f["structure"],
                                     f["nature"], f["effet"], f["compte"],
                                     *decalages)))
        lignes += ["", "[CAPACITES]", "id\t" + "\t".join(CAPACITE_CHAMPS)]
        for i, fiche in self.structures.items():
            if "capacite" in fiche:
                lignes.append("\t".join(
                    [i] + [fiche["capacite"][k] for k in CAPACITE_CHAMPS]))
        lignes += ["", "[PAIEMENTS]",
                   "id\t" + "\t".join(PAIEMENT_DEFAUT)]
        for i, f in self.flux.items():
            if "paiement" in f:
                lignes.append("\t".join(
                    [i] + [f["paiement"][k] for k in PAIEMENT_DEFAUT]))
        lignes += ["", "[CHARGES]", "id\tnom\tstructure\tcompte"]
        for i, c in self.charges.items():
            lignes.append("\t".join((i, c["nom"], c["structure"],
                                     c["compte"])))
        lignes += ["", "[POSTES]", "id\tnom\tstructure\tcategorie"]
        for i, c in self.postes.items():
            lignes.append("\t".join((i, c["nom"], c["structure"],
                                     c["categorie"])))
        lignes += ["", "[PARAMETRES]",
                   "id\tmode\texpression\tunite\tvaleur_initiale\tconvergence\t"
                   "suivi\tvariable_1_table\tlecture_table\tconversion"]
        for i, p in self.parametres.items():
            lignes.append("\t".join((i, p["mode"],
                                     vers_fichier(p["expression"]), p["unite"],
                                     p["valeur_initiale"], p["convergence"],
                                     "oui" if p["suivi"] else "non",
                                     p["variable_table"],
                                     p["lecture_table"],
                                     "oui" if p.get("conversion") else "non")))
        lignes += ["", "[PERIMETRES]",
                   "\t".join(["perimetre"] + self.colonnes_table())]
        for ligne in self.lignes_table():
            lignes.append("\t".join(ligne))
        lignes += ["", "[VALEURS_PERIMETRE]",
                   "id\tperimetre\tmode\texpression\tvaleur_initiale"]
        tables_p = []
        for i, fiche in self.parametres.items():
            for pid, v in fiche.get("perimetres", {}).items():
                lignes.append("\t".join((
                    i, pid, v.get("mode", ""),
                    vers_fichier(v.get("expression", "")),
                    v.get("valeur_initiale", ""))))
                for x, y in v.get("table", []):
                    tables_p.append("%s\t%s\t%r\t%r" % (i, pid, x, y))
        lignes += ["", "[TABLES_PERIMETRE]", "id\tperimetre\tx\ty"] + tables_p
        lignes += ["", "[TARIFS_OPTIMISABLES]", "id\ttarif_max"]
        for i, p in self.parametres.items():
            if p.get("optimisable"):
                lignes.append(i + "\t" + p.get("tarif_max", ""))
        lignes += ["", "[POST_TRAITEMENT]",
                   "id\tnom\tstructure\texpression\tunite"]
        for i, q in self.post.items():
            lignes.append("\t".join((i, q["nom"], q["structure"],
                                     vers_fichier(q["expression"]),
                                     q["unite"])))
        lignes += ["", "[TABLES]", "variable_2\tvariable_1\tvaleur"]
        for i, p in self.parametres.items():
            for valeur_1, valeur_2 in p["table"]:
                lignes.append("%s\t%r\t%r" % (i, valeur_1, valeur_2))
        return lignes

    @classmethod
    def lire(cls, chemin):
        """Lit un jeu de données, ou celui recopié dans un Resultat.dat."""
        modele, section, entete, colonnes = cls(), None, False, []
        anciens = {}
        with open(chemin, encoding="utf-8") as fichier:
            contenu = fichier.read().splitlines()
        if MARQUE_JEU_DE_DONNEES in contenu:
            contenu = contenu[contenu.index(MARQUE_JEU_DE_DONNEES) + 1:]
        if "[STRUCTURES]" not in contenu:
            raise ErreurModele("Ce fichier ne contient pas de mise en données.")
        FONCTIONS_UTILISATEUR.clear()
        for brut in contenu:
            ligne = brut.rstrip("\r\n")
            if not ligne.strip() or ligne.startswith("#"):
                continue
            if ligne.startswith("["):
                section, entete = ligne.strip("[]"), True
                continue
            if entete:
                entete, colonnes = False, ligne.split("\t")
                continue
            c = ligne.split("\t")
            if section == "CONVERSIONS":
                continue         # recalculées à partir des unités
            if section == "REFERENCES":
                modele.references_unites[c[0]] = c[1]
            elif section == "SIMULATION":
                if c[0] in modele.simulation:
                    modele.simulation[c[0]] = c[1] if len(c) > 1 else ""
                elif c[0] in ("annee_debut", "horizon"):
                    anciens[c[0]] = c[1] if len(c) > 1 else ""
            elif section == "FONCTIONS":
                modele.fonctions[c[0]] = {
                    "arguments": [a.strip() for a in c[1].split(",")
                                  if a.strip()],
                    "corps": depuis_fichier(c[2]),
                    "description": c[3] if len(c) > 3 else ""}
                modele.activer_fonctions()
            elif section == "STRUCTURES":
                missions = c[5].split(" | ") if len(c) > 5 and c[5] else []
                modele.structures[c[0]] = {
                    "nom": c[1], "type": c[2], "missions": missions,
                    "x": int(c[3]) if len(c) > 3 and c[3] else None,
                    "y": int(c[4]) if len(c) > 4 and c[4] else None}
            elif section == "POST_TRAITEMENT":
                modele.post[c[0]] = {"nom": c[1], "structure": c[2],
                                     "expression": depuis_fichier(c[3]),
                                     "unite": c[4]}
            elif section == "CHARGES":
                modele.charges[c[0]] = {
                    "nom": c[1], "structure": c[2],
                    "compte": c[3] if len(c) > 3 else "Résultat"}
            elif section == "CAPACITES":
                modele.structures[c[0]]["capacite"] = dict(
                    zip(CAPACITE_CHAMPS, c[1:]))
            elif section == "PAIEMENTS":
                modele.flux[c[0]]["paiement"] = dict(
                    zip(PAIEMENT_DEFAUT, c[1:]))
            elif section == "POSTES":
                modele.postes[c[0]] = {"nom": c[1], "structure": c[2],
                                       "categorie": c[3]}
            elif section == "FLUX":
                modele.flux[c[0]] = {"nom": c[1], "payeur": c[2],
                                     "beneficiaire": c[3],
                                     "structure": c[4],
                                     "nature": c[5] if len(c) > 5
                                     else "Financier",
                                     "effet": c[6] if len(c) > 6
                                     else "Capacité",
                                     "compte": c[7] if len(c) > 7
                                     else "Résultat"}
                # Étiquettes déplacées à la souris : schéma, puis résultats.
                valeurs = [int(float(v)) if v.strip() else 0
                           for v in (list(c[8:12]) + [""] * 4)[:4]]
                for rang, cle in enumerate(CLES_ETIQUETTES):
                    decalage = valeurs[2 * rang:2 * rang + 2]
                    if any(decalage):
                        modele.flux[c[0]][cle] = decalage
            elif section == "PARAMETRES":
                d = dict(zip(colonnes, c))
                modele.parametres[c[0]] = {
                    "id": c[0], "mode": c[1],
                    "expression": depuis_fichier(c[2]),
                    "table": [], "unite": c[3], "valeur_initiale": c[4],
                    "convergence": (d.get("convergence")
                                    or d.get("tol_abs")
                                    or CONVERGENCE_DEFAUT),
                    "suivi": d.get("suivi") == "oui",
                    "variable_table": c[7] if len(c) > 7
                    else VARIABLE_TEMPS,
                    "lecture_table": c[8] if len(c) > 8 else "paliers",
                    "conversion": len(c) > 9 and c[9] == "oui"}
            elif section == "PERIMETRES":
                groupes, fiche = fiche_perimetre(colonnes[1:], c)
                modele.colonnes_groupes = groupes
                modele.perimetres.append(fiche)
            elif section == "VALEURS_PERIMETRE":
                propres = {}
                if len(c) > 2 and c[2]:
                    propres.update({"mode": c[2], "table": [],
                                    "expression": depuis_fichier(c[3])})
                if len(c) > 4 and c[4]:
                    propres["valeur_initiale"] = c[4]
                if c[0] in modele.parametres:
                    modele.parametres[c[0]].setdefault(
                        "perimetres", {})[c[1]] = propres
            elif section == "TABLES_PERIMETRE":
                modele.parametres[c[0]]["perimetres"][c[1]].setdefault(
                    "table", []).append((float(c[2]), float(c[3])))
            elif section == "TARIFS_OPTIMISABLES":
                if c[0] in modele.parametres:
                    modele.parametres[c[0]]["optimisable"] = True
                    modele.parametres[c[0]]["tarif_max"] = \
                        c[1] if len(c) > 1 else ""
            elif section == "TABLES":
                modele.parametres[c[0]]["table"].append(
                    (float(c[1]), float(c[2])))
        modele.synchroniser()
        modele.convertir_ancien_cadre(anciens)
        return modele


def _segments_croises(a, b, c, d):
    def cote(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (cote(a, b, c) * cote(a, b, d) < 0
            and cote(c, d, a) * cote(c, d, b) < 0)


def _traverse_bloc(a, b, centre, demi_l, demi_h):
    """Vrai si le segment ab passe sur le rectangle autour de centre."""
    x1, y1 = centre[0] - demi_l, centre[1] - demi_h
    x2, y2 = centre[0] + demi_l, centre[1] + demi_h
    coins = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
    return any(_segments_croises(a, b, coins[i], coins[(i + 1) % 4])
               for i in range(4))


def _cout_schema(positions, liens, demi_l, demi_h):
    """Note d'un placement : plus elle est basse, plus le schéma est lisible."""
    cout = 0.0
    segments = [(positions[a], positions[b], a, b) for a, b in liens]
    for rang, (p, q, a, b) in enumerate(segments):
        cout += ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5
        for r, t, c, d in segments[rang + 1:]:
            if not {a, b} & {c, d} and _segments_croises(p, q, r, t):
                cout += 4000
        for bloc, centre in positions.items():
            if bloc not in (a, b) \
                    and _traverse_bloc(p, q, centre, demi_l, demi_h):
                cout += 8000
    return cout


def optimiser_positions(blocs, liens, largeur, hauteur, largeur_bloc=190,
                        hauteur_bloc=74, duree_max=2.0, essais=40):
    """Place les blocs sur une grille en limitant les croisements de flèches.

    Le résultat est reproductible : le tirage aléatoire utilise une graine fixe.
    """
    blocs = list(blocs)
    liens = sorted({tuple(sorted(lien)) for lien in liens})
    if not blocs:
        return {}
    largeur = max(largeur, largeur_bloc + 40)
    hauteur = max(hauteur, hauteur_bloc + 80)
    colonnes = max(1, min(int((largeur - 40) // (largeur_bloc + 90)),
                          math.ceil(math.sqrt(len(blocs) * largeur / hauteur))))
    lignes = max(math.ceil(len(blocs) / colonnes),
                 min(int((hauteur - 70) // (hauteur_bloc + 90)),
                     math.ceil(math.sqrt(len(blocs) * hauteur / largeur)) + 1))
    def coordonnee(rang, nombre, taille, dimension, bas):
        if nombre == 1:
            return (taille - bas) / 2
        marge = dimension / 2 + 20
        return marge + rang * (taille - bas - 2 * marge) / (nombre - 1)

    cases = [(coordonnee(c, colonnes, largeur, largeur_bloc, 0),
              coordonnee(l, lignes, hauteur, hauteur_bloc, 40))
             for l in range(lignes) for c in range(colonnes)]
    while len(cases) < len(blocs):     # cas extrême : petite fenêtre
        cases.append((cases[-1][0], cases[-1][1] + hauteur_bloc + 30))
    demi_l, demi_h = largeur_bloc / 2 + 8, hauteur_bloc / 2 + 8
    generateur = random.Random(20261104)
    limite = time.monotonic() + duree_max
    meilleur, meilleur_cout = None, float("inf")
    for essai in range(essais):
        ordre = cases[:]
        generateur.shuffle(ordre)
        place = dict(zip(blocs, ordre))
        libres = ordre[len(blocs):]
        cout = _cout_schema(place, liens, demi_l, demi_h)
        ameliore = True
        while ameliore and time.monotonic() < limite:
            ameliore = False
            for rang, a in enumerate(blocs):
                for b in blocs[rang + 1:]:
                    place[a], place[b] = place[b], place[a]
                    nouveau = _cout_schema(place, liens, demi_l, demi_h)
                    if nouveau < cout - 1e-6:
                        cout, ameliore = nouveau, True
                    else:
                        place[a], place[b] = place[b], place[a]
                for rang_libre, case in enumerate(libres):
                    ancienne = place[a]
                    place[a] = case
                    nouveau = _cout_schema(place, liens, demi_l, demi_h)
                    if nouveau < cout - 1e-6:
                        cout, ameliore = nouveau, True
                        libres[rang_libre] = ancienne
                    else:
                        place[a] = ancienne
        if cout < meilleur_cout:
            meilleur, meilleur_cout = dict(place), cout
        if time.monotonic() >= limite and meilleur is not None:
            break
    return {b: (int(round(p[0])), int(round(p[1])))
            for b, p in meilleur.items()}


def tester_appel(modele, texte):
    """Évalue un appel d'essai, avec les valeurs [projet] du modèle."""
    import copy
    import ppp_moteur
    modele.activer_fonctions()
    essai = Modele()
    essai.fonctions = copy.deepcopy(modele.fonctions)
    essai.activer_fonctions()
    essai.ajouter_structure("Essai", "Autorité")
    analyser_expression(texte, structures=essai.structures)
    fiche = essai.fiche_vide("essai[essai]")
    fiche.update({"expression": texte, "valeur_initiale": "0"})
    essai.parametres["essai[essai]"] = fiche
    a_copier = {n for n in modele.references_fonctions()}
    while a_copier:
        nom = a_copier.pop()
        if nom in modele.parametres and nom not in essai.parametres:
            essai.parametres[nom] = copy.deepcopy(modele.parametres[nom])
            a_copier |= modele.references(nom)
    essai.references_unites = dict(modele.references_unites)
    essai.definir_simulation("01/01/2030", "1", "31/12/2030")
    resultat = ppp_moteur.simuler(essai)
    modele.activer_fonctions()
    if resultat["erreurs"]:
        raise ErreurModele(resultat["erreurs"][0])
    return resultat["series"]["essai[essai]"][0]


def nombre_coordonnee(texte, nom):
    texte = str(texte).strip().replace(",", ".")
    if not texte:
        return None
    try:
        return float(texte)
    except ValueError:
        raise ErreurModele("Coordonnée illisible pour %s : %s" % (nom, texte))


def fiche_perimetre(colonnes, ligne):
    """(colonnes de groupes, fiche) ; X et Y deviennent des coordonnées."""
    ligne = list(ligne) + [""] * (len(colonnes) + 1)
    nom = str(ligne[0]).strip()
    fiche, groupes = {"nom": nom, "groupes": {}, "x": None, "y": None}, []
    for colonne, valeur in zip(colonnes, ligne[1:]):
        cle = creer_id(colonne)
        if cle in COLONNES_X:
            fiche["x"] = nombre_coordonnee(valeur, nom)
        elif cle in COLONNES_Y:
            fiche["y"] = nombre_coordonnee(valeur, nom)
        else:
            groupes.append(colonne)
            fiche["groupes"][colonne] = str(valeur).strip()
    return groupes, fiche


def lire_tableau_perimetres(chemin):
    """Lit un .csv ou .txt : 1re colonne le périmètre, puis les groupes."""
    for encodage in ("utf-8-sig", "cp1252"):
        try:
            with open(chemin, encoding=encodage) as fichier:
                texte = fichier.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ErreurModele("Encodage du fichier non reconnu.")
    lignes = [l for l in texte.splitlines() if l.strip()]
    if not lignes:
        raise ErreurModele("Le fichier est vide.")
    separateur = max(("\t", ";", ","), key=lambda c: lignes[0].count(c))
    tableau = [[v.strip().strip('"') for v in l.split(separateur)]
               for l in lignes]
    largeur = len(tableau[0])
    return tableau[0][1:], [(ligne + [""] * largeur)[:largeur]
                            for ligne in tableau[1:]]


def modele_de_depart():
    """Démarre sur l'exemple complet s'il est présent, sinon sur un modèle vide."""
    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          FICHIER_EXEMPLE)
    if CHARGER_EXEMPLE and os.path.exists(chemin):
        return Modele.lire(chemin)
    return Modele()


def ppp_moteur_erreur(texte):
    """Erreur qui arrête le moteur, importé seulement au lancement."""
    import ppp_moteur
    return ppp_moteur.ErreurCalcul(texte)


def lancer_interface():
    import tkinter as tk
    from tkinter import filedialog, font, messagebox, ttk

    LARGEUR_BLOC, HAUTEUR_BLOC = 190, 74
    TEMPS_LIBELLE = "Temps (année)"

    class ChampFormule(tk.Text):
        """Zone de formule sur plusieurs lignes, liée à une StringVar."""

        def __init__(self, parent, variable, hauteur=4, largeur=30):
            super().__init__(parent, height=hauteur, width=largeur, wrap="word",
                             undo=True, font="TkFixedFont", relief="solid",
                             borderwidth=1, highlightthickness=0)
            self.variable = variable
            self.bind("<<Modified>>", self.lire)
            self.bind("<Return>", self.nouvelle_ligne)
            self.bind("<Tab>", self.champ_suivant)
            variable.trace_add("write", self.ecrire)
            self.ecrire()

        def lire(self, _evenement=None):
            if self.edit_modified():
                self.edit_modified(False)
                texte = self.get("1.0", "end-1c")
                if texte != self.variable.get():
                    self.variable.set(texte)

        def ecrire(self, *_arguments):
            texte = self.variable.get()
            if not self.winfo_exists() or texte == self.get("1.0", "end-1c"):
                return
            etat = self.cget("state")
            tk.Text.configure(self, state="normal")
            self.delete("1.0", "end")
            self.insert("1.0", texte)
            self.edit_modified(False)
            tk.Text.configure(self, state=etat)

        def activer(self, actif):
            tk.Text.configure(self, state="normal" if actif else "disabled",
                              background="white" if actif else "#E4E6E8")

        def nouvelle_ligne(self, _evenement):
            """Garde le retrait de la ligne, et l'augmente après une parenthèse."""
            ligne = self.get("insert linestart", "insert")
            retrait = ligne[:len(ligne) - len(ligne.lstrip())]
            if ligne.rstrip().endswith("("):
                retrait += "    "
            self.insert("insert", "\n" + retrait)
            return "break"

        def champ_suivant(self, _evenement):
            self.tk_focusNext().focus_set()
            return "break"

    class FenetreSimulation(tk.Toplevel):
        """Avancement dans le temps et écart à la dernière itération."""

        def __init__(self, parent):
            super().__init__(parent)
            self.title(T("Simulation"))
            self.geometry("680x520")
            self.transient(parent)
            self.arret = self.fini = False
            self.dernier, self.ecart = 0.0, None
            self.points, self.total = [], 1      # (rang, écart, seuil, date)
            cadre = ttk.Frame(self, padding=14)
            cadre.pack(fill="both", expand=True)
            self.texte = tk.StringVar(value=T("Calcul en cours"))
            ttk.Label(cadre, textvariable=self.texte,
                      font=("TkDefaultFont", 11)).pack(anchor="w")
            self.barre = ttk.Progressbar(cadre, maximum=100)
            self.barre.pack(fill="x", pady=8)
            self.texte_ecart = tk.StringVar(value=T(
                "Aucune boucle à faire converger pour l'instant."))
            ttk.Label(cadre, textvariable=self.texte_ecart, wraplength=640,
                      foreground="#51616f").pack(anchor="w")
            self.dessin = tk.Canvas(cadre, background="white", height=250,
                                    highlightthickness=0)
            self.dessin.pack(fill="both", expand=True, pady=(6, 0))
            self.verdict = tk.Label(cadre, font=("TkDefaultFont", 15, "bold"))
            self.verdict.pack(anchor="w", pady=(10, 0))
            self.detail = ttk.Label(cadre, wraplength=520, foreground="#51616f")
            self.detail.pack(anchor="w")
            self.bouton = ttk.Button(cadre, text=T("Arrêter"),
                                     command=self.demander_arret)
            self.bouton.pack(anchor="e", side="bottom")
            self.protocol("WM_DELETE_WINDOW", self.demander_arret)
            self.update_idletasks()
            try:
                self.wait_visibility()
                self.grab_set()
            except tk.TclError:
                pass

        def demander_arret(self):
            if self.fini:
                self.destroy()
            else:
                self.arret = True

        def __call__(self, genre, *donnees):
            """Reçoit l'avancement du moteur."""
            if genre == "iteration":
                # Écart de la dernière itération : le plus grand de la boucle.
                variable, ecart, seuil = max(
                    donnees[0], key=lambda v: v[1] / max(v[2], 1e-300))
                self.ecart = (variable, ecart, seuil, len(donnees[0]))
            else:
                rang, total, date = donnees
                if rang == 1:                 # une nouvelle simulation commence
                    self.points = []
                self.total = total
                self.barre["value"] = 100 * rang / total
                self.texte.set(T("Pas %d sur %d : %s" % (rang, total, date)))
                if self.ecart:
                    variable, ecart, seuil, _n = self.ecart
                    self.texte_ecart.set(T(
                        "Écart à la dernière itération : %.3g sur %s "
                        "(convergence %g)" % (ecart, variable, seuil)))
                    self.points.append((rang, ecart, seuil, date))
                    self.ecart = None
            maintenant = time.monotonic()
            if maintenant - self.dernier > 0.05:
                self.dernier = maintenant
                self.tracer()
                self.update()
            if self.arret:
                raise ppp_moteur_erreur("Simulation arrêtée.")

        def tracer(self):
            """Plus grand écart de la dernière itération, en fonction du temps."""
            d = self.dessin
            d.delete("all")
            largeur, hauteur = d.winfo_width(), d.winfo_height()
            if largeur < 100 or hauteur < 80:
                return
            if not self.points:
                d.create_text(largeur / 2, hauteur / 2, fill="#51616f",
                              text=T("Aucune boucle à faire converger."))
                return
            valeurs = [max(p[1], 1e-15) for p in self.points] + \
                [p[2] for p in self.points]
            bas = math.floor(math.log10(min(valeurs)))
            haut = math.ceil(math.log10(max(valeurs)))
            if haut == bas:
                haut += 1
            g, dr, h, b = 58, largeur - 14, 12, hauteur - 34

            def px(rang):
                return g + (dr - g) * (rang - 1) / max(self.total - 1, 1)

            def py(valeur):
                return b - (b - h) * (math.log10(max(valeur, 1e-15)) - bas) \
                    / (haut - bas)

            pas = max(1, (haut - bas) // 5)
            for e in range(bas, haut + 1, pas):
                d.create_line(g, py(10.0 ** e), dr, py(10.0 ** e),
                              fill="#E6E9ED")
                d.create_text(g - 6, py(10.0 ** e), anchor="e",
                              fill="#51616f", text="1e%d" % e)
            for seuil in sorted({p[2] for p in self.points})[:3]:
                d.create_line(g, py(seuil), dr, py(seuil), fill="#c0392b",
                              dash=(5, 3))
                y = py(seuil) - 8 if py(seuil) > h + 14 else py(seuil) + 9
                d.create_text(dr, y, anchor="e", fill="#51616f",
                              text=T("Convergence %g" % seuil))
            coords = [v for p in self.points for v in (px(p[0]), py(p[1]))]
            if len(coords) >= 4:
                d.create_line(*coords, fill="#2a78d6", width=2)
            for rang, ecart, seuil, _date in self.points:
                couleur = "#2a78d6" if ecart <= seuil else "#c0392b"
                d.create_oval(px(rang) - 3, py(ecart) - 3, px(rang) + 3,
                              py(ecart) + 3, fill=couleur, outline="")
            d.create_text(g, hauteur - 12, anchor="w", fill="#51616f",
                          text=self.points[0][3])
            d.create_text(dr, hauteur - 12, anchor="e", fill="#51616f",
                          text=self.points[-1][3])
            d.create_text((g + dr) / 2, hauteur - 12, fill="#51616f",
                          text=T("Écart maximal à la dernière itération, "
                                 "par pas de temps"))

        def conclure(self, reussite, messages):
            self.fini = True
            self.tracer()
            if reussite:
                self.barre["value"] = 100
            self.texte.set(T("Simulation terminée"))
            self.verdict.configure(
                text=T("Réussite" if reussite else "Échec"),
                foreground="#1a7f4b" if reussite else "#c0392b")
            self.detail.configure(text="\n".join(T(m) for m in messages[:4]))
            self.bouton.configure(text=T("Fermer"))
            self.update_idletasks()

    class TableauSaisie(ttk.Frame):
        """Tableau à deux colonnes modifiable directement dans les cellules."""

        def __init__(self, parent):
            super().__init__(parent)
            self.arbre = ttk.Treeview(self, columns=("v1", "v2"),
                                      show="headings", height=4,
                                      selectmode="browse")
            self.arbre.heading("v1", text="Variable 1")
            self.arbre.heading("v2", text="Variable 2")
            self.arbre.column("v1", width=150, anchor="e")
            self.arbre.column("v2", width=150, anchor="e")
            self.arbre.grid(row=0, column=0, columnspan=3, sticky="we")
            ttk.Button(self, text="+ Ligne", command=self.ajouter).grid(
                row=1, column=0, pady=3, sticky="w")
            ttk.Button(self, text="- Ligne", command=self.retirer).grid(
                row=1, column=1, pady=3)
            ttk.Button(self, text="Coller", command=self.coller).grid(
                row=1, column=2, pady=3, sticky="e")
            self.champ = None
            self.actif = True
            self.arbre.bind("<Button-1>", self.cliquer)

        def activer(self, actif):
            self.fermer()
            self.actif = actif
            for enfant in self.winfo_children():
                if isinstance(enfant, ttk.Button):
                    enfant.state(["!disabled"] if actif else ["disabled"])

        def charger(self, points):
            self.fermer()
            self.arbre.delete(*self.arbre.get_children())
            for valeur_1, valeur_2 in points:
                self.arbre.insert("", "end", values=("%g" % valeur_1,
                                                     "%.15g" % valeur_2))

        def lignes(self):
            self.fermer()
            return [tuple(self.arbre.item(i, "values"))
                    for i in self.arbre.get_children()]

        def ajouter(self):
            ligne = self.arbre.insert("", "end", values=("", ""))
            self.arbre.see(ligne)
            self.update_idletasks()
            self.editer(ligne, 0)

        def retirer(self):
            self.fermer()
            for ligne in self.arbre.selection():
                self.arbre.delete(ligne)

        def coller(self):
            """Colle deux colonnes copiées depuis Excel ou un fichier texte."""
            if not self.actif:
                return
            try:
                texte = self.clipboard_get()
            except tk.TclError:
                return
            for ligne in texte.splitlines():
                parties = re.split(r"[\t; ]+", ligne.strip())
                if len(parties) == 2:
                    self.arbre.insert("", "end", values=tuple(parties))

        def cliquer(self, evenement):
            if not self.actif:
                return
            ligne = self.arbre.identify_row(evenement.y)
            colonne = self.arbre.identify_column(evenement.x)
            if ligne and colonne:
                self.after_idle(self.editer, ligne, int(colonne[1:]) - 1)

        def editer(self, ligne, colonne):
            self.fermer()
            cadre = self.arbre.bbox(ligne, colonne)
            if not cadre:
                return
            x, y, largeur, hauteur = cadre
            self.champ = ttk.Entry(self.arbre, justify="right")
            self.champ.insert(0, self.arbre.item(ligne, "values")[colonne])
            self.champ.place(x=x, y=y, width=largeur, height=hauteur)
            self.champ.select_range(0, "end")
            self.champ.focus_set()
            self.champ.position = (ligne, colonne)
            self.champ.bind("<Return>", lambda _e: self.suivant())
            self.champ.bind("<Tab>", lambda _e: self.suivant())
            self.champ.bind("<FocusOut>", lambda _e: self.fermer())
            self.champ.bind("<Escape>", lambda _e: self.fermer(False))

        def fermer(self, garder=True):
            if self.champ is None:
                return
            champ, self.champ = self.champ, None
            ligne, colonne = champ.position
            if garder and self.arbre.exists(ligne):
                valeurs = list(self.arbre.item(ligne, "values"))
                valeurs[colonne] = champ.get().strip()
                self.arbre.item(ligne, values=valeurs)
            champ.destroy()

        def suivant(self):
            ligne, colonne = self.champ.position
            self.fermer()
            if colonne == 0:
                self.editer(ligne, 1)
            else:
                suivante = self.arbre.next(ligne)
                if suivante:
                    self.editer(suivante, 0)
                else:
                    self.ajouter()
            return "break"

    class Application(tk.Tk):
        def __init__(self, modele):
            super().__init__()
            self.modele = modele
            self.chemin = FICHIER_SIMULATION
            largeur = min(1560, self.winfo_screenwidth() - 40)
            hauteur = min(900, self.winfo_screenheight() - 80)
            self.geometry("%dx%d+10+10" % (largeur, hauteur))
            self.fiche = None
            self.resultat = None
            self.fiche_structure = None
            self.prise = None
            self.zones_flux = []
            self.selection_structure = None
            self.selection_flux = None
            self.selection_parametre = None
            self.selection_dimension = None
            self.construire()

        def construire(self):
            """Construit l'interface dans la langue active."""
            self.afficher_titre()
            barre = ttk.Frame(self, padding=6)
            barre.pack(fill="x")
            ttk.Button(barre, text="Ouvrir", command=self.ouvrir).pack(
                side="left")
            ttk.Button(barre, text="Enregistrer",
                       command=self.enregistrer).pack(side="left", padx=6)
            self.message = tk.StringVar(value=T("Prêt"))
            ttk.Label(barre, textvariable=self.message).pack(side="left",
                                                              padx=12)
            self.choix_langue = tk.StringVar(value=next(
                nom for nom, code in LANGUES.items()
                if code == LANGUE["code"]))
            liste = ttk.Combobox(barre, textvariable=self.choix_langue,
                                 values=list(LANGUES), state="readonly",
                                 width=10)
            liste.pack(side="right")
            liste.bind("<<ComboboxSelected>>", self.changer_langue)
            ttk.Label(barre, text="Langue").pack(side="right", padx=6)
            ttk.Label(self, text=T("Copyright © 2026 A. C. Diagne. Logiciel "
                                   "libre, licence GNU GPL v3."), foreground="#7A8784",
                      font=("TkDefaultFont", 8)).pack(side="bottom",
                                                      anchor="e", padx=8)
            corps = ttk.Frame(self)
            corps.pack(fill="both", expand=True, padx=6, pady=(0, 6))
            corps.columnconfigure(0, weight=3, uniform="partage")
            corps.columnconfigure(1, weight=2, uniform="partage")
            corps.rowconfigure(0, weight=1)
            self.zone_schema = ttk.Frame(corps)
            self.zone_schema.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self.zone_courbes = ttk.Frame(corps)
            self.zone_courbes.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self.zone_courbes.grid_remove()
            style = ttk.Style(self)
            style.configure("Vertical.TNotebook", tabposition="wn")
            style.configure("Vertical.TNotebook.Tab", padding=(8, 7),
                            width=15, anchor="w", font=("TkDefaultFont", 10))
            self.onglets = ttk.Notebook(corps, style="Vertical.TNotebook")
            self.onglets.grid(row=0, column=1, sticky="nsew")
            self.creer_schema()
            self.creer_structures()
            self.creer_perimetres()
            self.creer_flux()
            self.creer_parametres()
            self.creer_etat_initial()
            self.creer_simulation()
            self.creer_post()
            self.creer_resultats()
            self.creer_fonctions()
            self.onglets.bind("<<NotebookTabChanged>>",
                              lambda _e: self.changer_onglet())
            self.traduire_widgets(self)
            for onglet in self.onglets.tabs():
                self.onglets.tab(onglet, text=T(self.onglets.tab(onglet,
                                                                 "text")))
            self.rafraichir()

        def afficher_titre(self):
            self.title("%s - %s" % (
                T("HapNatt - Structures, flux et paramètres"),
                os.path.basename(self.chemin)))

        def traduire_widgets(self, parent):
            for enfant in parent.winfo_children():
                if isinstance(enfant, ttk.Treeview):
                    for colonne in enfant["columns"]:
                        enfant.heading(colonne, text=T(
                            enfant.heading(colonne, "text")))
                elif isinstance(enfant, (ttk.Label, ttk.Button, ttk.Radiobutton,
                                         ttk.Checkbutton, ttk.LabelFrame)):
                    if not (enfant.cget("textvariable")
                            if "textvariable" in enfant.keys() else ""):
                        enfant.configure(text=T(enfant.cget("text")))
                self.traduire_widgets(enfant)

        def changer_langue(self, _evenement=None):
            self.lire_cadre()
            onglet = self.onglets.index("current")
            definir_langue(LANGUES[self.choix_langue.get()])
            if self.fiche is not None and self.fiche.winfo_exists():
                self.fiche.destroy()
            self.fiche = None
            self.selection_structure = None
            self.selection_flux = None
            self.selection_parametre = None
            self.selection_dimension = None
            for enfant in self.winfo_children():
                enfant.destroy()
            self.construire()
            self.onglets.select(onglet)

        def dire(self, texte):
            self.message.set(T(texte))

        def changer_onglet(self):
            self.lire_cadre()
            self.rafraichir()
            if self.onglets.index("current") == ONGLET_RESULTATS:
                self.zone_schema.grid_remove()
                self.zone_courbes.grid()
                self.tracer()
            else:
                self.zone_courbes.grid_remove()
                self.zone_schema.grid()

        def signaler(self, erreur):
            messagebox.showerror(T("HapNatt"), T(str(erreur)), parent=self)

        @staticmethod
        def creer_tableau(parent, colonnes, largeurs):
            cadre = ttk.Frame(parent)
            tableau = ttk.Treeview(cadre, columns=colonnes, show="headings",
                                   selectmode="browse")
            for colonne, largeur in zip(colonnes, largeurs):
                tableau.heading(colonne, text=colonne)
                tableau.column(colonne, width=largeur, anchor="w")
            defilement = ttk.Scrollbar(cadre, orient="vertical",
                                       command=tableau.yview)
            tableau.configure(yscrollcommand=defilement.set)
            tableau.pack(side="left", fill="both", expand=True)
            defilement.pack(side="right", fill="y")
            return cadre, tableau

        # ---------------- Schéma ----------------
        def creer_schema(self):
            page = self.zone_schema
            haut = ttk.Frame(page)
            haut.pack(fill="x", pady=(0, 6))
            ttk.Button(haut, text="Ajouter une structure",
                       command=lambda: self.onglets.select(0)).pack(side="left")
            ttk.Button(haut, text="Ajouter un flux",
                       command=lambda: self.onglets.select(2)).pack(
                side="left", padx=6)
            ttk.Button(haut, text="Optimiser le schéma",
                       command=self.optimiser_schema).pack(side="left")
            ttk.Label(page, text="Clic : ouvrir un bloc ou un flux.  "
                      "Glisser : déplacer un bloc.").pack(anchor="w",
                                                          pady=(0, 4))
            self.canevas = tk.Canvas(page, background="#FBFCFD",
                                     highlightthickness=1,
                                     highlightbackground="#D5DBE1")
            self.canevas.pack(fill="both", expand=True)
            self.canevas.bind("<ButtonPress-1>", self.saisir)
            self.canevas.bind("<B1-Motion>", self.glisser)
            self.canevas.bind("<ButtonRelease-1>", self.relacher)
            self.canevas.bind("<Configure>",
                              lambda _e: self.dessiner_schema())

        def optimiser_schema(self):
            m = self.modele
            self.config(cursor="watch")
            self.update_idletasks()
            positions = optimiser_positions(
                m.structures,
                [(f["payeur"], f["beneficiaire"]) for f in m.flux.values()],
                self.canevas.winfo_width(), self.canevas.winfo_height(),
                LARGEUR_BLOC, HAUTEUR_BLOC)
            for identifiant, (x, y) in positions.items():
                m.structures[identifiant]["x"] = x
                m.structures[identifiant]["y"] = y
            self.config(cursor="")
            self.dessiner_schema()
            self.dire("Schéma réorganisé.")

        def placer_blocs(self):
            largeur = self.canevas.winfo_width()
            colonnes = max(2, min(3, (largeur - 40) // 300))
            rang = 0
            for s in self.modele.structures.values():
                if s["x"] is None or s["y"] is None:
                    s["x"] = 140 + (rang % colonnes) * (largeur - 280) \
                        // max(colonnes - 1, 1)
                    s["y"] = 90 + (rang // colonnes) * 210
                rang += 1

        @staticmethod
        def bord_bloc(centre, cible):
            """Point du bord d'un bloc en direction d'une cible."""
            cx, cy = centre
            dx, dy = cible[0] - cx, cible[1] - cy
            if dx == 0 and dy == 0:
                return cx, cy
            demi_l, demi_h = LARGEUR_BLOC / 2 + 4, HAUTEUR_BLOC / 2 + 4
            rapport = min(demi_l / abs(dx) if dx else 1e9,
                          demi_h / abs(dy) if dy else 1e9)
            return cx + dx * rapport, cy + dy * rapport

        def dessiner_schema(self):
            c, m = self.canevas, self.modele
            if c.winfo_width() < 200:     # fenêtre pas encore affichée
                return
            c.delete("all")
            self.zones_flux = []
            self.placer_blocs()
            paires = {}
            for i, f in m.flux.items():
                paire = tuple(sorted((f["payeur"], f["beneficiaire"])))
                paires.setdefault(paire, []).append(i)
            for paire, flux in paires.items():
                a, b = m.structures[paire[0]], m.structures[paire[1]]
                ax, ay, bx, by = a["x"], a["y"], b["x"], b["y"]
                longueur = max(((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, 1)
                nx, ny = -(by - ay) / longueur, (bx - ax) / longueur
                for rang, i in enumerate(flux):
                    f = m.flux[i]
                    espace = 44 + 96 * abs(nx)
                    ecart = (rang - (len(flux) - 1) / 2) * espace
                    point = ((ax + bx) / 2 + nx * ecart,
                             (ay + by) / 2 + ny * ecart)
                    source = m.structures[f["payeur"]]
                    cible = m.structures[f["beneficiaire"]]
                    depart = self.bord_bloc((source["x"], source["y"]), point)
                    arrivee = self.bord_bloc((cible["x"], cible["y"]), point)
                    physique = f["nature"] == "Physique"
                    c.create_line(*depart, *point, *arrivee, smooth=True,
                                  width=2, arrow="last", arrowshape=(11, 13, 5),
                                  fill="#2e7d5b" if physique else "#5b6b7b",
                                  dash=(7, 4) if physique else ())
                    texte = c.create_text(*point, text=f["nom"],
                                          fill="#1d5c43" if physique
                                          else "#1f3a57",
                                          font=("TkDefaultFont", 9, "bold"))
                    x1, y1, x2, y2 = c.bbox(texte)
                    fond = c.create_rectangle(x1 - 4, y1 - 2, x2 + 4, y2 + 2,
                                              fill="#e6f4ec" if physique
                                              else "#eef3f8",
                                              outline="#b5d5c3" if physique
                                              else "#c7d3df")
                    c.tag_raise(texte, fond)
                    self.zones_flux.append(((x1 - 4, y1 - 2, x2 + 4, y2 + 2),
                                            i))
            hauteur = c.winfo_height()
            c.create_line(16, hauteur - 18, 56, hauteur - 18, width=2,
                          arrow="last", fill="#5b6b7b")
            c.create_text(62, hauteur - 18, text=T("Flux financier"), anchor="w",
                          fill="#51616f")
            c.create_line(170, hauteur - 18, 210, hauteur - 18, width=2,
                          arrow="last", fill="#2e7d5b", dash=(7, 4))
            c.create_text(216, hauteur - 18, text=T("Flux physique ou service"),
                          anchor="w", fill="#51616f")
            for s in m.structures.values():
                x, y = s["x"], s["y"]
                fond, accent = COULEURS_TYPES.get(s["type"], COULEUR_AUTRE_TYPE)
                gauche = x - LARGEUR_BLOC / 2
                haut = y - HAUTEUR_BLOC / 2
                c.create_rectangle(gauche, haut, x + LARGEUR_BLOC / 2,
                                   y + HAUTEUR_BLOC / 2, fill=fond,
                                   outline=accent, width=1)
                c.create_rectangle(gauche, haut, gauche + 7,
                                   y + HAUTEUR_BLOC / 2, fill=accent,
                                   outline=accent)
                c.create_text(x, y - 12, text=s["nom"], width=LARGEUR_BLOC - 12,
                              justify="center", fill="#14283c",
                              font=("TkDefaultFont", 10, "bold"))
                c.create_text(x, y + 20, text=T(s["type"]), fill=accent,
                              font=("TkDefaultFont", 9))

        def bloc_sous(self, x, y):
            for i, s in reversed(list(self.modele.structures.items())):
                if s["x"] is not None \
                        and abs(x - s["x"]) <= LARGEUR_BLOC / 2 \
                        and abs(y - s["y"]) <= HAUTEUR_BLOC / 2:
                    return i
            return None

        def saisir(self, evenement):
            bloc = self.bloc_sous(evenement.x, evenement.y)
            if bloc:
                s = self.modele.structures[bloc]
                self.prise = {"bloc": bloc, "dx": s["x"] - evenement.x,
                              "dy": s["y"] - evenement.y, "bouge": False,
                              "x": evenement.x, "y": evenement.y}
                return
            self.prise = None
            for (x1, y1, x2, y2), flux in self.zones_flux:
                if x1 <= evenement.x <= x2 and y1 <= evenement.y <= y2:
                    self.onglets.select(2)
                    self.update_idletasks()
                    self.t_flux.selection_set(flux)
                    self.t_flux.see(flux)
                    return

        def glisser(self, evenement):
            if not self.prise:
                return
            if abs(evenement.x - self.prise["x"]) \
                    + abs(evenement.y - self.prise["y"]) > 4:
                self.prise["bouge"] = True
            if self.prise["bouge"]:
                s = self.modele.structures[self.prise["bloc"]]
                s["x"] = max(LARGEUR_BLOC // 2, evenement.x + self.prise["dx"])
                s["y"] = max(HAUTEUR_BLOC // 2, evenement.y + self.prise["dy"])
                self.dessiner_schema()

        def relacher(self, _evenement):
            if self.prise and not self.prise["bouge"]:
                self.ouvrir_fiche(self.prise["bloc"])
            self.prise = None

        # ---------------- Fiche d'une structure ----------------
        def ouvrir_fiche(self, identifiant):
            if self.fiche is not None and self.fiche.winfo_exists():
                self.fiche.destroy()
            s = self.modele.structures[identifiant]
            self.fiche_structure = identifiant
            f = tk.Toplevel(self)
            self.fiche = f
            f.title(s["nom"])
            f.geometry("940x760")
            f.transient(self)
            ttk.Label(f, text="%s  (%s)" % (s["nom"], T(s["type"])),
                      font=("TkDefaultFont", 12, "bold")).pack(
                anchor="w", padx=12, pady=(10, 4))
            pages = ttk.Notebook(f)
            pages.pack(fill="both", expand=True, padx=8, pady=4)
            page_missions = ttk.Frame(pages, padding=4)
            page_flux = ttk.Frame(pages, padding=4)
            page_charges = ttk.Frame(pages, padding=4)
            page_comptes = ttk.Frame(pages, padding=4)
            page_capacite = ttk.Frame(pages, padding=8)
            pages.add(page_missions, text=T("Missions"))
            pages.add(page_flux, text=T("Recettes et flux physiques"))
            pages.add(page_charges, text=T("Charges"))
            pages.add(page_comptes, text=T("Comptes"))
            pages.add(page_capacite, text=T("Capacité d'investissement"))
            page_capacite.columnconfigure(1, weight=1)
            reglages = self.modele.structures[self.fiche_structure].get(
                "capacite", {})
            self.champs_capacite = {}
            for rang, (cle, libelle) in enumerate((
                    ("tresorerie_minimale", "Trésorerie minimale à garder"),
                    ("couverture", "Couverture minimale exigée"),
                    ("taux", "Taux d'emprunt (0.08 pour 8 %)"),
                    ("duree", "Durée d'emprunt (années)"),
                    ("besoin", "Besoin d'investissement"))):
                ttk.Label(page_capacite, text=libelle).grid(
                    row=rang, column=0, sticky="w", pady=3)
                self.champs_capacite[cle] = tk.StringVar(
                    value=reglages.get(cle, ""))
                ttk.Entry(page_capacite,
                          textvariable=self.champs_capacite[cle]).grid(
                    row=rang, column=1, padx=8, pady=3, sticky="we")
            ttk.Button(page_capacite, text="Appliquer",
                       command=self.appliquer_capacite).grid(
                row=5, column=0, columnspan=2, pady=8)
            ttk.Label(page_capacite, wraplength=800, foreground="#51616f",
                      text="Chaque champ accepte une valeur ou une formule. "
                      "Laissez tout vide pour ne pas calculer cette capacité."
                      ).grid(row=6, column=0, columnspan=2, sticky="w")
            bloc = ttk.LabelFrame(page_missions,
                                  text="Missions (une par ligne)", padding=6)
            bloc.pack(fill="x", padx=4, pady=4)
            self.txt_missions = tk.Text(bloc, height=4)
            self.txt_missions.pack(fill="x")
            self.txt_missions.insert("1.0", "\n".join(s["missions"]))
            ttk.Button(bloc, text="Enregistrer les missions",
                       command=self.enregistrer_missions).pack(anchor="e",
                                                               pady=(4, 0))
            bloc = ttk.LabelFrame(page_flux, text="Recettes : flux reçus",
                                  padding=6)
            bloc.pack(fill="both", expand=True, padx=4, pady=4)
            cadre, self.t_recettes = self.creer_tableau(
                bloc, ("Variable", "Payeur", "Formule ou valeur"),
                (310, 210, 360))
            self.t_recettes.configure(height=3)
            cadre.pack(fill="both", expand=True)
            bloc = ttk.LabelFrame(page_flux, text="Flux physiques et services",
                                  padding=6)
            bloc.pack(fill="both", expand=True, padx=4, pady=4)
            cadre, self.t_physiques = self.creer_tableau(
                bloc, ("Variable", "Sens", "Effet", "Autre structure",
                       "Formule ou valeur"), (280, 65, 75, 190, 270))
            self.t_physiques.configure(height=3)
            cadre.pack(fill="both", expand=True)
            bloc = ttk.LabelFrame(
                page_charges, text="Charges affectant son modèle financier",
                padding=6)
            bloc.pack(fill="both", expand=True, padx=4, pady=4)
            cadre, self.t_charges = self.creer_tableau(
                bloc, ("Variable", "Nature", "Bénéficiaire",
                       "Formule ou valeur"), (290, 70, 210, 310))
            self.t_charges.configure(height=5)
            cadre.pack(fill="both", expand=True)
            ligne = ttk.Frame(bloc)
            ligne.pack(fill="x", pady=(6, 0))
            self.c_nom, self.c_expr = tk.StringVar(), tk.StringVar()
            self.c_compte = tk.StringVar(value=T("Résultat"))
            ttk.Label(ligne, text="Charge").pack(side="left")
            ttk.Entry(ligne, textvariable=self.c_nom, width=20).pack(
                side="left", padx=4)
            ttk.Label(ligne, text="Formule ou valeur").pack(side="left")
            ChampFormule(ligne, self.c_expr, 3, 34).pack(
                side="left", padx=4)
            ttk.Combobox(ligne, textvariable=self.c_compte, state="readonly",
                         width=13, values=[T(v) for v in
                                           ("Résultat", "Investissement")]
                         ).pack(side="left", padx=2)
            ttk.Button(ligne, text="Ajouter", command=self.ajouter_charge
                       ).pack(side="left", padx=2)
            ttk.Button(ligne, text="Supprimer", command=self.supprimer_charge
                       ).pack(side="left", padx=2)
            bloc = ttk.LabelFrame(page_comptes, text="Postes du compte",
                                  padding=6)
            bloc.pack(fill="both", expand=True, padx=4, pady=4)
            cadre, self.t_postes = self.creer_tableau(
                bloc, ("Catégorie", "Variable", "Formule ou valeur"),
                (170, 290, 390))
            cadre.pack(fill="both", expand=True)
            ligne = ttk.Frame(bloc)
            ligne.pack(fill="x", pady=(6, 0))
            self.k_categorie = tk.StringVar(value=T(CATEGORIES_POSTES[0]))
            self.k_nom, self.k_expr = tk.StringVar(), tk.StringVar()
            ttk.Combobox(ligne, textvariable=self.k_categorie,
                         state="readonly", width=18,
                         values=[T(v) for v in CATEGORIES_POSTES]).pack(
                side="left", padx=2)
            ttk.Label(ligne, text="Nom").pack(side="left", padx=(6, 0))
            ttk.Entry(ligne, textvariable=self.k_nom, width=14).pack(
                side="left", padx=4)
            ttk.Label(ligne, text="Formule ou valeur").pack(side="left")
            ChampFormule(ligne, self.k_expr, 3, 20).pack(
                side="left", padx=4)
            ttk.Button(ligne, text="Ajouter", command=self.ajouter_poste
                       ).pack(side="left", padx=2)
            ttk.Button(ligne, text="Supprimer", command=self.supprimer_poste
                       ).pack(side="left", padx=2)
            ttk.Label(bloc, wraplength=840, foreground="#51616f",
                      text="Le moteur calcule la trésorerie, le résultat et "
                      "les fonds propres. Les postes de type Garantie restent "
                      "hors bilan.").pack(anchor="w", pady=(6, 0))
            self.traduire_widgets(f)
            self.remplir_fiche()

        def remplir_fiche(self):
            m, i = self.modele, self.fiche_structure
            if self.fiche is None or not self.fiche.winfo_exists() \
                    or i not in m.structures:
                return
            self.t_recettes.delete(*self.t_recettes.get_children())
            self.t_charges.delete(*self.t_charges.get_children())
            self.t_physiques.delete(*self.t_physiques.get_children())
            self.t_postes.delete(*self.t_postes.get_children())
            for identifiant, c in m.postes.items():
                if c["structure"] == i:
                    self.t_postes.insert("", "end", iid=identifiant, values=(
                        T(c["categorie"]), identifiant,
                        self.definition(identifiant)))
            noms = m.structures
            for identifiant, f in m.flux.items():
                definition = self.definition(identifiant)
                if f["nature"] == "Physique":
                    if i in (f["payeur"], f["beneficiaire"]):
                        sortant = f["payeur"] == i
                        autre = f["beneficiaire"] if sortant else f["payeur"]
                        self.t_physiques.insert("", "end", values=(
                            identifiant, T("Fournit" if sortant else "Reçoit"),
                            T(f["effet"]), noms[autre]["nom"], definition))
                    continue
                if f["beneficiaire"] == i:
                    self.t_recettes.insert("", "end", values=(
                        identifiant, noms[f["payeur"]]["nom"], definition))
                if f["payeur"] == i:
                    self.t_charges.insert("", "end", values=(
                        identifiant, T("Flux"), noms[f["beneficiaire"]]["nom"],
                        definition))
            for identifiant, c in m.charges.items():
                if c["structure"] == i:
                    self.t_charges.insert("", "end", iid=identifiant, values=(
                        identifiant, T("Interne"), "-",
                        self.definition(identifiant)))

        def appliquer_capacite(self):
            try:
                self.modele.definir_capacite(
                    self.fiche_structure,
                    {k: v.get() for k, v in self.champs_capacite.items()})
                self.rafraichir()
                self.dire("Capacité d'investissement mise à jour.")
            except ErreurModele as erreur:
                messagebox.showerror(T("HapNatt"), T(str(erreur)),
                                     parent=self.fiche)

        def ajouter_poste(self):
            try:
                self.modele.ajouter_poste(self.k_nom.get(),
                                          self.fiche_structure,
                                          origine(self.k_categorie.get()),
                                          self.k_expr.get())
                self.k_nom.set("")
                self.k_expr.set("")
                self.rafraichir()
            except ErreurModele as erreur:
                messagebox.showerror(T("HapNatt"), T(str(erreur)),
                                     parent=self.fiche)

        def supprimer_poste(self):
            selection = self.t_postes.selection()
            if selection:
                self.modele.supprimer_poste(selection[0])
                self.rafraichir()

        def definition(self, identifiant):
            p = self.modele.parametres[identifiant]
            return " ".join(p["expression"].split()) \
                if p["mode"] == "formule" else T("Table")

        def enregistrer_missions(self):
            self.modele.definir_missions(self.fiche_structure,
                                         self.txt_missions.get("1.0", "end"))
            self.dire("Missions enregistrées.")

        def ajouter_charge(self):
            try:
                self.modele.ajouter_charge(self.c_nom.get(),
                                           self.fiche_structure,
                                           self.c_expr.get(),
                                           origine(self.c_compte.get()))
                self.c_nom.set("")
                self.c_expr.set("")
                self.rafraichir()
            except ErreurModele as erreur:
                messagebox.showerror(T("HapNatt"), T(str(erreur)),
                                     parent=self.fiche)

        def supprimer_charge(self):
            selection = [i for i in self.t_charges.selection()
                         if i in self.modele.charges]
            if selection:
                self.modele.supprimer_charge(selection[0])
                self.rafraichir()

        # ---------------- Structures ----------------
        def creer_structures(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="1. Structures")
            form = ttk.Frame(page)
            form.pack(fill="x", pady=(0, 8))
            form.columnconfigure(1, weight=1)
            self.s_nom, self.s_type = tk.StringVar(), tk.StringVar()
            ttk.Label(form, text="Nom").grid(row=0, column=0, sticky="w")
            ttk.Entry(form, textvariable=self.s_nom).grid(
                row=0, column=1, padx=6, pady=3, sticky="we")
            ttk.Label(form, text="Type").grid(row=1, column=0, sticky="w")
            ttk.Combobox(form, textvariable=self.s_type,
                         values=[T(v) for v in TYPES_STRUCTURE]).grid(
                row=1, column=1, padx=6, pady=3, sticky="we")
            boutons = ttk.Frame(page)
            boutons.pack(fill="x", pady=(0, 8))
            ttk.Button(boutons, text="Ajouter", command=self.ajouter_structure
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Modifier", command=self.modifier_structure
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Supprimer",
                       command=self.supprimer_structure).pack(side="left",
                                                              padx=2)
            cadre, self.t_structures = self.creer_tableau(
                page, ("Nom", "Type"), (175, 150))
            cadre.pack(fill="both", expand=True)
            self.t_structures.bind("<<TreeviewSelect>>",
                                   self.choisir_structure)

        def ajouter_structure(self):
            try:
                self.modele.ajouter_structure(self.s_nom.get(),
                                              origine(self.s_type.get()))
                self.s_nom.set("")
                self.rafraichir()
            except ErreurModele as erreur:
                self.signaler(erreur)

        def modifier_structure(self):
            if not self.selection_structure:
                return
            try:
                self.modele.ajouter_structure(self.s_nom.get(),
                                              origine(self.s_type.get()),
                                              self.selection_structure)
                self.rafraichir()
            except ErreurModele as erreur:
                self.signaler(erreur)

        def supprimer_structure(self):
            identifiant = self.selection_structure
            if not identifiant:
                messagebox.showinfo(T("HapNatt"), T(
                    "Sélectionnez d'abord une structure dans la liste."))
                return
            retires, a_revoir = self.modele.consequences_suppression(
                identifiant)

            def liste(noms):
                texte = "\n".join("  " + n for n in noms[:15])
                if len(noms) > 15:
                    texte += "\n  ... (%d)" % len(noms)
                return texte

            message = T("Supprimer cette structure ?") + "\n" + \
                self.modele.structures[identifiant]["nom"]
            if retires:
                message += "\n\n" + T("Seront aussi supprimés :") + "\n" + \
                    liste(retires)
            if a_revoir:
                message += "\n\n" + T("Formules à revoir ensuite :") + "\n" + \
                    liste(a_revoir)
            if not messagebox.askyesno(T("HapNatt"), message):
                return
            self.modele.supprimer_structure(identifiant)
            self.selection_structure = None
            self.s_nom.set("")
            self.rafraichir()

        def choisir_structure(self, _event):
            selection = self.t_structures.selection()
            if selection:
                self.selection_structure = selection[0]
                s = self.modele.structures[selection[0]]
                self.s_nom.set(s["nom"])
                self.s_type.set(T(s["type"]))

        # ---------------- Flux ----------------
        def creer_flux(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="3. Flux")
            form = ttk.Frame(page)
            form.pack(fill="x", pady=(0, 6))
            form.columnconfigure(1, weight=1)
            self.f_nom = tk.StringVar()
            self.f_payeur = tk.StringVar()
            self.f_benef = tk.StringVar()
            self.f_expr = tk.StringVar()
            self.f_nature = tk.StringVar(value=T("Financier"))
            self.f_effet = tk.StringVar(value=T("Capacité"))
            self.f_compte = tk.StringVar(value=T("Résultat"))
            ttk.Label(form, text="Flux").grid(row=0, column=0, sticky="w")
            ttk.Entry(form, textvariable=self.f_nom).grid(
                row=0, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="De (payeur)").grid(row=1, column=0,
                                                     sticky="w")
            self.c_payeur = ttk.Combobox(form, textvariable=self.f_payeur,
                                         state="readonly")
            self.c_payeur.grid(row=1, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="Vers (bénéficiaire)").grid(row=2, column=0,
                                                             sticky="w")
            self.c_benef = ttk.Combobox(form, textvariable=self.f_benef,
                                        state="readonly")
            self.c_benef.grid(row=2, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="Formule ou valeur").grid(
                row=3, column=0, columnspan=2, sticky="w")
            ChampFormule(form, self.f_expr, 7).grid(
                row=4, column=0, columnspan=2, padx=(0, 6), pady=2, sticky="we")
            ttk.Label(form, text="Nature").grid(row=5, column=0, sticky="w")
            ttk.Combobox(form, textvariable=self.f_nature, state="readonly",
                         values=[T(v) for v in NATURES_FLUX]).grid(
                row=5, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="Effet (si physique)").grid(row=6, column=0,
                                                             sticky="w")
            ttk.Combobox(form, textvariable=self.f_effet, state="readonly",
                         values=[T(v) for v in EFFETS_FLUX]).grid(
                row=6, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="Compte").grid(row=7, column=0, sticky="w")
            ttk.Combobox(form, textvariable=self.f_compte, state="readonly",
                         values=[T(v) for v in COMPTES_FLUX]).grid(
                row=7, column=1, padx=6, pady=2, sticky="we")
            boutons = ttk.Frame(page)
            boutons.pack(fill="x", pady=(0, 4))
            ttk.Button(boutons, text="Ajouter", command=self.ajouter_flux
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Modifier", command=self.modifier_flux
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Supprimer", command=self.supprimer_flux
                       ).pack(side="left", padx=2)
            ttk.Button(page, text="Paiement : impayés et moratoire",
                       command=self.ouvrir_paiement).pack(anchor="w", padx=2,
                                                          pady=(0, 4))
            ttk.Label(page, wraplength=330, foreground="#51616f",
                      text="Écrivez chaque variable avec sa structure : "
                      "volume[exploitant]. Valeur commune : taux[projet]. "
                      "Condition : si(a > b, x, y)."
                      ).pack(anchor="w", pady=(0, 6))
            cadre, self.t_flux = self.creer_tableau(
                page, ("Variable", "Nature", "Formule ou valeur"),
                (170, 60, 105))
            cadre.pack(fill="both", expand=True)
            self.t_flux.bind("<<TreeviewSelect>>", self.choisir_flux)

        def id_structure(self, nom):
            for identifiant, s in self.modele.structures.items():
                if s["nom"] == nom:
                    return identifiant
            return ""

        def ajouter_flux(self):
            self._enregistrer_flux(None)

        def modifier_flux(self):
            if self.selection_flux:
                self._enregistrer_flux(self.selection_flux)

        def _enregistrer_flux(self, ancien_id):
            try:
                self.selection_flux = self.modele.ajouter_flux(
                    self.f_nom.get(), self.id_structure(self.f_payeur.get()),
                    self.id_structure(self.f_benef.get()), self.f_expr.get(),
                    ancien_id, origine(self.f_nature.get()),
                    origine(self.f_effet.get()), origine(self.f_compte.get()))
                self.rafraichir()
                self.dire("Flux enregistré. Paramètres mis à jour.")
            except ErreurModele as erreur:
                self.signaler(erreur)

        def supprimer_flux(self):
            if self.selection_flux:
                self.modele.supprimer_flux(self.selection_flux)
                self.selection_flux = None
                self.rafraichir()

        def choisir_flux(self, _event):
            selection = self.t_flux.selection()
            if selection:
                identifiant = selection[0]
                self.selection_flux = identifiant
                f = self.modele.flux[identifiant]
                s = self.modele.structures
                self.f_nom.set(f["nom"])
                self.f_nature.set(T(f["nature"]))
                self.f_effet.set(T(f["effet"]))
                self.f_compte.set(T(f["compte"]))
                self.f_payeur.set(s[f["payeur"]]["nom"])
                self.f_benef.set(s[f["beneficiaire"]]["nom"])
                self.f_expr.set(self.modele.parametres[identifiant]
                                ["expression"])

        def ouvrir_paiement(self):
            identifiant = self.selection_flux
            if not identifiant or identifiant not in self.modele.flux:
                self.dire("Sélectionnez un flux dans la liste.")
                return
            flux = self.modele.flux[identifiant]
            if flux["nature"] != "Financier":
                self.signaler("Un flux physique n'a pas de paiement.")
                return
            fenetre = tk.Toplevel(self)
            fenetre.title(T("Paiement") + " : " + identifiant)
            fenetre.transient(self)
            cadre = ttk.Frame(fenetre, padding=12)
            cadre.pack(fill="both", expand=True)
            cadre.columnconfigure(1, weight=1)
            reglages = dict(PAIEMENT_DEFAUT)
            reglages.update(flux.get("paiement", {}))
            champs = {}
            for rang, (cle, libelle) in enumerate((
                    ("recouvrement", "Taux de recouvrement"),
                    ("rattrapage", "Taux de rattrapage des impayés"),
                    ("abandon", "Taux d'abandon des impayés"),
                    ("moratoire_debut", "Début du moratoire (JJ/MM/AAAA)"),
                    ("moratoire_fin", "Fin du moratoire (JJ/MM/AAAA)"),
                    ("part_suspendue", "Part suspendue"),
                    ("reprise_pas", "Reprise (nombre de pas)"),
                    ("taux_moratoire", "Intérêt moratoire (par an)"))):
                ttk.Label(cadre, text=T(libelle)).grid(row=rang, column=0,
                                                       sticky="w", pady=2)
                champs[cle] = tk.StringVar(value=reglages[cle])
                ttk.Entry(cadre, textvariable=champs[cle], width=32).grid(
                    row=rang, column=1, padx=(8, 0), pady=2, sticky="we")
            ttk.Label(cadre, wraplength=430, foreground="#51616f", text=T(
                "Un taux s'écrit comme une formule : 0.9 pour 90 %, ou une "
                "variable comme taux[usagers].")).grid(
                row=8, column=0, columnspan=2, sticky="w", pady=6)

            def appliquer():
                try:
                    self.modele.definir_paiement(
                        identifiant,
                        {k: v.get() for k, v in champs.items()})
                except ErreurModele as erreur:
                    messagebox.showerror(T("HapNatt"), T(str(erreur)),
                                         parent=fenetre)
                    return
                self.rafraichir()
                self.dire("Paiement mis à jour.")
                fenetre.destroy()

            ttk.Button(cadre, text=T("Appliquer"), command=appliquer).grid(
                row=9, column=0, columnspan=2, pady=(6, 0))
            self.fenetre_paiement = (fenetre, champs, appliquer)

        # ---------------- Paramètres ----------------
        def creer_parametres(self):
            page = ttk.Frame(self.onglets, padding=8)
            self.onglets.add(page, text="4. Paramètres")
            cadre, self.t_param = self.creer_tableau(
                page, ("Variable", "Origine", "Unité", "État"),
                (165, 55, 50, 65))
            self.t_param.configure(height=4)
            cadre.pack(fill="both", expand=True)
            self.t_param.bind("<<TreeviewSelect>>", self.choisir_parametre)
            droite = ttk.LabelFrame(page, text="Fiche du paramètre", padding=8)
            droite.pack(side="bottom", fill="x", pady=(8, 0), before=cadre)
            droite.columnconfigure(1, weight=1)
            self.p_nom = tk.StringVar(value=T("Sélectionnez un paramètre"))
            ttk.Label(droite, textvariable=self.p_nom,
                      font=("TkDefaultFont", 10, "bold")).grid(
                row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
            self.p_portee = tk.StringVar()
            self.c_portee = ttk.Combobox(droite, textvariable=self.p_portee,
                                         state="disabled")
            self.c_portee.grid(row=1, column=1, sticky="e")
            self.c_portee.bind("<<ComboboxSelected>>",
                               lambda _e: self.charger_portee())
            self.p_mode = tk.StringVar(value="formule")
            ttk.Radiobutton(droite, text="Formule", value="formule",
                            variable=self.p_mode,
                            command=self.afficher_mode).grid(
                row=1, column=0, sticky="w")
            ttk.Radiobutton(droite, text="Table", value="table",
                            variable=self.p_mode,
                            command=self.afficher_mode).grid(
                row=1, column=0, padx=(88, 0), sticky="w")
            self.p_expr = tk.StringVar()
            self.e_expr = ChampFormule(droite, self.p_expr, 14)
            self.e_expr.grid(row=2, column=0, columnspan=2, pady=3, sticky="we")
            self.p_var1 = tk.StringVar(value=T(TEMPS_LIBELLE))
            etiquette_1 = ttk.Label(droite, text="Variable 1")
            etiquette_1.grid(row=3, column=0, sticky="w")
            self.c_var1 = ttk.Combobox(droite, textvariable=self.p_var1,
                                       state="readonly")
            self.c_var1.grid(row=3, column=1, pady=2, sticky="we")
            self.table = TableauSaisie(droite)
            self.table.grid(row=4, column=0, columnspan=2, pady=3, sticky="we")
            self.p_lecture = tk.StringVar(value=T("Par paliers"))
            etiquette_2 = ttk.Label(droite, text="Entre deux lignes")
            etiquette_2.grid(row=5, column=0, sticky="w")
            self.c_lecture = ttk.Combobox(
                droite, textvariable=self.p_lecture, state="readonly",
                values=[T(v) for v in LECTURES_TABLE])
            self.c_lecture.grid(row=5, column=1, pady=2, sticky="we")
            self.zone_table = (etiquette_1, self.c_var1, self.table,
                               etiquette_2, self.c_lecture)
            self.p_unite = tk.StringVar()
            self.p_convergence = tk.StringVar(value=CONVERGENCE_DEFAUT)
            self.p_suivi = tk.BooleanVar(value=False)
            ttk.Label(droite, text="Unité").grid(row=6, column=0, sticky="w")
            self.c_unite = ttk.Combobox(droite, textvariable=self.p_unite,
                                        values=[T(v) for v in UNITES],
                                        state="readonly")
            self.c_unite.grid(row=6, column=1, pady=2, sticky="we")
            for ligne, (texte, variable) in enumerate((
                    ("Convergence", self.p_convergence),), 7):
                ttk.Label(droite, text=texte).grid(row=ligne, column=0,
                                                   sticky="w")
                ttk.Entry(droite, textvariable=variable).grid(
                    row=ligne, column=1, pady=2, sticky="we")
            ttk.Checkbutton(droite, text="Suivre la convergence",
                            variable=self.p_suivi).grid(
                row=9, column=0, columnspan=2, pady=2, sticky="w")
            self.p_optimisable = tk.BooleanVar(value=False)
            self.p_tarif_max = tk.StringVar()
            ttk.Checkbutton(droite, text="Tarif optimisable",
                            variable=self.p_optimisable).grid(
                row=10, column=0, columnspan=2, pady=2, sticky="w")
            ttk.Label(droite, text="Tarif maximal").grid(row=11, column=0,
                                                         sticky="w")
            ttk.Entry(droite, textvariable=self.p_tarif_max).grid(
                row=11, column=1, pady=2, sticky="we")
            ttk.Button(droite, text="Appliquer", command=self.appliquer
                       ).grid(row=12, column=0, pady=(6, 0))
            ttk.Button(droite, text="Reprendre la valeur par défaut",
                       command=self.reprendre_commune).grid(
                row=12, column=1, pady=(6, 0), sticky="e")
            self.afficher_mode()

        def afficher_mode(self):
            formule = self.p_mode.get() == "formule"
            self.e_expr.activer(formule)
            for element in self.zone_table:
                if formule:
                    element.grid_remove()
                else:
                    element.grid()
            if formule:
                self.e_expr.grid()
            else:
                self.e_expr.grid_remove()
            self.table.activer(not formule)
            self.c_var1.configure(state="disabled" if formule else "readonly")
            self.c_lecture.configure(state="disabled" if formule
                                     else "readonly")

        def choisir_parametre(self, _event):
            selection = self.t_param.selection()
            if not selection:
                return
            self.selection_dimension = None
            self.selection_parametre = None
            self.c_unite.configure(values=[T(v) for v in UNITES])
            fiche = self.modele.parametres.get(selection[0], {})
            self.portees = {T("Par défaut (tout périmètre)"): None}
            if est_indexe(selection[0]):
                self.portees.update({p["nom"]: creer_id(p["nom"])
                                     for p in self.modele.perimetres})
            self.c_portee.configure(
                values=list(self.portees),
                state="readonly" if len(self.portees) > 1 else "disabled")
            self.p_portee.set(T("Par défaut (tout périmètre)")
                              if est_indexe(selection[0]) else "")
            self.p_optimisable.set(bool(fiche.get("optimisable")))
            self.p_tarif_max.set(fiche.get("tarif_max", ""))
            if ":" in selection[0]:      # référence ou conversion
                self.p_mode.set("formule")
                self.p_expr.set("")
                self.p_unite.set("")
                self.p_convergence.set(CONVERGENCE_DEFAUT)
                self.p_suivi.set(False)
                self.table.charger([])
                self.afficher_mode()
            if selection[0].startswith("reference:"):
                dimension = selection[0].split(":", 1)[1]
                self.selection_dimension = dimension
                self.p_nom.set(T("Unité de référence : " + dimension))
                self.c_unite.configure(values=list(DIMENSIONS[dimension]))
                self.p_unite.set(self.modele.references_unites[dimension])
                return
            if selection[0].startswith("conversion:"):
                self.p_nom.set(T("Conversion calculée automatiquement"))
                return
            if selection[0].startswith("systeme:"):
                nom = selection[0].split(":", 1)[1]
                self.p_nom.set(T("Temps de la simulation, calculé par le "
                                 "moteur"))
                self.p_unite.set("" if nom in TEMPS_CALENDRIER
                                 else TEMPS_FIXES.get(
                    nom, self.modele.references_unites["Temps"]))
                return
            self.selection_parametre = selection[0]
            p = self.modele.parametres[selection[0]]
            self.p_nom.set(selection[0])
            self.p_mode.set(p["mode"])
            self.p_expr.set(p["expression"])
            self.p_unite.set(T(p["unite"]))
            self.p_convergence.set(p["convergence"])
            self.p_suivi.set(p["suivi"])
            self.c_var1.configure(values=[T(TEMPS_LIBELLE), "t", "t_sim"] + list(TEMPS_FIXES)
                + list(TEMPS_CALENDRIER) + sorted(
                i for i in self.modele.parametres if i != selection[0]))
            self.p_var1.set(T(TEMPS_LIBELLE) if p["variable_table"] ==
                            VARIABLE_TEMPS else p["variable_table"])
            self.p_lecture.set(T("Interpolation"
                                 if p["lecture_table"] == "interpolation"
                                 else "Par paliers"))
            self.table.charger(p["table"])
            self.afficher_mode()

        def reprendre_commune(self):
            if self.portee() and self.selection_parametre:
                self.modele.definir_valeur_perimetre(
                    self.selection_parametre, self.portee(), {"mode": None})
                self.charger_portee()
                self.rafraichir()

        def portee(self):
            return getattr(self, "portees", {}).get(self.p_portee.get())

        def charger_portee(self):
            """Affiche la formule commune ou la valeur propre du périmètre."""
            fiche = self.modele.parametres.get(self.selection_parametre)
            if not fiche:
                return
            propres = fiche.get("perimetres", {}).get(self.portee(), {}) \
                if self.portee() else {}
            source = propres if "mode" in propres else fiche
            self.p_mode.set(source["mode"])
            self.p_expr.set(source.get("expression", ""))
            self.table.charger(source.get("table", []))
            self.afficher_mode()
            if self.portee():
                self.dire("Valeur propre de %s" % self.p_portee.get()
                          if "mode" in propres else
                          "%s reprend la valeur par défaut." % self.p_portee.get())

        def appliquer(self):
            if self.portee() and self.selection_parametre:
                try:
                    self.modele.definir_valeur_perimetre(
                        self.selection_parametre, self.portee(),
                        {"mode": self.p_mode.get(),
                         "expression": self.p_expr.get(),
                         "table": self.table.lignes()})
                    self.rafraichir()
                    self.dire("Valeur propre de %s mise à jour."
                              % self.p_portee.get())
                except ErreurModele as erreur:
                    self.signaler(erreur)
                return
            if self.selection_dimension:
                self.lire_cadre()
                self.modele.definir_reference(self.selection_dimension,
                                              origine(self.p_unite.get()))
                self.rafraichir()
                self.dire("Unité de référence mise à jour.")
                return
            if not self.selection_parametre:
                return
            variable_1 = self.p_var1.get()
            if variable_1 == T(TEMPS_LIBELLE):
                variable_1 = VARIABLE_TEMPS
            try:
                self.modele.definir_parametre(
                    self.selection_parametre, self.p_mode.get(),
                    self.p_expr.get(), self.table.lignes(),
                    origine(self.p_unite.get()),
                    self.modele.parametres[self.selection_parametre][
                        "valeur_initiale"],
                    self.p_convergence.get(), self.p_suivi.get(), variable_1,
                    LECTURES_TABLE[origine(self.p_lecture.get())])
                self.modele.definir_tarif(self.selection_parametre,
                                          self.p_optimisable.get(),
                                          self.p_tarif_max.get())
                self.rafraichir()
                self.dire("Paramètre mis à jour.")
            except ErreurModele as erreur:
                self.signaler(erreur)

        # ---------------- Simulation ----------------
        def creer_simulation(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="6. Simulation")
            cadre = ttk.LabelFrame(page, text="Cadre temporel", padding=8)
            cadre.pack(fill="x")
            cadre.columnconfigure(1, weight=1)
            self.v_debut, self.v_fin = tk.StringVar(), tk.StringVar()
            self.v_pas = tk.StringVar(value="1")
            self.v_libelle_pas = tk.StringVar(value="Pas de temps")
            ttk.Label(cadre, wraplength=190, text="Date de démarrage (JJ/MM/AAAA)").grid(
                row=0, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_debut).grid(
                row=0, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(cadre, wraplength=190, textvariable=self.v_libelle_pas).grid(
                row=1, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_pas).grid(
                row=1, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(cadre, wraplength=190, text="Date de fin (JJ/MM/AAAA)").grid(
                row=2, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_fin).grid(
                row=2, column=1, padx=6, pady=2, sticky="we")
            self.v_iterations = tk.StringVar(value=ITERATIONS_MAX_DEFAUT)
            ttk.Label(cadre, wraplength=190, text="Itérations max par pas de temps").grid(
                row=3, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_iterations).grid(
                row=3, column=1, padx=6, pady=2, sticky="we")
            self.v_taux = tk.StringVar()
            ttk.Label(cadre, wraplength=190, text="Taux d'actualisation (0.08 pour 8 %)").grid(
                row=5, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_taux).grid(
                row=5, column=1, padx=6, pady=2, sticky="we")
            self.v_conserver = tk.BooleanVar(value=False)
            ttk.Checkbutton(cadre, text="Conserver la convergence dans "
                            "Resultat.dat", variable=self.v_conserver).grid(
                row=4, column=0, columnspan=2, pady=2, sticky="w")
            cadre = ttk.LabelFrame(page, text="Tarifs optimisables",
                                   padding=8)
            cadre.pack(fill="x", pady=(8, 0))
            cadre.columnconfigure(1, weight=1)
            self.v_option = tk.StringVar(value=T(OPTIONS_TARIFS_UI["actuels"]))
            self.v_hausse, self.v_tri = tk.StringVar(), tk.StringVar()
            self.v_structure_tri, self.v_tres_min = tk.StringVar(), \
                tk.StringVar()
            ttk.Label(cadre, text="Option").grid(row=0, column=0, sticky="w")
            ttk.Combobox(cadre, textvariable=self.v_option, state="readonly",
                         values=[T(v) for v in OPTIONS_TARIFS_UI.values()]
                         ).grid(row=0, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(cadre, wraplength=190, text="Structures à équilibrer"
                      ).grid(row=1, column=0, sticky="nw")
            self.l_structures = tk.Listbox(cadre, selectmode="multiple",
                                           height=4, exportselection=False)
            self.l_structures.grid(row=1, column=1, padx=6, pady=2,
                                   sticky="we")
            for rang, (texte, variable) in enumerate((
                    ("Hausse maximale par an (0.1 pour 10 %)", self.v_hausse),
                    ("TRI cible (0.1 pour 10 %)", self.v_tri)), 2):
                ttk.Label(cadre, wraplength=190, text=texte).grid(
                    row=rang, column=0, sticky="w")
                ttk.Entry(cadre, width=12, textvariable=variable).grid(
                    row=rang, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(cadre, text="Structure du TRI").grid(row=4, column=0,
                                                           sticky="w")
            self.c_structure_tri = ttk.Combobox(
                cadre, textvariable=self.v_structure_tri, state="readonly")
            self.c_structure_tri.grid(row=4, column=1, padx=6, pady=2,
                                      sticky="we")
            ttk.Label(cadre, wraplength=190, text="Trésorerie minimale"
                      ).grid(row=5, column=0, sticky="w")
            ttk.Entry(cadre, width=12, textvariable=self.v_tres_min).grid(
                row=5, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(cadre, wraplength=330, foreground="#51616f", text=(
                "Cochez « Tarif optimisable » dans l'onglet 4. Un tarif "
                "social non coché reste fixe.")).grid(
                row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
            boutons = ttk.Frame(page)
            boutons.pack(fill="x", pady=(8, 4))
            ttk.Button(boutons, text="Vérifier",
                       command=self.verifier_modele).pack(side="left")
            ttk.Button(boutons, text="Lancer",
                       command=self.lancer_simulation).pack(side="left",
                                                            padx=6)
            ttk.Button(page, text="Écrire le fichier de simulation",
                       command=self.ecrire_simulation).pack(anchor="w",
                                                            pady=(0, 8))
            ttk.Label(page, wraplength=330, foreground="#51616f",
                      text="Valeurs initiales : onglet 5. État initial. "
                      "Critères de convergence : onglet 4. Paramètres.").pack(anchor="w")
            cadre, self.t_controle = self.creer_tableau(
                page, ("Niveau", "Message"), (70, 265))
            cadre.pack(fill="both", expand=True, pady=(8, 0))

        def lire_cadre(self):
            self.modele.definir_simulation(self.v_debut.get(),
                                           self.v_pas.get(),
                                           self.v_fin.get(),
                                           self.v_iterations.get(),
                                           "oui" if self.v_conserver.get()
                                           else "non", self.v_taux.get())
            ids = list(self.modele.structures)
            noms = {T(v): k for k, v in OPTIONS_TARIFS_UI.items()}
            par_nom = {f["nom"]: k for k, f in self.modele.structures.items()}
            try:
                self.modele.definir_tarifs(
                    noms.get(self.v_option.get(), "actuels"),
                    [ids[r] for r in self.l_structures.curselection()
                     if r < len(ids)],
                    self.v_hausse.get(), self.v_tri.get(),
                    par_nom.get(self.v_structure_tri.get(), ""),
                    self.v_tres_min.get())
            except ErreurModele as erreur:
                self.dire(str(erreur))

        def verifier_modele(self):
            self.lire_cadre()
            erreurs, alertes = self.modele.verifier()
            self.t_controle.delete(*self.t_controle.get_children())
            for texte in erreurs:
                self.t_controle.insert("", "end", values=(T("Bloquant"), T(texte)))
            for texte in alertes:
                self.t_controle.insert("", "end", values=(T("Alerte"), T(texte)))
            self.dire("%d blocage(s), %d alerte(s)"
                             % (len(erreurs), len(alertes)))
            return erreurs

        def ecrire_simulation(self):
            if self.verifier_modele():
                self.signaler("Corrigez les lignes marquées Bloquant avant "
                              "d'écrire le fichier.")
                return
            self.enregistrer()

        # ---------------- Post-traitement ----------------
        def creer_post(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="7. Post-traitement")
            form = ttk.Frame(page)
            form.pack(fill="x", pady=(0, 6))
            form.columnconfigure(1, weight=1)
            self.q_nom = tk.StringVar()
            self.q_structure = tk.StringVar()
            self.q_expr = tk.StringVar()
            self.q_unite = tk.StringVar()
            self.selection_post = None
            ttk.Label(form, text="Nom").grid(row=0, column=0, sticky="w")
            ttk.Entry(form, textvariable=self.q_nom).grid(
                row=0, column=1, padx=6, pady=2, sticky="we")
            ttk.Label(form, text="Structure").grid(row=1, column=0, sticky="w")
            self.c_post_structure = ttk.Combobox(
                form, textvariable=self.q_structure, state="readonly")
            self.c_post_structure.grid(row=1, column=1, padx=6, pady=2,
                                       sticky="we")
            ttk.Label(form, text="Formule").grid(row=2, column=0, columnspan=2,
                                                 sticky="w")
            ChampFormule(form, self.q_expr, 7).grid(
                row=3, column=0, columnspan=2, padx=(0, 6), pady=2, sticky="we")
            ttk.Label(form, text="Unité").grid(row=4, column=0, sticky="w")
            ttk.Combobox(form, textvariable=self.q_unite, state="readonly",
                         values=[T(v) for v in UNITES]).grid(
                row=4, column=1, padx=6, pady=2, sticky="we")
            boutons = ttk.Frame(page)
            boutons.pack(fill="x", pady=(0, 4))
            ttk.Button(boutons, text="Ajouter", command=self.ajouter_post
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Modifier", command=self.modifier_post
                       ).pack(side="left", padx=2)
            ttk.Button(boutons, text="Supprimer", command=self.supprimer_post
                       ).pack(side="left", padx=2)
            ttk.Label(page, wraplength=330, foreground="#51616f",
                      text="Calculé après la simulation, sans effet sur les "
                      "calculs. Fonctions : total, moyenne, minimum, maximum, "
                      "van(x, taux), tri(x).").pack(anchor="w", pady=(0, 6))
            cadre, self.t_post = self.creer_tableau(
                page, ("Variable", "Unité", "Formule"), (170, 60, 105))
            cadre.pack(fill="both", expand=True)
            self.t_post.bind("<<TreeviewSelect>>", self.choisir_post)

        def id_structure_post(self):
            nom = self.q_structure.get()
            if nom == STRUCTURE_COMMUNE:
                return nom
            return self.id_structure(nom)

        def ajouter_post(self):
            self._enregistrer_post(None)

        def modifier_post(self):
            if self.selection_post:
                self._enregistrer_post(self.selection_post)

        def _enregistrer_post(self, ancien_id):
            try:
                self.selection_post = self.modele.ajouter_post(
                    self.q_nom.get(), self.id_structure_post(),
                    self.q_expr.get(), origine(self.q_unite.get()), ancien_id)
                self.rafraichir()
                self.dire("Paramètre mis à jour.")
            except ErreurModele as erreur:
                self.signaler(erreur)

        def supprimer_post(self):
            if not self.selection_post:
                return
            try:
                self.modele.supprimer_post(self.selection_post)
                self.selection_post = None
                self.rafraichir()
            except ErreurModele as erreur:
                self.signaler(erreur)

        def choisir_post(self, _event):
            selection = self.t_post.selection()
            if selection:
                self.selection_post = selection[0]
                q = self.modele.post[selection[0]]
                self.q_nom.set(q["nom"])
                self.q_expr.set(q["expression"])
                self.q_unite.set(T(q["unite"]))
                s = self.modele.structures.get(q["structure"])
                self.q_structure.set(s["nom"] if s else q["structure"])

        def remplir_post(self):
            m = self.modele
            self.c_post_structure.configure(
                values=[STRUCTURE_COMMUNE] + [s["nom"] for s in
                                              m.structures.values()])
            self.t_post.delete(*self.t_post.get_children())
            for i, q in sorted(m.post.items()):
                self.t_post.insert("", "end", iid=i, values=(
                    i, T(q["unite"]), " ".join(q["expression"].split())))

        def lancer_simulation(self):
            """Étapes 7 et 8 : calcule et écrit Resultat.dat."""
            fenetre = FenetreSimulation(self)
            self.fenetre_simulation = fenetre
            self.update()
            if self.verifier_modele():
                fenetre.conclure(False, [
                    "Corrigez les lignes marquées Bloquant avant de lancer la "
                    "simulation."] + [self.t_controle.item(i, "values")[1]
                                      for i in self.t_controle.get_children()])
                return
            import ppp_moteur
            resultat = ppp_moteur.simuler_tarifs(self.modele, fenetre)
            ppp_moteur.ecrire_resultat(
                resultat, ppp_moteur.chemin_local(ppp_moteur.FICHIER_RESULTAT))
            self.resultat = None if resultat["erreurs"] \
                and not resultat.get("comptes") else resultat
            self.remplir_resultats()
            self.t_controle.delete(*self.t_controle.get_children())
            self.t_controle.insert("", "end", values=(T("Statut"),
                                                      T(resultat["statut"])))
            for bloc in resultat["convergence"]:
                self.t_controle.insert("", "end", values=(
                    T("Boucle"), T("%s%s : %d itération(s) au maximum, écart "
                                   "%.3g" % (" + ".join(bloc["variables"]),
                                             " (Newton)" if bloc["newton"]
                                             else "", bloc["iterations"],
                                             bloc["ecart"]))))
            for ligne in ppp_moteur.resumer_suivi(resultat):
                self.t_controle.insert("", "end", values=(T("Suivi"),
                                                          T(ligne)))
            for texte in resultat["erreurs"]:
                self.t_controle.insert("", "end", values=(T("Erreur"), T(texte)))
            for texte in resultat["alertes"]:
                self.t_controle.insert("", "end", values=(T("Alerte"), T(texte)))
            self.dire("Simulation : %s. Résultats dans %s"
                             % (resultat["statut"],
                                ppp_moteur.FICHIER_RESULTAT))
            reussite = not resultat["erreurs"]
            fenetre.conclure(reussite, resultat["erreurs"] if not reussite else
                             ["%d alerte(s)." % len(resultat["alertes"])]
                             if resultat["alertes"] else [])

        # ---------------- Fonctions ----------------
        def creer_fonctions(self):
            page = ttk.Frame(self.onglets, padding=8)
            self.onglets.add(page, text="9. Fonctions")
            cadre, self.t_fonctions = self.creer_tableau(
                page, ("Fonction", "Description"), (190, 150))
            self.t_fonctions.configure(height=5)
            cadre.pack(fill="both", expand=True)
            self.t_fonctions.bind("<<TreeviewSelect>>", self.choisir_fonction)
            fiche = ttk.LabelFrame(page, text="Fiche de la fonction",
                                   padding=8)
            fiche.pack(fill="x", pady=(8, 0))
            fiche.columnconfigure(1, weight=1)
            self.u_nom, self.u_args = tk.StringVar(), tk.StringVar()
            self.u_description, self.u_corps = tk.StringVar(), tk.StringVar()
            self.u_essai, self.u_resultat = tk.StringVar(), tk.StringVar()
            self.selection_fonction = None
            for rang, (texte, variable) in enumerate((
                    ("Nom", self.u_nom),
                    ("Arguments (séparés par des virgules)", self.u_args),
                    ("Description", self.u_description))):
                ttk.Label(fiche, text=texte, wraplength=150).grid(
                    row=rang, column=0, sticky="w")
                ttk.Entry(fiche, textvariable=variable).grid(
                    row=rang, column=1, pady=2, sticky="we")
            ttk.Label(fiche, text="Calcul : une ligne par paramètre interne, "
                      "la dernière est résultat = ...", wraplength=330
                      ).grid(row=3, column=0, columnspan=2, sticky="w")
            ChampFormule(fiche, self.u_corps, 7).grid(
                row=4, column=0, columnspan=2, pady=3, sticky="we")
            boutons = ttk.Frame(fiche)
            boutons.grid(row=5, column=0, columnspan=2, sticky="w")
            for texte, action in (("Ajouter", self.ajouter_fonction),
                                  ("Modifier", self.modifier_fonction),
                                  ("Supprimer", self.supprimer_fonction)):
                ttk.Button(boutons, text=texte, command=action).pack(
                    side="left", padx=(0, 4))
            ttk.Button(fiche, text="Ajouter la bibliothèque de départ",
                       command=self.ajouter_bibliotheque).grid(
                row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
            ttk.Label(fiche, text="Valeurs d'essai", wraplength=150).grid(
                row=7, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(fiche, textvariable=self.u_essai).grid(
                row=7, column=1, pady=(8, 2), sticky="we")
            ttk.Button(fiche, text="Tester", command=self.tester_fonction
                       ).grid(row=8, column=0, sticky="w")
            ttk.Label(fiche, textvariable=self.u_resultat, wraplength=230
                      ).grid(row=8, column=1, sticky="w")

        def remplir_fonctions(self):
            tableau = self.t_fonctions
            tableau.delete(*tableau.get_children())
            for nom, f in self.modele.fonctions.items():
                tableau.insert("", "end", iid=nom, values=(
                    "%s(%s)" % (nom, ", ".join(f["arguments"])),
                    f.get("description", "")))

        def choisir_fonction(self, _evenement):
            selection = self.t_fonctions.selection()
            if not selection:
                return
            f = self.modele.fonctions[selection[0]]
            self.selection_fonction = selection[0]
            self.u_nom.set(selection[0])
            self.u_args.set(", ".join(f["arguments"]))
            self.u_description.set(f.get("description", ""))
            self.u_corps.set(f["corps"])
            self.u_essai.set("")
            self.u_resultat.set("")

        def enregistrer_fonction(self, ancien):
            try:
                self.modele.definir_fonction(
                    self.u_nom.get(), self.u_args.get(), self.u_corps.get(),
                    self.u_description.get(), ancien)
            except ErreurModele as erreur:
                self.signaler(erreur)
                return
            self.selection_fonction = self.u_nom.get().strip()
            self.rafraichir()
            self.dire("Fonction enregistrée.")

        def ajouter_fonction(self):
            self.enregistrer_fonction(None)

        def modifier_fonction(self):
            if self.selection_fonction:
                self.enregistrer_fonction(self.selection_fonction)

        def supprimer_fonction(self):
            if not self.selection_fonction:
                return
            try:
                self.modele.supprimer_fonction(self.selection_fonction)
            except ErreurModele as erreur:
                self.signaler(erreur)
                return
            self.selection_fonction = None
            self.rafraichir()

        def ajouter_bibliotheque(self):
            ajoutees = self.modele.ajouter_bibliotheque()
            self.rafraichir()
            self.dire("Fonctions ajoutées : %s" % (", ".join(ajoutees)
                                                    or "aucune"))

        def tester_fonction(self):
            nom = self.selection_fonction
            if not nom:
                self.signaler("Sélectionnez une fonction.")
                return
            texte = "%s(%s)" % (nom, self.u_essai.get())
            try:
                valeur = tester_appel(self.modele, texte)
                self.u_resultat.set("= %.10g" % valeur)
            except ErreurModele as erreur:
                self.u_resultat.set(T(str(erreur)))

        # ---------------- Périmètres ----------------
        def creer_perimetres(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="2. Périmètres")
            ttk.Label(page, wraplength=330, foreground="#51616f", text=(
                "Une ligne par périmètre p, une colonne par groupe (centre, "
                "région...). Cliquez sur une case pour la modifier, puis "
                "Appliquer. La ligne Global, toujours présente, regroupe tous "
                "les périmètres ; sans périmètre, tout le modèle est "
                "Global.")).pack(anchor="w", pady=(0, 6))
            cadre = ttk.Frame(page)
            cadre.pack(fill="both", expand=True)
            self.t_perimetres = ttk.Treeview(cadre, show="headings",
                                             selectmode="browse")
            barre = ttk.Scrollbar(cadre, orient="vertical",
                                  command=self.t_perimetres.yview)
            self.t_perimetres.configure(yscrollcommand=barre.set)
            self.t_perimetres.pack(side="left", fill="both", expand=True)
            barre.pack(side="right", fill="y")
            self.t_perimetres.bind("<Button-1>", self.cliquer_perimetre)
            self.champ_perimetre = None
            for rang, boutons in enumerate((
                    (("+ Périmètre", self.ajouter_perimetre),
                     ("- Périmètre", self.retirer_perimetre)),
                    (("+ Colonne", self.ajouter_colonne),
                     ("- Colonne", self.retirer_colonne)),
                    (("Importer", self.importer_perimetres),
                     ("Exporter", self.exporter_perimetres),
                     ("Appliquer", self.appliquer_perimetres)))):
                ligne = ttk.Frame(page)
                ligne.pack(fill="x", pady=(6 if rang == 0 else 2, 0))
                for texte, action in boutons:
                    ttk.Button(ligne, text=texte, command=action).pack(
                        side="left", padx=(0, 4))
            ttk.Label(page, wraplength=330, foreground="#51616f", text=(
                "Dans une formule : x[structure, p] pour le périmètre "
                "courant, somme_p(x[structure, p], \"Région:Thiès\") pour "
                "un groupe.")).pack(anchor="w", pady=(8, 0))
            self.colonnes_perimetres, self.lignes_perimetres = [], []
            self.perimetres_modifies = False

        def charger_perimetres(self):
            m = self.modele
            self.colonnes_perimetres = m.colonnes_table()
            self.lignes_perimetres = m.lignes_table()
            self.afficher_perimetres(False)

        def afficher_perimetres(self, modifie=True):
            self.perimetres_modifies = modifie
            tableau = self.t_perimetres
            colonnes = ["Périmètre"] + self.colonnes_perimetres
            cles = ["c%d" % i for i in range(len(colonnes))]
            tableau.delete(*tableau.get_children())
            tableau.configure(columns=cles)
            for cle, titre in zip(cles, colonnes):
                tableau.heading(cle, text=T(titre))
                tableau.column(cle, width=110, stretch=True)
            # Ligne fixe : le Global, toujours présent, qui couvre tout.
            tableau.tag_configure("global", foreground="#51616f",
                                  background="#eef1f4")
            nombre = len([l for l in self.lignes_perimetres
                          if l and str(l[0]).strip()])
            groupes = ["" if not nombre or creer_id(c) in
                       COLONNES_X + COLONNES_Y else T("Tous")
                       for c in self.colonnes_perimetres]
            if groupes and not nombre:
                groupes[0] = T("Tout le modèle")
            tableau.insert("", "end", iid="global", tags=("global",),
                           values=[T("Global")] + groupes)
            for rang, ligne in enumerate(self.lignes_perimetres):
                tableau.insert("", "end", iid=str(rang),
                               values=ligne + [""] * (len(cles) - len(ligne)))

        def cliquer_perimetre(self, evenement):
            ligne = self.t_perimetres.identify_row(evenement.y)
            colonne = self.t_perimetres.identify_column(evenement.x)
            if ligne and colonne and ligne != "global":
                self.after_idle(lambda: self.saisir_perimetre(
                    ligne, int(colonne[1:]) - 1))

        def saisir_perimetre(self, ligne, rang):
            self.fermer_perimetre()
            boite = self.t_perimetres.bbox(ligne, "#%d" % (rang + 1))
            if not boite:
                return
            champ = ttk.Entry(self.t_perimetres)
            valeurs = self.lignes_perimetres[int(ligne)]
            champ.insert(0, valeurs[rang] if rang < len(valeurs) else "")
            champ.select_range(0, "end")
            champ.place(x=boite[0], y=boite[1], width=boite[2],
                        height=boite[3])
            champ.focus_set()
            self.champ_perimetre = (champ, int(ligne), rang)
            champ.bind("<Return>", lambda _e: self.fermer_perimetre())
            champ.bind("<FocusOut>", lambda _e: self.fermer_perimetre())
            champ.bind("<Escape>", lambda _e: self.fermer_perimetre(False))

        def fermer_perimetre(self, garder=True):
            if self.champ_perimetre is None:
                return
            champ, ligne, rang = self.champ_perimetre
            self.champ_perimetre = None
            if garder:
                valeurs = self.lignes_perimetres[ligne]
                valeurs += [""] * (rang + 1 - len(valeurs))
                valeurs[rang] = champ.get().strip()
            champ.destroy()
            self.afficher_perimetres(garder or self.perimetres_modifies)

        def ajouter_perimetre(self):
            self.fermer_perimetre()
            self.lignes_perimetres.append(
                [""] * (1 + len(self.colonnes_perimetres)))
            self.afficher_perimetres()
            self.saisir_perimetre(str(len(self.lignes_perimetres) - 1), 0)

        def retirer_perimetre(self):
            selection = self.t_perimetres.selection()
            if selection and selection[0] != "global":
                del self.lignes_perimetres[int(selection[0])]
                self.afficher_perimetres()

        def ajouter_colonne(self):
            from tkinter import simpledialog
            nom = simpledialog.askstring(
                T("HapNatt"), T("Nom de la colonne de groupes :"),
                parent=self)
            if nom and nom.strip():
                self.colonnes_perimetres.append(nom.strip())
                for ligne in self.lignes_perimetres:
                    ligne.append("")
                self.afficher_perimetres()

        def retirer_colonne(self):
            if not self.colonnes_perimetres:
                return
            from tkinter import simpledialog
            nom = simpledialog.askstring(
                T("HapNatt"), T("Colonne à retirer :"), parent=self,
                initialvalue=self.colonnes_perimetres[-1])
            if nom in self.colonnes_perimetres:
                rang = self.colonnes_perimetres.index(nom) + 1
                self.colonnes_perimetres.remove(nom)
                for ligne in self.lignes_perimetres:
                    if rang < len(ligne):
                        del ligne[rang]
                self.afficher_perimetres()

        def appliquer_perimetres(self):
            self.fermer_perimetre()
            try:
                self.modele.definir_perimetres(self.colonnes_perimetres,
                                               self.lignes_perimetres)
            except ErreurModele as erreur:
                self.signaler(erreur)
                return
            self.resultat = None
            self.perimetres_modifies = False
            self.remplir_resultats()
            self.rafraichir()
            self.dire("Périmètres mis à jour.")

        def importer_perimetres(self):
            chemin = filedialog.askopenfilename(
                parent=self, filetypes=[(T("Tableau"), "*.csv *.txt *.tsv"),
                                        ("*", "*")])
            if not chemin:
                return
            try:
                colonnes, lignes = lire_tableau_perimetres(chemin)
            except (OSError, ValueError, ErreurModele) as erreur:
                self.signaler(erreur)
                return
            self.colonnes_perimetres, self.lignes_perimetres = colonnes, lignes
            self.afficher_perimetres()
            self.dire("Importé : %d périmètre(s). Vérifiez, puis Appliquer."
                      % len(lignes))

        def exporter_perimetres(self):
            chemin = filedialog.asksaveasfilename(
                parent=self, defaultextension=".csv",
                initialfile="Perimetres.csv", filetypes=[(".csv", "*.csv")])
            if chemin:
                with open(chemin, "w", encoding="utf-8-sig") as fichier:
                    fichier.write("\n".join(";".join(l) for l in [
                        [T("Périmètre")] + self.colonnes_perimetres]
                        + self.lignes_perimetres) + "\n")
                self.dire("Fichier enregistré : " + os.path.basename(chemin))

        # ---------------- État initial ----------------
        def origine_parametre(self, i):
            m = self.modele
            if m.parametres[i].get("conversion"):
                return "Conversion"
            if i in m.flux:
                return "Flux" if m.flux[i]["nature"] == "Financier" \
                    else "Physique"
            if i in m.charges:
                return "Charge"
            return "Poste" if i in m.postes else "Paramètre"

        def parametres_ordonnes(self):
            ordre = ("Conversion", "Paramètre", "Flux", "Physique", "Charge",
                     "Poste")
            return sorted(self.modele.parametres, key=lambda v: (
                ordre.index(self.origine_parametre(v)), v))

        def creer_etat_initial(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="5. État initial")
            ttk.Label(page, wraplength=330, foreground="#51616f",
                      text="Cliquez sur une valeur pour la saisir. Entrée "
                      "passe à la ligne suivante.").pack(anchor="w",
                                                         pady=(0, 4))
            cadre, self.t_initial = self.creer_tableau(
                page, ("Variable", "Unité", "Valeur initiale"),
                (190, 60, 85))
            cadre.pack(fill="both", expand=True)
            self.t_initial.bind("<Button-1>", self.cliquer_initial)
            self.champ_initial = None

        def remplir_etat_initial(self):
            self.fermer_initial(False)
            tableau = self.t_initial
            tableau.delete(*tableau.get_children())
            noms = {creer_id(p["nom"]): p["nom"]
                    for p in self.modele.perimetres}
            for i in self.parametres_ordonnes():
                p = self.modele.parametres[i]
                tableau.insert("", "end", iid=i, values=(
                    i, T(p["unite"]), p["valeur_initiale"]))
                if est_indexe(i):
                    for pid, nom in noms.items():
                        propre = p.get("perimetres", {}).get(pid, {})
                        tableau.insert("", "end", iid=i + "|" + pid, values=(
                            "      " + nom, "",
                            propre.get("valeur_initiale", "")))

        def cliquer_initial(self, evenement):
            ligne = self.t_initial.identify_row(evenement.y)
            colonne = self.t_initial.identify_column(evenement.x)
            if ligne and colonne == "#3":
                self.after_idle(lambda: self.saisir_initial(ligne))

        def saisir_initial(self, ligne):
            self.fermer_initial()
            if not self.t_initial.exists(ligne):
                return
            self.t_initial.see(ligne)
            self.t_initial.update_idletasks()
            boite = self.t_initial.bbox(ligne, "#3")
            if not boite:
                return
            champ = ttk.Entry(self.t_initial)
            champ.insert(0, self.t_initial.set(ligne, "#3"))
            champ.select_range(0, "end")
            champ.place(x=boite[0], y=boite[1], width=boite[2],
                        height=boite[3])
            champ.focus_set()
            self.champ_initial = (champ, ligne)
            champ.bind("<Return>", lambda _e: self.suivant_initial())
            champ.bind("<Tab>", lambda _e: self.suivant_initial())
            champ.bind("<Escape>", lambda _e: self.fermer_initial(False))
            champ.bind("<FocusOut>", lambda _e: self.fermer_initial())

        def suivant_initial(self):
            if self.champ_initial is None:
                return "break"
            ligne = self.champ_initial[1]
            if self.fermer_initial():
                suivante = self.t_initial.next(ligne)
                if suivante:
                    self.saisir_initial(suivante)
            return "break"

        def fermer_initial(self, garder=True):
            """Ferme la saisie en cours. Retourne False si la valeur est refusée."""
            if self.champ_initial is None:
                return True
            champ, ligne = self.champ_initial
            self.champ_initial = None
            texte = champ.get()
            champ.destroy()
            if garder and "|" in ligne:
                identifiant, pid = ligne.split("|", 1)
                try:
                    self.modele.definir_valeur_perimetre(
                        identifiant, pid, {"valeur_initiale": texte})
                except ErreurModele as erreur:
                    self.signaler(erreur)
                    return False
                self.t_initial.set(ligne, "#3", texte.strip().replace(
                    ",", "."))
                return True
            if not garder or ligne not in self.modele.parametres:
                return True
            try:
                self.modele.definir_valeur_initiale(ligne, texte)
            except ErreurModele as erreur:
                self.signaler(erreur)
                return False
            self.t_initial.set(ligne, "#3",
                               self.modele.parametres[ligne]["valeur_initiale"])
            return True

        # ---------------- Résultats ----------------
        def creer_resultats(self):
            page = ttk.Frame(self.onglets, padding=10)
            self.onglets.add(page, text="8. Résultats")
            ttk.Label(page, wraplength=330, foreground="#51616f",
                      text="Sélectionnez une ou plusieurs variables avec Ctrl "
                      "ou Maj.").pack(anchor="w", pady=(0, 4))
            ligne = ttk.Frame(page)
            ligne.pack(fill="x", pady=(0, 4))
            self.r_vue = tk.StringVar(value="courbes")
            ttk.Radiobutton(ligne, text="Courbes", value="courbes",
                            variable=self.r_vue,
                            command=self.afficher_vue).pack(side="left")
            ttk.Radiobutton(ligne, text="Synthèse", value="synthese",
                            variable=self.r_vue,
                            command=self.afficher_vue).pack(side="left", padx=8)
            ttk.Radiobutton(ligne, text="Répartition", value="repartition",
                            variable=self.r_vue,
                            command=self.afficher_vue).pack(side="left")
            ttk.Radiobutton(ligne, text="Tarifs", value="tarifs",
                            variable=self.r_vue,
                            command=self.afficher_vue).pack(side="left",
                                                            padx=8)
            ligne = ttk.Frame(page)
            ligne.pack(fill="x", pady=(0, 4))
            ttk.Radiobutton(ligne, text="Périmètres", value="perimetres",
                            variable=self.r_vue,
                            command=self.afficher_vue).pack(side="left")
            ligne = ttk.Frame(page)
            ligne.pack(fill="x", pady=(0, 4))
            ttk.Label(ligne, text="Regrouper par").pack(side="left")
            self.r_niveau = tk.StringVar(value="Global")
            self.c_niveau = ttk.Combobox(ligne, textvariable=self.r_niveau,
                                         state="readonly", width=12,
                                         values=["Global"])
            self.c_niveau.pack(side="left", padx=6)
            self.c_niveau.bind("<<ComboboxSelected>>",
                               lambda _e: self.remplir_synthese())
            ttk.Label(ligne, text="Filtre").pack(side="left")
            self.r_filtre = tk.StringVar(value=T("Tous"))
            self.c_filtre = ttk.Combobox(ligne, textvariable=self.r_filtre,
                                         state="readonly", width=16,
                                         values=[T("Tous")])
            self.c_filtre.pack(side="left", padx=6)
            self.c_filtre.bind("<<ComboboxSelected>>",
                               lambda _e: self.remplir_synthese())
            ligne = ttk.Frame(page)
            ligne.pack(fill="x", pady=(0, 4))
            ttk.Label(ligne, text="Période").pack(side="left")
            self.r_periode = tk.StringVar(value=T("Toute la simulation"))
            self.c_periode = ttk.Combobox(
                ligne, textvariable=self.r_periode, state="readonly", width=20,
                values=[T("Toute la simulation")])
            self.c_periode.pack(side="left", padx=6)
            self.c_periode.bind("<<ComboboxSelected>>",
                                lambda _e: self.remplir_synthese())
            ligne = ttk.Frame(page)
            ligne.pack(fill="x", pady=(0, 4))
            ttk.Label(ligne, text="Axe du temps").pack(side="left")
            self.r_axe = tk.StringVar(value=T("Date"))
            axe = ttk.Combobox(ligne, textvariable=self.r_axe,
                               state="readonly", width=10,
                               values=[T("Date"), "t", "t_sim"] + list(TEMPS_FIXES))
            axe.pack(side="left", padx=6)
            axe.bind("<<ComboboxSelected>>", lambda _e: self.tracer())
            cadre = ttk.Frame(page)
            cadre.pack(fill="both", expand=True)
            self.t_resultats = ttk.Treeview(cadre, columns=("Unité",),
                                            show="tree headings",
                                            selectmode="extended")
            self.t_resultats.heading("#0", text="Variable")
            self.t_resultats.heading("Unité", text="Unité")
            self.t_resultats.column("#0", width=250)
            self.t_resultats.column("Unité", width=70, stretch=False)
            barre = ttk.Scrollbar(cadre, orient="vertical",
                                  command=self.t_resultats.yview)
            self.t_resultats.configure(yscrollcommand=barre.set)
            self.t_resultats.pack(side="left", fill="both", expand=True)
            barre.pack(side="right", fill="y")
            self.t_resultats.bind("<<TreeviewSelect>>",
                                  lambda _e: self.tracer())
            boutons = ttk.Frame(page)
            boutons.pack(fill="x", pady=(6, 0))
            ttk.Label(boutons, text="Exporter").pack(side="left", padx=(0, 6))
            ttk.Button(boutons, text="PDF", width=7,
                       command=self.exporter_pdf).pack(side="left")
            ttk.Button(boutons, text=".csv", width=7,
                       command=lambda: self.exporter_table(".csv")).pack(
                side="left", padx=4)
            ttk.Button(boutons, text=".dat", width=7,
                       command=lambda: self.exporter_table(".dat")).pack(
                side="left")
            self.r_message = ttk.Label(self.zone_courbes, wraplength=760,
                                       foreground="#51616f")
            self.r_message.pack(anchor="w", pady=(0, 4))
            self.cadre_synthese = ttk.Frame(self.zone_courbes)
            self.t_synthese = ttk.Treeview(
                self.cadre_synthese, show="tree headings", selectmode="none")
            haut = ttk.Scrollbar(self.cadre_synthese, orient="vertical",
                                 command=self.t_synthese.yview)
            bas = ttk.Scrollbar(self.cadre_synthese, orient="horizontal",
                                command=self.t_synthese.xview)
            self.t_synthese.configure(yscrollcommand=haut.set,
                                      xscrollcommand=bas.set)
            bas.pack(side="bottom", fill="x")
            haut.pack(side="right", fill="y")
            self.t_synthese.pack(side="left", fill="both", expand=True)
            gras = font.nametofont("TkDefaultFont").copy()
            gras.configure(weight="bold")
            self.police_grasse = gras
            self.t_synthese.tag_configure("titre", font=gras,
                                          background="#E9ECF1")
            self.t_synthese.tag_configure("total", font=gras)
            self.figure = self.toile = None
            try:
                from matplotlib.backends.backend_tkagg import \
                    FigureCanvasTkAgg
                from matplotlib.figure import Figure
                self.figure = Figure(layout="constrained")
                self.toile = FigureCanvasTkAgg(self.figure,
                                               master=self.zone_courbes)
                self.toile.get_tk_widget().pack(fill="both", expand=True)
            except ImportError:
                self.r_message.configure(text=T(
                    "Pour afficher les courbes, installez matplotlib : "
                    "pip install matplotlib"))
            self.remplir_resultats()

        def remplir_resultats(self):
            import ppp_moteur
            self.t_resultats.delete(*self.t_resultats.get_children())
            self.c_periode.configure(values=[T("Toute la simulation")] + (
                [str(a) for a in ppp_moteur.annees_resultat(self.resultat)]
                if self.resultat else []))
            self.r_periode.set(T("Toute la simulation"))
            if self.resultat is not None:
                niveaux = ppp_moteur.niveaux_perimetres(self.resultat)
                self.c_niveau.configure(values=niveaux)
                if self.r_niveau.get() not in niveaux:
                    self.r_niveau.set(niveaux[0])
                source = self.resultat.get("source", self.modele)
                filtres = [p["nom"] for p in source.perimetres]
                for colonne in source.colonnes_groupes:
                    for valeur in dict.fromkeys(
                            p["groupes"].get(colonne, "")
                            for p in source.perimetres):
                        if valeur:
                            filtres.append("%s:%s" % (colonne, valeur))
                self.c_filtre.configure(values=[T("Tous")] + filtres)
            self.remplir_synthese()
            if self.resultat is None:
                return
            noeuds = {}

            def groupe(nom, parent=""):
                cle = (parent, nom)
                if cle not in noeuds:
                    noeuds[cle] = self.t_resultats.insert(
                        parent, "end", text=nom, open=False)
                return noeuds[cle]

            for cle, table in ppp_moteur.tables_resultat(
                    self.resultat).items():
                nom_groupe = T(table[0]) if table[0] == "Temps" else table[0]
                parent = groupe(nom_groupe)
                if cle.startswith("compte:"):
                    parent = groupe(T("Comptes"), parent)
                self.t_resultats.insert(parent, "end", iid=cle, text=table[1],
                                        values=(T(table[2]),))

        def afficher_vue(self):
            synthese = self.r_vue.get() != "courbes"
            if self.toile is not None:
                widget = self.toile.get_tk_widget()
                if synthese:
                    widget.pack_forget()
                else:
                    widget.pack(fill="both", expand=True)
            if synthese:
                self.cadre_synthese.pack(fill="both", expand=True)
                self.remplir_synthese()
            else:
                self.cadre_synthese.pack_forget()
                self.tracer()

        def annee_synthese(self):
            periode = self.r_periode.get()
            return int(periode) if periode.isdigit() else None

        def remplir_synthese(self):
            import ppp_moteur
            tableau = self.t_synthese
            tableau.delete(*tableau.get_children())
            if self.resultat is None:
                if self.r_vue.get() != "courbes":
                    self.r_message.configure(text=T(
                        "Lancez d'abord la simulation dans l'onglet 6."))
                return
            vue = self.r_vue.get()
            fonction = ppp_moteur.VUES_TABLEAU.get(
                vue, ppp_moteur.synthese_resultat)
            options = {}
            if vue == "perimetres":
                options["niveau"] = self.r_niveau.get()
            elif vue == "repartition" and self.r_filtre.get() != T("Tous"):
                options["perimetre"] = self.r_filtre.get()
            try:
                structures, lignes = fonction(
                    self.resultat, self.annee_synthese(), **options)
            except ErreurModele as erreur:
                structures, lignes = [], [(str(erreur), "titre", [])]
            colonnes = ["nature"] + ["s%d" % i for i in range(len(structures))]
            tableau.configure(columns=colonnes[1:])
            tableau.heading("#0", text=T("Nature"))
            tableau.column("#0", width=340, stretch=False)
            noms = self.resultat["modele"].structures
            for colonne, s in zip(colonnes[1:], structures):
                tableau.heading(colonne, text=noms[s]["nom"] if s in noms else s)
                tableau.column(colonne, width=140, anchor="e", stretch=True)
            parent = ""

            def texte(valeur, genre):
                if valeur is None:
                    return ""
                if genre == "pourcent":
                    return "%.1f %%" % valeur
                if genre == "ratio":
                    return "%.2f" % valeur
                if genre == "tarif":
                    return "%.6g" % valeur
                return ppp_moteur.format_valeur(
                    0.0 if abs(valeur) < 0.005 else round(valeur))

            for libelle, genre, valeurs in lignes:
                ligne = tableau.insert(
                    parent if genre == "detail" else "", "end", text=libelle,
                    tags=(genre,), values=[texte(v, genre) for v in valeurs])
                if genre != "detail":
                    parent = ligne
            monnaie = self.resultat["modele"].references_unites["Monnaie"]
            self.r_message.configure(text=T(
                "Montants en %s. Flux : somme de la période. Bilan : valeur "
                "à la fin de la période." % monnaie) if vue == "synthese"
                else T("Moyenne annuelle de chaque tarif, selon l'option.")
                if vue == "tarifs"
                else T("Montants en %s, somme de la période. Les variables "
                       "prix ou taux sont des moyennes." % monnaie)
                if vue == "perimetres"
                else T("Montants en %s, somme de la période." % monnaie))

        def cles_resultats(self):
            tableau = self.t_resultats
            return [i for i in tableau.selection()
                    if not tableau.get_children(i)]

        def axe_resultats(self):
            axe = self.r_axe.get()
            return "Date" if axe == T("Date") else axe

        def tracer(self):
            if self.r_vue.get() != "courbes":
                self.remplir_synthese()
                return
            if self.figure is None:
                return
            cles = self.cles_resultats()
            if self.resultat is None:
                texte = "Lancez d'abord la simulation dans l'onglet 6."
            elif not cles:
                texte = "Choisissez une variable dans la liste."
            else:
                texte = ""
            import ppp_moteur
            if cles and self.resultat is not None:
                ecartees = ppp_moteur.dessiner_courbes(
                    self.figure, self.resultat, cles, self.axe_resultats())
                if ecartees:
                    texte = "%d courbe(s) non affichée(s) : 8 au maximum par " \
                        "graphique et 4 unités à la fois." % ecartees
            else:
                self.figure.clear()
            self.r_message.configure(text=T(texte))
            self.toile.draw_idle()

        def exporter_pdf(self):
            import ppp_moteur
            if self.r_vue.get() != "courbes":
                self.signaler("Le PDF concerne les courbes. Exportez la "
                              "synthèse en .csv ou en .dat.")
                return
            cles = self.cles_resultats()
            if self.resultat is None or not cles:
                self.signaler("Choisissez une variable dans la liste.")
                return
            try:
                chemin = filedialog.asksaveasfilename(
                    parent=self, defaultextension=".pdf", initialfile="Courbes.pdf",
                    filetypes=[("PDF", "*.pdf")])
                if chemin:
                    ppp_moteur.exporter_pdf(self.resultat, cles, chemin,
                                            self.axe_resultats())
                    self.dire("Fichier enregistré : "
                              + os.path.basename(chemin))
            except ImportError:
                self.signaler("Pour afficher les courbes, installez "
                              "matplotlib : pip install matplotlib")
            except OSError as erreur:
                self.signaler(erreur)

        def exporter_table(self, extension):
            import ppp_moteur
            if self.resultat is None:
                self.signaler("Lancez d'abord la simulation dans l'onglet 6.")
                return
            chemin = filedialog.asksaveasfilename(
                parent=self, defaultextension=extension,
                initialfile={"synthese": "Synthese",
                             "repartition": "Repartition"}.get(
                    self.r_vue.get(), "Tables") + extension,
                filetypes=[(extension, "*" + extension)])
            if chemin:
                try:
                    if self.r_vue.get() != "courbes":
                        ppp_moteur.exporter_synthese(
                            self.resultat, self.annee_synthese(), chemin,
                            self.r_vue.get())
                    else:
                        ppp_moteur.exporter_table(
                            self.resultat, self.cles_resultats(), chemin)
                    self.dire("Fichier enregistré : "
                              + os.path.basename(chemin))
                except OSError as erreur:
                    self.signaler(erreur)

        # ---------------- Commun ----------------
        def rafraichir(self):
            m = self.modele
            noms = [s["nom"] for s in m.structures.values()]
            self.c_payeur.configure(values=noms)
            self.c_benef.configure(values=noms)
            for tableau in (self.t_structures, self.t_flux, self.t_param):
                tableau.delete(*tableau.get_children())
            for i, s in m.structures.items():
                self.t_structures.insert("", "end", iid=i, values=(
                    s["nom"], T(s["type"])))
            for i, f in m.flux.items():
                nature = T(f["nature"] if f["nature"] == "Financier"
                           else f["effet"])
                self.t_flux.insert("", "end", iid=i, values=(
                    i, nature, self.definition(i)))
            circulaires = m.cycles()
            for dimension, unite in m.references_unites.items():
                self.t_param.insert(
                    "", "end", iid="reference:" + dimension, values=(
                        T("Référence : " + dimension), T("Base"), unite,
                        T("Défini")))
            for nom, libelle in (
                    ("t", "t (temps du modèle = t0 + t*)"),
                    ("t0", "t0 (date de démarrage)"),
                    ("t_sim", "t_sim (t* = n x pas de temps)")):
                self.t_param.insert("", "end", iid="systeme:" + nom, values=(
                    T(libelle), T("Base"), m.references_unites["Temps"],
                    T("Défini")))
            for nom, libelle in zip(TEMPS_CALENDRIER, (
                    "t[annee] (année du calendrier)",
                    "t[mois] (mois, de 1 à 12)",
                    "t[jour] (jour du mois, de 1 à 31)")):
                self.t_param.insert("", "end", iid="systeme:" + nom, values=(
                    T(libelle), T("Base"), "", T("Défini")))
            for nom, unite in TEMPS_FIXES.items():
                self.t_param.insert("", "end", iid="systeme:" + nom, values=(
                    nom, T("Base"), unite, T("Défini")))
            for atome, reference, facteur in m.conversions()[0]:
                self.t_param.insert(
                    "", "end", iid="conversion:" + atome, values=(
                        "1 %s = %s %s" % (atome, facteur, reference),
                        T("Conversion"), reference, T("Défini")))

            for i in self.parametres_ordonnes():
                self.t_param.insert("", "end", iid=i, values=(
                    i, T(self.origine_parametre(i)),
                    T(m.parametres[i]["unite"]), T(m.etat(i, circulaires))))
            self.remplir_etat_initial()
            self.dessiner_schema()
            self.remplir_fiche()
            self.v_debut.set(m.simulation["date_debut"])
            self.v_pas.set(m.simulation["pas"])
            self.v_fin.set(m.simulation["date_fin"])
            self.v_iterations.set(m.simulation["iterations_max"])
            self.v_conserver.set(m.simulation["conserver_convergence"] == "oui")
            self.v_taux.set(m.simulation["taux_actualisation"])
            self.remplir_fonctions()
            if self.champ_perimetre is None and \
                    not self.perimetres_modifies:
                self.charger_perimetres()
            # Le prototype ne gère qu'une option : celle des résultats
            # détaillés (la nouvelle interface peut en cocher plusieurs).
            self.v_option.set(T(OPTIONS_TARIFS_UI.get(
                m.simulation.get("option_principale")
                or m.simulation.get("option_tarifs"), "Tarifs actuels")))
            choisies = m.simulation.get("structures_equilibre", "").split(",")
            self.l_structures.delete(0, "end")
            for rang, (k, f) in enumerate(m.structures.items()):
                self.l_structures.insert("end", f["nom"])
                if k in choisies:
                    self.l_structures.selection_set(rang)
            self.v_hausse.set(m.simulation.get("hausse_max", ""))
            self.v_tri.set(m.simulation.get("tri_cible", ""))
            self.c_structure_tri.configure(
                values=[f["nom"] for f in m.structures.values()])
            self.v_structure_tri.set(
                m.structures[m.simulation["structure_tri"]]["nom"]
                if m.simulation.get("structure_tri") in m.structures else "")
            self.v_tres_min.set(m.simulation.get("tresorerie_min", ""))
            self.remplir_post()
            self.v_libelle_pas.set(
                T("Pas de temps (%s)" % m.references_unites["Temps"]))

        def enregistrer(self):
            """Enregistre la mise en données, même incomplète."""
            dossier = os.path.dirname(self.chemin)
            chemin = filedialog.asksaveasfilename(
                parent=self, defaultextension=".dat",
                initialfile=os.path.basename(self.chemin),
                initialdir=dossier or None,
                filetypes=[("Fichier dat", "*.dat")])
            if chemin:
                self.lire_cadre()
                self.modele.ecrire(chemin)
                self.chemin = chemin
                self.afficher_titre()
                self.dire("Enregistré : " + chemin)

        def ouvrir(self):
            chemin = filedialog.askopenfilename(
                parent=self, filetypes=[("Fichier dat", "*.dat")])
            if chemin:
                try:
                    modele = Modele.lire(chemin)
                except ErreurModele as erreur:
                    self.signaler(erreur)
                    return
                except (IndexError, KeyError, ValueError, UnicodeDecodeError):
                    self.signaler("Le fichier n'a pas pu être lu.")
                    return
                self.modele = modele
                self.resultat = None
                self.perimetres_modifies = False
                self.remplir_resultats()
                if self.fiche is not None and self.fiche.winfo_exists():
                    self.fiche.destroy()
                self.selection_structure = None
                self.selection_flux = None
                self.selection_parametre = None
                self.selection_dimension = None
                self.selection_post = None
                self.chemin = chemin
                self.afficher_titre()
                self.rafraichir()
                self.dire("Ouvert : " + chemin)

    definir_langue(LANGUE_INTERFACE)
    modele = modele_de_depart()
    Application(modele).mainloop()


if __name__ == "__main__":
    lancer_interface()
