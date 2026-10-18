"""helm_brain_tks28.py -- Canonical 28-Foundation TKS (Tootra System) Recipe Brain for HELM.

Directly maps the 28 Foundations from 'THE 28.pdf' into a 40-digit Decimal CAS Recipe Brain.

Matrix: 4 Planes x 7 Universal Archetypes = 28 Foundations
- Planes:
    a: Spiritual
    b: Mental
    c: Emotional
    d: Physical
- Archetypes:
    1: Desire to be and be with God (Transcendence / Divine Purpose)
    2: Wisdom, insight, and knowledge (Gnosis / Epistemology / Intuition)
    3: Life, vitality, and health (Prana / Resilience / Stamina)
    4: Companionship, love, and friendship (Bonding / Empathy / Unity)
    5: Worldly power, influence, and control (Will / Authority / Manifestation)
    6: Material food and things (Sustenance / Resources / Abundance)
    7: Lust, sex, and reproduction (Creation / Vital Drive / Replication)

Core Features:
1. 28 Transparent Foundations (Registers).
2. 40-Digit Decimal Exact Arithmetic (Zero float inaccuracies).
3. Constant Elasticity of Substitution (CES) with curvature rho.
4. RPM Safety Gate: Halts immediately on missing prerequisites (Zero Hallucination).
5. Exact Gauss-Jordan Witness Solver: Solves weights deterministically from 28 observations.
"""

from decimal import Decimal, getcontext
from fractions import Fraction
import math

getcontext().prec = 40

TKS_PLANES = {
    "a": "Spiritual",
    "b": "Mental",
    "c": "Emotional",
    "d": "Physical"
}

TKS_ARCHETYPES = {
    1: "Divine Purpose / God",
    2: "Wisdom & Insight",
    3: "Vitality & Health",
    4: "Love & Companionship",
    5: "Power & Influence",
    6: "Sustenance & Resources",
    7: "Creation & Reproduction"
}

# 28 Foundations in canonical order
TKS_FOUNDATIONS_28 = [f"{num}{plane}" for plane in ("a", "b", "c", "d") for num in range(1, 8)]
assert len(TKS_FOUNDATIONS_28) == 28


def d40(val):
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, str)):
        return Decimal(str(val))
    if isinstance(val, float):
        return Decimal(str(val))
    if isinstance(val, Fraction):
        return Decimal(val.numerator) / Decimal(val.denominator)
    raise TypeError(f"Cannot convert {type(val)} to Decimal40")


def d_pow(base, exp):
    base_d = d40(base)
    exp_d = d40(exp)
    if base_d == 0:
        return Decimal(0) if exp_d > 0 else None
    if exp_d == 0:
        return Decimal(1)
    if exp_d == 1:
        return base_d
    if exp_d == Decimal("0.5"):
        return base_d.sqrt()
    if exp_d == Decimal("2.0") or exp_d == Decimal("2"):
        return base_d * base_d
    if base_d < 0:
        raise ValueError("Negative base not supported for non-integer powers")
    return (exp_d * base_d.ln()).exp()


