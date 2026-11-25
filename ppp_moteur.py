# -*- coding: utf-8 -*-
"""
HapNatt - Étapes 7 et 8 : simulation

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

Lancement : placer ce fichier à côté de ppp_prototype.py, l'ouvrir dans IDLE,
puis appuyer sur F5. Il lit FICHIER_SIMULATION et écrit FICHIER_RESULTAT.

Le moteur calcule uniquement les formules et tables du jeu de données.
Il ne contient aucune règle de tarif, de rentabilité ou de comptabilité.

Unités : chaque valeur reste exprimée dans l'unité de son paramètre. Pendant
un calcul, elle est convertie vers une base commune, avec contrôle des
dimensions. Une boucle est résolue par itérations successives, puis par la
méthode de Newton si ces itérations divergent ou stagnent.
"""

# ============================ CONFIGURATION ============================
FICHIER_SIMULATION = "Exemple_Simulation.dat"
FICHIER_RESULTAT = "Resultat.dat"
PASSES_MAX = 50
DETAIL_ENTREES = ("recettes_encaissees", "apports_recus", "dette_recue",
                  "dividendes_recus", "autres_entrees")
DETAIL_SORTIES = ("charges_payees", "investissements", "dette_versee",
                  "dividendes_verses", "apports_verses")
DETAIL_ARGENT = DETAIL_ENTREES + DETAIL_SORTIES
CLASSEMENT_FLUX = {          # compte : (si la structure reçoit, si elle paie)
    "Résultat": ("recettes_encaissees", "charges_payees"),
    "Capital": ("apports_recus", "apports_verses"),
    "Dette": ("dette_recue", "dette_versee"),
    "Dividende": ("dividendes_recus", "dividendes_verses"),
    "Investissement": ("autres_entrees", "investissements"),
}
# Lignes de la synthèse : (clé ou None, libellé, genre)
# genre : titre, flux (somme de la période), stock (fin de période), total
LIGNES_SYNTHESE = (
    (None, "Mouvements d'argent", "titre"),
    ("recettes_encaissees", "Recettes encaissées", "flux"),
    ("apports_recus", "Apports en capital reçus", "flux"),
    ("dette_recue", "Dette : argent reçu", "flux"),
    ("dividendes_recus", "Dividendes reçus", "flux"),
    ("autres_entrees", "Autres entrées", "flux"),
    ("entrees", "Entrées d'argent", "total"),
    ("charges_payees", "Charges payées", "flux"),
    ("investissements", "Investissements", "flux"),
    ("dette_versee", "Dette : argent versé", "flux"),
    ("dividendes_verses", "Dividendes versés", "flux"),
    ("apports_verses", "Apports en capital versés", "flux"),
    ("sorties", "Sorties d'argent", "total"),
    ("solde", "Entrées moins sorties", "total"),
    (None, "Résultat comptable", "titre"),
    ("recettes", "Recettes dues", "flux"),
    ("charges_dues", "Charges dues", "flux"),
    ("amortissements", "Amortissements", "flux"),
    ("dotations", "Dotations aux provisions", "flux"),
    ("autres_resultat", "Intérêts moratoires et abandons", "flux"),
    ("resultat", "Résultat net", "total"),
    (None, "Bilan en fin de période", "titre"),
    ("actifs", "Actifs", "stock"),
    ("creances", "Créances", "stock"),
    ("impayes_a_recevoir", "Impayés et moratoires à recevoir", "stock"),
    ("tresorerie", "Trésorerie", "stock"),
    ("total_actif", "Total de l'actif", "total_stock"),
    ("capital", "dont capital", "stock"),
    ("fonds_propres", "Fonds propres", "stock"),
    ("dettes", "Dettes", "stock"),
    ("dettes_fournisseurs", "Dettes fournisseurs", "stock"),
    ("impayes_a_payer", "Impayés et moratoires à payer", "stock"),
    ("provisions", "Provisions", "stock"),
    ("total_passif", "Total du passif", "total_stock"),
    ("ecart_bilan", "Écart de bilan", "stock"),
    (None, "Capacité d'investissement", "titre"),
    ("caf", "Capacité d'autofinancement (CAF)", "flux_seul"),
    ("fonds_mobilisables", "Fonds propres mobilisables", "stock_seul"),
    ("annuite_supportable", "Annuité supportable", "stock_seul"),
    ("capacite_emprunt", "Capacité d'emprunt", "stock_seul"),
    ("capacite_investissement", "Capacité d'investissement", "total_seul"),
    ("besoin_investissement", "Besoin d'investissement", "stock_seul"),
    ("marge_investissement", "Marge ou déficit d'investissement", "total_seul"),
    (None, "Hors bilan", "titre"),
    ("reserves", "Réserves", "stock"),
    ("garanties", "Garanties et engagements", "stock"),
)
CATEGORIES_SYNTHESE = {"actifs": "Actif", "creances": "Créance",
                       "dettes": "Dette",
                       "dettes_fournisseurs": "Dette fournisseur",
                       "provisions": "Provision", "reserves": "Réserve",
                       "garanties": "Garantie"}
JOURS_MAX_PORTEE = {"jour": 1, "mois": 31, "annee": 366}
COURBES_PAR_GRAPHIQUE = 8
GRAPHIQUES_MAX = 4
COULEURS_COURBES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
                    "#008300", "#6250d6", "#e34948")
COMPTES_AFFICHES = (
    ("capital", "Capital"), ("tresorerie", "Trésorerie"),
    ("recettes", "Recettes"), ("charges", "Charges"),
    ("resultat", "Résultat net"), ("solde", "Entrées moins sorties"),
    ("entrees", "Entrées d'argent"), ("sorties", "Sorties d'argent"),
    ("charges_payees", "Charges payées"),
    ("investissements", "Investissements"),
    ("amortissements", "Amortissements"),
    ("dotations", "Dotations aux provisions"),
    ("charges_dues", "Charges dues"),
    ("autres_resultat", "Intérêts moratoires et abandons"),
    ("caf", "Capacité d'autofinancement (CAF)"),
    ("fonds_mobilisables", "Fonds propres mobilisables"),
    ("annuite_supportable", "Annuité supportable"),
    ("capacite_emprunt", "Capacité d'emprunt"),
    ("capacite_investissement", "Capacité d'investissement"),
    ("besoin_investissement", "Besoin d'investissement"),
    ("marge_investissement", "Marge ou déficit d'investissement"),
    ("impayes_a_recevoir", "Impayés et moratoires à recevoir"),
    ("impayes_a_payer", "Impayés et moratoires à payer"),
    ("dette_recue", "Dette : argent reçu"),
    ("dette_versee", "Dette : argent versé"),
    ("apports_recus", "Apports en capital reçus"),
    ("apports_verses", "Apports en capital versés"),
    ("dividendes_recus", "Dividendes reçus"),
    ("dividendes_verses", "Dividendes versés"),
    ("autres_entrees", "Autres entrées"),
    ("fonds_propres", "Fonds propres"),
    ("actifs", "Actifs"), ("creances", "Créances"), ("dettes", "Dettes"),
    ("dettes_fournisseurs", "Dettes fournisseurs"), ("reserves", "Réserves"),
    ("provisions", "Provisions"), ("garanties", "Garanties et engagements"),
    ("ecart_bilan", "Écart de bilan"))                  # passes complètes si lead() est utilisé
# =======================================================================

import ast
import calendar
import datetime
import math
import os
import re
import sys

from ppp_langues import T
from ppp_prototype import (ErreurModele, creer_id, est_indexe,
                           ANNEES_PAR_UNITE, MARQUE_JEU_DE_DONNEES, MULTIPLES_MONNAIE, PAIEMENT_DEFAUT,
                           PAIEMENT_FORMULES,
                           TEMPS_FIXES, TEMPS_MODELE, VARIABLE_TEMPS, VARIABLES_SYSTEME, Modele, ajouter_mois, lire_date,
                           compiler_expression, composer_id)


# Unité : (dimensions, facteur vers la base). Le temps a pour base l'année,
# la longueur le mètre, la masse le kg, l'énergie le kWh.
ATOMES_FIXES = {
    "m": ({"L": 1}, 1), "km": ({"L": 1}, 1000),
    "m2": ({"L": 2}, 1), "ha": ({"L": 2}, 1e4), "km2": ({"L": 2}, 1e6),
    "m3": ({"L": 3}, 1), "litre": ({"L": 3}, 0.001),
    "kg": ({"M": 1}, 1), "tonne": ({"M": 1}, 1000),
    "kWh": ({"E": 1}, 1), "MWh": ({"E": 1}, 1e3), "GWh": ({"E": 1}, 1e6),
    "Pa": ({"P": 1}, 1), "bar": ({"P": 1}, 1e5),
    "K": ({"Th": 1}, 1), "°C": ({"Th": 1}, 1),
    "%": ({}, 0.01), "sans": ({}, 1), "unité": ({}, 1), "an": ({"T": 1}, 1),
    "mois": ({"T": 1}, 1 / 12),
}
HEURES_PAR_UNITE = {"s": 1 / 3600, "min": 1 / 60, "h": 1, "j": 24, "jour": 24}
PUISSANCES = {"W": 0.001, "kW": 1, "MW": 1000}
MONNAIES = {"FCFA": ("FCFA", 1), "MFCFA": ("FCFA", 1e6), "EUR": ("EUR", 1),
            "USD": ("USD", 1)}


class ErreurCalcul(Exception):
    """Calcul impossible pour une variable et une période."""


