from flask import Flask, render_template_string, jsonify, request
import psutil
import shutil
from flask_cors import CORS
import requests
import datetime
import time

import os
import platform
import subprocess

# Contraseña sudo embebida en el código (solicitado)
SUDO_PASSWORD = "Investigacion2023"

# Configurar Flask para servir la carpeta 'palomas' como estática
app = Flask(__name__, static_folder="palomas", static_url_path="/palomas")
CORS(app)


URLS = [
    "https://cmasccp.cl",
    "https://api-sensores.cmasccp.cl/apidocs",
    "https://sensores.cmasccp.cl",
    "https://cmpc.cmasccp.cl",
    "https://dictuc.cmasccp.cl",
    "https://intravision.cmasccp.cl",
    "https://eolo.cmasccp.cl",
    "https://api-eolo.cmasccp.cl",
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
        .loading { opacity: 0.6; }
        .last-update { font-size: 12px; color: #666; margin-top: 20px; }
        
        /* Estilos para la tabla y enlaces */
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { padding: 10px; text-align: left; border: 1px solid #ddd; }
        th { background-color: #f2f2f2; font-weight: bold; }
        
        /* Estilos para los enlaces */
        a { 
            color: #0066cc; 
            text-decoration: none; 
            transition: color 0.3s ease;
        }
        a:hover { 
            color: #004499; 
            text-decoration: underline; 
        }
        a:visited { 
            color: #551a8b; 
        }
        
        /* Responsivo para dispositivos móviles */
        @media (max-width: 600px) {
            table { font-size: 12px; }
            th, td { padding: 5px; }
        }
    </style>
</head>
<body>
    <h1>Uso de Recursos del Servidor</h1>
        <p style="margin-bottom:10px"><a href="/cpu-ui">Ver detalles avanzados de CPU</a></p>
        <p style="margin-bottom:10px"><a href="/ram-ui">Ver detalles avanzados de RAM</a></p>
    <div id="content">
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
                <td><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></td>
                <td>{{ r.status }}</td>
                <td>{{ r.code or '-' }}</td>
                <td style="color:red;">{{ r.error or '' }}</td>
            </tr>
            {% endfor %}
        </table>
        </div>
    <div class="last-update">Última actualización: <span id="lastUpdate">{{ last_update }}</span></div>
    
    <script>
        function updateContent() {
            const content = document.getElementById('content');
            content.classList.add('loading');
            
            fetch('/')
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newContent = doc.getElementById('content').innerHTML;
                    const newLastUpdate = doc.getElementById('lastUpdate').textContent;
                    
                    content.innerHTML = newContent;
                    document.getElementById('lastUpdate').textContent = newLastUpdate;
                    content.classList.remove('loading');
                })
                .catch(error => {
                    console.error('Error actualizando datos:', error);
                    content.classList.remove('loading');
                });
        }
        
        // Actualizar cada 30 segundos
        setInterval(updateContent, 30000);
        
        // Mostrar próxima actualización
        let countdown = 30;
        setInterval(() => {
            countdown--;
            if (countdown <= 0) {
                countdown = 30;
            }
            document.title = `Estado Servidor (próxima actualización en ${countdown}s)`;
        }, 1000);
    </script>
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
    
    # Obtener timestamp actual
    last_update = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Lógica para determinar el estado
    # Si CPU > 80% o RAM > 90% o menos del 20% de disco libre, mostrar 'mal.png', si no 'normal.png'
    if cpu > 80 or ram_percent > 90 :
        status_img = "mal.png"
    elif ram_percent < 50:
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
        status_img=status_img,
        last_update=last_update
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

@app.route('/cpu-ui')
def cpu_ui():
    """Página con visualización amigable del uso de CPU."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>CPU Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            .title { margin: 0 0 8px; font-size: 18px; }
            .subtitle { color: #666; font-size: 12px; margin-bottom: 8px; }
            .kpi { font-size: 28px; font-weight: bold; }
            .row { display: flex; gap: 16px; align-items: baseline; }
            .muted { color: #666; }
            a.btn { display: inline-block; margin-top: 16px; color: #0066cc; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>CPU Dashboard</h1>
        <div class="subtitle">Actualiza cada 5s | <a href="/">← Volver</a></div>
        <div class="grid">
            <div class="card">
                <h3 class="title">Uso global de CPU</h3>
                <div class="row">
                    <div class="kpi" id="overallKpi">--%</div>
                    <div class="muted" id="countsInfo">CPU: -- lógicos / -- físicos</div>
                </div>
                <canvas id="doughnutChart" height="200"></canvas>
            </div>
            <div class="card">
                <h3 class="title">Uso por núcleo</h3>
                <canvas id="perCoreChart" height="200"></canvas>
            </div>
            <div class="card">
                <h3 class="title">Frecuencia</h3>
                <div id="freqInfo" class="muted">Cargando...</div>
            </div>
            <div class="card">
                <h3 class="title">Tiempos de CPU</h3>
                <pre id="timesPre" style="white-space: pre-wrap; margin:0">Cargando...</pre>
            </div>
            <div class="card" style="grid-column: 1 / -1;">
                <h3 class="title">Procesos con mayor uso de CPU</h3>
                <table style="width:100%; border-collapse:collapse">
                    <thead>
                        <tr>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">PID</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Proceso</th>
                            <th style="text-align:right; border-bottom:1px solid #ddd; padding:8px">CPU %</th>
                            <th style="text-align:right; border-bottom:1px solid #ddd; padding:8px">RAM %</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Estado</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="procTableBody"></tbody>
                </table>
                <div class="subtitle" id="procUpdateInfo">—</div>
            </div>
        </div>
        <a class="btn" href="/cpu">Ver JSON crudo</a>

        <script>
            const doughnutCtx = document.getElementById('doughnutChart').getContext('2d');
            const perCoreCtx = document.getElementById('perCoreChart').getContext('2d');

            const doughnutChart = new Chart(doughnutCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Usado', 'Libre'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#ff6384', '#36a2eb'],
                        hoverBackgroundColor: ['#ff6384', '#36a2eb']
                    }]
                },
                options: {
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom' } },
                }
            });

            const perCoreChart = new Chart(perCoreCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU %',
                        data: [],
                        backgroundColor: '#4bc0c0'
                    }]
                },
                options: {
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });

            async function refresh() {
                try {
                    const res = await fetch('/cpu');
                    const data = await res.json();

                    // KPI y doughnut
                    const overall = Math.round((data.overall_percent || 0) * 10) / 10;
                    document.getElementById('overallKpi').textContent = overall + '%';
                    doughnutChart.data.datasets[0].data = [overall, 100 - overall];
                    doughnutChart.update();

                    // Conteo de CPUs
                    const logical = (data.counts && data.counts.logical) ?? '--';
                    const physical = (data.counts && data.counts.physical) ?? '--';
                    document.getElementById('countsInfo').textContent = `CPU: ${logical} lógicos / ${physical} físicos`;

                    // Per-core
                    const perCore = data.per_cpu_percent || [];
                    const labels = perCore.map((_, i) => 'CPU ' + i);
                    perCoreChart.data.labels = labels;
                    perCoreChart.data.datasets[0].data = perCore.map(v => Math.round(v * 10) / 10);
                    perCoreChart.update();

                    // Frecuencia
                    const f = data.frequency;
                    if (f && (f.current || f.max)) {
                        document.getElementById('freqInfo').textContent = `Actual: ${f.current?.toFixed?.(0) ?? f.current} MHz | Máx: ${f.max ?? '--'} MHz | Mín: ${f.min ?? '--'} MHz`;
                    } else {
                        document.getElementById('freqInfo').textContent = 'Frecuencia no disponible en este sistema.';
                    }

                    // Tiempos
                    document.getElementById('timesPre').textContent = JSON.stringify(data.times, null, 2);
                } catch (e) {
                    console.error(e);
                }
            }

            refresh();
            setInterval(refresh, 5000);

            async function refreshProcesses() {
                try {
                    const res = await fetch('/cpu-processes');
                    const data = await res.json();
                    const tbody = document.getElementById('procTableBody');
                    tbody.innerHTML = '';
                    (data.processes || []).forEach(p => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.pid}</td>
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.name}</td>
                            <td style="padding:8px; text-align:right; border-bottom:1px solid #eee">${(p.cpu_percent ?? 0).toFixed ? (p.cpu_percent).toFixed(1) : p.cpu_percent}</td>
                            <td style="padding:8px; text-align:right; border-bottom:1px solid #eee">${(p.memory_percent ?? 0).toFixed ? (p.memory_percent).toFixed(1) : p.memory_percent}</td>
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.status ?? ''}</td>
                            <td style="padding:8px; border-bottom:1px solid #eee">
                                <button onclick="finalizeProcess(${p.pid}, '${(p.name || '').replace(/'/g, "\'")}')" style="padding:6px 10px">Finalizar</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('procUpdateInfo').textContent = `Actualizado: ${data.timestamp || ''}`;
                } catch (e) {
                    console.error(e);
                }
            }

            refreshProcesses();
            setInterval(refreshProcesses, 5000);

            async function finalizeProcess(pid, name) {
                const ok = confirm(`¿Finalizar el proceso ${name} (PID ${pid})?`);
                if (!ok) return;
                try {
                    const res = await fetch('/cpu-processes/kill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pid })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        alert(`Error: ${data.error || 'No se pudo finalizar el proceso.'}`);
                    } else {
                        alert(`Proceso finalizado: ${data.pid}`);
                        refreshProcesses();
                    }
                } catch (e) {
                    alert('Error al finalizar el proceso: ' + e);
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/cpu')
def cpu_details():
    """Devuelve detalles del uso de CPU en formato JSON."""
    # Porcentaje global (intervalo corto para medir) y por CPU
    overall_percent = psutil.cpu_percent(interval=0.5)
    per_cpu_percent = psutil.cpu_percent(percpu=True, interval=0.5)

    # Tiempos de CPU (user, system, idle, etc.)
    times = psutil.cpu_times()
    times_dict = times._asdict() if hasattr(times, '_asdict') else dict(times)

    # Frecuencia de CPU (puede ser None en algunos sistemas)
    freq = psutil.cpu_freq()
    freq_dict = None
    if freq is not None:
        freq_dict = {
            'current': getattr(freq, 'current', None),
            'min': getattr(freq, 'min', None),
            'max': getattr(freq, 'max', None),
        }

    cpu_counts = {
        'logical': psutil.cpu_count(logical=True),
        'physical': psutil.cpu_count(logical=False)
    }

    payload = {
        'overall_percent': overall_percent,
        'per_cpu_percent': per_cpu_percent,
        'times': times_dict,
        'frequency': freq_dict,
        'counts': cpu_counts,
    }
    return jsonify(payload)

@app.route('/ram')
def ram_details():
    """Devuelve detalles del uso de RAM y swap en formato JSON."""
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    def safe_get(obj, name):
        return getattr(obj, name, None)

    payload = {
        'virtual_memory': {
            'total': vm.total,
            'available': vm.available,
            'used': vm.used,
            'free': vm.free,
            'percent': vm.percent,
            'active': safe_get(vm, 'active'),
            'inactive': safe_get(vm, 'inactive'),
            'buffers': safe_get(vm, 'buffers'),
            'cached': safe_get(vm, 'cached'),
            'shared': safe_get(vm, 'shared'),
        },
        'swap_memory': {
            'total': sm.total,
            'used': sm.used,
            'free': sm.free,
            'percent': sm.percent,
            'sin': safe_get(sm, 'sin'),
            'sout': safe_get(sm, 'sout'),
        }
    }
    return jsonify(payload)

@app.route('/ram-processes')
def ram_processes():
    """Top procesos por uso de RAM (JSON)."""
    procs = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'status']):
            try:
                mem_pct = p.info.get('memory_percent')
                if mem_pct is None:
                    try:
                        mem_pct = p.memory_percent()
                    except Exception:
                        mem_pct = None
                rss = None
                try:
                    rss = p.memory_info().rss
                except Exception:
                    rss = None
                procs.append({
                    'pid': p.info.get('pid', p.pid),
                    'name': p.info.get('name', '') or getattr(p, 'name', lambda: '')(),
                    'memory_percent': mem_pct,
                    'rss_bytes': rss,
                    'status': p.info.get('status')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: (x['memory_percent'] or 0), reverse=True)
        top = procs[:15]
        return jsonify({
            'processes': top,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ram-ui')
def ram_ui():
    """Página con visualización amigable del uso de RAM."""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>RAM Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            .title { margin: 0 0 8px; font-size: 18px; }
            .subtitle { color: #666; font-size: 12px; margin-bottom: 8px; }
            .kpi { font-size: 28px; font-weight: bold; }
            .row { display: flex; gap: 16px; align-items: baseline; }
            .muted { color: #666; }
            a.btn { display: inline-block; margin-top: 16px; color: #0066cc; text-decoration: none; }
        </style>
    </head>
    <body>
        <h1>RAM Dashboard</h1>
        <div class="subtitle">Actualiza cada 5s | <a href="/">← Volver</a></div>
        <div class="grid">
            <div class="card">
                <h3 class="title">Uso global de RAM</h3>
                <div class="row">
                    <div class="kpi" id="ramKpi">--%</div>
                    <div class="muted" id="ramInfo">-- / --</div>
                </div>
                <canvas id="ramDoughnut" height="200"></canvas>
            </div>
            <div class="card">
                <h3 class="title">Top procesos por RAM</h3>
                <table style="width:100%; border-collapse:collapse">
                    <thead>
                        <tr>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">PID</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Proceso</th>
                            <th style="text-align:right; border-bottom:1px solid #ddd; padding:8px">RAM %</th>
                            <th style="text-align:right; border-bottom:1px solid #ddd; padding:8px">RSS MB</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Estado</th>
                            <th style="text-align:left; border-bottom:1px solid #ddd; padding:8px">Acciones</th>
                        </tr>
                    </thead>
                    <tbody id="ramProcBody"></tbody>
                </table>
                <div class="subtitle" id="ramProcUpdate">—</div>
            </div>
            <div class="card">
                <h3 class="title">Detalles de Memoria</h3>
                <pre id="ramDetails" style="white-space: pre-wrap; margin:0">Cargando...</pre>
            </div>
            <div class="card">
                <h3 class="title">Swap</h3>
                <div id="swapInfo" class="muted">Cargando...</div>
            </div>
        </div>
        <a class="btn" href="/ram">Ver JSON crudo</a>

        <script>
            const ramCtx = document.getElementById('ramDoughnut').getContext('2d');
            const ramChart = new Chart(ramCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Usado', 'Libre'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#ff9f40', '#36a2eb']
                    }]
                },
                options: { cutout: '70%', plugins: { legend: { position: 'bottom' } } }
            });

            function fmtMB(bytes) {
                if (bytes == null) return '--';
                return (bytes / (1024*1024)).toFixed(0) + ' MB';
            }

            async function refreshRAM() {
                try {
                    const res = await fetch('/ram');
                    const data = await res.json();
                    const vm = data.virtual_memory || {};
                    const usedPct = Math.round((vm.percent || 0) * 10) / 10;
                    document.getElementById('ramKpi').textContent = usedPct + '%';
                    document.getElementById('ramInfo').textContent = `${fmtMB(vm.used)} / ${fmtMB(vm.total)}`;
                    ramChart.data.datasets[0].data = [usedPct, 100 - usedPct];
                    ramChart.update();

                    document.getElementById('ramDetails').textContent = JSON.stringify(vm, null, 2);

                    const sm = data.swap_memory || {};
                    const swapTxt = `Uso swap: ${sm.percent ?? '--'}% | Usado: ${fmtMB(sm.used)} / Total: ${fmtMB(sm.total)}`;
                    document.getElementById('swapInfo').textContent = swapTxt;
                } catch (e) {
                    console.error(e);
                }
            }

            async function refreshRamProcesses() {
                try {
                    const res = await fetch('/ram-processes');
                    const data = await res.json();
                    const tbody = document.getElementById('ramProcBody');
                    tbody.innerHTML = '';
                    (data.processes || []).forEach(p => {
                        const tr = document.createElement('tr');
                        const rssMB = p.rss_bytes ? (p.rss_bytes / (1024*1024)).toFixed(0) : '--';
                        tr.innerHTML = `
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.pid}</td>
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.name}</td>
                            <td style="padding:8px; text-align:right; border-bottom:1px solid #eee">${(p.memory_percent ?? 0).toFixed ? (p.memory_percent).toFixed(1) : p.memory_percent}</td>
                            <td style="padding:8px; text-align:right; border-bottom:1px solid #eee">${rssMB}</td>
                            <td style="padding:8px; border-bottom:1px solid #eee">${p.status ?? ''}</td>
                            <td style=\"padding:8px; border-bottom:1px solid #eee\">
                                <button onclick=\"finalizeRamProcess(${p.pid}, '${(p.name || '').replace(/'/g, '\\\'')}')\" style=\"padding:6px 10px\">Finalizar</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                    document.getElementById('ramProcUpdate').textContent = `Actualizado: ${data.timestamp || ''}`;
                } catch (e) {
                    console.error(e);
                }
            }

            refreshRAM();
            refreshRamProcesses();
            setInterval(refreshRAM, 5000);
            setInterval(refreshRamProcesses, 5000);

            async function finalizeRamProcess(pid, name) {
                const ok = confirm(`¿Finalizar el proceso ${name} (PID ${pid})?`);
                if (!ok) return;
                try {
                    // Reutilizamos el endpoint existente de kill
                    const res = await fetch('/cpu-processes/kill', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pid })
                    });
                    const data = await res.json();
                    if (!res.ok) {
                        alert(`Error: ${data.error || 'No se pudo finalizar el proceso.'}`);
                    } else {
                        alert(`Proceso finalizado: ${data.pid}`);
                        refreshRamProcesses();
                    }
                } catch (e) {
                    alert('Error al finalizar el proceso: ' + e);
                }
            }
        </script>
    </body>
    </html>
    """)

@app.route('/cpu-processes/kill', methods=['POST'])
def kill_process():
    """Finaliza un proceso por PID."""
    try:
        data = request.get_json(silent=True) or {}
        pid = int(data.get('pid'))
    except Exception:
        return jsonify({'error': 'PID inválido'}), 400

    try:
        p = psutil.Process(pid)
        p.terminate()  # Solicitar cierre limpio
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()     # Forzar cierre
        return jsonify({'pid': pid, 'status': 'terminated'})
    except psutil.NoSuchProcess:
        return jsonify({'error': 'Proceso no encontrado'}), 404
    except psutil.AccessDenied:
        # Intentar con privilegios elevados según el sistema operativo
        system = platform.system()
        if system == 'Windows':
            # Intento con taskkill (requiere privilegios; puede fallar si no se ejecuta como admin)
            try:
                result = subprocess.run([
                    'taskkill', '/PID', str(pid), '/F'
                ], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return jsonify({'pid': pid, 'status': 'terminated'}), 200
                else:
                    return jsonify({'error': result.stderr.strip() or 'Acceso denegado en Windows'}), 403
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            # Linux/macOS: usar sudo con contraseña embebida
            sudo_password = SUDO_PASSWORD
            try:
                # TERM primero
                term = subprocess.run(
                    ['sudo', '-S', 'kill', '-TERM', str(pid)],
                    input=sudo_password + '\n', capture_output=True, text=True, timeout=5
                )
                # Verificar si aún existe
                still_exists = True
                try:
                    psutil.Process(pid)
                except psutil.NoSuchProcess:
                    still_exists = False

                if still_exists:
                    # KILL si sigue vivo
                    kill = subprocess.run(
                        ['sudo', '-S', 'kill', '-KILL', str(pid)],
                        input=sudo_password + '\n', capture_output=True, text=True, timeout=5
                    )
                    if kill.returncode != 0:
                        return jsonify({'error': kill.stderr.strip() or 'Fallo al ejecutar sudo kill -KILL'}), 403

                # Confirmar que se terminó
                try:
                    psutil.Process(pid)
                    # Si aún existe, reportar acceso denegado
                    return jsonify({'error': 'No se pudo finalizar el proceso con sudo.'}), 403
                except psutil.NoSuchProcess:
                    return jsonify({'pid': pid, 'status': 'terminated'}), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cpu-processes')
def cpu_processes():
    """Top procesos por uso de CPU (JSON)."""
    procs = []
    try:
        # Primera pasada para "priming" del cálculo de cpu_percent
        for p in psutil.process_iter(['pid', 'name']):
            try:
                p.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(0.3)

        # Segunda pasada: recoger métricas
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'status']):
            try:
                cpu = p.cpu_percent(None)
                mem = p.info.get('memory_percent')
                if mem is None:
                    try:
                        mem = p.memory_percent()
                    except Exception:
                        mem = None
                procs.append({
                    'pid': p.info.get('pid', p.pid),
                    'name': p.info.get('name', '') or getattr(p, 'name', lambda: '')(),
                    'cpu_percent': cpu,
                    'memory_percent': mem,
                    'status': p.info.get('status')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(key=lambda x: (x['cpu_percent'] or 0), reverse=True)
        top = procs[:15]
        return jsonify({
            'processes': top,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pages')
def pages():
    results = [check_url(url) for url in URLS]
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Status Checker</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            
            /* Estilos para la tabla y enlaces */
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { padding: 10px; text-align: left; border: 1px solid #ddd; }
            th { background-color: #f2f2f2; font-weight: bold; }
            
            /* Estilos para los enlaces */
            a { 
                color: #0066cc; 
                text-decoration: none; 
                transition: color 0.3s ease;
            }
            a:hover { 
                color: #004499; 
                text-decoration: underline; 
            }
            a:visited { 
                color: #551a8b; 
            }
            
            /* Responsivo para dispositivos móviles */
            @media (max-width: 600px) {
                table { font-size: 12px; }
                th, td { padding: 5px; }
            }
        </style>
    </head>
    <body>
        <h3>Status Checker</h3>
        <table>
            <tr>
                <th>URL</th>
                <th>Status</th>
                <th>HTTP Code</th>
                <th>Error</th>
            </tr>
            {% for r in results %}
            <tr>
                <td><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></td>
                <td>{{ r.status }}</td>
                <td>{{ r.code or '-' }}</td>
                <td style="color:red;">{{ r.error or '' }}</td>
            </tr>
            {% endfor %}
        </table>
        <br>
        <a href="/" style="font-size: 14px;">← Volver a la página principal</a>
    </body>
    </html>
    """, results=results)

if __name__ == "__main__":
    app.run(debug=True)