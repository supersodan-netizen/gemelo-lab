# GUÍA DE INSTALACIÓN COMPLETA — Sistema Gemelo-Lab con VS Code

> Guía para principiante absoluto. No se da nada por hecho: cada clic, cada
> comando y cada ventana están explicados. Sigue las partes EN ORDEN. Si un paso
> no coincide con lo que ves en tu pantalla, para y anótalo.

**Tiempo total:** ~45 minutos la primera vez. Luego el sistema funciona solo.

**Lo que vas a conseguir:** un sistema de inversión en papel (dinero ficticio)
que investiga con datos históricos, opera solo en la nube cada hora, y se ve
desde una web en tu móvil. Todo gratis.

---

## ÍNDICE

- **Parte 1** — Instalar las herramientas base (VS Code, Python, Git)
- **Parte 2** — Abrir el proyecto en VS Code
- **Parte 3** — Preparar el entorno de Python dentro de VS Code
- **Parte 4** — Comprobar que todo funciona
- **Parte 5** — Usar el laboratorio (investigar con datos)
- **Parte 6** — Entender el bot en vivo
- **Parte 7** — Subir a GitHub y activar la autonomía
- **Parte 8** — La web (sala de control)
- **Parte 9** — Cada funcionalidad explicada
- **Parte 10** — Problemas frecuentes
- **Glosario**

---

# PARTE 1 — Instalar las herramientas base

Necesitas tres programas. Instálalos en este orden.

## 1.1 · Visual Studio Code (el editor)

VS Code es el programa donde verás y ejecutarás todo el proyecto.

1. Ve a **https://code.visualstudio.com**
2. Pulsa el botón azul grande **"Download for Windows"** (o Mac/Linux según tu equipo).
3. Abre el archivo descargado (`VSCodeUserSetup-....exe`).
4. Acepta el acuerdo y pulsa **Siguiente** en todas las pantallas. **IMPORTANTE:**
   en la pantalla "Seleccionar tareas adicionales", marca las casillas:
   - ✅ "Agregar la acción «Abrir con Code»..." (las dos, archivo y directorio)
   - ✅ "Agregar a PATH"
5. Pulsa **Instalar** y luego **Finalizar**. VS Code se abrirá.

## 1.2 · Python (el motor que ejecuta el código)

1. Ve a **https://www.python.org/downloads/**
2. Pulsa el botón amarillo **"Download Python 3.12.x"** (o la versión 3.11+ que aparezca).
3. Abre el archivo descargado (`python-3.12....exe`).
4. **⚠️ EL PASO MÁS IMPORTANTE DE TODA LA GUÍA:** en la PRIMERA pantalla del
   instalador, ABAJO, marca la casilla:
   - ✅ **"Add python.exe to PATH"**

   Si no marcas esto, nada funcionará después. Es fácil pasarlo por alto.
5. Pulsa **"Install Now"**.
6. Cuando termine, pulsa **"Disable path length limit"** si aparece (es útil), y **Close**.

## 1.3 · Git (para subir el proyecto a la nube)

Git es la herramienta que sincroniza tu proyecto con GitHub.

1. Ve a **https://git-scm.com/download/win** (en Mac: `git-scm.com/download/mac`).
2. La descarga empieza sola. Abre el archivo (`Git-....exe`).
3. Pulsa **Siguiente** en TODAS las pantallas (los valores por defecto son
   correctos; son muchas pantallas, no te preocupes, siguiente siempre).
4. Pulsa **Install** y **Finish**.

## 1.4 · Reiniciar el ordenador

Cierra todo y **reinicia el ordenador**. Esto asegura que Windows reconozca
Python y Git. No te saltes este paso: evita el 90% de los problemas.

---

# PARTE 2 — Abrir el proyecto en VS Code

## 2.1 · Descomprimir el proyecto

1. Localiza el archivo **`gemelo-lab.zip`** que te pasé (probablemente en Descargas).
2. Haz **clic derecho** sobre él → **"Extraer todo..."** → elige una carpeta fácil
   de encontrar, por ejemplo tu carpeta de usuario. Pulsa **Extraer**.
3. Se creará una carpeta llamada **`gemelo-lab`** con archivos dentro
   (`main.py`, `motor.py`, `config.py`, etc.). Anota dónde está.

## 2.2 · Abrir la carpeta en VS Code

