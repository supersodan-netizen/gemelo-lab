# Visión del proyecto: Gemelo Digital + Laboratorio de Investigación

(Constitución del proyecto — redactada por Jorge; anexo técnico consensuado al final.)

Nuestro objetivo no es desarrollar un bot que compre acciones: es construir un
sistema profesional de apoyo a la inversión — objetivo, consistente, auditable —
en el que cada decisión pueda explicarse meses después, todo se mida, y ningún
cambio llegue a producción sin evidencia.

## Reparto de responsabilidades
- **Apps Script — el Gemelo Digital:** el entorno OPERATIVO y la fuente oficial
  del estado. Datos, indicadores, cartera, riesgo, registro, histórico, dashboard.
  Prioriza estabilidad y robustez; solo recibe cambios previamente validados.
- **Python — el Laboratorio:** el entorno CIENTÍFICO. Backtesting, walk-forward,
  Monte Carlo, rejillas de parámetros, detección de sobreajuste, comparación de
  versiones. Donde se experimenta; nunca donde se improvisa sobre dinero real.

## El ciclo de mejora
Idea → desarrollo en el laboratorio → backtest → walk-forward → Monte Carlo →
comparación con benchmarks → si demuestra valor, se incorpora al sistema
operativo → los resultados reales vuelven al laboratorio. Ciclo continuo.

## Principios innegociables
1. **Calidad sobre velocidad.** Semanas validando antes que minutos improvisando.
2. **Reproducibilidad total.** Cada decisión debe poder reconstruirse años después:
   datos, score, indicadores, VERSIÓN DEL ALGORITMO, parámetros, motivo.
3. **Todo se mide.** CAGR, Sharpe, Sortino, drawdown, profit factor, win rate,
   esperanza, exposición, rotación, contribución por factor, valor real de la IA.
4. **Ninguna mejora entra sin evidencia.** Los datos justifican; la intuición propone.
5. **La IA es asesor, no oráculo.** El núcleo es cuantitativo, reproducible, explicable.
6. **Arquitectura modular.** Datos, validación, indicadores, score, riesgo, decisión,
   ejecución, auditoría, dashboard, laboratorio: módulos independientes.

## Anexo técnico — el módulo de Ejecución (resolución consensuada)
La ejecución con broker exige una sesión persistente (IBKR Gateway) que Apps
Script no puede sostener; por el principio 6, la Ejecución es un MÓDULO y se
implementa donde puede vivir: `ejecutor.py` (Python), con triple seguridad,
kill switch, límites y auditoría. Esto NO altera los papeles: el cerebro que se
ejecute será siempre la estrategia validada por el ciclo completo de arriba, el
Gemelo sigue siendo la referencia del estado, y el laboratorio sigue siendo el
único lugar donde nacen y se prueban las ideas. Dos implementaciones
independientes (paridad demostrada con tests cruzados) se validan mutuamente:
ese es el verdadero valor del proyecto.
