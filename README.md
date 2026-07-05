# Laboratorio Gemelo de Mercado (Python)

Herramienta profesional de investigación para la estrategia del Gemelo Digital.
No sustituye al Gemelo (Apps Script): **lo complementa**. El Gemelo es el banco de
pruebas en vivo; el laboratorio es donde se investiga con rigor de ingeniería.

## Filosofía: paridad antes que potencia

El motor de este laboratorio es un **port fiel** del backtest del Gemelo — mismas
fórmulas (pesos del score, ventanas, varianza poblacional), mismo trinquete del
trailing, mismo freno de caída con reanclaje, misma prohibición de recomprar el día
de la venta, mismas comisiones y slippage. Dos implementaciones independientes que
dan lo mismo = confianza real en ambas (validación cruzada). Solo tras la paridad
tiene sentido usar la potencia (Monte Carlo, walk-forward, barridos masivos).

El test del trailing (`tests/test_motor.py::test_trailing_exacto`) usa **los mismos
números** que el test que validó el Gemelo (vende a 117,5 → 1175 € con 2×ATR; a
110 → 1100 € con 3×ATR). Ambos motores lo pasan.

## Instalación (Windows)

1. Instala Python 3.11+ desde https://www.python.org/downloads/ marcando
   **"Add python.exe to PATH"** en el instalador.
2. Abre PowerShell en la carpeta del proyecto y crea el entorno:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Comprueba que todo funciona (tests sin red):
   ```
   python main.py test
   ```

## Uso

```
python main.py descargar --anos 5          # baja el histórico (caché en cache_datos/)
python main.py backtest  --anos 5          # backtest con tu config validada (TP200/ATR3)
python main.py rejilla   --anos 5          # robustez de parámetros (9 combos, en segundos)
python main.py walkforward --anos 5        # estabilidad en ventanas rodantes de 2 años
python main.py montecarlo --anos 5 --meses 4   # distribución de resultados a 4 meses
```

Los resultados se guardan también en CSV (`curva_backtest.csv`, `rejilla.csv`,
`walkforward.csv`) para analizarlos en Excel si quieres.

## Protocolo de paridad (primera misión)

1. `python main.py descargar --anos 5` y luego `python main.py backtest --anos 5`.
2. Compara con la hoja Backtest del Gemelo (mismos años).
3. **Qué debe coincidir:** el orden de magnitud del CAGR/drawdown/Sharpe, la forma
   de la meseta en la rejilla, la dirección de las conclusiones.
4. **Qué NO va a coincidir al decimal, y por qué:** aunque la fuente es la misma
   (Yahoo, cierres ajustados), el ajuste por dividendos/splits, los festivos por
   mercado y la alineación de fechas difieren ligeramente entre la API v8 (Gemelo)
   y yfinance. Diferencias de unos pocos puntos porcentuales en 5 años son normales.
   Si vieras diferencias grandes (p. ej. el doble de CAGR, o drawdowns sin relación),
   eso sí sería una señal de investigación.

## Estructura

```
config.py     universo (143, extraído del Codigo.gs) + parámetros validados
datos.py      descarga Yahoo (yfinance) con caché CSV reproducible
motor.py      indicadores + score + frames + replay (el port fiel)
metricas.py   CAGR, drawdown, Sharpe/Sortino (ddof=0, rf=0), tabla por año
analisis.py   rejilla, walk-forward, Monte Carlo (bloques pareados motor/índice)
main.py       CLI
tests/        tests unitarios con datos sintéticos (sin red)
```

## Hoja de ruta

- **F3.1 (ahora):** paridad con el Gemelo — correr el protocolo de arriba.
- **F3.2:** usar la potencia: Monte Carlo para calibrar expectativas del test en
  vivo; walk-forward para ver la estabilidad temporal; rejillas más finas.
- **F3.3 (solo tras paridad):** investigar mejoras de estrategia con disciplina
  (una hipótesis → un experimento → aceptar el veredicto de los datos).
- **F4:** ejecución. Trade Republic no tiene API pública; si algún día el bot debe
  ejecutar solo con dinero real, hará falta un broker con API (p. ej. IBKR).

## Nota honesta

Este laboratorio valida y calibra expectativas; no predice el futuro. La regla de
la casa: los análisis **validan, no optimizan** — elegir la celda máxima de una
rejilla es sobreajustar con la herramienta anti-sobreajuste. El árbitro final
sigue siendo el test en vivo.

## Panel web (GitHub Pages) — `docs/index.html`

Sala de control de solo lectura: patrimonio, posiciones con P&L, operaciones (con
aviso de propuestas pendientes), radar de scores, sectores fuertes, curva de
patrimonio y la **banda de vuelo** del test en vivo (tu equity contra la banda
±1σ del modelo). Se conecta a la API que el Gemelo ya expone (doGet/JSONP).

