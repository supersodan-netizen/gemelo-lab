# GUÍA COMPLETA — Arranque y operación del sistema Gemelo-Lab

Esta guía te lleva de cero a tener el sistema completo funcionando: el laboratorio,
el bot autónomo de dos motores, la web y el ejecutor. Cada paso explica QUÉ hace y
POR QUÉ existe. Léela una vez entera y luego úsala como manual de referencia.

---

## 0. El mapa del sistema — qué es cada pieza

| Pieza | Dónde vive | Qué hace |
|---|---|---|
| **Laboratorio** (`main.py backtest/rejilla/...`) | Tu PC | Investiga: valida estrategias con datos históricos ANTES de usarlas |
| **Bot en vivo** (`main.py vivo`) | GitHub Actions (y tu PC si quieres) | Opera en papel cada hora de mercado con DOS motores en paralelo |
| **Sala de control** (`docs/index.html`) | GitHub Pages (web) | Muestra el estado de todo desde cualquier dispositivo |
| **Ejecutor** (`ejecutor.py`) | Tu PC (futuro: mini-servidor) | Traduce decisiones a órdenes en IBKR paper (fase 4, en espera) |
| **Gemelo Digital** (Apps Script) | Google Sheets | Sistema hermano e independiente; sirve de contraste (no se toca en esta guía) |

Los DOS MOTORES del bot: **PURO** (solo factores de precio — el validado por el
backtest, tu grupo de control) y **COMPLETO** (precio + analistas + fundamentales
+ sentimiento IA — el cerebro del Gemelo). Corren en paralelo con la misma caja:
en unos meses sus curvas dirán con datos si las capas extra aportan.

---

## PARTE A — Instalación en tu PC (15 minutos, una vez)

**A1. Instala Python.** Descarga 3.11+ de https://www.python.org/downloads/ y en
el instalador marca **"Add python.exe to PATH"** (imprescindible). Verifica
abriendo PowerShell: `python --version`.

