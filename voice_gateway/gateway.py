"""Glenda Voice Gateway — Twilio Media Streams ↔ OpenAI Realtime bridge.

Outbound voice. No audio transcoding: both legs speak g711 µ-law @ 8 kHz, so we relay
base64 payloads straight through.

    Odoo ──POST /place-call──► gateway ──Twilio REST──► PSTN call
    Twilio Voice ──Media Streams (g711_ulaw, WS /media)──► gateway ──WS──► OpenAI Realtime
    Twilio ──POST /call-status──► gateway ──┐
    gateway (transcript on hangup) ─────────┴──POST──► Odoo /ai-agent/voice/callback

Run:  uvicorn gateway:app --host 0.0.0.0 --port 8090   (systemd: glenda-voice.service)
⚠️ Runs as its OWN service — never inside an Odoo worker.
"""

import asyncio
import json
import logging

import requests
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from config_loader import (get_openai_key, get_public_base_url, get_settings,
                           twilio_client)
from glenda_instructions import GREETING_HINT, build_instructions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("glenda-voice")

SETTINGS = get_settings()
OPENAI_API_KEY = get_openai_key()
PUBLIC_HOST = SETTINGS.get("public_host", "localhost:8090")
DEFAULT_MODEL = SETTINGS.get("realtime_model", "gpt-realtime-2")
DEFAULT_VOICE = SETTINGS.get("voice", "sage")
HANGUP_DELAY = float(SETTINGS.get("hangup_delay_seconds", 3.0))   # let farewell audio drain
MAX_CALL_SECONDS = int(SETTINGS.get("max_call_seconds", 360))     # hard cost/safety cap

# Realtime function tools — LIVE data fetched from Odoo (static facts stay in the prompt).
TOOLS = [
    {
        "type": "function",
        "name": "get_pricing",
        "description": (
            "Devuelve las tarifas oficiales 2026-2027 del colegio (inscripción, "
            "mensualidad por número de hijos, descuentos por hermanos, costos anuales) "
            "Y las fechas/ventanas de inscripción (llamados). Úsala SIEMPRE que pregunten "
            "por precios, mensualidad, costo, inscripción o cuándo inscribirse."),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "get_balance",
        "description": (
            "Consulta el saldo pendiente (facturas por cobrar) de un representante por su "
            "cédula. Úsala SOLO cuando el representante pida su saldo o deuda y proporcione "
            "su cédula. Si no la tiene, pídela primero."),
        "parameters": {
            "type": "object",
            "properties": {
                "cedula": {"type": "string",
                           "description": "Cédula del representante, ej. V-12345678"},
            },
            "required": ["cedula"],
        },
    },
    {
        "type": "function",
        "name": "end_call",
        "description": (
            "Finaliza y cuelga la llamada. Úsala cuando la persona se despida "
            "(gracias, adiós, hasta luego) o indique que no tiene más preguntas — "
            "SIEMPRE después de despedirte brevemente. No alargues la llamada."),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "record_survey_vote",
        "description": (
            "Registra el voto del representante en la encuesta ligada a esta llamada "
            "(p.ej. el Plan de Contingencia Académica). Úsala SOLO después de: (1) confirmar "
            "que hablas con el representante, y (2) que exprese claramente su decisión. "
            "decision='si' = está de acuerdo / Opción A; decision='no' = no está de acuerdo / Opción B. "
            "Tras registrar, confírmale verbalmente que su voto quedó registrado."),
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["si", "no"],
                             "description": "'si' = de acuerdo; 'no' = no de acuerdo"},
            },
            "required": ["decision"],
        },
    },
]

# Per-call context keyed by Twilio CallSid (set at /place-call, read in /media + /call-status).
CALL_CONTEXT: dict[str, dict] = {}

app = FastAPI(title="Glenda Voice Gateway")


@app.get("/health")
async def health():
    return {"ok": True, "model": DEFAULT_MODEL, "voice": DEFAULT_VOICE}


