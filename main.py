#!/usr/bin/env python3
"""
MO IV Analyzer - Railway Server
Flask API pentru procesarea Monitoarelor Oficiale Partea IV
"""

import os
import re
import json
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename

# Import local modules
from patterns_relaxed import detect_operation, NOISE_OPERATIONS, HIGH_INTEREST_OPERATIONS
from mo_parser_v4 import (
    parse_monitor, 
    generate_html_report, 
    TOP_COMPANII,
    Act
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Landing page HTML
LANDING_PAGE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MO IV Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            overflow: hidden;
        }
        .header {
            background: #1e3a5f;
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { opacity: 0.8; font-size: 14px; }
        .content { padding: 30px; }
        .upload-area {
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s;
            cursor: pointer;
        }
        .upload-area:hover { border-color: #1e3a5f; background: #f8fafc; }
        .upload-area.dragover { border-color: #1e3a5f; background: #dbeafe; }
        .upload-icon { font-size: 48px; margin-bottom: 15px; }
        .upload-text { color: #64748b; margin-bottom: 10px; }
        .upload-hint { font-size: 12px; color: #94a3b8; }
        input[type="file"] { display: none; }
        .btn {
            background: #1e3a5f;
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            transition: background 0.3s;
        }
        .btn:hover { background: #2d5a87; }
        .btn:disabled { background: #94a3b8; cursor: not-allowed; }
        .file-list {
            margin: 15px 0;
            max-height: 150px;
            overflow-y: auto;
        }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f1f5f9;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .file-item .name { color: #334155; }
        .file-item .remove { 
            color: #dc2626; 
            cursor: pointer; 
            font-weight: bold;
            padding: 0 5px;
        }
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
        }
        .status.loading { background: #dbeafe; color: #1e40af; display: block; }
        .status.success { background: #d1fae5; color: #065f46; display: block; }
        .status.error { background: #fee2e2; color: #991b1b; display: block; }
        .footer {
            background: #f8fafc;
            padding: 15px 30px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background: #f8fafc;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-box .value { font-size: 24px; font-weight: 700; color: #1e3a5f; }
        .stat-box .label { font-size: 11px; color: #64748b; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 MO IV Analyzer</h1>
            <p>Analiză automată Monitorul Oficial Partea IV</p>
        </div>
        
        <div class="content">
            <div class="stats">
                <div class="stat-box">
                    <div class="value">{{ companies }}</div>
                    <div class="label">Companii în baza de date</div>
                </div>
                <div class="stat-box">
                    <div class="value">v4.0</div>
                    <div class="label">Versiune</div>
                </div>
            </div>
            
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="upload-area" id="dropArea">
                    <div class="upload-icon">📁</div>
                    <div class="upload-text">Trage fișierele HTML aici sau click pentru a selecta</div>
                    <div class="upload-hint">Acceptă mai multe fișiere .html (monitoare)</div>
                    <input type="file" id="fileInput" name="files" multiple accept=".html,.htm">
                </div>
                
                <div class="file-list" id="fileList"></div>
                
                <button type="submit" class="btn" id="submitBtn" disabled>
                    Procesează monitoarele
                </button>
            </form>
            
            <div class="status" id="status"></div>
        </div>
        
        <div class="footer">
            MO IV Analyzer v4.0 | Pattern-uri din analiza 2.093 acte | Dezvoltare: Adrian Seceleanu
        </div>
    </div>

    <script>
        const dropArea = document.getElementById('dropArea');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const submitBtn = document.getElementById('submitBtn');
        const status = document.getElementById('status');
        const form = document.getElementById('uploadForm');
        
        let selectedFiles = [];
        
        // Drag & drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e => {
            dropArea.addEventListener(e, ev => ev.preventDefault());
        });
        ['dragenter', 'dragover'].forEach(e => {
            dropArea.addEventListener(e, () => dropArea.classList.add('dragover'));
        });
        ['dragleave', 'drop'].forEach(e => {
            dropArea.addEventListener(e, () => dropArea.classList.remove('dragover'));
        });
        
        dropArea.addEventListener('drop', e => {
            const files = Array.from(e.dataTransfer.files).filter(f => 
                f.name.endsWith('.html') || f.name.endsWith('.htm')
            );
            addFiles(files);
        });
        
        dropArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', e => addFiles(Array.from(e.target.files)));
        
        function addFiles(files) {
            files.forEach(f => {
                if (!selectedFiles.find(sf => sf.name === f.name)) {
                    selectedFiles.push(f);
                }
            });
            renderFileList();
        }
        
        function removeFile(name) {
            selectedFiles = selectedFiles.filter(f => f.name !== name);
            renderFileList();
        }
        
        function renderFileList() {
            fileList.innerHTML = selectedFiles.map(f => `
                <div class="file-item">
                    <span class="name">📄 ${f.name}</span>
                    <span class="remove" onclick="removeFile('${f.name}')">✕</span>
                </div>
            `).join('');
            submitBtn.disabled = selectedFiles.length === 0;
        }
        
        form.addEventListener('submit', async e => {
            e.preventDefault();
            if (selectedFiles.length === 0) return;
            
            status.className = 'status loading';
            status.textContent = 'Se procesează ' + selectedFiles.length + ' monitoare...';
            submitBtn.disabled = true;
            
            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('files', f));
            
            try {
                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'raport_mo_iv_' + new Date().toISOString().slice(0,10) + '.html';
                    a.click();
                    
                    status.className = 'status success';
                    status.textContent = '✅ Raport generat cu succes!';
                } else {
                    const err = await response.json();
                    throw new Error(err.error || 'Eroare la procesare');
                }
            } catch (err) {
                status.className = 'status error';
                status.textContent = '❌ ' + err.message;
            }
            
            submitBtn.disabled = false;
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(LANDING_PAGE, companies=f"{len(TOP_COMPANII):,}")


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': '4.0',
        'companies_loaded': len(TOP_COMPANII),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/process', methods=['POST'])
def process_monitors():
    """Procesează monitoarele uploadate și returnează raportul HTML."""
    
    if 'files' not in request.files:
        return jsonify({'error': 'Nu au fost trimise fișiere'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Nu au fost selectate fișiere'}), 400
    
    all_acts = []
    monitors_info = {}
    errors = []
    
    for file in files:
        if not file.filename:
            continue
            
        filename = secure_filename(file.filename)
        
        if not filename.lower().endswith(('.html', '.htm')):
            errors.append(f'{filename}: nu este fișier HTML')
            continue
        
        try:
            # Citește conținutul
            html_content = file.read().decode('utf-8')
            
            # Extrage numărul monitorului din filename sau din conținut
            nr_match = re.search(r'(\d{2,4})', filename)
            if nr_match:
                nr_monitor = int(nr_match.group(1))
            else:
                # Încearcă să extragă din conținut
                content_match = re.search(r'nr\.\s*(\d+)\s*din', html_content, re.IGNORECASE)
                nr_monitor = int(content_match.group(1)) if content_match else len(monitors_info) + 1
            
            # Extrage data din filename sau conținut
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', html_content)
            if date_match:
                data_mo = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}"
            else:
                data_mo = datetime.now().strftime("%d.%m.%Y")
            
            # Parsează monitorul
            acts = parse_monitor(html_content, nr_monitor)
            all_acts.extend(acts)
            monitors_info[nr_monitor] = data_mo
            
        except Exception as e:
            errors.append(f'{filename}: {str(e)}')
    
    if not all_acts:
        return jsonify({
            'error': 'Nu s-au putut procesa monitoarele',
            'details': errors
        }), 400
    
    # Generează raportul
    report_html = generate_html_report(all_acts, monitors_info)
    
    # Salvează temporar și trimite
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(report_html)
        temp_path = f.name
    
    return send_file(
        temp_path,
        mimetype='text/html',
        as_attachment=True,
        download_name=f'raport_mo_iv_{datetime.now().strftime("%Y%m%d_%H%M")}.html'
    )


@app.route('/api/stats')
def stats():
    """Returnează statistici despre sistemul de analiză."""
    return jsonify({
        'version': '4.0',
        'companies_in_database': len(TOP_COMPANII),
        'noise_operations': list(NOISE_OPERATIONS),
        'high_interest_operations': list(HIGH_INTEREST_OPERATIONS),
        'developer': 'Adrian Seceleanu'
    })


@app.route('/analyze', methods=['POST'])
def analyze_for_apify():
    """
    Endpoint pentru Apify webhook.
    Primește HTML și returnează analiză JSON cu alerte.
    """
    try:
        data = request.get_json()
        
        if not data or 'html' not in data:
            return jsonify({'error': 'Missing html field'}), 400
        
        html_content = data['html']
        monitor_number = data.get('monitor', 0)
        
        # Parsează monitorul
        acts = parse_monitor(html_content, monitor_number)
        
        # Generează alertele pentru Apify
        alerts = []
        for act in acts:
            # Alertă pentru companii din TOP cu operațiuni de interes major
            if act.in_top and act.is_high_interest:
                alerts.append({
                    'companie': act.denumire,
                    'cui': act.cui,
                    'operatiuni': [act.tip_operatiune],
                    'motiv': f'Companie TOP #{act.rank} (CA: {act.ca:,} lei) - operațiune de interes major',
                    'monitor': monitor_number,
                    'categorie_ca': act.categorie_ca
                })
            # Alertă pentru orice companie TOP (chiar și fără operațiuni majore)
            elif act.in_top:
                alerts.append({
                    'companie': act.denumire,
                    'cui': act.cui,
                    'operatiuni': [act.tip_operatiune],
                    'motiv': f'Companie TOP #{act.rank} (CA: {act.ca:,} lei)',
                    'monitor': monitor_number,
                    'categorie_ca': act.categorie_ca
                })
        
        return jsonify({
            'monitor': monitor_number,
            'total_acts': len(acts),
            'total_alerts': len(alerts),
            'alerts': alerts,
            'top_companies_found': sum(1 for a in acts if a.in_top),
            'high_interest_found': sum(1 for a in acts if a.in_top and a.is_high_interest)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print(f"[INFO] Starting MO IV Analyzer v4.0")
    print(f"[INFO] Companies loaded: {len(TOP_COMPANII):,}")
    print(f"[INFO] Port: {port}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
