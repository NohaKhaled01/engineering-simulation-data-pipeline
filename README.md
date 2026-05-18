# Engineering Simulation Data Pipeline

## Overview
A full ETL pipeline that extracts, transforms, and loads engineering simulation project data from multiple sources into a relational MySQL database.

Built to consolidate data from 400+ simulation projects across multiple teams into a single queryable database, replacing manual tracking across disconnected files and spreadsheets.

---

## Problem Statement
Simulation project data was scattered across three disconnected sources:
- **JSON project files** — containing geometry, mesh, material, and configuration data
- **Project management system** — containing project hierarchy, timelines, and statuses
- **Reference CSVs** — containing variant specifications and reference data

No single source of truth existed. Engineers had no way to query across projects or track simulation history.

---

## Solution Architecture
```
Data Sources:
    JSON project files        → components, materials, system configurations
    Project management CSV    → models, design phases, requests
    Reference CSVs            → model specifications

Pipeline:
    Extract   → Python (json, pandas, os, re)
    Transform → cleaning, fuzzy matching, deduplication, normalization
    Load      → MySQL (SQLAlchemy)
```

## Database Schema
8 related tables organized in a parent-child hierarchy:

| Table | Description | Parent |
|---|---|---|
| variant | Vehicle/product variants | — |
| sync | Design sync points per variant | variant |
| request | Individual simulation requests per sync | sync |
| exhausts | Exhaust system configurations | sync |
| exhausts_materials | Material assignments per exhaust segment | exhausts |
| exhausts_meshes | Mesh file tracking for change detection | exhausts |
| components | Simulation components per variant | variant |
| component_materials | Material assignments per component region | components |

---

## Key Technical Challenges Solved

**1. Inconsistent Naming Conventions**
Project names and reference data used completely different formats with no enforced standard. Solved using a two-step fuzzy matching approach — first filtering by category abbreviation, then applying token-based matching to find the best match.

**2. Duplicate Detection Across Import Runs**
Scripts are run multiple times by different team members. Solved using mesh file name comparison — extracting mesh filenames from each project's JSON and comparing against existing DB entries before importing.

**3. Multi-Source FK Relationships**
Data from different sources had no common unique identifier. Solved by building a mapping table using fuzzy matching, linking project names across sources to establish foreign key relationships.

**4. Sync Name Disambiguation**
Multiple design phases could share the same phase number with different regional qualifiers. Solved using a two-step matching logic — first matching on phase number, then using an additional qualifier field as a tiebreaker.

**5. Projects Predating the Project Management System**
Older projects had no corresponding entry in the project management system. Solved with a dedicated validation script that flags missing entries before any import runs, preventing projects from being linked to wrong parents.

---

## Scripts

| Script | Purpose |
|---|---|
| `check_variant_script.py` | Validates projects directory before import — flags missing variants |
| `Components_Script.py` | Extracts component names from JSON files |
| `Components_Materials_Script.py` | Extracts component material assignments from JSON files |
| `Exhaust_Importing_Script.py` | Extracts exhaust data with duplicate detection logic |
| `Matching_Components_2_Variants_Script.py` | Links components to their parent variants using fuzzy matching |
| `Getting_Column_Names.py` | Surveys gas data column names across all projects |

---

## Tech Stack
- **Language:** Python 3.x
- **Data manipulation:** pandas
- **Database ORM:** SQLAlchemy (mysql+pymysql)
- **Fuzzy matching:** thefuzz
- **Pattern matching:** re (Python regex)
- **JSON parsing:** json (built-in)
- **Database:** MySQL
- **Dev environment:** VS Code + Jupyter Notebooks
- **Version control:** Git / GitHub

---

## Project Status
Core pipeline complete — variants, syncs, requests, components, materials, and exhaust data are fully importable. Gas data and results import scripts are planned but not yet developed.