def chemin_local(nom):
    """Chemin d'un fichier placé à côté de ce script."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), nom)


def combiner(a, b, signe=1):
    """Dimensions d'un produit (signe = 1) ou d'un quotient (signe = -1)."""
    resultat = dict(a)
    for cle, valeur in b.items():
        resultat[cle] = round(resultat.get(cle, 0) + signe * valeur, 9)
        if resultat[cle] == 0:
            del resultat[cle]
    return resultat


def texte_dimensions(d):
    if d is None:
        return "?"
    if not d:
        return "sans dimension"
    return "·".join("%s^%g" % (c, v) for c, v in sorted(d.items()))


def decouper_unite(unite):
    """Transforme FCFA/(km·an) en [(FCFA, 1), (km, -1), (an, -1)]."""
    unite = unite.strip()
    if not unite or unite == "sans unité":
        return []
    resultat, prochain, groupe = [], 1, None
    for jeton in re.findall(r"[^/*·() ]+|[/*·()]", unite):
        if jeton == "/":
            prochain = -1
        elif jeton == "(":
            groupe = prochain
        elif jeton == ")":
            groupe, prochain = None, 1
        elif jeton not in "*·":
            resultat.append((jeton, prochain if groupe is None else groupe))
            prochain = 1
    return resultat


def fraction_annees(debut, fin):
    """Durée en années, en suivant la longueur réelle de chaque année."""
    total, courant = 0.0, debut
    while courant < fin:
        suivant = min(fin, datetime.datetime(courant.year + 1, 1, 1))
        jours = 366 if calendar.isleap(courant.year) else 365
        total += (suivant - courant).total_seconds() / 86400 / jours
        courant = suivant
    return total


def construire_periodes(modele):
    """Construit la grille entre les dates de démarrage et de fin.

    Le pas multiplie le temps de référence. La date de fin est incluse ; si
    le dernier pas la dépasse, il est raccourci pour s'y arrêter.
    """
    sim = modele.simulation
    unite = modele.references_unites["Temps"]
    pas = float(sim["pas"].replace(",", "."))
    minuit = datetime.time()
    debut = datetime.datetime.combine(lire_date(sim["date_debut"]), minuit)
    fin = datetime.datetime.combine(lire_date(sim["date_fin"]), minuit) \
        + datetime.timedelta(days=1)
    mois = pas * {"an": 12, "mois": 1}.get(unite, 0)
    mois = int(round(mois)) if abs(mois - round(mois)) < 1e-9 else 0
    duree = datetime.timedelta(days=pas * ANNEES_PAR_UNITE[unite] * 365)
    sous_jour = not mois and duree % datetime.timedelta(days=1) \
        != datetime.timedelta(0)

    def jour(valeur):
        return valeur if sous_jour else valeur.date()

    def annee_decimale(date):
        civils = 366 if calendar.isleap(date.year) else 365
        return date.year + (date - datetime.datetime(date.year, 1, 1)
                            ).total_seconds() / 86400 / civils

    t0 = annee_decimale(debut) / ANNEES_PAR_UNITE[unite]
    periodes, courant, numero, ecoule, temps = [], debut, 0, 0.0, 0.0
    while courant < fin:
        numero += 1
        suivant = ajouter_mois(debut, mois * numero) if mois \
            else debut + duree * numero
        tronque = suivant > fin
        suivant = min(suivant, fin)
        jours = (suivant - courant).total_seconds() / 86400
        tau = mois / 12 if mois and mois % 12 == 0 and not tronque \
            else fraction_annees(courant, suivant)
        periodes.append({
            "rang": numero, "debut": jour(courant), "fin": jour(suivant),
            "jours": jours, "jours_annee": jours / tau, "tau": tau,
            "annee": courant.year, "tronque": tronque,
            "t": round(t0 + temps, 9), "t0": t0, "t_sim": round(temps, 9),
            "t[annee]": courant.year, "t[mois]": courant.month,
            "t[jour]": courant.day,
            "t_jour": (courant - debut).total_seconds() / 86400,
            "t_mois": round(ecoule * 12, 9), "t_an": round(ecoule, 9),
            "annee_decimale": annee_decimale(courant)})
        # Au démarrage, toutes les échelles de temps valent zéro.
        ecoule = numero * mois / 12 if mois and not tronque else ecoule + tau
        temps = numero * pas if not tronque else temps + (
            jours if unite in ("j", "jour") else tau / ANNEES_PAR_UNITE[unite])
        courant = suivant
    return periodes


def resoudre_lineaire(a, b):
    """Élimination de Gauss avec pivot. Retourne None si le système est singulier."""
    n = len(b)
    a = [ligne[:] + [valeur] for ligne, valeur in zip(a, b)]
    for i in range(n):
        pivot = max(range(i, n), key=lambda k: abs(a[k][i]))
        if abs(a[pivot][i]) < 1e-14:
            return None
        a[i], a[pivot] = a[pivot], a[i]
        for k in range(i + 1, n):
            rapport = a[k][i] / a[i][i]
            for j in range(i, n + 1):
                a[k][j] -= rapport * a[i][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (a[i][n] - sum(a[i][j] * x[j]
                              for j in range(i + 1, n))) / a[i][i]
    return x


class Simulateur:
    def __init__(self, modele):
        self.m = modele
        self.periodes = construire_periodes(modele)
        self.n = len(self.periodes)
        self.fiches = dict(modele.parametres)
        for i, q in modele.post.items():
            self.fiches[i] = {"mode": "formule", "expression": q["expression"],
                              "unite": q["unite"], "valeur_initiale": "0",
                              "conversion": False, "suivi": False}
        self.series = {}
        self.programmes = {}
        self.initiales = {}
        self.dependances = {}
        self.lead_utilise = False
        self.alertes_table = {}
        self.alertes_avant = set()
        self.progression = None
        self.ajustement = None
        self.formules_libres = {}
        self.index_portees = {}
        self.suivi = []
        self.iterations_max = int(modele.simulation["iterations_max"])
        self.cache_unites = {}
        self.courant = None
        self.taux = {}
        reference = modele.references_unites["Monnaie"]
        for i, p in self.fiches.items():
            self.initiales[i] = float(p["valeur_initiale"])
            self.series[i] = [self.initiales[i]] * self.n
            deps = set()
            if p["mode"] == "formule":
                arbre, _noms, noms = compiler_expression(
                    p["expression"], modele.structures, post=i in modele.post)
                self.programmes[i] = (arbre.body, noms)
                self.lire_dependances(arbre.body, noms, deps)
            elif p["variable_table"] not in VARIABLES_SYSTEME:
                deps.add(p["variable_table"])
            if not p.get("conversion"):
                for atome, _exposant in decouper_unite(p["unite"]):
                    devise = MONNAIES.get(atome, (None,))[0]
                    if devise and devise != reference:
                        deps.add(self.id_taux(devise, reference))
            self.dependances[i] = deps & set(self.fiches)
        self.groupes = self.composantes(modele.parametres)
        self.groupes_post = self.composantes(modele.post)

    @staticmethod
    def id_taux(devise, reference):
        return composer_id("taux_%s_%s" % (devise.lower(), reference.lower()),
                           "projet")

    def lire_dependances(self, noeud, noms, deps):
        """Dépendances dans la même période ; lag() n'en crée pas."""
        if isinstance(noeud, ast.Call):
            fonction = noeud.func.id
            if fonction == "lag":
                return
            if fonction.startswith(("somme_", "moyenne_")) \
                    and not fonction.endswith("_p") \
                    and len(noeud.args) == 2 and noeud.args[1].value > 0:
                return        # une période passée : aucune dépendance
            if fonction == "lead":
                self.lead_utilise = True
                return
            for argument in noeud.args:
                self.lire_dependances(argument, noms, deps)
            return
        if isinstance(noeud, ast.Name):
            if noeud.id in noms:
                deps.add(noms[noeud.id])
            return
        for enfant in ast.iter_child_nodes(noeud):
            self.lire_dependances(enfant, noms, deps)

    def composantes(self, variables):
        """Groupes de variables dans l'ordre de calcul (algorithme de Tarjan)."""
        indice, bas, pile, sur_pile, resultat = {}, {}, [], set(), []

        def visiter(v):
            indice[v] = bas[v] = len(indice)
            pile.append(v)
            sur_pile.add(v)
            for w in sorted(self.dependances[v] & set(variables)):
                if w not in indice:
                    visiter(w)
                    bas[v] = min(bas[v], bas[w])
                elif w in sur_pile:
                    bas[v] = min(bas[v], indice[w])
            if bas[v] == indice[v]:
                groupe = []
                while True:
                    w = pile.pop()
                    sur_pile.discard(w)
                    groupe.append(w)
                    if w == v:
                        break
                resultat.append(sorted(groupe))

        limite = sys.getrecursionlimit()
        sys.setrecursionlimit(max(limite, 2 * len(self.fiches) + 100))
        for v in sorted(variables):
            if v not in indice:
                visiter(v)
        sys.setrecursionlimit(limite)
        return resultat

    # ---------------- Unités ----------------
    def atome(self, nom, t):
        """Dimensions et facteur d'une unité simple à la période t."""
        if nom in ATOMES_FIXES:
            return ATOMES_FIXES[nom]
        jours_annee = self.periodes[min(max(t, 0),
                                        self.n - 1)]["jours_annee"]
        if nom in HEURES_PAR_UNITE:
            return {"T": 1}, HEURES_PAR_UNITE[nom] / (24 * jours_annee)
        if nom in PUISSANCES:
            return {"E": 1, "T": -1}, PUISSANCES[nom] * 24 * jours_annee
        if nom in MONNAIES:
            devise, multiple = MONNAIES[nom]
            reference = self.m.references_unites["Monnaie"]
            if devise == reference:
                return {"C": 1}, multiple
            taux = self.lire_variable(self.id_taux(devise, reference), t)
            return {"C": 1}, multiple * taux
        return {nom: 1}, 1

    def unite(self, texte, t):
        """Retourne (dimensions, facteur vers la base) ; dimensions None si vide."""
        if not texte.strip():
            return None, 1.0
        atomes = self.cache_unites.get(texte)
        if atomes is None:
            atomes = decouper_unite(texte)
            self.cache_unites[texte] = atomes
        dimensions, facteur = {}, 1.0
        for nom, exposant in atomes:
            d, f = self.atome(nom, t)
            dimensions = combiner(dimensions, d, exposant)
            facteur *= f ** exposant
        return dimensions, facteur

    def lire_grandeur(self, identifiant, t):
        fiche = self.fiches[identifiant]
        valeur = self.lire_variable(identifiant, t)
        if fiche.get("conversion"):
            return valeur, {}          # un taux de change est un rapport
        dimensions, facteur = self.unite(fiche["unite"], t)
        return valeur * facteur, dimensions

    def localiser(self):
        identifiant, t = self.courant
        return identifiant, self.periodes[t]["debut"].isoformat()

    def incompatibles(self, a, b):
        raise ErreurCalcul("%s, %s : unités incompatibles (%s et %s)." % (
            self.localiser() + (texte_dimensions(a), texte_dimensions(b))))

    def accorder(self, a, b):
        """Dimensions communes de deux grandeurs à additionner ou comparer."""
        va, da = a
        vb, db = b
        if da is None or db is None:
            return da if db is None else db
        if da == db:
            return da
        if vb == 0 and db == {}:
            return da
        if va == 0 and da == {}:
            return db
        return self.incompatibles(da, db)

    def sans_dimension(self, grandeur):
        if grandeur[1]:
            raise ErreurCalcul("%s, %s : argument sans dimension attendu."
                               % self.localiser())
        return grandeur[0]

    # ---------------- Évaluation ----------------
    def lire_variable(self, identifiant, t):
        if t < 0:
            return self.initiales[identifiant]
        return self.series[identifiant][min(t, self.n - 1)]

    def valeur_systeme(self, nom, t):
        periode = self.periodes[min(max(t, 0), self.n - 1)]
        if nom == "annee":
            return float(periode["annee"]), {}
        if nom == "t" or nom in TEMPS_MODELE or nom in TEMPS_FIXES:
            return float(periode[nom]), {}
        if nom.startswith("t_cal_"):
            return float(periode["t[%s]" % nom[6:]]), {}
        if nom == "jours_t":
            return periode["jours"] / periode["jours_annee"], {"T": 1}
        return periode["tau"], {"T": 1}

    def evaluer(self, noeud, noms, t):
        if isinstance(noeud, ast.Constant):
            if isinstance(noeud.value, str):       # type d'ouvrage, etc.
                return noeud.value, {}
            return float(noeud.value), {}
        if isinstance(noeud, ast.Name):
            if noeud.id in noms:
                return self.lire_grandeur(noms[noeud.id], t)
            return self.valeur_systeme(noeud.id, t)
        if isinstance(noeud, ast.BinOp):
            a = self.evaluer(noeud.left, noms, t)
            b = self.evaluer(noeud.right, noms, t)
            if isinstance(noeud.op, (ast.Add, ast.Sub)):
                dimensions = self.accorder(a, b)
                signe = 1 if isinstance(noeud.op, ast.Add) else -1
                return a[0] + signe * b[0], dimensions
            if isinstance(noeud.op, ast.Pow):
                exposant = self.sans_dimension(b)
                dimensions = None if a[1] is None else {
                    c: v * exposant for c, v in a[1].items()}
                return a[0] ** exposant, dimensions
            inconnue = a[1] is None or b[1] is None
            if isinstance(noeud.op, ast.Mult):
                return a[0] * b[0], None if inconnue \
                    else combiner(a[1], b[1])
            return a[0] / b[0], None if inconnue \
                else combiner(a[1], b[1], -1)
        if isinstance(noeud, ast.UnaryOp):
            valeur = self.evaluer(noeud.operand, noms, t)
            if isinstance(noeud.op, ast.USub):
                return -valeur[0], valeur[1]
            if isinstance(noeud.op, ast.Not):
                return float(not valeur[0]), {}
            return valeur
        if isinstance(noeud, ast.BoolOp):
            tests = (self.evaluer(v, noms, t)[0] for v in noeud.values)
            resultat = all(tests) if isinstance(noeud.op, ast.And) \
                else any(tests)
            return float(resultat), {}
        if isinstance(noeud, ast.Compare):
            gauche = self.evaluer(noeud.left, noms, t)
            for operateur, cote in zip(noeud.ops, noeud.comparators):
                droite = self.evaluer(cote, noms, t)
                self.accorder(gauche, droite)
                g, d = gauche[0], droite[0]
                if isinstance(operateur, ast.Lt):
                    vrai = g < d
                elif isinstance(operateur, ast.LtE):
                    vrai = g <= d
                elif isinstance(operateur, ast.Gt):
                    vrai = g > d
                elif isinstance(operateur, ast.GtE):
                    vrai = g >= d
                elif isinstance(operateur, ast.Eq):
                    vrai = g == d
                else:
                    vrai = g != d
                if not vrai:
                    return 0.0, {}
                gauche = droite
            return 1.0, {}
        return self.appeler(noeud, noms, t)

    def decalage(self, arguments, noms, t, nom):
        if not 1 <= len(arguments) <= 2:
            raise ErreurCalcul(nom + " attend (variable) ou (variable, n).")
        if len(arguments) == 1:
            return 1
        valeur = self.evaluer(arguments[1], noms, t)[0]
        if valeur != int(valeur) or valeur < 0:
            raise ErreurCalcul(nom + " : n doit être un entier positif.")
        return int(valeur)

    def suite(self, argument, noms):
        return [self.evaluer(argument, noms, s) for s in range(self.n)]

    def valeur_actuelle(self, valeurs, taux):
        origine = self.periodes[0]["debut"]
        total = 0.0
        for grandeur, periode in zip(valeurs, self.periodes):
            duree = (periode["fin"] - origine).total_seconds() / 31536000
            total += grandeur[0] / (1 + taux) ** duree
        return total

    def calculer_tri(self, valeurs):
        bas, haut = -0.99, 10.0
        va_bas = self.valeur_actuelle(valeurs, bas)
        va_haut = self.valeur_actuelle(valeurs, haut)
        if va_bas * va_haut > 0:
            raise ErreurCalcul("%s, %s : aucun TRI trouvé." % self.localiser())
        for _ in range(200):
            milieu = (bas + haut) / 2
            va = self.valeur_actuelle(valeurs, milieu)
            if va_bas * va > 0:
                bas, va_bas = milieu, va
            else:
                haut = milieu
        return (bas + haut) / 2

    def appeler(self, noeud, noms, t):
        f, args = noeud.func.id, noeud.args
        if f == "unite_lit":
            dimensions, facteur = self.unite(args[1].value, t)
            return float(args[0].value) * facteur, dimensions
        if f == "si":
            test = self.evaluer(args[0], noms, t)[0]
            return self.evaluer(args[1] if test else args[2], noms, t)
        if f == "lag":
            return self.evaluer(args[0], noms,
                                t - self.decalage(args, noms, t, f))
        if f == "lead":
            return self.evaluer(args[0], noms,
                                t + self.decalage(args, noms, t, f))
        if f in ("somme_p", "moyenne_p", "max_p", "min_p"):
            raise ErreurCalcul(f + " : remplissez la table des périmètres.")
        if f.startswith(("somme_", "moyenne_")):
            return self.agreger(f, args, noms, t)
        if f == "cumul":
            if len(args) != 1:
                raise ErreurCalcul("cumul attend une seule variable.")
            valeurs = [self.evaluer(args[0], noms, s) for s in range(t + 1)]
            return sum(v[0] for v in valeurs), valeurs[-1][1]
        if f in ("total", "moyenne", "minimum", "maximum"):
            valeurs = self.suite(args[0], noms)
            nombres = [v[0] for v in valeurs]
            dimensions = valeurs[0][1]
            if f == "total":
                return sum(nombres), dimensions
            if f == "moyenne":
                return sum(nombres) / len(nombres), dimensions
            return (min(nombres) if f == "minimum" else max(nombres)), \
                dimensions
        if f == "van":
            valeurs = self.suite(args[0], noms)
            taux = self.sans_dimension(self.evaluer(args[1], noms, t))
            return self.valeur_actuelle(valeurs, taux), valeurs[0][1]
        if f == "tri":
            return self.calculer_tri(self.suite(args[0], noms)), {}
        valeurs = [self.evaluer(a, noms, t) for a in args]
        if f in ("min", "max"):
            for autre in valeurs[1:]:
                self.accorder(valeurs[0], autre)
            choisie = (min if f == "min" else max)(
                valeurs, key=lambda v: v[0])
            dimensions = next((v[1] for v in valeurs if v[1]), choisie[1])
            return choisie[0], dimensions
        if f == "abs":
            return abs(valeurs[0][0]), valeurs[0][1]
        if f == "racine":
            d = valeurs[0][1]
            return math.sqrt(valeurs[0][0]), None if d is None else {
                c: v / 2 for c, v in d.items()}
        if f == "plancher":
            return float(math.floor(valeurs[0][0])), valeurs[0][1]
        if f == "plafond":
            return float(math.ceil(valeurs[0][0])), valeurs[0][1]
        if f == "arrondi":
            n = int(valeurs[1][0]) if len(valeurs) > 1 else 0
            return round(valeurs[0][0], n), valeurs[0][1]
        if f == "exp":
            return math.exp(self.sans_dimension(valeurs[0])), {}
        if f == "log":
            return math.log(self.sans_dimension(valeurs[0])), {}
        raise ErreurCalcul("Fonction non disponible : " + f)

    def agreger(self, fonction, args, noms, t):
        """Somme ou moyenne sur un jour, un mois ou une année du calendrier."""
        operation, portee = fonction.split("_")
        if self.periodes[t]["jours"] > JOURS_MAX_PORTEE[portee] + 1e-9:
            raise ErreurCalcul("%s demande un pas de temps d'au plus un %s."
                               % (fonction, portee))
        cible = self.rang_portee(portee, t) \
            - (args[1].value if len(args) == 2 else 0)
        rangs = [s for s in self.index_portee(portee).get(cible, ()) if s <= t]
        if not rangs:
            self.alertes_avant.add(fonction)
            rangs = [-1]          # avant le démarrage : valeur initiale
        valeurs = [self.evaluer(args[0], noms, s) for s in rangs]
        total = sum(v[0] for v in valeurs)
        if operation == "moyenne":
            total /= len(valeurs)
        return total, valeurs[-1][1]

    def rang_portee(self, portee, t):
        date = self.periodes[t]["debut"]
        if portee == "annee":
            return date.year
        if portee == "mois":
            return date.year * 12 + date.month
        return datetime.date(date.year, date.month, date.day).toordinal()

    def index_portee(self, portee):
        if portee not in self.index_portees:
            index = {}
            for s in range(self.n):
                index.setdefault(self.rang_portee(portee, s), []).append(s)
            self.index_portees[portee] = index
        return self.index_portees[portee]

    def lire_table(self, identifiant, t):
        p = self.fiches[identifiant]
        points = p["table"]
        if p["variable_table"] == VARIABLE_TEMPS:
            periode = self.periodes[t]
            x = periode["annee_decimale"]
            libelle = periode["debut"].isoformat()
        elif p["variable_table"] in VARIABLES_SYSTEME:
            x = float(self.periodes[t][p["variable_table"]])
            libelle = "%g" % x
        else:
            x = self.lire_variable(p["variable_table"], t)
            libelle = "%g" % x
        if x < points[0][0]:
            self.alertes_table.setdefault(identifiant, []).append(libelle)
            return points[0][1]
        if x > points[-1][0]:
            # La dernière ligne reste valable pendant l'année qu'elle désigne.
            couverte = p["variable_table"] == VARIABLE_TEMPS \
                and int(x) == int(points[-1][0])
            if not couverte:
                self.alertes_table.setdefault(identifiant, []).append(libelle)
            return points[-1][1]
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if x1 <= x < x2:
                if p["lecture_table"] == "paliers":
                    return y1
                return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
        return points[-1][1]

    @staticmethod
    def est_constante(noeud):
        if isinstance(noeud, ast.UnaryOp):
            noeud = noeud.operand
        return isinstance(noeud, ast.Constant)

    def affecter(self, identifiant, grandeur, t, constante):
        """Exprime un résultat dans l'unité du paramètre."""
        fiche = self.fiches[identifiant]
        valeur, obtenu = grandeur
        if fiche.get("conversion") or constante or not fiche["unite"].strip():
            return valeur
        attendu, facteur = self.unite(fiche["unite"], t)
        if obtenu is None or obtenu == attendu or valeur == 0:
            return valeur / facteur
        tau = self.periodes[t]["tau"]
        if combiner(obtenu, {"T": 1}) == attendu:    # débit vers quantité
            return valeur * tau / facteur
        if combiner(obtenu, {"T": 1}, -1) == attendu:  # quantité vers débit
            return valeur / tau / facteur
        raise ErreurCalcul("%s, %s : unité obtenue %s, unité attendue %s." % (
            self.localiser() + (texte_dimensions(obtenu),
                                texte_dimensions(attendu))))

    def calculer(self, identifiant, t):
        self.courant = (identifiant, t)
        try:
            if identifiant in self.programmes:
                arbre, noms = self.programmes[identifiant]
                valeur = self.affecter(identifiant,
                                       self.evaluer(arbre, noms, t), t,
                                       self.est_constante(arbre))
            else:
                valeur = self.lire_table(identifiant, t)
            if isinstance(valeur, complex):
                raise ValueError
            valeur = float(valeur)
            if self.ajustement and identifiant in self.ajustement["plafonds"]:
                valeur *= self.ajustement["coefficients"][t]
                plafond = self.ajustement["plafonds"][identifiant]
                if plafond is not None:
                    valeur = min(valeur, plafond)
            if math.isnan(valeur) or math.isinf(valeur):
                raise ValueError
            return valeur
        except ZeroDivisionError:
            raise ErreurCalcul("%s, %s : division par zéro." % (
                identifiant, self.periodes[t]["debut"].isoformat()))
        except (ValueError, OverflowError, TypeError):
            raise ErreurCalcul("%s, %s : calcul impossible." % (
                identifiant, self.periodes[t]["debut"].isoformat()))

    # ---------------- Résolution ----------------
    def balayer(self, groupe, t):
        """Un passage sur la boucle ; retourne les écarts obtenus."""
        ecarts = []
        for i in groupe:
            ancien = self.series[i][t]
            self.series[i][t] = self.calculer(i, t)
            ecarts.append(abs(self.series[i][t] - ancien))
        return ecarts

    def converge(self, groupe, ecarts):
        return all(e <= float(self.fiches[i]["convergence"])
                   for i, e in zip(groupe, ecarts))

    def noter(self, groupe, t, iteration, ecarts):
        for i, e in zip(groupe, ecarts):
            if self.fiches[i].get("suivi"):
                self.suivi.append({
                    "variable": i, "periode": self.periodes[t]["debut"],
                    "iteration": iteration, "valeur": self.series[i][t],
                    "ecart": e})

    def pas_newton(self, groupe, t, forcer=False):
        """Applique un pas de Newton à la boucle ; retourne (écarts, réussite).

        forcer : faire le pas même si le résidu est déjà sous le seuil
        (cas d'une convergence lente rejetée par la vérification finale).
        """
        x = [self.series[i][t] for i in groupe]
        ecarts = self.balayer(groupe, t)
        g = [self.series[i][t] for i in groupe]
        residu = [b - a for a, b in zip(x, g)]
        if not forcer and self.converge(groupe, [abs(r) for r in residu]):
            return ecarts, True
        n = len(groupe)
        jacobienne = [[0.0] * n for _ in range(n)]
        for j in range(n):
            pas = max(1e-6 * abs(x[j]), 1e-6)
            essai = list(x)
            essai[j] += pas
            for i, v in zip(groupe, essai):
                self.series[i][t] = v
            self.balayer(groupe, t)
            for k, i in enumerate(groupe):
                jacobienne[k][j] = (self.series[i][t] - g[k]) / pas
        for k in range(n):
            jacobienne[k][k] -= 1
        correction = resoudre_lineaire(jacobienne, [-r for r in residu])
        if correction is None:
            for i, v in zip(groupe, g):
                self.series[i][t] = v
            return ecarts, False
        for i, a, d in zip(groupe, x, correction):
            self.series[i][t] = a + d
        # En mode forcé, c'est la vérification finale qui tranche.
        return ecarts, forcer

    def verifier_boucle(self, groupe, t):
        """Vérification finale : distance estimée à la vraie solution.

        Deux passages de plus donnent e1 puis e2. Si la boucle converge au
        rythme r = e2 / e1, la solution est encore à environ e2 × r / (1 − r).
        Cette distance doit être sous la convergence de chaque variable.
        """
        e1 = self.balayer(groupe, t)
        e2 = self.balayer(groupe, t)
        distances = []
        for i, a, b in zip(groupe, e1, e2):
            seuil = float(self.fiches[i]["convergence"])
            if b <= seuil * 1e-6 or a <= 0:
                distances.append(b)
                continue
            rythme = b / a
            distances.append(math.inf if rythme >= 1
                             else max(b, b * rythme / (1 - rythme)))
        return self.converge(groupe, distances), distances

    def resoudre_boucle(self, groupe, t, bilan):
        """Itérations successives, puis Newton si elles divergent ou stagnent."""
        if t > 0:
            for i in groupe:
                self.series[i][t] = self.series[i][t - 1]
        depart = [self.series[i][t] for i in groupe]
        newton, historique, iteration = False, [], 0
        reussi, ecart, echec_verification = False, 0.0, False
        while iteration < self.iterations_max:
            iteration += 1
            if newton:
                ecarts, reussi = self.pas_newton(groupe, t, echec_verification)
            else:
                try:
                    ecarts = self.balayer(groupe, t)
                except ErreurCalcul:
                    if iteration == 1:
                        raise
                    historique = [math.inf] * 4
                    ecarts = [math.inf] * len(groupe)
                reussi = self.converge(groupe, ecarts)
            ecart = max(ecarts)
            self.noter(groupe, t, iteration, ecarts)
            if self.progression:
                self.progression("iteration", [
                    (i, e, float(self.fiches[i]["convergence"]))
                    for i, e in zip(groupe, ecarts)])
            if reussi:
                verifie, ecarts = self.verifier_boucle(groupe, t)
                ecart = max(ecarts)
                if self.progression:
                    self.progression("iteration", [
                        (i, e, float(self.fiches[i]["convergence"]))
                        for i, e in zip(groupe, ecarts)])
                if verifie:
                    break
                # Les itérations bougent peu mais la solution est encore
                # loin : on passe à Newton, depuis la valeur atteinte.
                reussi, echec_verification = False, True
                if not newton:
                    newton = True
                    bilan["newton"] = True
                continue
            if not newton:
                historique.append(ecart)
                diverge = len(historique) >= 4 and \
                    historique[-1] >= historique[-2] >= historique[-3]
                if diverge or iteration >= self.iterations_max // 2:
                    newton = True
                    bilan["newton"] = True
                    for i, v in zip(groupe, depart):
                        self.series[i][t] = v
        if not reussi:
            date = self.periodes[t]["debut"].isoformat()
            bilan["verification" if echec_verification
                  else "non_converge"].append(date)
        bilan["iterations"] = max(bilan["iterations"], iteration)
        bilan["ecart"] = max(bilan["ecart"], ecart)

    def lancer(self):
        boucles = [g for g in self.groupes
                   if len(g) > 1 or g[0] in self.dependances[g[0]]]
        bilans = {tuple(g): {"variables": g, "iterations": 0, "ecart": 0.0,
                             "non_converge": [], "verification": [],
                             "newton": False}
                  for g in boucles}
        erreurs = []
        try:
            for _passe in range(PASSES_MAX):
                precedent = {i: list(v) for i, v in self.series.items()}
                self.suivi = []
                for bilan in bilans.values():
                    bilan["non_converge"] = []
                    bilan["verification"] = []
                for t in range(self.n):
                    for groupe in self.groupes:
                        if tuple(groupe) in bilans:
                            self.resoudre_boucle(groupe, t,
                                                 bilans[tuple(groupe)])
                        else:
                            self.series[groupe[0]][t] = \
                                self.calculer(groupe[0], t)
                    if self.progression:
                        self.progression(
                            "pas", t + 1, self.n,
                            self.periodes[t]["debut"].strftime("%d/%m/%Y"))
                if not self.lead_utilise:
                    break
                variation = max(
                    (abs(a - b) / max(abs(a), 1.0)
                     for i in self.series
                     for a, b in zip(self.series[i], precedent[i])),
                    default=0.0)
                if variation < 1e-10:
                    break
            else:
                erreurs.append("lead() : pas de stabilisation après %d passes."
                               % PASSES_MAX)
            for groupe in ([] if self.ajustement
                           and self.ajustement.get("sans_post")
                           else self.groupes_post):
                if len(groupe) > 1 or groupe[0] in self.dependances[groupe[0]]:
                    raise ErreurCalcul("Boucle dans le post-traitement : "
                                       + " + ".join(groupe))
                for t in range(self.n):
                    self.series[groupe[0]][t] = self.calculer(groupe[0], t)
        except ErreurCalcul as erreur:
            erreurs.append(str(erreur))
        for bilan in bilans.values():
            if bilan["verification"]:
                erreurs.append("Vérification finale non satisfaite (%s) : %d "
                               "période(s), dont %s."
                               % (" + ".join(bilan["variables"]),
                                  len(bilan["verification"]),
                                  bilan["verification"][0]))
            if bilan["non_converge"]:
                erreurs.append("Boucle non convergée (%s) : %d période(s)."
                               % (" + ".join(bilan["variables"]),
                                  len(bilan["non_converge"])))
        return list(bilans.values()), erreurs

    def montant(self, identifiant, t):
        """Montant d'une variable dans la monnaie de référence, sur la période."""
        valeur, dimensions = self.lire_grandeur(identifiant, t)
        if dimensions == {"C": 1, "T": -1}:
            return valeur * self.periodes[t]["tau"]
        return valeur

    def calculer_paiements(self):
        """Du dû au payé : recouvrement, impayés, moratoire et rattrapage."""
        self.paiements = {}
        for i, f in self.m.flux.items():
            if f["nature"] != "Financier":
                continue
            reglages = f.get("paiement", PAIEMENT_DEFAUT)
            programmes = {}
            for cle in PAIEMENT_FORMULES:
                arbre, _noms, noms = compiler_expression(reglages[cle],
                                                         self.m.structures)
                programmes[cle] = (arbre.body, noms)

            def taux(cle, t, borne=True):
                corps, noms = programmes[cle]
                self.courant = (i, t)
                valeur = self.evaluer(corps, noms, t)[0]
                return min(1.0, max(0.0, valeur)) if borne else valeur

            debut = fin = ""
            if reglages["moratoire_debut"]:
                debut = lire_date(reglages["moratoire_debut"]).isoformat()
                fin = lire_date(reglages["moratoire_fin"]).isoformat()
            pas_reprise, repris = int(reglages["reprise_pas"]), 0
            impayes = moratoire = 0.0
            lignes = []
            for t, periode in enumerate(self.periodes):
                du = self.montant(i, t)
                date = periode["debut"].isoformat()[:10]
                actif = bool(debut) and debut <= date <= fin
                interet = moratoire * taux("taux_moratoire", t, False) \
                    * periode["tau"]
                suspendu = du * taux("part_suspendue", t) if actif else 0.0
                exigible = du - suspendu
                recouvre = exigible * taux("recouvrement", t)
                rattrapage = impayes * taux("rattrapage", t)
                abandon = (impayes - rattrapage) * taux("abandon", t)
                impayes += exigible - recouvre - rattrapage - abandon
                reprise = 0.0
                if not actif and moratoire + interet > 0:
                    reprise = (moratoire + interet) / max(
                        pas_reprise - repris, 1)
                    repris += 1
                moratoire += interet + suspendu - reprise
                lignes.append({
                    "du": du, "paye": recouvre + rattrapage + reprise,
                    "interet": interet, "abandon": abandon,
                    "stock": impayes + moratoire, "impayes": impayes,
                    "moratoire": moratoire})
            self.paiements[i] = lignes

    def evaluer_libre(self, texte, t, etiquette):
        """Évalue une formule hors du graphe de calcul."""
        if texte not in self.formules_libres:
            arbre, _noms, noms = compiler_expression(texte, self.m.structures)
            self.formules_libres[texte] = (arbre.body, noms)
        corps, noms = self.formules_libres[texte]
        self.courant = (etiquette, t)
        return self.evaluer(corps, noms, t)

    def montant_libre(self, texte, t, etiquette):
        valeur, dimensions = self.evaluer_libre(texte, t, etiquette)
        if dimensions == {"C": 1, "T": -1}:
            return valeur * self.periodes[t]["tau"]
        return valeur

    def paye(self, identifiant, t):
        return self.paiements[identifiant][t]["paye"]

    def soldes(self):
        """Recettes, charges et solde financier de chaque structure."""
        lignes = []
        for s in self.m.structures:
            cumul = 0.0
            for t, periode in enumerate(self.periodes):
                recettes = charges = 0.0
                for i, f in self.m.flux.items():
                    if f["nature"] != "Financier":
                        continue
                    if f["beneficiaire"] == s:
                        recettes += self.paye(i, t)
                    if f["payeur"] == s:
                        charges += self.paye(i, t)
                for i, c in self.m.charges.items():
                    if c["structure"] == s:
                        charges += self.montant(i, t)
                cumul += recettes - charges
                lignes.append({"structure": s, "periode": periode["debut"],
                               "recettes": recettes, "charges": charges,
                               "solde": recettes - charges, "cumul": cumul})
        return lignes


