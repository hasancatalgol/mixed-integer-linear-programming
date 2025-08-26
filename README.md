# Brew & Blend — A Pyomo MILP Example (README)

A friendly, story-driven **mixed-integer linear program (MILP)** modeled in **Pyomo**.  
You’ll choose which malts to include (binary on/off with activation fees) and how much of each (continuous) to **hit target beer style properties** at **minimum cost**—while respecting tank capacity and inventory.

---

## 📖 Story

You’re running a craft brewery. Each malt type contributes to **color** and **body**. Some premium malts require a fixed **activation fee** (extra cleaning, losses) if you use them at all. You have:
- A **minimum/maximum total grist** (batch size & tank capacity),
- **Inventory limits** per malt,
- **Target style windows** for color and body,
- And a practical cap on the **number of distinct malts** (operational simplicity).

**Goal:** Minimize *ingredient cost + activation fees* while meeting the style and capacity rules.

---

## 🧮 Mathematical Model

### Sets
- $J$: set of malts.

### Parameters
- $c_j$ — cost per kg for malt $j$.
- $f_j$ — fixed activation fee if malt $j$ is used at all.
- $\mathrm{col}_j$ — color contribution per kg of malt $j$.
- $\mathrm{body}_j$ — body contribution per kg of malt $j$.
- $\overline{x}_j$ — available inventory (kg) of malt $j$.
- Scalars: $\text{GRIST\_MIN}$, $\text{GRIST\_MAX}$, $\text{COLOR\_MIN}$, $\text{COLOR\_MAX}$, $\text{BODY\_MIN}$, $\text{BODY\_MAX}$, $\text{MAX\_DISTINCT\_MALTS}$.

### Decision Variables
- $x_j \ge 0$: kg of malt $j$ used.
- $z_j \in \{0,1\}$: 1 if malt $j$ is used, else 0.

### Objective
$$
\min \sum_{j\in J} c_j x_j + \sum_{j\in J} f_j z_j
$$

### Constraints

1. **Batch size (grist) bounds**
$$
\sum_{j\in J} x_j \ge \text{GRIST\_MIN}, \qquad
\sum_{j\in J} x_j \le \text{GRIST\_MAX}
$$

2. **Linking & inventory** (no using a malt unless it’s activated; respect stock)
$$
x_j \le \overline{x}_j\, z_j \quad \forall j\in J
$$

3. **Style windows** (normalize contributions by total grist so proportions govern style)
$$
\sum_{j\in J} \mathrm{col}_j\, x_j \;\ge\; \text{COLOR\_MIN}\, \sum_{j\in J} x_j, \qquad
\sum_{j\in J} \mathrm{col}_j\, x_j \;\le\; \text{COLOR\_MAX}\, \sum_{j\in J} x_j
$$
$$
\sum_{j\in J} \mathrm{body}_j\, x_j \;\ge\; \text{BODY\_MIN}\, \sum_{j\in J} x_j, \qquad
\sum_{j\in J} \mathrm{body}_j\, x_j \;\le\; \text{BODY\_MAX}\, \sum_{j\in J} x_j
$$

4. **Operational simplicity** (limit distinct malts)
$$
\sum_{j\in J} z_j \le \text{MAX\_DISTINCT\_MALTS}
$$

---

## 🔧 Requirements

- **Python** 3.9+ (3.11 is fine).
- **Pyomo**: `pip install pyomo`
- A MILP **solver** on your PATH, e.g.:
  - **HiGHS** (recommended): install the `highspy` wheel → `pip install highspy` (adds the `highs` executable for many platforms).
  - **CBC**: see COIN-OR Cbc releases or package managers.
  - **GLPK**: `apt-get install glpk-utils` (Linux) or `brew install glpk` (macOS).

> On Windows, you can use `pip install highspy` for HiGHS. For CBC/GLPK, either use conda-forge or prebuilt binaries and ensure the solver exe is on PATH.

---

## 🚀 Quick Start

1. **Create the model file** `brew_blend.py` and paste the complete code from the section below.
2. Install dependencies:
   ```bash
   pip install pyomo highspy
   ```
3. **Run**:
   ```bash
   uv run main.py
   ```
4. You should see a plan summary with:
   - Total cost,
   - Total grist,
   - Achieved style properties (color/body),
   - Which malts were used and their kg.

> If you don’t have a solver on PATH, the script will print a message telling you to install one (HiGHS/CBC/GLPK).

---

## 📦 Example Data (built into the script)

- **Malts**: Pilsner, Vienna, Munich, Crystal60 (premium), Roasted (premium), Wheat  
- **Activation fees** only for premium malts (Crystal60, Roasted).  
- **Color/body** contributions are linearized demo coefficients.  
- **Inventory caps** per malt.  
- **Grist** bounds: `GRIST_MIN = 180`, `GRIST_MAX = 200` (kg).  
- **Style windows**: `COLOR in [2.5, 5.0]`, `BODY in [1.15, 1.45]`.  
- **Distinct malts** cap: `MAX_DISTINCT_MALTS = 4`.

These can be tweaked in the code to represent real recipes/styles.

---

## 🧠 Why MILP here?

- Binary **activation** decisions ($z_j$) capture “use this malt at all (yes/no) and pay the fixed fee if yes”.  
- Continuous **quantity** decisions ($x_j$) choose the optimal mix.  
- **Linear** property windows and capacity constraints keep it MILP (no nonlinear brewing physics here).  
- The linking constraint $x_j \le \overline{x}_j z_j$ ensures no usage without activation (classic big-$M$, with $M = \overline{x}_j$).

---

## 🧪 Sample Output (will vary with solver/data)

```
=== Brew & Blend Plan ===
Total cost: 472.80
Total grist (kg): 190.0  (cap 200 kg)
Style props: color=3.10 in [2.50,5.00]  body=1.28 in [1.15,1.45]
Malts used: ['Pilsner', 'Munich', 'Crystal60', 'Wheat'] (count=4)

Breakdown (kg):
  Pilsner        120.00 kg
  Munich          40.00 kg
  Crystal60       10.00 kg
  Wheat           20.00 kg
```

*Numbers above are illustrative; your solution may differ.*

---

## 🧭 Variations & Extensions

- Add **minimum proportion** of base malt: `x['Pilsner'] ≥ 0.30 * Σ x`.
- Introduce **soft penalties** for going outside style windows (big-M slack with costs).
- Add **multiple style targets** (e.g., bitterness, gravity) if you have linear surrogates.
- Replace the distinct-malts cap with **per-malt min run sizes**.
- Turn this into a **multi-period** plan with inventory carryover and production scheduling.

---

## 🆘 Troubleshooting

- **“No MILP solver found”** → Install HiGHS (`pip install highspy`) or another solver and ensure the executable is on PATH.
- **Infeasible model** → Try relaxing style windows, raising GRIST_MAX, or upping inventory. Check `MAX_DISTINCT_MALTS` (too small can make it infeasible).
- **Different answers on different machines** → Equivalent optimal solutions can exist; tiny cost or tie-breaking differences are normal.

---