**Publicar el repo y activar la web:**
1. Crea un repositorio en GitHub (puede llamarse `gemelo-lab`) y sube TODO el
   contenido de esta carpeta (el `.gitignore` ya excluye datos locales).
2. En el repo: **Settings → Pages → Source: Deploy from a branch →
   Branch `main`, carpeta `/docs` → Save.** En un minuto tendrás
   `https://TU_USUARIO.github.io/gemelo-lab/`.
3. En el editor de Apps Script del Gemelo: **Implementar → Nueva implementación →
   Aplicación web** (Ejecutar como: tú · Acceso: **Cualquier usuario**). Copia la
   URL `/exec`.
4. Abre tu página de GitHub Pages y pega esa URL cuando te la pida (se guarda
   solo en tu navegador, nunca en el repo).

**Frecuencia de los datos, con honestidad:** el panel se relee cada 60 s, pero el
dato de fondo es el del Gemelo — precios cada ~10 minutos (PRECIO_CADA_MIN) e
indicadores diarios. Para una estrategia de swing con velas diarias, esa es la
granularidad correcta; "tiempo real" tick a tick requeriría feeds de pago y no
cambiaría ninguna decisión del motor. El LED de cabecera te dice la edad exacta
del dato en todo momento.

**Privacidad:** GitHub Pages en cuentas gratuitas exige repo público — el código
no contiene claves ni datos personales (la URL de tu API vive solo en tu
navegador), y el `.gitignore` evita subir la caché de datos. Aun así, quien
tenga tu URL /exec podría leer el estado del gemelo: no la publiques.

## Modo VIVO — el bot en papel, autosuficiente

`python main.py vivo` ejecuta UN paso de decisión del bot con el **mismo motor
validado** del backtest (hay un test que demuestra que la simulación por pasos
con estado persistente reproduce exactamente la continua). El bot mantiene su
propio estado en `estado_vivo.json` (líquido, posiciones, P&L neto de comisiones,
operaciones, curva) y exporta `docs/estado.json`, que el panel web lee
directamente — **sin depender del Apps Script**.

```
python main.py vivo                    # primer uso: crea el bot con 2000 € ficticios
python main.py vivo --aportar 100      # registrar una aportación
python main.py vivo --publicar         # además, git commit+push -> la web se actualiza
python main.py vivo --reset            # empezar de cero
```

**Operativa recomendada:** prográmalo a diario tras el cierre USA (22:30 hora
española) con el Programador de tareas de Windows:
`Programa: python · Argumentos: main.py vivo --publicar · Iniciar en: carpeta del repo`.
Una decisión al día es coherente con la estrategia (velas diarias) y con el backtest.

**La web elige su fuente sola:** si existe `docs/estado.json` (bot Python) lo usa
y muestra la insignia **BOT PYTHON**; si no, pide la URL del Apps Script y muestra
**HOJA**. Puedes tener ambos mundos: el Gemelo en la hoja y el bot en el repo.

**Honestidad de datos:** los precios del modo vivo vienen de Yahoo vía yfinance
(retardo típico de ~15 min, suficiente para decisiones diarias). El bot decide
con el último cierre disponible; no es tick a tick ni lo necesita. Dinero
ficticio; sin conexión a broker todavía (eso es la fase 4 con IBKR paper).

## Autonomía total — el bot corre solo (GitHub Actions)

El repo incluye `.github/workflows/bot.yml`: GitHub ejecuta el bot en SUS
servidores **cada hora durante las horas de mercado** (09:30–22:30 hora española,
de la apertura europea al cierre USA, lunes-viernes), sin tu PC y sin coste
(gratis e ilimitado en repos públicos). Es la misma postura en vivo que el
Gemelo de la hoja: decisión horaria, máximos del trailing frescos cada pasada
(el trinquete persiste en el estado), y **cooldown de 2 días** tras cada venta
para no recomprar por churn — todo cubierto por tests. El propio bot
commitea su estado al repo — cada decisión queda auditada en el historial de
commits — y GitHub Pages sirve el `estado.json` nuevo: la web se actualiza sola.

**Para activarlo:** sube el repo con la carpeta `.github/` incluida; en la
pestaña **Actions** acepta habilitar los workflows; y comprueba en
**Settings → Actions → General → Workflow permissions** que esté en
**"Read and write permissions"**. Nada más. El botón **Run workflow** te permite
lanzar un paso a mano cuando quieras — también desde la app móvil de GitHub.

**Honestidades de esta autonomía:** (1) el cron de Actions no es exacto al
minuto (puede retrasarse unos minutos en horas punta) — irrelevante para
decisiones diarias; (2) si Yahoo rechaza la descarga, el bot reintenta 3 veces
y, si aun así falla, NO opera (nunca con datos vacíos) y lo vuelve a intentar
al día siguiente; (3) corre lunes-viernes — la gestión de cripto en fin de
semana queda fuera por ahora (el motor vivo de la hoja sí la cubre); (4) el
estado del bot (dinero ficticio) queda visible en el repo público — es el
precio de Pages gratis; no hay nada sensible en él. Para la fase 4 (IBKR paper)
harán falta sesiones persistentes y ahí el hogar natural será una mini-máquina
siempre encendida (Raspberry Pi o VPS); para el bot en papel diario, Actions es
la solución perfecta.