def calculer_comptes(sim):
    """Compte de chaque entité, à partir des flux et des postes."""
    m, lignes = sim.m, []
    for s in m.structures:
        postes = {}
        for i, c in m.postes.items():
            if c["structure"] == s:
                postes.setdefault(c["categorie"], []).append(i)

        def somme(categorie, t):
            return sum(sim.montant(i, t) for i in postes.get(categorie, ()))

        resultat_cumule = distribue = apports = mouvements = 0.0
        participations = position_dette = 0.0
        provision_avant = 0.0
        for t, periode in enumerate(sim.periodes):
            recettes = charges = autres = 0.0
            a_recevoir = a_payer = 0.0
            mouvements_avant = mouvements
            service_dette = 0.0
            detail = dict.fromkeys(DETAIL_ARGENT, 0.0)
            for i, f in m.flux.items():
                if f["nature"] != "Financier" \
                        or s not in (f["payeur"], f["beneficiaire"]):
                    continue
                recoit = f["beneficiaire"] == s
                ligne = sim.paiements[i][t]
                du, paye = ligne["du"], ligne["paye"]
                mouvements += paye if recoit else -paye
                detail[CLASSEMENT_FLUX[f["compte"]][0 if recoit else 1]] += paye
                if recoit:
                    a_recevoir += ligne["stock"]
                    autres += ligne["interet"] - ligne["abandon"]
                else:
                    a_payer += ligne["stock"]
                    autres += ligne["abandon"] - ligne["interet"]
                if f["compte"] == "Résultat":
                    if recoit:
                        recettes += du
                    else:
                        charges += du
                elif f["compte"] == "Capital":
                    if recoit:
                        apports += du
                    else:
                        participations += du
                elif f["compte"] == "Dividende":
                    if recoit:
                        recettes += du
                    else:
                        distribue += du
                elif f["compte"] == "Dette":
                    position_dette += du if recoit else -du
                    if not recoit and position_dette >= 0:
                        service_dette += du
            for i, c in m.charges.items():
                if c["structure"] == s:
                    montant = sim.montant(i, t)
                    mouvements -= montant
                    detail["charges_payees" if c["compte"] == "Résultat"
                           else "investissements"] += montant
                    if c["compte"] == "Résultat":
                        charges += montant
            amortissement = somme("Amortissement", t)
            provisions = somme("Provision", t)
            dotation = provisions - provision_avant
            provision_avant = provisions
            charges_dues = charges
            charges += amortissement + dotation
            resultat = recettes - charges + autres
            resultat_cumule += resultat
            capital = somme("Capital", t) + apports
            creances = somme("Créance", t)
            fournisseurs = somme("Dette fournisseur", t)
            tresorerie = somme("Trésorerie initiale", 0) + mouvements \
                - creances + fournisseurs
            prets = max(-position_dette, 0.0)
            actifs = somme("Actif", t) + participations + prets
            dettes = somme("Dette", t) if "Dette" in postes \
                else max(position_dette, 0.0)
            reserves = somme("Réserve", t)
            fonds_propres = capital + resultat_cumule - distribue
            ecart = actifs + creances + a_recevoir + tresorerie \
                - fonds_propres - dettes - fournisseurs - a_payer - provisions
            entrees = sum(detail[k] for k in DETAIL_ENTREES)
            lignes.append({
                "structure": s, "periode": periode["debut"], **detail,
                "entrees": entrees,
                "sorties": entrees - (mouvements - mouvements_avant),
                "amortissements": amortissement, "dotations": dotation,
                "charges_dues": charges_dues, "autres_resultat": autres,
                "service_dette": service_dette,
                "impayes_a_recevoir": a_recevoir, "impayes_a_payer": a_payer,
                "capital": capital, "tresorerie": tresorerie,
                "recettes": recettes, "charges": charges,
                "resultat": resultat, "solde": mouvements - mouvements_avant,
                "fonds_propres": fonds_propres,
                "actifs": actifs, "creances": creances, "dettes": dettes,
                "dettes_fournisseurs": fournisseurs, "reserves": reserves,
                "provisions": provisions, "garanties": somme("Garantie", t),
                "ecart_bilan": ecart})
    return lignes


