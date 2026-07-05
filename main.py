# -*- coding: utf-8 -*-
"""Laboratorio Gemelo — CLI.

  python main.py descargar  --anos 5 [--forzar]
  python main.py backtest   --anos 5
  python main.py rejilla    --anos 5
  python main.py walkforward --anos 5 [--ventana 2] [--paso 6]
  python main.py montecarlo --anos 5 [--meses 4] [--caminos 5000]
  python main.py test
"""
import argparse

from config import PARAMS, TICKERS, SECTORES


def _prep(anos):
    import datos
    from motor import construir_frames, replay
    cierres = datos.cargar(anos)
    return cierres


def cmd_descargar(a):
    import datos
    datos.descargar(TICKERS, PARAMS["BENCHMARK"], anos=a.anos, forzar=a.forzar)


def cmd_backtest(a):
    from motor import construir_frames, replay
    from metricas import resumen, por_anio, imprimir
    cierres = _prep(a.anos)
    F = construir_frames(cierres, SECTORES, PARAMS)
    r = replay(PARAMS, F)
    R = resumen(r["curva"], r["cerrados"], r["ganados"], r["pct_mercado"],
                a.anos, PARAMS["REBALANCEO_DIAS"], PARAMS["LIQUIDO_INICIAL"])
    imprimir(R, por_anio(r["curva"]))
    r["curva"].to_csv("curva_backtest.csv")
    print("Curva guardada en curva_backtest.csv (motor vs índice, por fecha).")


def cmd_rejilla(a):
    from analisis import rejilla
    cierres = _prep(a.anos)
    df, bench, veredicto = rejilla(PARAMS, cierres, SECTORES, anos=a.anos)
    print("\n" + df.to_string(index=False))
    print(f"\nÍNDICE: CAGR {bench['cagr']:.2f}% · DD -{bench['dd']:.2f}% · Sharpe {bench['sharpe']:.2f}")
    print(veredicto + "\n")
    df.to_csv("rejilla.csv", index=False)


def cmd_walkforward(a):
    from analisis import walk_forward
    cierres = _prep(a.anos)
    df, res = walk_forward(PARAMS, cierres, SECTORES, ventana_anios=a.ventana, paso_meses=a.paso)
    print("\n" + df.to_string(index=False))
    print("\n" + res + "\n")
    df.to_csv("walkforward.csv", index=False)


def cmd_montecarlo(a):
    from analisis import montecarlo, imprimir_montecarlo
    cierres = _prep(a.anos)
    imprimir_montecarlo(montecarlo(PARAMS, cierres, SECTORES, meses=a.meses, n_caminos=a.caminos))


def cmd_vivo(a):
    from vivo import ciclo
    ciclo(anos_datos=a.anos_datos, aportar=a.aportar, reset=a.reset, publicar=a.publicar)


def cmd_volumen(a):
    import datos
    from analisis import experimento_volumen
    cierres = datos.cargar(a.anos)
    vol = datos.cargar_volumen(a.anos)
    comp, veredicto, _ = experimento_volumen(PARAMS, cierres, SECTORES, vol,
                                             peso_volumen=a.peso, anos=a.anos)
    print("\n=== EXPERIMENTO DE VOLUMEN — misma rejilla SIN vs CON volumen ===")
    print(comp.to_string(index=False))
    print("\n" + veredicto + "\n")
    comp.to_csv("experimento_volumen.csv", index=False)


def cmd_ibkr(a):
    from ejecutor import estado_cuenta
    estado_cuenta()


def cmd_test(a):
    from tests.test_motor import correr_todos
    correr_todos()


def main():
    p = argparse.ArgumentParser(description="Laboratorio Gemelo de Mercado")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("descargar"); d.add_argument("--anos", type=int, default=5)
    d.add_argument("--forzar", action="store_true"); d.set_defaults(fn=cmd_descargar)

    b = sub.add_parser("backtest"); b.add_argument("--anos", type=int, default=5)
    b.set_defaults(fn=cmd_backtest)

    g = sub.add_parser("rejilla"); g.add_argument("--anos", type=int, default=5)
    g.set_defaults(fn=cmd_rejilla)

    w = sub.add_parser("walkforward"); w.add_argument("--anos", type=int, default=5)
    w.add_argument("--ventana", type=float, default=2.0); w.add_argument("--paso", type=int, default=6)
    w.set_defaults(fn=cmd_walkforward)

    m = sub.add_parser("montecarlo"); m.add_argument("--anos", type=int, default=5)
    m.add_argument("--meses", type=int, default=4); m.add_argument("--caminos", type=int, default=5000)
    m.set_defaults(fn=cmd_montecarlo)

    v = sub.add_parser("vivo", help="un paso del bot en papel (estado propio + web)")
    v.add_argument("--anos-datos", type=int, default=2, dest="anos_datos")
    v.add_argument("--aportar", type=float, default=0.0)
    v.add_argument("--reset", action="store_true")
    v.add_argument("--publicar", action="store_true", help="git commit+push del estado para la web")
    v.set_defaults(fn=cmd_vivo)

    ev = sub.add_parser("volumen", help="experimento: ¿aporta el volumen al score?")
    ev.add_argument("--anos", type=int, default=5)
    ev.add_argument("--peso", type=float, default=15.0, help="peso del factor volumen a probar")
    ev.set_defaults(fn=cmd_volumen)

    ib = sub.add_parser("ibkr-estado", help="conciliar: cuenta y posiciones en IBKR paper")
    ib.set_defaults(fn=cmd_ibkr)

    t = sub.add_parser("test"); t.set_defaults(fn=cmd_test)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
