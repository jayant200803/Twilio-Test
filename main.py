"""
Twilio WebRTC Softphone
=======================

A browser-based phone (softphone) built on Twilio's Voice JavaScript SDK
(which uses WebRTC). It lets you:
  * make OUTBOUND calls   - type a number, it rings a real phone
  * receive INBOUND calls - a call to your Twilio number rings in the browser

You give it your Twilio Account SID + Auth Token (and your Twilio phone
number). The backend then, using the Twilio REST API:
  1. creates an API Key + Secret (needed to sign access tokens),
  2. creates a TwiML App whose Voice URL points back to this server's /voice,
  3. points your Twilio number's incoming-call webhook at /voice,
  4. issues a short-lived Access Token the browser SDK uses to connect.

Security notes:
  * The Auth Token only ever travels browser -> this backend over HTTPS and is
    kept in server memory. It is never exposed to the WebRTC layer.
  * The browser only ever receives the short-lived Access Token, never the
    Auth Token.

This is a demo: config is stored in memory and resets on restart.
"""
from __future__ import annotations

import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse, Dial

app = FastAPI(title="Twilio WebRTC Softphone")

IDENTITY = "webuser"          # the browser client's identity
CONFIG: dict = {}             # filled in by /setup


# ---------------------------------------------------------------------------
# 1. SETUP — take credentials, provision everything via the Twilio REST API
# ---------------------------------------------------------------------------
@app.post("/setup")
async def setup(
    account_sid: str = Form(...),
    auth_token: str = Form(...),
    phone_number: str = Form(...),
    base_url: str = Form(...),          # public URL of THIS server (https://...)
):
    """Provision API key, TwiML app, and inbound webhook. Called once from the UI."""
    step = "connect to Twilio"
    try:
        client = Client(account_sid, auth_token)
        voice_url = base_url.rstrip("/") + "/voice"

        step = "create API Key (new_keys.create)"
        # (a) create an API Key + Secret to sign access tokens
        key = client.new_keys.create(friendly_name="softphone-key")

        step = "find/create TwiML App"
        # (b) get a TwiML App pointing to our /voice (used for outbound).
        # Trial accounts can't CREATE a TwiML App via the API, so if one named
        # "softphone-app" already exists (made by hand in the Console), reuse it
        # and just point its Voice URL at our current /voice. Otherwise try to
        # create it (works on upgraded accounts).
        existing = client.applications.list(friendly_name="softphone-app", limit=1)
        if existing:
            twiml_app = existing[0].update(voice_url=voice_url, voice_method="POST")
        else:
            twiml_app = client.applications.create(
                friendly_name="softphone-app",
                voice_url=voice_url,
                voice_method="POST",
            )

        step = "update number webhook (incoming_phone_numbers)"
        # (c) point the Twilio number's incoming webhook at /voice (for inbound)
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if numbers:
            numbers[0].update(voice_url=voice_url, voice_method="POST")

        CONFIG.update(
            account_sid=account_sid,
            api_key_sid=key.sid,
            api_key_secret=key.secret,
            app_sid=twiml_app.sid,
            phone_number=phone_number,
        )
        return {"status": "ok", "twiml_app_sid": twiml_app.sid, "voice_url": voice_url}
    except Exception as exc:
        return JSONResponse(status_code=400, content={"status": "error", "detail": f"[step: {step}] {exc}"})


# ---------------------------------------------------------------------------
# 2. TOKEN — issue a short-lived Access Token for the browser SDK
# ---------------------------------------------------------------------------
@app.get("/token")
async def token():
    if not CONFIG:
        return JSONResponse(status_code=400, content={"detail": "Run /setup first"})

    at = AccessToken(
        CONFIG["account_sid"], CONFIG["api_key_sid"], CONFIG["api_key_secret"],
        identity=IDENTITY,
    )
    at.add_grant(VoiceGrant(
        outgoing_application_sid=CONFIG["app_sid"],
        incoming_allow=True,          # allow this client to RECEIVE calls
    ))
    jwt = at.to_jwt()
    if isinstance(jwt, bytes):
        jwt = jwt.decode()
    return {"token": jwt, "identity": IDENTITY}


# ---------------------------------------------------------------------------
# 3. VOICE — TwiML that tells Twilio what to do on each call
# ---------------------------------------------------------------------------
@app.post("/voice")
async def voice(request: Request):
    """Handles BOTH directions:
       * Outbound (from the browser SDK): the client sends a 'PhoneNumber'
         param, so we Dial that real number using the Twilio number as caller ID.
       * Inbound (from the phone network): no 'PhoneNumber' param, so we Dial
         the browser client so it rings in the browser.
    """
    form = await request.form()
    number = form.get("PhoneNumber")
    resp = VoiceResponse()

    if number:
        # OUTBOUND: browser -> real phone
        dial = Dial(caller_id=CONFIG.get("phone_number"))
        dial.number(number)
        resp.append(dial)
    else:
        # INBOUND: real phone -> browser
        dial = Dial()
        dial.client(IDENTITY)
        resp.append(dial)

    return Response(content=str(resp), media_type="application/xml")


# ---------------------------------------------------------------------------
# Serve the dialer UI
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join("static", "index.html"))


@app.get("/health")
async def health():
    return {"status": "ok", "configured": bool(CONFIG)}
