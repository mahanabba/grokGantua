from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def ping():
    return "✅ Bot is alive!"

def run_ping_server():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_ping_server).start()
