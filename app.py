from flask import Flask, render_template_string
import psutil
import shutil
from flask_cors import CORS
import requests

import os

# Configurar Flask para servir la carpeta 'palomas' como estática
app = Flask(__name__, static_folder="palomas", static_url_path="/palomas")
CORS(app)


URLS = [
    "https://cmasccp.cl",
    "https://sensores.cmasccp.cl",
    "https://cmpc.cmasccp.cl",
    "https://dictuc.cmasccp.cl",
    "https://intravision.cmasccp.cl",
]

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Estado Servidor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .stat { margin-bottom: 15px; }
        .status-img { width: 120px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Uso de Recursos del Servidor</h1>
    <img class="status-img" src="/palomas/{{ status_img }}" alt="Estado recursos">
    <div class="stat"><strong>Uso de CPU:</strong> {{ cpu }}%</div>
    <div class="stat"><strong>Uso de RAM:</strong> {{ ram_used }} MB / {{ ram_total }} MB ({{ ram_percent }}%)</div>
    <div class="stat"><strong>Espacio Libre en Disco:</strong> {{ disk_free }} GB / {{ disk_total }} GB</div>

           <h3>Status Checker</h3>
        <table border="1" cellpadding="5">
            <tr>
                <th>URL</th>
                <th>Status</th>
                <th>HTTP Code</th>
                <th>Error</th>
            </tr>
            {% for r in results %}
            <tr>
                <td>{{ r.url }}</td>
                <td>{{ r.status }}</td>
                <td>{{ r.code or '-' }}</td>
                <td style="color:red;">{{ r.error or '' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
</html>
"""

@app.route("/")
def index():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    ram_used = round(mem.used / (1024 ** 2))
    ram_total = round(mem.total / (1024 ** 2))
    ram_percent = mem.percent
    disk = shutil.disk_usage("/")
    disk_free = round(disk.free / (1024 ** 3), 2)
    disk_total = round(disk.total / (1024 ** 3), 2)

    # Lógica para determinar el estado
    # Si CPU > 80% o RAM > 90% o menos del 20% de disco libre, mostrar 'mal.png', si no 'normal.png'
    if cpu > 80 or ram_percent > 90 or (disk_free / disk_total) < 0.2:
        status_img = "mal.png"
    elif cpu < 50 and ram_percent < 50 and (disk_free / disk_total) > 0.5:
        status_img = "bien.png"
    else:
        status_img = "normal.png"

    return render_template_string(
        TEMPLATE,
        results=[check_url(url) for url in URLS],
        cpu=cpu,
        ram_used=ram_used,
        ram_total=ram_total,
        ram_percent=ram_percent,
        disk_free=disk_free,
        disk_total=disk_total,
        status_img=status_img
    )



def check_url(url):
    try:
        response = requests.get(url, timeout=5)
        return {
            "url": url,
            "status": "Online 🟢" if response.ok else "Offline 🔴",
            "code": response.status_code,
            "error": None
        }
    except requests.RequestException as e:
        return {
            "url": url,
            "status": "Offline 🔴",
            "code": None,
            "error": str(e)
        }

@app.route('/pages')
def pages():
    results = [check_url(url) for url in URLS]
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Status Checker</title>
    </head>
    <body>
        <h3>Status Checker</h3>
        <table border="1" cellpadding="5">
            <tr>
                <th>URL</th>
                <th>Status</th>
                <th>HTTP Code</th>
                <th>Error</th>
            </tr>
            {% for r in results %}
            <tr>
                <td>{{ r.url }}</td>
                <td>{{ r.status }}</td>
                <td>{{ r.code or '-' }}</td>
                <td style="color:red;">{{ r.error or '' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, results=results)

if __name__ == "__main__":
    app.run(debug=True)