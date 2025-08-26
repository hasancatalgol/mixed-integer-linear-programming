# Brew & Blend: choose which malts to include (binary) and how much of each (continuous)
# to hit target beer properties at minimum ingredient + activation (fixed) cost.
#
# Setup:
#   pip install pyomo
#   and a MILP solver on PATH: HiGHS (recommended), CBC, or GLPK
# ------------------------------------------------------------

from pyomo.environ import (
    ConcreteModel, Set, Param, Var, Objective, Constraint, NonNegativeReals, Binary,
    SolverFactory, value
)

# ---------- Story data (toy but realistic-ish) ----------
# Malts: some “premium” ones carry an activation fee if used at all
MALTS = ['Pilsner', 'Vienna', 'Munich', 'Crystal60', 'Roasted', 'Wheat']

# Cost per kg of malt
cost = {
    'Pilsner':   1.8,
    'Vienna':    2.1,
    'Munich':    2.2,
    'Crystal60': 3.0,   # premium
    'Roasted':   3.4,   # premium
    'Wheat':     2.0,
}

# Fixed “activation” cost (setup/cleaning/losses) if the malt is used at all
activate_fee = {
    'Pilsner':   0.0,
    'Vienna':    0.0,
    'Munich':    0.0,
    'Crystal60': 25.0,
    'Roasted':   25.0,
    'Wheat':     0.0,
}

# Property contributions per kg of malt (linearized coefficients for demo)
# Think: “color points” and “body points” contributed per kg into the mash.
color_pt = {   # higher = darker
    'Pilsner':   1.0,
    'Vienna':    2.0,
    'Munich':    3.0,
    'Crystal60': 6.0,
    'Roasted':   12.0,
    'Wheat':     1.0,
}
body_pt = {    # higher = fuller body (a proxy property)
    'Pilsner':   1.0,
    'Vienna':    1.4,
    'Munich':    1.6,
    'Crystal60': 1.2,
    'Roasted':   0.8,
    'Wheat':     1.5,
}

# Availability/upper bound per malt (kg you have on hand today)
stock_max = {
    'Pilsner':   160,
    'Vienna':    80,
    'Munich':    80,
    'Crystal60': 40,
    'Roasted':   20,
    'Wheat':     60,
}

# Tank (mash tun) capacity measured in total grain kg; and minimum target batch grain
GRIST_MIN = 180   # must at least hit this to meet brew size
GRIST_MAX = 200   # physical capacity

# Target style ranges (per-kg normalized so proportions matter, not absolute size)
COLOR_MIN = 2.5
COLOR_MAX = 5.0
BODY_MIN  = 1.15
BODY_MAX  = 1.45

# Optional: cap the number of distinct malts used (simplify operations)
MAX_DISTINCT_MALTS = 4

# ---------- Model ----------
m = ConcreteModel()

m.J = Set(initialize=MALTS)

m.c = Param(m.J, initialize=cost)
m.fee = Param(m.J, initialize=activate_fee)
m.col = Param(m.J, initialize=color_pt)
m.body = Param(m.J, initialize=body_pt)
m.ub = Param(m.J, initialize=stock_max)

# Decision vars
m.x = Var(m.J, domain=NonNegativeReals)  # kg of each malt
m.z = Var(m.J, domain=Binary)            # 1 if malt is used at all

# Convenience: total grist
def total_grist(m):
    return sum(m.x[j] for j in m.J)
# We’ll reference this frequently; Pyomo likes explicit constraints, so we’ll recompute inline.

# Objective: minimize ingredient spend + activation fees
def obj_rule(m):
    return sum(m.c[j]*m.x[j] for j in m.J) + sum(m.fee[j]*m.z[j] for j in m.J)
m.OBJ = Objective(rule=obj_rule)

# Capacity & demand (size) constraints
m.GristMin = Constraint(expr=sum(m.x[j] for j in m.J) >= GRIST_MIN)
m.GristMax = Constraint(expr=sum(m.x[j] for j in m.J) <= GRIST_MAX)

# Linking: if a malt isn’t activated, you can’t use it; also respect stock
def link_rule(m, j):
    return m.x[j] <= m.ub[j] * m.z[j]
m.Link = Constraint(m.J, rule=link_rule)

# Style windows (normalized by total grist so the *proportions* drive properties)
# COLOR_MIN * total_grist <= sum(col_j * x_j) <= COLOR_MAX * total_grist
m.ColorLo = Constraint(expr=sum(m.col[j]*m.x[j] for j in m.J) >= COLOR_MIN * sum(m.x[j] for j in m.J))
m.ColorHi = Constraint(expr=sum(m.col[j]*m.x[j] for j in m.J) <= COLOR_MAX * sum(m.x[j] for j in m.J))
m.BodyLo  = Constraint(expr=sum(m.body[j]*m.x[j] for j in m.J) >= BODY_MIN  * sum(m.x[j] for j in m.J))
m.BodyHi  = Constraint(expr=sum(m.body[j]*m.x[j] for j in m.J) <= BODY_MAX  * sum(m.x[j] for j in m.J))

# Operational simplicity: limit distinct malts
m.DistinctLimit = Constraint(expr=sum(m.z[j] for j in m.J) <= MAX_DISTINCT_MALTS)

# (Optional) Require at least some base malt if you want:
# m.BaseRequired = Constraint(expr=m.x['Pilsner'] >= 0.30 * sum(m.x[j] for j in m.J))

# ---------- Solve ----------
solver = None
for cand in ['highs', 'cbc', 'glpk']:
    try:
        s = SolverFactory(cand)
        if s and s.available(exception=False):
            solver = s
            break
    except:
        pass

if solver is None:
    print("No MILP solver found (HiGHS/CBC/GLPK). Install one and re-run.")
else:
    solver.solve(m, tee=False)

    # ---------- Report ----------
    total_grist_val = sum(value(m.x[j]) for j in m.J)
    color_val = sum(value(m.col[j])*value(m.x[j]) for j in m.J) / total_grist_val if total_grist_val > 0 else 0.0
    body_val  = sum(value(m.body[j])*value(m.x[j]) for j in m.J) / total_grist_val if total_grist_val > 0 else 0.0

    print("\n=== Brew & Blend Plan ===")
    print(f"Total cost: {value(m.OBJ):.2f}")
    print(f"Total grist (kg): {total_grist_val:.1f}  (cap {GRIST_MAX} kg)")
    print(f"Style props: color={color_val:.2f} in [{COLOR_MIN},{COLOR_MAX}]  "
          f"body={body_val:.2f} in [{BODY_MIN},{BODY_MAX}]")
    used = [j for j in m.J if value(m.z[j]) > 0.5]
    print("Malts used:", used, f"(count={len(used)})")
    print("\nBreakdown (kg):")
    for j in m.J:
        if value(m.x[j]) > 1e-6:
            print(f"  {j:<10}  {value(m.x[j]):6.2f} kg")
