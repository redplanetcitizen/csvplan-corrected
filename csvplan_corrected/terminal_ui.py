"""Terminal-only presentation helpers.

These functions format values for operator display. They never alter solver data.
"""
from __future__ import annotations


def amount(value, decimals=2):
    x = float(value)
    if abs(x) < 0.5 * 10 ** (-decimals):
        x = 0.0
    return f"{x:,.{decimals}f}"


def ratio(value, decimals=5):
    x = float(value)
    if abs(x) < 0.5 * 10 ** (-decimals):
        x = 0.0
    return f"{x:.{decimals}f}"


def percent_fraction(value, decimals=2):
    return f"{100.0 * float(value):.{decimals}f}%"


def percent_value(value, decimals=2):
    return f"{float(value):.{decimals}f}%"


def render_table(headers, rows, right_align=None):
    headers = [str(x) for x in headers]
    rows = [[str(x) for x in row] for row in rows]
    ncols = len(headers)

    if right_align is None:
        right_align = set(range(1, ncols))
    else:
        right_align = set(right_align)

    widths = [len(headers[i]) for i in range(ncols)]
    for row in rows:
        for i in range(ncols):
            cell = row[i] if i < len(row) else ""
            widths[i] = max(widths[i], len(cell))

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def fmt_row(row):
        cells = []
        for i, width in enumerate(widths):
            cell = row[i] if i < len(row) else ""
            if i in right_align:
                cells.append(" " + cell.rjust(width) + " ")
            else:
                cells.append(" " + cell.ljust(width) + " ")
        return "|" + "|".join(cells) + "|"

    lines = [border, fmt_row(headers), border]
    lines.extend(fmt_row(row) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def final_operator_pause():
    print("\n" + "=" * 72)
    print("FINE ELABORAZIONE - RISULTATI DISPONIBILI")
    print("=" * 72)
    print(
        "I risultati restano visibili nella finestra.\n"
        "Puoi usare la barra di scorrimento del terminale per consultarli."
    )
    input("\nPremi INVIO solo quando vuoi chiudere il programma...")


def operator_note(title, text, width=96):
    """Print a compact explanatory note for the operator."""
    import textwrap

    print("\n" + "-" * width)
    print(f"NOTA DI LETTURA - {title}")
    print("-" * width)
    paragraphs = str(text).strip().split("\n")
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            print()
            continue
        print(
            textwrap.fill(
                paragraph,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
