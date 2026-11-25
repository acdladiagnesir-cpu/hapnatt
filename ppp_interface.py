# -*- coding: utf-8 -*-
"""
HapNatt - Interface

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

Lancement : ouvrir ce fichier dans IDLE, puis appuyer sur F5.
Installation requise une fois : pip install PySide6 xyzservices
(xyzservices est facultatif : sans lui, le fond OpenStreetMap est utilisé.)
"""

# ============================ CONFIGURATION ============================
FICHIER_DEPART = "Exemple_Simulation.dat"   # mise en données ouverte au démarrage
TITRE_APPLICATION = "HapNatt"
FOND_DE_CARTE = "OpenStreetMap.Mapnik"      # nom xyzservices (fond libre par défaut)
CARTE_ATTENUEE = True                       # fond de carte en gris clair, points lisibles
CONTACT_APPLICATION = "diagne.amicolle@gmail.com"  # envoyé aux
                                            # serveurs de tuiles (règles d'OpenStreetMap)
DOSSIER_CACHE_CARTE = "cache_carte"         # tuiles gardées sur le disque (hors ligne ensuite)
LANGUE_INTERFACE = "fr"                     # "fr" pour français, "en" pour anglais
# =======================================================================

import copy
import datetime
import math
import re
import os
import sys
import time

from PySide6.QtCore import (QDate, QMarginsF, QPointF, QRectF, Qt, QTimer,
                            QUrl, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QImage,
                           QPageLayout, QPageSize, QPainter, QPdfWriter,
                           QPainterPath, QPainterPathStroker, QPen,
                           QPixmap, QPolygonF, QSyntaxHighlighter,
                           QKeySequence, QShortcut, QTextCharFormat,
                           QTextCursor)
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox,
    QDialog, QGridLayout, QMenu, QProgressBar, QScrollArea, QTabWidget,
    QLineEdit, QRadioButton, QStyle, QStyledItemDelegate, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QFrame,
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsObject, QGraphicsPathItem,
    QGraphicsPixmapItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem, QGraphicsView, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QToolButton, QToolTip, QVBoxLayout, QWidget,
)

import ppp_moteur
from ppp_prototype import (
    CATEGORIES_POSTES, COMPTES_FLUX, EFFETS_FLUX, PAIEMENT_DEFAUT,
    TYPES_STRUCTURE, composer_id,
    COLONNES_X, COLONNES_Y, DIMENSIONS, FONCTIONS, FONCTIONS_POST,
    FONCTIONS_UTILISATEUR, STRUCTURE_COMMUNE, tester_appel,
    LECTURES_TABLE, MOTS_CLES, TEMPS_FIXES, UNITES, VARIABLE_TEMPS,
    VARIABLES_SYSTEME, ErreurModele, Modele, analyser_expression, creer_id,
    decomposer_id, est_indexe, indexee, lire_tableau_perimetres,
    perimetre_id)
from ppp_langues import LANGUE, T, definir_langue, origine
from PySide6 import QtWidgets as _Qt

COPYRIGHT = "Copyright © 2026 A. C. Diagne. Logiciel libre, licence GNU GPL v3."


# ============================== TRADUCTION ==============================
# Les textes de l'interface sont écrits en français ; en anglais, chaque
# texte affiché passe par T() au moment où il est posé sur l'écran. Les
# textes riches (<span>...) sont traduits morceau par morceau, et les
# messages sur plusieurs lignes ligne par ligne.
def tr(texte):
    if LANGUE["code"] == "fr" or not isinstance(texte, str) or not texte:
        return texte
    entier = T(texte)
    if entier != texte:
        return entier
    if "<" in texte:
        return "".join(morceau if morceau.startswith("<") else tr(morceau)
                       for morceau in re.split(r"(<[^>]+>)", texte))
    if "\n" in texte:
        return "\n".join(tr(ligne) for ligne in texte.split("\n"))
    coeur = texte.strip()
    if coeur and coeur != texte:
        traduit = T(coeur)
        if traduit != coeur:
            return texte.replace(coeur, traduit)
    return texte


def _traduire_arguments(args, kw, positionnel=True):
    if positionnel:
        args = [tr(a) if isinstance(a, str) else a for a in args]
    for cle in ("text", "placeholderText", "toolTip"):
        if cle in kw:
            kw[cle] = tr(kw[cle])
    return args, kw


def _classe_traduite(base, positionnel=True):
    class Traduite(base):
        def __init__(self, *args, **kw):
            args, kw = _traduire_arguments(args, kw, positionnel)
            super().__init__(*args, **kw)

        def setToolTip(self, texte):
            super().setToolTip(tr(texte))

    Traduite.__name__ = base.__name__
    if hasattr(base, "setText") and positionnel:
        Traduite.setText = lambda self, texte: base.setText(self, tr(texte))
    if hasattr(base, "setPlaceholderText"):
        Traduite.setPlaceholderText = \
            lambda self, texte: base.setPlaceholderText(self, tr(texte))
    return Traduite


QLabel = _classe_traduite(_Qt.QLabel)
QPushButton = _classe_traduite(_Qt.QPushButton)
QCheckBox = _classe_traduite(_Qt.QCheckBox)
QRadioButton = _classe_traduite(_Qt.QRadioButton)
QToolButton = _classe_traduite(_Qt.QToolButton)
QLineEdit = _classe_traduite(_Qt.QLineEdit, positionnel=False)
QPlainTextEdit = _classe_traduite(_Qt.QPlainTextEdit, positionnel=False)


class QComboBox(_Qt.QComboBox):
    """Liste affichée dans la langue choisie ; le programme lit toujours
    la valeur française (celle qui est enregistrée dans les fichiers)."""

    def addItem(self, texte, donnee=None):
        super().addItem(tr(texte), donnee)

    def addItems(self, textes):
        super().addItems([tr(t) for t in textes])

    def setCurrentText(self, texte):
        super().setCurrentText(tr(texte))

    def currentText(self):
        return origine(super().currentText())

    def findText(self, texte, *args):
        return super().findText(tr(texte), *args)

    def itemText(self, rang):
        return origine(super().itemText(rang))

    def setToolTip(self, texte):
        super().setToolTip(tr(texte))


class QTabWidget(_Qt.QTabWidget):
    def addTab(self, page, texte):
        return super().addTab(page, tr(texte))


class QMenu(_Qt.QMenu):
    def addAction(self, texte, *args):
        return super().addAction(tr(texte), *args)


class QTreeWidget(_Qt.QTreeWidget):
    def setHeaderLabels(self, textes):
        super().setHeaderLabels([tr(t) for t in textes])


class QTableWidget(_Qt.QTableWidget):
    def setHorizontalHeaderLabels(self, textes):
        super().setHorizontalHeaderLabels([tr(t) for t in textes])


class QTreeWidgetItem(_Qt.QTreeWidgetItem):
    def __init__(self, textes=None, *args):
        if isinstance(textes, list):
            super().__init__([tr(t) for t in textes], *args)
        elif textes is None:
            super().__init__(*args)
        else:
            super().__init__(textes, *args)

    def setText(self, colonne, texte):
        super().setText(colonne, tr(texte))

    def setToolTip(self, colonne, texte):
        super().setToolTip(colonne, tr(texte))


def _dialogue(fonction, *rangs):
    """Fonction statique dont les arguments de rang donné sont traduits."""
    def traduite(*args, **kw):
        args = list(args)
        for rang in rangs:
            if rang < len(args) and isinstance(args[rang], str):
                args[rang] = tr(args[rang])
        return fonction(*args, **kw)
    return staticmethod(traduite)


QMessageBox = _Qt.QMessageBox
QFileDialog = _Qt.QFileDialog
QInputDialog = _Qt.QInputDialog
QMessageBox.question = _dialogue(_Qt.QMessageBox.question, 1, 2)
QMessageBox.warning = _dialogue(_Qt.QMessageBox.warning, 1, 2)
QFileDialog.getOpenFileName = _dialogue(_Qt.QFileDialog.getOpenFileName,
                                        1, 3)
QFileDialog.getSaveFileName = _dialogue(_Qt.QFileDialog.getSaveFileName,
                                        1, 3)
QInputDialog.getText = _dialogue(_Qt.QInputDialog.getText, 1, 2)
QInputDialog.getItem = _dialogue(_Qt.QInputDialog.getItem, 1, 2)


LARGEUR_BLOC, HAUTEUR_BLOC = 210, 86
ENCRE, GRIS, FILET = "#16211F", "#55625F", "#E1E4DF"
VERT, VERT_CLAIR = "#0B6E66", "#E2F1EE"
COULEURS_TYPES = {                 # type : (fond, bordure)
    "Société de patrimoine": ("#E2F1EE", "#8CC7BE"),
    "Exploitant": ("#FBEBD9", "#E0B078"),
    "Autorité": ("#E6ECF7", "#A4B8DC"),
    "Vendeur": ("#F6E6EE", "#D9A7BE"),
    "Bailleur de fonds": ("#ECE6F5", "#BBA7D9"),
}
FOND_AUTRE = ("#EEF0ED", "#C9CEC8")
ETAPES = ("1. Structures", "2. Périmètres", "3. Flux", "4. Paramètres",
          "5. État initial", "6. Simulation", "7. Post-traitement",
          "8. Résultats", "9. Fonctions")
(PAGE_SCHEMA, PAGE_PERIMETRES, PAGE_PARAMETRES, PAGE_INITIAL,
 PAGE_SIMULATION, PAGE_RESULTATS, PAGE_POST, PAGE_FONCTIONS,
 PAGE_ATTENTE) = range(9)
# Palette des groupes sur la carte (contrastée, lisible sur fond clair).
PALETTE = ("#0B6E66", "#C2610C", "#2467B5", "#A33B6B", "#6B3FA0",
           "#4E7D1E", "#B8860B", "#3A5A78", "#8C4A2F", "#1E8C8C")
# Fond de carte utilisé si xyzservices n'est pas installé : OpenStreetMap,
# données libres (ODbL). La mention des contributeurs est obligatoire.
ATTRIBUTION_OSM = ('© <a href="https://www.openstreetmap.org/copyright">'
                   'OpenStreetMap</a> contributors')
