import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from groq import Groq
import edge_tts

app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

historial_conversacion = []

# Lista de modelos candidatos en orden de preferencia
MODELOS_GROQ = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768"
]

SYSTEM_PROMPT = """Eres zay, el asistente personal de IA definitivo.
Eres leal, elegante, eficiente y ligeramente sarcástico.
Pero tambien eres alguien divertido.
Respondes siempre en español de forma breve, concisa y dirigiéndote al usuario como 'zaylas'.
Si el usuario hace una consulta, analiza la situación rápidamente y da respuestas útiles y breves."""

@app.post("/procesar")
async def procesar(
    prompt: str = Form(...),
    file: UploadFile = File(None),
    vision: str = Form("false"),
    dispositivo: str = Form("desconocido")
):
    global historial_conversacion
    
    if not client:
        return JSONResponse(status_code=500, content={"error": "GROQ_API_KEY no está configurada en Render."})

    historial_conversacion.append({"role": "user", "content": f"({dispositivo}): {prompt}"})
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial_conversacion[-8:]

    respuesta_texto = None
    ultimo_error = None

    # Probar modelos disponibles hasta que uno responda
    for modelo in MODELOS_GROQ:
        try:
            chat_completion = client.chat.completions.create(
                messages=mensajes,
                model=modelo,
            )
            respuesta_texto = chat_completion.choices[0].message.content
            print(f"Éxito con el modelo: {modelo}")
            break
        except Exception as e:
            ultimo_error = str(e)
            print(f"Fallo con {modelo}: {ultimo_error}")
            continue

    if not respuesta_texto:
        return JSONResponse(status_code=500, content={"error": f"Ningún modelo respondió. Último error: {ultimo_error}"})

    historial_conversacion.append({"role": "assistant", "content": respuesta_texto})

    # Generar audio con edge-tts
    archivo_audio = "respuesta.mp3"
    communicate = edge_tts.Communicate(respuesta_texto, "es-ES-AlvaroNeural")
    await communicate.save(archivo_audio)

    return FileResponse(archivo_audio, media_type="audio/mpeg")
