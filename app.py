from flask import Flask, render_template_string
import psutil
import shutil

import os

# Configurar Flask para servir la carpeta 'palomas' como estática
app = Flask(__name__, static_folder="palomas", static_url_path="/palomas")

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
        cpu=cpu,
        ram_used=ram_used,
        ram_total=ram_total,
        ram_percent=ram_percent,
        disk_free=disk_free,
        disk_total=disk_total,
        status_img=status_img
    )

if __name__ == "__main__":
    app.run(debug=True)