# ------------------------- Optimisation des tarifs -------------------------
OPTIONS_TARIFS = ("actuels", "maintien", "financement")
LIBELLES_OPTIONS = {"actuels": "Tarifs actuels",
                    "maintien": "Maintien du service",
                    "financement": "Financement des investissements"}
COEFFICIENT_MAX = 100.0
ESSAIS_BISSECTION = 40


def nombre_option(texte, defaut=None):
    texte = (texte or "").strip().replace(",", ".")
    return float(texte) if texte else defaut


def regler_tarifs(modele):
    """Lit les réglages ; retourne (tarifs optimisables, réglages)."""
    tarifs = {i: nombre_option(p.get("tarif_max", ""))
              for i, p in modele.parametres.items() if p.get("optimisable")}
    sim = modele.simulation
    choisies = [s for s in sim.get("structures_equilibre", "").split(",")
                if s.strip() in modele.structures]
    if not choisies:
        choisies = [s for s, f in modele.structures.items()
                    if f["type"] != "Usager"]
    reglages = {
        "structures": [s.strip() for s in choisies],
        "hausse_max": nombre_option(sim.get("hausse_max")),
        "tri_cible": nombre_option(sim.get("tri_cible")),
        "structure_tri": sim.get("structure_tri", ""),
        "tresorerie_min": nombre_option(sim.get("tresorerie_min")),
    }
    return tarifs, reglages


