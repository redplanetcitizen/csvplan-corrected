# csvplan_corrected 1.0.0

Pacchetto autonomo del solver corretto New Harmony derivato da `csvplan.jl`.
Comprende il motore, i quattro CSV dimostrativi a cinque settori, il navigatore
persistente, il riferimento legacy e i test. Non richiede file dal repository
di sviluppo o da Milestone E/F.

## Requisiti

- Python 3.10 o successivo;
- NumPy 1.24 o successivo;

Il pacchetto è autonomo rispetto a codice e dati, ma non incorpora un runtime
Python. Sul computer destinatario Python e NumPy devono essere disponibili.

## Avvio immediato su Windows

1. Estrarre interamente lo ZIP.
2. Aprire la cartella estratta.
3. Avviare `AVVIA_CSVPLAN_CORRECTED.bat`.

In alternativa, dal terminale aperto nella cartella:

```powershell
python -m pip install -r requirements.txt
python -m csvplan_corrected
```

Il navigatore mantiene input e risultati consultabili fino al comando di uscita
e alla conferma finale con INVIO.

## Esecuzione non interattiva

```powershell
python -m csvplan_corrected --defaults --batch --no-preview
```

Per fornire quattro CSV esterni:

```powershell
python -m csvplan_corrected `
  --flow percorso\flows.csv `
  --capital percorso\capital.csv `
  --depreciation percorso\depreciation.csv `
  --targets percorso\targets.csv
```

I quattro percorsi devono essere specificati insieme.

## Installazione come pacchetto

```powershell
python -m pip install .
csvplan-corrected --defaults
```

Uso da Python:

```python
from csvplan_corrected import SolverConfig, run_default

result = run_default(
    config=SolverConfig(strict=False, verbose=False)
)
scenario = result["scenario"]
print(result["stop_reason"], scenario.meanh)
```

## Verifica del pacchetto

Controllo rapido senza modificare i dati:

```powershell
python verify_package.py
```

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Su Windows si può anche usare `ESEGUI_TEST.bat`.

## Contenuto

- `csvplan_corrected/solver.py`: solver corretto;
- `csvplan_corrected/legacy.py`: riproduzione legacy usata soltanto per confronto;
- `csvplan_corrected/cli.py`: navigatore terminale;
- `csvplan_corrected/data/`: economia dimostrativa a cinque settori;
- `tests/`: test contabili, intertemporali, di regressione e dell'interfaccia;
- `MODEL_NOTES.md`: formule, correzioni e limiti interpretativi;
- `pyproject.toml`: installazione e comando `csvplan-corrected`.

## Stato del modello

Il solver conserva la struttura euristica New Harmony, ma corregge gli errori
di indicizzazione e contabilità riscontrati nel programma Julia storico. Ogni
scenario accettato rispetta i bilanci I/O, i vincoli di lavoro e capitale e la
positività dell'output netto. La procedura migliora monotonicamente l'obiettivo
lungo le correzioni accettate, ma non costituisce una prova di ottimo globale.

Il modulo `legacy.py` non è il motore consigliato. È incluso per rendere
riproducibile il confronto numerico con il comportamento storico.
