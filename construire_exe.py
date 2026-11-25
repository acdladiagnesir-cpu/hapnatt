"""HapNatt - Construction de l'exécutable Windows.

Lancer dans IDLE avec F5 (sous Windows), ou : python construire_exe.py
Le résultat est dans dist/HapNatt/ (HapNatt.exe et ses fichiers) et dans
l'archive dist/HapNatt-<version>-windows.zip, prête à distribuer.

Copyright © 2026 A. C. Diagne.
Ce programme est un logiciel libre, distribué selon les termes de la GNU GPL
version 3 ou ultérieure (voir LICENSE).
SPDX-License-Identifier: GPL-3.0-or-later
"""

# --------------------------- Configuration ---------------------------------
VERSION = "1.0.0"           # remplacée par l'étiquette (v1.0.0) sur GitHub
NOM = "HapNatt"
SCRIPT_PRINCIPAL = "ppp_interface.py"
FICHIERS_JOINTS = ["Exemple_Simulation.dat", "Exemple_Perimetres.dat",
                   "README_Formules.md", "LICENSE"]
FENETRE_SEULE = True        # True : pas de console noire au lancement
# ---------------------------------------------------------------------------

import os
import shutil
import subprocess
import sys

DOSSIER = os.path.dirname(os.path.abspath(__file__))


def installer_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installation de PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "pyinstaller"])


def construire():
    global VERSION
    os.chdir(DOSSIER)
    etiquette = os.environ.get("GITHUB_REF_NAME", "")
    if etiquette.startswith("v"):
        VERSION = etiquette[1:]
    installer_pyinstaller()
    separateur = ";" if os.name == "nt" else ":"
    commande = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--name", NOM, "--collect-data", "xyzservices"]
    if FENETRE_SEULE:
        commande.append("--windowed")
    for fichier in FICHIERS_JOINTS:
        if os.path.exists(fichier):
            commande += ["--add-data", fichier + separateur + "."]
        else:
            print("Attention : fichier absent, ignoré :", fichier)
    commande.append(SCRIPT_PRINCIPAL)
    print("Construction en cours (quelques minutes)...")
    subprocess.check_call(commande)
    systeme = "windows" if os.name == "nt" else sys.platform
    archive = os.path.join("dist", "%s-%s-%s" % (NOM, VERSION, systeme))
    shutil.make_archive(archive, "zip", "dist", NOM)
    print("\nTerminé.")
    print("Programme :", os.path.join(DOSSIER, "dist", NOM))
    print("Archive à distribuer :", os.path.join(DOSSIER, archive + ".zip"))


if __name__ == "__main__":
    construire()