def lancer_avec(modele, tarifs, coefficients_annee, annees, progression,
                recherche=True):
    """Simule avec un coefficient par année appliqué aux tarifs optimisables."""
    periodes = construire_periodes(modele)
    rang = {a: n for n, a in enumerate(annees)}
    coefficients = [coefficients_annee[rang[p["debut"].year]]
                    for p in periodes]
    # Pendant la recherche, le post-traitement n'est pas calculé : un
    # indicateur sans valeur pour un essai ne doit pas l'interrompre.
    return simuler(modele, progression,
                   {"coefficients": coefficients, "plafonds": tarifs,
                    "sans_post": recherche})


def comptes_par(resultat):
    sortie = {}
    for c in resultat["comptes"]:
        sortie.setdefault(c["structure"], []).append(c)
    return sortie


def plus_petit(possible, haut):
    """Plus petit coefficient dans [0, haut] qui respecte les contraintes."""
    if possible(0.0):
        return 0.0
    bas = 0.0
    for _ in range(ESSAIS_BISSECTION):
        milieu = (bas + haut) / 2
        if possible(milieu):
            haut = milieu
        else:
            bas = milieu
        if haut - bas < 1e-7 * max(haut, 1.0):
            break
    return haut


def optimiser_maintien(modele, tarifs, reglages, annees, progression):
    """Chaque année, les recettes encaissées couvrent les charges payées."""
    coefficients, messages = [], []
    hausse = reglages["hausse_max"]
    for n, annee in enumerate(annees):
        precedent = coefficients[-1] if coefficients else 1.0
        haut = COEFFICIENT_MAX if hausse is None else precedent * (1 + hausse)
        dernier = {}

        def ecarts(k):
            essai = coefficients + [k] * (len(annees) - n)
            resultat = lancer_avec(modele, tarifs, essai, annees, progression)
            if resultat["erreurs"]:
                raise ErreurCalcul(resultat["erreurs"][0])
            sortie = {}
            for s, lignes in comptes_par(resultat).items():
                if s in reglages["structures"]:
                    sortie[s] = sum(c["recettes_encaissees"]
                                    - c["charges_payees"] for c in lignes
                                    if c["periode"].year == annee)
            dernier["ecarts"] = sortie
            return sortie

        def possible(k):
            return all(v >= -1e-6 for v in ecarts(k).values())

        if possible(haut):
            coefficients.append(plus_petit(possible, haut))
        else:
            ecarts(haut)
            pire = min(dernier["ecarts"].items(), key=lambda e: e[1])
            limite = "hausse maximale par an" if hausse is not None \
                else "tarif maximal ou tarif sans effet"
            messages.append("%d : équilibre impossible pour %s (écart %.6g), "
                            "contrainte limitante : %s."
                            % (annee, pire[0], pire[1], limite))
            coefficients.append(haut)
    return coefficients, messages


def chemin_financement(cible, nombre, hausse):
    """Tarif unique, atteint progressivement si la hausse est plafonnée."""
    if hausse is None or cible <= 1:
        return [cible] * nombre
    return [min(cible, (1 + hausse) ** (n + 1)) for n in range(nombre)]


def optimiser_financement(modele, tarifs, reglages, annees, progression):
    """À la fin, les entrées couvrent toutes les sorties ; TRI cible atteint."""
    dernier = {}

    def manques(k):
        resultat = lancer_avec(
            modele, tarifs,
            chemin_financement(k, len(annees), reglages["hausse_max"]),
            annees, progression)
        if resultat["erreurs"]:
            raise ErreurCalcul(resultat["erreurs"][0])
        sortie = []
        comptes = comptes_par(resultat)
        for s in reglages["structures"]:
            lignes = comptes.get(s, [])
            total = sum(c["solde"] for c in lignes)
            if total < -1e-6:
                sortie.append("%s : entrées moins sorties %.6g" % (s, total))
            minimum = reglages["tresorerie_min"]
            if minimum is not None and lignes \
                    and min(c["tresorerie"] for c in lignes) < minimum:
                sortie.append("%s : trésorerie minimale" % s)
        cible, structure = reglages["tri_cible"], reglages["structure_tri"]
        if cible is not None and structure in comptes:
            soldes = [(c["solde"], {}) for c in comptes[structure]]
            if any(v[0] < 0 for v in soldes):
                try:
                    tri = resultat["simulateur"].calculer_tri(soldes)
                except ErreurCalcul:
                    tri = -1.0
                if tri < cible - 1e-7:
                    sortie.append("%s : TRI %.4g %% sous la cible"
                                  % (structure, 100 * tri))
        dernier["manques"] = sortie
        return sortie

    def possible(k):
        return not manques(k)

    if possible(COEFFICIENT_MAX):
        cible = plus_petit(possible, COEFFICIENT_MAX)
        return chemin_financement(cible, len(annees),
                                  reglages["hausse_max"]), []
    message = "Financement impossible même avec un tarif multiplié par %g : " \
        % COEFFICIENT_MAX + " ; ".join(dernier["manques"])
    return chemin_financement(COEFFICIENT_MAX, len(annees),
                              reglages["hausse_max"]), [message]


def simuler_tarifs(modele, progression=None):
    """Simule l'option choisie et compare les trois options de tarifs."""
    tarifs, reglages = regler_tarifs(modele)
    options = [o for o in OPTIONS_TARIFS if o in str(
        modele.simulation.get("option_tarifs", "actuels")).split(",")] \
        or ["actuels"]
    choix = modele.simulation.get("option_principale") or options[0]
    if choix not in options:
        choix = options[0]
    if not tarifs or modele.verifier()[0]:
        return simuler(modele, progression)
    annees = sorted({p["debut"].year for p in construire_periodes(modele)})
    comparaison, principal, scenarios = {}, None, {}
    for option in options:
        messages = []
        try:
            if option == "actuels":
                coefficients = [1.0] * len(annees)
            elif option == "maintien":
                coefficients, messages = optimiser_maintien(
                    modele, tarifs, reglages, annees, progression)
            else:
                coefficients, messages = optimiser_financement(
                    modele, tarifs, reglages, annees, progression)
        except ErreurCalcul as erreur:
            if str(erreur) == "Simulation arrêtée.":
                return {"statut": "non valide", "erreurs": [str(erreur)],
                        "alertes": [], "convergence": [], "periodes": [],
                        "series": {}, "soldes": [], "comptes": [],
                        "montants": {}, "dus": {}, "suivi": [],
                        "modele": modele, "unites": {}}
            coefficients, messages = [1.0] * len(annees), [str(erreur)]
        resultat = lancer_avec(
            modele, tarifs if option != "actuels" else dict.fromkeys(tarifs),
            coefficients, annees, progression, recherche=False)
        comparaison[option] = {
            "coefficients": coefficients, "messages": messages,
            "series": {i: serie_tarif(resultat, i) for i in tarifs}}
        scenarios[option] = resultat
        if option == choix:
            principal = resultat
    principal["scenarios"] = scenarios      # résultats complets par option
    principal["tarifs"] = {"annees": annees, "options": comparaison,
                           "choix": choix, "reglages": reglages,
                           "unites": {i: modele.parametres[i]["unite"]
                                      for i in tarifs}}
    for message in comparaison[choix]["messages"]:
        principal["erreurs"].append("%s : %s" % (
            T(LIBELLES_OPTIONS[choix]), message))
    if principal["erreurs"]:
        principal["statut"] = "non valide"
    return principal


def serie_tarif(resultat, identifiant):
    """Série d'un tarif ; pour un tarif par périmètre, la moyenne des p."""
    if identifiant in resultat["series"]:
        return list(resultat["series"][identifiant])
    dev = getattr(resultat["modele"], "developpement", {})
    instances = [resultat["series"][i] for i in
                 dev.get("indexes", {}).get(identifiant, [])
                 if i in resultat["series"]]
    if not instances:
        return [0.0] * len(resultat["periodes"])
    return [sum(v) / len(instances) for v in zip(*instances)]


def tarifs_resultat(resultat, _annee=None):
    """Vue Tarifs : moyenne annuelle de chaque tarif selon chaque option."""
    donnees = resultat.get("tarifs")
    if not donnees:
        return [], [(T("Aucun tarif n'est marqué optimisable."), "titre", [])]
    options = [o for o in OPTIONS_TARIFS if o in donnees["options"]]
    colonnes = [T(LIBELLES_OPTIONS[o]) for o in options] + [
        T("Écart %s (%%)" % LIBELLES_COURTS[o]) for o in options[1:]]
    annee_de = [p["debut"].year for p in resultat["periodes"]]
    lignes = []
    for i, unite in donnees["unites"].items():
        lignes.append(("%s (%s)" % (i, unite), "titre", []))
        for annee in donnees["annees"]:
            rangs = [r for r, a in enumerate(annee_de) if a == annee]
            valeurs = []
            for o in options:
                serie = donnees["options"][o]["series"][i]
                valeurs.append(sum(serie[r] for r in rangs) / len(rangs))
            base = valeurs[0]
            valeurs += [rapport(v - base, base, 100) for v in valeurs[1:]]
            lignes.append((str(annee), "tarif", valeurs))
    lignes.append((T("Résultat de l'optimisation"), "titre", []))
    for o in options:
        messages = donnees["options"][o]["messages"]
        lignes.append((T(LIBELLES_OPTIONS[o]) + " : " + (
            T("réussie") if not messages else "; ".join(messages)),
            "detail", []))
    return colonnes, lignes


LIBELLES_COURTS = {"actuels": "actuels", "maintien": "maintien",
                   "financement": "financement"}


def calculer_capacites(sim, comptes):
    """Capacité d'investissement de chaque structure, à chaque pas."""
    par_structure = {}
    for ligne in comptes:
        par_structure.setdefault(ligne["structure"], []).append(ligne)
        ligne["caf"] = ligne["resultat"] + ligne["amortissements"] \
            + ligne["dotations"]
    for s, lignes in par_structure.items():
        reglages = sim.m.structures[s].get("capacite")
        if not reglages:
            continue
        etiquette = "capacite[%s]" % s
        for t, ligne in enumerate(lignes):
            tau = sim.periodes[t]["tau"]
            couverture = sim.evaluer_libre(reglages["couverture"], t,
                                           etiquette)[0]
            taux = sim.evaluer_libre(reglages["taux"], t, etiquette)[0]
            duree = sim.evaluer_libre(reglages["duree"], t, etiquette)[0]
            if couverture <= 0 or duree <= 0 or taux <= -1:
                raise ErreurCalcul("%s : couverture, taux ou durée incorrects."
                                   % s)
            minimum = sim.montant_libre(reglages["tresorerie_minimale"], t,
                                        etiquette)
            facteur = duree if taux == 0 \
                else (1 - (1 + taux) ** -duree) / taux
            # La CAF et le service de la dette sont ramenés à l'année.
            annuite = ligne["caf"] / tau / couverture \
                - ligne["service_dette"] / tau
            mobilisables = ligne["tresorerie"] - minimum
            emprunt = max(annuite, 0.0) * facteur
            capacite = mobilisables + emprunt
            besoin = sim.montant_libre(reglages["besoin"], t, etiquette)
            ligne.update({
                "fonds_mobilisables": mobilisables,
                "annuite_supportable": annuite, "capacite_emprunt": emprunt,
                "capacite_investissement": capacite,
                "besoin_investissement": besoin,
                "marge_investissement": capacite - besoin})


