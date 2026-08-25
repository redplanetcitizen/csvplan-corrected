# Note metodologiche

## Funzione di armonia

Il pacchetto usa la forma fratta:

```text
H(x) = x / (1.1 + x)
H^-1(h) = 1.1 h / (1 - h)
```

L'armonia annuale è il minimo fra i prodotti con target strettamente positivo.
I prodotti con target nullo non entrano nel rapporto di fulfillment, ma il loro
output netto deve rimanere non negativo.

## Flussi e investimento

Per ogni anno il programma risolve:

```text
o = (I - A)^-1 (lambda g + i)
```

dove `i` è il vettore dei beni d'investimento aggregato per bene produttore.
L'investimento resta memorizzato come tensore:

```text
anno × bene-capitale-produttore × settore-utilizzatore
```

La sottrazione dell'investimento dall'output finale conserva quindi l'identità
dei beni e non usa l'indicizzazione lineare del programma legacy.

## Capitale

Lo stock segue esattamente:

```text
S[t+1] = (1 - D) * S[t] + I[t]
```

Un investimento prodotto nell'anno sorgente entra nella capacità disponibile
all'inizio dell'anno successivo. La funzione di deprezzamento inverso compensa
soltanto gli anni compresi fra ingresso nello stock e anno destinazione.

Il fabbisogno di capitale è valutato cella per cella come:

```text
C[i,j] * o[j]
```

## Lavoro e positività

La produzione destinata all'investimento è una domanda prioritaria nello stesso
anno in cui viene prodotta. Il massimo `lambda` di consumo viene calcolato dopo
avere impegnato lavoro e capitale per tale produzione. Un candidato non viene
accettato se l'investimento da solo è irrealizzabile o se produce output netto
negativo.

## Anno terminale

La sostituzione terminale usa:

```text
o = (I - A - D)^-1 (q g)
```

e applica insieme il limite di lavoro e quello di capitale. In modalità non
rigorosa il solver segnala se lo stock terminale non consente il pieno impiego;
in modalità rigorosa solleva `TerminalCapitalConstraint`.

## Ricerca intertemporale

La procedura:

1. ordina gli anni correggibili per armonia crescente;
2. prova ogni anno, non soltanto il minimo assoluto;
3. prova tutti gli anni sorgente precedenti;
4. accetta soltanto un aumento dell'armonia totale;
5. riduce il passo quando nessun candidato è ammissibile;
6. aumenta moderatamente il passo dopo correzioni non oscillanti;
7. arresta la ricerca alla soglia di convergenza, al passo minimo o al limite
   massimo di iterazioni.

Questo è un algoritmo euristico monotono. Non garantisce l'ottimo globale.

## Differenza dal modulo legacy

`legacy.py` conserva intenzionalmente il comportamento numerico storico,
compresi gli effetti degli errori originari, per permettere test di regressione.
Non deve essere usato come sostituto del solver corretto.

