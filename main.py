import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from groq import Groq
import edge_tts

app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

historial_conversacion = []

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

    try:
        historial_conversacion.append({"role": "user", "content": f"({dispositivo}): {prompt}"})
        mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial_conversacion[-8:]

        # Consulta al modelo de Groq
        chat_completion = client.chat.completions.create(
            messages=mensajes,
            model="llama-3.1-8b-instant",
        )
        
        respuesta_texto = chat_completion.choices[0].message.content
        historial_conversacion.append({"role": "assistant", "content": respuesta_texto})

        # Generar audio con edge-tts
        archivo_audio = "respuesta.mp3"
        communicate = edge_tts.Communicate(respuesta_texto, "es-ES-AlvaroNeural")
        await communicate.save(archivo_audio)

        return FileResponse(archivo_audio, media_type="audio/mpeg")

    except Exception as e:
        print(f"Error interno: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