# ----------------------------------------------------------------- place a call
@app.post("/place-call")
async def place_call(request: Request):
    """Odoo → gateway: dial a contact and bridge Glenda."""
    body = await request.json()
    to = body.get("to")
    if not to:
        return {"error": "missing 'to'"}
    base = get_public_base_url()
    if not base:
        return {"error": "gateway has no public URL (tunnel/host) for Twilio callbacks"}

    client, tw = twilio_client()
    from_ = body.get("caller_id") or tw["from_number"]
    try:
        call = await asyncio.to_thread(
            client.calls.create,
            to=to, from_=from_,
            url=f"{base}/twiml",
            status_callback=f"{base}/call-status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
            status_callback_method="POST",
        )
    except Exception as e:
        _log.exception("place-call failed")
        return {"error": str(e)}

    CALL_CONTEXT[call.sid] = {
        "reason": body.get("reason", ""),
        "voice": body.get("voice") or DEFAULT_VOICE,
        "model": body.get("model") or DEFAULT_MODEL,
        "odoo_call_id": body.get("odoo_call_id"),
        "callback_url": body.get("callback_url"),
        "tool_url": body.get("tool_url"),
        "callback_token": body.get("callback_token"),
    }
    _log.info("place-call sid=%s to=%s from=%s", call.sid, to, from_)
    return {"sid": call.sid, "from": from_}


# ---------------------------------------------------------- Twilio status hook
@app.post("/call-status")
async def call_status(request: Request):
    """Twilio → gateway: call lifecycle events. Forward status+duration to Odoo."""
    form = dict(await request.form())
    call_sid = form.get("CallSid", "")
    raw_status = form.get("CallStatus", "")
    duration = form.get("CallDuration")
    status = raw_status.replace("-", "_")  # no-answer → no_answer
    _log.info("call-status sid=%s status=%s dur=%s", call_sid, raw_status, duration)
    ctx = CALL_CONTEXT.get(call_sid, {})
    payload = {"twilio_sid": call_sid, "status": status}
    if duration:
        payload["duration"] = int(duration)
    _notify_odoo(ctx, payload)
    return HTMLResponse(content="", media_type="application/xml")


@app.api_route("/twiml", methods=["GET", "POST"])
async def twiml(request: Request):
    """TwiML: tell Twilio to open a bidirectional Media Stream to /media."""
    form = dict(await request.form()) if request.method == "POST" else {}
    call_sid = form.get("CallSid", request.query_params.get("CallSid", ""))
    host = request.headers.get("host") or PUBLIC_HOST
    _log.info("TwiML for CallSid=%s host=%s", call_sid, host)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{host}/media" />
  </Connect>
