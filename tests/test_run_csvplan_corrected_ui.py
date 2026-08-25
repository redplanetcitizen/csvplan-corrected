from __future__ import annotations

from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from csvplan_corrected import cli as ui
from csvplan_corrected import solver as csvplan_corrected


def small_result():
    return csvplan_corrected.run_default(
        config=csvplan_corrected.SolverConfig(strict=False, max_iterations=2)
    )


class TerminalUiTests(unittest.TestCase):
    def test_all_navigation_sections_render(self):
        result = small_result()
        for section in range(len(ui.SECTION_TITLES)):
            screen = ui.render_year_section(result, 0, section)
            self.assertIn("ANNO 1", screen)
            self.assertIn(ui.SECTION_TITLES[section].upper(), screen)
        self.assertIn("RIEPILOGO", ui.render_summary(result))

    def test_navigation_remains_open_until_final_enter(self):
        result = small_result()
        commands = iter(["", "Q", ""])
        output = io.StringIO()
        with patch("builtins.input", side_effect=lambda _prompt="": next(commands)):
            with redirect_stdout(output):
                ui.navigation_loop(
                    result,
                    tuple(csvplan_corrected.default_data_paths()),
                    clear_screen=False,
                )
        text = output.getvalue()
        self.assertIn("FLUSSI INPUT-OUTPUT", text)
        self.assertIn("FINE CONSULTAZIONE", text)


if __name__ == "__main__":
    unittest.main()