## Dos motores en paralelo — el experimento A/B dentro del bot

Desde esta versión el bot lleva DOS carteras simultáneas con los mismos datos y
la misma caja: **PURO** (el motor validado por el backtest: solo factores de
precio) y **COMPLETO** (el cerebro del Gemelo: precio + analistas + fundamentales
+ sentimiento IA, con paridad matemática demostrada contra scoreStock). Cada una
tiene su estado, su P&L, su cooldown y su curva. En la web, el selector
PURO/COMPLETO cambia **la vista**, no la estrategia — así el experimento nunca se
contamina y en unos meses las dos curvas responden con datos si las capas extra
aportan, restan o dan igual.

**Señales del COMPLETO:** fundamentales/analistas vía yfinance (caché diaria en
`fundamentales.json`, commiteada; si un valor no tiene dato, su peso se excluye)
y sentimiento vía Gemini si añades el secret `GEMINI_API_KEY` en GitHub
(Settings → Secrets and variables → Actions). Sin clave, el COMPLETO opera con
precio + analistas + fundamentales (sentimiento neutro). Degradación elegante
siempre: una señal caída jamás detiene al bot.

**Regla de decisión (formalizada):** revisar a los ~3 meses. Si COMPLETO bate a
PURO de forma consistente, las capas aportan (y con evidencia se llevan también
a real). Si empatan o pierde, el motor puro gana por simplicidad. En ambos casos,
se sabe — que es el objetivo.

## Fase 4 — Ejecutor IBKR (paper), listo para enchufar

`ejecutor.py` traduce las decisiones del motor PURO a órdenes reales en la cuenta
**paper** de Interactive Brokers. El cerebro no cambia: solo se añade el brazo.

**Triple seguridad, verificada con tests:** (1) sin `IBKR_EJECUTAR=SI` en el
entorno NO hace nada (en GitHub Actions esa variable no existe → el bot en la
nube jamás envía órdenes); (2) crear un archivo llamado `KILL_SWITCH` en la
carpeta detiene toda ejecución al instante, sin tocar código; (3) tras conectar,
la cuenta debe empezar por `DU` (paper de IBKR) — operar en real exigiría además
DOS llaves explícitas que hoy no existen. Límites duros de órdenes por ciclo y
de importe por orden, y auditoría de todo intento en `ordenes_ibkr.json`.

**Puesta en marcha cuando tengas la cuenta IBKR Pro:**
1. Instala IB Gateway, entra en modo PAPER (usuario `DU…`), habilita la API
   (Configuración → API → Enable ActiveX and Socket Clients, puerto 4002).
2. `pip install ib_async` y comprueba la conexión: `python main.py ibkr-estado`
   (verás la cuenta DU… y su millón simulado).
3. Lanza un paso con ejecución: `IBKR_EJECUTAR=SI python main.py vivo`
   (en Windows PowerShell: `$env:IBKR_EJECUTAR="SI"; python main.py vivo`).
4. Concilia: `python main.py ibkr-estado` vs la sala de control.

**Limitaciones honestas de la v1:** cripto fuera (IBKR no la ofrece en EUR para
cuentas UE; sigue en el papel interno), unidades enteras (las fraccionadas de
valores caros se omiten y se registra el porqué), órdenes a mercado. El paso a
dinero real NO es un cambio de código sino una decisión: la tomará el cuaderno
vivo-vs-esperado a los ~3 meses, y aun entonces, con dinero pequeño.

## Experimento: ¿aporta el VOLUMEN? (tu hipótesis de "psicología de mercado")

La intuición "el contexto de un nivel importa" tiene una versión medible: el
volumen como confirmación de participación. Está implementado como factor
OPCIONAL (`W_VOLUMEN`, 0 por defecto → el motor validado no cambia) y con su
propio A/B riguroso:

```
python main.py descargar --anos 5      # ahora también cachea el volumen
python main.py volumen --anos 5        # corre la MISMA rejilla SIN vs CON volumen
```

Compara la meseta entera (no una celda: eso sería sobreajuste) y da veredicto:
🟢 aporta (candidato a incorporar), 🔴 resta (descartado con razón documentada),
🟡 neutro/redundante con el momentum. Regla del proyecto: si aporta con evidencia,
entra y sube `VERSION_ALGORITMO`; si no, se queda fuera y hemos aprendido algo.
Apuesta previa honesta: probablemente 🟡 — el momentum ya captura buena parte de
lo que el volumen confirmaría. Pero se decide con datos, no con la apuesta.
