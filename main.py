import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from groq import Groq
import edge_tts

app = FastAPI()

# Inicializar el cliente con la API Key de Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

historial_conversacion = []

SYSTEM_PROMPT = """Eres zay, el asistente personal de IA definitivo.
Eres leal, elegante, eficiente y ligeramente sarcástico.
Pero tambien eres alguien divertido.
Respondes siempre en español de forma breve, concisa y dirigiéndote al usuario como 'zaylas'.
Si el usuario hace una consulta, analiza la situación rápidamente y da respuestas útiles y breves."""

@app.post("/procesar")
async def procesar(prompt: str = Form(...), dispositivo: str = Form("desconocido")):
    global historial_conversacion
    
    historial_conversacion.append({"role": "user", "content": f"({dispositivo}): {prompt}"})
    
    # Mantenemos las últimas 8 interacciones en el historial
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}] + historial_conversacion[-8:]

    # Llamada al modelo gratuito de Groq (Llama 3 70B)
    chat_completion = client.chat.completions.create(
        messages=mensajes,
        model="llama-3.3-70b-versatile",
    )
    
    respuesta_texto = chat_completion.choices[0].message.content
    historial_conversacion.append({"role": "assistant", "content": respuesta_texto})

    # Generación del archivo de audio con edge-tts
    archivo_audio = "respuesta.mp3"
    communicate = edge_tts.Communicate(respuesta_texto, "es-ES-AlvaroNeural")
    await communicate.save(archivo_audio)

    return FileResponse(archivo_audio, media_type="audio/mpeg")