FOND_PAR_DEFAUT = ("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                   ATTRIBUTION_OSM, 19)

STYLE = """
QMainWindow, #page { background: #F5F6F3; }
QWidget { font-family: Inter, "Segoe UI", sans-serif; font-size: 14px;
          color: #16211F; }
#entete, #rail, #fiche { background: #FFFFFF; }
#entete { border-bottom: 1px solid #E1E4DF; }
#rail { border-right: 1px solid #E1E4DF; }
#fiche { border-left: 1px solid #E1E4DF; }
#marque { font-size: 18px; font-weight: 600; }
#titre { font-size: 24px; font-weight: 600; }
#titreFiche { font-size: 22px; font-weight: 600; }
#discret { color: #55625F; font-size: 13px; }
#titreSection { font-size: 15px; font-weight: 600; padding-top: 6px; }
QPushButton { min-height: 40px; padding: 0 16px; background: #FFFFFF;
              border: 1px solid #C9CEC8; border-radius: 8px; }
QPushButton:hover { background: #F5F6F3; }
QPushButton#principal { background: #0B6E66; color: #FFFFFF; border: 0;
                        font-weight: 600; }
QPushButton#principal:hover { background: #084F49; }
QPushButton#etape { text-align: left; border: 0; border-radius: 8px;
                    padding: 0 12px; }
QPushButton#etape:hover { background: #F5F6F3; }
QPushButton#etape:checked { background: #E2F1EE; color: #084F49;
                            font-weight: 600; }
QPlainTextEdit { font-family: "JetBrains Mono", Consolas, monospace;
                 font-size: 13px; background: #FBFBFA; padding: 8px;
                 border: 1px solid #C9CEC8; border-radius: 8px; }
QGraphicsView { background: #FFFFFF; border: 1px solid #E1E4DF;
                border-radius: 12px; }
QTableWidget { background: #FFFFFF; border: 1px solid #E1E4DF;
               border-radius: 12px; gridline-color: #EEF0ED;
               selection-background-color: #E2F1EE;
               selection-color: #084F49; }
QHeaderView::section { background: #FFFFFF; color: #55625F; border: 0;
                       border-bottom: 1px solid #E1E4DF; padding: 8px;
                       font-weight: 600; }
QComboBox { min-height: 36px; padding: 0 10px; background: #FFFFFF;
            border: 1px solid #C9CEC8; border-radius: 8px; }
QToolButton#carte { min-width: 34px; min-height: 34px; font-size: 16px;
                    background: #FFFFFF; border: 1px solid #C9CEC8;
                    border-radius: 8px; }
QToolButton#carte:hover { background: #F5F6F3; }
#surCarte { background: rgba(255, 255, 255, 230); border: 1px solid #E1E4DF;
            border-radius: 8px; padding: 6px 10px; font-size: 12px;
            color: #33423F; }
#attribution { background: rgba(255, 255, 255, 200); font-size: 10px;
               color: #55625F; padding: 1px 4px; }
QSplitter::handle { background: transparent; }
#carteBlanche { background: #FFFFFF; border: 1px solid #E1E4DF;
                border-radius: 12px; }
#titreCarte { font-size: 13px; font-weight: 600; color: #33423F; }
QProgressBar { background: #E9EBE7; border: 0; border-radius: 4px; }
QProgressBar::chunk { background: #0B6E66; border-radius: 4px; }
QDialog { background: #FFFFFF; }
#mention { font-size: 10px; color: #7A8784; padding: 8px 6px 0 6px; }
QToolButton#section { border: 0; background: transparent; font-weight: 600;
                      color: #33423F; padding: 4px 0; }
QPushButton#danger { color: #C0392B; }
QWidget#fond { background: #FFFFFF; }
#chiffre { font-family: "Space Grotesk", "Inter"; font-size: 22px;
           font-weight: 600; color: #16211F; }
QTabWidget#onglets::pane { border: 0; }
QTabBar::tab { padding: 8px 16px; margin-right: 4px; color: #55625F;
               background: transparent; border: 0;
               border-bottom: 2px solid transparent; font-size: 13px; }
QTabBar::tab:selected { color: #16211F; font-weight: 600;
                        border-bottom: 2px solid #0B6E66; }
QTreeWidget#tableau, QTableWidget#tableau {
    background: #FFFFFF; border: 1px solid #E1E4DF; border-radius: 12px; }
QToolButton#export { min-height: 36px; padding: 0 14px; background: #FFFFFF;
                     border: 1px solid #C9CEC8; border-radius: 8px; }
QTreeWidget { border: 0; background: #FFFFFF; font-size: 13px; }
QTreeWidget::item { min-height: 26px; }
QTreeWidget::item:selected { background: #E2F1EE; color: #084F49; }
QLineEdit { min-height: 34px; padding: 0 10px; background: #FFFFFF;
            border: 1px solid #C9CEC8; border-radius: 8px; }
QLineEdit:focus, QPlainTextEdit#formuleCode:focus { border-color: #0B6E66; }
QPlainTextEdit#formuleCode { background: #FBFCFA; border: 1px solid #C9CEC8;
                             border-radius: 10px; padding: 8px; }
QPushButton#pastille { min-height: 30px; padding: 0 12px;
                       border-radius: 15px; }
QPushButton#pastille:checked { background: #E2F1EE; color: #084F49;
                               border-color: #0B6E66; font-weight: 600; }
"""


# Version installée (.exe) : les fichiers de l'utilisateur, les exemples et le
# cache de la carte vont dans Documents/HapNatt, toujours accessible en
# écriture. En script (IDLE, F5) : le dossier du script, comme avant.
EXECUTABLE = getattr(sys, "frozen", False)
if EXECUTABLE:
    DOSSIER_UTILISATEUR = os.path.join(os.path.expanduser("~"), "Documents",
                                       "HapNatt")
else:
    DOSSIER_UTILISATEUR = os.path.dirname(os.path.abspath(__file__))


def preparer_dossier_utilisateur():
    """Au premier lancement de l'exécutable, copie les exemples et la
    documentation dans Documents/HapNatt (sans écraser une copie modifiée)."""
    if not EXECUTABLE:
        return
    import shutil
    os.makedirs(DOSSIER_UTILISATEUR, exist_ok=True)
    source = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    for nom in ("Exemple_Simulation.dat", "Exemple_Perimetres.dat",
                "README_Formules.md", "LICENSE"):
        cible = os.path.join(DOSSIER_UTILISATEUR, nom)
        if os.path.exists(os.path.join(source, nom)) \
                and not os.path.exists(cible):
            shutil.copy2(os.path.join(source, nom), cible)


def chemin_local(nom):
    return os.path.join(DOSSIER_UTILISATEUR, nom)


def millions(valeur):
    return "{:,.0f}".format(valeur / 1e6).replace(",", " ") + " M"


class Bloc(QGraphicsObject):
    """Une structure : se déplace à la souris, s'ouvre au clic."""

    def __init__(self, fenetre, identifiant, fiche):
        super().__init__()
        self.fenetre, self.identifiant, self.fiche = fenetre, identifiant, fiche
        self.setPos(fiche["x"], fiche["y"])
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(2)

    def boundingRect(self):
        return QRectF(-LARGEUR_BLOC / 2, -HAUTEUR_BLOC / 2,
                      LARGEUR_BLOC, HAUTEUR_BLOC)

    def paint(self, peintre, _option, _widget=None):
        fond, bord = COULEURS_TYPES.get(self.fiche["type"], FOND_AUTRE)
        peintre.setRenderHint(peintre.RenderHint.Antialiasing)
        peintre.setBrush(QColor(fond))
        peintre.setPen(QPen(QColor(bord), 1))
        peintre.drawRoundedRect(self.boundingRect().adjusted(.5, .5, -.5, -.5),
                                12, 12)
        peintre.setPen(QColor(ENCRE))
        # Taille en pixels de scène : même rendu à l'écran, en PDF et à
        # l'impression (la police par défaut dépend de l'appareil).
        police = QFont(QApplication.font())
        police.setPixelSize(15)
        police.setBold(True)
        peintre.setFont(police)
        peintre.drawText(self.boundingRect().adjusted(8, 12, -8, -38),
                         Qt.AlignCenter, self.fiche["nom"])
        police.setBold(False)
        police.setPixelSize(13)
        peintre.setFont(police)
        peintre.setPen(QColor("#33423F"))
        peintre.drawText(self.boundingRect().adjusted(8, 42, -8, -8),
                         Qt.AlignCenter, tr(self.fiche["type"]))

    def itemChange(self, changement, valeur):
        if changement == QGraphicsItem.ItemScenePositionHasChanged:
            self.fiche["x"], self.fiche["y"] = int(self.x()), int(self.y())
            # Redessin différé, sans recadrer la scène pendant le glisser :
            # recadrer fait défiler la vue, qui rejoue le mouvement de la
            # souris et rappelait itemChange en boucle.
            self.fenetre.planifier_flux()
        return super().itemChange(changement, valeur)

    def mouseReleaseEvent(self, evenement):
        super().mouseReleaseEvent(evenement)
        QTimer.singleShot(0, self.fenetre.tracer_flux)
        self.fenetre.cliquer_structure(self.identifiant)


class EtiquetteMobile(QGraphicsRectItem):
    """Étiquette d'une flèche : se déplace à la souris ; le double-clic la
    remet à sa place. rappel(decalage) reçoit le décalage (dx, dy) par
    rapport à la place calculée, ou None pour la remettre en place."""

    def __init__(self, rectangle, place, decalage, rappel):
        super().__init__(rectangle)
        self.place, self.rappel, self.depart = place, rappel, None
        self.setPos(place + QPointF(*decalage))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(tr("Glisser pour déplacer l'étiquette · double-clic "
                           "pour la remettre en place"))

    def mousePressEvent(self, evenement):
        self.depart = self.pos()
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(evenement)
        evenement.accept()

    def mouseReleaseEvent(self, evenement):
        super().mouseReleaseEvent(evenement)
        self.setCursor(Qt.OpenHandCursor)
        if self.depart is not None and self.pos() != self.depart:
            ecart = self.pos() - self.place
            self.rappel((int(round(ecart.x())), int(round(ecart.y()))))
        self.depart = None

    def mouseDoubleClickEvent(self, evenement):
        evenement.accept()
        self.rappel(None)


class Schema(QGraphicsView):
    def __init__(self, fenetre=None):
        super().__init__()
        self.fenetre = fenetre
        self.setRenderHint(self.renderHints().__class__.Antialiasing)
        self.setScene(QGraphicsScene(self))
        self.setAlignment(Qt.AlignCenter)

    def keyPressEvent(self, evenement):
        if self.fenetre and evenement.key() in (Qt.Key_Delete,
                                                 Qt.Key_Backspace):
            self.fenetre.supprimer_selection()
        elif self.fenetre and evenement.key() == Qt.Key_Escape:
            self.fenetre.annuler_outil()
        else:
            super().keyPressEvent(evenement)


class Section(QWidget):
    """Partie repliable d'une fiche : titre cliquable, contenu dessous."""

    def __init__(self, nom):
        super().__init__()
        self.nom = nom
        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(0, 6, 0, 0)
        colonne.setSpacing(6)
        self.bouton = QToolButton(objectName="section", checkable=True,
                                  toolButtonStyle=Qt.ToolButtonTextBesideIcon)
        self.bouton.setArrowType(Qt.RightArrow)
        self.bouton.setText(nom)
        self.bouton.toggled.connect(self.deplier)
        colonne.addWidget(self.bouton)
        self.contenu = QWidget()
        self.boite = QVBoxLayout(self.contenu)
        self.boite.setContentsMargins(4, 0, 0, 0)
        colonne.addWidget(self.contenu)
        self.contenu.hide()

    def titre(self, texte):
        self.bouton.setText(texte)

    def ajouter(self, element):
        if isinstance(element, QWidget):
            self.boite.addWidget(element)
        else:
            self.boite.addLayout(element)

    def deplier(self, ouvert=True):
        self.bouton.blockSignals(True)
        self.bouton.setChecked(ouvert)
        self.bouton.blockSignals(False)
        self.bouton.setArrowType(Qt.DownArrow if ouvert else Qt.RightArrow)
        self.contenu.setVisible(ouvert)


# ================================ CARTE ================================
def fond_de_carte(nom):
    """(modèle d'adresse {z}/{x}/{y}, attribution, zoom maximal)."""
    try:
        import xyzservices.providers as xyz
        fournisseur = xyz.query_name(nom)
        adresse = fournisseur.build_url(x="{x}", y="{y}", z="{z}")
        mention = fournisseur.get("html_attribution") \
            or fournisseur.get("attribution", "")
        if "openstreetmap" in adresse.lower():
            mention = ATTRIBUTION_OSM
        return (adresse, mention, int(fournisseur.get("max_zoom") or 18))
    except Exception:              # module absent, nom inconnu ou clé exigée
        return FOND_PAR_DEFAUT


# Identification demandée par la politique d'usage des tuiles OpenStreetMap.
AGENT_UTILISATEUR = ("HapNatt/1.0 (%s)" % (
    CONTACT_APPLICATION or "logiciel libre de modelisation PPP")).encode()


def attenuer(pixmap):
    """Tuile en gris clair : les couleurs restent réservées aux points."""
    image = pixmap.toImage().convertToFormat(QImage.Format_Grayscale8)
    image = image.convertToFormat(QImage.Format_RGB32)
    peintre = QPainter(image)
    peintre.setOpacity(0.45)
    peintre.fillRect(image.rect(), QColor("#F5F6F3"))
    peintre.end()
    return QPixmap.fromImage(image)


def vers_pixels(lon, lat, zoom):
    """Longitude, latitude (WGS 84) -> pixels Web Mercator au niveau zoom."""
    n = 256 * 2 ** zoom
    lat = max(min(lat, 85.0511), -85.0511)
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def vers_degres(x, y, zoom):
    n = 256 * 2 ** zoom
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


class PointCarte(QGraphicsEllipseItem):
    """Un périmètre sur la carte : le clic le sélectionne."""

    def __init__(self, carte, nom, rayon):
        super().__init__(-rayon, -rayon, 2 * rayon, 2 * rayon)
        self.carte, self.nom = carte, nom
        self.setCursor(Qt.PointingHandCursor)
        self.setZValue(10)

    def mousePressEvent(self, evenement):
        self.carte.point_choisi.emit(self.nom)
        evenement.accept()


class Carte(QGraphicsView):
    """Carte en tuiles (xyzservices), stable : pas de navigateur intégré.

    Les tuiles téléchargées sont gardées dans DOSSIER_CACHE_CARTE ; sans
    connexion, la carte affiche les tuiles déjà vues, ou un fond uni.
    """

    point_choisi = Signal(str)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor("#EEF0ED"))
        self.adresse, attribution, self.zoom_max = fond_de_carte(FOND_DE_CARTE)
        self.cache = chemin_local(os.path.join(
            chemin_local(DOSSIER_CACHE_CARTE), creer_id(FOND_DE_CARTE) or "fond"))
        self.reseau = QNetworkAccessManager(self)
        self.reseau.finished.connect(self.tuile_recue)
        self.zoom, self.tuiles, self.demandes = 7, {}, set()
        self.points, self.choisi, self.dessins = [], None, []
        self.minuterie = QTimer(self, singleShot=True, interval=60)
        self.minuterie.timeout.connect(self.charger_tuiles)
        # Commandes et mentions posées sur la carte.
        self.commandes = QFrame(self)
        ligne = QVBoxLayout(self.commandes)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(6)
        for texte, aide, action in (("+", "Zoomer", lambda: self.zoomer(1)),
                                    ("−", "Dézoomer", lambda: self.zoomer(-1)),
                                    ("⤢", "Tout voir", self.ajuster)):
            bouton = QToolButton(text=texte, objectName="carte", toolTip=aide)
            bouton.clicked.connect(action)
            ligne.addWidget(bouton)
        self.legende = QLabel(self, objectName="surCarte")
        self.message = QLabel(self, objectName="surCarte",
                              wordWrap=True, alignment=Qt.AlignCenter)
        self.mention = QLabel(attribution, self, objectName="attribution",
                              openExternalLinks=True,
                              textFormat=Qt.RichText)

    # ------------------------------ Placement ------------------------------
    def showEvent(self, evenement):
        super().showEvent(evenement)
        if not getattr(self, "deja_vue", False):
            self.deja_vue = True
            QTimer.singleShot(0, self.ajuster)

    def resizeEvent(self, evenement):
        super().resizeEvent(evenement)
        self.placer_mentions()
        self.minuterie.start()

    def placer_mentions(self):
        # Posées sur la vue, pas sur le contenu : elles ne défilent pas.
        zone = self.viewport().geometry()
        self.commandes.adjustSize()
        self.commandes.move(zone.left() + 12, zone.top() + 12)
        self.mention.adjustSize()
        self.mention.move(zone.right() - self.mention.width(),
                          zone.bottom() - self.mention.height())
        self.legende.adjustSize()
        self.legende.move(zone.right() - self.legende.width() - 12,
                          zone.top() + 12)
        self.message.setFixedWidth(min(420, zone.width() - 40))
        self.message.adjustSize()
        self.message.move(zone.center().x() - self.message.width() // 2,
                          zone.center().y() - self.message.height() // 2)

    def drawBackground(self, peintre, zone):
        """Fond uni et quadrillage en degrés : la carte reste lisible
        hors connexion ; les tuiles, quand elles arrivent, le recouvrent."""
        super().drawBackground(peintre, zone)
        lon0, lat1 = vers_degres(zone.left(), zone.top(), self.zoom)
        lon1, lat0 = vers_degres(zone.right(), zone.bottom(), self.zoom)
        etendue = max(lon1 - lon0, 1e-6)
        pas = next(p for p in (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30)
                   if etendue / p <= 12)
        peintre.setPen(QPen(QColor("#D9DDD8"), 0))
        police = QFont("Inter")
        police.setPointSize(8)
        peintre.setFont(police)
        lon = math.floor(lon0 / pas) * pas
        while lon <= lon1:
            x, _y = vers_pixels(lon, 0, self.zoom)
            peintre.drawLine(QPointF(x, zone.top()), QPointF(x, zone.bottom()))
            peintre.drawText(QPointF(x + 3, zone.bottom() - 4), "%g°" % lon)
            lon += pas
        lat = math.floor(lat0 / pas) * pas
        while lat <= lat1:
            _x, y = vers_pixels(0, lat, self.zoom)
            peintre.drawLine(QPointF(zone.left(), y), QPointF(zone.right(), y))
            peintre.drawText(QPointF(zone.left() + 54, y - 3), "%g°" % lat)
            lat += pas

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.minuterie.start()

    def wheelEvent(self, evenement):
        self.zoomer(1 if evenement.angleDelta().y() > 0 else -1,
                    evenement.position())

    # -------------------------------- Zoom ---------------------------------
    def centre_degres(self):
        centre = self.mapToScene(self.viewport().rect().center())
        return vers_degres(centre.x(), centre.y(), self.zoom)

    def zoomer(self, pas, curseur=None):
        nouveau = max(2, min(self.zoom_max, self.zoom + pas))
        if nouveau == self.zoom:
            return
        if curseur is None:
            curseur = QPointF(self.viewport().rect().center())
        ici = self.mapToScene(curseur.toPoint())
        lon, lat = vers_degres(ici.x(), ici.y(), self.zoom)
        self.aller(nouveau, lon, lat,
                   curseur - QPointF(self.viewport().rect().center()))

    def aller(self, zoom, lon, lat, ecart=QPointF(0, 0)):
        """Niveau zoom, avec (lon, lat) au centre, décalé de ecart pixels."""
        self.zoom = zoom
        for element in list(self.tuiles.values()):
            self.scene().removeItem(element)
        self.tuiles = {}
        n = 256 * 2 ** zoom
        self.scene().setSceneRect(0, 0, n, n)
        self.dessiner_points()
        x, y = vers_pixels(lon, lat, zoom)
        self.centerOn(x - ecart.x(), y - ecart.y())
        self.minuterie.start()

    def ajuster(self):
        """Cadre tous les périmètres qui ont des coordonnées."""
        places = [(p["x"], p["y"]) for p in self.points]
        if not places:
            self.aller(5, -14.5, 14.5)     # vue d'ensemble par défaut
            return
        lon = [x for x, _y in places]
        lat = [y for _x, y in places]
        largeur = max(self.viewport().width() - 260, 100)   # place des noms
        hauteur = max(self.viewport().height() - 140, 100)
        zoom = 2
        for z in range(self.zoom_max, 1, -1):
            x0, y0 = vers_pixels(min(lon), max(lat), z)
            x1, y1 = vers_pixels(max(lon), min(lat), z)
            if x1 - x0 <= largeur and y1 - y0 <= hauteur:
                zoom = z
                break
        x0, y0 = vers_pixels(min(lon), max(lat), zoom)
        x1, y1 = vers_pixels(max(lon), min(lat), zoom)
        centre = vers_degres((x0 + x1) / 2, (y0 + y1) / 2, zoom)
        self.aller(min(zoom, 12), *centre)

    # ------------------------------- Tuiles --------------------------------
    def fichier_tuile(self, z, x, y):
        return os.path.join(self.cache, str(z), str(x), "%d.png" % y)

    def charger_tuiles(self):
        zone = self.mapToScene(self.viewport().rect()).boundingRect()
        n = 2 ** self.zoom
        x0, x1 = int(max(zone.left(), 0) // 256), int(zone.right() // 256)
        y0, y1 = int(max(zone.top(), 0) // 256), int(zone.bottom() // 256)
        for x in range(x0, min(x1, n - 1) + 1):
            for y in range(y0, min(y1, n - 1) + 1):
                cle = (self.zoom, x, y)
                if cle in self.tuiles or cle in self.demandes:
                    continue
                fichier = self.fichier_tuile(*cle)
                if os.path.exists(fichier):
                    self.poser_tuile(cle, QPixmap(fichier))
                    continue
                demande = QNetworkRequest(QUrl(self.adresse.format(
                    z=self.zoom, x=x, y=y)))
                demande.setRawHeader(b"User-Agent", AGENT_UTILISATEUR)
                demande.setAttribute(QNetworkRequest.User, "%d/%d/%d" % cle)
                self.demandes.add(cle)
                self.reseau.get(demande)

    def tuile_recue(self, reponse):
        cle = reponse.request().attribute(QNetworkRequest.User)
        cle = tuple(int(v) for v in str(cle).split("/")) if cle else None
        self.demandes.discard(cle)
        donnees = bytes(reponse.readAll())
        reponse.deleteLater()
        if cle is None or reponse.error() != QNetworkReply.NoError:
            return                       # hors ligne : le fond uni reste
        image = QPixmap()
        if not image.loadFromData(donnees):
            return
        fichier = self.fichier_tuile(*cle)
        try:
            os.makedirs(os.path.dirname(fichier), exist_ok=True)
            image.save(fichier, "PNG")
        except OSError:
            pass
        if cle[0] == self.zoom:
            self.poser_tuile(cle, image)

    def poser_tuile(self, cle, image):
        if image.isNull():
            return
        if CARTE_ATTENUEE:
            image = attenuer(image)
        tuile = QGraphicsPixmapItem(image)
        tuile.setPos(cle[1] * 256, cle[2] * 256)
        tuile.setZValue(0)
        tuile.setTransformationMode(Qt.SmoothTransformation)
        self.scene().addItem(tuile)
        self.tuiles[cle] = tuile

    # ------------------------------- Points --------------------------------
    def montrer(self, points, choisi=None, legende=None, message=""):
        """points : dictionnaires nom, x (longitude), y (latitude), couleur."""
        premiere = not self.points and points
        self.points, self.choisi = points, choisi
        self.legende.setText(legende or "")
        self.legende.setVisible(bool(legende))
        self.message.setText(message)
        self.message.setVisible(bool(message))
        if premiere or not self.scene().sceneRect().width():
            self.ajuster()
        else:
            self.dessiner_points()
        self.placer_mentions()

    def dessiner_points(self):
        scene = self.scene()
        for element in self.dessins:
            scene.removeItem(element)
        self.dessins = []
        for p in self.points:
            x, y = vers_pixels(p["x"], p["y"], self.zoom)
            choisi = p["nom"] == self.choisi
            if choisi:
                halo = QGraphicsEllipseItem(-15, -15, 30, 30)
                halo.setPos(x, y)
                halo.setBrush(QColor(p["couleur"]).lighter(185))
                halo.setPen(QPen(QColor(p["couleur"]), 1.5))
                halo.setZValue(9)
                scene.addItem(halo)
                self.dessins.append(halo)
            point = PointCarte(self, p["nom"], p.get("rayon")
                               or (8 if choisi else 6.5))
            point.setPos(x, y)
            point.setBrush(QColor(p["couleur"]))
            point.setPen(QPen(QColor("#FFFFFF"), 2))
            scene.addItem(point)
            etiquette = QGraphicsSimpleTextItem(
                p["nom"] + ("   " + p["texte"] if p.get("texte") else ""))
            police = QFont("Inter")
            police.setPointSize(10)
            police.setBold(choisi)
            etiquette.setFont(police)
            taille = etiquette.boundingRect()
            fond = scene.addRect(taille.adjusted(-4, -1, 4, 1), Qt.NoPen,
                                 QBrush(QColor(255, 255, 255, 215)))
            ecart = max(12, (p.get("rayon") or 0) + 6)
            for element in (fond, etiquette):
                element.setPos(x + ecart, y - taille.height() / 2)
            fond.setZValue(11)
            etiquette.setZValue(12)
            etiquette.setBrush(QColor(ENCRE))
            scene.addItem(etiquette)
            self.dessins += [point, fond, etiquette]


# ============================== PARAMÈTRES ==============================
RE_UNITE = re.compile(r"(\d+\.?\d*(?:[eE][+-]?\d+)?)\s*(\[[^\]]*\])")
RE_NOM = re.compile(r"([A-Za-z_]\w*)\s*\[([^\]]*)\]")
RE_APPEL = re.compile(r"([A-Za-z_]\w*)\s*\(")
RE_TEXTE = re.compile(r'"[^"]*"')
ORDRE_ORIGINES = ("Base", "Paramètre", "Flux", "Physique", "Charge", "Poste",
                  "Conversion")
TITRES_ORIGINES = {"Base": "BASE", "Paramètre": "PARAMÈTRES",
                   "Flux": "FLUX FINANCIERS", "Physique": "FLUX PHYSIQUES",
                   "Charge": "CHARGES", "Poste": "POSTES",
                   "Conversion": "CONVERSIONS"}
COULEURS_ETAT = {"Défini": "#2E8B57", "À définir": "#D9822B",
                 "Circulaire": "#2467B5"}
BASE_TEMPS = (
    ("t", "Temps du modèle : t = t0 + t*"),
    ("t0", "Date de démarrage, dans l'unité de référence du temps"),
    ("t_sim", "t* : n × pas de temps, vaut 0 au démarrage"),
    ("t_jour", "Temps écoulé en jours depuis le démarrage"),
    ("t_mois", "Temps écoulé en mois depuis le démarrage"),
    ("t_an", "Temps écoulé en années depuis le démarrage"),
    ("t[annee]", "Année du calendrier"),
    ("t[mois]", "Mois du calendrier, de 1 à 12"),
    ("t[jour]", "Jour du mois, de 1 à 31"),
)


def origine_parametre(modele, i):
    if modele.parametres[i].get("conversion"):
        return "Conversion"
    if i in modele.flux:
        return "Flux" if modele.flux[i]["nature"] == "Financier" \
            else "Physique"
    if i in modele.charges:
        return "Charge"
    return "Poste" if i in modele.postes else "Paramètre"


def id_ecrit(nom, dedans):
    """nom[structure, Dakar] tel qu'écrit -> identifiant x[s,dakar]."""
    try:
        return "%s[%s]" % (creer_id(nom), ",".join(
            creer_id(morceau) for morceau in dedans.split(",")))
    except ErreurModele:
        return ""


class Surligneur(QSyntaxHighlighter):
    """Couleurs de la formule : variables connues, nouvelles, fonctions."""

    def __init__(self, document, fenetre):
        super().__init__(document)
        self.fenetre = fenetre
        self.formats = {}
        for cle, couleur, gras, italique in (
                ("connu", "#0B6E66", True, False),
                ("nouveau", "#C2610C", True, False),
                ("temps", "#2467B5", True, False),
                ("fonction", "#6B3FA0", False, False),
                ("inconnue", "#C0392B", False, False),
                ("unite", "#7A8784", False, True),
                ("texte", "#8C4A2F", False, False)):
            forme = QTextCharFormat()
            forme.setForeground(QColor(couleur))
            forme.setFontWeight(QFont.DemiBold if gras else QFont.Normal)
            forme.setFontItalic(italique)
            self.formats[cle] = forme

    def statut(self, identifiant):
        modele = self.fenetre.modele
        if identifiant.startswith("t[") or identifiant in VARIABLES_SYSTEME:
            return "temps"
        return "connu" if indexee(identifiant) in modele.parametres \
            or identifiant in modele.post else "nouveau"

    def highlightBlock(self, texte):
        couverts = []
        for trouve in RE_TEXTE.finditer(texte):
            self.setFormat(trouve.start(), len(trouve.group()),
                           self.formats["texte"])
            couverts.append(trouve.span())
        for trouve in RE_UNITE.finditer(texte):
            debut, fin = trouve.span(2)
            self.setFormat(debut, fin - debut, self.formats["unite"])
            couverts.append((debut, fin))

        def libre(position):
            return not any(a <= position < b for a, b in couverts)

        for trouve in RE_NOM.finditer(texte):
            if not libre(trouve.start()):
                continue
            identifiant = id_ecrit(trouve.group(1), trouve.group(2))
            if trouve.group(1) == "t":
                identifiant = "t[" + creer_id(trouve.group(2) or "x") + "]"
            self.setFormat(trouve.start(), len(trouve.group()),
                           self.formats[self.statut(identifiant)])
        connues = FONCTIONS | FONCTIONS_POST | set(FONCTIONS_UTILISATEUR) \
            | MOTS_CLES
        for trouve in RE_APPEL.finditer(texte):
            if libre(trouve.start()):
                self.setFormat(trouve.start(), len(trouve.group(1)),
                               self.formats["fonction" if trouve.group(1)
                                            in connues else "inconnue"])


def nombre_tableau(valeur, genre="ligne"):
    """Nombre d'un tableau de résultats : 1 234 567, 12,5 %, 1,25."""
    if valeur is None:
        return "—"
    if isinstance(valeur, str):
        return valeur
    if abs(valeur) < 1e-6:               # reste d'arrondi du calcul
        return "0"
    if genre == "pourcent":
        return ("%.1f %%" % valeur).replace(".", ",")
    if genre == "ratio":
        return ("%.2f" % valeur).replace(".", ",")
    if abs(valeur) >= 100 or valeur == int(valeur):
        return "{:,.0f}".format(valeur).replace(",", "\u202f")
    return ("%.3g" % valeur).replace(".", ",")


def pas_rond(etendue, nombre=5):
    """Pas « rond » (1, 2, 2,5 ou 5 × 10^k) pour environ nombre graduations."""
    if etendue <= 0:
        return 1.0
    brut = etendue / nombre
    puissance = 10 ** math.floor(math.log10(brut))
    for facteur in (1, 2, 2.5, 5, 10):
        if facteur * puissance >= brut:
            return facteur * puissance
    return 10 * puissance


def nombre_court(valeur):
    """1 800 000 -> « 1,8 M » ; 12 500 -> « 12 500 » ; 0,05 -> « 0,05 »."""
    absolu = abs(valeur)
    for seuil, suffixe in ((1e9, " Md"), (1e6, " M")):
        if absolu >= seuil:
            return ("%.3g" % (valeur / seuil)).replace(".", ",") + suffixe
    if absolu >= 1000:
        return "{:,.0f}".format(valeur).replace(",", " ")
    if absolu == 0:
        return "0"
    return ("%.3g" % valeur).replace(".", ",")


class DiagrammeArgent(QWidget):
    """Diagramme « Où va l'argent » : bandes proportionnelles aux montants.

    Les structures sont placées en colonnes, de celles qui apportent
    l'argent (usagers...) vers celles qui le reçoivent ; à droite de chaque
    structure partent ses charges, ses investissements et ce qui lui reste.
    """

    TERMINAUX = {   # genre : (libellé, couleur de bande, couleur de barre)
        "reste": ("Reste à", "#BFE3DC", VERT),
        "charges": ("Charges", "#F6D9B5", "#A34F0B"),
        "investissements": ("Investissements", "#C9DDF4", "#2467B5"),
    }
    BARRE, ECART, MARGE = 12, 22, 18
    GAUCHE, DROITE = 190, 210          # place des étiquettes de bord

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(380)
        self.donnees = None
        self.setMouseTracking(True)

    def montrer(self, donnees):
        self.donnees = donnees
        self.update()

    # Mise en page
    def disposer(self):
        d = self.donnees
        liens = d["liens"]
        actives = [s for s in d["structures"]
                   if any(s in (a, b) for a, b, _v, _n in liens)
                   or d["charges"][s] or d["investissements"][s]]
        if not actives:
            return [], []
        # Colonnes : plus long chemin depuis les apporteurs, boucles ignorées.
        ordre = sorted(actives, key=lambda s: d["restes"][s])
        sortants = {s: [b for a, b, _v, _n in liens if a == s] for s in actives}
        etat, arcs = {}, []

        def parcourir(s):
            etat[s] = 1
            for b in sortants[s]:
                if etat.get(b) == 1:
                    continue                          # arc retour : boucle
                arcs.append((s, b))
                if b not in etat:
                    parcourir(b)
            etat[s] = 2

        for s in ordre:
            if s not in etat:
                parcourir(s)
        colonne = dict.fromkeys(actives, 0)
        for _tour in range(len(actives)):
            for a, b in arcs:
                colonne[b] = max(colonne[b], colonne[a] + 1)
        # Nœuds : structures et terminaux.
        noeuds = {}
        for s in actives:
            entree = sum(v for a, b, v, _n in liens if b == s)
            sortie = sum(v for a, b, v, _n in liens if a == s)
            sortie += d["charges"][s] + d["investissements"][s]
            sortie += max(d["restes"][s], 0.0)
            noeuds[s] = {"genre": "structure", "col": colonne[s],
                         "valeur": max(entree, sortie), "parent": None}
        for s in actives:
            for genre, valeur in (("charges", d["charges"][s]),
                                  ("investissements",
                                   d["investissements"][s]),
                                  ("reste", d["restes"][s])):
                if valeur > 1e-9:
                    noeuds[(genre, s)] = {"genre": genre, "parent": s,
                                          "col": colonne[s] + 1,
                                          "valeur": valeur}
        aretes = [(a, b, v, n) for a, b, v, n in liens
                  if a in noeuds and b in noeuds]
        aretes += [(cle[1], cle, n["valeur"], None) for cle, n in noeuds.items()
                   if n["parent"]]
        # Arcs « retour » (boucles) : dessinés sous le diagramme.
        retours = [(a, b) for a, b, _v, _n in aretes
                   if noeuds[b]["col"] <= noeuds[a]["col"]]
        valeur_retours = sum(v for a, b, v, _n in aretes
                             if (a, b) in retours)
        # Échelle commune à toutes les colonnes.
        colonnes = sorted({n["col"] for n in noeuds.values()})
        hauteur = self.height() - 2 * self.MARGE - 10
        hauteur -= 16 * len(retours)

        def echelle_pour(hauteur):
            return max(0.0, min(
                (hauteur - self.ECART * (len(membres) - 1))
                / (sum(n["valeur"] for n in membres) or 1.0)
                for c in colonnes
                for membres in [[n for n in noeuds.values()
                                 if n["col"] == c]]))

        echelle = echelle_pour(hauteur)
        if valeur_retours:
            hauteur -= valeur_retours * echelle
            echelle = echelle_pour(hauteur)
        largeur = self.width() - 2 * self.MARGE - self.GAUCHE - self.DROITE
        pas_x = largeur / (len(colonnes) - 1) if len(colonnes) > 1 else 0
        # Placement vertical, colonne par colonne (barycentre des sources).
        rang_initial = {cle: k for k, cle in enumerate(noeuds)}
        for c in colonnes:
            membres = [cle for cle, n in noeuds.items() if n["col"] == c]

            def centre_sources(cle):
                sources = [(noeuds[a], v) for a, b, v, _n in aretes
                           if b == cle and "y" in noeuds[a]]
                if not sources:
                    return (1e9, rang_initial[cle])
                poids = sum(v for _n, v in sources) or 1.0
                return (sum((n["y"] + n["h"] / 2) * v for n, v in sources)
                        / poids, rang_initial[cle])

            membres.sort(key=centre_sources)
            total = sum(noeuds[k]["valeur"] * echelle for k in membres)
            total += self.ECART * (len(membres) - 1)
            y = self.MARGE + 10 + max(0.0, (hauteur - total) / 2)
            for cle in membres:
                n = noeuds[cle]
                n["h"] = max(n["valeur"] * echelle, 2.0)
                n["y"] = y
                n["x"] = self.MARGE + self.GAUCHE + colonnes.index(c) * pas_x
                y += n["h"] + self.ECART
        # Décalages des bandes au départ et à l'arrivée.
        bandes = []
        depart = {cle: n["y"] for cle, n in noeuds.items()}
        arrivee = dict(depart)
        bas = self.MARGE + 10 + hauteur + 14
        for a, b, v, nf in sorted(aretes, key=lambda t: (
                (t[0], t[1]) in retours, noeuds[t[0]]["y"],
                noeuds[t[1]]["y"])):
            epaisseur = v * echelle
            bande = {"de": a, "vers": b, "valeur": v, "noms": nf,
                     "y0": depart[a], "y1": arrivee[b], "e": epaisseur,
                     "retour": (a, b) in retours}
            if bande["retour"]:
                bande["bas"] = bas
                bas += max(epaisseur, 2.0) + 16
            bandes.append(bande)
            depart[a] += epaisseur
            arrivee[b] += epaisseur
        return noeuds, bandes

    def couleur_bande(self, bande, noeuds):
        cible = noeuds[bande["vers"]]
        if cible["genre"] == "structure":
            couleur = QColor(COULEURS_TYPES.get(
                self.donnees["types"][bande["vers"]], FOND_AUTRE)[1])
            couleur.setAlpha(60 if bande["retour"] else 110)
        else:
            couleur = QColor(self.TERMINAUX[cible["genre"]][1])
        return couleur

    def chemin_bande(self, bande, noeuds):
        n0, n1 = noeuds[bande["de"]], noeuds[bande["vers"]]
        x0, x1, e = n0["x"] + self.BARRE, n1["x"], max(bande["e"], 1.0)
        y0, y1 = bande["y0"], bande["y1"]
        if not bande["retour"]:
            milieu = (x0 + x1) / 2
            chemin = QPainterPath(QPointF(x0, y0))
            chemin.cubicTo(milieu, y0, milieu, y1, x1, y1)
            chemin.lineTo(x1, y1 + e)
            chemin.cubicTo(milieu, y1 + e, milieu, y0 + e, x0, y0 + e)
            chemin.closeSubpath()
            return chemin
        # Boucle : on sort à droite, on passe sous le diagramme, on revient
        # par la gauche de la structure qui reçoit.
        bas, r = bande["bas"], 30.0
        trace = QPainterPath(QPointF(x0, y0 + e / 2))
        trace.cubicTo(x0 + r + e, y0 + e / 2, x0 + r + e, bas + e / 2,
                      x0, bas + e / 2)
        trace.lineTo(x1, bas + e / 2)
        trace.cubicTo(x1 - r - e, bas + e / 2, x1 - r - e, y1 + e / 2,
                      x1, y1 + e / 2)
        contour = QPainterPathStroker()
        contour.setWidth(e)
        contour.setCapStyle(Qt.FlatCap)
        return contour.createStroke(trace)

    def texte_montant(self, v):
        d = self.donnees
        texte = nombre_court(v) + (" " + d["monnaie"] if d["monnaie"] else "")
        if d["apporte"]:
            texte += ", %s %%" % ("%.1f" % (100 * v / d["apporte"])).replace(
                ".", ",")
        return texte

    def paintEvent(self, _evenement):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.Antialiasing)
        peintre.fillRect(self.rect(), QColor("#FFFFFF"))
        police = QFont("Inter")
        police.setPointSize(9)
        gras = QFont(police)
        gras.setBold(True)
        peintre.setFont(police)
        d = self.donnees
        noeuds, bandes = self.disposer() if d else ([], [])
        self.zones = []                              # pour les infobulles
        if not noeuds:
            peintre.setPen(QColor(GRIS))
            peintre.drawText(QRectF(self.rect()), Qt.AlignCenter,
                             tr("Pas de flux d'argent sur cette période."))
            return
        b, montant = self.BARRE, self.texte_montant
        # Bandes.
        for bande in bandes:
            chemin = self.chemin_bande(bande, noeuds)
            peintre.fillPath(chemin, self.couleur_bande(bande, noeuds))
            if noeuds[bande["vers"]]["genre"] == "structure":
                noms = bande["noms"] or [tr("Paiements")]
                info = "%s\n%s → %s\n%s" % (
                    ", ".join(noms), d["noms"][bande["de"]],
                    d["noms"][bande["vers"]], montant(bande["valeur"]))
            else:
                parent = noeuds[bande["vers"]]["parent"]
                info = "%s\n%s\n%s" % (
                    self.libelle(noeuds[bande["vers"]]["genre"]),
                    d["noms"][parent], montant(bande["valeur"]))
            self.zones.append((chemin, info))
        # Barres.
        for cle, n in noeuds.items():
            rect = QRectF(n["x"], n["y"], b, n["h"])
            if n["genre"] == "structure":
                couleur = COULEURS_TYPES.get(d["types"][cle], FOND_AUTRE)[1]
            else:
                couleur = self.TERMINAUX[n["genre"]][2]
            peintre.setPen(Qt.NoPen)
            peintre.setBrush(QColor(couleur))
            peintre.drawRoundedRect(rect, 3, 3)
            chemin = QPainterPath()
            chemin.addRect(rect.adjusted(-3, -3, 3, 3))
            if n["genre"] == "structure":
                info = d["noms"][cle]
                if d["restes"][cle] < -1e-9:
                    info += "\n" + tr("Apporte") + " " + montant(
                        -d["restes"][cle])
            else:
                info = "%s\n%s\n%s" % (self.libelle(n["genre"]),
                                         d["noms"][n["parent"]],
                                         montant(n["valeur"]))
            self.zones.append((chemin, info))
        # Étiquettes, placées sans se chevaucher (sinon : infobulle).
        occupees = [QRectF(n["x"] - 2, n["y"], b + 4, n["h"])
                    for n in noeuds.values()]
        etiquettes = []
        premiere = min(n["col"] for n in noeuds.values())
        for cle, n in noeuds.items():
            centre = n["y"] + n["h"] / 2
            if n["genre"] == "structure":
                lignes = [d["noms"][cle]]
                if d["restes"][cle] < -1e-9:
                    lignes.append(tr("Apporte") + " " + montant(
                        -d["restes"][cle]))
                if n["col"] == premiere:
                    etiquettes.append((0, n["x"] - 8, centre, lignes,
                                       Qt.AlignRight))
                else:
                    etiquettes.append((0, n["x"], n["y"] - 11, lignes[:1],
                                       Qt.AlignLeft))
            else:
                etiquettes.append((1, n["x"] + b + 8, centre,
                                   [self.libelle(n["genre"]),
                                    d["noms"][n["parent"]],
                                    montant(n["valeur"])], Qt.AlignLeft))
        for bande in bandes:
            if noeuds[bande["vers"]]["genre"] != "structure":
                continue
            noms = bande["noms"] or []
            titre = ", ".join(noms[:2]) + ("…" if len(noms) > 2 else "")
            lignes = [titre or tr("Paiements"), montant(bande["valeur"])]
            n0 = noeuds[bande["de"]]
            if bande["retour"]:
                n1 = noeuds[bande["vers"]]
                x = (n0["x"] + n1["x"]) / 2
                y = bande["bas"] + bande["e"] / 2
                etiquettes.append((2, x, y, lignes, Qt.AlignLeft))
            else:
                etiquettes.append((2, n0["x"] + b + 10,
                                   bande["y0"] + bande["e"] / 2, lignes,
                                   Qt.AlignLeft))
        for _rang, x, y, lignes, aligner in sorted(etiquettes,
                                                   key=lambda t: t[0]):
            self.poser(peintre, police, gras, occupees, x, y, lignes, aligner)

    def libelle(self, genre):
        return tr("Reste") if genre == "reste" else tr(
            self.TERMINAUX[genre][0])

    def poser(self, peintre, police, gras, occupees, x, y, lignes, aligner):
        """Pose une étiquette à l'endroit libre le plus proche de (x, y)."""
        hauteur = 15 * len(lignes)
        largeur = max(QFontMetricsF(gras if k == 0 else police)
                      .horizontalAdvance(t) for k, t in enumerate(lignes))
        gauche = x - largeur if aligner == Qt.AlignRight else x
        gauche = max(2.0, min(gauche, self.width() - largeur - 4))
        for decalage in (0, 1, -1, 2, -2, 3, -3):
            haut = y - hauteur / 2 + decalage * (hauteur / 2 + 4)
            fond = QRectF(gauche - 3, haut - 2, largeur + 6, hauteur + 4)
            if fond.top() < 0 or fond.bottom() > self.height():
                continue
            if not any(fond.intersects(r) for r in occupees):
                break
        else:
            return                                    # pas de place libre
        occupees.append(fond)
        peintre.fillRect(fond, QColor(255, 255, 255, 215))
        for k, texte in enumerate(lignes):
            peintre.setFont(gras if k == 0 else police)
            peintre.setPen(QColor(ENCRE if k == 0 else "#33423F"))
            peintre.drawText(QRectF(gauche, haut + 15 * k, largeur, 15),
                             aligner | Qt.AlignVCenter, texte)

    def mouseMoveEvent(self, evenement):
        point = evenement.position()
        for chemin, info in reversed(getattr(self, "zones", [])):
            if chemin.contains(point):
                QToolTip.showText(evenement.globalPosition().toPoint(), info,
                                  self)
                return
        QToolTip.hideText()


class Apercu(QWidget):
    """Courbe d'aperçu d'un paramètre (formule simulée ou table saisie).

    Quadrillage vertical à chaque unité de temps de référence quand l'axe
    horizontal est le temps ; graduations rondes et lisibles en ordonnée.
    """

    PAS_TEMPS = {"an": 1.0, "mois": 1 / 12, "jour": 1 / 365, "j": 1 / 365}
    # Abscisse en années : une ligne par unité de temps de référence.

    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 260)
        self.courbes, self.message, self.unite = [], "", ""
        self.temps, self.pas_temps = True, 1.0

    def montrer(self, courbes, temps=True, pas_temps=1.0, unite="",
                message=""):
        """courbes : (nom, couleur, [(x, y)...], paliers).

        temps : l'abscisse est un temps ; pas_temps est alors l'écart entre
        deux lignes verticales (1 an, 1/12 d'an pour un mois...).
        """
        self.courbes, self.temps, self.pas_temps = courbes, temps, pas_temps
        self.unite, self.message = unite, tr(message)
        self.update()

    def paintEvent(self, _evenement):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.Antialiasing)
        police = QFont("Inter")
        police.setPointSize(9)
        peintre.setFont(police)
        mesure = peintre.fontMetrics()
        points = [p for c in self.courbes for p in c[2]]
        if not points:
            peintre.setPen(QColor(GRIS))
            peintre.drawText(QRectF(self.rect()).adjusted(16, 16, -16, -16),
                             Qt.AlignCenter | Qt.TextWordWrap,
                             self.message or tr("Aperçu de la courbe"))
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, x1 = min(xs), max(xs)
        if self.courbes and self.courbes[0][3] and self.temps:
            x1 += self.pas_temps                      # dernier palier
        if x1 <= x0:
            x1 = x0 + 1
        y0, y1 = min(ys + [0.0]), max(ys + [0.0])
        if y1 <= y0:
            y1 = y0 + 1
        pas_y = pas_rond(y1 - y0)
        y0 = math.floor(y0 / pas_y) * pas_y
        y1 = math.ceil(y1 / pas_y) * pas_y
        graduations = []
        y = y0
        while y <= y1 + pas_y / 2:
            graduations.append(y)
            y += pas_y
        gauche = max(mesure.horizontalAdvance(nombre_court(g))
                     for g in graduations) + 14
        zone = QRectF(self.rect()).adjusted(gauche, 24, -14, -26)

        def place(x, y):
            return QPointF(zone.left() + (x - x0) / (x1 - x0) * zone.width(),
                           zone.bottom() - (y - y0) / (y1 - y0)
                           * zone.height())

        # Quadrillage horizontal et ordonnées.
        for g in graduations:
            ici = place(x0, g).y()
            peintre.setPen(QPen(QColor("#EEF0ED"), 1))
            peintre.drawLine(QPointF(zone.left(), ici),
                             QPointF(zone.right(), ici))
            peintre.setPen(QColor(GRIS))
            peintre.drawText(QRectF(0, ici - 8, gauche - 8, 16),
                             Qt.AlignRight | Qt.AlignVCenter,
                             nombre_court(g))
        if self.unite:
            peintre.drawText(QRectF(4, 2, 300, 16), Qt.AlignLeft,
                             self.unite)
        # Quadrillage vertical : une ligne par unité de temps.
        if self.temps:
            pas_x = self.pas_temps
            while (x1 - x0) / pas_x > 60:          # reste lisible
                pas_x *= 2
            etiquette = max(1, math.ceil((x1 - x0) / 10))
        else:
            pas_x = pas_rond(x1 - x0, 8)
            etiquette = None
        x = math.ceil(x0 / pas_x - 1e-9) * pas_x
        while x <= x1 + 1e-9:
            ici = place(x, y0).x()
            peintre.setPen(QPen(QColor("#E6E9E4"), 1))
            peintre.drawLine(QPointF(ici, zone.top()),
                             QPointF(ici, zone.bottom()))
            entier = abs(x - round(x)) < 1e-6
            if (etiquette is None) or (entier and round(x) % etiquette == 0):
                peintre.setPen(QColor(GRIS))
                peintre.drawText(QRectF(ici - 40, zone.bottom() + 4, 80, 16),
                                 Qt.AlignHCenter,
                                 "%d" % round(x) if self.temps
                                 else nombre_court(x))
            x += pas_x
        peintre.setPen(QPen(QColor("#C9CEC8"), 1))
        peintre.drawLine(zone.bottomLeft(), zone.bottomRight())
        # Courbes.
        for rang, courbe in enumerate(self.courbes):
            nom, couleur, liste, paliers = courbe[:4]
            tirets = len(courbe) > 4 and courbe[4]
            if not liste:
                continue
            chemin = QPainterPath(place(*liste[0]))
            for (xa, ya), (xb, yb) in zip(liste, liste[1:]):
                if paliers:
                    chemin.lineTo(place(xb, ya))
                chemin.lineTo(place(xb, yb))
            if paliers:
                chemin.lineTo(place(x1, liste[-1][1]))
            stylo = QPen(QColor(couleur), 2)
            if tirets:                         # calcul de référence
                stylo.setStyle(Qt.DashLine)
            peintre.setPen(stylo)
            peintre.setBrush(Qt.NoBrush)
            peintre.drawPath(chemin)
            if len(liste) <= 40 and not tirets:
                peintre.setBrush(QColor(couleur))
                peintre.setPen(Qt.NoPen)
                for p in liste:
                    peintre.drawEllipse(place(*p), 2.5, 2.5)
        if len(self.courbes) > 1:                 # légende
            x = zone.right()
            for courbe in reversed(self.courbes):
                nom, couleur = courbe[:2]
                tirets = len(courbe) > 4 and courbe[4]
                repere = 18 if tirets else 10
                largeur = mesure.horizontalAdvance(nom) + repere + 20
                x -= largeur
                if tirets:
                    stylo = QPen(QColor(couleur), 2)
                    stylo.setStyle(Qt.DashLine)
                    peintre.setPen(stylo)
                    peintre.drawLine(QPointF(x + 6, 10), QPointF(x + 24, 10))
                else:
                    peintre.setPen(Qt.NoPen)
                    peintre.setBrush(QColor(couleur))
                    peintre.drawEllipse(QPointF(x + 11, 10), 4, 4)
                peintre.setPen(QColor(ENCRE))
                peintre.drawText(QRectF(x + repere + 12, 2, largeur, 16),
                                 Qt.AlignLeft, nom)
        if self.message:
            peintre.setPen(QColor("#C2610C"))
            peintre.drawText(zone.adjusted(8, 4, -8, -4),
                             Qt.AlignTop | Qt.AlignLeft | Qt.TextWordWrap,
                             self.message)


# ============================== SIMULATION ==============================
TEXTES_OPTIONS = {
    "actuels": ("Tarifs actuels", "Les tarifs saisis, sans changement."),
    "maintien": ("Maintien du service",
                 "Tarif juste suffisant pour équilibrer chaque année."),
    "financement": ("Financement des investissements",
                    "Équilibre atteint à la fin de la période, "
                    "investissements compris."),
}


class CourbeEcart(QWidget):
    """Plus grand écart de la dernière itération, en fonction du temps."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.points, self.total = [], 1

    def paintEvent(self, _evenement):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.Antialiasing)
        police = QFont("Inter")
        police.setPointSize(8)
        peintre.setFont(police)
        zone = QRectF(self.rect()).adjusted(52, 10, -12, -24)
        peintre.setPen(QPen(QColor(FILET), 1))
        peintre.drawRect(zone)
        if not self.points:
            peintre.setPen(QColor(GRIS))
            peintre.drawText(zone, Qt.AlignCenter, tr(
                "Aucune boucle à faire converger pour l'instant."))
            return
        valeurs = [max(p[1], 1e-15) for p in self.points] + \
            [p[2] for p in self.points]
        bas = math.floor(math.log10(min(valeurs)))
        haut = math.ceil(math.log10(max(valeurs)))
        haut = haut if haut > bas else bas + 1

        def px(rang):
            return zone.left() + zone.width() * (rang - 1) / max(
                self.total - 1, 1)

        def py(valeur):
            return zone.bottom() - zone.height() * (
                math.log10(max(valeur, 1e-15)) - bas) / (haut - bas)

        for e in range(bas, haut + 1, max(1, (haut - bas) // 5)):
            peintre.setPen(QPen(QColor("#EEF0ED"), 1))
            peintre.drawLine(QPointF(zone.left(), py(10.0 ** e)),
                             QPointF(zone.right(), py(10.0 ** e)))
            peintre.setPen(QColor(GRIS))
            peintre.drawText(QRectF(0, py(10.0 ** e) - 8, 46, 16),
                             Qt.AlignRight | Qt.AlignVCenter, "1e%d" % e)
        for seuil in sorted({p[2] for p in self.points})[:3]:
            peintre.setPen(QPen(QColor("#C0392B"), 1, Qt.DashLine))
            peintre.drawLine(QPointF(zone.left(), py(seuil)),
                             QPointF(zone.right(), py(seuil)))
            haut_libre = py(seuil) - 16 >= zone.top()
            peintre.drawText(QRectF(zone.right() - 160, py(seuil) - 16
                                    if haut_libre else py(seuil) + 2, 156,
                                    14), Qt.AlignRight,
                             tr("convergence %g" % seuil))
        chemin = QPainterPath(QPointF(px(self.points[0][0]),
                                      py(self.points[0][1])))
        for rang, ecart, _s, _d in self.points[1:]:
            chemin.lineTo(px(rang), py(ecart))
        peintre.setPen(QPen(QColor("#2467B5"), 2))
        peintre.drawPath(chemin)
        peintre.setPen(Qt.NoPen)
        for rang, ecart, seuil, _d in self.points:
            peintre.setBrush(QColor("#2467B5" if ecart <= seuil
                                    else "#C0392B"))
            peintre.drawEllipse(QPointF(px(rang), py(ecart)), 3, 3)
        peintre.setPen(QColor(GRIS))
        peintre.drawText(QRectF(zone.left(), zone.bottom() + 4, 120, 16),
                         Qt.AlignLeft, self.points[0][3])
        peintre.drawText(QRectF(zone.right() - 120, zone.bottom() + 4, 120,
                                16), Qt.AlignRight, self.points[-1][3])


class FenetreCalcul(QDialog):
    """Avancement du calcul ; reçoit les messages du moteur."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Simulation")
        self.setModal(True)
        self.resize(620, 470)
        self.arret = self.fini = False
        self.ecart, self.dernier = None, 0.0
        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(24, 22, 24, 20)
        colonne.setSpacing(10)
        self.titre = QLabel("Calcul en cours", objectName="titre")
        colonne.addWidget(self.titre)
        self.texte = QLabel("Préparation...", objectName="discret")
        colonne.addWidget(self.texte)
        self.barre = QProgressBar(textVisible=False, maximum=1000)
        self.barre.setFixedHeight(8)
        colonne.addWidget(self.barre)
        self.texte_ecart = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.texte_ecart)
        colonne.addWidget(QLabel("Écart maximal à la dernière itération, "
                                 "par pas de temps", objectName="discret"))
        self.courbe = CourbeEcart()
        colonne.addWidget(self.courbe, 1)
        self.bilan = QLabel(wordWrap=True)
        self.bilan.hide()
        colonne.addWidget(self.bilan)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.bouton_arret = QPushButton("Arrêter")
        self.bouton_arret.clicked.connect(self.demander_arret)
        boutons.addWidget(self.bouton_arret)
        self.bouton_fermer = QPushButton("Fermer")
        self.bouton_fermer.clicked.connect(self.accept)
        self.bouton_fermer.hide()
        boutons.addWidget(self.bouton_fermer)
        self.bouton_resultats = QPushButton("Voir les résultats",
                                            objectName="principal")
        self.bouton_resultats.clicked.connect(lambda: self.done(2))
        self.bouton_resultats.hide()
        boutons.addWidget(self.bouton_resultats)
        colonne.addLayout(boutons)

    def demander_arret(self):
        self.arret = True
        self.texte.setText("Arrêt demandé...")

    def reject(self):                     # Échap ou fermeture de la fenêtre
        if self.fini:
            super().reject()
        else:
            self.demander_arret()

    def __call__(self, genre, *donnees):
        if genre == "iteration":
            self.ecart = max(donnees[0],
                             key=lambda v: v[1] / max(v[2], 1e-300))
        else:
            rang, total, date = donnees
            if rang == 1:                   # une nouvelle simulation commence
                self.courbe.points = []
            self.courbe.total = total
            self.barre.setValue(int(1000 * rang / total))
            self.texte.setText("Pas %d sur %d : %s" % (rang, total, date))
            if self.ecart:
                variable, ecart, seuil = self.ecart
                self.texte_ecart.setText(
                    "Écart à la dernière itération : %.3g sur %s "
                    "(convergence %g)" % (ecart, variable, seuil))
                self.courbe.points.append((rang, ecart, seuil, date))
                self.ecart = None
        maintenant = time.monotonic()
        if maintenant - self.dernier > 0.05:
            self.dernier = maintenant
            self.courbe.update()
            QApplication.processEvents()
        if self.arret:
            raise ppp_moteur.ErreurCalcul("Simulation arrêtée.")

    def terminer(self, resultat):
        self.fini = True
        self.courbe.update()
        self.bouton_arret.hide()
        self.bouton_fermer.show()
        reussi = not resultat["erreurs"]
        self.titre.setText("Réussite" if reussi else "Échec")
        self.titre.setStyleSheet("color: %s;" % (VERT if reussi
                                                 else "#C0392B"))
        if reussi:
            self.barre.setValue(1000)
            scenarios = resultat.get("scenarios") or {}
            self.bilan.setText(
                "Simulation terminée%s." % (
                    " : " + ", ".join(TEXTES_OPTIONS[o][0] for o in scenarios)
                    if len(scenarios) > 1 else ""))
            self.bouton_resultats.show()
        else:
            self.bilan.setText('<span style="color:#C0392B">%s</span>'
                               % "<br>".join(resultat["erreurs"][:4]))
        self.bilan.show()


