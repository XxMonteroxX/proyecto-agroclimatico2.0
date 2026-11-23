"""
PROYECTO 1: Sistema de Monitoreo Agroclimático de Cultivos de Maíz y Aguacate
Backend FastAPI con servicio de Frontend integrado para despliegue web.
"""
import os
import random
import sys
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import storage
from storage import ALGORITMOS_POR_CAMPO, CAMPOS, CAMPOS_CLAVE, estado
import auth
from auth import RegistroRequest, LoginRequest

sys.setrecursionlimit(10000)

app = FastAPI(
    title="Sistema de Monitoreo Agroclimático - Maíz y Aguacate",
    description=(
        "API académica que procesa en RAM 30,000 registros agroclimáticos, "
        "implementando manualmente Radix Sort, Counting Sort, Bucket Sort, "
        "Quick Sort, Merge Sort, Heap Sort, Búsqueda Binaria y Búsqueda Lineal."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrdenamientoPayload(BaseModel):
    username: Optional[str] = None
    forzar_campo: Optional[str] = None


class BusquedaPayload(BaseModel):
    metodo: str
    campo: str
    valor: Any


class CasoPruebaPayload(BaseModel):
    tipo: str
    campo: str = "id_estacion"


# ---------------------------------------------------------------------------
# AUTENTICACIÓN Y CONTROL DE ACCESO (CON O SIN CLAVE)
# ---------------------------------------------------------------------------

@app.post("/api/auth/registro")
def api_registro(payload: RegistroRequest):
    return auth.registrar_usuario(payload)


@app.post("/api/auth/login")
def api_login(payload: LoginRequest):
    return auth.login_usuario(payload)


# ---------------------------------------------------------------------------
# FASE 1: CARGA A MEMORIA RAM
# ---------------------------------------------------------------------------

@app.post("/api/fase1/cargar")
def cargar():
    if not storage.DATASET_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontró el archivo '{storage.DATASET_PATH.name}' junto "
                f"a main.py. Coloque el dataset de 30,000 registros en esa ruta."
            ),
        )

    tiempo_ns, total = storage.cargar_csv()

    primeros_60 = estado.registros[:60]
    ultimos_60 = estado.registros[-60:]

    return {
        "mensaje": (
            f"Se realizó la carga de los {total} registros con sus 10 columnas a la "
            f"estructura [ArrayList/Lista de Objetos] y le tomó [{tiempo_ns}] "
            f"nanosegundos completar la acción."
        ),
        "tiempo_ns": tiempo_ns,
        "total_registros": total,
        "muestra_primeros_60": primeros_60,
        "muestra_ultimos_60": ultimos_60,
        "primeros_60": primeros_60,
        "ultimos_60": ultimos_60,
        "muestra_primeros_30": primeros_60,
        "muestra_ultimos_30": ultimos_60,
        "primeros_30": primeros_60,
        "ultimos_30": ultimos_60,
    }


# ---------------------------------------------------------------------------
# FASE 2: DISPARADOR ALEATORIO DE ORDENAMIENTO
# ---------------------------------------------------------------------------

@app.post("/api/fase2/disparador-ordenamiento")
def disparador_ordenamiento(payload: Optional[OrdenamientoPayload] = None):
    if not estado.cargado:
        raise HTTPException(
            status_code=400,
            detail="Los datos no han sido cargados en RAM. Ejecute antes /api/fase1/cargar.",
        )

    username = payload.username if payload else None
    forzar = payload.forzar_campo if payload else None

    if forzar and forzar in ALGORITMOS_POR_CAMPO:
        campo = forzar
        clave = next(k for k, v in CAMPOS_CLAVE.items() if v == campo)
    else:
        clave = random.choice(list(CAMPOS_CLAVE.keys()))
        campo = CAMPOS_CLAVE[clave]

    metodo = random.choice(ALGORITMOS_POR_CAMPO[campo])

    comparaciones, movimientos, tiempo_ns = storage.ejecutar_ordenamiento(campo, metodo, username=username)
    alfa_nombre, alfa_conteo = storage.metodo_alfa()
    stats_alfa = auth.obtener_estadisticas_alfa(username)

    primeros_60 = estado.registros[:60]
    ultimos_60 = estado.registros[-60:]

    return {
        "campo_seleccionado": {"clave": clave, "nombre": campo},
        "campo": campo,
        "clave": clave,
        "metodo_asignado": metodo,
        "metodo": metodo,
        "tiempo_ns": tiempo_ns,
        "comparaciones": comparaciones,
        "movimientos": movimientos,
        "mensaje_benchmarking": (
            f"Ordenamiento '{metodo}' sobre el campo '{campo}' completado en "
            f"{tiempo_ns} ns, con {comparaciones} comparaciones y {movimientos} "
            f"movimientos/asignaciones de memoria."
        ),
        "metodo_alfa": {
            "nombre": alfa_nombre,
            "veces_ejecutado": alfa_conteo,
            "historial_completo": dict(estado.conteo_metodos),
            "usuario": stats_alfa["usuario"],
            "general": stats_alfa["general"],
        },
        "muestra_primeros_60": primeros_60,
        "muestra_ultimos_60": ultimos_60,
        "primeros_60": primeros_60,
        "ultimos_60": ultimos_60,
        "muestra_primeros_30": primeros_60,
        "muestra_ultimos_30": ultimos_60,
        "primeros_30": primeros_60,
        "ultimos_30": ultimos_60,
    }


