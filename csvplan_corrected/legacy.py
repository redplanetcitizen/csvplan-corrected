"""Legacy compatibility implementation of ``csvplan.jl``.

This module is intentionally autonomous and preserves the Julia prototype's
runtime semantics on the supplied CSV files, including its anomalous linear
indexing, terminal buffer, investment scheduling, depreciation timing, Harmony
calculation, and sample standard deviation.  Choices without a basis in the
Design are retained solely to provide a historical comparison oracle; see
``README_csvplan_corrected.md``.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import copy
import csv
import io
import time
import numpy as np

MINCOEFF = 0.034
MAXITER = 3000
VERBOSE = False
LINEAR = False
INVERSE_DEPRECIATE_INVESTMENTS = False
DEPRECIATION_HORIZON = 14
INITIAL_INVESTMENT_LEVEL = 0.7
EPSILON = 0.25 / DEPRECIATION_HORIZON


@dataclass
class PlanProblem:
    headers: list[str]
    flows: np.ndarray
    caps: np.ndarray
    dep: np.ndarray
    labtarg: np.ndarray
    A: np.ndarray
    V: np.ndarray
    C: np.ndarray
    D: np.ndarray
    AD: np.ndarray
    IminusA: np.ndarray
    InvIA: np.ndarray
    labouravailable: np.ndarray
    g: np.ndarray
    TheLastYear: int
    caprows: int
    capcols: int


@dataclass
class Scenario:
    prob: PlanProblem
    O: np.ndarray
    si: np.ndarray
    investments: np.ndarray
    goal_fullfilment_ratio_vector: np.ndarray
    h: np.ndarray
    meanh: float
    stdh: float
    investmentsByTypeAndYear: np.ndarray
    netoutputs: list[np.ndarray]
    targets: np.ndarray


def _read_csv_numeric(path: str | Path):
    path = Path(path)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = [[float(x) for x in row] for row in reader if row]
    return np.asarray(rows, dtype=np.float64), headers


def readinspreadsheets(flow, cap, dep, labtarg):
    flowsd, _ = _read_csv_numeric(flow)
    capsd, _ = _read_csv_numeric(cap)
    depsd, _ = _read_csv_numeric(dep)
    labtargsd, labtargsh = _read_csv_numeric(labtarg)
    return labtargsh, flowsd, capsd, depsd, labtargsd


def extractlaboursupply(labtargs, headers):
    lrow, _ = labtargs.shape
    hcol = len(headers)
    if headers[hcol - 1] != "Labour":
        raise ValueError("Labour not last header of labtargs")
    l = np.zeros(lrow + DEPRECIATION_HORIZON, dtype=np.float64)
    # Julia: for i=1:lrow+horizon; if i < lrow ... else last row.
    for i0 in range(lrow + DEPRECIATION_HORIZON):
        i = i0 + 1
        if i < lrow:
            l[i0] = labtargs[i0, hcol - 1]
        else:
            l[i0] = labtargs[lrow - 1, hcol - 1]
    return l


def extracttargets(labtargs, headers):
    lrow, _ = labtargs.shape
    hcol = len(headers)
    if headers[0] != "Year":
        raise ValueError("Year not first header of labtargs")
    v = labtargs[:, 1 : hcol - 1]
    g = np.zeros((lrow + DEPRECIATION_HORIZON, hcol - 2), dtype=np.float64)
    g[:lrow, :] = v
    for i0 in range(lrow, lrow + DEPRECIATION_HORIZON):
        g[i0, :] = v[lrow - 1, :]
    return np.hstack([g, np.zeros((lrow + DEPRECIATION_HORIZON, 1), dtype=np.float64)])


def generateDMatrix(C, dep):
    crow, ccol = C.shape
    drow, dcol = dep.shape
    D = np.zeros((crow, ccol), dtype=np.float64)
    D[:drow, :dcol] = C[:drow, :dcol] * dep
    return D


def generateCMatrix(flowmatrix, cap):
    rows, cols = flowmatrix.shape
    N = rows - 1
    if N != cols + 1:
        raise ValueError("rows not equal to cols +2 in flowmatrix")
    O = flowmatrix[rows - 1, :cols]
    Normcap = np.zeros((N, N), dtype=np.float64)
    for row in range(N - 1):
        for col in range(N - 1):
            Normcap[row, col] = cap[row, col] / O[col]
    return Normcap


def generateAMatrix(flowmatrix):
    rows, cols = flowmatrix.shape
    N = rows - 1
    if N != cols + 1:
        raise ValueError("rows not equal to cols +2 in flowmatrix")
    O = flowmatrix[rows - 1, :cols]
    Normfloe = np.zeros((N, cols), dtype=np.float64)
    for row in range(N):
        for col in range(cols):
            Normfloe[row, col] = flowmatrix[row, col] / O[col]
    return np.hstack([Normfloe, np.zeros((N, 1), dtype=np.float64)])


def inversedepreciate(capital, yearsearlier, depreciationmatrix):
    if yearsearlier <= 1:
        return capital
    c = inversedepreciate(capital, yearsearlier - 1, depreciationmatrix)
    return c / (1.0 - depreciationmatrix)


def rowiseScale(A, b):
    # Julia loops colwise: C[row,col] = A[row,col] * b[col]
    return np.asarray(A, dtype=np.float64) * np.asarray(b, dtype=np.float64)[None, :]


def grossOutputForDemandf(f, A):
    invia = np.linalg.inv(np.eye(A.shape[0]) - A)
    return invia @ f


def computeMaxPossOutput_in_principle_possible(s, l, A, C, O, year):
    N, _ = A.shape
    labrow = A[N - 1, :]
    thisyearoutput = O[year, :]
    labourneeded = float(np.sum(labrow * thisyearoutput))
    labourconstraint = float(l[year] / labourneeded)
    capneeded = rowiseScale(C, thisyearoutput)
    caprow, capcol = s[year, :, :].shape
    metratios = s[year, :, :] / capneeded[:caprow, :capcol]
    capitalmin = float(np.min(metratios))
    return min(capitalmin, labourconstraint)


def computeMaxPossOutputRatioAllYears(s, l, A, C, O):
    lastyear, _ = O.shape
    return np.array(
        [computeMaxPossOutput_in_principle_possible(s, l, A, C, O, year) for year in range(lastyear)],
        dtype=np.float64,
    )


def compute_goal_fulfillment_vector_raw(s, l, O, A, C):
    return computeMaxPossOutputRatioAllYears(s, l, A, C, O)


def compute_Labour_Value_From_Augmented_A_Matrix(A):
    N, _ = A.shape
    v = np.zeros(N, dtype=np.float64)
    v[N - 1] = 1.0
    for _ in range(12):
        nv = A.T @ v
        v = nv
        v[N - 1] = 1.0
    return v


def inproduct(v1, v2):
    a = np.asarray(v1, dtype=np.float64).reshape(-1)
    b = np.asarray(v2, dtype=np.float64).reshape(-1)
    short = min(a.size, b.size)
    t = 0.0
    for i in range(short):
        t += a[i] * b[i]
    return t


def valueof(valuation, commodity):
    commodity = np.asarray(commodity, dtype=np.float64)
    if commodity.ndim == 1:
        return inproduct(valuation, commodity)
    n, _ = commodity.shape
    subv = np.asarray(valuation, dtype=np.float64)[:n]
    return float(np.sum(commodity.T @ subv))


def For_the_last_year_of_the_plan_return_a_net_output_target(last_year, A, D, g, l):
    Gross = grossOutputForDemandf(g[last_year, :], A)
    labourRow, _ = A.shape
    labourUsed = float(Gross.T @ A[labourRow - 1, :])
    depreciationvec = D @ Gross
    scale = float(l[last_year] / labourUsed)
    newtarget = (g[last_year, :] + depreciationvec) * scale
    scaledgross = Gross * scale
    depreciationallowanceMatrix = rowiseScale(D, scaledgross)
    return depreciationallowanceMatrix, newtarget


def harmony(x):
    if LINEAR:
        return x
    return x / (1.1 + x)


def harmonyInverse(h):
    if LINEAR:
        return h
    return (1.1 * h) / (1.0 - h)


def finaloutputforGross(gross, A):
    return (np.eye(A.shape[0]) - A) @ gross


def depreciateamountbyyears(amount, years, depreciationmatrix):
    # Exact recursive semantics of Julia source: years <= 1 returns amount.
    if years <= 1:
        return amount
    return depreciateamountbyyears(amount, years - 1, depreciationmatrix) * (1.0 - depreciationmatrix)


def investmentsByTypeandYear(investments):
    years, sources, dests = investments.shape
    bytypeandyear = np.zeros((years, sources), dtype=np.float64)
    for y in range(years):
        for s in range(sources):
            for d in range(dests):
                bytypeandyear[y, s] += investments[y, s, d]
    return bytypeandyear


def update_subsequent_years_capital(firstyearavailable, amount, horizons, si):
    years, _, _ = si.shape
    for y in range(firstyearavailable, years):
        si[y, :, :] = si[y, :, :] + depreciateamountbyyears(
            amount, y - firstyearavailable, horizons
        )


def setup_preliminary_investment_schedule(year, investments, preassignedcapital, horizons, si):
    investments[year, :, :] = preassignedcapital[:, :]
    update_subsequent_years_capital(year + 1, preassignedcapital, horizons, si)


def Assign_to_each_year_capital_stock(caps, deps, TheLastYear):
    caprow, capcol = caps.shape
    si = np.zeros((TheLastYear, caprow, capcol), dtype=np.float64)
    si[0, :, :] = caps
    for i0 in range(1, TheLastYear):
        # Julia year i is 2..T and calls depreciateamountbyyears(caps, i, deps)
        si[i0, :, :] = depreciateamountbyyears(caps, i0 + 1, deps)
    return si


def compute_goal_fulfillment_scenario(s: Scenario):
    s.goal_fullfilment_ratio_vector = compute_goal_fulfillment_vector_raw(
        s.si, s.prob.labouravailable, s.O, s.prob.A, s.prob.C
    )


def update_outputs(s: Scenario):
    lastyear = s.prob.TheLastYear
    investmentsbytype = investmentsByTypeandYear(s.investments)
    s.investmentsByTypeAndYear = investmentsbytype
    s.targets = s.prob.g[:, :-1] + s.investmentsByTypeAndYear
    gplusi = np.zeros_like(s.prob.g, dtype=np.float64)
    gplusi[:, :-1] = s.targets
    s.O = np.vstack([grossOutputForDemandf(gplusi[i, :], s.prob.A) for i in range(lastyear)])
    compute_goal_fulfillment_scenario(s)
    possibleratios = s.goal_fullfilment_ratio_vector
    finaloutput = [s.targets[i, :] * possibleratios[i] for i in range(lastyear)]
    # Exact Julia semantics: `investmentsbytype[i]` uses ONE index on a 2-D
    # matrix, hence Julia's column-major linear indexing returns a scalar.
    # The scalar is then broadcast-subtracted from the whole final-output row.
    inv_linear = investmentsbytype.ravel(order="F")
    s.netoutputs = [finaloutput[i] - inv_linear[i] for i in range(lastyear)]


def computeHarmonies_raw(s: Scenario, possibleratios, investmentsbytype, netgoals, O, A):
    lastyear = s.prob.TheLastYear
    fulfillmentratio = [s.netoutputs[i] / s.prob.g[i, :-1] for i in range(lastyear)]
    harmonyarrayofarrays = [harmony(fulfillmentratio[i]) for i in range(lastyear)]
    # Faithful to Julia: [1:end-1] is applied after labour has already been
    # removed from g, so the last commodity is also excluded from the minimum.
    minimised = np.array([np.min(harmonyarrayofarrays[i][:-1]) for i in range(lastyear)], dtype=np.float64)
    return minimised


def Compute_mean_harmony_and_standard_deviation(harmonies):
    # Julia Statistics.std => corrected/sample standard deviation.
    return float(np.mean(harmonies)), float(np.std(harmonies, ddof=1))


def computeHarmonies(s: Scenario):
    s.h = computeHarmonies_raw(
        s,
        s.goal_fullfilment_ratio_vector,
        s.investmentsByTypeAndYear,
        s.prob.g,
        s.O,
        s.prob.A,
    )
    s.meanh, s.stdh = Compute_mean_harmony_and_standard_deviation(s.h)


def updateScenario(s: Scenario, bestyear, capital):
    s.investments[bestyear, :, :] = s.investments[bestyear, :, :] + capital
    if float(np.sum(capital)) == 0.0:
        raise ValueError("attempt to update with zero investment")
    update_subsequent_years_capital(bestyear + 1, capital, s.prob.dep, s.si)
    return s


def variant_scenario(s: Scenario, newinvestmentforyear, year):
    s2 = copy.deepcopy(s)
    updateScenario(s2, year, newinvestmentforyear)
    update_outputs(s2)
    computeHarmonies(s2)
    return s2


def gainfromInvesting(s: Scenario, fromyear: int, amountmore):
    variant = variant_scenario(s, amountmore, fromyear)
    return variant.meanh - s.meanh, variant


def capitalbyyear(s: Scenario):
    return np.array([np.sum(s.si[i, :, :]) for i in range(s.prob.TheLastYear)], dtype=np.float64)


def Attempt_to_scale_up(s: Scenario, destyear: int, scaleincrementtomeetmeanharmony: float):
    csy = s.si[destyear, :, :]
    n, m = csy.shape
    additionalcapital = csy * scaleincrementtomeetmeanharmony
    additionalcapital = np.where(additionalcapital < 0.0, 0.0, additionalcapital)

    bestyear = None
    bestgain = 0.0
    bestscenario = s
    for y in range(0, destyear):
        originalcapital = additionalcapital
        if INVERSE_DEPRECIATE_INVESTMENTS:
            # Julia: destyear - 1 - y in 1-based variables. Converting both
            # indices to 0-based leaves destyear - 1 - y numerically unchanged.
            originalcapital = inversedepreciate(additionalcapital, destyear - 1 - y, s.prob.dep)
        gain, newscenario = gainfromInvesting(s, y, originalcapital)
        posflags = s.netoutputs[y][:n] > np.zeros(n)
        if gain > bestgain and bool(np.prod(posflags)):
            bestyear = y
            bestgain = gain
            bestscenario = newscenario

    if bestyear is None:
        return s, False
    return bestscenario, True


def Estimate_how_much__production_to_be_scaled_up(s: Scenario, this_year):
    target = harmonyInverse(s.meanh)
    current = harmonyInverse(s.h[this_year])
    diff = target - current
    if diff < 0:
        raise ValueError("request for negative upscale")
    return diff * EPSILON


def readInProblem(flowname, capname, depname, labtagsname):
    headers, flows, caps, dep, labtarg = readinspreadsheets(flowname, capname, depname, labtagsname)
    A = generateAMatrix(flows)
    V = compute_Labour_Value_From_Augmented_A_Matrix(A)
    C = generateCMatrix(flows, caps)
    D = generateDMatrix(C, dep)
    AD = A + D
    IminusA = np.eye(A.shape[0]) - A
    labouravailable = extractlaboursupply(labtarg, headers)
    g = extracttargets(labtarg, headers)
    TheLastYear = g.shape[0]
    caprows, capcols = caps.shape
    return PlanProblem(
        headers, flows, caps, dep, labtarg, A, V, C, D, AD, IminusA,
        np.linalg.inv(IminusA), labouravailable, g, TheLastYear, caprows, capcols
    )



def _display_label(value):
    text = str(value)
    aliases = {
        "foreigntrade": "Foreign trade",
        "Labour": "Labour",
        "Year": "Year",
    }
    return aliases.get(text, text)


def _format_amount(value):
    """Presentation only: economic quantities, two decimals."""
    if value == "" or value is None:
        return "—"
    x = float(value)
    if abs(x) < 0.005:
        x = 0.0
    return f"{x:,.2f}"


def _format_ratio(value, decimals=5):
    """Presentation only: dimensionless ratios/harmony values."""
    return f"{float(value):.{decimals}f}"


def _format_percent(value, decimals=2):
    return f"{100.0 * float(value):.{decimals}f}%"


def _render_table(headers, rows, right_align=None):
    """Render a compact ASCII table suitable for Windows/macOS/Linux terminals."""
    string_rows = [[str(cell) for cell in row] for row in rows]
    string_headers = [str(h) for h in headers]

    ncols = len(string_headers)
    if right_align is None:
        right_align = set(range(1, ncols))
    else:
        right_align = set(right_align)

    widths = [len(string_headers[i]) for i in range(ncols)]
    for row in string_rows:
        for i in range(ncols):
            value = row[i] if i < len(row) else ""
            widths[i] = max(widths[i], len(value))

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def make_row(row):
        cells = []
        for i, width in enumerate(widths):
            value = row[i] if i < len(row) else ""
            if i in right_align:
                cells.append(" " + value.rjust(width) + " ")
            else:
                cells.append(" " + value.ljust(width) + " ")
        return "|" + "|".join(cells) + "|"

    lines = [border, make_row(string_headers), border]
    lines.extend(make_row(row) for row in string_rows)
    lines.append(border)
    return "\n".join(lines)



def _operator_note_text(title, text, width=96):
    """Render an explanatory note into the csvplan output stream."""
    import textwrap
    lines = [
        "-" * width,
        f"NOTA DI LETTURA - {title}",
        "-" * width,
    ]
    for paragraph in str(text).strip().split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
        else:
            lines.extend(
                textwrap.wrap(
                    paragraph,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
    return "\n".join(lines)

def display_result(
    year,
    investmentsbytype,
    C,
    si,
    harmonies,
    headings,
    gross,
    A,
    labsupply,
    goal,
    s,
    out=None,
):
    if out is None:
        import sys
        out = sys.stdout

    labels = [_display_label(h) for h in headings[1:]]
    rows, cols = A.shape
    _, invrows = investmentsbytype.shape

    flow_rows = []
    balance_rows = []
    labused = 0.0

    for row in range(rows):
        cells = A[row, :] * gross
        tot = float(np.sum(cells))

        # Preserve the original Julia display semantics exactly:
        # `row < invrows` is evaluated in Julia's 1-based coordinates.
        julia_row = row + 1
        toti = investmentsbytype[year, row] if julia_row < invrows else 0.0
        final = s.netoutputs[year][row] if julia_row < rows else ""
        target = goal[year, row] if julia_row < rows else ""

        flow_rows.append(
            [labels[row]]
            + [_format_amount(x) for x in cells]
            + [_format_amount(tot)]
        )

        balance_rows.append(
            [
                labels[row],
                _format_amount(toti),
                _format_amount(final),
                _format_amount(target),
            ]
        )

        if julia_row == rows:
            labused = tot

    employment_ratio = float(labused / labsupply)

    print("\n" + "=" * 96, file=out)
    print(
        f"YEAR {year + 1} RESULTS  |  Harmony: {_format_ratio(harmonies[year])}  "
        f"|  Employment: {_format_percent(employment_ratio)}",
        file=out,
    )
    print("=" * 96, file=out)

    print("\nA. INPUT-OUTPUT FLOWS", file=out)
    print(
        _operator_note_text(
            "Flussi input-output",
            "Ogni colonna rappresenta un settore produttore e ogni riga un input necessario. "
            "Le celle sono i consumi intermedi richiesti dal gross output effettivamente realizzabile "
            "nell'anno. La colonna 'Intermediate cons.' somma, per ciascun input, quanto viene "
            "assorbito complessivamente dalla produzione. La riga Labour mostra il lavoro incorporato "
            "nel livello di produzione raggiunto.",
        ),
        file=out,
    )
    print(
        _render_table(
            ["Input sector"] + labels + ["Intermediate cons."],
            flow_rows,
        ),
        file=out,
    )

    print("\nB. INVESTMENT AND FINAL OUTPUT", file=out)
    print(
        _operator_note_text(
            "Investimento e prodotto finale",
            "Investment è la parte dell'output del settore destinata ad accumulazione di capitale "
            "anziché a uso finale. Final output è ciò che resta disponibile dopo consumi intermedi "
            "e investimento. Target è l'obiettivo di domanda finale per quell'anno. Il confronto "
            "Final output / Target determina il fulfillment per prodotto da cui viene ricavata "
            "l'Harmony dell'anno.",
        ),
        file=out,
    )
    print(
        _render_table(
            ["Sector", "Investment", "Final output", "Target"],
            balance_rows,
        ),
        file=out,
    )

    gross_rows = [
        [labels[i], _format_amount(gross[i])]
        for i in range(len(gross))
    ]
    print("\nC. GROSS OUTPUT", file=out)
    print(
        _operator_note_text(
            "Gross output",
            "Il gross output è la produzione totale necessaria prima di sottrarre consumi intermedi "
            "e investimenti. È ottenuto tramite la relazione input-output con la matrice A e poi "
            "ridotto, se necessario, dai vincoli di capitale e lavoro. Per questo non coincide con "
            "il prodotto finale disponibile al consumo.",
        ),
        file=out,
    )
    print(
        _render_table(
            ["Sector", "Gross output"],
            gross_rows,
        ),
        file=out,
    )

    capital_rows = []
    rows_c, cols_c = C.shape
    for row in range(rows_c):
        cells = C[row, :] * gross
        capital_rows.append(
            [labels[row]] + [_format_amount(x) for x in cells]
        )

    print("\nD. CAPITAL STOCK", file=out)
    print(
        _operator_note_text(
            "Capitale richiesto",
            "La matrice mostra il capitale di ciascun tipo richiesto per sostenere il gross output "
            "dell'anno, applicando la matrice dei coefficienti di capitale C. Il confronto tra questa "
            "domanda di capitale e lo stock effettivamente disponibile è ciò che identifica eventuali "
            "vincoli di capacità produttiva.",
        ),
        file=out,
    )
    print(
        _render_table(
            ["Capital type"] + labels,
            capital_rows,
        ),
        file=out,
    )

    print("\nE. YEAR SUMMARY", file=out)
    print(
        _operator_note_text(
            "Riepilogo annuale",
            "Harmony sintetizza il peggior grado di soddisfazione tra i prodotti dell'anno, dopo la "
            "trasformazione H(x)=x/(1.1+x). Labour used deriva dalla riga lavoro della matrice A; "
            "Employment confronta lavoro usato e lavoro disponibile. Questi indicatori servono a "
            "valutare l'equilibrio del piano, non sono direttamente percentuali di benessere sociale.",
        ),
        file=out,
    )
    summary_rows = [
        ["Harmony", _format_ratio(harmonies[year])],
        ["Labour available", _format_amount(labsupply)],
        ["Labour used", _format_amount(labused)],
        ["Employment ratio", _format_ratio(employment_ratio)],
        ["Employment", _format_percent(employment_ratio)],
    ]
    print(
        _render_table(
            ["Indicator", "Value"],
            summary_rows,
        ),
        file=out,
    )

def solvePlanProblem(
    fln,
    cpn,
    dpn,
    ltn,
    *,
    print_output=True,
    verbose=False,
    progress=False,
    progress_every=25,
):
    start_time = time.perf_counter()
    if progress:
        print("\n[CSVPLAN] Lettura e validazione degli input...", flush=True)

    problem = readInProblem(fln, cpn, dpn, ltn)

    if progress:
        original_years = problem.TheLastYear - DEPRECIATION_HORIZON
        print(
            f"[CSVPLAN] Input validati: {original_years} anni espliciti, "
            f"{problem.capcols} settori produttivi.",
            flush=True,
        )
        print(
            f"[CSVPLAN] Orizzonte interno: {problem.TheLastYear} periodi "
            f"(inclusi {DEPRECIATION_HORIZON} periodi terminali di deprezzamento).",
            flush=True,
        )
        print("[CSVPLAN] Costruzione dello scenario iniziale...", flush=True)
    _, lastgoal = For_the_last_year_of_the_plan_return_a_net_output_target(
        problem.TheLastYear - 1, problem.A, problem.D, problem.g, problem.labouravailable
    )
    problem.g[problem.TheLastYear - 1, :] = lastgoal

    Otmp = np.vstack([grossOutputForDemandf(problem.g[i, :], problem.A) for i in range(problem.TheLastYear)])
    sitmp = Assign_to_each_year_capital_stock(problem.caps, problem.dep, problem.TheLastYear)
    investmentstmp = np.zeros((problem.TheLastYear, problem.caprows, problem.capcols), dtype=np.float64)
    preassignedcapital = INITIAL_INVESTMENT_LEVEL * (problem.caps * problem.dep)
    for y in range(problem.TheLastYear - 1):
        setup_preliminary_investment_schedule(y, investmentstmp, preassignedcapital, problem.dep, sitmp)

    baseScenario = Scenario(
        problem,
        Otmp,
        sitmp,
        investmentstmp,
        np.zeros(problem.TheLastYear, dtype=np.float64),
        np.zeros(problem.TheLastYear, dtype=np.float64),
        0.0,
        0.0,
        np.zeros((problem.TheLastYear, problem.capcols), dtype=np.float64),
        [np.zeros(problem.capcols, dtype=np.float64) for _ in range(problem.TheLastYear)],
        problem.g.copy(),
    )
    update_outputs(baseScenario)
    computeHarmonies(baseScenario)

    if progress:
        initial_cv = baseScenario.stdh / abs(baseScenario.meanh)
        print(
            "[CSVPLAN] Scenario iniziale pronto: "
            f"mean harmony={baseScenario.meanh:.5f}, "
            f"std={baseScenario.stdh:.5f}, CV={initial_cv:.5f}.",
            flush=True,
        )
        print("[CSVPLAN] Avvio delle iterazioni di riallocazione...", flush=True)

    iter_count = 1
    doagain = True
    stop_reason = None
    while doagain:
        for i in range(1, problem.TheLastYear):  # Julia 2:TheLastYear
            cv_abs = baseScenario.stdh / abs(baseScenario.meanh)
            if (cv_abs < MINCOEFF) or (iter_count > MAXITER):
                if print_output:
                    print(" iterations,Harmony coefficient of variation ")
                    print(str(iter_count) + "," + str(baseScenario.stdh / baseScenario.meanh))
                doagain = False
                stop_reason = "cv" if cv_abs < MINCOEFF else "maxiter"
                break
            iter_count += 1

            if progress and (
                iter_count == 2 or iter_count % max(1, int(progress_every)) == 0
            ):
                current_cv = baseScenario.stdh / abs(baseScenario.meanh)
                elapsed = time.perf_counter() - start_time
                print(
                    f"[CSVPLAN] iterazione {iter_count:4d}/{MAXITER} | "
                    f"mean H={baseScenario.meanh:.5f} | "
                    f"std={baseScenario.stdh:.5f} | "
                    f"CV={current_cv:.5f} | "
                    f"{elapsed:.1f} s",
                    flush=True,
                )

            if doagain and baseScenario.h[i] < baseScenario.meanh:
                lowyear = i
                upscale = Estimate_how_much__production_to_be_scaled_up(baseScenario, lowyear)
                baseScenario, success = Attempt_to_scale_up(baseScenario, lowyear, upscale)
                if not success:
                    if print_output:
                        print(" we have not found a possible transfer of resources, terminating")
                    doagain = False
                    stop_reason = "no_transfer"
        if not doagain:
            break

    if progress:
        elapsed = time.perf_counter() - start_time
        final_cv = baseScenario.stdh / abs(baseScenario.meanh)
        print(
            f"[CSVPLAN] Iterazioni terminate: {iter_count}. "
            f"Motivo: {stop_reason}. CV finale={final_cv:.5f}.",
            flush=True,
        )
        print(
            f"[CSVPLAN] Calcolo completato in {elapsed:.1f} s. "
            "Preparazione delle tabelle di output...",
            flush=True,
        )

    rendered = io.StringIO()
    print("\n" + "=" * 96, file=rendered)
    print("CSVPLAN - FORMATTED RESULTS", file=rendered)
    print("=" * 96, file=rendered)
    print(
        "Display precision: economic quantities = 2 decimals; "
        "Harmony/ratios = 5 decimals; percentages = 2 decimals.",
        file=rendered,
    )
    print(
        "IMPORTANT: rounding affects presentation only; all calculations use full Float64 precision.",
        file=rendered,
    )
    print(
        _operator_note_text(
            "Come leggere i risultati",
            "Le sezioni A-E vengono ripetute per ciascun anno del piano. La sequenza segue la logica "
            "del modello: dai flussi necessari alla produzione si passa all'investimento e al prodotto "
            "finale, quindi al gross output, al capitale richiesto e infine agli indicatori sintetici "
            "di Harmony e occupazione.",
        ),
        file=rendered,
    )
    for yr in range(problem.TheLastYear - DEPRECIATION_HORIZON):
        display_result(
            yr,
            baseScenario.investmentsByTypeAndYear,
            problem.C,
            baseScenario.si,
            baseScenario.h,
            problem.headers,
            baseScenario.O[yr, :] * baseScenario.goal_fullfilment_ratio_vector[yr],
            problem.A,
            problem.labouravailable[yr],
            problem.g,
            baseScenario,
            out=rendered,
        )
    output_tables = rendered.getvalue()
    if print_output:
        print(output_tables, end="", flush=True)

    return {
        "problem": problem,
        "scenario": baseScenario,
        "iterations": iter_count,
        "stop_reason": stop_reason,
        "coefficient_of_variation": baseScenario.stdh / abs(baseScenario.meanh),
        "output_tables": output_tables,
    }


def default_data_paths():
    data = Path(__file__).resolve().parent / "data"
    return data / "jeuflows.csv", data / "jeucap.csv", data / "jeudep.csv", data / "jeulabtargs.csv"


def run_default(print_output=True):
    return solvePlanProblem(*default_data_paths(), print_output=print_output)


if __name__ == "__main__":
    run_default(print_output=True)