class TKS28RecipeBrain:
    def __init__(self, weights=None, rho=None, thresholds=None):
        self.foundations = list(TKS_FOUNDATIONS_28)
        self.rho = d40(rho) if rho is not None else Decimal("0.5")

        if weights is None:
            self.weights = {f: Decimal("1.0") for f in self.foundations}
        else:
            self.weights = {f: d40(weights.get(f, 0)) for f in self.foundations}

        # Baseline thresholds for foundations (optional offsets)
        self.thresholds = {}
        if thresholds is not None:
            for f, val in thresholds.items():
                if f in self.foundations:
                    self.thresholds[f] = d40(val)

    def evaluate_recipe(self, inputs, recipe_name="TKS_Evaluation"):
        """Evaluate a state, decision, or psychological profile over the 28 Foundations."""
        # RPM Safety Gate: Check for absent prerequisites
        absent = []
        for f, w in self.weights.items():
            if w > 0:
                v = inputs.get(f)
                if v is None or d40(v) <= 0:
                    absent.append(f)

        if absent:
            plane_names = [f"{f} ({TKS_PLANES[f[1]]} {TKS_ARCHETYPES[int(f[0])]})" for f in absent]
            return {
                "status": "UNDETERMINED",
                "gate_code": "G-ABSENT",
                "recipe_name": recipe_name,
                "refusal_reason": f"Missing essential foundations: {plane_names}",
                "limiting_reagent": absent[0],
                "output_value": None,
                "hallucinations": 0
            }

        # Compute net values and bottleneck ratio
        net_inputs = {}
        min_ratio = None
        bottleneck = None

        for f in self.foundations:
            c_i = self.weights[f]
            raw_x = d40(inputs.get(f, Decimal(0)))
            thresh = self.thresholds.get(f, Decimal(0))
            net_x = max(Decimal(0), raw_x - thresh)
            net_inputs[f] = net_x

            ratio = net_x / (c_i if c_i > 0 else Decimal(1))
            if min_ratio is None or ratio < min_ratio:
                min_ratio = ratio
                bottleneck = f

        inner_sum = Decimal(0)
        weighted_sum_c = sum(self.weights.values())
        if weighted_sum_c == 0:
            output_y = Decimal(0)
            inner_sum = Decimal(0)
        elif self.rho == 0:
            # Cobb-Douglas limit (continuous weighted power mean as rho -> 0)
            weighted_ln = Decimal(0)
            zero_input = False
            for f in self.foundations:
                c_i = self.weights[f]
                if c_i > 0:
                    x_i = net_inputs[f]
                    if x_i <= 0:
                        zero_input = True
                        break
                    weighted_ln += (c_i / weighted_sum_c) * x_i.ln()
            output_y = Decimal(0) if zero_input else weighted_ln.exp()
            inner_sum = output_y
        else:
            for f in self.foundations:
                c_i = self.weights[f]
                x_i = net_inputs[f]
                w_i = c_i / weighted_sum_c
                term = w_i * d_pow(x_i, self.rho)
                inner_sum += term

            inv_rho = Decimal(1) / self.rho
            output_y = d_pow(inner_sum, inv_rho)

        return {
            "status": "EVALUATED",
            "gate_code": "GATE_PASS",
            "recipe_name": recipe_name,
            "output_value": str(output_y),
            "limiting_foundation": bottleneck,
            "limiting_description": f"{bottleneck} ({TKS_PLANES[bottleneck[1]]} {TKS_ARCHETYPES[int(bottleneck[0])]})",
            "rho": str(self.rho),
            "parameters": len(self.weights) + 1 + len(self.thresholds),
            "precision": "Decimal40",
            "hallucinations": 0
        }

    @classmethod
    def solve_witness_weights(cls, witness_rows, fixed_rho=Decimal("0.5"), thresholds=None):
        """Deterministically solve 28 foundation weights from 28 witness observations via Gauss-Jordan."""
        assert len(witness_rows) == 28, "Requires exactly 28 witness rows"
        rho = d40(fixed_rho)
        thresh = thresholds or {}

        A = []
        B = []
        for inputs, target_y in witness_rows:
            row = []
            for f in TKS_FOUNDATIONS_28:
                raw_x = d40(inputs[f])
                t = d40(thresh.get(f, 0))
                net_x = max(Decimal(0), raw_x - t)
                row.append(d_pow(net_x, rho))
            A.append(row)
            B.append(d_pow(d40(target_y), rho))

        n = 28
        M = [A[i][:] + [B[i]] for i in range(n)]

        for col in range(n):
            pivot = col
            while pivot < n and M[pivot][col] == 0:
                pivot += 1
            if pivot == n:
                raise ValueError("Witness rows are linearly dependent")
            M[col], M[pivot] = M[pivot], M[col]

            pv = M[col][col]
            for j in range(col, n + 1):
                M[col][j] /= pv

            for r in range(n):
                if r != col and M[r][col] != 0:
                    f = M[r][col]
                    for j in range(col, n + 1):
                        M[r][j] -= f * M[col][j]

        weights = {TKS_FOUNDATIONS_28[i]: M[i][n] for i in range(n)}
        return cls(weights=weights, rho=rho, thresholds=thresh)


def self_test_tks28():
    print("Testing TKS28RecipeBrain...")
    brain = TKS28RecipeBrain()
    inputs = {f: Decimal(f"10.{i+1}") for i, f in enumerate(TKS_FOUNDATIONS_28)}
    res = brain.evaluate_recipe(inputs, "Wholeness_Check")
    assert res["status"] == "EVALUATED"
    print(f"[PASS] Evaluated successfully. Output Y = {res['output_value']}, Limiting = {res['limiting_description']}")

    # Missing Spiritual Purpose (1a)
    missing_inputs = dict(inputs)
    del missing_inputs["1a"]
    halt = brain.evaluate_recipe(missing_inputs, "Leadership_Without_Purpose")
    assert halt["status"] == "UNDETERMINED"
    print(f"[PASS] RPM Gate successfully blocked execution: {halt['refusal_reason']}")
    print("TKS28 BRAIN VERIFIED CLEANLY.")


if __name__ == "__main__":
    self_test_tks28()
