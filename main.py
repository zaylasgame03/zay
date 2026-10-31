import os
import sqlite3
import re
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from groq import Groq
import edge_tts

app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Base de datos SQLite para persistencia
DB_FILE = "zay_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def guardar_mensaje(user_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historial (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def obtener_historial(user_id: str, limite: int = 10):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM historial WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limite))
    filas = cursor.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in reversed(filas)]

MODELOS_GROQ = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b"
]

SYSTEM_PROMPT = """Eres ZAY, el asistente táctico definitivo de IA.
Eres leal, eficiente, estratégico y divertido.
Respondes siempre en español de forma directa y breve. Te diriges al usuario como 'zaylas'.
Si el usuario te pide abrir una aplicación (ej. 'abre WhatsApp'), incluye exactamente este comando en tu respuesta: [ABRIR: nombre_de_app]."""

@app.post("/procesar")
async def procesar(
    prompt: str = Form(...),
    modo_salida: str = Form("audio"), # "audio" o "texto"
    captura_pantalla: UploadFile = File(None),
    foto_camara: UploadFile = File(None),
    user_id: str = Form("zaylas_main"),
    dispositivo: str = Form("android_app")
):
    if not client:
        return JSONResponse(status_code=500, content={"error": "GROQ_API_KEY no configurada."})

    mensaje_usuario = prompt
    if captura_pantalla:
        mensaje_usuario = f"[Captura de pantalla recibida]: {prompt}"
    elif foto_camara:
        mensaje_usuario = f"[Foto de cámara recibida]: {prompt}"

    guardar_mensaje(user_id, "user", mensaje_usuario)
    historial = obtener_historial(user_id, limite=8)
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial

    respuesta_texto = None
    ultimo_error = None

    for modelo in MODELOS_GROQ:
        try:
            chat_completion = client.chat.completions.create(
                messages=mensajes,
                model=modelo,
            )
            respuesta_texto = chat_completion.choices[0].message.content
            break
        except Exception as e:
            ultimo_error = str(e)
            continue

    if not respuesta_texto:
        return JSONResponse(status_code=500, content={"error": f"Error en modelos: {ultimo_error}"})

    guardar_mensaje(user_id, "assistant", respuesta_texto)

    # Extraer comandos de ejecución de apps
    app_target = None
    match = re.search(r"\[ABRIR:\s*(.*?)\]", respuesta_texto)
    if match:
        app_target = match.group(1).strip()
        respuesta_texto = re.sub(r"\[ABRIR:\s*.*?\]", "", respuesta_texto).strip()

    # Devolución para modo silencioso/nocturno
    if modo_salida == "texto":
        return JSONResponse(content={
            "modo": "texto",
            "respuesta": respuesta_texto,
            "abrir_app": app_target
        })

    # Generación y devolución de Audio para modo normal
    archivo_audio = "respuesta.mp3"
    communicate = edge_tts.Communicate(respuesta_texto, "es-ES-AlvaroNeural")
    await communicate.save(archivo_audio)

    headers = {}
    if app_target:
        headers["X-Abrir-App"] = app_target

    return FileResponse(archivo_audio, media_type="audio/mpeg", headers=headers)
