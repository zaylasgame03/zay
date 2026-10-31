import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from google import genai
import edge_tts

app = FastAPI()

GENAI_API_KEY = os.getenv("GENAI_API_KEY")
client = genai.Client(api_key=GENAI_API_KEY)

historial_conversacion = []
frame_actual_juego = "frame_juego.png"

SYSTEM_PROMPT = """Eres zay, el asistente personal de IA definitivo.
Eres leal, elegante, eficiente y ligeramente sarcástico.
Pero tambien eres alguien divertido.
Respondes siempre en español de forma breve, concisa y dirigiéndote al usuario como 'zaylas'.
Si recibes una imagen de un videojuego o pantalla, analiza la situación rápidamente y da consejos estratégicos en tiempo real."""

@app.post("/stream_frame")
async def recibir_frame(frame: UploadFile = File(...)):
    contenido = await frame.read()
    with open(frame_actual_juego, "wb") as f:
        f.write(contenido)
    return {"status": "ok"}

@app.post("/procesar")
async def procesar(prompt: str = Form(...), vision: str = Form("false"), dispositivo: str = Form("desconocido")):
    global historial_conversacion
    
    historial_conversacion.append(f"Usuario ({dispositivo}): {prompt}")
    contexto = "\n".join(historial_conversacion[-8:])
    
    prompt_completo = f"{SYSTEM_PROMPT}\n\nHistorial reciente:\n{contexto}\n\nMensaje actual de {dispositivo}: {prompt}"
    archivos_gemini = [prompt_completo]
    
    if vision == "true" and os.path.exists(frame_actual_juego):
        imagen_subida = client.files.upload(file=frame_actual_juego)
        archivos_gemini.append(imagen_subida)

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=archivos_gemini
    )
    respuesta_texto = response.text
    historial_conversacion.append(f"JARVIS: {respuesta_texto}")

    archivo_audio = "respuesta.mp3"
    communicate = edge_tts.Communicate(respuesta_texto, "es-ES-AlvaroNeural")
    await communicate.save(archivo_audio)

    return FileResponse(archivo_audio, media_type="audio/mpeg")