class DelegueSaisie(QStyledItemDelegate):
    """Champ de saisie d'une case ; retient si Entrée a validé."""

    def __init__(self, parent):
        super().__init__(parent)
        self.entree = False

    def createEditor(self, parent, option, index):
        champ = QLineEdit(parent)
        champ.setAlignment(Qt.AlignRight)
        champ.returnPressed.connect(lambda: setattr(self, "entree", True))
        return champ


class PastilleEtat(QStyledItemDelegate):
    """Colore la pastille ● de la liste selon l'état du paramètre."""

    def paint(self, peintre, option, index):
        couleur = index.data(Qt.UserRole + 1)
        texte = index.data(Qt.DisplayRole) or ""
        if not couleur or not texte.startswith("●"):
            super().paint(peintre, option, index)
            return
        self.initStyleOption(option, index)
        option.text = ""
        option.widget.style().drawControl(QStyle.CE_ItemViewItem, option,
                                          peintre, option.widget)
        zone = option.rect.adjusted(4, 0, 0, 0)
        peintre.save()
        peintre.setPen(QColor(couleur))
        peintre.drawText(zone, Qt.AlignVCenter | Qt.AlignLeft, "●")
        peintre.setPen(option.palette.text().color())
        peintre.drawText(zone.adjusted(18, 0, 0, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, texte[3:])
        peintre.restore()


class Fenetre(QMainWindow):
    def __init__(self, modele, chemin):
        super().__init__()
        self.modele, self.chemin = modele, chemin
        self.resultat, self.selection = None, None
        self.dessins_flux, self.boutons_etapes = [], []
        self.forcer_fermeture = False
        self.reference = modele.texte()      # état enregistré du modèle
        self.construire()
        self.recharger()
        for touches, action in (("Ctrl+S", self.enregistrer),
                                ("Ctrl+Shift+S", self.enregistrer_sous),
                                ("Ctrl+O", self.ouvrir),
                                ("Ctrl+N", self.nouveau),
                                ("F5", self.lancer)):
            QShortcut(QKeySequence(touches), self, action)
        for rang in range(len(ETAPES)):
            QShortcut(QKeySequence("Ctrl+%d" % (rang + 1)), self,
                      lambda r=rang: self.choisir(r))

    # ------------------------------ Structure ------------------------------
    def construire(self):
        self.resize(1440, 900)
        centre = QWidget(objectName="page")
        self.setCentralWidget(centre)
        colonne = QVBoxLayout(centre)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(0)
        colonne.addWidget(self.creer_entete())
        corps = QHBoxLayout()
        corps.setSpacing(0)
        colonne.addLayout(corps, 1)
        corps.addWidget(self.creer_rail())
        self.perimetres_modifies = False
        self.structure_choisie, self.flux_en_cours = None, None
        self.dernier_resultat = None      # gardé même si le modèle change
        self.pages = QStackedWidget()
        self.pages.addWidget(self.creer_page_schema())
        self.pages.addWidget(self.creer_page_perimetres())
        self.pages.addWidget(self.creer_page_parametres())
        self.pages.addWidget(self.creer_page_initial())
        self.pages.addWidget(self.creer_page_simulation())
        self.pages.addWidget(self.creer_page_resultats())
        self.pages.addWidget(self.creer_page_post())
        self.pages.addWidget(self.creer_page_fonctions())
        self.page_attente = QLabel(alignment=Qt.AlignCenter,
                                   objectName="discret")
        self.pages.addWidget(self.page_attente)
        corps.addWidget(self.pages, 1)
        self.panneau_fiche = self.creer_fiche()
        corps.addWidget(self.panneau_fiche)

    def creer_entete(self):
        entete = QFrame(objectName="entete")
        ligne = QHBoxLayout(entete)
        ligne.setContentsMargins(24, 10, 24, 10)
        ligne.addWidget(QLabel(TITRE_APPLICATION, objectName="marque"))
        self.nom_projet = QLabel(objectName="discret")
        ligne.addWidget(self.nom_projet)
        ligne.addStretch(1)
        self.etat_calcul = QLabel(objectName="discret")
        ligne.addWidget(self.etat_calcul)
        self.choix_langue = QComboBox()
        self.choix_langue.addItems(["Français", "English"])
        self.choix_langue.setCurrentIndex(
            1 if LANGUE["code"] == "en" else 0)
        self.choix_langue.setToolTip("Langue")
        self.choix_langue.activated.connect(self.changer_langue)
        ligne.addWidget(self.choix_langue)
        nouveau = QPushButton("Nouveau")
        nouveau.setToolTip("Ctrl+N")
        nouveau.clicked.connect(self.nouveau)
        ligne.addWidget(nouveau)
        bouton = QPushButton("Ouvrir")
        bouton.setToolTip("Ctrl+O")
        bouton.clicked.connect(self.ouvrir)
        ligne.addWidget(bouton)
        enregistrer = QToolButton(text="Enregistrer", objectName="export",
                                  popupMode=QToolButton.MenuButtonPopup)
        enregistrer.setToolTip("Ctrl+S")
        enregistrer.clicked.connect(self.enregistrer)
        menu = QMenu(enregistrer)
        menu.addAction("Enregistrer sous...", self.enregistrer_sous)
        enregistrer.setMenu(menu)
        ligne.addWidget(enregistrer)
        lancer = QPushButton("Lancer la simulation", objectName="principal")
        lancer.clicked.connect(self.lancer)
        ligne.addWidget(lancer)
        return entete

    def creer_rail(self):
        rail = QFrame(objectName="rail")
        rail.setFixedWidth(232)
        colonne = QVBoxLayout(rail)
        colonne.setContentsMargins(12, 20, 12, 20)
        colonne.setSpacing(4)
        for rang in range(len(ETAPES)):
            bouton = QPushButton(objectName="etape", checkable=True,
                                 autoExclusive=True)
            bouton.clicked.connect(lambda _c=False, r=rang: self.choisir(r))
            ligne = QHBoxLayout(bouton)
            ligne.setContentsMargins(12, 0, 12, 0)
            bouton.nom = QLabel(ETAPES[rang])
            bouton.etat = QLabel(objectName="discret")
            for element in (bouton.nom, bouton.etat):
                element.setAttribute(Qt.WA_TransparentForMouseEvents)
                element.setStyleSheet("background: transparent")
            ligne.addWidget(bouton.nom)
            ligne.addStretch(1)
            ligne.addWidget(bouton.etat)
            colonne.addWidget(bouton)
            self.boutons_etapes.append(bouton)
        self.boutons_etapes[0].setChecked(True)
        colonne.addStretch(1)
        mention = QLabel(COPYRIGHT, objectName="mention", wordWrap=True)
        colonne.addWidget(mention)
        return rail

    def creer_page_schema(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(24, 24, 24, 24)
        entete = QHBoxLayout()
        entete.addWidget(QLabel("Schéma du projet", objectName="titre"))
        entete.addStretch(1)
        for texte, action in (
                ("+ Structure", self.nouvelle_structure),
                ("+ Flux", self.commencer_flux),
                ("+ Charge", lambda: self.charge_ou_poste(self.e_charge_nom)),
                ("+ Poste", lambda: self.charge_ou_poste(self.e_poste_nom))):
            bouton = QPushButton(texte)
            bouton.clicked.connect(action)
            entete.addWidget(bouton)
        entete.addWidget(self.bouton_impression(
            lambda: (self.schema.scene(), tr("Schéma du projet"), "Schema")))
        colonne.addLayout(entete)
        self.sous_titre = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.sous_titre)
        self.schema = Schema(self)
        colonne.addWidget(self.schema, 1)
        legende = QHBoxLayout()
        legende.addWidget(QLabel("——▶  Flux financier", objectName="discret"))
        legende.addSpacing(24)
        legende.addWidget(QLabel("- - -▶  Flux physique ou service",
                                 objectName="discret"))
        legende.addSpacing(24)
        legende.addWidget(QLabel("Glisser un bloc ou une étiquette pour le "
                                 "déplacer · Suppr pour supprimer l'élément "
                                 "choisi",
                                 objectName="discret"))
        legende.addStretch(1)
        colonne.addLayout(legende)
        return page

    def creer_fiche(self):
        fiche = QFrame(objectName="fiche")
        fiche.setFixedWidth(400)
        exterieur = QVBoxLayout(fiche)
        exterieur.setContentsMargins(0, 0, 0, 0)
        defilement = QScrollArea(widgetResizable=True,
                                 frameShape=QFrame.NoFrame)
        exterieur.addWidget(defilement)
        self.pile_fiche = QStackedWidget()
        contenu = QWidget(objectName="fond")
        boite = QVBoxLayout(contenu)
        boite.setContentsMargins(22, 22, 22, 22)
        boite.addWidget(self.pile_fiche)
        defilement.setWidget(contenu)
        info = QWidget()
        self.pile_fiche.addWidget(info)
        colonne = QVBoxLayout(info)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(10)
        self.fiche_type = QLabel(objectName="discret")
        self.fiche_nom = _Qt.QLabel(objectName="titreFiche", wordWrap=True)
        self.fiche_detail = QLabel(wordWrap=True)
        for element in (self.fiche_type, self.fiche_nom, self.fiche_detail):
            colonne.addWidget(element)
        self.etiquette_formule = QLabel("Formule")
        colonne.addWidget(self.etiquette_formule)
        self.formule = QPlainTextEdit()
        self.formule.setFixedHeight(170)
        colonne.addWidget(self.formule)
        self.controle = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.controle)
        self.resume = QLabel(wordWrap=True)
        colonne.addWidget(self.resume)
        colonne.addStretch(1)
        self.appliquer = QPushButton("Appliquer", objectName="principal")
        self.appliquer.clicked.connect(self.appliquer_formule)
        colonne.addWidget(self.appliquer)
        self.creer_editeurs()
        return fiche

    # ------------------------------ Périmètres ------------------------------
    def creer_page_perimetres(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(24, 24, 24, 16)
        colonne.setSpacing(10)
        colonne.addWidget(QLabel("Périmètres", objectName="titre"))
        colonne.addWidget(QLabel(
            "Une ligne par périmètre p, une colonne par groupe (centre, "
            "région...). Les colonnes X (longitude) et Y (latitude) placent "
            "le périmètre sur la carte. La ligne Global regroupe tout.",
            objectName="discret", wordWrap=True))
        outils = QHBoxLayout()
        outils.setSpacing(8)
        for texte, action in (("+ Périmètre", self.ajouter_perimetre),
                              ("− Périmètre", self.retirer_perimetre),
                              ("+ Colonne", self.ajouter_colonne),
                              ("− Colonne", self.retirer_colonne),
                              ("Importer", self.importer_perimetres),
                              ("Exporter", self.exporter_perimetres)):
            bouton = QPushButton(texte)
            bouton.clicked.connect(action)
            outils.addWidget(bouton)
        outils.addStretch(1)
        outils.addWidget(QLabel("Colorer par", objectName="discret"))
        self.couleur_par = _Qt.QComboBox()   # noms = données
        self.couleur_par.setMinimumWidth(140)
        self.couleur_par.currentIndexChanged.connect(self.dessiner_carte)
        outils.addWidget(self.couleur_par)
        appliquer = QPushButton("Appliquer", objectName="principal")
        appliquer.clicked.connect(self.appliquer_perimetres)
        outils.addWidget(appliquer)
        colonne.addLayout(outils)
        coupe = QSplitter(Qt.Vertical, childrenCollapsible=False)
        self.carte = Carte()
        self.carte.point_choisi.connect(self.choisir_sur_carte)
        coupe.addWidget(self.carte)
        self.table_p = _Qt.QTableWidget()   # en-têtes = données du modèle
        self.table_p.verticalHeader().hide()
        self.table_p.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_p.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_p.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table_p.cellChanged.connect(self.perimetre_modifie)
        self.table_p.itemSelectionChanged.connect(
            lambda: self.ouvrir_perimetre(self.perimetre_choisi()))
        coupe.addWidget(self.table_p)
        coupe.setSizes([520, 240])
        colonne.addWidget(coupe, 1)
        self.etat_perimetres = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.etat_perimetres)
        return page

    def remplir_table(self, colonnes, lignes):
        table = self.table_p
        table.blockSignals(True)
        table.clear()
        table.setColumnCount(1 + len(colonnes))
        table.setHorizontalHeaderLabels([tr("Périmètre")] + list(colonnes))
        table.setRowCount(1 + len(lignes))
        coordonnees = [creer_id(c) in COLONNES_X + COLONNES_Y
                       for c in colonnes]
        valeurs_global = ["Global"] + [
            "" if coord or not lignes else tr("Tous") for coord in coordonnees]
        if not lignes and colonnes:
            valeurs_global[1] = tr("Tout le modèle")
        for rang, texte in enumerate(valeurs_global):
            case = QTableWidgetItem(texte)
            case.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            case.setBackground(QColor("#F5F6F3"))
            case.setForeground(QColor(GRIS))
            table.setItem(0, rang, case)
        for ligne, valeurs in enumerate(lignes, start=1):
            for rang in range(1 + len(colonnes)):
                texte = valeurs[rang] if rang < len(valeurs) else ""
                table.setItem(ligne, rang, QTableWidgetItem(str(texte)))
        table.blockSignals(False)
        actuel = self.couleur_par.currentText()
        groupes = ["Périmètre"] + [c for c, coord in zip(colonnes, coordonnees)
                                   if not coord]
        self.couleur_par.blockSignals(True)
        self.couleur_par.clear()
        self.couleur_par.addItems(groupes)
        if actuel in groupes:
            self.couleur_par.setCurrentText(actuel)
        elif len(groupes) > 1:
            self.couleur_par.setCurrentIndex(1)
        self.couleur_par.blockSignals(False)
        self.dessiner_carte()

    def lire_table(self):
        """(colonnes, lignes) saisies, sans la ligne Global."""
        table = self.table_p
        colonnes = [table.horizontalHeaderItem(c).text()
                    for c in range(1, table.columnCount())]
        lignes = []
        for ligne in range(1, table.rowCount()):
            lignes.append([(table.item(ligne, c).text().strip()
                            if table.item(ligne, c) else "")
                           for c in range(table.columnCount())])
        return colonnes, lignes

    def charger_perimetres(self):
        m = self.modele
        self.carte.points = []          # nouveau modèle : recadrer la carte
        self.remplir_table(m.colonnes_table(), m.lignes_table())
        self.perimetres_modifies = False
        self.etat_perimetres.setText("")
        if self.pages.currentIndex() == PAGE_PERIMETRES:
            self.ouvrir_perimetre(self.perimetre_choisi())

    def perimetre_modifie(self, *_args):
        self.perimetres_modifies = True
        self.etat_perimetres.setText(
            "Modifications non appliquées : cliquez sur Appliquer.")
        self.dessiner_carte()
        self.ouvrir_perimetre(self.perimetre_choisi())

    def perimetre_choisi(self):
        ligne = self.table_p.currentRow()
        if ligne <= 0 or not self.table_p.item(ligne, 0):
            return "Global"
        return self.table_p.item(ligne, 0).text().strip() or "Global"

    def dessiner_carte(self, *_args):
        colonnes, lignes = self.lire_table()
        cles = [creer_id(c) for c in colonnes]
        rang_x = next((r for r, c in enumerate(cles) if c in COLONNES_X), None)
        rang_y = next((r for r, c in enumerate(cles) if c in COLONNES_Y), None)
        critere = self.couleur_par.currentText()
        rang_g = colonnes.index(critere) if critere in colonnes else None
        couleurs, points, sans = {}, [], []
        for ligne in lignes:
            nom = ligne[0]
            if not nom:
                continue
            groupe = ligne[rang_g + 1] if rang_g is not None else nom
            groupe = groupe or "Sans groupe"
            couleur = couleurs.setdefault(
                groupe, PALETTE[len(couleurs) % len(PALETTE)])
            try:
                x = float(ligne[rang_x + 1].replace(",", "."))
                y = float(ligne[rang_y + 1].replace(",", "."))
            except (TypeError, ValueError, AttributeError):
                sans.append(nom)
                continue
            points.append({"nom": nom, "x": x, "y": y, "couleur": couleur})
        legende = ""
        if rang_g is not None and couleurs:
            legende = "<b>%s</b><br>" % critere + "<br>".join(
                '<span style="color:%s">●</span>&nbsp;%s' % (c, g)
                for g, c in list(couleurs.items())[:10])
        if not any(l[0] for l in lignes):
            message = ("Aucun périmètre : tout le modèle est Global.\n"
                       "Ajoutez des périmètres avec leurs colonnes X "
                       "(longitude) et Y (latitude) pour les voir ici.")
        elif rang_x is None or rang_y is None:
            message = ("Ajoutez les colonnes X (longitude) et Y (latitude) "
                       "pour placer les périmètres sur la carte.")
        else:
            message = ""
        choisi = self.perimetre_choisi()
        self.carte.montrer(points, None if choisi == "Global" else choisi,
                           legende, message)
        if sans and not message:
            self.etat_perimetres.setText(
                "Sans coordonnées, donc absents de la carte : "
                + ", ".join(sans) + ".")

    def choisir_sur_carte(self, nom):
        for ligne in range(1, self.table_p.rowCount()):
            case = self.table_p.item(ligne, 0)
            if case and case.text().strip() == nom:
                self.table_p.selectRow(ligne)
                return

    def ouvrir_perimetre(self, nom):
        colonnes, lignes = self.lire_table()
        self.pile_fiche.setCurrentIndex(0)
        self.selection = None
        for element in (self.etiquette_formule, self.formule, self.appliquer):
            element.hide()
        self.controle.setText("")
        self.fiche_type.setText("Périmètre")
        self.fiche_nom.setText(nom)
        coordonnees = [creer_id(c) in COLONNES_X + COLONNES_Y
                       for c in colonnes]
        noms = [l[0] for l in lignes if l[0]]
        if nom == "Global":
            self.fiche_detail.setText(
                "Ensemble des %d périmètres." % len(noms) if noms else
                "Aucun périmètre défini : tout le modèle est Global.")
            resume = []
            for rang, (colonne, coord) in enumerate(zip(colonnes,
                                                        coordonnees)):
                if coord:
                    continue
                valeurs = list(dict.fromkeys(
                    l[rang + 1] for l in lignes if l[0] and l[rang + 1]))
                resume.append("%s : %d groupe(s), %s" % (
                    colonne, len(valeurs), ", ".join(valeurs) or "—"))
            self.resume.setText("\n".join(resume))
        else:
            ligne = next((l for l in lignes if l[0] == nom), None) or [nom]
            ligne += [""] * (len(colonnes) + 1 - len(ligne))
            details, position = [], {}
            for colonne, coord, valeur in zip(colonnes, coordonnees,
                                              ligne[1:]):
                if coord:
                    position[creer_id(colonne) in COLONNES_X] = valeur
                else:
                    details.append("%s : %s" % (colonne, valeur or "—"))
            if position.get(True) and position.get(False):
                details.append("Longitude %s, latitude %s"
                               % (position[True], position[False]))
            else:
                details.append("Sans coordonnées")
            self.fiche_detail.setText("\n".join(details))
            pid = creer_id(nom)
            propres = sorted(i for i, fiche in self.modele.parametres.items()
                             if pid in fiche.get("perimetres", {}))
            self.resume.setText(
                "Valeurs propres à ce périmètre :\n" + "\n".join(
                    "• " + i for i in propres[:12]) if propres else
                "Aucune valeur propre : les formules en x[structure, p] "
                "s'appliquent telles quelles.")
        self.dessiner_carte_selection()

    def dessiner_carte_selection(self):
        choisi = self.perimetre_choisi()
        self.carte.choisi = None if choisi == "Global" else choisi
        self.carte.dessiner_points()

    def ajouter_perimetre(self):
        table = self.table_p
        ligne = table.rowCount()
        table.blockSignals(True)
        table.insertRow(ligne)
        for rang in range(table.columnCount()):
            table.setItem(ligne, rang, QTableWidgetItem(""))
        table.blockSignals(False)
        table.selectRow(ligne)
        table.editItem(table.item(ligne, 0))
        self.perimetre_modifie()

    def retirer_perimetre(self):
        ligne = self.table_p.currentRow()
        if ligne > 0:
            self.table_p.removeRow(ligne)
            self.perimetre_modifie()

    def ajouter_colonne(self):
        nom, ok = QInputDialog.getText(
            self, TITRE_APPLICATION,
            "Nom de la colonne (un groupe, ou X / Y pour les coordonnées) :")
        if ok and nom.strip():
            colonnes, lignes = self.lire_table()
            self.remplir_table(colonnes + [nom.strip()], lignes)
            self.perimetre_modifie()

    def retirer_colonne(self):
        colonnes, lignes = self.lire_table()
        if not colonnes:
            return
        nom, ok = QInputDialog.getItem(self, TITRE_APPLICATION,
                                       "Colonne à retirer :", colonnes,
                                       len(colonnes) - 1, False)
        if ok and nom in colonnes:
            rang = colonnes.index(nom) + 1
            self.remplir_table(colonnes[:rang - 1] + colonnes[rang:],
                               [l[:rang] + l[rang + 1:] for l in lignes])
            self.perimetre_modifie()

    def importer_perimetres(self):
        chemin = QFileDialog.getOpenFileName(
            self, "Importer des périmètres", "",
            "Tableau (*.csv *.txt *.tsv);;Tous les fichiers (*)")[0]
        if not chemin:
            return
        try:
            colonnes, lignes = lire_tableau_perimetres(chemin)
        except (OSError, ValueError, ErreurModele) as erreur:
            QMessageBox.warning(self, TITRE_APPLICATION, str(erreur))
            return
        ignores = [l for l in lignes if creer_id(l[0]) == "global"]
        lignes = [l for l in lignes if creer_id(l[0]) != "global"]
        self.remplir_table(colonnes, lignes)
        self.perimetre_modifie()
        self.etat_perimetres.setText(
            "Importé : %d périmètre(s)%s. Vérifiez, puis Appliquer." % (
                len(lignes), " (ligne Global du fichier ignorée)"
                if ignores else ""))

    def exporter_perimetres(self):
        chemin = QFileDialog.getSaveFileName(
            self, "Exporter les périmètres", chemin_local("Perimetres.csv"),
            "Fichier csv (*.csv)")[0]
        if not chemin:
            return
        colonnes, lignes = self.lire_table()
        with open(chemin, "w", encoding="utf-8-sig") as fichier:
            fichier.write("\n".join(";".join(l) for l in
                                    [["Périmètre"] + colonnes] + lignes)
                          + "\n")
        self.etat_perimetres.setText(
            "Fichier enregistré : " + os.path.basename(chemin))

    def appliquer_perimetres(self):
        colonnes, lignes = self.lire_table()
        try:
            self.modele.definir_perimetres(colonnes, lignes)
        except ErreurModele as erreur:
            QMessageBox.warning(self, TITRE_APPLICATION, str(erreur))
            return False
        choisi = self.perimetre_choisi()
        self.resultat = None
        self.charger_perimetres()
        self.choisir_sur_carte(choisi)
        self.etat_perimetres.setText(
            "Périmètres appliqués. Relancez la simulation.")
        self.rafraichir()
        return True

    # ------------------------------ Paramètres ------------------------------
    def creer_page_parametres(self):
        page = QWidget()
        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(24, 24, 24, 16)
        ligne.setSpacing(16)
        # Liste, groupée par origine.
        liste = QFrame(objectName="carteBlanche")
        liste.setFixedWidth(360)
        colonne = QVBoxLayout(liste)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(8)
        colonne.addWidget(QLabel("Paramètres", objectName="titre"))
        self.recherche_p = QLineEdit(placeholderText="Rechercher")
        self.recherche_p.textChanged.connect(self.remplir_liste_parametres)
        colonne.addWidget(self.recherche_p)
        self.filtre_p = QComboBox()
        self.filtre_p.addItems(["Tous", "À définir", "Circulaire",
                                "Par périmètre"])
        self.filtre_p.currentIndexChanged.connect(
            self.remplir_liste_parametres)
        colonne.addWidget(self.filtre_p)
        self.arbre_p = QTreeWidget(columnCount=2, headerHidden=True,
                                   indentation=10, rootIsDecorated=False)
        self.arbre_p.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.arbre_p.header().setSectionResizeMode(
            1, QHeaderView.ResizeToContents)
        self.arbre_p.header().setStretchLastSection(False)
        self.arbre_p.itemClicked.connect(self.plier_groupe)
        self.groupes_plies = {"Base", "Conversion"}
        self.arbre_p.currentItemChanged.connect(
            lambda actuel, _ancien: actuel and actuel.data(0, Qt.UserRole)
            and self.ouvrir_parametre(actuel.data(0, Qt.UserRole)))
        colonne.addWidget(self.arbre_p, 1)
        colonne.addWidget(QLabel(
            "Un paramètre apparaît dès qu'une formule l'utilise.",
            objectName="discret", wordWrap=True))
        ligne.addWidget(liste)
        # Éditeur.
        editeur = QFrame(objectName="carteBlanche")
        colonne = QVBoxLayout(editeur)
        colonne.setContentsMargins(20, 18, 20, 18)
        colonne.setSpacing(10)
        self.p_titre = _Qt.QLabel(objectName="titreFiche", wordWrap=True)
        self.p_titre.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.p_sous_titre = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.p_titre)
        colonne.addWidget(self.p_sous_titre)
        self.zone_portee = QWidget()
        self.ligne_portee = QHBoxLayout(self.zone_portee)
        self.ligne_portee.setContentsMargins(0, 0, 0, 0)
        self.ligne_portee.setSpacing(6)
        self.groupe_portee = QButtonGroup(self)
        self.groupe_portee.idClicked.connect(self.changer_portee)
        colonne.addWidget(self.zone_portee)
        modes = QHBoxLayout()
        self.p_formule = QRadioButton("Formule")
        self.p_table = QRadioButton("Table")
        self.p_formule.toggled.connect(self.afficher_mode_p)
        self.p_formule.toggled.connect(lambda _b: self.apercu_table())
        for bouton in (self.p_formule, self.p_table):
            modes.addWidget(bouton)
        modes.addStretch(1)
        self.zone_modes = QWidget()
        self.zone_modes.setLayout(modes)
        modes.setContentsMargins(0, 0, 0, 0)
        colonne.addWidget(self.zone_modes)
        # Formule.
        self.p_expression = QPlainTextEdit(objectName="formuleCode")
        police = QFont("Consolas")
        police.setStyleHint(QFont.Monospace)
        police.setPointSize(11)
        self.p_expression.setFont(police)
        self.p_expression.setTabStopDistance(28)
        self.surligneur = Surligneur(self.p_expression.document(), self)
        self.minuterie_p = QTimer(self, singleShot=True, interval=300)
        self.minuterie_p.timeout.connect(self.verifier_formule_p)
        self.p_expression.textChanged.connect(self.minuterie_p.start)
        self.minuterie_apercu = QTimer(self, singleShot=True, interval=400)
        self.minuterie_apercu.timeout.connect(self.actualiser_apercu)
        self.apercu_lent = False
        self.p_expression.cursorPositionChanged.connect(
            self.marquer_parentheses)
        travail = QHBoxLayout()
        travail.setSpacing(16)
        self.colonne_saisie = QVBoxLayout()
        self.colonne_saisie.addWidget(self.p_expression, 1)
        travail.addLayout(self.colonne_saisie, 5)
        droite = QVBoxLayout()
        self.apercu = Apercu()
        droite.addWidget(self.apercu, 1)
        self.bouton_apercu = QPushButton("Actualiser l'aperçu")
        self.bouton_apercu.clicked.connect(self.actualiser_apercu)
        self.bouton_apercu.hide()
        droite.addWidget(self.bouton_apercu, 0, Qt.AlignRight)
        travail.addLayout(droite, 4)
        colonne.addLayout(travail, 1)
        self.p_controle = QLabel(wordWrap=True)
        self.p_utilise = QLabel(wordWrap=True, objectName="discret")
        self.p_utilise_par = QLabel(wordWrap=True, objectName="discret")
        for etiquette in (self.p_utilise, self.p_utilise_par):
            etiquette.linkActivated.connect(self.aller_parametre)
        for etiquette in (self.p_controle, self.p_utilise,
                          self.p_utilise_par):
            colonne.addWidget(etiquette)
        # Table.
        self.zone_table_p = QWidget()
        table = QHBoxLayout(self.zone_table_p)
        table.setContentsMargins(0, 0, 0, 0)
        gauche = QVBoxLayout()
        reglages = QHBoxLayout()
        reglages.addWidget(QLabel("Variable 1"))
        self.p_variable_1 = _Qt.QComboBox()   # noms = données
        self.p_variable_1.setMinimumWidth(180)
        reglages.addWidget(self.p_variable_1, 1)
        reglages.addWidget(QLabel("Entre deux lignes"))
        self.p_lecture = QComboBox()
        self.p_lecture.addItems(list(LECTURES_TABLE))
        self.p_lecture.currentIndexChanged.connect(self.apercu_table)
        reglages.addWidget(self.p_lecture)
        gauche.addLayout(reglages)
        self.p_lignes = QTableWidget(0, 2)
        self.p_lignes.setHorizontalHeaderLabels(["Variable 1", "Valeur"])
        self.p_lignes.verticalHeader().hide()
        self.p_lignes.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.p_lignes.cellChanged.connect(self.apercu_table)
        self.p_variable_1.currentIndexChanged.connect(self.apercu_table)
        gauche.addWidget(self.p_lignes, 1)
        boutons = QHBoxLayout()
        for texte, action in (("+ Ligne", self.ajouter_ligne_table),
                              ("− Ligne", self.retirer_ligne_table)):
            bouton = QPushButton(texte)
            bouton.clicked.connect(action)
            boutons.addWidget(bouton)
        boutons.addStretch(1)
        gauche.addLayout(boutons)
        table.addLayout(gauche, 1)
        self.colonne_saisie.addWidget(self.zone_table_p, 1)
        # Réglages.
        self.zone_reglages = QWidget()
        reglages = QHBoxLayout(self.zone_reglages)
        reglages.setContentsMargins(0, 0, 0, 0)
        reglages.addWidget(QLabel("Unité"))
        self.p_unite = QComboBox()
        self.p_unite.setMinimumWidth(130)
        reglages.addWidget(self.p_unite)
        reglages.addSpacing(12)
        reglages.addWidget(QLabel("Convergence"))
        self.p_convergence = QLineEdit()
        self.p_convergence.setFixedWidth(80)
        reglages.addWidget(self.p_convergence)
        self.p_suivi = QCheckBox("Suivre la convergence")
        reglages.addWidget(self.p_suivi)
        reglages.addStretch(1)
        self.p_optimisable = QCheckBox("Tarif optimisable")
        reglages.addWidget(self.p_optimisable)
        reglages.addWidget(QLabel("max"))
        self.p_tarif_max = QLineEdit()
        self.p_tarif_max.setFixedWidth(80)
        self.p_optimisable.toggled.connect(self.p_tarif_max.setEnabled)
        reglages.addWidget(self.p_tarif_max)
        colonne.addWidget(self.zone_reglages)
        actions = QHBoxLayout()
        self.p_message = QLabel(objectName="discret", wordWrap=True)
        actions.addWidget(self.p_message, 1)
        self.p_commune = QPushButton("Reprendre la valeur par défaut")
        self.p_commune.clicked.connect(self.reprendre_commune)
        actions.addWidget(self.p_commune)
        annuler = QPushButton("Annuler")
        annuler.clicked.connect(lambda: self.ouvrir_parametre(
            self.parametre_ouvert, self.portee_p))
        actions.addWidget(annuler)
        self.p_appliquer = QPushButton("Appliquer", objectName="principal")
        self.p_appliquer.clicked.connect(self.appliquer_parametre)
        actions.addWidget(self.p_appliquer)
        colonne.addLayout(actions)
        ligne.addWidget(editeur, 1)
        self.parametre_ouvert, self.portee_p = None, None
        return page

    # Liste
    def remplir_liste_parametres(self, *_args):
        m = self.modele
        filtre = self.filtre_p.currentText()
        cherche = self.recherche_p.text().strip().lower()
        circulaires = m.cycles()
        groupes = {o: [] for o in ORDRE_ORIGINES}
        if filtre == "Tous":
            for dimension, unite in m.references_unites.items():
                groupes["Base"].append(("reference:" + dimension,
                                        "Référence : " + dimension, unite,
                                        "Défini"))
            for nom, _texte in BASE_TEMPS:
                unite = TEMPS_FIXES.get(nom, "" if nom.startswith("t[")
                                        else m.references_unites["Temps"])
                groupes["Base"].append(("systeme:" + nom, nom, unite,
                                        "Défini"))
            for atome, reference, facteur in m.conversions()[0]:
                groupes["Conversion"].append((
                    "conversion:" + atome, "1 %s = %s %s"
                    % (atome, facteur, reference), reference, "Défini"))
        for i, fiche in m.parametres.items():
            origine = origine_parametre(m, i)
            if origine == "Conversion":
                continue
            etat = m.etat(i, circulaires)
            if (filtre in ("À définir", "Circulaire") and etat != filtre) or \
                    (filtre == "Par périmètre" and not est_indexe(i)):
                continue
            groupes[origine].append((i, i, fiche["unite"], etat))
        arbre = self.arbre_p
        arbre.blockSignals(True)
        arbre.clear()
        choisi = None
        for origine in ORDRE_ORIGINES:
            elements = [e for e in sorted(groupes[origine], key=lambda e:
                                          e[1] if origine != "Base" else "")
                        if not cherche or cherche in e[1].lower()]
            if not elements:
                continue
            plie = origine in self.groupes_plies and not cherche
            titre = QTreeWidgetItem(["%s  %s   %d" % (
                "▸" if plie else "▾", tr(TITRES_ORIGINES[origine]),
                len(elements)), ""])
            titre.setData(0, Qt.UserRole + 2, origine)
            titre.setFlags(Qt.ItemIsEnabled)
            police = titre.font(0)
            police.setPointSize(8)
            police.setBold(True)
            titre.setFont(0, police)
            titre.setForeground(0, QColor(GRIS))
            arbre.addTopLevelItem(titre)
            for cle, libelle, unite, etat in elements:
                element = QTreeWidgetItem(["●  " + libelle, unite])
                element.setData(0, Qt.UserRole, cle)
                element.setForeground(1, QColor(GRIS))
                element.setToolTip(0, "%s : %s" % (libelle, etat))
                element.setData(0, Qt.UserRole + 1,
                                COULEURS_ETAT.get(etat, GRIS))
                titre.addChild(element)
                if cle == self.parametre_ouvert:
                    choisi = element
            titre.setExpanded(not plie or choisi in [
                titre.child(k) for k in range(titre.childCount())])
        arbre.setItemDelegateForColumn(0, PastilleEtat(arbre))
        if choisi:
            arbre.setCurrentItem(choisi)
        arbre.blockSignals(False)

    def plier_groupe(self, element, _colonne):
        origine = element.data(0, Qt.UserRole + 2)
        if origine:
            self.groupes_plies ^= {origine}
            self.remplir_liste_parametres()

    def aller_parametre(self, identifiant):
        self.recherche_p.clear()
        self.filtre_p.setCurrentIndex(0)
        self.ouvrir_parametre(identifiant)
        self.remplir_liste_parametres()

    # Éditeur
    def ouvrir_parametre(self, identifiant, portee=None):
        m = self.modele
        self.parametre_ouvert, self.portee_p = identifiant, portee
        self.p_message.setText("")
        base = identifiant and ":" in identifiant
        fiche = m.parametres.get(identifiant) if identifiant else None
        for zone in (self.zone_modes, self.p_expression, self.p_controle,
                     self.p_utilise, self.p_utilise_par, self.zone_reglages,
                     self.zone_table_p, self.p_commune, self.zone_portee):
            zone.setVisible(bool(fiche))
        self.p_appliquer.setVisible(bool(fiche) or identifiant is not None
                                    and identifiant.startswith("reference:"))
        if not identifiant:
            self.p_titre.setText("Sélectionnez un paramètre")
            self.p_sous_titre.setText("")
            return
        if base:
            self.ouvrir_base(identifiant)
            return
        # Portée : la formule commune ou la valeur propre d'un périmètre.
        while self.ligne_portee.count():
            element = self.ligne_portee.takeAt(0)
            if element.widget():
                element.widget().deleteLater()
        for bouton in self.groupe_portee.buttons():
            self.groupe_portee.removeButton(bouton)
        self.portees_p = [None]
        if est_indexe(identifiant) and m.perimetres:
            self.portees_p += [creer_id(p["nom"]) for p in m.perimetres]
        propres = fiche.get("perimetres", {})
        for rang, cle in enumerate(self.portees_p):
            nom = "Par défaut (tout périmètre)" if cle is None else next(
                p["nom"] for p in m.perimetres if creer_id(p["nom"]) == cle)
            marque = cle is not None and "mode" in propres.get(cle, {})
            bouton = QPushButton(nom + ("  •" if marque else ""),
                                 objectName="pastille", checkable=True)
            bouton.setChecked(cle == portee)
            bouton.setToolTip("Valeur propre à ce périmètre" if marque else
                              "Reprend la valeur par défaut" if cle else
                              "Valeur par défaut, reprise par chaque "
                              "périmètre sans valeur propre. Ce n'est pas "
                              "le total Global.")
            self.groupe_portee.addButton(bouton, rang)
            self.ligne_portee.addWidget(bouton)
        self.ligne_portee.addStretch(1)
        self.zone_portee.setVisible(len(self.portees_p) > 1)
        self.p_commune.setVisible(portee is not None)
        source = propres.get(portee, {}) if portee else {}
        source = source if "mode" in source else fiche
        origine = origine_parametre(m, identifiant)
        self.p_titre.setText(identifiant)
        self.p_sous_titre.setText(" · ".join(tr(t) for t in filter(None, (
            origine, fiche["unite"] or "sans unité",
            "par p" if est_indexe(identifiant) else "",
            m.etat(identifiant)))))
        self.p_formule.setChecked(source["mode"] == "formule")
        self.p_table.setChecked(source["mode"] == "table")
        self.p_expression.blockSignals(True)
        self.p_expression.setPlainText(source.get("expression", ""))
        # Recolorer sans relancer la vérification (évite une boucle).
        self.surligneur.rehighlight()
        self.p_expression.blockSignals(False)
        self.p_variable_1.clear()
        self.p_variable_1.addItems(
            [tr("annee (année du calendrier)"), "t", "t_sim"]
            + list(TEMPS_FIXES)
            + sorted(i for i in m.parametres if i != identifiant))
        variable = fiche.get("variable_table", VARIABLE_TEMPS)
        self.p_variable_1.setCurrentIndex(
            0 if variable == VARIABLE_TEMPS else
            max(self.p_variable_1.findText(variable), 0))
        self.p_lecture.setCurrentIndex(
            1 if fiche.get("lecture_table") == "interpolation" else 0)
        self.p_lignes.blockSignals(True)
        self.p_lignes.setRowCount(0)
        for x, y in source.get("table", []):
            rang = self.p_lignes.rowCount()
            self.p_lignes.insertRow(rang)
            self.p_lignes.setItem(rang, 0, QTableWidgetItem("%g" % x))
            self.p_lignes.setItem(rang, 1, QTableWidgetItem("%g" % y))
        self.p_lignes.blockSignals(False)
        self.p_unite.clear()
        self.p_unite.addItems(UNITES)
        self.p_unite.setCurrentText(fiche["unite"])
        self.p_convergence.setText(fiche["convergence"])
        self.p_suivi.setChecked(bool(fiche["suivi"]))
        self.p_optimisable.setChecked(bool(fiche.get("optimisable")))
        self.p_tarif_max.setText(fiche.get("tarif_max", ""))
        self.p_tarif_max.setEnabled(bool(fiche.get("optimisable")))
        # Les réglages communs ne se changent pas depuis un périmètre.
        self.zone_reglages.setEnabled(portee is None)
        utilise_par = sorted(i for i in m.parametres
                             if identifiant in m.references(i))
        self.p_utilise_par.setText(
            "Utilisé par : " + self.liens(utilise_par) if utilise_par else
            "Utilisé par : un flux, une charge ou un poste" if origine
            != "Paramètre" else "N'est utilisé par aucune formule.")
        self.afficher_mode_p()
        self.verifier_formule_p()
        self.apercu_table()

    def ouvrir_base(self, identifiant):
        m = self.modele
        genre, nom = identifiant.split(":", 1)
        self.zone_reglages.setVisible(genre == "reference")
        for element in (self.p_convergence, self.p_suivi, self.p_optimisable,
                        self.p_tarif_max):
            element.setVisible(genre != "reference")
        self.zone_reglages.setEnabled(True)
        if genre == "reference":
            self.p_titre.setText("Unité de référence : " + nom)
            self.p_sous_titre.setText(
                "Base · les valeurs de cette dimension sont converties dans "
                "cette unité pour le calcul.")
            self.p_unite.clear()
            self.p_unite.addItems(list(DIMENSIONS[nom]))
            self.p_unite.setCurrentText(m.references_unites[nom])
        elif genre == "systeme":
            self.p_titre.setText(nom)
            self.p_sous_titre.setText(
                "Base · calculé par le moteur · " + dict(BASE_TEMPS)[nom])
        else:
            self.p_titre.setText(nom)
            self.p_sous_titre.setText(
                "Conversion calculée automatiquement à partir des unités.")

    def liens(self, identifiants):
        return ", ".join('<a href="%s" style="color:%s">%s</a>'
                         % (i, VERT, i) for i in identifiants)

    def afficher_mode_p(self, *_args):
        formule = self.p_formule.isChecked()
        if self.parametre_ouvert and ":" in self.parametre_ouvert:
            return
        for zone in (self.p_expression, self.p_controle, self.p_utilise):
            zone.setVisible(formule)
        self.zone_table_p.setVisible(not formule)

    def changer_portee(self, rang):
        self.ouvrir_parametre(self.parametre_ouvert, self.portees_p[rang])

    def verifier_formule_p(self):
        """Contrôle pendant la frappe, sans rien changer au modèle."""
        identifiant = self.parametre_ouvert
        if not identifiant or ":" in identifiant \
                or not self.p_formule.isChecked():
            return
        texte = self.p_expression.toPlainText()
        if not texte.strip():
            self.p_controle.setText(
                '<span style="color:#D9822B">● Formule à saisir.</span>')
            self.p_utilise.setText("")
            return
        try:
            utilises = analyser_expression(
                texte, decomposer_id(identifiant)[1])
            self.modele.controler_calcul(texte, decomposer_id(identifiant)[1])
        except ErreurModele as erreur:
            self.p_controle.setText(
                '<span style="color:#C0392B">✗ %s</span>' % erreur)
            self.apercu.montrer([], message="La courbe apparaîtra quand la "
                                "formule sera valide.")
            return
        self.minuterie_apercu.start()
        connus = sorted(n for n in utilises
                        if indexee(n) in self.modele.parametres)
        nouveaux = sorted(n for n in utilises
                          if indexee(n) not in self.modele.parametres
                          and n not in VARIABLES_SYSTEME)
        self.p_controle.setText(
            '<span style="color:#2E8B57">✓ Formule valide.</span>' + (
                ' <span style="color:#C2610C">À l\'application, nouveaux '
                'paramètres créés : %s.</span>' % ", ".join(nouveaux)
                if nouveaux else ""))
        self.p_utilise.setText("Utilise : " + (self.liens(connus) or "—"))

    def marquer_parentheses(self):
        """Surligne la parenthèse correspondant à celle sous le curseur."""
        texte = self.p_expression.toPlainText()
        position = self.p_expression.textCursor().position()
        marques = []
        for ici in (position - 1, position):
            if 0 <= ici < len(texte) and texte[ici] in "()":
                pas = 1 if texte[ici] == "(" else -1
                niveau, j = 0, ici
                while 0 <= j < len(texte):
                    niveau += {"(": 1, ")": -1}.get(texte[j], 0) * pas
                    if niveau == 0:
                        break
                    j += pas
                for k in (ici, j) if 0 <= j < len(texte) else (ici,):
                    selection = QTextEdit.ExtraSelection()
                    curseur = self.p_expression.textCursor()
                    curseur.setPosition(k)
                    curseur.setPosition(k + 1, QTextCursor.KeepAnchor)
                    selection.cursor = curseur
                    selection.format.setBackground(
                        QColor("#CDE9E3" if 0 <= j < len(texte)
                               else "#F6C9C3"))
                    marques.append(selection)
                break
        self.p_expression.setExtraSelections(marques)

    def lignes_table_p(self):
        return [[(self.p_lignes.item(r, c).text()
                  if self.p_lignes.item(r, c) else "") for c in (0, 1)]
                for r in range(self.p_lignes.rowCount())]

    def apercu_table(self, *_args):
        """Toute saisie relance l'aperçu, un instant après la frappe."""
        self.minuterie_apercu.start()

    def actualiser_apercu(self):
        m, identifiant = self.modele, self.parametre_ouvert
        self.bouton_apercu.setVisible(False)
        if not identifiant or ":" in identifiant:
            self.apercu.montrer([], message="")
            return
        if self.p_table.isChecked():
            self.apercu_de_table()
            return
        if self.apercu_lent and self.sender() is not self.bouton_apercu:
            self.bouton_apercu.setVisible(True)
            return
        # Formule : simulation d'une copie du modèle, avec la saisie en cours.
        copie = copy.deepcopy(m)
        try:
            self.appliquer_sur(copie, identifiant)
            depart = time.perf_counter()
            resultat = ppp_moteur.simuler(copie)
        except Exception as erreur:      # saisie incomplète : pas de courbe
            self.apercu.montrer([], message=str(erreur))
            return
        self.apercu_lent = time.perf_counter() - depart > 1.5
        nom, structure = decomposer_id(identifiant)
        if est_indexe(identifiant):
            cles = [p["nom"] for p in m.perimetres
                    if self.portee_p in (None, creer_id(p["nom"]))]
            series = [(c, "%s[%s,%s]" % (nom, structure, creer_id(c)))
                      for c in cles]
        else:
            series = [(identifiant, identifiant)]
        temps = [p["annee_decimale"] for p in resultat["periodes"]]
        courbes = []
        for rang, (libelle, cle) in enumerate(series):
            valeurs = resultat["series"].get(cle)
            if valeurs:
                courbes.append((libelle, PALETTE[rang % len(PALETTE)],
                                list(zip(temps, valeurs)), True))
        unite = resultat.get("unites", {}).get(
            series[0][1] if series else "", m.parametres[identifiant]["unite"])
        message = "" if courbes else (
            resultat["erreurs"][0] if resultat["erreurs"]
            else "Pas de valeur calculée.")
        self.apercu.montrer(
            courbes, True, Apercu.PAS_TEMPS.get(
                m.references_unites["Temps"], 1.0), unite, message)

    def apercu_de_table(self):
        points = []
        for x, y in self.lignes_table_p():
            try:
                points.append((float(x.replace(",", ".")),
                               float(y.replace(",", "."))))
            except ValueError:
                pass
        variable = self.p_variable_1.currentText()
        temps = self.p_variable_1.currentIndex() == 0 or variable in (
            "t", "t_sim") or variable in TEMPS_FIXES
        self.apercu.montrer(
            [(self.parametre_ouvert, VERT, sorted(points),
              self.p_lecture.currentIndex() == 0)], temps, 1.0,
            self.p_unite.currentText(),
            "" if points else "Saisissez des lignes dans la table.")

    def ajouter_ligne_table(self):
        rang = self.p_lignes.rowCount()
        self.p_lignes.insertRow(rang)
        self.p_lignes.setItem(rang, 0, QTableWidgetItem(""))
        self.p_lignes.setItem(rang, 1, QTableWidgetItem(""))
        self.p_lignes.editItem(self.p_lignes.item(rang, 0))

    def retirer_ligne_table(self):
        if self.p_lignes.currentRow() >= 0:
            self.p_lignes.removeRow(self.p_lignes.currentRow())
            self.apercu_table()

    def appliquer_parametre(self):
        m, identifiant = self.modele, self.parametre_ouvert
        try:
            self.appliquer_sur(m, identifiant)
        except ErreurModele as erreur:
            self.p_message.setText(
                '<span style="color:#C0392B">%s</span>' % erreur)
            return
        self.resultat = None
        self.rafraichir()
        if identifiant in m.parametres or ":" in identifiant:
            self.ouvrir_parametre(identifiant, self.portee_p)
        self.remplir_liste_parametres()
        self.p_message.setText("Enregistré dans le modèle.")

    def appliquer_sur(self, m, identifiant):
        """Porte la saisie de l'éditeur dans le modèle m (ou une copie)."""
        mode = "formule" if self.p_formule.isChecked() else "table"
        if True:
            if identifiant.startswith("reference:"):
                m.definir_reference(identifiant.split(":", 1)[1],
                                    self.p_unite.currentText())
            elif self.portee_p:
                m.definir_valeur_perimetre(identifiant, self.portee_p, {
                    "mode": mode,
                    "expression": self.p_expression.toPlainText(),
                    "table": self.lignes_table_p()})
            else:
                variable = self.p_variable_1.currentText()
                if self.p_variable_1.currentIndex() == 0:
                    variable = VARIABLE_TEMPS
                m.definir_parametre(
                    identifiant, mode, self.p_expression.toPlainText(),
                    self.lignes_table_p(), self.p_unite.currentText(),
                    m.parametres[identifiant]["valeur_initiale"],
                    self.p_convergence.text(), self.p_suivi.isChecked(),
                    variable, LECTURES_TABLE[self.p_lecture.currentText()])
                m.definir_tarif(identifiant, self.p_optimisable.isChecked(),
                                self.p_tarif_max.text())

    def reprendre_commune(self):
        if self.portee_p:
            self.modele.definir_valeur_perimetre(
                self.parametre_ouvert, self.portee_p, {"mode": None})
            self.resultat = None
            self.ouvrir_parametre(self.parametre_ouvert, self.portee_p)
            self.p_message.setText("Ce périmètre reprend la valeur par défaut.")

    # ----------------------------- État initial -----------------------------
    def creer_page_initial(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(24, 24, 24, 16)
        colonne.setSpacing(10)
        entete = QHBoxLayout()
        entete.addWidget(QLabel("État initial", objectName="titre"))
        entete.addStretch(1)
        self.compte_initial = QLabel(objectName="discret")
        entete.addWidget(self.compte_initial)
        colonne.addLayout(entete)
        colonne.addWidget(QLabel(
            "Valeur de chaque paramètre avant le premier pas de temps : "
            "point de départ des itérations et valeur de lag(...) au "
            "démarrage. Cliquez sur une valeur pour la saisir ; Entrée passe "
            "à la suivante. Pour un paramètre par périmètre, la ligne du "
            "paramètre est la valeur par défaut de tout périmètre (pas le total) ; "
            "la ligne Global, calculée, donne la somme ou la moyenne.", objectName="discret", wordWrap=True))
        outils = QHBoxLayout()
        self.recherche_i = QLineEdit(placeholderText="Rechercher")
        self.recherche_i.setFixedWidth(280)
        self.recherche_i.textChanged.connect(self.remplir_initial)
        outils.addWidget(self.recherche_i)
        self.filtre_i = QComboBox()
        self.filtre_i.addItems(["Tous", "À saisir", "Par périmètre"])
        self.filtre_i.currentIndexChanged.connect(self.remplir_initial)
        outils.addWidget(self.filtre_i)
        outils.addStretch(1)
        self.bouton_proposer = QPushButton("Proposer d'après la simulation")
        self.bouton_proposer.setToolTip(
            "Remplit les cases vides avec la valeur calculée au premier pas "
            "de la dernière simulation.")
        self.bouton_proposer.clicked.connect(self.proposer_initial)
        outils.addWidget(self.bouton_proposer)
        colonne.addLayout(outils)
        self.arbre_i = QTreeWidget(columnCount=4, rootIsDecorated=False,
                                   indentation=14)
        self.arbre_i.setHeaderLabels(["Variable", "Origine", "Unité",
                                      "Valeur initiale"])
        entetes = self.arbre_i.header()
        entetes.setSectionResizeMode(0, QHeaderView.Stretch)
        for rang, largeur in ((1, 150), (2, 110), (3, 200)):
            entetes.setSectionResizeMode(rang, QHeaderView.Fixed)
            entetes.resizeSection(rang, largeur)
        entetes.setStretchLastSection(False)
        self.arbre_i.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.delegue_i = DelegueSaisie(self.arbre_i)
        self.arbre_i.setItemDelegateForColumn(3, self.delegue_i)
        self.arbre_i.itemClicked.connect(self.cliquer_initial)
        self.arbre_i.itemChanged.connect(self.valeur_initiale_saisie)
        colonne.addWidget(self.arbre_i, 1)
        self.message_i = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.message_i)
        return page

    def remplir_initial(self, *_args):
        m = self.modele
        cherche = self.recherche_i.text().strip().lower()
        filtre = self.filtre_i.currentText()
        noms = [(creer_id(p["nom"]), p["nom"]) for p in m.perimetres]
        arbre = self.arbre_i
        arbre.blockSignals(True)
        arbre.clear()
        police = QFont("Inter")
        police.setPointSize(8)
        police.setBold(True)
        manquants = 0
        for origine in ORDRE_ORIGINES[1:]:
            identifiants = sorted(i for i in m.parametres
                                  if origine_parametre(m, i) == origine)
            lignes = []
            for i in identifiants:
                fiche = m.parametres[i]
                manquants += not fiche["valeur_initiale"]
                if cherche and cherche not in i.lower():
                    continue
                if filtre == "À saisir" and fiche["valeur_initiale"]:
                    continue
                if filtre == "Par périmètre" and not est_indexe(i):
                    continue
                lignes.append(i)
            if not lignes:
                continue
            titre = QTreeWidgetItem([tr(TITRES_ORIGINES[origine])])
            titre.setFlags(Qt.ItemIsEnabled)
            titre.setFont(0, police)
            titre.setForeground(0, QColor(GRIS))
            arbre.addTopLevelItem(titre)
            titre.setFirstColumnSpanned(True)
            for i in lignes:
                fiche = m.parametres[i]
                element = QTreeWidgetItem([i, origine, fiche["unite"],
                                           fiche["valeur_initiale"]])
                element.setData(0, Qt.UserRole, (i, None))
                self.marquer_initial(element, fiche["valeur_initiale"], True)
                arbre.addTopLevelItem(element)
                if est_indexe(i) and noms:
                    element.setText(0, i + "   · par défaut, tout périmètre")
                    propres = fiche.get("perimetres", {})
                    effectives = []
                    for pid, nom in noms:
                        valeur = propres.get(pid, {}).get(
                            "valeur_initiale", "")
                        enfant = QTreeWidgetItem(["      " + nom, "", "",
                                                  valeur])
                        enfant.setData(0, Qt.UserRole, (i, pid))
                        enfant.setForeground(0, QColor(GRIS))
                        self.marquer_initial(enfant, valeur, False,
                                             fiche["valeur_initiale"])
                        arbre.addTopLevelItem(enfant)
                        effectives.append(valeur or fiche["valeur_initiale"])
                    arbre.addTopLevelItem(self.ligne_globale(
                        effectives, fiche["unite"]))
        arbre.blockSignals(False)
        self.compte_initial.setText(
            "Toutes les valeurs sont saisies." if not manquants else
            "%d valeur(s) à saisir" % manquants)
        self.compte_initial.setStyleSheet(
            "color: %s;" % (VERT if not manquants else "#C2610C"))
        self.bouton_proposer.setEnabled(bool(self.dernier_resultat
                                             and manquants))

    def ligne_globale(self, valeurs, unite):
        """Ligne Global en lecture seule : somme (quantités, débits,
        montants) ou moyenne (prix, taux, sans unité)."""
        try:
            nombres = [float(v) for v in valeurs]
        except ValueError:
            nombres = []
        additive = ppp_moteur.est_additive(unite)
        if nombres and len(nombres) == len(valeurs):
            total = sum(nombres) if additive else sum(nombres) / len(nombres)
            texte = "%s  (%s)" % (nombre_court(total),
                                  "somme" if additive else "moyenne")
        else:
            texte = "incomplet"
        ligne = QTreeWidgetItem(["      Global", "", "", texte])
        ligne.setFlags(Qt.ItemIsEnabled)
        police = ligne.font(0)
        police.setBold(True)
        ligne.setFont(0, police)
        ligne.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)
        for colonne in (0, 3):
            ligne.setForeground(colonne, QColor(VERT))
        ligne.setToolTip(3, "Calculé à partir des périmètres ; ne se saisit "
                         "pas.")
        return ligne

    def marquer_initial(self, element, valeur, commune, defaut=""):
        element.setFlags(element.flags() | Qt.ItemIsEditable)
        element.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)
        if valeur:
            element.setForeground(3, QColor(ENCRE))
            element.setBackground(3, QColor("#FFFFFF"))
            element.setToolTip(3, "")
        elif commune:
            element.setText(3, "à saisir")
            element.setForeground(3, QColor("#C2610C"))
            element.setBackground(3, QColor("#FDF1E4"))
        else:
            element.setText(3, "%s  (par défaut)" % defaut if defaut
                            else "(par défaut)")
            element.setForeground(3, QColor("#9AA5A2"))
            police = element.font(3)
            police.setItalic(True)
            element.setFont(3, police)
            element.setToolTip(3, "Reprend la valeur par défaut. Cliquez "
                               "pour saisir une valeur propre à ce "
                               "périmètre.")

    def cliquer_initial(self, element, colonne):
        if colonne == 3 and element.data(0, Qt.UserRole):
            self.editer_initial(element)

    def editer_initial(self, element):
        i, pid = element.data(0, Qt.UserRole)
        fiche = self.modele.parametres[i]
        valeur = fiche.get("perimetres", {}).get(pid, {}).get(
            "valeur_initiale", "") if pid else fiche["valeur_initiale"]
        self.arbre_i.blockSignals(True)
        element.setText(3, valeur)
        self.arbre_i.blockSignals(False)
        self.arbre_i.scrollToItem(element)
        self.arbre_i.setCurrentItem(element, 3)
        self.arbre_i.editItem(element, 3)

    def valeur_initiale_saisie(self, element, colonne):
        if colonne != 3 or not element.data(0, Qt.UserRole):
            return
        i, pid = element.data(0, Qt.UserRole)
        texte = element.text(3).strip()
        try:
            if pid:
                self.modele.definir_valeur_perimetre(
                    i, pid, {"valeur_initiale": texte})
            else:
                self.modele.definir_valeur_initiale(i, texte)
        except ErreurModele as erreur:
            self.message_i.setText(
                '<span style="color:#C0392B">%s : %s</span>' % (i, erreur))
            QTimer.singleShot(0, lambda: self.editer_initial(element))
            return
        self.message_i.setText("")
        self.resultat = None
        suivant = self.delegue_i.entree
        self.delegue_i.entree = False
        position = self.arbre_i.indexOfTopLevelItem(element)
        self.remplir_initial()
        self.rafraichir()
        if suivant:                       # Entrée : ligne suivante
            for rang in range(position + 1, self.arbre_i.topLevelItemCount()):
                prochain = self.arbre_i.topLevelItem(rang)
                if prochain.data(0, Qt.UserRole):
                    QTimer.singleShot(
                        0, lambda e=prochain: self.editer_initial(e))
                    break

    def proposer_initial(self):
        """Cases vides <- valeur du premier pas de la dernière simulation."""
        if not self.dernier_resultat:
            return
        series, remplis = self.dernier_resultat["series"], []
        for i, fiche in self.modele.parametres.items():
            if fiche["valeur_initiale"]:
                continue
            if est_indexe(i):          # moyenne des périmètres au 1er pas
                nom, structure = decomposer_id(i)
                cles = ["%s[%s,%s]" % (nom, structure, creer_id(p["nom"]))
                        for p in self.modele.perimetres]
                premiers = [series[c][0] for c in cles if series.get(c)]
                valeur = sum(premiers) / len(premiers) if premiers else None
            else:
                valeur = series[i][0] if series.get(i) else None
            if valeur is not None:
                self.modele.definir_valeur_initiale(i, "%.6g" % valeur)
                remplis.append(i)
        self.remplir_initial()
        self.rafraichir()
        self.message_i.setText(
            "%d valeur(s) proposée(s) d'après le premier pas : vérifiez-les."
            % len(remplis) if remplis else "Aucune valeur à proposer.")

    # ------------------------------ Simulation ------------------------------
    def nouvelle_carte(self, titre):
        cadre = QFrame(objectName="carteBlanche")
        colonne = QVBoxLayout(cadre)
        colonne.setContentsMargins(18, 16, 18, 16)
        colonne.setSpacing(8)
        colonne.addWidget(QLabel(titre, objectName="titreCarte"))
        return cadre, colonne

    def champ_reglage(self, grille, ligne, libelle, aide=""):
        grille.addWidget(QLabel(libelle), ligne, 0)
        champ = QLineEdit()
        champ.setFixedWidth(130)
        champ.editingFinished.connect(self.appliquer_reglages)
        grille.addWidget(champ, ligne, 1)
        if aide:
            grille.addWidget(QLabel(aide, objectName="discret"), ligne, 2)
        return champ

    def creer_page_simulation(self):
        defilement = QScrollArea(widgetResizable=True,
                                 frameShape=QFrame.NoFrame)
        page = QWidget(objectName="page")
        defilement.setWidget(page)
        grille = QGridLayout(page)
        grille.setContentsMargins(24, 24, 24, 16)
        grille.setSpacing(16)
        titre = QLabel("Simulation", objectName="titre")
        grille.addWidget(titre, 0, 0, 1, 2)
        # Cadre temporel.
        cadre, colonne = self.nouvelle_carte("Cadre temporel")
        reglages = QGridLayout()
        self.s_debut = self.champ_reglage(reglages, 0, "Démarrage",
                                          "JJ/MM/AAAA")
        self.s_pas = self.champ_reglage(reglages, 1, "Pas")
        self.s_libelle_pas = QLabel(objectName="discret")
        reglages.addWidget(self.s_libelle_pas, 1, 2)
        self.s_fin = self.champ_reglage(reglages, 2, "Fin", "JJ/MM/AAAA")
        reglages.setColumnStretch(2, 1)
        colonne.addLayout(reglages)
        self.s_resume = QLabel(wordWrap=True)
        colonne.addWidget(self.s_resume)
        grille.addWidget(cadre, 1, 0)
        # Calcul.
        cadre, colonne = self.nouvelle_carte("Calcul")
        reglages = QGridLayout()
        self.s_iterations = self.champ_reglage(
            reglages, 0, "Itérations max par pas")
        self.s_taux = self.champ_reglage(reglages, 1, "Taux d'actualisation",
                                         "0,08 pour 8 %")
        reglages.setColumnStretch(2, 1)
        colonne.addLayout(reglages)
        self.s_conserver = QCheckBox(
            "Conserver la convergence d'un pas au suivant")
        self.s_conserver.toggled.connect(self.appliquer_reglages)
        colonne.addWidget(self.s_conserver)
        colonne.addStretch(1)
        grille.addWidget(cadre, 2, 0)
        # Tarifs.
        cadre, colonne = self.nouvelle_carte("Tarifs")
        colonne.addWidget(QLabel(
            "Cochez une ou plusieurs options : chacune est simulée, et les "
            "résultats les comparent.", objectName="discret", wordWrap=True))
        self.s_options = {}
        for option, (libelle, aide) in TEXTES_OPTIONS.items():
            case = QCheckBox(libelle)
            case.toggled.connect(self.appliquer_reglages)
            colonne.addWidget(case)
            explication = QLabel(aide, objectName="discret", wordWrap=True)
            explication.setContentsMargins(26, 0, 0, 4)
            colonne.addWidget(explication)
            self.s_options[option] = case
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel("Résultats détaillés pour"))
        self.s_principale = QComboBox()
        self.s_principale.activated.connect(self.appliquer_reglages)
        ligne.addWidget(self.s_principale, 1)
        colonne.addLayout(ligne)
        self.zone_contraintes = QWidget()
        contraintes = QVBoxLayout(self.zone_contraintes)
        contraintes.setContentsMargins(0, 6, 0, 0)
        contraintes.addWidget(QLabel("Structures à équilibrer",
                                     objectName="titreCarte"))
        self.ligne_equilibre = QHBoxLayout()
        self.ligne_equilibre.setSpacing(6)
        contraintes.addLayout(self.ligne_equilibre)
        reglages = QGridLayout()
        self.s_hausse = self.champ_reglage(reglages, 0, "Hausse max par an",
                                           "0,05 pour 5 %")
        self.s_tri = self.champ_reglage(reglages, 1, "TRI cible",
                                        "0,10 pour 10 %")
        reglages.addWidget(QLabel("Structure du TRI"), 2, 0)
        self.s_structure_tri = _Qt.QComboBox()   # noms = données
        self.s_structure_tri.activated.connect(self.appliquer_reglages)
        reglages.addWidget(self.s_structure_tri, 2, 1, 1, 2)
        self.s_tresorerie = self.champ_reglage(reglages, 3,
                                               "Trésorerie minimale")
        reglages.setColumnStretch(2, 1)
        contraintes.addLayout(reglages)
        colonne.addWidget(self.zone_contraintes)
        colonne.addWidget(QLabel("Tarifs concernés", objectName="titreCarte"))
        self.s_tarifs = QLabel(wordWrap=True)
        self.s_tarifs.linkActivated.connect(self.ouvrir_tarif)
        colonne.addWidget(self.s_tarifs)
        colonne.addStretch(1)
        grille.addWidget(cadre, 1, 1, 2, 1)
        # Vérification.
        cadre, colonne = self.nouvelle_carte("Vérification avant lancement")
        self.s_verification = QLabel(wordWrap=True)
        self.s_verification.linkActivated.connect(self.ouvrir_probleme)
        colonne.addWidget(self.s_verification)
        grille.addWidget(cadre, 3, 0, 1, 2)
        ligne = QHBoxLayout()
        self.s_message = QLabel(objectName="discret", wordWrap=True)
        ligne.addWidget(self.s_message, 1)
        self.s_lancer = QPushButton("Lancer la simulation  ▶",
                                    objectName="principal")
        self.s_lancer.clicked.connect(self.lancer)
        ligne.addWidget(self.s_lancer)
        grille.addLayout(ligne, 4, 0, 1, 2)
        grille.setColumnStretch(0, 1)
        grille.setColumnStretch(1, 1)
        grille.setRowStretch(5, 1)
        return defilement

    def remplir_simulation(self):
        m, s = self.modele, self.modele.simulation
        self.chargement_simulation = True
        for champ, cle in ((self.s_debut, "date_debut"), (self.s_pas, "pas"),
                           (self.s_fin, "date_fin"),
                           (self.s_iterations, "iterations_max"),
                           (self.s_taux, "taux_actualisation"),
                           (self.s_hausse, "hausse_max"),
                           (self.s_tri, "tri_cible"),
                           (self.s_tresorerie, "tresorerie_min")):
            champ.setText(s.get(cle, ""))
        self.s_libelle_pas.setText(m.references_unites["Temps"] + " "
                                   + tr("(unité de référence)"))
        self.s_conserver.setChecked(s.get("conserver_convergence") == "oui")
        options = str(s.get("option_tarifs") or "actuels").split(",")
        for option, case in self.s_options.items():
            case.setChecked(option in options)
        while self.ligne_equilibre.count():
            element = self.ligne_equilibre.takeAt(0)
            if element.widget():
                element.widget().deleteLater()
        equilibre = s.get("structures_equilibre", "").split(",")
        self.s_equilibre = {}
        for i, fiche in m.structures.items():
            bouton = _Qt.QPushButton(fiche["nom"], objectName="pastille",
                                 checkable=True)
            bouton.setChecked(i in equilibre)
            bouton.toggled.connect(self.appliquer_reglages)
            self.ligne_equilibre.addWidget(bouton)
            self.s_equilibre[i] = bouton
        self.ligne_equilibre.addStretch(1)
        self.s_structure_tri.clear()
        self.s_structure_tri.addItem("—", "")
        for i, fiche in m.structures.items():
            self.s_structure_tri.addItem(fiche["nom"], i)
        self.s_structure_tri.setCurrentIndex(
            max(self.s_structure_tri.findData(s.get("structure_tri", "")), 0))
        self.chargement_simulation = False
        self.majs_simulation()

    def appliquer_reglages(self, *_args):
        """Chaque réglage est porté dans le modèle dès sa saisie."""
        if getattr(self, "chargement_simulation", True):
            return
        m = self.modele
        options = [o for o, case in self.s_options.items()
                   if case.isChecked()]
        principale = self.s_principale.currentData()
        try:
            m.definir_simulation(
                self.s_debut.text(), self.s_pas.text().replace(",", "."),
                self.s_fin.text(), self.s_iterations.text(),
                "oui" if self.s_conserver.isChecked() else "non",
                self.s_taux.text().replace(",", "."))
            if principale in options:
                m.simulation["option_principale"] = principale
            m.definir_tarifs(
                ",".join(options),
                [i for i, b in self.s_equilibre.items() if b.isChecked()],
                self.s_hausse.text().replace(",", "."),
                self.s_tri.text().replace(",", "."),
                self.s_structure_tri.currentData() or "",
                self.s_tresorerie.text().replace(",", "."))
            self.s_message.setText("")
        except ErreurModele as erreur:
            self.s_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
        self.resultat = None
        self.majs_simulation()
        self.rafraichir()

    def majs_simulation(self):
        """Résumé du temps, options, tarifs concernés et vérification."""
        m, s = self.modele, self.modele.simulation
        try:
            periodes = ppp_moteur.construire_periodes(m)
            premier, dernier = periodes[0], periodes[-1]
            texte = "→ %d pas de %s %s, du %s au %s" % (
                len(periodes), s["pas"], m.references_unites["Temps"],
                premier["debut"].strftime("%d/%m/%Y"),
                (dernier["fin"] - datetime.timedelta(days=1)).strftime(
                    "%d/%m/%Y"))
            if dernier.get("tronque"):
                texte += " ; dernier pas raccourci"
            self.s_resume.setText('<span style="color:%s">%s</span>'
                                  % (VERT, texte))
        except Exception as erreur:
            texte = str(erreur)
            if "/" in texte and " " not in texte.strip():
                texte = "Date invalide : " + texte
            self.s_resume.setText('<span style="color:#C0392B">%s</span>'
                                  % texte)
        options = [o for o, case in self.s_options.items()
                   if case.isChecked()]
        principale = s.get("option_principale") or (options or [""])[0]
        self.s_principale.blockSignals(True)
        self.s_principale.clear()
        for option in options:
            self.s_principale.addItem(TEXTES_OPTIONS[option][0], option)
        self.s_principale.setCurrentIndex(
            max(self.s_principale.findData(principale), 0))
        self.s_principale.setEnabled(len(options) > 1)
        self.s_principale.blockSignals(False)
        self.zone_contraintes.setVisible(
            any(o != "actuels" for o in options))
        tarifs = [(i, f.get("tarif_max", "")) for i, f in
                  sorted(m.parametres.items()) if f.get("optimisable")]
        self.s_tarifs.setText(
            "<br>".join('<a href="%s" style="color:%s">%s</a>%s' % (
                i, VERT, i, "  ·  max %s" % t if t else "")
                for i, t in tarifs) or
            '<span style="color:#C2610C">Aucun tarif optimisable : cochez '
            '« Tarif optimisable » dans l\'écran Paramètres.</span>')
        erreurs, alertes = m.verifier()
        lignes = []
        for texte in erreurs[:8]:
            lignes.append('<span style="color:#C0392B">✗</span> %s %s'
                          % (texte, self.lien_probleme(texte)))
        for texte in alertes[:6]:
            lignes.append('<span style="color:#C2610C">⚠</span> %s %s'
                          % (texte, self.lien_probleme(texte)))
        reste = len(erreurs) + len(alertes) - len(lignes)
        if reste > 0:
            lignes.append('<span style="color:%s">… et %d autre(s)</span>'
                          % (GRIS, reste))
        if not erreurs:
            lignes.insert(0, '<span style="color:%s">✓ Modèle complet : %d '
                          'paramètres, état initial saisi.</span>'
                          % (VERT, len(m.parametres)))
        self.s_verification.setText("<br>".join(lignes))
        self.s_lancer.setEnabled(not erreurs)

    def lien_probleme(self, texte):
        identifiant = texte.split(" : ")[0].strip()
        if identifiant not in self.modele.parametres:
            return ""
        ecran = "initial" if "valeur initiale" in texte else "parametre"
        return '&nbsp;<a href="%s|%s" style="color:%s">Ouvrir →</a>' % (
            ecran, identifiant, VERT)

    def ouvrir_probleme(self, lien):
        ecran, identifiant = lien.split("|", 1)
        if ecran == "initial":
            self.choisir(4)
            self.recherche_i.setText(identifiant.split("[")[0])
        else:
            self.ouvrir_tarif(identifiant)

    def ouvrir_tarif(self, identifiant):
        self.choisir(3)
        self.aller_parametre(identifiant)

    # ------------------------------- Résultats -------------------------------
    def creer_page_resultats(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(24, 20, 24, 14)
        colonne.setSpacing(10)
        entete = QHBoxLayout()
        entete.setSpacing(8)
        entete.addWidget(QLabel("Résultats", objectName="titre"))
        entete.addSpacing(16)
        entete.addWidget(QLabel("Scénario", objectName="discret"))
        self.r_scenario = QComboBox()
        self.r_scenario.setMinimumWidth(210)
        entete.addWidget(self.r_scenario)
        entete.addWidget(QLabel("Périmètre", objectName="discret"))
        self.r_perimetre = _Qt.QComboBox()   # noms = données
        self.r_perimetre.setMinimumWidth(170)
        entete.addWidget(self.r_perimetre)
        entete.addWidget(QLabel("De", objectName="discret"))
        self.r_debut = QComboBox()
        entete.addWidget(self.r_debut)
        entete.addWidget(QLabel("à", objectName="discret"))
        self.r_fin = QComboBox()
        entete.addWidget(self.r_fin)
        for choix in (self.r_scenario, self.r_perimetre, self.r_debut,
                      self.r_fin):
            choix.activated.connect(self.afficher_resultats)
        entete.addStretch(1)
        self.r_ref_etiquette = _Qt.QLabel(objectName="discret")
        entete.addWidget(self.r_ref_etiquette)
        comparer = QToolButton(text="Comparer  ▾", objectName="export",
                               popupMode=QToolButton.InstantPopup)
        menu = QMenu(comparer)
        menu.addAction("Garder ce calcul comme référence",
                       self.garder_reference)
        menu.addAction("Charger un calcul de référence (.dat)...",
                       self.charger_reference)
        menu.addAction("Retirer la référence", self.retirer_reference)
        comparer.setMenu(menu)
        entete.addWidget(comparer)
        exporter = QToolButton(text="Exporter  ▾", objectName="export",
                               popupMode=QToolButton.InstantPopup)
        menu = QMenu(exporter)
        for texte, action in (
                ("Tableau de l'onglet (.csv)", self.exporter_onglet),
                ("Image de l'onglet (.png)", self.exporter_image),
                ("Imprimer le schéma des flux...",
                 lambda: self.imprimer_scene(*self.scene_resultat())),
                ("Schéma des flux en PDF ou PNG...",
                 lambda: self.exporter_scene(*self.scene_resultat())),
                ("Courbes cochées en PDF", self.exporter_courbes),
                ("Valeurs des courbes cochées (.csv)",
                 lambda: self.exporter_series(".csv")),
                ("Valeurs des courbes cochées (.dat)",
                 lambda: self.exporter_series(".dat")),
                ("Fichier Resultat.dat", self.exporter_dat)):
            menu.addAction(texte, action)
        exporter.setMenu(menu)
        entete.addWidget(exporter)
        colonne.addLayout(entete)
        self.r_vide = QLabel(
            "Aucun résultat pour l'instant : lancez la simulation (écran 6).",
            objectName="discret", alignment=Qt.AlignCenter)
        colonne.addWidget(self.r_vide, 1)
        self.r_onglets = QTabWidget(objectName="onglets")
        self.r_onglets.currentChanged.connect(self.afficher_resultats)
        colonne.addWidget(self.r_onglets, 1)
        self.r_onglets.addTab(self.creer_onglet_flux(), "Flux")
        self.r_onglets.addTab(self.creer_onglet_synthese(), "Synthèse")
        self.r_onglets.addTab(self.creer_onglet_repartition(), "Répartition")
        self.r_onglets.addTab(self.creer_onglet_comptes(), "Comptes")
        self.r_onglets.addTab(self.creer_onglet_tarifs(), "Tarifs")
        self.r_onglets.addTab(self.creer_onglet_perimetres_r(), "Périmètres")
        self.r_onglets.addTab(self.creer_onglet_courbes(), "Courbes")
        self.r_onglets.addTab(self.creer_onglet_comparaison(), "Comparaison")
        self.r_onglets.addTab(self.creer_onglet_controle(), "Contrôle")
        self.r_message = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.r_message)
        return page

    # Réglages communs
    def preparer_resultats(self):
        """Remplit les sélecteurs à partir du dernier calcul."""
        r = self.resultat
        self.r_vide.setVisible(r is None)
        self.r_onglets.setVisible(r is not None)
        if r is None:
            return
        for choix in (self.r_scenario, self.r_perimetre, self.r_debut,
                      self.r_fin):
            choix.blockSignals(True)
        self.r_scenario.clear()
        scenarios = r.get("scenarios") or {}
        for option in scenarios or ["actuels"]:
            self.r_scenario.addItem(TEXTES_OPTIONS[option][0], option)
        principale = (r.get("tarifs") or {}).get("choix")
        self.r_scenario.setCurrentIndex(
            max(self.r_scenario.findData(principale), 0))
        self.r_scenario.setEnabled(len(scenarios) > 1)
        self.r_perimetre.clear()
        self.r_perimetre.addItem(tr("Global"), "")
        source = r.get("source") or self.modele
        for p in source.perimetres:
            self.r_perimetre.addItem(p["nom"], p["nom"])
        for colonne in source.colonnes_groupes:
            valeurs = list(dict.fromkeys(p["groupes"].get(colonne, "")
                                         for p in source.perimetres))
            for valeur in valeurs:
                if valeur:
                    self.r_perimetre.addItem(
                        "%s : %s" % (colonne, valeur),
                        "%s:%s" % (colonne, valeur))
        self.r_perimetre.setEnabled(self.r_perimetre.count() > 1)
        annees = ppp_moteur.annees_resultat(r)
        for choix, rang in ((self.r_debut, 0), (self.r_fin, -1)):
            choix.clear()
            for annee in annees:
                choix.addItem(str(annee), annee)
            choix.setCurrentIndex(rang % len(annees))
        for choix in (self.r_scenario, self.r_perimetre, self.r_debut,
                      self.r_fin):
            choix.blockSignals(False)
        self.remplir_liste_courbes()
        self.afficher_resultats()

    # ------------------------- Comparaison (sensibilité) --------------------
    def vue_reference(self):
        """Calcul de référence, même scénario que le calcul affiché s'il
        existe ; None sans référence."""
        ref = getattr(self, "r_reference", None)
        if not ref:
            return None
        r = ref["resultat"]
        option = self.r_scenario.currentData()
        return (r.get("scenarios") or {}).get(option) or r

    def poser_reference(self, resultat, nom):
        self.r_reference = {"resultat": resultat, "nom": nom}
        self.r_ref_etiquette.setText(tr("Comparé à : ") + nom)
        self.r_ref_etiquette.setToolTip(tr(
            "Les courbes de la référence sont en tirets ; l'onglet "
            "Comparaison donne les écarts."))
        self.afficher_resultats()

    def garder_reference(self):
        if self.resultat is None:
            return
        nom = "%s (%s)" % (os.path.basename(self.chemin)
                           or tr("Nouveau projet"),
                           datetime.datetime.now().strftime("%H:%M"))
        # Copie : le modèle continuera d'être modifié. La fenêtre de calcul,
        # gardée par le simulateur, ne se copie pas : elle est laissée vide.
        memo = {}
        for r in [self.resultat] + list(
                (self.resultat.get("scenarios") or {}).values()):
            progression = getattr(r.get("simulateur"), "progression", None)
            if progression is not None:
                memo[id(progression)] = None
        self.poser_reference(copy.deepcopy(self.resultat, memo), nom)
        self.r_message.setText(tr(
            "Calcul gardé comme référence. Modifiez le modèle, relancez la "
            "simulation : les deux calculs seront comparés."))

    def charger_reference(self):
        chemin = QFileDialog.getOpenFileName(
            self, "Calcul de référence", os.path.dirname(
                os.path.abspath(self.chemin or chemin_local("x"))),
            "Fichier dat (*.dat)")[0]
        if not chemin:
            return
        try:
            modele = Modele.lire(chemin)
        except (ErreurModele, IndexError, KeyError, ValueError,
                UnicodeDecodeError) as erreur:
            QMessageBox.warning(self, TITRE_APPLICATION, str(erreur))
            return
        erreurs = modele.verifier()[0]
        if erreurs:
            QMessageBox.warning(
                self, TITRE_APPLICATION,
                tr("Ce modèle n'est pas prêt à être simulé :") + "\n"
                + "\n".join(erreurs[:6]))
            return
        fenetre = FenetreCalcul(self)
        fenetre.setWindowTitle(tr("Calcul de référence"))
        fenetre.show()
        QApplication.processEvents()
        resultat = ppp_moteur.simuler_tarifs(modele, fenetre)
        fenetre.terminer(resultat)
        fenetre.bouton_resultats.hide()
        if not resultat["erreurs"]:
            self.poser_reference(resultat, os.path.basename(chemin))
        fenetre.exec()

    def retirer_reference(self):
        self.r_reference = None
        self.r_ref_etiquette.setText("")
        self.afficher_resultats()

    def creer_onglet_comparaison(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        self.r_cmp_note = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.r_cmp_note)
        self.r_cmp = self.arbre_tableau()
        colonne.addWidget(self.r_cmp, 1)
        return page

    def afficher_comparaison(self):
        arbre = self.r_cmp
        arbre.clear()
        ref = self.vue_reference()
        if ref is None:
            arbre.setColumnCount(1)
            arbre.setHeaderLabels([""])
            self.r_cmp_note.setText(tr(
                "Aucune référence. Menu « Comparer » : gardez le calcul "
                "actuel comme référence avant de modifier le modèle, ou "
                "chargez un autre fichier .dat (il est simulé, seuls ses "
                "résultats sont gardés)."))
            return
        periode = self.periode_choisie()
        def principales(synthese):
            # Sans le détail flux par flux : les totaux de la synthèse.
            return synthese[0], [l for l in synthese[1] if l[1] != "detail"]

        actuel = principales(ppp_moteur.synthese_resultat(self.vue(), periode))
        autre = principales(ppp_moteur.synthese_resultat(ref, periode))
        noms_ref = ref["modele"].structures
        noms = self.vue()["modele"].structures
        valeurs_ref = {}
        for libelle, genre, valeurs in autre[1]:
            for s, v in zip(autre[0], valeurs):
                valeurs_ref[(s, libelle, genre)] = v
        self.r_cmp_note.setText(tr(
            "Écart = calcul actuel − référence (%s), sur la période "
            "choisie. Les structures sont reconnues par leur identifiant.")
            % self.r_reference["nom"])
        arbre.setColumnCount(5)
        arbre.setHeaderLabels(["", tr("Actuel"), tr("Référence"),
                               tr("Écart"), tr("Écart %")])
        structures = list(actuel[0]) + [s for s in autre[0]
                                         if s not in actuel[0]]
        for s in structures:
            nom = (noms.get(s) or noms_ref.get(s) or {}).get("nom", s)
            groupe = QTreeWidgetItem([nom])
            arbre.addTopLevelItem(groupe)
            groupe.setFirstColumnSpanned(True)
            lignes = [(l, g) for l, g, _v in actuel[1]]
            lignes += [(l, g) for l, g, _v in autre[1]
                       if (l, g) not in lignes]
            for libelle, genre in lignes:
                ligne_actuelle = next((v for l, g, v in actuel[1]
                                       if (l, g) == (libelle, genre)), [])
                a = dict(zip(actuel[0], ligne_actuelle)).get(s)
                b = valeurs_ref.get((s, libelle, genre))
                if not a and not b:
                    continue
                ecart = (a or 0.0) - (b or 0.0)
                pourcent = "%+.1f %%" % (100 * ecart / abs(b)) \
                    if b else "—"
                ligne = QTreeWidgetItem(
                    [tr(libelle),
                     nombre_tableau(a) if a is not None else "—",
                     nombre_tableau(b) if b is not None else "—",
                     ("+" if ecart > 0 else "") + nombre_tableau(ecart),
                     pourcent.replace(".", ",")])
                for colonne in range(1, 5):
                    ligne.setTextAlignment(colonne,
                                           Qt.AlignRight | Qt.AlignVCenter)
                if abs(ecart) > 1e-9 * max(abs(a or 0), abs(b or 0), 1):
                    couleur = QColor(VERT if ecart > 0 else "#C0392B")
                    ligne.setForeground(3, couleur)
                    ligne.setForeground(4, couleur)
                groupe.addChild(ligne)
            groupe.setExpanded(True)
        arbre.header().setStretchLastSection(False)
        for colonne in range(5):
            arbre.resizeColumnToContents(colonne)
        arbre.setColumnWidth(0, max(arbre.columnWidth(0), 320))

    def vue(self):
        """Résultat du scénario choisi."""
        r = self.resultat
        option = self.r_scenario.currentData()
        return (r.get("scenarios") or {}).get(option) or r

    def periode_choisie(self):
        debut, fin = self.r_debut.currentData(), self.r_fin.currentData()
        annees = ppp_moteur.annees_resultat(self.resultat)
        if debut is None or (debut == annees[0] and fin == annees[-1]):
            return None
        debut, fin = min(debut, fin), max(debut, fin)
        return debut if debut == fin else (debut, fin)

    def rangs_choisis(self, r):
        periode = self.periode_choisie()
        return [k for k, p in enumerate(r["periodes"])
                if ppp_moteur.dans_periode(p, periode)]

    def afficher_resultats(self, *_args):
        if self.resultat is None:
            return
        onglet = self.r_onglets.currentIndex()
        self.r_message.setText("")
        try:
            (self.afficher_flux, self.afficher_synthese,
             self.afficher_repartition, self.afficher_comptes,
             self.afficher_tarifs, self.afficher_perimetres_r,
             self.afficher_courbes, self.afficher_comparaison,
             self.afficher_controle)[onglet]()
        except Exception as erreur:              # vue incomplète : on le dit
            self.r_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)

    # Onglet Flux
    def creer_onglet_flux(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        self.r_cartes = QHBoxLayout()
        self.r_cartes.setSpacing(12)
        colonne.addLayout(self.r_cartes)
        self.r_coupe_flux = QSplitter(Qt.Horizontal,
                                      childrenCollapsible=False)
        self.r_schema = QGraphicsView(QGraphicsScene(self))
        self.r_schema.setRenderHint(QPainter.Antialiasing)
        self.r_coupe_flux.addWidget(self.r_schema)
        detail = QFrame(objectName="carteBlanche")
        detail.setMinimumWidth(360)
        self.r_pile_detail = QStackedWidget()
        cadre = QVBoxLayout(detail)
        cadre.setContentsMargins(16, 14, 16, 14)
        cadre.addWidget(self.r_pile_detail)
        page_fleche = QWidget()
        boite = QVBoxLayout(page_fleche)
        boite.setContentsMargins(0, 0, 0, 0)
        self.r_pile_detail.addWidget(page_fleche)
        self.r_detail_titre = QLabel("Cliquez sur une flèche",
                                     objectName="titreCarte", wordWrap=True)
        boite.addWidget(self.r_detail_titre)
        self.r_detail_texte = QLabel(objectName="discret", wordWrap=True)
        boite.addWidget(self.r_detail_texte)
        self.r_detail_courbe = Apercu()
        self.r_detail_courbe.setMinimumSize(320, 220)
        boite.addWidget(self.r_detail_courbe, 1)
        # Détail d'une structure : tableau par année et courbe de la ligne.
        page_structure = QWidget()
        boite = QVBoxLayout(page_structure)
        boite.setContentsMargins(0, 0, 0, 0)
        self.r_s_titre = _Qt.QLabel(objectName="titreCarte")
        boite.addWidget(self.r_s_titre)
        self.r_s_note = QLabel(objectName="discret", wordWrap=True)
        boite.addWidget(self.r_s_note)
        coupe = QSplitter(Qt.Vertical, childrenCollapsible=False)
        self.r_s_table = self.arbre_tableau()
        self.r_s_table.itemClicked.connect(self.courbe_ligne_structure)
        coupe.addWidget(self.r_s_table)
        self.r_s_courbe = Apercu()
        self.r_s_courbe.setMinimumHeight(200)
        coupe.addWidget(self.r_s_courbe)
        coupe.setSizes([420, 220])
        boite.addWidget(coupe, 1)
        self.r_pile_detail.addWidget(page_structure)
        self.r_coupe_flux.addWidget(detail)
        self.r_coupe_flux.setSizes([700, 500])
        colonne.addWidget(self.r_coupe_flux, 1)
        colonne.addWidget(QLabel(
            "Montants payés sur la période. Trait plein : argent ; "
            "pointillé : flux physique. Sous le montant payé : le dû et les "
            "impayés quand ils diffèrent. Cliquez sur une structure pour "
            "voir l'évolution de tous ses chiffres.", objectName="discret",
            wordWrap=True))
        return page

    def montants_vue(self, r):
        perimetre = self.r_perimetre.currentData()
        if perimetre and r.get("par_p"):
            return ppp_moteur.flux_filtres(r, perimetre)
        return r["montants"], r["dus"]

    def afficher_flux(self):
        r = self.vue()
        m = r["modele"]
        rangs = self.rangs_choisis(r)
        payes, dus = self.montants_vue(r)
        structures, lignes = ppp_moteur.repartition_resultat(
            r, self.periode_choisie(), self.r_perimetre.currentData() or "")
        par_ligne = {libelle: valeurs for libelle, _g, valeurs in lignes}
        # Cartes : ce qu'il reste à chaque structure.
        while self.r_cartes.count():
            element = self.r_cartes.takeAt(0)
            if element.widget():          # retiré tout de suite de l'écran
                element.widget().setParent(None)
        restes = par_ligne.get(T("Reste à la structure"), [])
        parts = par_ligne.get(T("Part de l'argent apporté (%)"), [])
        for rang, s in enumerate(structures):
            carte = QFrame(objectName="carteBlanche")
            boite = QVBoxLayout(carte)
            boite.setContentsMargins(14, 10, 14, 10)
            boite.setSpacing(0)
            boite.addWidget(_Qt.QLabel(tr("Reste à") + " "
                                       + m.structures[s]["nom"],
                                       objectName="discret"))
            valeur = restes[rang] if rang < len(restes) else None
            boite.addWidget(QLabel(nombre_court(valeur or 0),
                                   objectName="chiffre"))
            part = parts[rang] if rang < len(parts) else None
            boite.addWidget(QLabel("" if part is None else
                                   ("%.1f %% de l'argent apporté" % part)
                                   .replace(".", ","), objectName="discret"))
            self.r_cartes.addWidget(carte)
        self.r_cartes.addStretch(1)
        # Schéma : une flèche par couple payeur -> bénéficiaire.
        scene = self.r_schema.scene()
        scene.clear()
        for i, fiche in m.structures.items():
            fond, bord = COULEURS_TYPES.get(fiche["type"], FOND_AUTRE)
            choisie = i == getattr(self, "r_structure_vue", None)
            bloc = ClicBlocResultat(self, i, QRectF(
                fiche["x"] - LARGEUR_BLOC / 2, fiche["y"] - HAUTEUR_BLOC / 2,
                LARGEUR_BLOC, HAUTEUR_BLOC))
            bloc.setPen(QPen(QColor(VERT if choisie else bord),
                             3 if choisie else 1.5))
            bloc.setBrush(QBrush(QColor(fond)))
            scene.addItem(bloc)
            bloc.setZValue(2)
            nom = scene.addSimpleText(fiche["nom"], QFont("Inter", 11,
                                                          QFont.DemiBold))
            nom.setPos(fiche["x"] - nom.boundingRect().width() / 2,
                       fiche["y"] - 12)
            nom.setZValue(3)
        couples = {}
        for i, f in m.flux.items():
            if f["nature"] == "Financier":
                total = sum(payes.get(i, [0] * len(r["periodes"]))[k]
                            for k in rangs)
                du = sum(dus.get(i, [0] * len(r["periodes"]))[k]
                         for k in rangs)
                unite = m.references_unites["Monnaie"]
            else:
                if i not in r["series"]:
                    continue
                total, unite = self.volume_physique(r, i, rangs)
                du = total
            cle = (f["payeur"], f["beneficiaire"], f["nature"])
            somme = couples.setdefault(cle, {"paye": 0.0, "du": 0.0,
                                             "flux": [], "unite": unite})
            somme["paye"] += total
            somme["du"] += du
            somme["flux"].append(i)
        plus_grand = max([abs(c["paye"]) for (a, b, n), c in couples.items()
                          if n == "Financier"] + [1e-9])
        self.r_couples = couples
        rangs_couple = {}
        for (a, b, nature), c in couples.items():
            paire = tuple(sorted((a, b)))
            rangs_couple.setdefault(paire, []).append((a, b, nature))
        for paire, liste in rangs_couple.items():
            for rang, cle in enumerate(liste):
                decalage = (rang - (len(liste) - 1) / 2) * 70
                self.fleche_resultat(scene, cle, couples[cle], decalage,
                                     plus_grand)
        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-40, -40,
                                                              40, 40))
        self.r_schema.fitInView(scene.sceneRect(), Qt.KeepAspectRatio)
        if self.r_schema.transform().m11() > 1:
            self.r_schema.resetTransform()
        choisie = getattr(self, "r_fleche", None)
        structure = getattr(self, "r_structure_vue", None)
        if choisie in couples:              # même flèche, nouveaux réglages
            self.detail_fleche(choisie)
        elif structure in m.structures:     # même structure, nouvelle période
            self.detail_structure(structure)
        else:
            self.r_pile_detail.setCurrentIndex(0)
            self.r_detail_titre.setText("Cliquez sur une flèche")
            self.r_detail_texte.setText("pour voir son montant année par "
                                        "année.")
            self.r_detail_courbe.montrer([], message="")

    def fleche_resultat(self, scene, cle, somme, decalage, plus_grand):
        m = self.vue()["modele"]
        a, b = m.structures[cle[0]], m.structures[cle[1]]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        longueur = max(math.hypot(dx, dy), 1)
        ux, uy = dx / longueur, dy / longueur
        if cle[0] > cle[1]:
            decalage = -decalage
        ox, oy = -uy * decalage, ux * decalage

        def bord(vx, vy):
            distances = [((LARGEUR_BLOC / 2 + 6) / abs(vx)) if abs(vx) > 1e-9
                         else 1e9, ((HAUTEUR_BLOC / 2 + 6) / abs(vy))
                         if abs(vy) > 1e-9 else 1e9]
            return min(distances)

        depart = QPointF(a["x"] + ox + ux * bord(ux, uy),
                         a["y"] + oy + uy * bord(ux, uy))
        arrivee = QPointF(b["x"] + ox - ux * bord(ux, uy),
                          b["y"] + oy - uy * bord(ux, uy))
        financier = cle[2] == "Financier"
        epaisseur = 2 + 9 * abs(somme["paye"]) / plus_grand if financier \
            else 2
        couleur = QColor(VERT if financier else GRIS)
        stylo = QPen(couleur, epaisseur, Qt.SolidLine if financier
                     else Qt.DashLine, Qt.FlatCap)
        chemin = QPainterPath(depart)
        chemin.lineTo(arrivee - QPointF(ux, uy) * 10)
        trait = ClicResultat(self, cle, chemin)
        trait.setPen(stylo)
        trait.setZValue(1)
        scene.addItem(trait)
        pointe = QPolygonF([arrivee, arrivee - QPointF(ux, uy) * 14
                            + QPointF(-uy, ux) * (5 + epaisseur / 2),
                            arrivee - QPointF(ux, uy) * 14
                            - QPointF(-uy, ux) * (5 + epaisseur / 2)])
        scene.addPolygon(pointe, Qt.NoPen, QBrush(couleur)).setZValue(1)
        # Le montant, à côté de la flèche.
        texte = "%s %s" % (nombre_court(somme["paye"]), somme["unite"])
        details = []
        if financier and abs(somme["du"] - somme["paye"]) > 0.005 * max(
                abs(somme["du"]), 1):
            details.append(tr("dû %s · impayés %s") % (
                nombre_court(somme["du"]),
                nombre_court(somme["du"] - somme["paye"])))
        noms = [m.flux[i]["nom"] if i in m.flux else i
                for i in somme["flux"]]
        details.append(", ".join(noms[:2]) + ("…" if len(noms) > 2 else ""))
        etiquette = QGraphicsSimpleTextItem(texte)
        etiquette.setFont(QFont("Inter", 11, QFont.DemiBold))
        etiquette.setBrush(QColor(ENCRE if financier else GRIS))
        petit = QGraphicsSimpleTextItem("\n".join(details))
        petit.setFont(QFont("Inter", 8))
        petit.setBrush(QColor(GRIS))
        largeur = max(etiquette.boundingRect().width(),
                      petit.boundingRect().width())
        hauteur = etiquette.boundingRect().height() + \
            petit.boundingRect().height()
        # À côté de la flèche, du côté extérieur, sans la recouvrir.
        nx, ny = -uy, ux
        distance = epaisseur / 2 + 8 + abs(nx) * (largeur / 2 + 6) \
            + abs(ny) * (hauteur / 2 + 3)
        milieu = (depart + arrivee) / 2 + QPointF(nx, ny) * distance * (
            1 if decalage >= 0 else -1)
        coin = milieu - QPointF(largeur / 2, hauteur / 2)
        porteur = somme["flux"][0]          # le décalage est gardé sur lui
        fond = EtiquetteMobile(
            QRectF(0, 0, largeur, hauteur).adjusted(-6, -3, 6, 3), coin,
            self.modele.flux.get(porteur, {}).get("etiquette_resultat")
            or (0, 0),
            lambda decalage: self.deplacer_etiquette(
                porteur, "etiquette_resultat", decalage))
        fond.setPen(Qt.NoPen)
        fond.setBrush(QBrush(QColor(255, 255, 255, 235)))
        fond.setZValue(4)
        scene.addItem(fond)
        for element, y in ((etiquette, 0),
                           (petit, etiquette.boundingRect().height())):
            element.setParentItem(fond)
            element.setPos((largeur - element.boundingRect().width()) / 2, y)

    def volume_physique(self, r, i, rangs):
        """Volume d'un flux physique sur les pas ; avec un périmètre ou un
        groupe, somme de ses parts x[s,dakar]... quand le flux en a."""
        perimetre = self.r_perimetre.currentData()
        source = r.get("source")
        if not perimetre or source is None:
            return ppp_moteur.quantite_physique(r, i, rangs)
        nom, structure = decomposer_id(i)
        parts = ["%s[%s,%s]" % (nom, structure, pid)
                 for pid in source.membres(perimetre)]
        parts = [p for p in parts if p in r["series"]]
        if not parts:                  # flux sans part par périmètre
            total, unite = ppp_moteur.quantite_physique(r, i, rangs)
            return total, unite + " (global)"
        total, unite = 0.0, ""
        for part in parts:
            valeur, unite = ppp_moteur.quantite_physique(r, part, rangs)
            total += valeur
        return total, unite

    def detail_structure(self, identifiant):
        """Tableau année par année d'une structure : sa synthèse (charges,
        recettes, impôts, résultat...) puis tous ses paramètres."""
        r = self.vue()
        m = r["modele"]
        source = r.get("source") or self.modele
        self.r_structure_vue, self.r_fleche = identifiant, None
        self.r_pile_detail.setCurrentIndex(1)
        largeur = self.r_coupe_flux.width()
        self.r_coupe_flux.setSizes([int(largeur * 0.38), int(largeur * 0.62)])
        QTimer.singleShot(0, self.recadrer_schema_resultat)
        rangs = self.rangs_choisis(r)
        annees = sorted({r["periodes"][k]["debut"].year for k in rangs})
        self.r_s_titre.setText(m.structures[identifiant]["nom"])
        perimetre = self.r_perimetre.currentData()
        self.r_s_note.setText(tr(
            "Synthèse au niveau Global ; paramètres par périmètre filtrés."
            if perimetre else
            "Cliquez sur une ligne pour voir sa courbe. Synthèse par année, "
            "puis tous les paramètres de la structure."))
        lignes = []
        # 1. Synthèse, une année à la fois.
        par_annee = {}
        for annee in annees:
            structures, synthese = ppp_moteur.synthese_resultat(r, annee)
            if identifiant not in structures:
                continue
            rang = structures.index(identifiant)
            for libelle, genre, valeurs in synthese:
                cle = (libelle, genre)
                par_annee.setdefault(cle, {})[annee] = \
                    valeurs[rang] if rang < len(valeurs) else None
        ordre = []
        for annee in annees[:1]:
            ordre = [(l, g) for l, g, _v in ppp_moteur.synthese_resultat(
                r, annee)[1]]
        lignes.append((tr("Synthèse"), "titre", []))
        for libelle, genre in ordre:
            valeurs = [par_annee.get((libelle, genre), {}).get(a)
                       for a in annees]
            if genre != "titre" and all(v in (None, 0) for v in valeurs):
                continue                      # ligne vide pour cette structure
            lignes.append((libelle, genre, valeurs))
        # 2. Tous les paramètres de la structure (développés par périmètre
        # puis regroupés selon le périmètre choisi).
        membres = set(source.membres(perimetre)) if perimetre else None
        groupes = {}
        for cle, serie in r["series"].items():
            if "[" not in cle:
                continue
            nom, structure = decomposer_id(cle)
            if structure != identifiant:
                continue
            pid = perimetre_id(cle) if "," in cle else ""
            if pid and membres is not None and pid not in membres:
                continue
            base = "%s[%s%s]" % (nom, structure, ",p" if pid else "")
            groupes.setdefault(base, []).append(cle)
        # Un flux réparti par périmètre existe deux fois : le total x[s] et
        # ses parts x[s,p]. Global : le total ; périmètre choisi : ses parts.
        for base in list(groupes):
            if base.endswith(",p]"):
                total = base[:-3] + "]"
                if total in groupes:
                    del groupes[total if perimetre else base]
        lignes.append((tr("Paramètres"), "titre", []))
        for base in sorted(groupes):
            cles = groupes[base]
            unite = r["unites"].get(cles[0], "")
            valeurs = [self.valeur_annuelle(r, cles, annee, unite, m)
                       for annee in annees]
            libelle = base + ("  (%s)" % unite if unite else "")
            lignes.append((libelle, "ligne", valeurs))
        self.r_s_lignes = {libelle: (annees, valeurs)
                           for libelle, genre, valeurs in lignes
                           if genre != "titre"}
        self.remplir_arbre(self.r_s_table, [str(a) for a in annees], lignes)
        self.r_s_courbe.montrer([], message="Cliquez sur une ligne du tableau.")

    def recadrer_schema_resultat(self):
        vue = self.r_schema
        vue.fitInView(vue.scene().sceneRect(), Qt.KeepAspectRatio)
        if vue.transform().m11() > 1:
            vue.resetTransform()

    def valeur_annuelle(self, r, cles, annee, unite, m):
        """Valeur d'une année : somme des montants par pas, valeur de fin
        d'année pour un poste (stock), moyenne pour un prix, un taux ou un
        débit. Plusieurs périmètres : somme si additif, sinon moyenne."""
        rangs = [k for k, p in enumerate(r["periodes"])
                 if p["debut"].year == annee]
        if not rangs:
            return None
        resultats = []
        for cle in cles:
            serie = r["series"][cle]
            generique = cle.split(",")[0] + "]" if "," in cle else cle
            if generique in m.postes or cle in m.postes:
                resultats.append(serie[rangs[-1]])
            elif "/" not in unite and unite not in ("", "sans unité"):
                resultats.append(sum(serie[k] for k in rangs))
            else:
                resultats.append(sum(serie[k] for k in rangs) / len(rangs))
        if len(resultats) == 1:
            return resultats[0]
        return sum(resultats) if ppp_moteur.est_additive(unite) \
            else sum(resultats) / len(resultats)

    def courbe_ligne_structure(self, element, _colonne=0):
        libelle = element.text(0)
        if libelle not in getattr(self, "r_s_lignes", {}):
            return
        annees, valeurs = self.r_s_lignes[libelle]
        points = [(a, v) for a, v in zip(annees, valeurs) if v is not None]
        self.r_s_courbe.montrer([(libelle, VERT, points, True)], True, 1.0,
                                libelle, "" if points else
                                "Pas de valeur sur ces années.")

    def detail_fleche(self, cle):
        """Courbe annuelle d'une flèche : argent payé ou volume livré."""
        r = self.vue()
        m = r["modele"]
        self.r_fleche, self.r_structure_vue = cle, None
        self.r_pile_detail.setCurrentIndex(0)
        somme = self.r_couples[cle]
        payes, _dus = self.montants_vue(r)
        rangs = self.rangs_choisis(r)
        financier = cle[2] == "Financier"
        par_annee = {}
        for i in somme["flux"]:
            if financier:
                serie = payes.get(i)
                if not serie:
                    continue
                quantites = [(k, serie[k]) for k in rangs]
            else:
                # Un débit (m3/an) devient un volume : débit × durée du pas,
                # comme dans le total affiché sur la flèche.
                quantites = [(k, self.volume_physique(r, i, [k])[0])
                             for k in rangs if i in r["series"]]
            for k, valeur in quantites:
                annee = r["periodes"][k]["debut"].year
                par_annee[annee] = par_annee.get(annee, 0.0) + valeur
        unite = somme["unite"].replace(" (global)", "")
        self.r_detail_titre.setText("%s → %s" % (
            m.structures[cle[0]]["nom"], m.structures[cle[1]]["nom"]))
        self.r_detail_texte.setText(
            "%s : %s %s sur la période" % (
                ", ".join(somme["flux"]), nombre_court(somme["paye"]), unite))
        courbes = [("payé" if financier else "volume",
                    VERT if financier else GRIS, sorted(par_annee.items()),
                    True)]
        ref = self.vue_reference()
        if ref is not None:
            try:
                payes_ref = self.montants_vue(ref)[0]
            except Exception:                  # périmètre absent de la réf.
                payes_ref = ref["montants"]
            par_annee_ref = {}
            for i in somme["flux"]:
                if financier:
                    serie = payes_ref.get(i)
                    valeurs = [(k, serie[k]) for k in self.rangs_choisis(ref)
                               if serie and k < len(serie)]
                elif i in ref["series"]:
                    valeurs = [(k, self.volume_physique(ref, i, [k])[0])
                               for k in self.rangs_choisis(ref)]
                else:
                    valeurs = []
                for k, valeur in valeurs:
                    annee = ref["periodes"][k]["debut"].year
                    par_annee_ref[annee] = par_annee_ref.get(annee, 0.0) \
                        + valeur
            if par_annee_ref:
                courbes.append((tr("référence"), VERT if financier else GRIS,
                                sorted(par_annee_ref.items()), True, True))
        self.r_detail_courbe.montrer(courbes, True, 1.0, unite + " par an")

    # Onglet Synthèse
    def arbre_tableau(self):
        arbre = QTreeWidget(objectName="tableau")
        arbre.setRootIsDecorated(True)
        arbre.setAlternatingRowColors(False)
        arbre.setUniformRowHeights(True)
        return arbre

    def creer_onglet_synthese(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        self.r_note_synthese = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.r_note_synthese)
        self.r_synthese = self.arbre_tableau()
        colonne.addWidget(self.r_synthese, 1)
        return page

    def remplir_arbre(self, arbre, colonnes, lignes):
        """Lignes (libellé, genre, valeurs) ; les « detail » se déplient."""
        arbre.clear()
        arbre.setColumnCount(1 + len(colonnes))
        arbre.setHeaderLabels([""] + list(colonnes))
        entetes = arbre.header()
        entetes.setMinimumSectionSize(120)
        for rang in range(1 + len(colonnes)):
            entetes.setSectionResizeMode(rang, QHeaderView.ResizeToContents)
        if len(colonnes) <= 5:          # peu de colonnes : libellés au large
            entetes.setSectionResizeMode(0, QHeaderView.Stretch)
        entetes.setStretchLastSection(False)
        parent = None
        for libelle, genre, valeurs in lignes:
            element = QTreeWidgetItem([libelle] + [
                nombre_tableau(v, genre) for v in valeurs])
            for rang in range(1, 1 + len(colonnes)):
                element.setTextAlignment(rang, Qt.AlignRight
                                         | Qt.AlignVCenter)
            if genre == "titre":
                police = element.font(0)
                police.setBold(True)
                police.setPointSize(9)
                element.setFont(0, police)
                element.setForeground(0, QColor(VERT))
                arbre.addTopLevelItem(element)
                element.setFirstColumnSpanned(True)   # après l'ajout
                parent = None
            elif genre == "detail":
                for rang in range(1 + len(colonnes)):
                    element.setForeground(rang, QColor(GRIS))
                if parent is not None:
                    parent.addChild(element)
                else:                    # détail sans ligne mère : à plat
                    arbre.addTopLevelItem(element)
            else:
                if genre == "total":
                    for rang in range(1 + len(colonnes)):
                        police = element.font(rang)
                        police.setBold(True)
                        element.setFont(rang, police)
                arbre.addTopLevelItem(element)
                parent = element

    def afficher_synthese(self):
        r = self.vue()
        structures, lignes = ppp_moteur.synthese_resultat(
            r, self.periode_choisie())
        noms = [r["modele"].structures[s]["nom"] for s in structures]
        self.remplir_arbre(self.r_synthese, noms, lignes)
        self.r_note_synthese.setText(
            "La synthèse est au niveau Global ; l'onglet Périmètres détaille "
            "chaque périmètre." if self.r_perimetre.currentData() else
            "Cliquez sur ▸ pour voir le détail d'une ligne. VAN et TRI ne "
            "sont calculés que sur toute la durée.")

    # Onglet Comptes
    def creer_onglet_comptes(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel("Structure", objectName="discret"))
        self.r_structure = _Qt.QComboBox()   # noms = données
        self.r_structure.setMinimumWidth(220)
        self.r_structure.activated.connect(self.afficher_resultats)
        ligne.addWidget(self.r_structure)
        ligne.addStretch(1)
        colonne.addLayout(ligne)
        self.r_comptes = QTableWidget(objectName="tableau")
        self.r_comptes.verticalHeader().hide()
        self.r_comptes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        colonne.addWidget(self.r_comptes, 1)
        return page

    def afficher_comptes(self):
        r = self.vue()
        m = r["modele"]
        actuelle = self.r_structure.currentData()
        self.r_structure.clear()
        for i, fiche in m.structures.items():
            self.r_structure.addItem(fiche["nom"], i)
        self.r_structure.setCurrentIndex(
            max(self.r_structure.findData(actuelle), 0))
        s = self.r_structure.currentData()
        rangs = set(self.rangs_choisis(r))
        lignes = [c for k, c in enumerate(
            [c for c in r["comptes"] if c["structure"] == s]) if k in rangs]
        colonnes = [(cle, libelle) for cle, libelle in
                    ppp_moteur.COMPTES_AFFICHES
                    if any(abs(c.get(cle) or 0) > 1e-9 for c in lignes)]
        table = self.r_comptes
        table.clear()
        table.setRowCount(len(colonnes))
        table.setColumnCount(1 + len(lignes))
        table.setHorizontalHeaderLabels(
            ["Compte"] + [c["periode"].strftime("%Y") if r["periodes"][0][
                "jours"] >= 365 else c["periode"].strftime("%m/%Y")
                for c in lignes])
        for rang, (cle, libelle) in enumerate(colonnes):
            table.setItem(rang, 0, QTableWidgetItem(libelle))
            for k, c in enumerate(lignes, start=1):
                case = QTableWidgetItem(nombre_tableau(c.get(cle), "ligne"))
                case.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(rang, k, case)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        for k in range(1, 1 + len(lignes)):
            table.horizontalHeader().resizeSection(k, 120)
        self.r_message.setText(
            "Comptes en %s, structure par structure ; les lignes toujours "
            "nulles sont masquées." % m.references_unites["Monnaie"])

    # Onglet Tarifs
    def creer_onglet_tarifs(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel("Tarif", objectName="discret"))
        self.r_tarif = _Qt.QComboBox()   # noms = données
        self.r_tarif.setMinimumWidth(240)
        self.r_tarif.activated.connect(self.afficher_resultats)
        ligne.addWidget(self.r_tarif)
        ligne.addStretch(1)
        colonne.addLayout(ligne)
        coupe = QSplitter(Qt.Horizontal, childrenCollapsible=False)
        self.r_courbe_tarif = Apercu()
        coupe.addWidget(self.r_courbe_tarif)
        self.r_table_tarifs = self.arbre_tableau()
        coupe.addWidget(self.r_table_tarifs)
        coupe.setSizes([600, 600])
        colonne.addWidget(coupe, 1)
        return page

    def afficher_tarifs(self):
        r = self.resultat
        donnees = r.get("tarifs")
        if not donnees:
            self.r_courbe_tarif.montrer(
                [], message="Aucun tarif optimisable : cochez « Tarif "
                "optimisable » dans l'écran Paramètres.")
            self.r_table_tarifs.clear()
            return
        actuel = self.r_tarif.currentData()
        self.r_tarif.clear()
        for i in donnees["unites"]:
            self.r_tarif.addItem(i, i)
        self.r_tarif.setCurrentIndex(max(self.r_tarif.findData(actuel), 0))
        i = self.r_tarif.currentData()
        annees_de = [p["debut"].year for p in r["periodes"]]
        courbes = []
        for rang, (option, valeurs) in enumerate(donnees["options"].items()):
            serie = valeurs["series"][i]
            points = []
            for annee in donnees["annees"]:
                rangs = [k for k, a in enumerate(annees_de) if a == annee]
                points.append((annee, sum(serie[k] for k in rangs)
                               / len(rangs)))
            courbes.append((TEXTES_OPTIONS[option][0],
                            PALETTE[rang % len(PALETTE)], points, True))
        self.r_courbe_tarif.montrer(courbes, True, 1.0,
                                    donnees["unites"][i])
        colonnes, lignes = ppp_moteur.tarifs_resultat(r)
        self.remplir_arbre(self.r_table_tarifs, colonnes, lignes)

    # Onglet Périmètres
    def creer_onglet_perimetres_r(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel("Regrouper par", objectName="discret"))
        self.r_niveau = _Qt.QComboBox()   # noms = données
        self.r_niveau.activated.connect(self.afficher_resultats)
        ligne.addWidget(self.r_niveau)
        ligne.addSpacing(12)
        ligne.addWidget(QLabel("Indicateur sur la carte",
                               objectName="discret"))
        self.r_indicateur = QComboBox()
        self.r_indicateur.setMinimumWidth(320)
        self.r_indicateur.activated.connect(self.afficher_resultats)
        ligne.addWidget(self.r_indicateur)
        ligne.addStretch(1)
        colonne.addLayout(ligne)
        coupe = QSplitter(Qt.Horizontal, childrenCollapsible=False)
        self.r_carte = Carte()
        coupe.addWidget(self.r_carte)
        self.r_table_perimetres = self.arbre_tableau()
        coupe.addWidget(self.r_table_perimetres)
        coupe.setSizes([520, 680])
        colonne.addWidget(coupe, 1)
        return page

    def afficher_perimetres_r(self):
        r = self.vue()
        source = r.get("source") or self.modele
        niveaux = ppp_moteur.niveaux_perimetres(r)
        actuel = self.r_niveau.currentText()
        self.r_niveau.clear()
        for niveau in niveaux:
            self.r_niveau.addItem(tr("Périmètre (p)") if niveau == "p"
                                  else tr(niveau), niveau)
        self.r_niveau.setCurrentIndex(max(self.r_niveau.findText(actuel), 0
                                          if len(niveaux) < 2 else 1))
        niveau = self.r_niveau.currentData() or ppp_moteur.GLOBAL
        colonnes, lignes = ppp_moteur.perimetres_resultat(
            r, self.periode_choisie(), niveau)
        self.remplir_arbre(self.r_table_perimetres, colonnes, lignes)
        # Indicateurs : chaque ligne chiffrée, préfixée de sa structure.
        choix, titre = [], ""
        for libelle, genre, valeurs in lignes:
            if genre == "titre":
                titre = libelle
            elif valeurs:
                choix.append(("%s · %s" % (titre, libelle), valeurs))
        actuel = self.r_indicateur.currentText()
        self.r_indicateur.clear()
        for libelle, _v in choix:
            self.r_indicateur.addItem(libelle)
        if actuel:
            self.r_indicateur.setCurrentIndex(
                max(self.r_indicateur.findText(actuel), 0))
        if not choix:
            self.r_carte.montrer([], message="Pas de valeur par périmètre.")
            return
        valeurs = dict(zip(colonnes, choix[max(
            self.r_indicateur.currentIndex(), 0)][1]))
        # Position de chaque colonne : périmètre ou centre de ses membres.
        _libelles, correspondance = ppp_moteur.colonnes_perimetres(r, niveau)
        positions = {}
        for p in source.perimetres:
            if p.get("x") is None or p.get("y") is None:
                continue
            colonne = correspondance.get(creer_id(p["nom"]))
            positions.setdefault(colonne, []).append((p["x"], p["y"]))
        if niveau == ppp_moteur.GLOBAL:
            toutes = [xy for liste in positions.values() for xy in liste]
            positions = {colonnes[0]: toutes} if toutes else {}
        plus_grand = max([abs(v or 0) for c, v in valeurs.items()
                          if c in positions] + [1e-9])
        points = []
        for rang, (colonne, liste) in enumerate(positions.items()):
            if colonne not in valeurs or not liste:
                continue
            valeur = valeurs[colonne] or 0
            points.append({
                "nom": colonne, "texte": nombre_court(valeur),
                "x": sum(x for x, _y in liste) / len(liste),
                "y": sum(y for _x, y in liste) / len(liste),
                "rayon": 6 + 26 * math.sqrt(abs(valeur) / plus_grand),
                "couleur": VERT if valeur >= 0 else "#C0392B"})
        self.r_carte.points = []
        self.r_carte.montrer(points, None, "", "" if points else
                             "Ajoutez les colonnes X et Y des périmètres "
                             "(écran 2) pour les voir sur la carte.")

    # Onglet Courbes
    def creer_onglet_courbes(self):
        page = QWidget()
        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(0, 12, 0, 0)
        gauche = QVBoxLayout()
        self.r_recherche = QLineEdit(placeholderText="Rechercher une "
                                     "variable")
        self.r_recherche.textChanged.connect(self.filtrer_courbes)
        gauche.addWidget(self.r_recherche)
        self.r_liste = QTreeWidget(headerHidden=True)
        self.r_liste.itemChanged.connect(
            lambda _e, _c: self.afficher_resultats())
        gauche.addWidget(self.r_liste, 1)
        bouton = QPushButton("Tout décocher")
        bouton.clicked.connect(self.decocher_courbes)
        gauche.addWidget(bouton)
        boite = QWidget()
        boite.setLayout(gauche)
        boite.setFixedWidth(340)
        ligne.addWidget(boite)
        droite = QVBoxLayout()
        reglages = QHBoxLayout()
        self.r_mode = QComboBox()
        self.r_mode.addItems(["Courbes", "Tableau des valeurs"])
        self.r_mode.activated.connect(self.afficher_resultats)
        reglages.addWidget(self.r_mode)
        reglages.addSpacing(12)
        reglages.addWidget(QLabel("Axe du temps", objectName="discret"))
        self.r_axe = QComboBox()
        self.r_axe.addItems(["Date", "t", "t_sim"] + list(TEMPS_FIXES))
        self.r_axe.activated.connect(self.afficher_resultats)
        reglages.addWidget(self.r_axe)
        reglages.addStretch(1)
        droite.addLayout(reglages)
        self.r_pile = QStackedWidget()
        defilement = QScrollArea(widgetResizable=True,
                                 frameShape=QFrame.NoFrame)
        self.r_zone_courbes = QWidget(objectName="page")
        self.r_boite_courbes = QVBoxLayout(self.r_zone_courbes)
        self.r_boite_courbes.setContentsMargins(0, 0, 0, 0)
        defilement.setWidget(self.r_zone_courbes)
        self.r_pile.addWidget(defilement)
        self.r_valeurs = QTableWidget(objectName="tableau")
        self.r_valeurs.verticalHeader().hide()
        self.r_valeurs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r_pile.addWidget(self.r_valeurs)
        droite.addWidget(self.r_pile, 1)
        ligne.addLayout(droite, 1)
        return page

    def decocher_courbes(self):
        self.r_liste.blockSignals(True)
        for k in range(self.r_liste.topLevelItemCount()):
            groupe = self.r_liste.topLevelItem(k)
            for j in range(groupe.childCount()):
                groupe.child(j).setCheckState(0, Qt.Unchecked)
        self.r_liste.blockSignals(False)
        self.afficher_resultats()

    def afficher_courbes(self):
        r = self.vue()
        self.r_tables = ppp_moteur.tables_resultat(r)
        cles = [c for c in self.cles_cochees() if c in self.r_tables]
        while self.r_boite_courbes.count():
            element = self.r_boite_courbes.takeAt(0)
            if element.widget():
                element.widget().setParent(None)
        rangs = self.rangs_choisis(r)
        axe = self.r_axe.currentText()
        if axe == "Date":
            abscisses = [r["periodes"][k]["annee_decimale"] for k in rangs]
            pas = Apercu.PAS_TEMPS.get(
                r["modele"].references_unites["Temps"], 1.0)
        else:
            source = r["series"].get(axe) or [p.get(axe, 0)
                                              for p in r["periodes"]]
            abscisses = [source[k] for k in rangs]
            pas = 1.0
        if self.r_mode.currentIndex() == 1:
            self.r_pile.setCurrentIndex(1)
            self.remplir_valeurs(r, cles, rangs)
            return
        self.r_pile.setCurrentIndex(0)
        if not cles:
            vide = Apercu()
            vide.montrer([], message="Cochez une ou plusieurs variables à "
                         "gauche : un graphique par unité.")
            self.r_boite_courbes.addWidget(vide)
            return
        # Un graphique par unité, comme dans le rapport PDF.
        par_unite = {}
        for cle in cles:
            par_unite.setdefault(self.r_tables[cle][2], []).append(cle)
        self.r_boite_courbes.setSpacing(12)
        reference = None
        ref = self.vue_reference()
        if ref is not None:
            reference = (ppp_moteur.tables_resultat(ref), ref["periodes"],
                         self.rangs_choisis(ref))
        for unite, groupe in par_unite.items():
            carte = QFrame(objectName="carteBlanche")
            carte.setMinimumHeight(320 if len(par_unite) > 1 else 460)
            boite = QVBoxLayout(carte)
            boite.setContentsMargins(12, 10, 12, 8)
            graphique = Apercu()
            boite.addWidget(graphique)
            courbes = []
            for rang, cle in enumerate(groupe[:10]):
                _g, libelle, _u, valeurs = self.r_tables[cle]
                couleur = PALETTE[rang % len(PALETTE)]
                courbes.append((libelle, couleur,
                                list(zip(abscisses,
                                         [valeurs[k] for k in rangs])),
                                axe == "Date"))
                if reference and cle in reference[0] and axe == "Date":
                    serie = reference[0][cle][3]
                    courbes.append((
                        "%s (%s)" % (libelle, tr("réf.")), couleur,
                        [(reference[1][k]["annee_decimale"], serie[k])
                         for k in reference[2] if k < len(serie)],
                        True, True))
            graphique.montrer(courbes, True, pas, unite or "sans unité")
            self.r_boite_courbes.addWidget(carte)
        self.r_boite_courbes.addStretch(1)

    def remplir_valeurs(self, r, cles, rangs):
        """Tableau des valeurs : une ligne par pas, une colonne par série."""
        table = self.r_valeurs
        table.clear()
        cles = cles or []
        table.setColumnCount(1 + len(cles))
        table.setRowCount(len(rangs))
        table.setHorizontalHeaderLabels(
            ["Date"] + ["%s\n(%s)" % (self.r_tables[c][1],
                                      self.r_tables[c][2]) for c in cles])
        for ligne, k in enumerate(rangs):
            table.setItem(ligne, 0, QTableWidgetItem(
                r["periodes"][k]["debut"].strftime("%d/%m/%Y")))
            for colonne, cle in enumerate(cles, start=1):
                case = QTableWidgetItem(nombre_tableau(
                    self.r_tables[cle][3][k]))
                case.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(ligne, colonne, case)
        table.resizeColumnsToContents()
        if not cles:
            self.r_message.setText("Cochez des variables à gauche pour voir "
                                   "leurs valeurs.")

    # Onglet Répartition
    def creer_onglet_repartition(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        colonne.addWidget(QLabel(
            "Qui paie qui, et ce qu'il reste à chaque structure : montants "
            "payés, sur la période et le périmètre choisis.",
            objectName="discret", wordWrap=True))
        self.r_titre_argent = QLabel(objectName="titreSection")
        colonne.addWidget(self.r_titre_argent)
        self.r_argent = DiagrammeArgent()
        self.r_repartition = self.arbre_tableau()
        partage = QSplitter(Qt.Vertical)
        partage.addWidget(self.r_argent)
        partage.addWidget(self.r_repartition)
        partage.setStretchFactor(0, 3)
        partage.setStretchFactor(1, 2)
        partage.setChildrenCollapsible(False)
        colonne.addWidget(partage, 1)
        return page

    def afficher_repartition(self):
        r = self.vue()
        structures, lignes = ppp_moteur.repartition_resultat(
            r, self.periode_choisie(), self.r_perimetre.currentData() or "")
        self.remplir_arbre(self.r_repartition,
                           [r["modele"].structures[s]["nom"]
                            for s in structures], lignes)
        donnees = ppp_moteur.flux_argent(
            r, self.periode_choisie(), self.r_perimetre.currentData() or "")
        self.r_argent.montrer(donnees)
        self.r_titre_argent.setText(
            tr("Où va l'argent") + (" : " if LANGUE["code"] == "fr" else ": ")
            + "%s %s %s" % (
                nombre_court(donnees["apporte"]), donnees["monnaie"],
                tr("apportés sur la période")))

    # Onglet Contrôle
    def creer_onglet_controle(self):
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 12, 0, 0)
        self.r_controle = self.arbre_tableau()
        colonne.addWidget(self.r_controle, 1)
        return page

    def afficher_controle(self):
        """Statut, convergence des boucles, alertes et variables suivies."""
        r = self.vue()
        lignes = [("Statut", "titre", []),
                  ("Simulation : " + r["statut"], "ligne", [])]
        if r.get("convergence"):
            lignes.append(("Boucles", "titre", []))
            for bloc in r["convergence"]:
                lignes.append(("%s%s : %d itération(s) au plus, écart %.3g"
                               % (" + ".join(bloc["variables"]),
                                  " (Newton)" if bloc["newton"] else "",
                                  bloc["iterations"], bloc["ecart"]),
                               "ligne", []))
        for titre, cle in (("Erreurs", "erreurs"), ("Alertes", "alertes")):
            if r.get(cle):
                lignes.append((titre, "titre", []))
                lignes += [(texte, "ligne", []) for texte in r[cle]]
        suivi = ppp_moteur.resumer_suivi(r)
        if suivi:
            lignes.append(("Variables suivies", "titre", []))
            lignes += [(texte, "detail", []) for texte in suivi[:400]]
        self.remplir_arbre(self.r_controle, [], lignes)

    def remplir_liste_courbes(self):
        self.r_tables = ppp_moteur.tables_resultat(self.vue())
        liste = self.r_liste
        liste.blockSignals(True)
        cochees = set(getattr(self, "r_cochees", []))
        liste.clear()
        groupes = {}
        for cle, (groupe, libelle, unite, _v) in self.r_tables.items():
            if groupe not in groupes:
                groupes[groupe] = QTreeWidgetItem([groupe])
                groupes[groupe].setFlags(Qt.ItemIsEnabled)
                liste.addTopLevelItem(groupes[groupe])
            element = QTreeWidgetItem(["%s  (%s)" % (libelle, unite)
                                       if unite else libelle])
            element.setData(0, Qt.UserRole, cle)
            element.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            element.setCheckState(0, Qt.Checked if cle in cochees
                                  else Qt.Unchecked)
            groupes[groupe].addChild(element)
        liste.blockSignals(False)
        self.filtrer_courbes()

    def filtrer_courbes(self, *_args):
        texte = self.r_recherche.text().strip().lower()
        for k in range(self.r_liste.topLevelItemCount()):
            groupe = self.r_liste.topLevelItem(k)
            visibles = 0
            for j in range(groupe.childCount()):
                enfant = groupe.child(j)
                montre = not texte or texte in enfant.text(0).lower()
                enfant.setHidden(not montre)
                visibles += montre
            groupe.setHidden(not visibles)
            cochee = any(groupe.child(j).checkState(0) == Qt.Checked
                         for j in range(groupe.childCount()))
            groupe.setExpanded(bool(texte) or cochee or k < 2)

    def cles_cochees(self):
        cles = []
        for k in range(self.r_liste.topLevelItemCount()):
            groupe = self.r_liste.topLevelItem(k)
            for j in range(groupe.childCount()):
                if groupe.child(j).checkState(0) == Qt.Checked:
                    cles.append(groupe.child(j).data(0, Qt.UserRole))
        self.r_cochees = cles
        return cles

    # Exports
    def exporter_onglet(self):
        onglet = self.r_onglets.currentWidget()
        tableau = onglet.findChild(QTreeWidget, "tableau") or \
            onglet.findChild(QTableWidget, "tableau")
        if tableau is None:
            self.r_message.setText("Cet onglet n'a pas de tableau : utilisez "
                                   "l'export en image.")
            return
        chemin = QFileDialog.getSaveFileName(
            self, "Exporter le tableau", chemin_local(
                "Resultats_%s.csv" % self.r_onglets.tabText(
                    self.r_onglets.currentIndex())),
            "Fichier csv (*.csv)")[0]
        if not chemin:
            return
        lignes = []
        if isinstance(tableau, QTreeWidget):
            entetes = [tableau.headerItem().text(c)
                       for c in range(tableau.columnCount())]
            lignes.append(entetes)
            pile = [tableau.topLevelItem(k)
                    for k in range(tableau.topLevelItemCount())]
            while pile:
                element = pile.pop(0)
                lignes.append([element.text(c) for c in
                               range(tableau.columnCount())])
                pile[0:0] = [element.child(j)
                             for j in range(element.childCount())]
        else:
            lignes.append([tableau.horizontalHeaderItem(c).text()
                           for c in range(tableau.columnCount())])
            for ligne in range(tableau.rowCount()):
                lignes.append([tableau.item(ligne, c).text()
                               if tableau.item(ligne, c) else ""
                               for c in range(tableau.columnCount())])
        with open(chemin, "w", encoding="utf-8-sig") as fichier:
            for ligne in lignes:
                fichier.write(";".join(t.replace(" ", "")
                                       for t in ligne) + "\n")
        self.r_message.setText("Tableau enregistré : "
                               + os.path.basename(chemin))

    # ------------------------- Impression des schémas ----------------------
    def bouton_impression(self, source):
        """Bouton « Imprimer ▾ » : imprimante, PDF ou image PNG.
        source() rend (scène, titre, nom de fichier proposé)."""
        bouton = QToolButton(text="Imprimer  ▾", objectName="export",
                             popupMode=QToolButton.InstantPopup)
        menu = QMenu(bouton)
        menu.addAction("Imprimer...", lambda: self.imprimer_scene(*source()))
        menu.addAction("Enregistrer en PDF ou PNG...",
                       lambda: self.exporter_scene(*source()))
        bouton.setMenu(menu)
        return bouton

    def scene_resultat(self):
        periode = "%s-%s" % (self.r_debut.currentText(),
                             self.r_fin.currentText())
        titre = "%s · %s · %s · %s" % (
            tr("Flux"), self.r_scenario.currentText(),
            self.r_perimetre.currentText(), periode)
        return self.r_schema.scene(), titre, "Flux_" + periode

    def peindre_scene(self, peintre, page, scene, titre):
        """Dessine le schéma entier dans le rectangle page (titre en haut,
        mention en bas), proportions gardées."""
        projet = os.path.basename(self.chemin) or tr("Nouveau projet")
        hauteur_texte = min(page.height(), page.width() * 0.75) * 0.045
        police = QFont("Inter")
        police.setPixelSize(max(int(hauteur_texte * 0.55), 8))
        police.setBold(True)
        peintre.setFont(police)
        peintre.setPen(QColor(ENCRE))
        entete = QFontMetricsF(police, peintre.device()).elidedText(
            "%s — %s" % (projet, titre), Qt.ElideMiddle, page.width())
        peintre.drawText(QRectF(page.left(), page.top(), page.width(),
                                hauteur_texte),
                         Qt.AlignLeft | Qt.AlignVCenter, entete)
        police.setBold(False)
        police.setPixelSize(max(int(hauteur_texte * 0.35), 6))
        peintre.setFont(police)
        peintre.setPen(QColor(GRIS))
        peintre.drawText(QRectF(page.left(), page.bottom() - hauteur_texte,
                                page.width(), hauteur_texte),
                         Qt.AlignRight | Qt.AlignVCenter,
                         "%s · %s" % (QDate.currentDate().toString(
                             "dd/MM/yyyy"), tr(COPYRIGHT)))
        source = scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
        cible = QRectF(page.left(), page.top() + hauteur_texte * 1.3,
                       page.width(), page.height() - hauteur_texte * 2.6)
        scene.clearSelection()
        scene.render(peintre, cible, source, Qt.KeepAspectRatio)

    def imprimer_scene(self, scene, titre, _nom):
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        imprimante = QPrinter(QPrinter.HighResolution)
        source = scene.itemsBoundingRect()
        imprimante.setPageOrientation(
            QPageLayout.Landscape if source.width() >= source.height()
            else QPageLayout.Portrait)
        dialogue = QPrintDialog(imprimante, self)
        dialogue.setWindowTitle(tr("Imprimer le schéma"))
        if dialogue.exec() != QDialog.Accepted:
            return
        self.imprimer_vers(imprimante, scene, titre)

    def imprimer_vers(self, appareil, scene, titre):
        peintre = QPainter(appareil)
        peintre.setRenderHint(QPainter.Antialiasing)
        page = QRectF(appareil.pageLayout().paintRectPixels(
            appareil.resolution()))
        self.peindre_scene(peintre, QRectF(0, 0, page.width(),
                                           page.height()), scene, titre)
        peintre.end()

    def exporter_scene(self, scene, titre, nom):
        chemin, filtre = QFileDialog.getSaveFileName(
            self, "Enregistrer le schéma", chemin_local(nom + ".pdf"),
            "PDF (*.pdf);;Image (*.png)")
        if not chemin:
            return
        if not chemin.lower().endswith((".pdf", ".png")):
            chemin += ".png" if "png" in filtre.lower() else ".pdf"
        source = scene.itemsBoundingRect()
        if chemin.lower().endswith(".pdf"):
            pdf = QPdfWriter(chemin)
            pdf.setResolution(300)
            pdf.setPageSize(QPageSize(QPageSize.A4))
            pdf.setPageMargins(QMarginsF(10, 10, 10, 10),
                               QPageLayout.Millimeter)
            pdf.setPageOrientation(
                QPageLayout.Landscape if source.width() >= source.height()
                else QPageLayout.Portrait)
            pdf.setTitle(titre)
            self.imprimer_vers(pdf, scene, titre)
        else:
            echelle = min(3.0, 3200 / max(source.width(), source.height(), 1))
            largeur = int(source.width() * echelle) + 80
            hauteur = int((source.height() * echelle + 80) / 0.91)
            image = QImage(largeur, hauteur, QImage.Format_ARGB32)
            image.fill(QColor("#FFFFFF"))
            peintre = QPainter(image)
            peintre.setRenderHint(QPainter.Antialiasing)
            peintre.setRenderHint(QPainter.TextAntialiasing)
            self.peindre_scene(peintre, QRectF(40, 20, largeur - 80,
                                               hauteur - 40), scene, titre)
            peintre.end()
            image.save(chemin, "PNG")
        QMessageBox.information(self, TITRE_APPLICATION,
                                tr("Schéma enregistré : ")
                                + os.path.basename(chemin))

    def exporter_image(self):
        chemin = QFileDialog.getSaveFileName(
            self, "Exporter l'image", chemin_local(
                "Resultats_%s.png" % self.r_onglets.tabText(
                    self.r_onglets.currentIndex())), "Image (*.png)")[0]
        if chemin:
            self.r_onglets.currentWidget().grab().save(chemin, "PNG")
            self.r_message.setText("Image enregistrée : "
                                   + os.path.basename(chemin))

    def exporter_courbes(self):
        cles = self.cles_cochees() if hasattr(self, "r_liste") else []
        if not cles:
            self.r_message.setText("Cochez d'abord des courbes dans "
                                   "l'onglet Courbes.")
            return
        chemin = QFileDialog.getSaveFileName(
            self, "Exporter les courbes", chemin_local("Courbes.pdf"),
            "PDF (*.pdf)")[0]
        if chemin:
            try:
                ppp_moteur.exporter_pdf(self.vue(), cles, chemin)
                self.r_message.setText("PDF enregistré : "
                                       + os.path.basename(chemin))
            except ImportError:
                self.r_message.setText("L'export PDF demande matplotlib : "
                                       "py -m pip install matplotlib")

    def exporter_series(self, extension):
        cles = self.cles_cochees() if hasattr(self, "r_liste") else []
        chemin = QFileDialog.getSaveFileName(
            self, "Exporter les valeurs", chemin_local("Series" + extension),
            "Fichier (*%s)" % extension)[0]
        if chemin:
            nombre = ppp_moteur.exporter_table(self.vue(), cles, chemin)
            self.r_message.setText(
                "%d série(s) enregistrée(s)%s : %s" % (
                    nombre, "" if cles else " (aucune cochée : toutes)",
                    os.path.basename(chemin)))

    def exporter_dat(self):
        chemin = QFileDialog.getSaveFileName(
            self, "Enregistrer le résultat",
            chemin_local(ppp_moteur.FICHIER_RESULTAT),
            "Fichier dat (*.dat)")[0]
        if chemin:
            ppp_moteur.ecrire_resultat(self.resultat, chemin)
            self.r_message.setText("Résultat enregistré : "
                                   + os.path.basename(chemin))

    # ---------------------------- Éditeur commun ----------------------------
    def editeur_code(self, hauteur=160):
        champ = QPlainTextEdit(objectName="formuleCode")
        police = QFont("Consolas")
        police.setStyleHint(QFont.Monospace)
        police.setPointSize(11)
        champ.setFont(police)
        champ.setTabStopDistance(28)
        champ.setMinimumHeight(hauteur)
        champ.surligneur = Surligneur(champ.document(), self)
        return champ

    def liste_laterale(self, titre, boutons):
        cadre = QFrame(objectName="carteBlanche")
        cadre.setFixedWidth(340)
        colonne = QVBoxLayout(cadre)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(8)
        colonne.addWidget(QLabel(titre, objectName="titre"))
        ligne = QHBoxLayout()
        for texte, action in boutons:
            bouton = QPushButton(texte)
            bouton.clicked.connect(action)
            ligne.addWidget(bouton)
        ligne.addStretch(1)
        colonne.addLayout(ligne)
        liste = QTreeWidget(headerHidden=True, rootIsDecorated=False,
                            indentation=10, columnCount=2)
        liste.header().setSectionResizeMode(0, QHeaderView.Stretch)
        liste.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        liste.header().setStretchLastSection(False)
        colonne.addWidget(liste, 1)
        return cadre, colonne, liste

    # ---------------------------- Post-traitement ----------------------------
    def creer_page_post(self):
        page = QWidget()
        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(24, 24, 24, 16)
        ligne.setSpacing(16)
        cadre, colonne, self.liste_post = self.liste_laterale(
            "Post-traitement", (("+ Nouvel indicateur", self.nouveau_post),))
        colonne.addWidget(QLabel(
            "Calculé après la simulation, sans effet sur le calcul : TRI, "
            "VAN, ratios, totaux...", objectName="discret", wordWrap=True))
        self.liste_post.currentItemChanged.connect(
            lambda actuel, _a: actuel and actuel.data(0, Qt.UserRole)
            and self.ouvrir_post(actuel.data(0, Qt.UserRole)))
        ligne.addWidget(cadre)
        editeur = QFrame(objectName="carteBlanche")
        colonne = QVBoxLayout(editeur)
        colonne.setContentsMargins(20, 18, 20, 18)
        colonne.setSpacing(10)
        self.q_titre = _Qt.QLabel(tr("Nouvel indicateur"),
                                 objectName="titreFiche")
        colonne.addWidget(self.q_titre)
        grille = QGridLayout()
        grille.addWidget(QLabel("Nom"), 0, 0)
        self.q_nom = QLineEdit(placeholderText="ex. tri_projet")
        grille.addWidget(self.q_nom, 0, 1)
        grille.addWidget(QLabel("Structure"), 0, 2)
        self.q_structure = _Qt.QComboBox()   # noms = données
        grille.addWidget(self.q_structure, 0, 3)
        grille.addWidget(QLabel("Unité"), 0, 4)
        self.q_unite = QComboBox()
        self.q_unite.addItems(UNITES)
        grille.addWidget(self.q_unite, 0, 5)
        grille.setColumnStretch(1, 1)
        colonne.addLayout(grille)
        travail = QHBoxLayout()
        travail.setSpacing(16)
        gauche = QVBoxLayout()
        self.q_expression = self.editeur_code()
        self.q_expression.setPlaceholderText(
            "ex. tri(entrees_moins_sorties[exploitant])")
        gauche.addWidget(self.q_expression, 1)
        self.q_controle = QLabel(wordWrap=True)
        gauche.addWidget(self.q_controle)
        gauche.addWidget(QLabel(
            "Fonctions de post-traitement : total, moyenne, minimum, "
            "maximum, van(série, taux), tri(série). Les autres fonctions "
            "s'appliquent pas à pas.", objectName="discret", wordWrap=True))
        travail.addLayout(gauche, 5)
        droite = QVBoxLayout()
        self.q_valeur = QLabel(objectName="chiffre")
        droite.addWidget(self.q_valeur)
        self.q_apercu = Apercu()
        droite.addWidget(self.q_apercu, 1)
        travail.addLayout(droite, 4)
        colonne.addLayout(travail, 1)
        actions = QHBoxLayout()
        self.q_message = QLabel(objectName="discret", wordWrap=True)
        actions.addWidget(self.q_message, 1)
        self.q_supprimer = QPushButton("Supprimer")
        self.q_supprimer.clicked.connect(self.supprimer_post)
        actions.addWidget(self.q_supprimer)
        bouton = QPushButton("Annuler")
        bouton.clicked.connect(lambda: self.ouvrir_post(self.post_ouvert))
        actions.addWidget(bouton)
        bouton = QPushButton("Enregistrer", objectName="principal")
        bouton.clicked.connect(self.enregistrer_post)
        actions.addWidget(bouton)
        colonne.addLayout(actions)
        ligne.addWidget(editeur, 1)
        self.minuterie_q = QTimer(self, singleShot=True, interval=500)
        self.minuterie_q.timeout.connect(self.verifier_post)
        for signal in (self.q_expression.textChanged,
                       self.q_nom.textChanged,
                       self.q_structure.currentIndexChanged):
            signal.connect(self.minuterie_q.start)
        self.post_ouvert = None
        return page

    def remplir_page_post(self):
        m = self.modele
        self.q_structure.blockSignals(True)
        self.q_structure.clear()
        self.q_structure.addItem(tr("projet (commun)"), STRUCTURE_COMMUNE)
        for i, fiche in m.structures.items():
            self.q_structure.addItem(fiche["nom"], i)
        self.q_structure.blockSignals(False)
        liste = self.liste_post
        liste.blockSignals(True)
        liste.clear()
        choisi = None
        for i, q in sorted(m.post.items()):
            element = QTreeWidgetItem([i, q["unite"]])
            element.setData(0, Qt.UserRole, i)
            element.setForeground(1, QColor(GRIS))
            liste.addTopLevelItem(element)
            if i == self.post_ouvert:
                choisi = element
        if choisi:
            liste.setCurrentItem(choisi)
        liste.blockSignals(False)
        self.ouvrir_post(self.post_ouvert if self.post_ouvert in m.post
                         else None)

    def nouveau_post(self):
        self.liste_post.clearSelection()
        self.ouvrir_post(None)
        self.q_nom.setFocus()

    def ouvrir_post(self, identifiant):
        m = self.modele
        self.post_ouvert = identifiant
        fiche = m.post.get(identifiant) if identifiant else None
        self.q_titre.setText(identifiant or tr("Nouvel indicateur"))
        for champ in (self.q_nom, self.q_expression):
            champ.blockSignals(True)
        self.q_nom.setText(fiche["nom"] if fiche else "")
        self.q_expression.setPlainText(fiche["expression"] if fiche else "")
        self.q_expression.surligneur.rehighlight()
        for champ in (self.q_nom, self.q_expression):
            champ.blockSignals(False)
        self.q_structure.setCurrentIndex(max(self.q_structure.findData(
            fiche["structure"] if fiche else STRUCTURE_COMMUNE), 0))
        self.q_unite.setCurrentText(fiche["unite"] if fiche else "")
        self.q_supprimer.setVisible(fiche is not None)
        self.q_message.setText("")
        self.verifier_post()

    def verifier_post(self):
        """Contrôle et aperçu sur une copie du modèle, sans le modifier."""
        texte = self.q_expression.toPlainText()
        if not texte.strip() or not self.q_nom.text().strip():
            self.q_controle.setText(
                '<span style="color:#D9822B">● Saisissez un nom et une '
                'formule.</span>')
            self.q_valeur.setText("")
            self.q_apercu.montrer([], message="")
            return
        copie = copy.deepcopy(self.modele)
        try:
            cle = copie.ajouter_post(
                self.q_nom.text(), self.q_structure.currentData(), texte,
                self.q_unite.currentText(), self.post_ouvert)
            resultat = ppp_moteur.simuler(copie)
        except Exception as erreur:
            self.q_controle.setText('<span style="color:#C0392B">✗ %s</span>'
                                    % erreur)
            self.q_valeur.setText("")
            self.q_apercu.montrer([], message="")
            return
        serie = resultat["series"].get(cle)
        if not serie:
            self.q_controle.setText('<span style="color:#C0392B">✗ %s</span>'
                                    % (resultat["erreurs"] or
                                       ["Pas de valeur calculée."])[0])
            return
        self.q_controle.setText(
            '<span style="color:#2E8B57">✓ Formule valide : %s.</span>' % cle)
        unite = self.q_unite.currentText()
        constante = max(serie) - min(serie) < 1e-12 * max(1, abs(serie[0]))
        self.q_valeur.setText("%s %s" % (nombre_court(serie[-1]), unite)
                              if constante else
                              "dernière valeur : %s %s"
                              % (nombre_court(serie[-1]), unite))
        temps = [p["annee_decimale"] for p in resultat["periodes"]]
        self.q_apercu.montrer(
            [] if constante else [(cle, VERT, list(zip(temps, serie)),
                                   True)], True,
            Apercu.PAS_TEMPS.get(self.modele.references_unites["Temps"], 1),
            unite, "Valeur unique sur toute la simulation." if constante
            else "")

    def enregistrer_post(self):
        try:
            cle = self.modele.ajouter_post(
                self.q_nom.text(), self.q_structure.currentData(),
                self.q_expression.toPlainText(), self.q_unite.currentText(),
                self.post_ouvert)
        except ErreurModele as erreur:
            self.q_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
            return
        self.post_ouvert, self.resultat = cle, None
        self.remplir_page_post()
        self.rafraichir()
        self.q_message.setText("Enregistré dans le modèle.")

    def supprimer_post(self):
        if not self.post_ouvert:
            return
        try:
            self.modele.supprimer_post(self.post_ouvert)
        except ErreurModele as erreur:
            self.q_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
            return
        self.post_ouvert, self.resultat = None, None
        self.remplir_page_post()
        self.rafraichir()
        self.q_message.setText("Indicateur supprimé.")

    # ------------------------------- Fonctions -------------------------------
    def creer_page_fonctions(self):
        page = QWidget()
        ligne = QHBoxLayout(page)
        ligne.setContentsMargins(24, 24, 24, 16)
        ligne.setSpacing(16)
        cadre, colonne, self.liste_fonctions = self.liste_laterale(
            "Fonctions", (("+ Nouvelle", self.nouvelle_fonction),
                          ("Bibliothèque", self.ajouter_bibliotheque)))
        colonne.addWidget(QLabel(
            "Vos fonctions s'appellent dans toute formule, comme min ou si : "
            "annuite(montant[projet], 0.06, 15).", objectName="discret",
            wordWrap=True))
        self.liste_fonctions.currentItemChanged.connect(
            lambda actuel, _a: actuel and actuel.data(0, Qt.UserRole)
            and self.ouvrir_fonction(actuel.data(0, Qt.UserRole)))
        ligne.addWidget(cadre)
        editeur = QFrame(objectName="carteBlanche")
        colonne = QVBoxLayout(editeur)
        colonne.setContentsMargins(20, 18, 20, 18)
        colonne.setSpacing(10)
        self.f_titre = _Qt.QLabel(tr("Nouvelle fonction"),
                                 objectName="titreFiche")
        colonne.addWidget(self.f_titre)
        grille = QGridLayout()
        grille.addWidget(QLabel("Nom"), 0, 0)
        self.f_nom = QLineEdit(placeholderText="ex. cout_ouvrage")
        grille.addWidget(self.f_nom, 0, 1)
        grille.addWidget(QLabel("Arguments"), 0, 2)
        self.f_arguments = QLineEdit(placeholderText="ex. type, taille")
        grille.addWidget(self.f_arguments, 0, 3)
        grille.addWidget(QLabel("Description"), 1, 0)
        self.f_description = QLineEdit()
        grille.addWidget(self.f_description, 1, 1, 1, 3)
        grille.setColumnStretch(1, 1)
        grille.setColumnStretch(3, 1)
        colonne.addLayout(grille)
        colonne.addWidget(QLabel(
            "Corps : une ligne par calcul, « nom = formule » ; la dernière "
            "ligne est « résultat = ... ». Les arguments et les calculs "
            "internes s'écrivent sans crochets.", objectName="discret",
            wordWrap=True))
        self.f_corps = self.editeur_code(200)
        colonne.addWidget(self.f_corps, 1)
        self.f_controle = QLabel(wordWrap=True)
        colonne.addWidget(self.f_controle)
        self.f_appels = QLabel(objectName="discret", wordWrap=True)
        self.f_appels.linkActivated.connect(self.ouvrir_tarif)
        colonne.addWidget(self.f_appels)
        essai = QHBoxLayout()
        essai.addWidget(QLabel("Essai"))
        self.f_essai = QLineEdit(placeholderText="ex. annuite(1000000, "
                                 "0.06, 15)")
        self.f_essai.returnPressed.connect(self.essayer_fonction)
        essai.addWidget(self.f_essai, 1)
        bouton = QPushButton("Calculer")
        bouton.clicked.connect(self.essayer_fonction)
        essai.addWidget(bouton)
        self.f_resultat_essai = QLabel(objectName="chiffre")
        self.f_resultat_essai.setMinimumWidth(160)
        essai.addWidget(self.f_resultat_essai)
        colonne.addLayout(essai)
        actions = QHBoxLayout()
        self.f_message = QLabel(objectName="discret", wordWrap=True)
        actions.addWidget(self.f_message, 1)
        self.f_supprimer = QPushButton("Supprimer")
        self.f_supprimer.clicked.connect(self.supprimer_fonction)
        actions.addWidget(self.f_supprimer)
        bouton = QPushButton("Annuler")
        bouton.clicked.connect(lambda: self.ouvrir_fonction(
            self.fonction_ouverte))
        actions.addWidget(bouton)
        bouton = QPushButton("Enregistrer", objectName="principal")
        bouton.clicked.connect(self.enregistrer_fonction)
        actions.addWidget(bouton)
        colonne.addLayout(actions)
        ligne.addWidget(editeur, 1)
        self.minuterie_f = QTimer(self, singleShot=True, interval=400)
        self.minuterie_f.timeout.connect(self.verifier_fonction)
        for signal in (self.f_corps.textChanged, self.f_nom.textChanged,
                       self.f_arguments.textChanged):
            signal.connect(self.minuterie_f.start)
        self.fonction_ouverte = None
        return page

    def remplir_page_fonctions(self):
        liste = self.liste_fonctions
        liste.blockSignals(True)
        liste.clear()
        choisi = None
        for nom, fiche in sorted(self.modele.fonctions.items()):
            element = QTreeWidgetItem([
                "%s(%s)" % (nom, ", ".join(fiche["arguments"])),
                "%d appel(s)" % len(self.modele.appels(nom))])
            element.setData(0, Qt.UserRole, nom)
            element.setToolTip(0, fiche.get("description", ""))
            element.setForeground(1, QColor(GRIS))
            liste.addTopLevelItem(element)
            if nom == self.fonction_ouverte:
                choisi = element
        if choisi:
            liste.setCurrentItem(choisi)
        liste.blockSignals(False)
        self.ouvrir_fonction(self.fonction_ouverte if self.fonction_ouverte
                             in self.modele.fonctions else None)

    def nouvelle_fonction(self):
        self.liste_fonctions.clearSelection()
        self.ouvrir_fonction(None)
        self.f_nom.setFocus()

    def ouvrir_fonction(self, nom):
        fiche = self.modele.fonctions.get(nom) if nom else None
        self.fonction_ouverte = nom
        self.f_titre.setText(nom or tr("Nouvelle fonction"))
        for champ in (self.f_nom, self.f_arguments, self.f_corps):
            champ.blockSignals(True)
        self.f_nom.setText(nom or "")
        self.f_arguments.setText(", ".join(fiche["arguments"])
                                 if fiche else "")
        self.f_description.setText(fiche.get("description", "")
                                   if fiche else "")
        self.f_corps.setPlainText(fiche["corps"] if fiche else
                                  "résultat = ")
        self.f_corps.surligneur.rehighlight()
        for champ in (self.f_nom, self.f_arguments, self.f_corps):
            champ.blockSignals(False)
        appels = self.modele.appels(nom) if nom else []
        self.f_appels.setText(
            "Utilisée par : " + ", ".join(
                '<a href="%s" style="color:%s">%s</a>' % (i, VERT, i)
                for i in appels if i in self.modele.parametres)
            + "".join(", " + i for i in appels
                      if i not in self.modele.parametres)
            if appels else "Pas encore utilisée.")
        self.f_supprimer.setVisible(fiche is not None)
        self.f_essai.setText("%s(%s)" % (nom, ", ".join(fiche["arguments"]))
                             if fiche else "")
        self.f_resultat_essai.setText("")
        self.f_message.setText("")
        self.verifier_fonction()

    def verifier_fonction(self):
        """Contrôle la fonction sur une copie du modèle."""
        if not self.f_nom.text().strip():
            self.f_controle.setText('<span style="color:#D9822B">● '
                                    'Saisissez un nom.</span>')
            return
        copie = copy.deepcopy(self.modele)
        try:
            copie.definir_fonction(self.f_nom.text(), self.f_arguments.text(),
                                   self.f_corps.toPlainText(),
                                   self.f_description.text(),
                                   self.fonction_ouverte)
            self.f_controle.setText('<span style="color:#2E8B57">✓ Fonction '
                                    'valide.</span>')
        except ErreurModele as erreur:
            self.f_controle.setText('<span style="color:#C0392B">✗ %s</span>'
                                    % erreur)
        finally:
            self.modele.activer_fonctions()   # le registre reste celui du modèle

    def essayer_fonction(self):
        copie = copy.deepcopy(self.modele)
        try:
            copie.definir_fonction(self.f_nom.text(), self.f_arguments.text(),
                                   self.f_corps.toPlainText(),
                                   self.f_description.text(),
                                   self.fonction_ouverte)
            valeur = tester_appel(copie, self.f_essai.text())
            self.f_resultat_essai.setText("= " + nombre_court(valeur))
            self.f_message.setText("")
        except Exception as erreur:
            self.f_resultat_essai.setText("")
            self.f_message.setText('<span style="color:#C0392B">Essai : '
                                   '%s</span>' % erreur)
        finally:
            self.modele.activer_fonctions()

    def enregistrer_fonction(self):
        try:
            self.modele.definir_fonction(
                self.f_nom.text(), self.f_arguments.text(),
                self.f_corps.toPlainText(), self.f_description.text(),
                self.fonction_ouverte)
        except ErreurModele as erreur:
            self.f_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
            return
        self.fonction_ouverte, self.resultat = self.f_nom.text().strip(), None
        self.remplir_page_fonctions()
        self.rafraichir()
        self.f_message.setText("Enregistrée dans le modèle.")

    def supprimer_fonction(self):
        try:
            self.modele.supprimer_fonction(self.fonction_ouverte)
        except ErreurModele as erreur:
            self.f_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
            return
        self.fonction_ouverte, self.resultat = None, None
        self.remplir_page_fonctions()
        self.rafraichir()
        self.f_message.setText("Fonction supprimée.")

    def ajouter_bibliotheque(self):
        try:
            ajoutees = self.modele.ajouter_bibliotheque()
        except ErreurModele as erreur:
            self.f_message.setText('<span style="color:#C0392B">%s</span>'
                                   % erreur)
            return
        self.remplir_page_fonctions()
        self.rafraichir()
        self.f_message.setText(
            "Ajoutées : %s." % ", ".join(ajoutees) if ajoutees else
            "La bibliothèque est déjà complète dans ce modèle.")

    # --------------------------- Édition du schéma ---------------------------
    def creer_editeurs(self):
        """Fiches modifiables : structure (page 1) et flux (page 2)."""
        # Structure.
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(8)
        self.e_genre = QLabel("STRUCTURE", objectName="discret")
        colonne.addWidget(self.e_genre)
        self.e_titre = _Qt.QLabel(objectName="titreFiche", wordWrap=True)
        colonne.addWidget(self.e_titre)
        grille = QGridLayout()
        grille.addWidget(QLabel("Nom"), 0, 0)
        self.e_nom = QLineEdit()
        grille.addWidget(self.e_nom, 0, 1)
        grille.addWidget(QLabel("Type"), 1, 0)
        self.e_type = QComboBox()
        self.e_type.addItems(TYPES_STRUCTURE)
        grille.addWidget(self.e_type, 1, 1)
        colonne.addLayout(grille)
        colonne.addWidget(QLabel("Missions (une par ligne)",
                                 objectName="discret"))
        self.e_missions = QPlainTextEdit()
        self.e_missions.setFixedHeight(64)
        colonne.addWidget(self.e_missions)
        self.e_flux = Section("Flux")
        self.e_flux_liste = QLabel(wordWrap=True)
        self.e_flux_liste.linkActivated.connect(self.ouvrir_lien_schema)
        self.e_flux.ajouter(self.e_flux_liste)
        colonne.addWidget(self.e_flux)
        # Charges et postes : liste + petite ligne d'ajout.
        self.e_charges = Section("Charges")
        self.e_charges_liste = QLabel(wordWrap=True)
        self.e_charges_liste.linkActivated.connect(self.ouvrir_lien_schema)
        self.e_charges.ajouter(self.e_charges_liste)
        ligne = QHBoxLayout()
        self.e_charge_nom = QLineEdit(placeholderText="nouvelle charge")
        ligne.addWidget(self.e_charge_nom, 1)
        self.e_charge_compte = QComboBox()
        self.e_charge_compte.addItems(COMPTES_FLUX)
        ligne.addWidget(self.e_charge_compte)
        bouton = QPushButton("+")
        bouton.setFixedWidth(40)
        bouton.clicked.connect(self.ajouter_charge)
        ligne.addWidget(bouton)
        self.e_charges.ajouter(ligne)
        colonne.addWidget(self.e_charges)
        self.e_postes = Section("Postes (bilan)")
        self.e_postes_liste = QLabel(wordWrap=True)
        self.e_postes_liste.linkActivated.connect(self.ouvrir_lien_schema)
        self.e_postes.ajouter(self.e_postes_liste)
        ligne = QHBoxLayout()
        self.e_poste_nom = QLineEdit(placeholderText="nouveau poste")
        ligne.addWidget(self.e_poste_nom, 1)
        self.e_poste_categorie = QComboBox()
        self.e_poste_categorie.addItems(CATEGORIES_POSTES)
        ligne.addWidget(self.e_poste_categorie)
        bouton = QPushButton("+")
        bouton.setFixedWidth(40)
        bouton.clicked.connect(self.ajouter_poste)
        ligne.addWidget(bouton)
        self.e_postes.ajouter(ligne)
        colonne.addWidget(self.e_postes)
        self.e_capacite = Section("Capacité d'investissement")
        grille = QGridLayout()
        self.e_cap = {}
        for rang, (cle, libelle) in enumerate((
                ("tresorerie_minimale", "Trésorerie minimale"),
                ("couverture", "Couverture de la dette"),
                ("taux", "Taux d'emprunt"), ("duree", "Durée (ans)"),
                ("besoin", "Besoin d'investissement"))):
            grille.addWidget(QLabel(libelle), rang, 0)
            self.e_cap[cle] = QLineEdit()
            grille.addWidget(self.e_cap[cle], rang, 1)
        self.e_capacite.ajouter(grille)
        self.e_capacite.ajouter(QLabel(
            "Laisser vide pour ne pas calculer la capacité de cette "
            "structure.", objectName="discret", wordWrap=True))
        colonne.addWidget(self.e_capacite)
        colonne.addStretch(1)
        self.e_message = QLabel(objectName="discret", wordWrap=True)
        self.e_message.linkActivated.connect(self.ouvrir_lien_schema)
        colonne.addWidget(self.e_message)
        colonne.addLayout(self.boutons_fiche(
            self.supprimer_structure, lambda: self.ouvrir_structure(
                self.structure_choisie), self.enregistrer_structure))
        self.pile_fiche.addWidget(page)
        # Flux.
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(8)
        self.x_genre = QLabel(objectName="discret")
        colonne.addWidget(self.x_genre)
        self.x_titre = _Qt.QLabel(objectName="titreFiche", wordWrap=True)
        colonne.addWidget(self.x_titre)
        grille = QGridLayout()
        self.x_nom = QLineEdit()
        self.x_payeur = _Qt.QComboBox()   # noms = données
        self.x_beneficiaire = _Qt.QComboBox()   # noms = données
        self.x_compte = QComboBox()
        self.x_compte.addItems(COMPTES_FLUX)
        self.x_effet = QComboBox()
        self.x_effet.addItems(EFFETS_FLUX)
        self.x_financier = QRadioButton("Financier")
        self.x_physique = QRadioButton("Physique")
        natures = QHBoxLayout()
        natures.addWidget(self.x_financier)
        natures.addWidget(self.x_physique)
        natures.addStretch(1)
        self.x_financier.toggled.connect(self.afficher_nature)
        self.x_etiquette_compte = QLabel("Compte")
        self.x_etiquette_effet = QLabel("Effet")
        for rang, (libelle, champ) in enumerate((
                ("Nom", self.x_nom), ("Payeur", self.x_payeur),
                ("Bénéficiaire", self.x_beneficiaire))):
            grille.addWidget(QLabel(libelle), rang, 0)
            grille.addWidget(champ, rang, 1)
        grille.addWidget(QLabel("Nature"), 3, 0)
        grille.addLayout(natures, 3, 1)
        grille.addWidget(self.x_etiquette_compte, 4, 0)
        grille.addWidget(self.x_compte, 4, 1)
        grille.addWidget(self.x_etiquette_effet, 5, 0)
        grille.addWidget(self.x_effet, 5, 1)
        colonne.addLayout(grille)
        colonne.addWidget(QLabel("Formule (payée par le payeur, reçue par "
                                 "le bénéficiaire)", objectName="discret",
                                 wordWrap=True))
        self.x_formule = self.editeur_code(90)
        self.x_formule.setMaximumHeight(150)
        self.minuterie_x = QTimer(self, singleShot=True, interval=300)
        self.minuterie_x.timeout.connect(self.verifier_flux)
        self.x_formule.textChanged.connect(self.minuterie_x.start)
        self.x_beneficiaire.currentIndexChanged.connect(
            self.minuterie_x.start)
        colonne.addWidget(self.x_formule)
        self.x_controle = QLabel(wordWrap=True)
        colonne.addWidget(self.x_controle)
        self.x_paiement = Section("Paiement")
        grille = QGridLayout()
        self.x_reglages = {}
        for rang, (cle, libelle) in enumerate((
                ("recouvrement", "Recouvrement (part payée)"),
                ("rattrapage", "Rattrapage des impayés"),
                ("abandon", "Abandon des impayés"),
                ("taux_moratoire", "Intérêt du moratoire"),
                ("moratoire_debut", "Moratoire du (JJ/MM/AAAA)"),
                ("moratoire_fin", "au (JJ/MM/AAAA)"),
                ("part_suspendue", "Part suspendue"),
                ("reprise_pas", "Reprise en (pas)"))):
            grille.addWidget(QLabel(libelle), rang, 0)
            self.x_reglages[cle] = QLineEdit()
            grille.addWidget(self.x_reglages[cle], rang, 1)
        self.x_paiement.ajouter(grille)
        colonne.addWidget(self.x_paiement)
        colonne.addStretch(1)
        self.x_message = QLabel(objectName="discret", wordWrap=True)
        colonne.addWidget(self.x_message)
        colonne.addLayout(self.boutons_fiche(
            self.supprimer_flux, lambda: self.ouvrir_flux(self.selection),
            self.enregistrer_flux))
        self.pile_fiche.addWidget(page)

    def boutons_fiche(self, supprimer, annuler, enregistrer):
        ligne = QHBoxLayout()
        for texte, action, nom in (("Supprimer", supprimer, "danger"),
                                   ("Annuler", annuler, ""),
                                   ("Enregistrer", enregistrer, "principal")):
            bouton = QPushButton(texte, objectName=nom)
            bouton.clicked.connect(action)
            ligne.addWidget(bouton)
        return ligne

    def ouvrir_lien_schema(self, lien):
        genre, identifiant = lien.split("|", 1)
        if genre == "flux":
            self.ouvrir_flux(identifiant)
        elif genre == "parametre":
            self.ouvrir_tarif(identifiant)
        elif genre == "retirer":
            self.retirer_charge_poste(identifiant)

    def modifier_copie(self, action):
        """Applique action(copie) ; le modèle n'est remplacé qu'en cas de
        succès, donc une erreur ne laisse rien à moitié enregistré."""
        copie = copy.deepcopy(self.modele)
        try:
            retour = action(copie)
            copie.synchroniser()
        except ErreurModele as erreur:
            self.modele.activer_fonctions()
            return False, str(erreur)
        self.modele = copie
        self.modele.activer_fonctions()
        self.resultat = None
        return True, retour

    # Structure
    def ouvrir_structure(self, identifiant):
        m = self.modele
        if identifiant not in m.structures:
            return
        s = m.structures[identifiant]
        self.selection, self.structure_choisie = None, identifiant
        self.pile_fiche.setCurrentIndex(1)
        self.e_titre.setText(s["nom"])
        self.e_nom.setText(s["nom"])
        self.e_type.setCurrentText(s["type"])
        self.e_missions.setPlainText("\n".join(s.get("missions", [])))
        lignes = []
        for i, f in m.flux.items():
            if identifiant in (f["payeur"], f["beneficiaire"]):
                sens = "← %s" % m.structures[f["payeur"]]["nom"] \
                    if f["beneficiaire"] == identifiant else \
                    "→ %s" % m.structures[f["beneficiaire"]]["nom"]
                lignes.append('<a href="flux|%s" style="color:%s">%s</a> %s'
                              % (i, VERT, f["nom"], sens))
        self.e_flux.titre("Flux · %d" % len(lignes))
        self.e_flux_liste.setText("<br>".join(lignes) or "Aucun flux.")
        for section, liste, elements, detail in (
                (self.e_charges, self.e_charges_liste, m.charges, "compte"),
                (self.e_postes, self.e_postes_liste, m.postes, "categorie")):
            propres = sorted(i for i, c in elements.items()
                             if c["structure"] == identifiant)
            section.titre("%s · %d" % (section.nom, len(propres)))
            liste.setText("<br>".join(
                '<a href="parametre|%s" style="color:%s">%s</a> '
                '<span style="color:%s">%s</span> &nbsp;'
                '<a href="retirer|%s" style="color:#C0392B">retirer</a>'
                % (i, VERT, elements[i]["nom"], GRIS, elements[i][detail], i)
                for i in propres) or "Aucun.")
        capacite = s.get("capacite", {})
        for cle, champ in self.e_cap.items():
            champ.setText(capacite.get(cle, ""))
        self.e_capacite.deplier(bool(capacite))
        self.e_message.setText("")
        self.tracer_flux()

    def enregistrer_structure(self):
        ancien = self.structure_choisie

        def action(m):
            nouveau = m.ajouter_structure(self.e_nom.text(),
                                          self.e_type.currentText(), ancien)
            m.definir_missions(nouveau, self.e_missions.toPlainText())
            m.definir_capacite(nouveau, {k: c.text()
                                         for k, c in self.e_cap.items()})
            return nouveau

        reussi, retour = self.modifier_copie(action)
        if not reussi:
            self.e_message.setText('<span style="color:#C0392B">%s</span>'
                                   % retour)
            return
        self.rafraichir()
        self.ouvrir_structure(retour)
        self.e_message.setText("Enregistré." + (
            " Les formules suivent le nouveau nom." if retour != ancien
            else ""))

    def supprimer_structure(self):
        i = self.structure_choisie
        if i not in self.modele.structures:
            return
        retires, a_revoir = self.modele.consequences_suppression(i)
        texte = "Supprimer « %s » ?" % self.modele.structures[i]["nom"]
        if retires:
            texte += "\n\nSupprimés avec elle :\n" + "\n".join(
                "• " + r for r in retires[:15]) + (
                "\n…" if len(retires) > 15 else "")
        if a_revoir:
            texte += "\n\nFormules à revoir ensuite :\n" + "\n".join(
                "• " + r for r in a_revoir[:10])
        if QMessageBox.question(self, TITRE_APPLICATION, texte) != \
                QMessageBox.Yes:
            return
        self.modifier_copie(lambda m: m.supprimer_structure(i))
        self.structure_choisie = None
        self.pile_fiche.setCurrentIndex(0)
        self.vider_fiche()
        self.rafraichir()

    def ajouter_charge(self):
        s, nom = self.structure_choisie, self.e_charge_nom.text()
        reussi, retour = self.modifier_copie(lambda m: m.ajouter_charge(
            nom, s, "0", self.e_charge_compte.currentText()))
        self.apres_ajout(reussi, retour, self.e_charge_nom)

    def ajouter_poste(self):
        s, nom = self.structure_choisie, self.e_poste_nom.text()
        reussi, retour = self.modifier_copie(lambda m: m.ajouter_poste(
            nom, s, self.e_poste_categorie.currentText(), "0"))
        self.apres_ajout(reussi, retour, self.e_poste_nom)

    def apres_ajout(self, reussi, retour, champ):
        if not reussi:
            self.e_message.setText('<span style="color:#C0392B">%s</span>'
                                   % retour)
            return
        champ.clear()
        self.rafraichir()
        self.ouvrir_structure(self.structure_choisie)
        self.e_message.setText(
            'Créé avec la valeur 0. <a href="parametre|%s" style="color:%s">'
            'Écrire sa formule →</a>' % (retour, VERT))

    def retirer_charge_poste(self, identifiant):
        m = self.modele
        if QMessageBox.question(self, TITRE_APPLICATION, "Retirer %s ?"
                                % identifiant) != QMessageBox.Yes:
            return
        self.modifier_copie(lambda c: c.supprimer_charge(identifiant)
                            if identifiant in c.charges
                            else c.supprimer_poste(identifiant))
        self.rafraichir()
        self.ouvrir_structure(self.structure_choisie)

    # Flux
    def ouvrir_flux(self, identifiant):
        m = self.modele
        if identifiant not in m.flux:
            return
        f = m.flux[identifiant]
        self.selection, self.structure_choisie = identifiant, None
        self.pile_fiche.setCurrentIndex(2)
        self.x_titre.setText(f["nom"])
        self.x_nom.setText(f["nom"])
        for choix, valeur in ((self.x_payeur, f["payeur"]),
                              (self.x_beneficiaire, f["beneficiaire"])):
            choix.blockSignals(True)
            choix.clear()
            for i, s in m.structures.items():
                choix.addItem(s["nom"], i)
            choix.setCurrentIndex(max(choix.findData(valeur), 0))
            choix.blockSignals(False)
        (self.x_financier if f["nature"] == "Financier"
         else self.x_physique).setChecked(True)
        self.x_compte.setCurrentText(f.get("compte", "Résultat"))
        self.x_effet.setCurrentText(f.get("effet", "Capacité"))
        self.x_formule.blockSignals(True)
        self.x_formule.setPlainText(m.parametres[identifiant]["expression"])
        self.x_formule.surligneur.rehighlight()
        self.x_formule.blockSignals(False)
        reglages = f.get("paiement") or PAIEMENT_DEFAUT
        for cle, champ in self.x_reglages.items():
            champ.setText(reglages.get(cle, ""))
        self.x_paiement.deplier("paiement" in f)
        self.afficher_nature()
        self.x_message.setText("")
        self.verifier_flux()
        self.tracer_flux()

    def afficher_nature(self, *_args):
        financier = self.x_financier.isChecked()
        self.x_genre.setText("FLUX FINANCIER" if financier
                             else "FLUX PHYSIQUE OU SERVICE")
        for element in (self.x_etiquette_compte, self.x_compte,
                        self.x_paiement):
            element.setVisible(financier)
        for element in (self.x_etiquette_effet, self.x_effet):
            element.setVisible(not financier)

    def verifier_flux(self):
        texte = self.x_formule.toPlainText()
        if not texte.strip():
            self.x_controle.setText('<span style="color:#D9822B">● Formule '
                                    'à saisir.</span>')
            return
        try:
            self.modele.controler_calcul(texte,
                                         self.x_beneficiaire.currentData())
            self.x_controle.setText('<span style="color:#2E8B57">✓ Formule '
                                    'valide.</span>')
        except ErreurModele as erreur:
            self.x_controle.setText('<span style="color:#C0392B">✗ %s</span>'
                                    % erreur)

    def enregistrer_flux(self):
        ancien = self.selection
        financier = self.x_financier.isChecked()

        def action(m):
            nouveau = m.ajouter_flux(
                self.x_nom.text(), self.x_payeur.currentData(),
                self.x_beneficiaire.currentData(),
                self.x_formule.toPlainText(), ancien,
                "Financier" if financier else "Physique",
                self.x_effet.currentText(), self.x_compte.currentText())
            if financier:
                m.definir_paiement(nouveau, {k: c.text() for k, c in
                                             self.x_reglages.items()})
            else:
                m.flux[nouveau].pop("paiement", None)
            return nouveau

        reussi, retour = self.modifier_copie(action)
        if not reussi:
            self.x_message.setText('<span style="color:#C0392B">%s</span>'
                                   % retour)
            return
        self.rafraichir()
        self.ouvrir_flux(retour)
        self.x_message.setText("Enregistré." + (
            " Les formules suivent le nouveau nom." if ancien and
            retour != ancien else ""))

    def supprimer_flux(self):
        i = self.selection
        if i not in self.modele.flux:
            return
        utilisateurs = sorted(p for p in self.modele.parametres
                              if i in self.modele.references(p))
        texte = "Supprimer le flux « %s » ?" % self.modele.flux[i]["nom"]
        if utilisateurs:
            texte += "\n\nFormules qui l'utilisent, à revoir ensuite :\n" + \
                "\n".join("• " + p for p in utilisateurs[:10])
        if QMessageBox.question(self, TITRE_APPLICATION, texte) != \
                QMessageBox.Yes:
            return
        self.modifier_copie(lambda m: m.supprimer_flux(i))
        self.selection = None
        self.pile_fiche.setCurrentIndex(0)
        self.vider_fiche()
        self.rafraichir()

    def vider_fiche(self):
        self.fiche_type.setText("")
        self.fiche_nom.setText("Cliquez sur une structure ou un flux")
        self.fiche_detail.setText("pour voir et modifier sa fiche.")
        self.resume.setText("")
        self.controle.setText("")
        for element in (self.etiquette_formule, self.formule,
                        self.appliquer):
            element.hide()

    # Outils du schéma
    @staticmethod
    def place_libre(x0, y0, autres, segments=()):
        """Emplacement le plus proche de (x0, y0) où un nouveau bloc ne
        chevauche ni une structure existante ni une flèche de flux
        (recherche en anneaux)."""
        pas_x, pas_y = LARGEUR_BLOC + 40, HAUTEUR_BLOC + 40

        def coupe(x, y, segment):
            # Le segment passe-t-il dans le bloc (élargi de 30 px) ?
            (ax, ay), (bx, by) = segment
            gauche, droite = x - LARGEUR_BLOC / 2 - 30, x + LARGEUR_BLOC / 2 + 30
            haut, bas = y - HAUTEUR_BLOC / 2 - 30, y + HAUTEUR_BLOC / 2 + 30
            t0, t1, dx, dy = 0.0, 1.0, bx - ax, by - ay
            for p, q in ((-dx, ax - gauche), (dx, droite - ax),
                         (-dy, ay - haut), (dy, bas - ay)):
                if abs(p) < 1e-12:
                    if q < 0:
                        return False
                    continue
                t = q / p
                if p < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
                if t0 > t1:
                    return False
            return True

        def libre(x, y):
            return all(abs(x - a) >= pas_x or abs(y - b) >= pas_y
                       for a, b in autres) and \
                not any(coupe(x, y, sg) for sg in segments)

        for anneau in range(0, 30):
            cases = [(i, j) for i in range(-anneau, anneau + 1)
                     for j in range(-anneau, anneau + 1)
                     if max(abs(i), abs(j)) == anneau]
            cases.sort(key=lambda c: (abs(c[1]), abs(c[0]), -c[0], -c[1]))
            for i, j in cases:
                x, y = x0 + i * pas_x, y0 + j * pas_y
                if libre(x, y):
                    return x, y
        return x0, y0 + pas_y * 30

    def nouvelle_structure(self):
        def action(m):
            rang, nom = 1, "Nouvelle structure"
            while creer_id(nom) in m.structures:
                rang += 1
                nom = "Nouvelle structure %d" % rang
            autres = [(f.get("x", 0), f.get("y", 0))
                      for f in m.structures.values()]
            segments = [((m.structures[f["payeur"]].get("x", 0),
                          m.structures[f["payeur"]].get("y", 0)),
                         (m.structures[f["beneficiaire"]].get("x", 0),
                          m.structures[f["beneficiaire"]].get("y", 0)))
                        for f in m.flux.values()
                        if f["payeur"] in m.structures
                        and f["beneficiaire"] in m.structures]
            i = m.ajouter_structure(nom, "Autorité")
            centre = self.schema.mapToScene(
                self.schema.viewport().rect().center())
            depart = autres[0] if autres else (centre.x(), centre.y())
            x, y = self.place_libre(depart[0], depart[1], autres, segments)
            m.structures[i]["x"], m.structures[i]["y"] = int(x), int(y)
            return i

        reussi, retour = self.modifier_copie(action)
        if reussi:
            self.rafraichir()
            self.ouvrir_structure(retour)
            self.e_nom.setFocus()
            self.e_nom.selectAll()

    def commencer_flux(self):
        if len(self.modele.structures) < 2:
            self.sous_titre.setText("Il faut au moins deux structures.")
            return
        self.flux_en_cours = []
        self.sous_titre.setText(
            "Nouveau flux : cliquez sur le payeur, puis sur le bénéficiaire "
            "(Échap pour annuler).")
        self.schema.setFocus()

    def cliquer_structure(self, identifiant):
        if self.flux_en_cours is None:
            self.ouvrir_structure(identifiant)
            return
        self.flux_en_cours.append(identifiant)
        if len(self.flux_en_cours) == 1:
            self.sous_titre.setText(
                "Payeur : %s. Cliquez maintenant sur le bénéficiaire."
                % self.modele.structures[identifiant]["nom"])
            return
        payeur, beneficiaire = self.flux_en_cours
        self.flux_en_cours = None
        if payeur == beneficiaire:
            self.sous_titre.setText("Le payeur et le bénéficiaire doivent "
                                    "différer. Recommencez avec + Flux.")
            return

        def action(m):
            rang, nom = 1, "nouveau_flux"
            while composer_id(nom, beneficiaire) in m.parametres:
                rang += 1
                nom = "nouveau_flux_%d" % rang
            return m.ajouter_flux(nom, payeur, beneficiaire, "0")

        reussi, retour = self.modifier_copie(action)
        if reussi:
            self.rafraichir()
            self.ouvrir_flux(retour)
            self.x_nom.setFocus()
            self.x_nom.selectAll()
            self.x_message.setText("Flux créé avec la formule 0 : donnez-lui "
                                   "un nom et sa formule, puis Enregistrer.")

    def annuler_outil(self):
        if self.flux_en_cours is not None:
            self.flux_en_cours = None
            self.rafraichir()

    def charge_ou_poste(self, champ):
        if not self.structure_choisie:
            self.sous_titre.setText("Cliquez d'abord sur la structure qui "
                                    "porte la charge ou le poste.")
            return
        section = self.e_charges if champ is self.e_charge_nom \
            else self.e_postes
        section.deplier(True)
        champ.setFocus()

    def supprimer_selection(self):
        if self.selection:
            self.supprimer_flux()
        elif self.structure_choisie:
            self.supprimer_structure()

    # ------------------------------ Affichage ------------------------------
    def choisir(self, rang):
        self.boutons_etapes[rang].setChecked(True)
        # L'écran Paramètres a son propre éditeur : la fiche s'efface.
        self.panneau_fiche.setVisible(rang in (0, 1, 2))
        if rang == 6:
            self.pages.setCurrentIndex(PAGE_POST)
            self.remplir_page_post()
            return
        if rang == 8:
            self.pages.setCurrentIndex(PAGE_FONCTIONS)
            self.remplir_page_fonctions()
            return
        if rang == 7:
            self.pages.setCurrentIndex(PAGE_RESULTATS)
            self.preparer_resultats()
            return
        if rang == 5:
            self.pages.setCurrentIndex(PAGE_SIMULATION)
            self.remplir_simulation()
            return
        if rang == 4:
            self.pages.setCurrentIndex(PAGE_INITIAL)
            self.remplir_initial()
            return
        if rang == 3:
            self.pages.setCurrentIndex(PAGE_PARAMETRES)
            self.remplir_liste_parametres()
            if self.parametre_ouvert not in self.modele.parametres:
                self.ouvrir_parametre(None)
            return
        if rang in (0, 2):
            self.pages.setCurrentIndex(PAGE_SCHEMA)
            return
        if rang == 1:
            self.pages.setCurrentIndex(PAGE_PERIMETRES)
            self.ouvrir_perimetre(self.perimetre_choisi())
            return
        self.page_attente.setText(
            "%s : écran à migrer. En attendant, utilisez ppp_prototype.py."
            % ETAPES[rang])
        self.pages.setCurrentIndex(PAGE_ATTENTE)

    def rafraichir(self):
        m = self.modele
        self.nom_projet.setText((os.path.basename(self.chemin)
                                 or tr("Nouveau projet"))
                                + ("  •" if self.modifie() else ""))
        self.nom_projet.setToolTip("Modifications non enregistrées"
                                   if self.modifie() else "")
        manquants = sum(not p["valeur_initiale"]
                        for p in m.parametres.values())
        etats = (len(m.structures),
                 len(m.perimetres) if m.perimetres else "Global",
                 len(m.flux), len(m.parametres),
                 "Complet" if not manquants else "%d à saisir" % manquants,
                 T(self.resultat["statut"]).capitalize() if self.resultat
                 else "À lancer", len(m.post),
                 "Ouvrir" if self.resultat else "—", len(m.fonctions))
        for bouton, etat in zip(self.boutons_etapes, etats):
            bouton.etat.setText(str(etat))
        periodes = self.resultat["periodes"] if self.resultat else []
        self.sous_titre.setText(
            "Montants cumulés de %d à %d, après simulation."
            % (periodes[0]["debut"].year, periodes[-1]["debut"].year)
            if periodes else "Lancez la simulation pour voir les montants.")
        self.dessiner_schema()

    def recharger(self):
        """Après ouverture d'un fichier : tout l'écran suit le modèle."""
        self.charger_perimetres()
        self.ouvrir_parametre(None)
        self.remplir_liste_parametres()
        self.rafraichir()

    def dessiner_schema(self):
        scene = self.schema.scene()
        scene.clear()
        self.dessins_flux = []
        for rang, fiche in enumerate(self.modele.structures.values()):
            if fiche["x"] is None or fiche["y"] is None:
                fiche["x"] = 170 + 300 * (rang % 3)
                fiche["y"] = 120 + 200 * (rang // 3)
        for i, fiche in self.modele.structures.items():
            scene.addItem(Bloc(self, i, fiche))
        self.tracer_flux()

    def planifier_flux(self):
        """Redessine les flèches au prochain passage de la boucle Qt (une
        seule fois, même si plusieurs blocs bougent)."""
        if not getattr(self, "flux_planifie", False):
            self.flux_planifie = True
            QTimer.singleShot(0, lambda: self.tracer_flux(recadrer=False))

    def tracer_flux(self, recadrer=True):
        self.flux_planifie = False
        scene = self.schema.scene()
        for element in self.dessins_flux:
            scene.removeItem(element)
        self.dessins_flux = []
        paires = {}
        for i, f in self.modele.flux.items():
            cle = tuple(sorted((f["payeur"], f["beneficiaire"])))
            paires.setdefault(cle, []).append(i)
        for flux in paires.values():
            for rang, i in enumerate(flux):
                self.tracer_un_flux(i, (rang - (len(flux) - 1) / 2) * 64)
        if recadrer:
            marge = 40
            scene.setSceneRect(scene.itemsBoundingRect().adjusted(
                -marge, -marge, marge, marge))

    def deplacer_etiquette(self, identifiant, cle, decalage):
        """Garde dans le modèle le décalage d'une étiquette déplacée."""
        fiche = self.modele.flux.get(identifiant)
        if fiche is None:
            return
        if decalage is None or decalage == (0, 0):
            fiche.pop(cle, None)
        else:
            fiche[cle] = list(decalage)
        self.maj_titre()
        # Redessin après l'événement souris : l'étiquette ne peut pas être
        # détruite pendant qu'elle le traite.
        QTimer.singleShot(0, self.tracer_flux if cle == "etiquette"
                          else self.afficher_flux)

    def maj_titre(self):
        self.nom_projet.setText((os.path.basename(self.chemin)
                                 or tr("Nouveau projet"))
                                + ("  •" if self.modifie() else ""))
        self.nom_projet.setToolTip("Modifications non enregistrées"
                                   if self.modifie() else "")

    def tracer_un_flux(self, identifiant, decalage):
        m, f = self.modele, self.modele.flux[identifiant]
        a, b = m.structures[f["payeur"]], m.structures[f["beneficiaire"]]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        longueur = max(math.hypot(dx, dy), 1)
        ux, uy = dx / longueur, dy / longueur
        nx, ny = -uy, ux
        if f["payeur"] > f["beneficiaire"]:   # même côté pour les deux sens
            decalage = -decalage
        # La flèche, décalée, s'arrête au bord de chaque bloc.
        ox, oy = nx * decalage, ny * decalage

        def sortie(vx, vy):
            """Distance entre le point décalé et le bord du bloc."""
            distances = []
            if abs(vx) > 1e-9:
                distances.append(((LARGEUR_BLOC / 2) * math.copysign(1, vx)
                                  - ox) / vx)
            if abs(vy) > 1e-9:
                distances.append(((HAUTEUR_BLOC / 2) * math.copysign(1, vy)
                                  - oy) / vy)
            return max(min(distances), 0) + 5

        depart = QPointF(a["x"] + ox + ux * sortie(ux, uy),
                         a["y"] + oy + uy * sortie(ux, uy))
        arrivee = QPointF(b["x"] + ox - ux * sortie(-ux, -uy),
                          b["y"] + oy - uy * sortie(-ux, -uy))
        financier = f["nature"] == "Financier"
        choisi = identifiant == self.selection
        couleur = QColor(VERT if financier else GRIS)
        stylo = QPen(couleur, 3.5 if choisi else 2.5 if financier else 2)
        if not financier:
            stylo.setStyle(Qt.DashLine)
        chemin = QPainterPath(depart)
        chemin.lineTo(arrivee)
        trait = ClicFlux(self, identifiant, chemin)
        trait.setPen(stylo)
        pointe = QPolygonF([
            arrivee,
            arrivee - QPointF(ux * 11 + nx * 5, uy * 11 + ny * 5),
            arrivee - QPointF(ux * 11 - nx * 5, uy * 11 - ny * 5)])
        tete = QGraphicsPolygonItem(pointe)
        tete.setBrush(QBrush(couleur))
        tete.setPen(Qt.NoPen)
        texte = f["nom"]
        if self.resultat and identifiant in self.resultat["montants"]:
            texte += "\n%s FCFA" % millions(
                sum(self.resultat["montants"][identifiant]))
        etiquette = QGraphicsSimpleTextItem(texte)
        taille = etiquette.boundingRect()
        etiquette.setBrush(QColor(ENCRE))
        place = QPointF((depart.x() + arrivee.x()) / 2 - taille.width() / 2,
                        (depart.y() + arrivee.y()) / 2 - taille.height() / 2)
        fond = EtiquetteMobile(
            taille.adjusted(-6, -3, 6, 3), place,
            f.get("etiquette") or (0, 0),
            lambda decalage: self.deplacer_etiquette(identifiant, "etiquette",
                                                     decalage))
        fond.setPen(QPen(QColor(FILET)))
        fond.setBrush(QBrush(QColor("#FFFFFF")))
        fond.setZValue(3)
        etiquette.setParentItem(fond)
        scene = self.schema.scene()
        for element in (trait, tete, fond):
            scene.addItem(element)
        self.dessins_flux += [trait, tete, fond]

    # -------------------------------- Fiches --------------------------------
    def appliquer_formule(self):
        i, m = self.selection, self.modele
        if not i:
            return
        f = m.flux[i]
        try:
            m.ajouter_flux(f["nom"], f["payeur"], f["beneficiaire"],
                           self.formule.toPlainText(), i, f["nature"],
                           f["effet"], f["compte"])
            self.resultat = None
            self.controle.setText("Formule enregistrée. Relancez la simulation.")
            self.rafraichir()
        except ErreurModele as erreur:
            self.controle.setText(str(erreur))

    # ------------------------------- Actions --------------------------------
    def modifie(self):
        try:
            return self.modele.texte() != self.reference
        except Exception:
            return True

    def proteger(self, question):
        """Modèle modifié : propose de l'enregistrer. Faux si on annule."""
        if not self.modifie():
            return True
        reponse = QMessageBox.question(
            self, TITRE_APPLICATION, question,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reponse == QMessageBox.Cancel:
            return False
        if reponse == QMessageBox.Yes:
            self.enregistrer()
            return not self.modifie()
        return True

    def closeEvent(self, evenement):
        if self.forcer_fermeture or self.proteger(
                "Le modèle a été modifié. L'enregistrer avant de fermer ?"):
            evenement.accept()
        else:
            evenement.ignore()

    def nouveau(self):
        """Ctrl+N : projet vide ; le nom du fichier est demandé au premier
        enregistrement."""
        if not self.proteger("Le modèle a été modifié. L'enregistrer avant "
                             "de commencer un nouveau projet ?"):
            return
        self.modele = Modele()
        self.chemin, self.resultat, self.selection = "", None, None
        self.dernier_resultat = None
        self.etat_calcul.setText("")
        self.reference = self.modele.texte()
        self.recharger()
        self.choisir(0)

    def ouvrir(self):
        if not self.proteger("Le modèle a été modifié. L'enregistrer avant "
                             "d'en ouvrir un autre ?"):
            return
        chemin = QFileDialog.getOpenFileName(self, "Ouvrir", "",
                                             "Fichier dat (*.dat)")[0]
        if not chemin:
            return
        try:
            self.modele = Modele.lire(chemin)
        except (ErreurModele, IndexError, KeyError, ValueError,
                UnicodeDecodeError) as erreur:
            QMessageBox.warning(self, TITRE_APPLICATION, str(erreur))
            return
        self.chemin, self.resultat, self.selection = chemin, None, None
        self.etat_calcul.setText("")
        self.reference = self.modele.texte()
        self.recharger()

    def enregistrer(self):
        """Ctrl+S : enregistre dans le fichier ouvert."""
        if not self.chemin or not os.path.isdir(
                os.path.dirname(os.path.abspath(self.chemin))):
            self.enregistrer_sous()
            return
        self.modele.ecrire(self.chemin)
        self.reference = self.modele.texte()
        self.rafraichir()

    def enregistrer_sous(self):
        chemin = QFileDialog.getSaveFileName(self, "Enregistrer", self.chemin,
                                             "Fichier dat (*.dat)")[0]
        if chemin:
            self.chemin = chemin
            self.enregistrer()

    def changer_langue(self, rang):
        """Change de langue : l'écran est reconstruit, le modèle et le
        dernier calcul sont gardés tels quels."""
        code = ("fr", "en")[rang]
        if code == LANGUE["code"]:
            return
        definir_langue(code)
        nouvelle = Fenetre(self.modele, self.chemin)
        nouvelle.reference = self.reference
        nouvelle.resultat = self.resultat
        nouvelle.dernier_resultat = self.dernier_resultat
        nouvelle.setWindowTitle(tr(TITRE_APPLICATION))
        nouvelle.setGeometry(self.geometry())
        etape = next((r for r, b in enumerate(self.boutons_etapes)
                      if b.isChecked()), 0)
        nouvelle.show()
        nouvelle.rafraichir()
        nouvelle.choisir(etape)
        QApplication.instance().fenetre = nouvelle
        self.forcer_fermeture = True
        self.close()

    def lancer(self):
        if self.perimetres_modifies and not self.appliquer_perimetres():
            return
        erreurs = self.modele.verifier()[0]
        if erreurs:                  # la page Simulation détaille les erreurs
            self.choisir(5)
            self.s_message.setText(
                '<span style="color:#C0392B">Le modèle n\'est pas prêt : '
                'corrigez les erreurs ci-dessus.</span>')
            return
        fenetre = FenetreCalcul(self)
        fenetre.show()
        QApplication.processEvents()
        resultat = ppp_moteur.simuler_tarifs(self.modele, fenetre)
        ppp_moteur.ecrire_resultat(
            resultat, chemin_local(ppp_moteur.FICHIER_RESULTAT))
        if resultat["erreurs"]:
            self.resultat = None
            self.etat_calcul.setText("Échec")
        else:
            self.resultat = self.dernier_resultat = resultat
            self.etat_calcul.setText("Réussite")
        fenetre.terminer(resultat)
        self.rafraichir()
        if self.pages.currentIndex() == PAGE_RESULTATS:
            self.preparer_resultats()
        if fenetre.exec() == 2:
            self.choisir(7)


class ClicBlocResultat(QGraphicsRectItem):
    """Structure de l'onglet Flux des résultats : le clic ouvre ses chiffres
    année par année."""

    def __init__(self, fenetre, identifiant, rectangle):
        super().__init__(rectangle)
        self.fenetre, self.identifiant = fenetre, identifiant
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, evenement):
        # Le schéma est redessiné juste après : pas pendant le clic.
        self.fenetre.r_structure_vue = self.identifiant
        self.fenetre.r_fleche = None
        QTimer.singleShot(0, self.fenetre.afficher_flux)
        evenement.accept()


class ClicResultat(QGraphicsPathItem):
    """Flèche de l'onglet Flux des résultats : le clic montre sa courbe."""

    def __init__(self, fenetre, cle, chemin):
        super().__init__(chemin)
        self.fenetre, self.cle = fenetre, cle
        self.setCursor(Qt.PointingHandCursor)

    def shape(self):
        from PySide6.QtGui import QPainterPathStroker
        trace = QPainterPathStroker()
        trace.setWidth(18)
        return trace.createStroke(self.path())

    def mousePressEvent(self, evenement):
        self.fenetre.detail_fleche(self.cle)
        evenement.accept()


class ClicFlux(QGraphicsPathItem):
    """Trait d'un flux : le clic ouvre sa fiche."""

    def __init__(self, fenetre, identifiant, chemin):
        super().__init__(chemin)
        self.fenetre, self.identifiant = fenetre, identifiant
        self.setCursor(Qt.PointingHandCursor)

    def shape(self):
        zone = QPainterPath(self.path())
        from PySide6.QtGui import QPainterPathStroker
        trace = QPainterPathStroker()
        trace.setWidth(16)
        return trace.createStroke(zone)

    def mousePressEvent(self, _evenement):
        self.fenetre.ouvrir_flux(self.identifiant)


def lancer_interface():
    application = QApplication.instance() or QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    definir_langue(LANGUE_INTERFACE)
    preparer_dossier_utilisateur()
    chemin = chemin_local(FICHIER_DEPART)
    modele = Modele.lire(chemin) if os.path.exists(chemin) else Modele()
    fenetre = Fenetre(modele, chemin)
    fenetre.setWindowTitle(tr(TITRE_APPLICATION))
    application.fenetre = fenetre
    fenetre.show()
    application.exec()


if __name__ == "__main__":
    lancer_interface()