</Response>"""
    return HTMLResponse(content=xml, media_type="application/xml")


# --------------------------------------------------------------- media bridge
@app.websocket("/media")
async def media(ws: WebSocket):
    await ws.accept()
    _log.info("Twilio media stream connected")
    stream_sid = call_sid = None
    ctx = {}
    transcript: list[tuple[str, str]] = []

    # Wait for Twilio's "start" event to learn CallSid → per-call context.
    try:
        while True:
            data = json.loads(await ws.receive_text())
            if data.get("event") == "start":
                stream_sid = data["start"]["streamSid"]
                call_sid = data["start"].get("callSid")
                ctx = CALL_CONTEXT.get(call_sid, {})
                break
            if data.get("event") == "stop":
                return
    except WebSocketDisconnect:
        return

    reason = ctx.get("reason", "")
    voice = ctx.get("voice", DEFAULT_VOICE)
    model = ctx.get("model", DEFAULT_MODEL)
    _log.info("Stream start sid=%s call=%s voice=%s model=%s", stream_sid, call_sid, voice, model)

    openai_url = f"wss://api.openai.com/v1/realtime?model={model}"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    try:
        async with websockets.connect(openai_url, additional_headers=headers, max_size=None) as oai:
            await oai.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "instructions": build_instructions(reason),
                    "output_modalities": ["audio"],
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcmu"},
                            "turn_detection": {
                                "type": "server_vad", "threshold": 0.5,
                                "prefix_padding_ms": 300, "silence_duration_ms": 600,
                                "create_response": True,
                            },
                            "transcription": {"model": "whisper-1"},
                        },
                        "output": {"voice": voice, "format": {"type": "audio/pcmu"}},
                    },
                    "tools": TOOLS,
                    "tool_choice": "auto",
                },
            }))
            # Glenda speaks first.
            await oai.send(json.dumps({"type": "response.create",
                                       "response": {"instructions": GREETING_HINT}}))

            async def twilio_to_openai():
                async for raw in ws.iter_text():
                    data = json.loads(raw)
                    ev = data.get("event")
                    if ev == "media":
                        await oai.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"],
                        }))
                    elif ev == "stop":
                        break

            async def run_tool(call_id, name, arguments_str):
                """Execute a function tool against Odoo, feed result back to the model."""
                try:
                    arguments = json.loads(arguments_str or "{}")
                except Exception:
                    arguments = {}

                # Hang up: ack the tool, let the farewell audio drain, then end the
                # Twilio call via its Call SID. No response.create (conversation is over).
                if name == "end_call":
                    await oai.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {"type": "function_call_output", "call_id": call_id,
                                 "output": json.dumps({"ok": True})},
                    }))
                    _log.info("end_call requested → hanging up %s in %ss", call_sid, HANGUP_DELAY)
                    await asyncio.sleep(HANGUP_DELAY)
                    await _hangup(call_sid)
                    return

                result = {}
                tool_url = ctx.get("tool_url")
                if tool_url:
                    body = {"jsonrpc": "2.0", "method": "call", "params": {
                        "name": name, "arguments": arguments,
                        "odoo_call_id": ctx.get("odoo_call_id"),
                        "callback_token": ctx.get("callback_token")}}
                    try:
                        resp = await asyncio.to_thread(
                            lambda: requests.post(tool_url, json=body, timeout=12))
                        result = resp.json().get("result", {})
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": "no tool_url configured"}
                _log.info("tool %s(%s) → %s", name, arguments, str(result)[:120])
                await oai.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {"type": "function_call_output", "call_id": call_id,
                             "output": json.dumps(result, ensure_ascii=False)},
                }))
                await oai.send(json.dumps({"type": "response.create"}))

            async def openai_to_twilio():
                async for raw in oai:
                    msg = json.loads(raw)
                    t = msg.get("type")
                    if t == "response.output_audio.delta":
                        await ws.send_text(json.dumps({
                            "event": "media", "streamSid": stream_sid,
                            "media": {"payload": msg["delta"]},
                        }))
                    elif t == "input_audio_buffer.speech_started":
                        await ws.send_text(json.dumps({"event": "clear", "streamSid": stream_sid}))
                    elif t == "conversation.item.input_audio_transcription.completed":
                        transcript.append(("Cliente", msg.get("transcript", "")))
                    elif t == "response.output_audio_transcript.done":
                        transcript.append(("Glenda", msg.get("transcript", "")))
                    elif t == "response.function_call_arguments.done":
                        # Run the tool without blocking the receive loop.
                        asyncio.create_task(run_tool(
                            msg.get("call_id"), msg.get("name"), msg.get("arguments")))
                    elif t == "error":
                        _log.error("OpenAI error: %s", msg.get("error"))

            async def watchdog():
                await asyncio.sleep(MAX_CALL_SECONDS)
                _log.info("max call duration (%ss) reached → hangup %s", MAX_CALL_SECONDS, call_sid)
                await _hangup(call_sid)

            t1 = asyncio.create_task(twilio_to_openai())
            t2 = asyncio.create_task(openai_to_twilio())
            t3 = asyncio.create_task(watchdog())
            _done, pending = await asyncio.wait({t1, t2, t3}, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()

    except websockets.exceptions.ConnectionClosed:
        _log.info("OpenAI connection closed")
    except Exception:
        _log.exception("media bridge error")
    finally:
        _log.info("Call bridge ended sid=%s", stream_sid)
        if transcript:
            text = "\n".join(f"{spk}: {txt}" for spk, txt in transcript if txt)
            _notify_odoo(ctx, {"twilio_sid": call_sid, "transcript": text})
        CALL_CONTEXT.pop(call_sid, None)


# --------------------------------------------------------------------- helpers
async def _hangup(call_sid: str):
    """End a live call via its Twilio Call SID (REST), best-effort."""
    if not call_sid:
        return
    try:
        client, _ = twilio_client()
        await asyncio.to_thread(lambda: client.calls(call_sid).update(status="completed"))
        _log.info("hung up call %s", call_sid)
    except Exception as e:
        _log.warning("hangup failed for %s: %s", call_sid, e)


def _notify_odoo(ctx: dict, fields: dict):
    """POST an update to Odoo's voice callback (JSON-RPC envelope), best-effort."""
    url = (ctx or {}).get("callback_url")
    if not url:
        return
    body = dict(fields)
    body["odoo_call_id"] = ctx.get("odoo_call_id")
    if ctx.get("callback_token"):
        body["callback_token"] = ctx["callback_token"]
    try:
        # Odoo type='json' controllers expect a JSON-RPC envelope.
        requests.post(url, json={"jsonrpc": "2.0", "method": "call", "params": body},
                      timeout=10)
    except Exception as e:
        _log.warning("Odoo callback failed: %s", e)