1. Abre **VS Code**.
2. Menú **Archivo → Abrir carpeta...** (o `Ctrl+K` y luego `Ctrl+O`).
3. Navega hasta la carpeta **`gemelo-lab`**, selecciónala y pulsa **"Seleccionar carpeta"**.
4. Si aparece un aviso "¿Confías en los autores de esta carpeta?", pulsa
   **"Sí, confío en los autores"**.
5. A la izquierda verás la lista de archivos del proyecto. **Ya está abierto.**

## 2.3 · Instalar la extensión de Python en VS Code

1. En la barra vertical de la IZQUIERDA, pulsa el icono de **Extensiones**
   (son cuatro cuadraditos, uno separado). O pulsa `Ctrl+Shift+X`.
2. En el buscador que aparece, escribe **`Python`**.
3. El primer resultado es **"Python"** de **Microsoft** (tiene millones de
   descargas). Pulsa el botón azul **"Install"**.
4. Espera unos segundos. Se instalará también "Pylance" automáticamente. Listo.

---

# PARTE 3 — Preparar el entorno de Python dentro de VS Code

Aquí abrirás la **terminal** (una consola de texto DENTRO de VS Code) y prepararás
las librerías. Suena técnico pero son 3 comandos.

## 3.1 · Abrir la terminal en VS Code