def simuler(modele, progression=None, ajustement=None):
    """Lance la simulation et retourne un dictionnaire de résultats.

    progression(genre, ...) reçoit l'avancement : "pas" (rang, total) et
    "iteration" [(variable, écart, convergence)]. Elle peut lever ErreurCalcul pour arrêter.
    """
    source = modele
    if modele.a_developper():
        try:
            modele = modele.developper()
        except ErreurModele as erreur:
            return {"statut": "non valide", "erreurs": [str(erreur)],
                    "alertes": [], "convergence": [], "periodes": [],
                    "series": {}, "soldes": [], "comptes": [],
                    "montants": {}, "dus": {}, "suivi": [],
                    "modele": source, "source": source, "unites": {}}
        if ajustement:
            plafonds = {}
            for i, plafond in ajustement["plafonds"].items():
                for instance in modele.developpement["indexes"].get(i, [i]):
                    plafonds[instance] = plafond
            ajustement = dict(ajustement, plafonds=plafonds)
    erreurs_modele, alertes = modele.verifier()
    if erreurs_modele:
        return {"statut": "non valide", "erreurs": erreurs_modele,
                "alertes": alertes, "convergence": [], "periodes": [],
                "series": {}, "soldes": [], "comptes": [], "montants": {},
                "dus": {},
                "suivi": [],
                "modele": modele, "source": source, "unites": {}}
    simulateur = Simulateur(modele)
    simulateur.progression = progression
    simulateur.ajustement = ajustement
    convergence, erreurs = simulateur.lancer()
    alertes = [a for a in alertes if "ne couvre pas" not in a]
    for fonction in sorted(simulateur.alertes_avant):
        alertes.append("%s : période antérieure au démarrage, valeur initiale "
                       "utilisée." % fonction)
    for identifiant, valeurs in sorted(simulateur.alertes_table.items()):
        alertes.append(
            "%s : hors de la table pour %d valeur(s), de %s à %s ; valeur "
            "connue la plus proche gardée."
            % (identifiant, len(set(valeurs)), min(valeurs), max(valeurs)))
    if not erreurs and simulateur.periodes[-1]["tronque"]:
        alertes.append("Dernier pas raccourci pour finir à la date de fin.")
    if not erreurs:
        try:
            simulateur.calculer_paiements()
        except ErreurCalcul as erreur:
            erreurs = erreurs + [str(erreur)]
    soldes = [] if erreurs else simulateur.soldes()
    comptes = [] if erreurs else calculer_comptes(simulateur)
    if not erreurs:
        try:
            calculer_capacites(simulateur, comptes)
        except ErreurCalcul as erreur:
            erreurs = erreurs + [str(erreur)]
    montants = {} if erreurs else {
        i: [ligne["paye"] for ligne in lignes]
        for i, lignes in simulateur.paiements.items()}
    dus = {} if erreurs else {
        i: [ligne["du"] for ligne in lignes]
        for i, lignes in simulateur.paiements.items()}
    if not erreurs:
        for i in list(modele.charges) + list(modele.postes):
            montants[i] = [simulateur.montant(i, t)
                           for t in range(simulateur.n)]
    tolerance = 1.0
    desequilibres = {}
    for ligne in comptes:
        if abs(ligne["ecart_bilan"]) > tolerance:
            desequilibres.setdefault(ligne["structure"], ligne["ecart_bilan"])
    for structure, ecart in sorted(desequilibres.items()):
        alertes.append("%s : bilan non équilibré, premier écart %.6g."
                       % (structure, ecart))
    statut = "non valide" if erreurs else (
        "valide avec alertes" if alertes else "valide")
    return {"statut": statut, "erreurs": erreurs, "alertes": alertes,
            "convergence": convergence, "periodes": simulateur.periodes,
            "series": simulateur.series, "soldes": soldes,
            "comptes": comptes, "montants": montants, "dus": dus,
            "simulateur": simulateur,
            "suivi": simulateur.suivi, "modele": modele, "source": source,
            "par_p": [] if erreurs else repartir_perimetres(simulateur,
                                                              montants, dus),
            "unites": {i: f["unite"] for i, f in simulateur.fiches.items()}}


def repartir_perimetres(sim, montants, dus):
    """Montants dus et payés de chaque flux ou charge, par périmètre.

    Un flux dont la formule utilise p a un détail par périmètre ; le payé
    est réparti comme le dû. Les autres vont dans « non réparti ».
    """
    developpement = getattr(sim.m, "developpement", None) \
        or {"details": {}, "perimetres": []}
    details = developpement["details"]
    sortie = {"dus": {}, "payes": {}}
    for i in list(sim.m.flux) + list(sim.m.charges):
        if i not in montants:
            continue
        total_du = dus.get(i, montants[i])
        payes = montants[i]
        par_p_dus, par_p_payes = {}, {}
        if i in details:
            for instance, pid in zip(details[i],
                                     developpement["perimetres"]):
                du_p = [sim.montant(instance, t) for t in range(sim.n)]
                par_p_dus[pid] = du_p
                par_p_payes[pid] = [payes[t] * d / total_du[t]
                                    if total_du[t] else 0.0
                                    for t, d in enumerate(du_p)]
        else:
            par_p_dus[NON_REPARTI] = list(total_du)
            par_p_payes[NON_REPARTI] = list(payes)
        sortie["dus"][i], sortie["payes"][i] = par_p_dus, par_p_payes
    return sortie


NON_REPARTI = "_non_reparti"


GLOBAL = "Global"


def niveaux_perimetres(resultat):
    """Regroupements possibles : global, « p », puis chaque colonne."""
    developpement = getattr(resultat["modele"], "developpement", None)
    if not developpement or not developpement["perimetres"]:
        return [GLOBAL]
    return [GLOBAL, "p"] + developpement["colonnes"]


def colonnes_perimetres(resultat, niveau):
    """(libellés, {périmètre: libellé}) pour regrouper les périmètres."""
    dev = getattr(resultat["modele"], "developpement", None) \
        or {"perimetres": [], "noms": {}, "table": []}
    if niveau == GLOBAL:
        return [T(GLOBAL)], {p: T(GLOBAL) for p in dev["perimetres"]}
    if niveau == "p":
        correspondance = {p: dev["noms"][p] for p in dev["perimetres"]}
    else:
        correspondance = {}
        for ligne in dev["table"]:
            valeur = ligne["groupes"].get(niveau, "") or T("Sans groupe")
            correspondance[creer_id(ligne["nom"])] = valeur
    libelles = list(dict.fromkeys(correspondance.values()))
    return libelles, correspondance


def perimetres_resultat(resultat, annee=None, niveau=GLOBAL):
    """Vue Périmètres : les montants de chaque structure, par périmètre.

    Le niveau « Global » donne le projet entier, avec ou sans périmètres.
    """
    m = resultat["modele"]
    if not resultat.get("par_p"):
        return [], [(T("Lancez d'abord la simulation dans l'onglet 6."),
                     "titre", [])]
    if niveau not in niveaux_perimetres(resultat):
        niveau = GLOBAL
    libelles, correspondance = colonnes_perimetres(resultat, niveau)
    globale = niveau == GLOBAL
    colonnes = libelles if globale else \
        libelles + [T("Non réparti"), T("Total")]
    rangs = [r for r, p in enumerate(resultat["periodes"])
             if dans_periode(p, annee)]

    def vide():
        return dict.fromkeys(colonnes, 0.0)

    def ajouter(cumul, table, identifiant, signe=1):
        for pid, serie in resultat["par_p"][table][identifiant].items():
            if globale:
                colonne = T(GLOBAL)
            else:
                colonne = T("Non réparti") if pid == NON_REPARTI \
                    else correspondance[pid]
            valeur = signe * sum(serie[r] for r in rangs)
            cumul[colonne] += valeur
            if not globale:
                cumul[T("Total")] += valeur

    lignes = []
    for s, fiche in m.structures.items():
        natures = {k: vide() for k in ("dus", "encaisses", "charges",
                                       "invest", "solde")}
        for i, f in m.flux.items():
            if f["nature"] != "Financier" or i not in resultat["par_p"]["dus"]:
                continue
            if f["beneficiaire"] == s:
                if f["compte"] == "Résultat":
                    ajouter(natures["dus"], "dus", i)
                    ajouter(natures["encaisses"], "payes", i)
                ajouter(natures["solde"], "payes", i)
            if f["payeur"] == s:
                ajouter(natures["charges"] if f["compte"] == "Résultat"
                        else natures["invest"], "payes", i)
                ajouter(natures["solde"], "payes", i, -1)
        for i, c in m.charges.items():
            if c["structure"] == s and i in resultat["par_p"]["payes"]:
                ajouter(natures["charges"] if c["compte"] == "Résultat"
                        else natures["invest"], "payes", i)
                ajouter(natures["solde"], "payes", i, -1)
        if not any(any(v.values()) for v in natures.values()):
            continue
        lignes.append((fiche["nom"], "titre", []))
        for cle, libelle, genre in (
                ("dus", "Recettes dues", "ligne"),
                ("encaisses", "Recettes encaissées", "ligne"),
                ("charges", "Charges payées", "ligne"),
                ("invest", "Investissements", "ligne"),
                ("solde", "Entrées moins sorties", "total")):
            lignes.append((T(libelle), genre,
                           [natures[cle][c] for c in colonnes]))
    grandeurs = []
    indexes = getattr(m, "developpement", {}).get("indexes", {})
    for i, instances in indexes.items():
        unite = m.parametres[instances[0]]["unite"]
        par_colonne = {c: [] for c in colonnes}
        for instance, pid in zip(instances, m.developpement["perimetres"]):
            if instance not in resultat["series"]:
                continue
            total, affichee = quantite_physique(resultat, instance, rangs)
            if not est_additive(unite):
                total = sum(resultat["series"][instance][r]
                            for r in rangs) / len(rangs)
                affichee = unite
            par_colonne[correspondance[pid]].append(total)
            if not globale:
                par_colonne[T("Total")].append(total)
        additive = est_additive(unite)
        grandeurs.append(("%s (%s)" % (i, affichee if additive else unite),
                          "ligne", [
            None if not v else sum(v) if additive else sum(v) / len(v)
            for v in (par_colonne[c] for c in colonnes)]))
    if grandeurs:
        lignes.append((T("Variables par périmètre"), "titre", []))
        lignes += grandeurs
    return colonnes, lignes


def est_additive(unite):
    """Une quantité, un débit ou un montant s'additionne ; un prix non."""
    atomes = decouper_unite(unite) if unite.strip() else []
    if not atomes:
        return False
    if any(e < 0 for _a, e in atomes):
        return atomes[-1][0] in ANNEES_PAR_UNITE    # débit : par unité de temps
    return True


def flux_filtres(resultat, texte):
    """Montants payés et dus limités à un périmètre ou à un groupe."""
    membres = set(resultat["source"].membres(texte))
    payes, dus = {}, {}
    n = len(resultat["periodes"])
    for i in resultat["par_p"]["payes"]:
        payes[i], dus[i] = [0.0] * n, [0.0] * n
        for pid, serie in resultat["par_p"]["payes"][i].items():
            if pid in membres:
                payes[i] = [a + b for a, b in zip(payes[i], serie)]
                dus[i] = [a + b for a, b in zip(
                    dus[i], resultat["par_p"]["dus"][i][pid])]
    return payes, dus


def resumer_suivi(resultat):
    """Une ligne par variable suivie et par période."""
    derniers = {}
    for ligne in resultat["suivi"]:
        derniers[(ligne["variable"], ligne["periode"])] = ligne
    lignes = ["%s, %s : %d itération(s), écart %.3g" % (
        v, p.isoformat(), d["iteration"], d["ecart"])
        for (v, p), d in sorted(derniers.items())]
    suivies = {v for v, _p in derniers}
    for i, fiche in sorted(resultat["modele"].parametres.items()):
        if fiche["suivi"] and i not in suivies:
            lignes.append("%s : calcul direct, sans itération." % i)
    return lignes


# ---------------------------- Étape 9 : résultats ----------------------------
def echelles_temps(modele):
    reference = modele.references_unites["Temps"]
    return [(nom, reference) for nom in ("t",) + TEMPS_MODELE] \
        + list(TEMPS_FIXES.items())


def groupe_courbe(modele, identifiant):
    """« usagers » ou « usagers / Dakar » pour une variable par périmètre."""
    structure = identifiant.rsplit("[", 1)[-1].rstrip("]")
    if "," not in structure:
        return structure
    structure, pid = structure.split(",", 1)
    noms = getattr(modele, "developpement", {}).get("noms", {})
    return "%s / %s" % (structure, noms.get(pid, pid))


def tables_resultat(resultat):
    """Rassemble toutes les séries : clé -> (groupe, libellé, unité, valeurs)."""
    m = resultat["modele"]
    tables = {}
    for cle, unite in echelles_temps(m):
        tables[cle] = ("Temps", cle, unite, [float(p[cle])
                                             for p in resultat["periodes"]])
    for ensemble in (m.parametres, m.post):
        for i in sorted(ensemble):
            if i in resultat["series"]:
                tables[i] = (groupe_courbe(m, i), i,
                             resultat["unites"].get(i, "")
                             or ensemble[i].get("unite", ""),
                             list(resultat["series"][i]))
    if resultat.get("tarifs"):
        for option, donnees in resultat["tarifs"]["options"].items():
            for i, serie in donnees["series"].items():
                tables["tarif:%s:%s" % (option, i)] = (
                    "Tarifs", "%s (%s)" % (i, T(LIBELLES_OPTIONS[option])),
                    resultat["tarifs"]["unites"][i], list(serie))
    monnaie = m.references_unites["Monnaie"]
    for ligne in resultat["comptes"]:
        for colonne, libelle in COMPTES_AFFICHES:
            cle = "compte:%s:%s" % (ligne["structure"], colonne)
            if colonne not in ligne:
                continue
            if cle not in tables:
                tables[cle] = (ligne["structure"], T(libelle) + " ["
                               + ligne["structure"] + "]", monnaie, [])
            tables[cle][3].append(float(ligne[colonne]))
    return tables


