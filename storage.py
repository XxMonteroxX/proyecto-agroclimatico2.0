"""
Capa de negocio: recibe archivos Excel (.xlsx) o CSV subidos por el usuario,
valida que cumplan exactamente con la estructura agroclimática de 10 columnas,
detecta el total real de registros, carga en RAM la cantidad elegida por el
usuario y orquesta los algoritmos de ordenamiento y búsqueda.
"""
import csv
import io
import time
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook

import auth
from algorithms import (
    radix_sort,
    counting_sort,
    bucket_sort,
    quick_sort,
    merge_sort,
    heap_sort,
    linear_search,
    binary_search,
)

BASE_DIR = Path(__file__).parent

BITACORA_ORDEN_PATH = BASE_DIR / "bitacora_ordenacion.txt"
BITACORA_BUSQUEDA_PATH = BASE_DIR / "bitacora_busqueda.txt"
BACKUP_PATH = BASE_DIR / "registros_ordenados_backup.csv"

CAMPOS = [
    "id_estacion",
    "temperatura_promedio",
    "fecha_registro",
    "estado",
    "municipio",
    "humedad_relativa",
    "precipitacion_mm",
    "tipo_cultivo_predominante",
    "presion_atmosferica",
    "velocidad_viento",
]

CAMPOS_SET = set(CAMPOS)
CAMPOS_ENTEROS = {"id_estacion", "temperatura_promedio", "fecha_registro"}
CAMPOS_FLOTANTES = {"humedad_relativa", "precipitacion_mm", "presion_atmosferica", "velocidad_viento"}

CAMPOS_CLAVE = {
    1: "id_estacion",
    2: "temperatura_promedio",
    3: "fecha_registro",
}

TIPOS_CAMPO_CLAVE = {
    "id_estacion": "Entero (ID Único)",
    "temperatura_promedio": "Entero (°C)",
    "fecha_registro": "Entero (AAAAMMDD)",
}

ALGORITMOS_POR_CAMPO = {
    "id_estacion": ["Radix Sort", "Counting Sort"],
    "temperatura_promedio": ["Bucket Sort"],
    "fecha_registro": ["Quick Sort", "Merge Sort", "Heap Sort"],
}

_FUNCIONES_ORDENAMIENTO = {
    "Radix Sort": radix_sort,
    "Counting Sort": counting_sort,
    "Bucket Sort": bucket_sort,
    "Quick Sort": quick_sort,
    "Merge Sort": merge_sort,
    "Heap Sort": heap_sort,
}


class EstadoRAM:
    """Representa el estado único de la 'RAM' simulada y el archivo subido."""

    def __init__(self):
        # Archivo inspeccionado listo para cargarse
        self.archivo_nombre = None
        self.archivo_tamano_bytes = 0
        self.registros_disponibles = []

        # Datos activos cargados en memoria RAM
        self.registros = []
        self.cargado = False
        self.campo_actualmente_ordenado = None
        self.ultimo_metodo = None
        self.primera_ordenacion_hecha = False
        self.conteo_metodos = {}
        self.tiempo_carga_ns = None
        self.mejor_por_campo = {}


estado = EstadoRAM()


def castear_valor(campo, valor):
    """Convierte el valor recibido por JSON al tipo nativo de forma segura."""
    try:
        if campo in CAMPOS_ENTEROS:
            return int(float(valor))
        if campo in CAMPOS_FLOTANTES:
            return float(valor)
    except (ValueError, TypeError):
        raise ValueError(f"El valor '{valor}' no es válido para el campo numérico '{campo}'.")
    return str(valor)


def _normalizar_fila(fila_dict: dict, num_fila: int) -> dict:
    """Valida y convierte los tipos de una fila individual."""
    try:
        return {
            "id_estacion": int(float(fila_dict["id_estacion"])),
            "temperatura_promedio": int(float(fila_dict["temperatura_promedio"])),
            "fecha_registro": int(float(fila_dict["fecha_registro"])),
            "estado": str(fila_dict["estado"]).strip(),
            "municipio": str(fila_dict["municipio"]).strip(),
            "humedad_relativa": float(fila_dict["humedad_relativa"]),
            "precipitacion_mm": float(fila_dict["precipitacion_mm"]),
            "tipo_cultivo_predominante": str(fila_dict["tipo_cultivo_predominante"]).strip(),
            "presion_atmosferica": float(fila_dict["presion_atmosferica"]),
            "velocidad_viento": float(fila_dict["velocidad_viento"]),
        }
    except (ValueError, TypeError, KeyError) as e:
        raise ValueError(
            f"Archivo incompatible: error de formato en la fila {num_fila} ({e}). "
            f"Asegúrate de subir un dataset agroclimático válido."
        )


