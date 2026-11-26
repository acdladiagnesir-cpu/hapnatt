# HapNatt – Technical documentation

This document is for developers and technical reviewers. It explains how to install, run and build HapNatt, how the code is organised, and the format of model files. User-level documentation is in the [README](../README.md); the full reference of formulas and calculations is in [README_Formules.md](../README_Formules.md) (French).

## 1. Install and run

Requirements: Python 3.10 or later on Windows, macOS or Linux.

```
git clone https://github.com/acdladiagnesir-cpu/hapnatt
cd hapnatt
pip install -r requirements.txt
python ppp_interface.py
```

The application opens `Exemple_Simulation.dat`, a complete example with fictitious data. Settings (file opened at start-up, interface language, basemap) are constants at the top of `ppp_interface.py`; set `LANGUE_INTERFACE = "en"` for English. The script can also be run from IDLE with F5.

Windows users without Python can download `HapNatt-<version>-windows.zip` from the [Releases](https://github.com/acdladiagnesir-cpu/hapnatt/releases) page, unzip it and run `HapNatt.exe`. User files and examples are stored in `Documents/HapNatt`.

### Quick check

1. Run `python ppp_interface.py`.
2. Go to step 5 (Simulation) and press **F5** (or "Lancer la simulation").
3. Open step 7 (Results): flows on the diagram, summary, accounts, distribution of users' payments, curves and convergence checks are displayed.

## 2. Build the Windows executable

- Locally: run `construire_exe.py` (F5 in IDLE, or `python construire_exe.py`). PyInstaller is installed if missing; the result is in `dist/HapNatt/` and `dist/HapNatt-<version>-<os>.zip`.
- Automatically: the GitHub Actions workflow `.github/workflows/windows.yml` builds the executable on `windows-latest` whenever a release is published, and attaches the zip to the release. It can also be started manually from the Actions tab.

## 3. Code organisation

| File | Role |
|---|---|
| `ppp_prototype.py` | Data model (`Modele`): entities, flows, parameters, tables, perimeters. Reading and writing `.dat` files. Formula parser and compiler. Legacy Tkinter interface. |
| `ppp_moteur.py` | Simulation engine, tariff scenarios, result tables (summary, accounts, distribution, controls) and exports (CSV, tab-separated results, PDF). |
| `ppp_interface.py` | Graphical interface (PySide6), organised in nine steps: diagram, perimeters (with map), parameters, initial state, simulation, results, post-processing, functions, waiting list. |
| `ppp_langues.py` | French / English translations of the interface and of result labels. |
| `construire_exe.py` | Build script for the standalone executable. |

Dependencies flow in one direction: `ppp_interface` → `ppp_moteur` → `ppp_prototype`, with `ppp_langues` used by all three. The engine has no dependency on the interface and can be scripted:

```python
import ppp_prototype, ppp_moteur
modele = ppp_prototype.Modele.lire("Exemple_Simulation.dat")
resultat = ppp_moteur.simuler(modele)
print(ppp_moteur.synthese_resultat(resultat))
```

## 4. Modelling concepts

- **Entities** (`STRUCTURES`): authority, asset-holding company, operator, users, lenders, or any other type.
- **Flows** (`FLUX`): a financial flow (money) or a physical flow (service, volume, assets made available) from one entity to another. Each flow's amount per period is given by a formula.
- **Parameters**: values, formulas or tables attached to an entity, written `name[entity]` in formulas. Formulas use the variables `t`, the previous period (`[t-1]`), conditions (`si(...)`), tables and user-defined functions.
- **Perimeters**: the same model computed per service area (city, region, zone), each with its own values and map coordinates, plus a Global line.
- **Payments**: collection rate, recovery of arrears, write-offs and moratoria per financial flow, separating amounts due from amounts paid.
- **Tariff scenarios**: current tariffs, tariffs that keep the service running, and tariffs that finance investment, with caps on increases and fixed social tariffs.

## 5. Simulation engine

1. **Compilation.** Every formula is parsed with Python's `ast` module and checked against a whitelist of allowed nodes and functions; no arbitrary code can be executed. References are resolved to parameter identifiers.
2. **Dependency graph.** Parameters and flows form a directed graph. Strongly connected components (Tarjan's algorithm) identify loops, for example an incentive fee that depends on a result that depends on the fee.
3. **Time loop.** For each period, acyclic parts are evaluated in topological order. Loops are solved by successive substitution, accelerated by Newton steps when convergence is slow.
4. **Convergence check.** For each loop the engine estimates the contraction ratio ρ = e₂/e₁ from successive errors and the remaining distance e₂·ρ/(1−ρ), and reports any loop that has not converged in the Control tab.
5. **Accounts.** Payments are applied, then each entity's revenue, costs, investment, net result, cash and investment capacity are computed per period and per perimeter.

## 6. Model file format (`.dat`)

A model is a single UTF-8 text file. Lines starting with `#` are comments. The file is divided into sections in square brackets; each section starts with a header line, followed by one tab-separated row per item.

| Section | Content |
|---|---|
| `[SIMULATION]` | Key / value settings: start and end dates, time step, discount rate, iteration limit, tariff options. |
| `[FONCTIONS]` | User-defined functions: name, arguments, body, description. |
| `[REFERENCES]`, `[CONVERSIONS]` | Reference unit per dimension (time, volume, money...) and unit conversion factors. |
| `[STRUCTURES]` | Entities: id, name, type, x, y position on the diagram, missions. |
| `[FLUX]` | Flows: id, name, payer, beneficiary, nature (financial / physical), effect, account, label offsets. |
| `[CAPACITES]`, `[PAIEMENTS]` | Financing capacity settings; payment settings per financial flow. |
| `[CHARGES]`, `[POSTES]` | Costs and balance-sheet items of each entity. |
| `[PARAMETRES]` | Parameters: id, mode (value, formula, table), expression, unit, initial value, convergence tolerance, table settings. |
| `[PERIMETRES]`, `[VALEURS_PERIMETRE]`, `[TABLES_PERIMETRE]` | Perimeters and their specific values and tables. |
| `[TARIFS_OPTIMISABLES]`, `[POST_TRAITEMENT]`, `[TABLES]` | Tariffs open to optimisation, post-processing indicators, data tables. |

Files are human-readable and can be opened in any text editor or spreadsheet. Results can be exported as CSV and as a tab-separated results file.

## 7. Network use and privacy

The only network access is the download of basemap tiles (OpenStreetMap by default, cached in `cache_carte/`). No personal data is collected or transmitted; see [CONFIDENTIALITE.md](../CONFIDENTIALITE.md).

## 8. Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md). Before proposing a change, check that both examples still run in French and English.

---

Copyright © 2026 Aminata Collé Diagne. Licensed under GPL-3.0-or-later.
