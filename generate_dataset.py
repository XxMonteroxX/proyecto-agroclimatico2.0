"""
Genera dataset_agroclimatico_15000.csv (o el nombre que usa tu backend)
con 30,000 registros sintéticos y climáticamente coherentes.
"""
import csv
import random

random.seed(42)

# 1. Cambiar la cantidad a 30,000
TOTAL_REGISTROS = 30000

MUNICIPIOS_POR_ESTADO = {
    "Jalisco": ["Zapotlán el Grande", "Autlán de Navarro", "Tapalpa", "Sayula", "Tecolotlán", "Ameca"],
    "Michoacán": ["Uruapan", "Tacámbaro", "Peribán", "Los Reyes", "Tancítaro", "Ario de Rosales"],
    "Sinaloa": ["Culiacán", "Guasave", "Navolato", "Angostura", "Mocorito", "Badiraguato"],
    "Veracruz": ["Cosamaloapan", "Martínez de la Torre", "Tierra Blanca", "Huatusco", "Córdoba", "Atoyac"],
}

ESTADOS = list(MUNICIPIOS_POR_ESTADO.keys())

def fecha_aleatoria():
    anio = random.randint(2022, 2024)
    mes = random.randint(1, 12)
    dias_mes = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    dia = random.randint(1, dias_mes[mes])
    return int(f"{anio:04d}{mes:02d}{dia:02d}")

def generar_registro(id_estacion):
    estado = random.choice(ESTADOS)
    municipio = random.choice(MUNICIPIOS_POR_ESTADO[estado])
    tipo_cultivo = random.choice(["Maíz Blanco", "Aguacate Hass"])

    temperatura_promedio = random.randint(10, 45)
    fecha_registro = fecha_aleatoria()
    humedad_relativa = round(random.uniform(30.0, 95.0), 2)
    precipitacion_mm = round(random.uniform(0.0, 180.0), 2)
    presion_atmosferica = round(random.uniform(870.0, 1020.0), 2)
    velocidad_viento = round(random.uniform(0.0, 60.0), 2)

    return {
        "id_estacion": id_estacion,
        "temperatura_promedio": temperatura_promedio,
        "fecha_registro": fecha_registro,
        "estado": estado,
        "municipio": municipio,
        "humedad_relativa": humedad_relativa,
        "precipitacion_mm": precipitacion_mm,
        "tipo_cultivo_predominante": tipo_cultivo,
        "presion_atmosferica": presion_atmosferica,
        "velocidad_viento": velocidad_viento,
    }

def main():
    campos = [
        "id_estacion", "temperatura_promedio", "fecha_registro", "estado", "municipio",
        "humedad_relativa", "precipitacion_mm", "tipo_cultivo_predominante",
        "presion_atmosferica", "velocidad_viento",
    ]

    # 2. Escalar el banco de IDs disponibles para 30k filas (60% = 18,000 folios base)
    ids_disponibles = list(range(1000, 1000 + int(TOTAL_REGISTROS * 0.6)))

    # Conservamos el mismo nombre que espera storage.py para que no tengas que cambiar rutas
    archivo_salida = "dataset_agroclimatico_30000.csv"

    with open(archivo_salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for _ in range(TOTAL_REGISTROS):
            id_estacion = random.choice(ids_disponibles)
            writer.writerow(generar_registro(id_estacion))

    print(f"Dataset generado exitosamente: {archivo_salida} con {TOTAL_REGISTROS} filas.")

if __name__ == "__main__":
    main()