def inspeccionar_archivo(nombre_archivo: str, contenido_bytes: bytes) -> dict:
    """
    Valida la extensión (.xlsx o .csv), comprueba que tenga las 10 columnas
    requeridas y parsea todos los registros para reportar el total disponible.
    """
    nombre_lower = nombre_archivo.lower()
    if not (nombre_lower.endswith(".xlsx") or nombre_lower.endswith(".csv")):
        raise ValueError(
            f"Formato no soportado ('{nombre_archivo}'). Solo se permiten archivos Excel (.xlsx) o CSV (.csv)."
        )

    registros_parseados = []

    if nombre_lower.endswith(".xlsx"):
        try:
            wb = load_workbook(filename=io.BytesIO(contenido_bytes), read_only=True, data_only=True)
            ws = wb.active
            filas_iter = ws.iter_rows(values_only=True)
            primera_fila = next(filas_iter, None)
        except Exception as e:
            raise ValueError(f"No se pudo leer el archivo Excel. Verifica que no esté dañado ({e}).")

        if not primera_fila:
            raise ValueError("El archivo Excel está completamente vacío.")

        encabezados = [str(c).strip() if c is not None else "" for c in primera_fila]
        faltantes = [c for c in CAMPOS if c not in encabezados]
        if faltantes:
            raise ValueError(
                f"El archivo '{nombre_archivo}' no corresponde al proyecto agroclimático. "
                f"Faltan las columnas obligatorias: {', '.join(faltantes)}."
            )

        indices = {col: encabezados.index(col) for col in CAMPOS}

        for idx, row in enumerate(filas_iter, start=2):
            if not row or all(v is None or str(v).strip() == "" for v in row):
                continue
            fila_dict = {col: row[indices[col]] for col in CAMPOS}
            registros_parseados.append(_normalizar_fila(fila_dict, idx))

        wb.close()

    else:  # .csv
        try:
            texto = contenido_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                texto = contenido_bytes.decode("latin-1")
            except Exception:
                raise ValueError("Codificación de archivo CSV no válida. Guárdalo en UTF-8.")

        lector = csv.DictReader(io.StringIO(texto))
        if not lector.fieldnames:
            raise ValueError("El archivo CSV está vacío o no tiene encabezados.")

        encabezados = [c.strip() for c in lector.fieldnames]
        faltantes = [c for c in CAMPOS if c not in encabezados]
        if faltantes:
            raise ValueError(
                f"El archivo '{nombre_archivo}' no corresponde al proyecto agroclimático. "
                f"Faltan las columnas obligatorias: {', '.join(faltantes)}."
            )

        for idx, fila in enumerate(lector, start=2):
            if not fila or all(v is None or str(v).strip() == "" for v in fila.values()):
                continue
            fila_limpia = {k.strip(): v for k, v in fila.items() if k}
            registros_parseados.append(_normalizar_fila(fila_limpia, idx))

    if len(registros_parseados) == 0:
        raise ValueError(f"El archivo '{nombre_archivo}' tiene los encabezados correctos pero 0 registros de datos.")

    # Guardar en zona de preparación (staging)
    estado.archivo_nombre = nombre_archivo
    estado.archivo_tamano_bytes = len(contenido_bytes)
    estado.registros_disponibles = registros_parseados

    return {
        "status": "valid",
        "archivo": nombre_archivo,
        "tamano_bytes": len(contenido_bytes),
        "total_disponible": len(registros_parseados),
        "columnas": CAMPOS,
    }


def cargar_en_ram(limite: Optional[int] = None):
    """
    Carga en estado.registros (RAM activa) la cantidad exacta de registros
    solicitada por el usuario desde estado.registros_disponibles.
    """
    total_disp = len(estado.registros_disponibles)
    if total_disp == 0:
        raise ValueError("No hay ningún archivo validado. Selecciona y valida un archivo Excel o CSV primero.")

    if limite is None:
        cantidad = total_disp
    else:
        if limite < 1:
            raise ValueError("Debes cargar al menos 1 registro a la memoria RAM.")
        if limite > total_disp:
            raise ValueError(
                f"Solicitaste cargar {limite:,} registros, pero el archivo '{estado.archivo_nombre}' "
                f"solo contiene {total_disp:,} registros."
            )
        cantidad = limite

    t0 = time.perf_counter_ns()
    # Copia efectiva a la estructura activa en RAM
    subconjunto = [dict(reg) for reg in estado.registros_disponibles[:cantidad]]
    t1 = time.perf_counter_ns()

    tiempo_ns = t1 - t0
    estado.registros = subconjunto
    estado.cargado = True
    estado.campo_actualmente_ordenado = None
    estado.ultimo_metodo = None
    estado.tiempo_carga_ns = tiempo_ns
    estado.primera_ordenacion_hecha = False
    estado.mejor_por_campo = {}

    return tiempo_ns, len(subconjunto), total_disp