def en_tete_colonne(table):
    return "%s (%s)" % (table[1], table[2]) if table[2] else table[1]


def exporter_table(resultat, cles, chemin):
    """Écrit les séries en colonnes : .csv pour un tableur, .dat sinon."""
    tables = tables_resultat(resultat)
    cles = [c for c in cles if c in tables] or list(tables)
    csv = chemin.lower().endswith(".csv")
    separateur = ";" if csv else "\t"

    def nombre(valeur):
        texte = repr(float(valeur))
        return texte.replace(".", ",") if csv else texte

    lignes = [separateur.join([T("Date")] + [en_tete_colonne(tables[c])
                                             for c in cles])]
    for rang, periode in enumerate(resultat["periodes"]):
        lignes.append(separateur.join(
            [periode["debut"].isoformat()]
            + [nombre(tables[c][3][rang]) for c in cles]))
    # Avec cet encodage, Excel lit correctement les accents.
    with open(chemin, "w", encoding="utf-8-sig" if csv else "utf-8") as fichier:
        fichier.write("\n".join(lignes) + "\n")
    return len(cles)


def annees_resultat(resultat):
    return sorted({p["debut"].year for p in resultat["periodes"]})


def dans_periode(periode, annee):
    """annee : None (toute la simulation), une année, ou (première, dernière)."""
    if annee is None:
        return True
    if isinstance(annee, (tuple, list)):
        return annee[0] <= periode["debut"].year <= annee[1]
    return periode["debut"].year == annee


def synthese_resultat(resultat, annee=None):
    """Compare les structures par nature, sur la simulation ou sur une année.

    Retourne (structures, lignes), avec lignes = (libellé, genre, valeurs).
    """
    m = resultat["modele"]
    structures = list(m.structures)
    rangs = [r for r, p in enumerate(resultat["periodes"])
             if dans_periode(p, annee)]
    comptes = {}
    for c in resultat["comptes"]:
        comptes.setdefault(c["structure"], []).append(c)

    def valeur(s, cle, genre):
        choisies = [comptes[s][r] for r in rangs]
        if genre in ("flux", "total", "flux_seul"):
            return sum(c[cle] for c in choisies)
        fin = choisies[-1]
        if genre.endswith("_seul"):
            return fin.get(cle)
        if cle == "total_actif":
            return fin["actifs"] + fin["creances"] + fin["tresorerie"] \
                + fin["impayes_a_recevoir"]
        if cle == "total_passif":
            return fin["fonds_propres"] + fin["dettes"] \
                + fin["dettes_fournisseurs"] + fin["provisions"] \
                + fin["impayes_a_payer"]
        return fin[cle]

    def details(cle, genre):
        """Détail d'une ligne : chaque flux, charge ou poste qui la compose."""
        sortie = []

        def ajouter(identifiant, table, colonnes):
            valeurs_ligne = resultat[table][identifiant]
            montant = sum(valeurs_ligne[r] for r in rangs) if genre == "flux" \
                else valeurs_ligne[rangs[-1]]
            sortie.append((identifiant, "detail", [
                montant if s in colonnes else None for s in structures]))

        if genre == "stock":
            categorie = CATEGORIES_SYNTHESE.get(cle)
            for i, c in m.postes.items():
                if c["categorie"] == categorie:
                    ajouter(i, "montants", (c["structure"],))
            return sortie
        if cle == "amortissements":
            for i, c in m.postes.items():
                if c["categorie"] == "Amortissement":
                    ajouter(i, "montants", (c["structure"],))
            return sortie
        dues = cle in ("recettes", "charges_dues")
        entree = {"recettes": "recettes_encaissees",
                  "charges_dues": "charges_payees"}.get(cle, cle)
        for i, f in m.flux.items():
            if f["nature"] != "Financier":
                continue
            recu, verse = CLASSEMENT_FLUX[f["compte"]]
            colonnes = ()
            if entree == verse:
                colonnes = (f["payeur"],)
            elif entree == recu or (cle == "recettes"
                                    and recu == "dividendes_recus"):
                colonnes = (f["beneficiaire"],)
            if colonnes:
                ajouter(i, "dus" if dues else "montants", colonnes)
        if entree in ("charges_payees", "investissements"):
            compte = "Résultat" if entree == "charges_payees" \
                else "Investissement"
            for i, c in m.charges.items():
                if c["compte"] == compte:
                    ajouter(i, "montants", (c["structure"],))
        return sortie

    lignes = []
    for cle, libelle, genre in LIGNES_SYNTHESE:
        if cle is None:
            lignes.append((T(libelle), "titre", []))
        else:
            lignes.append((T(libelle), "total" if "total" in genre else "ligne",
                           [valeur(s, cle, genre) for s in structures]))
            if genre in ("flux", "stock"):
                lignes += details(cle, genre)
    physiques = [(i, f) for i, f in m.flux.items()
                 if f["nature"] != "Financier" and i in resultat["series"]]
    if physiques:
        lignes.append((T("Flux physiques (reçu +, fourni -)"), "titre", []))
    for i, f in physiques:
        total, unite = quantite_physique(resultat, i, rangs)
        lignes.append(("%s (%s)" % (i, unite) if unite else i, "ligne", [
            total if s == f["beneficiaire"]
            else -total if s == f["payeur"] else None for s in structures]))
    grandeurs = []
    for i, p in sorted(m.parametres.items()):
        structure = i.rsplit("[", 1)[-1].rstrip("]")
        if structure in structures and i in resultat["series"] \
                and i not in m.flux and i not in m.charges \
                and i not in m.postes and est_physique(p["unite"]):
            total, unite = quantite_physique(resultat, i, rangs)
            grandeurs.append(("%s (%s)" % (i, unite), "ligne", [
                total if s == structure else None for s in structures]))
    if grandeurs:
        lignes.append((T("Grandeurs physiques"), "titre", []))
        lignes += grandeurs
    lignes += indicateurs(resultat, annee, structures, comptes, rangs)
    return structures, lignes


def est_physique(unite):
    atomes = [a for a, _e in decouper_unite(unite)] if unite.strip() else []
    return bool(atomes) and not any(
        a in MONNAIES or a in MULTIPLES_MONNAIE for a in atomes)


def rapport(numerateur, denominateur, facteur=1.0):
    return facteur * numerateur / denominateur if denominateur else None


def indicateurs(resultat, annee, structures, comptes, rangs):
    """Indicateurs par structure, sans valeur de référence imposée."""
    m = resultat["modele"]
    lignes = [(T("Indicateurs"), "titre", [])]
    marge, taux_rec, couverture, tres_min = [], [], [], []
    van, tri = [], []
    texte = m.simulation.get("taux_actualisation", "")
    taux = float(texte.replace(",", ".")) if texte else None
    for s in structures:
        choisies = [comptes[s][r] for r in rangs]

        def somme(cle):
            return sum(c[cle] for c in choisies)

        marge.append(rapport(somme("resultat"), somme("recettes"), 100))
        dus = sum(resultat["dus"][i][r] for i, f in m.flux.items()
                  if f["nature"] == "Financier" and f["beneficiaire"] == s
                  for r in rangs)
        recus = sum(resultat["montants"][i][r] for i, f in m.flux.items()
                    if f["nature"] == "Financier" and f["beneficiaire"] == s
                    for r in rangs)
        taux_rec.append(rapport(recus, dus, 100))
        couverture.append(rapport(
            somme("recettes_encaissees") - somme("charges_payees"),
            somme("dette_versee")))
        tres_min.append(min(c["tresorerie"] for c in choisies))
        flux_argent = [(c["solde"], {}) for c in comptes[s]]
        simulateur = resultat["simulateur"]
        if taux is not None:
            van.append(simulateur.valeur_actuelle(flux_argent, taux))
        try:
            tri.append(100 * simulateur.calculer_tri(flux_argent)
                       if any(v[0] for v in flux_argent) else None)
        except ErreurCalcul:
            tri.append(None)
    lignes += [
        (T("Marge (résultat / recettes dues) (%)"), "pourcent", marge),
        (T("Taux de recouvrement constaté (%)"), "pourcent", taux_rec),
        (T("Couverture des remboursements de dette"), "ratio", couverture),
        (T("Trésorerie la plus basse"), "ligne", tres_min)]
    if annee is None:
        if taux is not None:
            lignes.append((T("VAN des entrées moins sorties"), "ligne", van))
        lignes.append((T("TRI des entrées moins sorties (%)"), "pourcent", tri))
    return lignes


def quantite_physique(resultat, identifiant, rangs):
    """Somme sur la période ; un débit est multiplié par la durée de chaque pas."""
    unite = resultat["unites"].get(identifiant, "")
    valeurs = resultat["series"][identifiant]
    if "/" in unite:
        numerateur, denominateur = unite.rsplit("/", 1)
        if denominateur in ANNEES_PAR_UNITE:
            return sum(
                valeurs[r] * resultat["periodes"][r]["tau"]
                / ANNEES_PAR_UNITE[denominateur] for r in rangs), numerateur
    return sum(valeurs[r] for r in rangs), unite


def repartition_resultat(resultat, annee=None, perimetre=""):
    """Suit l'argent : qui paie qui, et ce qu'il reste à chaque structure.

    Retourne (structures, lignes), dans le même format que la synthèse.
    Avec un périmètre ou un groupe, seuls les flux et charges écrits par
    périmètre comptent, pour leur part dans ce périmètre.
    """
    m = resultat["modele"]
    structures = list(m.structures)
    rangs = [r for r, p in enumerate(resultat["periodes"])
             if dans_periode(p, annee)]
    tables = {"montants": resultat["montants"], "dus": resultat["dus"]}
    if perimetre and resultat.get("par_p"):
        tables["montants"], tables["dus"] = flux_filtres(resultat, perimetre)

    def cumul(identifiant, table="montants"):
        serie = tables[table].get(identifiant)
        return sum(serie[r] for r in rangs) if serie else 0.0

    paye = {(a, b): 0.0 for a in structures for b in structures}
    dus = dict.fromkeys(structures, 0.0)
    for i, f in m.flux.items():
        if f["nature"] == "Financier":
            paye[f["payeur"], f["beneficiaire"]] += cumul(i)
            dus[f["beneficiaire"]] += cumul(i, "dus")
    charges = dict.fromkeys(structures, 0.0)
    investissements = dict.fromkeys(structures, 0.0)
    detail_charges, detail_invest, detail_verse = [], [], []

    def detail(identifiant, structure):
        return (identifiant, "detail", [cumul(identifiant) if s == structure
                                        else None for s in structures])

    for i, c in m.charges.items():
        if c["compte"] == "Résultat":
            charges[c["structure"]] += cumul(i)
            detail_charges.append(detail(i, c["structure"]))
        else:
            investissements[c["structure"]] += cumul(i)
            detail_invest.append(detail(i, c["structure"]))
    for i, f in m.flux.items():
        if f["nature"] == "Financier":
            detail_verse.append(detail(i, f["payeur"]))
    encaisse = [sum(paye[a, b] for a in structures) for b in structures]
    verse = [sum(paye[a, b] for b in structures) for a in structures]
    propres = [charges[s] for s in structures]
    investis = [investissements[s] for s in structures]
    nets = [e - v - c - i
            for e, v, c, i in zip(encaisse, verse, propres, investis)]
    base = -sum(n for n in nets if n < 0)

    def part(valeur):
        return 100 * valeur / base if base else None

    noms = {s: m.structures[s]["nom"] for s in structures}
    fin = max(rangs)
    a_recevoir = [None if perimetre else next(
        c["impayes_a_recevoir"] for c in resultat["comptes"]
        if c["structure"] == s
        and c["periode"] == resultat["periodes"][fin]["debut"])
        for s in structures]
    lignes = [(T("Qui paie qui (la colonne reçoit)"), "titre", [])]
    for a in structures:
        lignes.append((T("Payé par %s" % noms[a]), "ligne",
                       [paye[a, b] for b in structures]))
    lignes += [
        (T("Encaissé"), "total", encaisse),
        (T("Dû"), "ligne", [dus[s] for s in structures]),
        (T("Impayés et moratoires à recevoir"), "ligne", a_recevoir),
        (T("Répartition de l'argent"), "titre", []),
        (T("Encaissé"), "ligne", encaisse),
        (T("Payé aux autres structures"), "ligne", verse)] + detail_verse + [
        (T("Charges propres"), "ligne", propres)] + detail_charges + [
        (T("Investissements propres"), "ligne", investis)] + detail_invest + [
        (T("Reste à la structure"), "total", nets),
        (T("Part de l'argent apporté (%)"), "pourcent", [part(n) for n in nets]),
        (T("Part des charges propres (%)"), "pourcent",
         [part(c) for c in propres]),
        (T("Part des investissements propres (%)"), "pourcent",
         [part(i) for i in investis]),
    ]
    return structures, lignes


