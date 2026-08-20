# 🏗️ ECP 203 – Reinforced Concrete Engineering Dashboard

A comprehensive, interactive structural engineering dashboard built in **Python + Streamlit**
for the design of reinforced concrete elements according to the
**Egyptian Code of Practice (ECP 203-2018)**.

## Modules

| Module | Element | Key Checks |
|--------|---------|------------|
| 1 | Rectangular Columns | Slenderness, Axial capacity, Rebar layout, Stirrups |
| 2 | Isolated Footings   | PC thickness, RC thickness, Punching shear, One-way shear, Bottom steel mesh |
| 3 | Flat Slabs          | Min. thickness, Ultimate Wu, Direct Design Method moments, Column & Middle strip steel |

## Unit System
All inputs and outputs use the traditional engineering system:
`ton · kg · cm · m · kg/cm²`  — no Newton (N) or MPa.

---

## Installation & Usage

### Step 1 – Install Python (if not installed)
Download from https://www.python.org/downloads/  
✅ Check **"Add Python to PATH"** during installation.

### Step 2 – Install dependencies
Open a terminal in this folder and run:
```
pip install streamlit pandas
```

### Step 3 – Launch the dashboard
```
streamlit run app.py
```
The browser will open automatically at `http://localhost:8501`.

---

## File Structure
```
Concrete Design/
├── app.py                  ← Main entry-point (run this)
├── requirements.txt        ← Dependencies
├── README.md
└── modules/
    ├── __init__.py
    ├── columns.py          ← Module 1: Rectangular Columns
    ├── footings.py         ← Module 2: Isolated Footings
    └── flat_slab.py        ← Module 3: Flat Slabs
```

## Code References (ECP 203)
- **Column design**: ECP 203 §6.3.1, §6.7.1, §6.7.4
- **Footing design**: ECP 203 §8.2, Shear §7.3
- **Flat slab DDM**: ECP 203 §8.7 (aligned with ACI 318 §8.10)
