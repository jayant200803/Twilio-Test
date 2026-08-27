# Twilio WebRTC Softphone

A browser-based phone (softphone) built on **Twilio's Voice JavaScript SDK**
(which uses **WebRTC**). It can:

- **make outbound calls** — type a number, it rings a real phone
- **receive inbound calls** — a call to your Twilio number rings in the browser

You enter your **Twilio Account SID + Auth Token + phone number**, and the
backend provisions everything automatically (API key, TwiML app, inbound
webhook) and issues the access token the browser SDK needs.

Built by Jayant Raj.

---

## How it works (the architecture)

```
Browser dialer (Twilio Voice SDK, WebRTC)
        │  1. /setup  (SID + token + number)
        │  2. /token  (short-lived access token)
        ▼
FastAPI backend  ──uses Twilio REST API──►  Twilio
        ▲                                     │
        │  3. /voice (TwiML: what to do)      │  bridges to the
        └─────────────────────────────────────┘  real phone network (PSTN)
```

- **/setup** — takes your credentials once; via the Twilio REST API it creates
  an API Key+Secret, creates a TwiML App pointing to `/voice`, and points your
  Twilio number's incoming webhook at `/voice`.
- **/token** — issues a short-lived Access Token (JWT) the browser SDK uses.
  Your Auth Token never reaches the browser.
- **/voice** — returns TwiML. Outbound: `<Dial>` the real number. Inbound:
  `<Dial><Client>` the browser.

---

## Prerequisites (in the Twilio Console — one-time)

1. A **Twilio account** (a free trial works; trial accounts can only call
   *verified* numbers).
2. A **Twilio phone number** with **Voice** capability (Console → Phone Numbers
   → Buy a number).
3. Your **Account SID** and **Auth Token** (Console dashboard, top of the page).

That's all you enter into the app — it configures the API key, TwiML app, and
webhook for you.

---

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://localhost:8000

> Note: for **inbound** calls to work, Twilio must be able to reach your
> `/voice` URL over the internet, so local testing of inbound needs a public
> tunnel (e.g. `ngrok http 8000`) or a deploy. Outbound works locally as long
> as the browser can reach Twilio.

---

## Deploy (recommended, so inbound works and it's always reachable)

`render.yaml` and `Procfile` are included.

1. Push this folder to a GitHub repo.
2. render.com → New → Web Service → connect the repo → it reads `render.yaml`.
3. Deploy → you get a public URL like `https://twilio-softphone.onrender.com`.
4. Open that URL, enter your SID / Auth Token / Twilio number, click
   **Set up & Connect**. The app auto-configures Twilio and connects.

---

## Using it

1. Enter **Account SID**, **Auth Token**, and your **Twilio phone number**.
2. Click **Set up & Connect** → status becomes "Connected & ready".
3. **Outbound:** type a destination number → **Call**. (On a trial account the
   destination must be a verified number.)
4. **Inbound:** call your Twilio number from any phone → it rings in the
   browser → **Accept**.
5. Allow the browser **microphone** permission when prompted.

---

## Notes & security

- The **Auth Token** travels only browser → this backend (over HTTPS) and stays
  in server memory; it is never exposed to the WebRTC/browser call layer. The
  browser only receives the short-lived Access Token.
- Config is stored in memory (demo) and resets on restart — just click
  **Set up & Connect** again.
- Trial Twilio accounts: outbound calls only to **verified** numbers, and calls
  play a short trial notice. Upgrade to remove these limits.
- Free Render tier sleeps after ~15 min idle; the first request wakes it (~30s).
