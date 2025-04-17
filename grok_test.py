# grok_console.py
import os, sys, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("XAI_API_KEY")
if not API_KEY:
    print("⚠️  Set XAI_API_KEY in your .env"); sys.exit(1)

BASE_URL = "https://api.x.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ——— YOUR REFINED PROMPTS ———
SYSTEM_PROMPT = (
    "You are an AI that writes a Lil X choose‑your‑own‑adventure on Mars. "
    "Mentally track karma: one morally Good choice, one morally Bad. "
    "End with exactly two choices labeled:\n"
    "  Good: <25 chars\n"
    "  Bad:  <25 chars\n"
    "Don't mention word counts."
)

INITIAL_USER_PROMPT = (
    "Lil X is stranded on Mars, craving to see his dad Elon. "
    "He’s haunted by a cosmic deity, grokGantua, which holds the answers to the universe"
    "Write 125–175 words in second‑person perspective."
)

def chat(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": "grok-3-mini",
        "temperature": 0.6,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    }
    r = requests.post(f"{BASE_URL}/chat/completions",
                      headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def main():
    # 1) Send the one‑time initial prompt
    print("\nGrok ▶", chat(SYSTEM_PROMPT, INITIAL_USER_PROMPT), "\n")

    # 2) Then let you keep typing follow‑up user prompts
    while True:
        user_p = input("You ▶ ").strip()
        if user_p.lower() in ("quit", "exit"):
            print("👋 Bye!"); break

        try:
            reply = chat(SYSTEM_PROMPT, user_p)
            print("\nGrok ▶", reply, "\n")
        except Exception as e:
            print("❌ Error:", e, "\n")

if __name__ == "__main__":
    main()