**A2. Descomprime el proyecto** (el zip `gemelo-lab`) en una carpeta tuya, p. ej.
`C:\gemelo-lab`. Abre PowerShell EN esa carpeta (shift+clic derecho → "Abrir
ventana de PowerShell aquí").

**A3. Crea el entorno e instala dependencias.** El entorno virtual aísla las
librerías del proyecto del resto de tu sistema (higiene profesional):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Verás `(.venv)` delante del prompt: estás dentro del entorno. (Cada vez que
abras una consola nueva, repite solo la línea `activate`.)

**A4. Comprueba que TODO funciona antes de usarlo** — los tests no necesitan
internet y validan el motor entero (trailing al céntimo, contabilidad,
freno de caída, cooldown, seguridad del ejecutor…):

```
python main.py test
```

Debes ver 8 líneas con ✓ y `TODOS LOS TESTS PASAN ✅`. Si algo falla aquí,
no sigas: dime el error.

---

## PARTE B — El laboratorio: valida antes de creer

El laboratorio responde preguntas con datos. Orden recomendado la primera vez:

**B1. Descarga el histórico** (una vez; queda cacheado en `cache_datos/` para
que todos los experimentos usen EXACTAMENTE el mismo dataset — reproducibilidad):

```
python main.py descargar --anos 5
```

Baja 5 años de los 143 valores + benchmark desde Yahoo (2-5 min). `--forzar`
re-descarga si quieres datos más frescos.

**B2. Backtest** — ¿cómo se habría comportado la estrategia?:

```
python main.py backtest --anos 5
```

Imprime la tabla Motor vs Índice (CAGR, drawdown, Sharpe, Sortino, % aciertos,
fuera-de-muestra) y el desglose POR AÑO. Guarda `curva_backtest.csv` (ábrelo en
Excel si quieres la curva). **Primera misión:** compara estos números con la
hoja Backtest de tu Gemelo — deben parecerse en magnitud y dirección (no al
decimal: el ajuste de dividendos difiere un poco entre APIs).

**B3. Rejilla de robustez** — ¿la ventaja es real o sobreajuste?:

```
python main.py rejilla --anos 5
```

Corre 9 backtests (take-profit 25/60/200 × trailing 2/3/4) con los MISMOS datos
y scores. Si casi todas las celdas baten al índice → meseta → ventaja robusta.
Genera `rejilla.csv`.

**B4. Walk-forward** — ¿la ventaja vive en todos los tramos temporales?:

```
python main.py walkforward --anos 5
```

Backtests completos en ventanas rodantes de 2 años. Te dice cuántas ventanas
ganan al índice — la estabilidad temporal que un solo backtest no enseña.

**B5. Monte Carlo** — ¿qué rango de resultados es NORMAL a 4 meses?:

```
python main.py montecarlo --anos 5 --meses 4
```

5.000 caminos simulados (bootstrap de bloques pareados motor/índice). Te da
percentiles, probabilidad de acabar en pérdida y drawdown esperado. **Úsalo para
calibrar expectativas:** si a los 2 meses vas −8% pero el P25 es −9%, el sistema
va DENTRO de lo normal — esa lectura evita capitulaciones por ruido.

Regla de la casa (VISION.md): el laboratorio **valida, no optimiza** — elegir la
celda máxima de una rejilla es sobreajustar con la herramienta anti-sobreajuste.

---

## PARTE C — El bot en vivo (local): entiende un "paso"

```
python main.py vivo
```

Cada ejecución = UN paso del bot. Qué hace por dentro, en orden:
1. **Descarga datos frescos** de Yahoo (2 años, para indicadores; 3 reintentos;
   si falla del todo, NO opera — nunca con datos vacíos).
2. **Señales externas** para el motor COMPLETO: fundamentales/analistas (caché
   diaria en `fundamentales.json`) y sentimiento Gemini si hay clave (caché 12 h
   en `sentimiento.json`). Si faltan, su peso se excluye: nunca bloquean.
3. **Calcula scores de hoy** con el MISMO constructor del backtest (paridad).
4. **Para cada motor** (puro y completo): evalúa VENTAS de sus posiciones
   (trailing 3×ATR desde el máximo, stop −12%, score < 45), luego COMPRAS
   (score ≥ 60, régimen alcista, sin drawdown −20%, máx. 6 posiciones / 2 por
   sector, cooldown 2 días), dimensiona por volatilidad inversa, y ejecuta EN
   PAPEL con comisión 1€ + slippage 0,10%.
5. **Guarda su estado** (`estado_vivo.json`: posiciones, caja, P&L, cooldowns,
   historial) y **exporta la web** (`docs/estado.json`, ambos motores).

Comandos útiles: `--aportar 100` (ingresa 100€ ficticios en AMBOS motores, A/B
justo) · `--reset` (borrón y cuenta nueva) · `--publicar` (además hace git push).

---

## PARTE D — GitHub: autonomía total (20 minutos, una vez)

**D1. Crea el repositorio.** En github.com → New repository → nombre
`gemelo-lab` → **Public** (Pages gratis lo exige; el contenido no tiene claves
ni nada sensible — solo código y dinero ficticio).

**D2. Sube TODO el contenido** de la carpeta (incluida la carpeta `.github` —
es la que da la autonomía). Vía web: "uploading an existing file" y arrastra.
Vía git (mejor, permite `--publicar`):

```
git init && git add . && git commit -m "sistema gemelo-lab"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/gemelo-lab.git
git push -u origin main
```

**D3. Activa la web (Pages):** Settings → Pages → Source: *Deploy from a branch*
→ Branch `main`, carpeta `/docs` → Save. En ~1 minuto:
`https://TU_USUARIO.github.io/gemelo-lab/`.

**D4. Activa la autonomía (Actions):** pestaña **Actions** → habilita los
workflows. Luego Settings → Actions → General → Workflow permissions →
**"Read and write permissions"** → Save. Desde ese momento, GitHub ejecuta el
bot **cada hora de 09:30 a 22:30 (España), lunes a viernes**, y el propio bot
commitea su estado (cada decisión = un commit de `gemelo-bot`: auditoría gratis).
Botón **Run workflow** para lanzar un paso a mano (también desde la app móvil).

**D5. (Opcional) Sentimiento IA:** Settings → Secrets and variables → Actions →
New repository secret → nombre `GEMINI_API_KEY`, valor tu clave de
aistudio.google.com. Sin ella, el motor COMPLETO opera igual (sin la capa IA).

**D6. Verifica el primer run:** Actions → el workflow `bot-diario` → mira el log:
verás la descarga, "— Motor PURO —", "— Motor COMPLETO —" y el commit. Si sale
en rojo, el log dice exactamente dónde; tráemelo.

---

## PARTE E — La sala de control (web): qué es cada cosa

Abre tu URL de Pages. La web busca primero `estado.json` (el bot; insignia
**BOT PYTHON**) y si no existe pide la URL del Apps Script (insignia **HOJA**).

- **Selector PURO / COMPLETO:** cambia QUÉ motor ves (no cambia la estrategia —
  el experimento nunca se contamina). Tu elección se recuerda.
- **LED de frescura** (cabecera): verde pulsando = dato de <15 min; ámbar =
  envejeciendo; rojo = revisa la automatización. La edad exacta, al lado.
- **Instrumentos:** patrimonio, P&L realizado (neto de comisiones) con
  rentabilidad sobre lo aportado, nº de posiciones, edad del dato.
- **Banda de vuelo (test en vivo):** tu equity como aguja dentro de la banda
  ±1σ que predice el backtest. 🟢 en banda = el vivo se comporta como el modelo
  (aunque pierda dinero); 🟠 bajo −1σ = vigilar; 🔴 bajo −2σ = el vivo NO se
  parece al modelo → parar y repensar; 🔵 sobre banda = disfruta sin extrapolar.
  **Es el instrumento que decidirá el paso a dinero real.**
- **Curva de patrimonio:** la evolución del motor seleccionado.
- **Posiciones abiertas:** con precio de compra, actual, valor y P&L vivo.
- **Últimas operaciones:** cada una con su motivo (Trailing/Stop/Objetivo/Score)
  y el sello `alg v5.0` (reproducibilidad: sabrás qué versión decidió).
- **Radar de mercado:** los 10 mejores scores de hoy del universo (candidatos).
- **Sectores en cabeza:** la rotación sectorial actual.

La web se relee cada 60 s; el dato de fondo cambia con cada pasada del bot.

---

## PARTE F — Operación diaria y mantenimiento

**Tu ritual (2 minutos):** abre la web → LED verde → mira la banda de vuelo →
ojea operaciones nuevas. Semanalmente: compara PURO vs COMPLETO (el A/B).
A los ~3 meses: la revisión formal (regla de decisión en el README).

**Mantenimiento:** ninguno. El bot reintenta, degrada con elegancia y se cura
solo. Si un día falla una pasada (Yahoo, etc.), la siguiente la cubre.

**Pausar todo:** pestaña Actions → workflow `bot-diario` → "···" → Disable.
**Frenazo del ejecutor** (cuando exista): crea un archivo `KILL_SWITCH` en la
carpeta del repo local. **Cambiar parámetros:** edita `config.py` → commit →
push (queda auditado qué cambió y cuándo; sube `VERSION_ALGORITMO` si cambias
la estrategia).

---

## PARTE G — El ejecutor IBKR (fase 4, cuando llegue tu cuenta)

Hoy está construido, testeado y BLOQUEADO por defecto. Cuando tengas la cuenta
IBKR Pro (solicítala ya; el KYC tarda): instala IB Gateway en modo **paper**
(usuario `DU…`), habilita la API (puerto 4002), y:

```
pip install ib_async
python main.py ibkr-estado                      # apretón de manos: verás la cuenta DU y su millón simulado
$env:IBKR_EJECUTAR="SI"; python main.py vivo    # primer paso con órdenes reales-de-mentira
```

Triple seguridad activa siempre: sin `IBKR_EJECUTAR=SI` no hace nada (en Actions
esa variable no existe → la nube jamás envía órdenes); `KILL_SWITCH` detiene
todo; y si la cuenta no empieza por `DU` (paper), se desconecta sola. Techos de
10 órdenes/ciclo y 600€/orden; todo intento queda en `ordenes_ibkr.json`.
Limitaciones v1: cripto fuera (IBKR no la da en EUR para UE), unidades enteras.

---

## Solución de problemas

- **`python` no se reconoce** → reinstala marcando "Add to PATH" y abre consola nueva.
- **Los tests fallan** → captura el error y me lo pasas; no continúes.
- **`descargar` va lento o da errores 429** → Yahoo frenando; espera 10 min y reintenta.
- **La web da 404** → Pages tarda ~1 min tras activarse; revisa Branch `main` + `/docs`.
- **La web dice "sin conexión"** → aún no hay `docs/estado.json` (lanza un Run
  workflow) o, en modo HOJA, la URL del Apps Script no está implementada como
  "Cualquier usuario".
- **El workflow falla en el push** → Workflow permissions no está en "Read and write".
- **Un ticker sale sin datos** → Yahoo lo cambió o deslistó; dímelo y lo ajustamos
  en `config.py` (el motor mientras tanto lo ignora sin romperse).

## Glosario mínimo

**Score** nota 0-100 de atractivo (momentum+tendencia+rango 52s+fuerza+rotación;
el COMPLETO añade analistas/fundamental/IA) · **ATR** movimiento diario típico
de un valor · **Trailing stop** venta cuando el precio cae 3×ATR desde su máximo
(protege ganancias dejándolas correr) · **Drawdown** caída desde el pico ·
**Régimen** filtro "solo comprar con el S&P sobre su media de 200 días" ·
**Cooldown** 2 días sin recomprar lo vendido · **Banda ±1σ** rango donde debería
vivir tu equity si el modelo es cierto (~68% de los caminos) · **Slippage**
céntimos que pierdes al ejecutar vs el precio teórico (el bot los descuenta) ·
**A/B** los dos motores en paralelo que dirán con datos si las capas extra aportan.

---

*Dinero ficticio hasta que la banda de vuelo diga lo contrario. Esto es una
herramienta de apoyo a la decisión, no asesoramiento financiero. — v5.0*
