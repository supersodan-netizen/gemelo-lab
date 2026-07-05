# Despliegue con GitHub Desktop — Gemelo-Lab

Guía adaptada a **tu** situación: código en **VS Code**, web en **GitHub Pages**,
y subida con **GitHub Desktop** (la app que ya tienes) en vez de comandos de git.

Tu proyecto ya está extraído en:
`...\Herramienta trade\gemelo-lab\`

Sigue las partes EN ORDEN. Marcadas con ⏱️ las que tardan un poco.

---

## PARTE A — Abrir y probar en VS Code (local)

### A.1 · Abrir la carpeta
1. Abre **VS Code**.
2. **Archivo → Abrir carpeta...** y elige la carpeta **`gemelo-lab`**
   (dentro de `Herramienta trade`).
3. Si pregunta "¿Confías en los autores?", pulsa **"Sí, confío"**.

### A.2 · Instalar la extensión de Python
1. Icono de **Extensiones** en la barra izquierda (o `Ctrl+Shift+X`).
2. Busca **`Python`**, instala el primero (de **Microsoft**).

### A.3 · Abrir la terminal
- Menú **Terminal → Nueva terminal**. La ruta debe terminar en `gemelo-lab`.
- Si sale un error rojo de "scripts deshabilitados", pega esto, Enter, escribe `S`, Enter:
  ```
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```

### A.4 · Crear y activar el entorno virtual
Tienes **Python 3.14.6**. En Windows el comando fiable es `py`:
```
py -m venv .venv
.venv\Scripts\activate
```
Debe aparecer **`(.venv)`** al principio de la línea. Si VS Code pregunta si usar
este entorno, di **Sí**.

### A.5 · Instalar librerías ⏱️
```
pip install -r requirements.txt
```
> ⚠️ **Nota sobre Python 3.14:** es una versión muy nueva. Si este paso falla con
> errores al compilar `pandas`/`numpy`, la causa casi seguro es que aún no hay
> versión precompilada para 3.14. Solución sencilla: instala **Python 3.12** desde
> python.org (marca "Add to PATH"), borra la carpeta `.venv`, y repite A.4 usando
> `py -3.12 -m venv .venv`. Nada más cambia. *(Esto solo afecta al laboratorio en
> tu PC; el bot en la nube usa 3.12 siempre, ver Parte C.)*

### A.6 · Comprobar que funciona
```
py main.py test
```
Debes ver varias líneas con ✓ y **TODOS LOS TESTS PASAN ✅**.
*(Yo ya los ejecuté: el motor da resultados correctos.)*

### A.7 · Usar el laboratorio (opcional, cuando quieras)
```
py main.py descargar --anos 5      # 1 sola vez, ⏱️ 2-5 min
py main.py backtest --anos 5
py main.py rejilla --anos 5
```

---

## PARTE B — Subir a GitHub con GitHub Desktop

### B.1 · Iniciar sesión
1. Abre **GitHub Desktop**.
2. **File → Options → Accounts → Sign in** con tu cuenta de GitHub
   (si no tienes cuenta, créala gratis en github.com).

### B.2 · Convertir la carpeta en repositorio
1. **File → Add local repository...**
2. Elige la carpeta **`gemelo-lab`** y pulsa continuar.
3. Dirá "*this directory does not appear to be a Git repository*" →
   pulsa el enlace **"create a repository"**.
4. En la ventana:
   - **Name:** `gemelo-lab`
   - Deja lo demás por defecto. **NO** marques "Initialize with README".
   - Pulsa **"Create repository"**.

### B.3 · Primer commit
1. Abajo a la izquierda verás todos los archivos como cambios.
2. En **Summary** escribe: `primera version` y pulsa
   **"Commit to main"**.

### B.4 · Publicar en la nube
1. Arriba pulsa **"Publish repository"**.
2. **IMPORTANTE:** desmarca la casilla **"Keep this code private"**
   (debe ser **público** para que la web y el bot gratis funcionen; el proyecto
   no tiene contraseñas).
3. Pulsa **"Publish repository"**. ⏱️ Unos segundos.

Ya está tu código en `github.com/TU_USUARIO/gemelo-lab`.

---

## PARTE C — Activar la web y la autonomía (en github.com)

Abre tu repositorio en el navegador: `github.com/TU_USUARIO/gemelo-lab`

### C.1 · La web (GitHub Pages)
1. Pestaña **Settings** → menú izquierdo **Pages**.
2. **Source:** "Deploy from a branch".
3. **Branch:** `main` · carpeta: **`/docs`** · pulsa **Save**.
4. ⏱️ ~1 min. Recarga: arriba aparece tu dirección
   **`https://TU_USUARIO.github.io/gemelo-lab/`**. Guárdala en el móvil.

### C.2 · La autonomía (GitHub Actions)
1. Pestaña **Actions** → si sale aviso, botón verde
   **"I understand my workflows, go ahead and enable them"**.
2. **Settings → Actions → General** → baja a **"Workflow permissions"** →
   marca **"Read and write permissions"** → **Save**.

Con esto el bot corre **solo cada hora de mercado (L-V)** en los servidores de
GitHub, gratis, aunque tu PC esté apagado.

### C.3 · Probarlo ya (sin esperar)
- Pestaña **Actions** → workflow **"bot-diario"** → **"Run workflow"** → verde.
- ⏱️ ~1 min. Pulsa la ejecución para ver el registro.
- Al terminar, abre tu web: ya mostrará datos.

### C.4 · (Opcional) Sentimiento con IA
1. Clave gratis en `aistudio.google.com` ("Get API key").
2. Repo → **Settings → Secrets and variables → Actions** →
   **"New repository secret"**.
3. Nombre: `GEMINI_API_KEY` · Valor: tu clave · **Add secret**.

---

## Trabajo diario (después del primer despliegue)

- **En VS Code**, cada vez que lo abras: `Terminal → Nueva terminal` y activa el
  entorno con `.venv\Scripts\activate` antes de usar el laboratorio.
- **Si cambias código** y quieres subirlo: abre **GitHub Desktop**, escribe un
  resumen, **Commit to main**, y pulsa **"Push origin"**.
- **La web y el bot** funcionan solos: no tienes que hacer nada más.

---

## Si algo falla
| Síntoma | Solución |
|---|---|
| `py`/`python` no se reconoce | Reinstala Python marcando "Add to PATH", reinicia. |
| `pip install` falla al compilar | Es Python 3.14: instala 3.12 y usa `py -3.12 -m venv .venv` (ver A.5). |
| No aparece `(.venv)` | Repite `.venv\Scripts\activate`; cierra y reabre terminal. |
| Web da 404 | Espera 1-2 min; revisa Branch `main` + carpeta `/docs`. |
| Web dice "sin conexión" | Aún no corrió el bot: lanza "Run workflow" (C.3). |
| Workflow en rojo | Falta "Read and write permissions" (C.2). |

*Dinero ficticio. Herramienta de apoyo a la decisión, no asesoramiento financiero.*
