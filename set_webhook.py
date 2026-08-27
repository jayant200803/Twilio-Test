"""
One-off helper: point your Twilio phone number's incoming-call webhook at the
deployed /voice URL, using the Twilio REST API.

Why: some trial accounts block the Console's number-config UI behind an upgrade,
but updating an existing number via the API is allowed. Your Auth Token is read
from the environment and never leaves your machine.

Usage (PowerShell):
    $env:TWILIO_ACCOUNT_SID = "ACxxxxxxxx"
    $env:TWILIO_AUTH_TOKEN  = "your auth token"
    python set_webhook.py
"""
import os
import sys
from twilio.rest import Client

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "+17372508034")
VOICE_URL = os.environ.get(
    "VOICE_URL", "https://twilio-test-eosin-three.vercel.app/voice"
)

if not ACCOUNT_SID or not AUTH_TOKEN:
    sys.exit("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables first.")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

numbers = client.incoming_phone_numbers.list(phone_number=PHONE_NUMBER)
if not numbers:
    sys.exit(f"No Twilio number matching {PHONE_NUMBER} found on this account.")

updated = numbers[0].update(voice_url=VOICE_URL, voice_method="POST")
print("Success! Incoming-call webhook set.")
print(f"  Number:    {updated.phone_number}")
print(f"  Voice URL: {updated.voice_url}")
print(f"  Method:    {updated.voice_method}")
