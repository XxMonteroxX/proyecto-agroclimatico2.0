
"""
Módulo de autenticación y persistencia de usuarios con SQLite.
"""
import sqlite3
import hashlib
import secrets
from pathlib import Path
from pydantic import BaseModel
from fastapi import HTTPException

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "usuarios.db"

def init_db():
    """Crea la tabla de usuarios si no existe al arrancar."""
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
        conn.commit()

# Ejecutar creación de tabla automáticamente al importar
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
    password: str

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
                (usuario_limpio, pass_hash, req.nombre.strip())
            )
            conn.commit()
        return {"status": "success", "mensaje": "Usuario registrado exitosamente."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está registrado.")

def login_usuario(req: LoginRequest):
    usuario_limpio = req.username.strip().lower()
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
            "rol": row[3]
        },
        "token": token
    }