# ---------------------------------------------------------------------------
# FASE 3: DISPARADOR Y EJECUCIÓN DE BÚSQUEDA
# ---------------------------------------------------------------------------

@app.get("/api/fase3/disparador-busqueda")
def disparador_busqueda():
    if not estado.cargado:
        raise HTTPException(
            status_code=400,
            detail="Los datos no han sido cargados en RAM. Ejecute antes /api/fase1/cargar.",
        )

    metodo = random.choice(["Búsqueda Binaria", "Búsqueda Lineal"])

    if metodo == "Búsqueda Binaria":
        campo_ordenado = estado.campo_actualmente_ordenado or "id_estacion"
        return {
            "metodo_seleccionado": metodo,
            "metodo": metodo,
            "alerta_seguridad": False,
            "campo_requerido": campo_ordenado,
            "campo": campo_ordenado,
            "mensaje": f"Se realizará Búsqueda Binaria sobre el campo previamente ordenado: '{campo_ordenado}'.",
        }

    return {
        "metodo_seleccionado": "Búsqueda Lineal",
        "metodo": "Búsqueda Lineal",
        "alerta_seguridad": False,
        "campo": random.choice(CAMPOS),
        "campos_disponibles": CAMPOS,
        "mensaje": "Solicite al usuario que elija cualquiera de los 10 campos disponibles y el valor a buscar.",
    }


@app.post("/api/fase3/ejecutar-busqueda")
def ejecutar_busqueda(payload: BusquedaPayload):
    if not estado.cargado:
        raise HTTPException(status_code=400, detail="Los datos no han sido cargados en RAM.")

    if payload.campo not in CAMPOS:
        raise HTTPException(
            status_code=422,
            detail=f"Campo '{payload.campo}' no válido. Campos disponibles: {CAMPOS}",
        )

    if payload.metodo not in ("Búsqueda Binaria", "Búsqueda Lineal", "Búsqueda Secuencial"):
        raise HTTPException(
            status_code=422,
            detail="Método inválido. Use 'Búsqueda Binaria' o 'Búsqueda Lineal / Secuencial'.",
        )

    try:
        encontrado, idx, registro, comparaciones, tiempo_ns = storage.ejecutar_busqueda(
            payload.metodo, payload.campo, payload.valor
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "encontrado": encontrado,
        "indice_ram": idx,
        "indice": idx,
        "registro": registro,
        "tiempo_ns": tiempo_ns,
        "comparaciones": comparaciones,
        "benchmarking": {
            "tiempo_ns": tiempo_ns,
            "comparaciones": comparaciones,
            "mensaje": (
                f"Búsqueda '{payload.metodo}' sobre el campo '{payload.campo}' "
                f"completada en {tiempo_ns} ns con {comparaciones} comparaciones."
            ),
        },
    }


# ---------------------------------------------------------------------------
# ENDPOINTS DE MÉTODO ALFA, REPORTES Y BENCHMARKING
# ---------------------------------------------------------------------------

@app.get("/api/alfa")
def obtener_alfa(username: Optional[str] = None):
    return auth.obtener_estadisticas_alfa(username)


@app.delete("/api/alfa/{username}")
def reiniciar_alfa(username: str):
    return auth.reiniciar_alfa_usuario(username)


@app.get("/api/reportes/comparativa")
def reporte_comparativo():
    return {
        "comparativa_campos_clave": storage.obtener_reporte_comparativo(),
        "total_registros": len(estado.registros),
        "cargado": estado.cargado,
    }


@app.post("/api/benchmarking/configurar-caso")
def configurar_caso(payload: CasoPruebaPayload):
    try:
        mensaje = storage.configurar_caso_prueba(payload.tipo, payload.campo)
        return {
            "mensaje": mensaje,
            "muestra_primeros_60": storage.estado.registros[:60],
            "muestra_ultimos_60": storage.estado.registros[-60:],
            "muestra_primeros_30": storage.estado.registros[:60],
            "muestra_ultimos_30": storage.estado.registros[-60:],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/estado")
def obtener_estado(username: Optional[str] = None):
    alfa_nombre, alfa_conteo = storage.metodo_alfa()
    stats_alfa = auth.obtener_estadisticas_alfa(username)
    return {
        "datos_cargados": estado.cargado,
        "total_registros": len(estado.registros),
        "campo_actualmente_ordenado": estado.campo_actualmente_ordenado,
        "ultimo_metodo_usado": estado.ultimo_metodo,
        "metodo_alfa": {
            "nombre": alfa_nombre,
            "veces_ejecutado": alfa_conteo,
            "usuario": stats_alfa["usuario"],
            "general": stats_alfa["general"],
        },
        "historial_metodos": dict(estado.conteo_metodos),
    }


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def raiz():
    ruta_index = os.path.join("static", "index.html")
    if os.path.exists(ruta_index):
        return FileResponse(ruta_index)
    return {
        "proyecto": "Sistema de Monitoreo Agroclimático - Maíz y Aguacate",
        "documentacion": "/docs",
        "aviso": "Coloque index.html dentro de la carpeta static/ para ver la interfaz.",
    }