def ejecutar_ordenamiento(campo, metodo, username: Optional[str] = None):
    """Ejecuta el algoritmo indicado sobre estado.registros, actualiza el
    estado de la RAM, persiste el Método Alfa en SQLite y escribe la bitácora."""
    funcion = _FUNCIONES_ORDENAMIENTO[metodo]
    ordenados, comparaciones, movimientos, tiempo_ns = funcion(estado.registros, campo)

    estado.registros = ordenados
    estado.campo_actualmente_ordenado = campo
    estado.ultimo_metodo = metodo
    estado.conteo_metodos[metodo] = estado.conteo_metodos.get(metodo, 0) + 1

    auth.registrar_ejecucion_alfa(username, metodo)

    previo = estado.mejor_por_campo.get(campo)
    if previo is None or tiempo_ns < previo["tiempo_ns"]:
        estado.mejor_por_campo[campo] = {
            "campo": campo,
            "tipo_dato": TIPOS_CAMPO_CLAVE.get(campo, "Numérico"),
            "metodo": metodo,
            "tiempo_ns": tiempo_ns,
            "comparaciones": comparaciones,
            "movimientos": movimientos,
        }

    total_reg = len(estado.registros)
    linea = (
        f"Se ordenaron {total_reg:,} registros por el campo [{campo}] usando el método "
        f"[{metodo}] en [{tiempo_ns}] nanosegundos. Comparaciones: [{comparaciones}], "
        f"Asignaciones/Movimientos de Memoria: [{movimientos}]\n"
    )

    with open(BITACORA_ORDEN_PATH, "a", encoding="utf-8") as f:
        f.write(linea)

    if not estado.primera_ordenacion_hecha:
        guardar_backup()
        estado.primera_ordenacion_hecha = True

    return comparaciones, movimientos, tiempo_ns


def guardar_backup():
    """Respaldo de la primera ordenación en registros_ordenados_backup.csv."""
    with open(BACKUP_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        writer.writerows(estado.registros)


def metodo_alfa():
    """El método de ordenamiento más ejecutado hasta el momento en RAM."""
    if not estado.conteo_metodos:
        return None, 0
    nombre_alfa = max(estado.conteo_metodos, key=lambda k: estado.conteo_metodos[k])
    return nombre_alfa, estado.conteo_metodos[nombre_alfa]


def obtener_reporte_comparativo():
    """Devuelve la comparativa estructurada de los 3 campos clave para Reportes."""
    filas = []
    for clave, campo in CAMPOS_CLAVE.items():
        dato = estado.mejor_por_campo.get(campo)
        if dato:
            filas.append(dato)
        else:
            filas.append({
                "campo": campo,
                "tipo_dato": TIPOS_CAMPO_CLAVE.get(campo, "Numérico"),
                "metodo": "Sin ejecutar aún",
                "tiempo_ns": None,
                "comparaciones": None,
                "movimientos": None,
            })
    return filas


def ejecutar_busqueda(metodo, campo, valor):
    """Ejecuta Búsqueda Binaria o Lineal sobre estado.registros, valida las
    condiciones de memoria física y escribe la bitácora de búsqueda."""
    valor_casteado = castear_valor(campo, valor)

    if metodo == "Búsqueda Binaria":
        if estado.campo_actualmente_ordenado != campo:
            raise ValueError(
                f"ALERTA DE SEGURIDAD DE MEMORIA: la RAM no está ordenada por el campo "
                f"'{campo}'. Campo actualmente ordenado: "
                f"{estado.campo_actualmente_ordenado or 'ninguno'}. "
                f"La Búsqueda Binaria fue rechazada."
            )
        idx, comparaciones, tiempo_ns = binary_search(estado.registros, campo, valor_casteado)
    elif metodo in ("Búsqueda Lineal", "Búsqueda Secuencial"):
        idx, comparaciones, tiempo_ns = linear_search(estado.registros, campo, valor_casteado)
    else:
        raise ValueError(f"Método de búsqueda no reconocido: '{metodo}'")

    encontrado = idx != -1
    registro = estado.registros[idx] if encontrado else None

    total_reg = len(estado.registros)
    linea = (
        f"Se realizó la búsqueda en {total_reg:,} registros por el campo [{campo}] usando "
        f"el método de búsqueda [{metodo}] en [{tiempo_ns}] nanosegundos. "
        f"Comparaciones: [{comparaciones}]\n"
    )
    with open(BITACORA_BUSQUEDA_PATH, "a", encoding="utf-8") as f:
        f.write(linea)

    return encontrado, idx, registro, comparaciones, tiempo_ns


def configurar_caso_prueba(tipo: str, campo: str = "id_estacion"):
    """Modifica el orden de los registros en RAM para benchmarking."""
    if not estado.cargado:
        raise ValueError("No hay registros en RAM. Carga primero los datos del archivo.")

    cantidad_actual = len(estado.registros)
    if tipo == "aleatorio":
        cargar_en_ram(cantidad_actual)
        return f"Los {cantidad_actual:,} registros fueron restablecidos al orden original del archivo."

    estado.registros.sort(key=lambda x: x[campo], reverse=(tipo == "peor"))
    estado.campo_actualmente_ordenado = campo if tipo == "mejor" else None
    return f"Memoria RAM configurada en modo [{tipo.upper()}] según el campo [{campo}]."