1. Menú superior **Terminal → Nueva terminal** (o pulsa `` Ctrl+Ñ `` / `` Ctrl+` ``).
2. Abajo aparecerá un panel con texto y un cursor parpadeando. Fíjate que la ruta
   que aparece termina en **`gemelo-lab`** — eso confirma que estás en la carpeta
   correcta. Aquí escribirás los comandos.

> **Nota Windows/PowerShell:** si al escribir el primer comando ves un error rojo
> sobre "ejecución de scripts está deshabilitada", copia y pega esta línea, pulsa
> Enter, escribe `S` y Enter, y continúa:
> ```
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

## 3.2 · Crear el "entorno virtual"

Un entorno virtual es una cajita aislada donde se instalan las librerías del
proyecto sin ensuciar tu sistema. Escribe (o copia y pega) esta línea en la
terminal y pulsa **Enter**:

```
python -m venv .venv
```

Tarda unos segundos y no muestra nada especial. Se habrá creado una carpeta
`.venv`. Si `python` no funciona, prueba con `py -m venv .venv`.

## 3.3 · Activar el entorno virtual

```
.venv\Scripts\activate
```

(En Mac o Linux sería `source .venv/bin/activate`.)

Verás que al principio de la línea aparece **`(.venv)`**. Eso significa que la
cajita está activa. **Cada vez que abras VS Code de nuevo, tendrás que volver a
ejecutar esta línea de activación** antes de trabajar.

> VS Code suele preguntarte "¿Quieres seleccionar este entorno para la carpeta?"
> → pulsa **Sí**. Así lo usará automáticamente.

## 3.4 · Instalar las librerías del proyecto

Este comando lee el archivo `requirements.txt` y descarga las herramientas que el
proyecto necesita (pandas, numpy, etc.):

```
pip install -r requirements.txt
```

Verás muchas líneas de texto y barras de progreso durante 1-2 minutos. Cuando
vuelva el cursor sin errores en rojo, **ya tienes todo instalado**.

---

# PARTE 4 — Comprobar que TODO funciona

Antes de usar nada, verifica que el motor está sano. Este comando ejecuta 8
pruebas automáticas (no necesita internet) que comprueban que los cálculos son
exactos: el trailing stop al céntimo, la contabilidad, el freno de caídas, etc.

```
python main.py test
```

**Debes ver 8 líneas que empiezan por ✓ y al final:**

```
TODOS LOS TESTS PASAN ✅
```

Si ves eso: **enhorabuena, el sistema está instalado y funcionando.** Si algo
sale en rojo, cópialo y pásamelo antes de continuar — no sigas a ciegas.

---

# PARTE 5 — Usar el laboratorio (investigar con datos)

El laboratorio sirve para responder preguntas con datos históricos ANTES de
arriesgar nada. Ejecuta estos comandos en la misma terminal, en orden.

## 5.1 · Descargar el histórico (una vez)

```
python main.py descargar --anos 5
```

Descarga 5 años de precios de los 143 valores desde Yahoo Finance (tarda 2-5
min). Los guarda en una carpeta `cache_datos` para que todos los experimentos
usen los mismos datos (reproducibilidad). Solo hay que hacerlo una vez.

## 5.2 · Backtest — ¿habría funcionado la estrategia?

```
python main.py backtest --anos 5
```

Simula la estrategia sobre esos 5 años y te imprime una tabla comparándola con
el índice (S&P 500): rentabilidad, CAGR (rentabilidad anualizada), caída máxima,
Sharpe, Sortino, % de aciertos, y un desglose año por año. Guarda un archivo
`curva_backtest.csv` que puedes abrir en Excel.

## 5.3 · Rejilla de robustez — ¿es real o es casualidad?

```
python main.py rejilla --anos 5
```

Ejecuta 9 backtests con distintos parámetros. Si casi todos baten al índice, la
ventaja es **robusta** (no depende de haber acertado los números por suerte). Si
solo gana con parámetros muy concretos, es **sobreajuste** (una trampa). Te da un
veredicto claro: meseta 🟢, mixto 🟡 o pico 🔴.

## 5.4 · Walk-forward — ¿gana en todas las épocas?

```
python main.py walkforward --anos 5
```

Prueba la estrategia en ventanas de tiempo que van rodando, para ver si la
ventaja es constante o solo apareció en un tramo con suerte.

## 5.5 · Monte Carlo — ¿qué resultados son NORMALES?

```
python main.py montecarlo --anos 5 --meses 4
```

Simula 5.000 futuros posibles a 4 meses. Te dice el rango de resultados normal,
la probabilidad de acabar perdiendo y la caída esperada. Sirve para no asustarte:
si vas perdiendo pero dentro del rango previsto, el sistema funciona bien.

---

# PARTE 6 — Entender el bot en vivo (local)

```
python main.py vivo
```

Cada vez que ejecutas esto, el bot da **un paso**: descarga datos frescos,
calcula los scores de hoy, decide qué vender y comprar (con dinero ficticio) y
guarda su estado. Corre **dos motores a la vez**:

- **PURO:** solo usa datos de precio (la estrategia validada por el backtest).
- **COMPLETO:** añade opinión de analistas, fundamentales y sentimiento de una IA.

Los dos compiten con la misma cantidad de dinero ficticio. En unos meses sabrás,
con datos, cuál es mejor. Comandos extra: `--aportar 100` (mete 100€ ficticios en
ambos), `--reset` (empieza de cero).

En local no hace falta programarlo: lo importante es que corra en la nube (Parte
7), donde funcionará solo aunque tu ordenador esté apagado.

---

# PARTE 7 — Subir a GitHub y activar la autonomía

Aquí conseguirás que el bot funcione **solo, en los servidores de GitHub, gratis**,
sin tu ordenador. También publicará la web.

## 7.1 · Crear una cuenta y un repositorio en GitHub

1. Ve a **https://github.com** y crea una cuenta gratuita (si no la tienes).
2. Arriba a la derecha, pulsa el **+** → **"New repository"**.
3. En "Repository name" escribe: **`gemelo-lab`**
4. Marca **"Public"** (obligatorio para que la web gratis funcione; tu proyecto
   no contiene contraseñas ni nada sensible).
5. **NO** marques ninguna casilla de "Add a README/gitignore/license".
6. Pulsa **"Create repository"**. Verás una página con instrucciones y una URL
   parecida a `https://github.com/TU_USUARIO/gemelo-lab.git`. Cópiala.

## 7.2 · Conectar tu proyecto y subirlo (desde la terminal de VS Code)

En la terminal de VS Code (con `(.venv)` delante), escribe estas líneas UNA A UNA,
pulsando Enter tras cada una. Sustituye `TU_USUARIO` por tu usuario de GitHub:

```
git init
git add .
git commit -m "primera version del sistema"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/gemelo-lab.git
git push -u origin main
```

> La primera vez, Git te pedirá iniciar sesión en GitHub: se abrirá una ventana
> del navegador, pulsa **"Authorize"** y listo. Si te pide usuario/contraseña en
> la terminal, usa tu usuario y, como contraseña, un "token" (GitHub → Settings →
> Developer settings → Personal access tokens); pero lo normal es que se abra el
> navegador y baste con autorizar.

Cuando termine, **recarga la página de tu repositorio en GitHub**: verás todos
los archivos subidos.

## 7.3 · Activar la web (GitHub Pages)

1. En tu repositorio, pulsa **"Settings"** (arriba).
2. En el menú izquierdo, pulsa **"Pages"**.
3. En "Source", elige **"Deploy from a branch"**.
4. En "Branch", elige **`main`** y, en la carpeta, elige **`/docs`**. Pulsa **Save**.
5. Espera ~1 minuto y recarga. Arriba aparecerá tu dirección web:
   **`https://TU_USUARIO.github.io/gemelo-lab/`**. Guárdala en favoritos y en el móvil.

## 7.4 · Activar la autonomía (GitHub Actions)

1. En tu repositorio, pulsa la pestaña **"Actions"** (arriba).
2. Si aparece un aviso, pulsa el botón verde **"I understand my workflows, go
   ahead and enable them"**.
3. Ahora ve a **Settings → Actions → General** (menú izquierdo).
4. Baja hasta **"Workflow permissions"**, marca **"Read and write permissions"**
   y pulsa **Save**.

**¡Ya está!** A partir de ahora, GitHub ejecuta el bot **cada hora de mercado
(9:30 a 22:30, hora española, de lunes a viernes)** por su cuenta. Cada decisión
queda guardada como un "commit" (un registro con fecha) — tienes un historial
auditado de todo, gratis.

## 7.5 · (Opcional) Activar el sentimiento con IA

Solo si quieres que el motor COMPLETO use la IA de Google (gratis):

1. Consigue una clave gratis en **https://aistudio.google.com** (botón "Get API key").
2. En tu repositorio: **Settings → Secrets and variables → Actions** →
   **"New repository secret"**.
3. Nombre: **`GEMINI_API_KEY`** · Valor: pega tu clave · **"Add secret"**.

Sin esto, el motor COMPLETO funciona igual, solo que sin la capa de IA.

## 7.6 · Probarlo ya (sin esperar a la hora)

En la pestaña **Actions**, pulsa el workflow **"bot-diario"** → botón
**"Run workflow"** → **"Run workflow"** verde. En un minuto se ejecutará; pulsa
sobre la ejecución para ver el registro (verás "Motor PURO", "Motor COMPLETO" y
el resultado). Esto también puedes hacerlo desde la **app de GitHub en el móvil**.

---

# PARTE 8 — La web (sala de control)

Abre tu dirección `https://TU_USUARIO.github.io/gemelo-lab/` en el ordenador o el
móvil. Verás la sala de control con:

- **Insignia BOT PYTHON** y un **selector PURO / COMPLETO**: elige qué motor
  quieres ver (no cambia nada del funcionamiento, solo lo que muestras).
- **Luz de estado (LED):** verde = datos recientes; ámbar = envejeciendo; rojo =
  algo va mal. Te dice de un vistazo si el bot está al día.
- **Patrimonio, P&L, posiciones:** el dinero (ficticio) y cómo evoluciona.
- **Banda de vuelo:** una aguja que muestra si tu resultado va donde el modelo
  predijo. Es el instrumento clave: cuando esté "en banda" durante meses, será la
  señal de que el sistema es fiable.
- **Curva, posiciones abiertas, operaciones, radar de mercado y sectores.**

La web se actualiza sola cada minuto.

---

# PARTE 9 — Cada funcionalidad explicada

## Cómo decide el bot (el cerebro)

**Compra** un valor cuando su "score" (nota de 0 a 100) llega a **60 o más** y se
cumplen los filtros de seguridad. El score combina:

- **Momentum (peso 45):** ¿el precio viene subiendo con fuerza? (mezcla de 1, 3 y 6 meses)
- **Tendencia (25):** ¿el precio está por encima de sus medias de 50 y 200 días?
- **Posición 52 semanas (15):** ¿está cerca de sus máximos del año?
- **Fuerza relativa (20):** ¿lo hace mejor que el S&P 500?
- **Rotación sectorial (15):** ¿pertenece a un sector fuerte ahora?
- *(Solo el motor COMPLETO añade):* **Analistas (20)**, **Fundamentales (15)** y
  **Sentimiento IA (10)**.

**Filtros de seguridad antes de comprar:**
- Solo si el mercado general está alcista (S&P sobre su media de 200 días).
- Nunca si la cartera ha caído más de un 20% desde su máximo (freno de protección).
- Máximo 6 posiciones a la vez, y máximo 2 por sector (diversificación).
- No recompra un valor hasta 2 días después de haberlo vendido (evita el bucle).

**Mantiene** una posición hasta que salta una de estas 4 salidas:
- **Trailing stop:** vende si el precio cae 3×ATR desde su punto más alto. (El ATR
  es "cuánto se mueve al día" ese valor.) Esta es la salida que MÁS actúa: protege
  las ganancias dejando correr a los ganadores.
- **Stop-loss:** vende si pierde un 12% desde la compra (corta pérdidas).
- **Objetivo:** +200% (en la práctica nunca salta: es como decir "deja correr").
- **Score bajo:** vende si la nota cae por debajo de 45 (el valor se ha debilitado).

**Cada cuánto decide:** cada hora, en horas de mercado, de lunes a viernes.

## Los dos motores (el experimento A/B)

Corren en paralelo con el mismo dinero ficticio para responder a una pregunta con
datos: *¿aportan valor los analistas, fundamentales y la IA, o basta con el
precio?* En unos meses, comparando sus dos curvas, lo sabrás sin adivinar.

## El laboratorio

Es donde se prueban ideas antes de usarlas. La regla de oro: **el laboratorio
valida, no optimiza.** Nunca se elige "el mejor número del backtest" (eso es
engañarse); se comprueba que la ventaja aguanta en muchos escenarios.

## El ejecutor IBKR (fase futura)

Está construido pero **desactivado y bloqueado**. Cuando tengas cuenta en
Interactive Brokers, permitirá que el bot ponga órdenes reales en una cuenta de
prácticas (dinero ficticio pero mercado real). Tiene triple seguridad para que sea
imposible tocar dinero real por accidente. El paso a dinero de verdad no es un
cambio de código: es una decisión que se tomará cuando los datos (la banda de
vuelo) digan que el sistema es fiable, y aun entonces, con poco dinero.

---

# PARTE 10 — Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| **`python` no se reconoce** | No marcaste "Add to PATH". Reinstala Python marcándolo, reinicia y abre terminal nueva. Prueba también `py` en vez de `python`. |
| **Error rojo de "scripts deshabilitados"** | Ejecuta el comando `Set-ExecutionPolicy` de la sección 3.1 y responde `S`. |
| **No aparece `(.venv)`** | Repite `.venv\Scripts\activate`. Si falla, cierra y reabre la terminal. |
| **`pip install` falla** | Revisa tu conexión; reintenta. Asegúrate de que `(.venv)` está activo. |
| **Los tests fallan** | Cópiame el error completo; no continúes. |
| **`descargar` da errores 429** | Yahoo te está frenando; espera 10 minutos y reintenta. |
| **La web da error 404** | Espera 1-2 min tras activar Pages; verifica Branch `main` + carpeta `/docs`. |
| **La web dice "sin conexión"** | Aún no se ha ejecutado el bot: lanza un "Run workflow" (7.6). |
| **El workflow sale en rojo** | Falta poner "Read and write permissions" (7.4). Mira el log; me lo pasas. |
| **`git push` pide contraseña** | Usa el navegador que se abre para autorizar, o crea un token en GitHub. |

---

# GLOSARIO

- **VS Code:** el editor donde abres y ejecutas el proyecto.
- **Terminal:** la consola de texto dentro de VS Code donde escribes comandos.
- **Python:** el lenguaje/motor que ejecuta el código del bot.
- **Git / GitHub:** Git sincroniza tu proyecto; GitHub es la web donde vive y donde
  el bot corre solo.
- **Entorno virtual (`.venv`):** cajita aislada con las librerías del proyecto.
- **Score:** nota de 0 a 100 que mide cómo de atractivo es un valor para comprar.
- **ATR:** cuánto se mueve de media al día un valor (su "nerviosismo").
- **Trailing stop:** venta automática cuando el precio baja cierta distancia desde
  su máximo; protege ganancias.
- **Drawdown:** caída desde el punto más alto alcanzado.
- **CAGR:** rentabilidad media anual.
- **Sharpe / Sortino:** rentabilidad ajustada al riesgo (más alto = mejor).
- **Backtest:** simular la estrategia sobre datos del pasado.
- **Sobreajuste:** cuando algo funciona solo con datos pasados por casualidad.
- **Banda ±1σ:** rango donde debería estar tu resultado si el modelo acierta.
- **Papel / paper:** dinero ficticio; sin riesgo real.
- **Commit:** un registro guardado con fecha de un cambio o una decisión.
- **Workflow / Actions:** el sistema de GitHub que ejecuta el bot solo.
- **A/B:** los dos motores en paralelo que se comparan para decidir con datos.

---

*Dinero ficticio hasta que los datos digan lo contrario. Esto es una herramienta
de apoyo a la decisión, no asesoramiento financiero. — Sistema Gemelo-Lab v5.0*
