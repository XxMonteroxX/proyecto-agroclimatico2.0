"""
Módulo de autenticación, persistencia de usuarios y control del Método Alfa
(Individual por Usuario vs. Acumulado General Protegido) con SQLite.
"""
import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import HTTPException

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "usuarios.db"


def init_db():
    """Crea las tablas de usuarios e historial_alfa si no existen al arrancar."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT DEFAULT 'Investigador Agroclimático'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historial_alfa (
                ambito TEXT NOT NULL,
                metodo TEXT NOT NULL,
                ejecuciones INTEGER DEFAULT 0,
                PRIMARY KEY (ambito, metodo)
            )
        """)
        conn.commit()


init_db()


def hash_password(password: str) -> str:
    """Genera un hash SHA-256 seguro para no guardar contraseñas en texto plano."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class RegistroRequest(BaseModel):
    username: str
    password: str
    nombre: str


class LoginRequest(BaseModel):
    username: str
    password: Optional[str] = ""


def registrar_usuario(req: RegistroRequest):
    usuario_limpio = req.username.strip().lower()
    if len(usuario_limpio) < 3 or len(req.password.strip()) < 4:
        raise HTTPException(
            status_code=400,
            detail="El usuario debe tener al menos 3 caracteres y la contraseña al menos 4."
        )

    pass_hash = hash_password(req.password.strip())
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO usuarios (username, password_hash, nombre) VALUES (?, ?, ?)",
                (usuario_limpio, pass_hash, req.nombre.strip() or usuario_limpio)
            )
            conn.commit()
        return {"status": "success", "mensaje": "Usuario registrado exitosamente."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado.")


def login_usuario(req: LoginRequest):
    usuario_limpio = req.username.strip().lower()
    if len(usuario_limpio) < 2:
        raise HTTPException(status_code=400, detail="Ingresa un nombre de usuario válido.")

    # Modalidad: Ingresar sin clave (Invitado)
    if not req.password or not req.password.strip():
        token = secrets.token_hex(16)
        return {
            "status": "success",
            "usuario": {
                "id": 0,
                "username": usuario_limpio,
                "nombre": req.username.strip(),
                "rol": "Invitado (Sin clave)",
                "invitado": True
            },
            "token": token
        }

    # Modalidad: Usuario registrado con contraseña
    pass_hash = hash_password(req.password.strip())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, nombre, rol FROM usuarios WHERE username = ? AND password_hash = ?",
            (usuario_limpio, pass_hash)
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    token = secrets.token_hex(16)
    return {
        "status": "success",
        "usuario": {
            "id": row[0],
            "username": row[1],
            "nombre": row[2],
            "rol": row[3],
            "invitado": False
        },
        "token": token
    }


def registrar_ejecucion_alfa(username: Optional[str], metodo: str):
    """Suma +1 ejecución al acumulado GLOBAL y +1 al ámbito del USUARIO activo."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO historial_alfa (ambito, metodo, ejecuciones)
            VALUES ('__GENERAL__', ?, 1)
            ON CONFLICT(ambito, metodo) DO UPDATE SET ejecuciones = ejecuciones + 1
        """, (metodo,))

        if username and username.strip():
            user_key = username.strip().lower()
            conn.execute("""
                INSERT INTO historial_alfa (ambito, metodo, ejecuciones)
                VALUES (?, ?, 1)
                ON CONFLICT(ambito, metodo) DO UPDATE SET ejecuciones = ejecuciones + 1
            """, (user_key, metodo))
        conn.commit()


def obtener_estadisticas_alfa(username: Optional[str] = None):
    """Devuelve el desglose y líder Alfa tanto del usuario como del acumulado general."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("SELECT metodo, ejecuciones FROM historial_alfa WHERE ambito = '__GENERAL__'")
        general_dict = dict(cur.fetchall())

        usuario_dict = {}
        if username and username.strip():
            user_key = username.strip().lower()
            cur.execute("SELECT metodo, ejecuciones FROM historial_alfa WHERE ambito = ?", (user_key,))
            usuario_dict = dict(cur.fetchall())

    def calcular_lider(conteo: dict):
        if not conteo:
            return {"nombre": None, "veces_ejecutado": 0, "porcentaje": 0, "desglose": {}}
        total = sum(conteo.values())
        lider = max(conteo, key=lambda k: conteo[k])
        pct = round((conteo[lider] * 100) / total) if total > 0 else 0
        return {
            "nombre": lider,
            "veces_ejecutado": conteo[lider],
            "porcentaje": pct,
            "total_ejecuciones": total,
            "desglose": conteo
        }

    return {
        "usuario": calcular_lider(usuario_dict),
        "general": calcular_lider(general_dict)
    }


def reiniciar_alfa_usuario(username: str):
    """Reinicia únicamente el historial Alfa del usuario sin afectar el Alfa General."""
    if not username or not username.strip():
        raise HTTPException(status_code=400, detail="Usuario no especificado.")
    user_key = username.strip().lower()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM historial_alfa WHERE ambito = ?", (user_key,))
        conn.commit()
    return {"status": "success", "mensaje": f"Historial Alfa de '{username}' reiniciado. El Alfa General permanece intacto."}