def flux_argent(resultat, annee=None, perimetre=""):
    """Données du diagramme « Où va l'argent » (montants payés cumulés).

    Retourne un dictionnaire :
      structures : identifiants, noms : {id: nom}, types : {id: type}
      liens : [(payeur, beneficiaire, montant, [noms des flux])], montants
              nets entre deux structures (A paie B moins B paie A), > 0
      charges, investissements, restes : {id: montant}
      apporte : total apporté par les structures qui versent plus qu'elles
                ne reçoivent (base des pourcentages, comme la Répartition)
      monnaie : unité monétaire de référence
    """
    m = resultat["modele"]
    structures = list(m.structures)
    rangs = [r for r, p in enumerate(resultat["periodes"])
             if dans_periode(p, annee)]
    montants = resultat["montants"]
    if perimetre and resultat.get("par_p"):
        montants = flux_filtres(resultat, perimetre)[0]

    def cumul(identifiant):
        serie = montants.get(identifiant)
        return sum(serie[r] for r in rangs) if serie else 0.0

    paye, noms_flux = {}, {}
    for i, f in m.flux.items():
        if f["nature"] == "Financier" and f["payeur"] != f["beneficiaire"]:
            cle = (f["payeur"], f["beneficiaire"])
            paye[cle] = paye.get(cle, 0.0) + cumul(i)
            noms_flux.setdefault(cle, []).append(f["nom"])
    charges = dict.fromkeys(structures, 0.0)
    investissements = dict.fromkeys(structures, 0.0)
    for i, c in m.charges.items():
        cible = charges if c["compte"] == "Résultat" else investissements
        cible[c["structure"]] += cumul(i)
    liens, vus = [], set()
    for (a, b), valeur in paye.items():
        if (a, b) in vus:
            continue
        vus.update({(a, b), (b, a)})
        net = valeur - paye.get((b, a), 0.0)
        noms = noms_flux.get((a, b), []) if net >= 0 else \
            noms_flux.get((b, a), [])
        if net < 0:
            a, b, net = b, a, -net
        if net > 1e-9:
            liens.append((a, b, net, noms))
    restes = {}
    for s in structures:
        recu = sum(v for a, b, v, _n in liens if b == s)
        verse = sum(v for a, b, v, _n in liens if a == s)
        restes[s] = recu - verse - charges[s] - investissements[s]
    return {
        "structures": structures,
        "noms": {s: m.structures[s]["nom"] for s in structures},
        "types": {s: m.structures[s].get("type", "") for s in structures},
        "liens": liens, "charges": charges,
        "investissements": investissements, "restes": restes,
        "apporte": -sum(r for r in restes.values() if r < 0),
        "monnaie": m.references_unites.get("Monnaie", ""),
    }


VUES_TABLEAU = {"synthese": synthese_resultat,
                "repartition": repartition_resultat,
                "tarifs": tarifs_resultat,
                "perimetres": perimetres_resultat}


def lignes_synthese_texte(resultat, annee, separateur, virgule,
                          vue="synthese", **options):
    structures, lignes = VUES_TABLEAU[vue](resultat, annee, **options)

    def nombre(valeur):
        if valeur is None:
            return ""
        texte = repr(float(valeur))
        return texte.replace(".", ",") if virgule else texte

    sortie = [separateur.join([T("Nature")] + structures)]
    for libelle, genre, valeurs in lignes:
        if genre == "detail":
            libelle = "    " + libelle
        sortie.append(separateur.join([libelle] + [nombre(v) for v in valeurs]))
    return sortie


def exporter_synthese(resultat, annee, chemin, vue="synthese"):
    csv = chemin.lower().endswith(".csv")
    lignes = lignes_synthese_texte(resultat, annee, ";" if csv else "\t", csv,
                                   vue)
    with open(chemin, "w", encoding="utf-8-sig" if csv else "utf-8") as fichier:
        fichier.write("\n".join(lignes) + "\n")


def format_valeur(valeur, _position=None):
    """Sépare les milliers sur les axes, sans notation scientifique."""
    if abs(valeur) >= 1000:
        return "{:,.0f}".format(valeur).replace(",", "\u202f")
    return "%g" % round(valeur, 6)


def dessiner_courbes(figure, resultat, cles, axe="Date"):
    """Trace une ou plusieurs séries : un graphique par unité, jamais deux axes.

    Retourne le nombre de séries laissées de côté.
    """
    from matplotlib.ticker import FuncFormatter
    tables = tables_resultat(resultat)
    figure.clear()
    groupes = {}
    for cle in cles:
        if cle in tables:
            groupes.setdefault(tables[cle][2], []).append(cle)
    ecartees = sum(max(0, len(v) - COURBES_PAR_GRAPHIQUE)
                   for v in groupes.values())
    unites = list(groupes)
    ecartees += sum(len(groupes[u]) for u in unites[GRAPHIQUES_MAX:])
    unites = unites[:GRAPHIQUES_MAX]
    if not unites:
        return ecartees
    if axe == "Date":
        abscisses = [p["debut"] for p in resultat["periodes"]]
        titre_axe = T("Date")
    else:
        abscisses = tables[axe][3]
        titre_axe = "%s (%s)" % (axe, tables[axe][2])
    graphiques = figure.subplots(len(unites), 1, sharex=True, squeeze=False)
    for graphique, unite in zip(graphiques[:, 0], unites):
        retenues = groupes[unite][:COURBES_PAR_GRAPHIQUE]
        for cle, couleur in zip(retenues, COULEURS_COURBES):
            graphique.plot(abscisses, tables[cle][3], color=couleur,
                           linewidth=2, label=tables[cle][1],
                           marker="o" if len(abscisses) <= 40 else None,
                           markersize=4, markeredgecolor="white",
                           markeredgewidth=1)
        graphique.set_ylabel(unite or T("sans unité"), color="#51616f")
        graphique.yaxis.set_major_formatter(FuncFormatter(format_valeur))
        graphique.grid(axis="y", color="#E6E9ED", linewidth=0.8)
        graphique.set_axisbelow(True)
        for cote in ("top", "right", "left"):
            graphique.spines[cote].set_visible(False)
        graphique.spines["bottom"].set_color("#AEB6BF")
        graphique.tick_params(colors="#51616f", length=0, labelsize=8)
        if len(retenues) > 1:
            graphique.legend(loc="upper center", frameon=False, fontsize=8,
                             ncol=min(2, len(retenues)),
                             bbox_to_anchor=(0.5, 1.02 + 0.08 * (
                                 (len(retenues) + 1) // 2)))
        else:
            graphique.set_title(tables[retenues[0]][1], fontsize=9, loc="left",
                                color="#1f2933")
    graphiques[-1, 0].set_xlabel(titre_axe, color="#51616f", fontsize=9)
    return ecartees


def exporter_pdf(resultat, cles, chemin, axe="Date"):
    """Enregistre le graphique en PDF, au format A4 paysage."""
    from matplotlib.figure import Figure
    figure = Figure(figsize=(11.69, 8.27), layout="constrained")
    ecartees = dessiner_courbes(figure, resultat, cles, axe)
    figure.text(0.99, 0.005, T("Copyright © 2026 A. C. Diagne. Logiciel libre, "
                               "licence GNU GPL v3."), ha="right", va="bottom",
                fontsize=7, color="#7A8784")
    figure.savefig(chemin, format="pdf")
    return ecartees


def ecrire_resultat(resultat, chemin):
    m = resultat["modele"]
    lignes = ["# HapNatt - résultats", "", "[EXECUTION]", "cle\tvaleur",
              "statut\t" + resultat["statut"],
              "periodes\t%d" % len(resultat["periodes"]),
              "variables\t%d" % len(resultat["series"]), "",
              "[ERREURS]", "message"]
    lignes += resultat["erreurs"]
    lignes += ["", "[ALERTES]", "message"] + resultat["alertes"]
    lignes += ["", "[CONVERGENCE]", "variables\titerations_max\tecart_final\t"
               "methode"]
    for bloc in resultat["convergence"]:
        lignes.append("%s\t%d\t%r\t%s" % (
            " + ".join(bloc["variables"]), bloc["iterations"], bloc["ecart"],
            "newton" if bloc["newton"] else "iterations"))
    if m.simulation.get("conserver_convergence") == "oui":
        lignes += ["", "[SUIVI_CONVERGENCE]",
                   "variable\tperiode\titeration\tvaleur\tecart"]
        for s in resultat["suivi"]:
            lignes.append("%s\t%s\t%d\t%r\t%r" % (
                s["variable"], s["periode"].isoformat(), s["iteration"],
                s["valeur"], s["ecart"]))
    lignes += ["", "[SOLDES]",
               "structure\tperiode\trecettes\tcharges\tsolde\tcumul"]
    for s in resultat["soldes"]:
        lignes.append("%s\t%s\t%r\t%r\t%r\t%r" % (
            s["structure"], s["periode"].isoformat(), s["recettes"],
            s["charges"], s["solde"], s["cumul"]))
    colonnes = ("capital", "tresorerie", "recettes", "charges", "resultat",
                "solde", "fonds_propres", "actifs", "creances", "dettes",
                "dettes_fournisseurs", "reserves", "provisions", "garanties",
                "ecart_bilan", "entrees", "sorties", "amortissements",
                "dotations", "charges_dues", "autres_resultat",
                "impayes_a_recevoir", "impayes_a_payer", "service_dette",
                "caf", "fonds_mobilisables", "annuite_supportable",
                "capacite_emprunt", "capacite_investissement",
                "besoin_investissement", "marge_investissement") \
        + DETAIL_ARGENT
    lignes += ["", "[COMPTES]", "structure\tperiode\t" + "\t".join(colonnes)]
    for c in resultat["comptes"]:
        lignes.append("%s\t%s\t" % (c["structure"], c["periode"].isoformat())
                      + "\t".join(repr(c[k]) if k in c else ""
                                   for k in colonnes))
    if resultat["comptes"]:
        lignes += ["", "[SYNTHESE]"] + lignes_synthese_texte(
            resultat, None, "\t", False)
        lignes += ["", "[REPARTITION]"] + lignes_synthese_texte(
            resultat, None, "\t", False, "repartition")
    if resultat.get("par_p"):
        for niveau in niveaux_perimetres(resultat)[:2]:
            lignes += ["", "[PERIMETRES_RESULTATS]", "# " + niveau] + \
                lignes_synthese_texte(resultat, None, "\t", False,
                                      "perimetres", niveau=niveau)
    if resultat.get("tarifs"):
        lignes += ["", "[TARIFS]"] + lignes_synthese_texte(
            resultat, None, "\t", False, "tarifs")
    for section, ensemble in (("SERIES", m.parametres),
                              ("POST_TRAITEMENT", m.post)):
        lignes += ["", "[%s]" % section, "variable\tperiode\tvaleur\tunite"]
        if section == "SERIES":
            for nom, unite in echelles_temps(m):
                for periode in resultat["periodes"]:
                    lignes.append("%s\t%s\t%r\t%s" % (
                        nom, periode["debut"].isoformat(),
                        float(periode[nom]), unite))
        for i in sorted(ensemble):
            if i not in resultat["series"]:
                continue
            for periode, valeur in zip(resultat["periodes"],
                                       resultat["series"][i]):
                lignes.append("%s\t%s\t%r\t%s" % (
                    i, periode["debut"].isoformat(), valeur,
                    resultat["unites"].get(i, "")))
    # La mise en données complète accompagne les résultats qu'elle a produits.
    lignes += ["", MARQUE_JEU_DE_DONNEES] + resultat.get("source", m).texte()
    with open(chemin, "w", encoding="utf-8") as fichier:
        fichier.write("\n".join(lignes) + "\n")


def lancer_fichier():
    modele = Modele.lire(chemin_local(FICHIER_SIMULATION))
    resultat = simuler_tarifs(modele)
    ecrire_resultat(resultat, chemin_local(FICHIER_RESULTAT))
    print("Statut :", resultat["statut"])
    for texte in resultat["erreurs"]:
        print("Erreur :", texte)
    for texte in resultat["alertes"]:
        print("Alerte :", texte)
    for bloc in resultat["convergence"]:
        print("Boucle %s : %d itérations au maximum"
              % (" + ".join(bloc["variables"]), bloc["iterations"]))
    for ligne in resumer_suivi(resultat):
        print("Suivi :", ligne)
    print("Résultats écrits dans", FICHIER_RESULTAT)


if __name__ == "__main__":
    lancer_fichier()
