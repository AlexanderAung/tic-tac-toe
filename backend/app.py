from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/api/health", methods=["GET"])
def health():
    return {"status": "ok", "message": "Flask is connected!"}