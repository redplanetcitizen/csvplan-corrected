from __future__ import annotations

"""Interactive terminal navigator for ``csvplan_corrected``.

The solver and the presentation layer remain separate.  This launcher keeps
the selected input tables and calculated I/O results available until the
operator explicitly confirms exit with ENTER.
"""

import argparse
import csv
import logging
import math
from pathlib import Path
import sys

import numpy as np

from . import solver as csvplan_corrected
from .terminal_ui import amount, percent_fraction, ratio, render_table


DESCRIPTIONS = (
    "Flow / input-output table",
    "Initial capital-stock matrix",
    "Capital depreciation-rate matrix",
    "Plan targets and labour supply",
)

SECTION_TITLES = (
    "Quadro annuale",
    "Flussi input-output",
    "Output finale, target e Harmony",
    "Capitale e investimenti per cella",
)


def _year_label(value: float) -> str:
    value = float(value)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def show_csv(path: Path, title: str) -> None:
    print(f"\n--- {title} ---")
    print(f"File: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    if not rows:
        print("(file vuoto)")
        return
    columns = max(len(row) for row in rows)
    widths = [
        max(len(row[col]) if col < len(row) else 0 for row in rows)
        for col in range(columns)
    ]
    for index, row in enumerate(rows):
        cells = [
            (row[col] if col < len(row) else "").rjust(widths[col])
            for col in range(columns)
        ]
        print(" | ".join(cells))
        if index == 0:
            print("-+-".join("-" * width for width in widths))


def render_selected_files(paths: tuple[Path, Path, Path, Path]) -> str:
    lines = ["INPUT FILES", "==========="]
    for index, (description, path) in enumerate(zip(DESCRIPTIONS, paths), 1):
        lines.append(f"{index}. {description}: {path}")
    return "\n".join(lines)


def show_all_inputs(paths: tuple[Path, Path, Path, Path]) -> None:
    print("\nINPUT DATA - OPERATOR REVIEW")
    print("============================")
    for description, path in zip(DESCRIPTIONS, paths):
        show_csv(path, description)


def ask_path(description: str, default: Path) -> Path:
    while True:
        raw = input(
            f"\n{description}\nDefault: {default}\n"
            "Path [INVIO = default]: "
        ).strip().strip('"')
        path = default if raw == "" else Path(raw).expanduser()
        if path.is_file():
            return path.resolve()
        print(f"ERRORE: file non trovato: {path}")


def choose_inputs() -> tuple[Path, Path, Path, Path]:
    defaults = tuple(Path(path).resolve() for path in csvplan_corrected.default_data_paths())
    print("\nNEW HARMONY - CSVPLAN CORRECTED")
    print("================================")
    print(render_selected_files(defaults))
    answer = input("\nUsare i quattro CSV inclusi nel pacchetto? [S/n]: ").strip().lower()
    if answer in ("", "s", "si", "sì", "y", "yes"):
        return defaults
    return tuple(
        ask_path(description, default)
        for description, default in zip(DESCRIPTIONS, defaults)
    )


def operator_review(
    paths: tuple[Path, Path, Path, Path],
) -> tuple[Path, Path, Path, Path] | None:
    while True:
        print("\n" + render_selected_files(paths))
        show_all_inputs(paths)
        print("\n" + "=" * 78)
        print("CONTROLLO OPERATORE - CALCOLO NON ANCORA AVVIATO")
        print("=" * 78)
        print("ESEGUI = avvia | R = riseleziona | Q = esce senza calcolare")
        command = input("\nComando: ").strip().upper()
        if command in ("ESEGUI", "RUN"):
            return paths
        if command in ("R", "RISELEZIONA", "RESELECT"):
            paths = choose_inputs()
            continue
        if command in ("Q", "QUIT", "ESCI"):
            return None
        print("Comando non riconosciuto.")


def _labels(problem) -> tuple[list[str], list[str]]:
    products = list(problem.headers[1:-1])
    return products, products + [problem.headers[-1]]


def render_summary(result: dict) -> str:
    scenario = result["scenario"]
    problem = result["problem"]
    rows = []
    for year in range(problem.horizon):
        report = scenario.constraint_report[year]
        rows.append(
            [
                _year_label(problem.years[year]),
                ratio(scenario.h[year]),
                ratio(scenario.lambdas[year]),
                amount(np.sum(scenario.net_output[year])),
                amount(np.sum(scenario.I[year])),
                percent_fraction(report.labour_used / report.labour_available),
                "OK" if report.compliant else "VIOLAZIONE",
            ]
        )
    summary = render_table(
        ["Anno", "Harmony", "Lambda", "Consumo netto", "Investimento", "Occupazione", "Vincoli"],
        rows,
    )
    indicators = render_table(
        ["Indicatore", "Valore"],
        [
            ["Iterazioni accettate", str(result["iterations"])],
            ["Motivo arresto", str(result["stop_reason"])],
            ["Harmony media", ratio(scenario.meanh)],
            ["Deviazione standard", ratio(scenario.stdh)],
            ["Coefficiente di variazione", ratio(result["coefficient_of_variation"])],
            ["Harmony totale", ratio(scenario.objective)],
            ["Capitale terminale limitante", "SI" if scenario.terminal_capital_limited else "NO"],
        ],
    )
    return (
        "CSVPLAN CORRECTED - RIEPILOGO\n"
        "================================\n"
        + indicators
        + "\n\nRISULTATI PER ANNO\n"
        + summary
    )


def render_overview(result: dict, year: int) -> str:
    scenario = result["scenario"]
    problem = result["problem"]
    report = scenario.constraint_report[year]
    end_stock = (1.0 - problem.dep) * scenario.S[year] + scenario.I[year]
    rows = [
        ["Harmony annuale", ratio(scenario.h[year])],
        ["Scala del piano ray (lambda)", ratio(scenario.lambdas[year])],
        ["Harmony media dell'orizzonte", ratio(scenario.meanh)],
        ["Gross output totale", amount(np.sum(scenario.O[year, : problem.products]))],
        ["Output finale totale", amount(np.sum(scenario.final_available[year]))],
        ["Consumo netto totale", amount(np.sum(scenario.net_output[year]))],
        ["Investimento totale", amount(np.sum(scenario.I[year]))],
        ["Stock iniziale totale", amount(np.sum(scenario.S[year]))],
        ["Stock finale totale", amount(np.sum(end_stock))],
        ["Lavoro disponibile", amount(report.labour_available)],
        ["Lavoro utilizzato", amount(report.labour_used)],
        ["Occupazione", percent_fraction(report.labour_used / report.labour_available)],
        ["Residuo massimo del bilancio", f"{report.max_flow_residual:.3e}"],
        ["Massimo eccesso di capitale richiesto", f"{report.max_capital_excess:.3e}"],
        ["Conformità complessiva", "OK" if report.compliant else "VIOLAZIONE"],
    ]
    return render_table(["Indicatore", "Valore"], rows)


def render_io_flows(result: dict, year: int) -> str:
    scenario = result["scenario"]
    problem = result["problem"]
    _, augmented_labels = _labels(problem)
    gross = scenario.O[year]
    flows = problem.A * gross[None, :]
    rows = []
    for row, label in enumerate(augmented_labels):
        rows.append(
            [label]
            + [amount(value) for value in flows[row]]
            + [amount(np.sum(flows[row]))]
        )
    return render_table(
        ["Input / settore"] + augmented_labels + ["Totale input"],
        rows,
    )


def render_final_output(result: dict, year: int) -> str:
    scenario = result["scenario"]
    problem = result["problem"]
    product_labels, _ = _labels(problem)
    inv = csvplan_corrected.investment_vector(scenario.I[year])
    rows = []
    for product, label in enumerate(product_labels):
        target = problem.g[year, product]
        net = scenario.net_output[year, product]
        fulfillment = "—" if target <= 0.0 else ratio(net / target)
        product_harmony = scenario.harmony_by_product[year, product]
        harmony_text = "—" if math.isnan(product_harmony) else ratio(product_harmony)
        rows.append(
            [
                label,
                amount(target),
                amount(scenario.final_available[year, product]),
                amount(inv[product]),
                amount(net),
                fulfillment,
                harmony_text,
            ]
        )
    return render_table(
        ["Prodotto", "Target", "Output finale", "Investimento", "Consumo netto", "Fulfillment", "Harmony"],
        rows,
    )


def render_capital_cells(result: dict, year: int) -> str:
    scenario = result["scenario"]
    problem = result["problem"]
    product_labels, _ = _labels(problem)
    required = csvplan_corrected._capital_requirement(problem, scenario.O[year])
    end_stock = (1.0 - problem.dep) * scenario.S[year] + scenario.I[year]
    rows = []
    for capital_good, capital_label in enumerate(product_labels):
        for user_sector, sector_label in enumerate(product_labels):
            start = scenario.S[year, capital_good, user_sector]
            need = required[capital_good, user_sector]
            rows.append(
                [
                    capital_label,
                    sector_label,
                    amount(start),
                    amount(need),
                    amount(start - need),
                    amount(scenario.I[year, capital_good, user_sector]),
                    amount(end_stock[capital_good, user_sector]),
                ]
            )
    return render_table(
        ["Bene capitale", "Settore utilizzatore", "Stock iniz.", "Richiesto", "Margine", "Investimento", "Stock finale"],
        rows,
    )


def render_year_section(result: dict, year: int, section: int) -> str:
    problem = result["problem"]
    heading = (
        f"CSVPLAN CORRECTED - ANNO {_year_label(problem.years[year])} "
        f"- {SECTION_TITLES[section].upper()}"
    )
    underline = "=" * len(heading)
    renderers = (render_overview, render_io_flows, render_final_output, render_capital_cells)
    notes = (
        "Sintesi dell'anno e controllo dei vincoli fisici e contabili.",
        "Ogni cella è A[i,j] moltiplicato per il gross output del settore j.",
        "Output finale = consumo netto + investimento, calcolato prodotto per prodotto.",
        "Il margine confronta lo stock disponibile all'inizio dell'anno con C[i,j]*o[j].",
    )
    return f"{heading}\n{underline}\n{notes[section]}\n\n{renderers[section](result, year)}"


def render_comparison(comparison: dict) -> str:
    return render_table(
        ["Indicatore", "Valore"],
        [
            ["Anni confrontati", str(comparison["years_compared"])],
            ["Harmony media corrected", ratio(comparison["corrected_mean_harmony"])],
            ["Harmony media legacy", ratio(comparison["legacy_mean_harmony"])],
            ["Iterazioni corrected", str(comparison["corrected_iterations"])],
            ["Iterazioni legacy", str(comparison["legacy_iterations"])],
            ["Massima differenza net output", amount(comparison["max_abs_net_output_difference"])],
            ["Output negativi nascosti nel legacy", "SI" if comparison["legacy_negative_outputs_hidden"] else "NO"],
        ],
    )


def _clear_terminal(enabled: bool) -> None:
    if enabled and sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def navigation_loop(
    result: dict,
    paths: tuple[Path, Path, Path, Path],
    *,
    clear_screen: bool = True,
) -> None:
    year = 0
    section = 0
    comparison_cache: dict | None = None
    while True:
        _clear_terminal(clear_screen)
        print(render_year_section(result, year, section))
        print("\n" + "-" * 96)
        print(
            "INVIO = sezione successiva | N/P = anno successivo/precedente | "
            "1-5 = vai all'anno"
        )
        print("S = riepilogo | I = input | L = confronto legacy | Q = uscita")
        command = input("\nComando: ").strip().upper()

        if command == "":
            section += 1
            if section >= len(SECTION_TITLES):
                section = 0
                year = (year + 1) % result["problem"].horizon
            continue
        if command in ("N", "+"):
            year = (year + 1) % result["problem"].horizon
            section = 0
            continue
        if command in ("P", "-"):
            year = (year - 1) % result["problem"].horizon
            section = 0
            continue
        if command.isdigit() and 1 <= int(command) <= result["problem"].horizon:
            year = int(command) - 1
            section = 0
            continue
        if command == "S":
            _clear_terminal(clear_screen)
            print(render_summary(result))
            input("\nPremi INVIO per tornare alla navigazione...")
            continue
        if command == "I":
            _clear_terminal(clear_screen)
            print(render_selected_files(paths))
            show_all_inputs(paths)
            input("\nPremi INVIO per tornare alla navigazione...")
            continue
        if command == "L":
            _clear_terminal(clear_screen)
            if comparison_cache is None:
                print("Calcolo del riferimento legacy in corso...", flush=True)
                from . import legacy as csvplan_legacy

                legacy_result = csvplan_legacy.solvePlanProblem(*paths, print_output=False)
                comparison_cache = csvplan_corrected.compare_with_legacy(result, legacy_result)
            print("\nCONFRONTO CORRECTED / LEGACY")
            print("============================")
            print(render_comparison(comparison_cache))
            input("\nPremi INVIO per tornare alla navigazione...")
            continue
        if command in ("Q", "QUIT", "ESCI"):
            print("\n" + "=" * 78)
            print("FINE CONSULTAZIONE - DATI ANCORA DISPONIBILI")
            print("=" * 78)
            input("Premi INVIO per chiudere definitivamente il programma...")
            return
        print("Comando non riconosciuto.")


def batch_display(result: dict) -> None:
    print(render_summary(result))
    for year in range(result["problem"].horizon):
        for section in range(len(SECTION_TITLES)):
            print("\n\n" + render_year_section(result, year, section))


def _parse_paths(args, parser) -> tuple[Path, Path, Path, Path]:
    explicit = (args.flow, args.capital, args.depreciation, args.targets)
    if any(path is not None for path in explicit):
        if not all(path is not None for path in explicit):
            parser.error("Specificare insieme --flow --capital --depreciation --targets")
        paths = tuple(Path(path).expanduser().resolve() for path in explicit)
        missing = [str(path) for path in paths if not path.is_file()]
        if missing:
            parser.error("File non trovati: " + ", ".join(missing))
        return paths
    if args.defaults or args.batch:
        return tuple(Path(path).resolve() for path in csvplan_corrected.default_data_paths())
    return choose_inputs()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Navigatore persistente dei dati I/O prodotti da csvplan_corrected."
    )
    parser.add_argument("--defaults", action="store_true", help="preseleziona i CSV inclusi")
    parser.add_argument("--batch", action="store_true", help="stampa tutte le schermate senza pause")
    parser.add_argument("--no-preview", action="store_true", help="non mostra i CSV prima del calcolo")
    parser.add_argument("--no-clear", action="store_true", help="non pulisce il terminale fra le schermate")
    parser.add_argument("--strict", action="store_true", help="solleva eccezione su vincolo terminale")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=3000)
    parser.add_argument("--flow", type=Path)
    parser.add_argument("--capital", type=Path)
    parser.add_argument("--depreciation", type=Path)
    parser.add_argument("--targets", type=Path)
    args = parser.parse_args()

    paths = _parse_paths(args, parser)
    if args.batch:
        print(render_selected_files(paths))
        if not args.no_preview:
            show_all_inputs(paths)
    else:
        reviewed = operator_review(paths)
        if reviewed is None:
            print("Esecuzione annullata. Nessun calcolo eseguito.")
            return
        paths = reviewed

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    print("\nCalcolo csvplan_corrected in corso...", flush=True)
    config = csvplan_corrected.SolverConfig(
        strict=args.strict,
        verbose=args.verbose,
        max_iterations=args.max_iterations,
    )
    result = csvplan_corrected.solve_problem(*paths, config=config)
    print(
        f"Calcolo terminato: {result['iterations']} iterazioni accettate, "
        f"motivo={result['stop_reason']}.",
        flush=True,
    )

    if args.batch:
        batch_display(result)
    else:
        navigation_loop(result, paths, clear_screen=not args.no_clear)


if __name__ == "__main__":
    main()
