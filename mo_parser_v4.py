#!/usr/bin/env python3
"""
MO IV Parser v4.0 - Cu pattern-uri îmbunătățite din analiza 2.093 acte
Generează raport HTML grupat pe categorii CA

Changelog v4:
- Integrare patterns_dict.py din analiza monitoarelor
- Detecție operațiuni combinate
- Excludere notificări ORC și actualizări CAEN din raportul principal
- Focus pe operațiuni relevante jurnalistic
"""

import re
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Import pattern-uri relaxate (mai permisive)
from patterns_relaxed import (
    detect_operation as detect_op_relaxed,
    OPERATION_NAMES,
    OPERATION_CATEGORIES,
    NOISE_OPERATIONS,
    HIGH_INTEREST_OPERATIONS
)

# Încarcă TOP companii
TOP_COMPANII = {}
TOP_COMPANII_BY_NAME = {}

# Căutăm fișierul JSON în mai multe locații
possible_paths = [
    os.path.join(os.path.dirname(__file__), 'top_companii.json'),  # Același folder
    '/mnt/user-data/uploads/top_companii.json',  # Local development
    'top_companii.json',  # Current directory
]

json_path = None
for path in possible_paths:
    if os.path.exists(path):
        json_path = path
        break

if json_path:
    with open(json_path, 'r', encoding='utf-8') as f:
        TOP_COMPANII = json.load(f)
    for cui, info in TOP_COMPANII.items():
        name_norm = info['denumire'].upper().strip()
        for suffix in [' S.R.L.', ' SRL', ' S.A.', ' SA', ' S.C.S.', ' SCS']:
            name_norm = name_norm.replace(suffix, '')
        TOP_COMPANII_BY_NAME[name_norm.strip()] = {'cui': cui, **info}
    print(f"[INFO] Încărcat {len(TOP_COMPANII):,} companii TOP din {json_path}")
else:
    print("[WARNING] Nu s-a găsit top_companii.json - funcționalitatea TOP va fi dezactivată")

def detect_operation(text: str) -> Tuple[str, str, str]:
    """
    Detectează operațiunea folosind pattern-urile relaxate.
    Returnează (operation_id, operation_name, category)
    """
    op_id, op_name, category = detect_op_relaxed(text)
    
    if op_id:
        return op_id, op_name, category
    
    # Fallback pentru cazuri nedetectate
    return "nedeterminat", "Operațiune nedeterminată", "Altele"


@dataclass
class Act:
    nr_act: int
    denumire: str
    cui: Optional[str] = None
    tip_operatiune: str = ""
    tip_operatiune_id: str = ""
    categorie_operatiune: str = ""
    text_complet: str = ""
    nr_monitor: int = 0
    in_top: bool = False
    rank: int = 0
    ca: int = 0
    categorie_ca: str = ""
    is_noise: bool = False
    is_high_interest: bool = False


def normalize_name(name: str) -> str:
    name = name.upper().strip()
    for suffix in [' - S.R.L.', ' -S.R.L.', ' S.R.L.', ' SRL', 
                   ' - S.A.', ' -S.A.', ' S.A.', ' SA', ' S.C.S.', ' SCS']:
        name = name.replace(suffix, '')
    return name.strip()


def get_ca_category(ca: int) -> Tuple[str, int]:
    if ca > 10_000_000_000: return ("GIGANT", 1)
    elif ca > 1_000_000_000: return ("MARI", 2)
    elif ca > 500_000_000: return ("MEDII-MARI", 3)
    elif ca > 200_000_000: return ("MEDII", 4)
    elif ca > 100_000_000: return ("MEDII-MICI", 5)
    elif ca > 50_000_000: return ("MICI DIN TOP", 6)
    else: return ("SUB 50M", 7)


def extract_cui(text: str) -> Optional[str]:
    patterns = [
        r'cod unic de înregistrare[:\s]+(\d{6,10})',
        r'CUI[:\s]+(?:RO)?(\d{6,10})',
        r'C\.U\.I\.[:\s]+(?:RO)?(\d{6,10})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def parse_monitor(html: str, nr_monitor: int) -> List[Act]:
    """Parsează un monitor și returnează lista de acte."""
    acts = []
    company_pattern = r'<strong>(?:Societatea\s+)?([^<]+(?:S\.R\.L\.|SRL|S\.A\.|SA|S\.C\.S\.|SCS)[^<]*)</strong>'
    matches = list(re.finditer(company_pattern, html, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        company_name = match.group(1).strip()
        company_name = re.sub(r'\s+', ' ', company_name)
        
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        
        text_complet = html[start_pos:end_pos]
        text_complet = re.sub(r'<[^>]+>', ' ', text_complet)
        text_complet = re.sub(r'\s+', ' ', text_complet).strip()
        
        # Skip notificări ORC (sunt doar confirmări)
        if 'oficiul registrului comer' in text_complet.lower()[:100]:
            continue
        
        cui = extract_cui(text_complet)
        op_id, op_name, op_category = detect_operation(text_complet)
        
        act = Act(
            nr_act=len(acts) + 1,
            denumire=company_name,
            cui=cui,
            tip_operatiune=op_name,
            tip_operatiune_id=op_id,
            categorie_operatiune=op_category,
            text_complet=text_complet[:2000],
            nr_monitor=nr_monitor,
            is_noise=op_id in NOISE_OPERATIONS,
            is_high_interest=op_id in HIGH_INTEREST_OPERATIONS
        )
        
        # Verificăm TOP
        name_norm = normalize_name(company_name)
        if cui and cui in TOP_COMPANII:
            info = TOP_COMPANII[cui]
            act.in_top = True
            act.rank = info['rank']
            act.ca = info['ca']
            act.categorie_ca, _ = get_ca_category(info['ca'])
        elif name_norm in TOP_COMPANII_BY_NAME:
            info = TOP_COMPANII_BY_NAME[name_norm]
            act.in_top = True
            act.rank = info['rank']
            act.ca = info['ca']
            act.categorie_ca, _ = get_ca_category(info['ca'])
        
        acts.append(act)
    
    return acts


def format_ca(ca: int) -> str:
    if ca >= 1_000_000_000:
        return f"{ca / 1_000_000_000:.1f} mld lei"
    elif ca >= 1_000_000:
        return f"{ca / 1_000_000:.0f}M lei"
    else:
        return f"{ca:,} lei"


def generate_html_report(all_acts: List[Act], monitors_info: Dict[int, str]) -> str:
    """Generează raportul HTML."""
    
    # Separăm actele
    top_acts = [a for a in all_acts if a.in_top and not a.is_noise]
    relevant_acts = [a for a in all_acts if not a.is_noise]
    noise_acts = [a for a in all_acts if a.is_noise]
    high_interest_top = [a for a in top_acts if a.is_high_interest]
    
    # Grupăm TOP pe categorii CA
    ca_categories = {
        "GIGANT": [], "MARI": [], "MEDII-MARI": [],
        "MEDII": [], "MEDII-MICI": [], "MICI DIN TOP": [],
    }
    for act in top_acts:
        if act.categorie_ca in ca_categories:
            ca_categories[act.categorie_ca].append(act)
    for cat in ca_categories:
        ca_categories[cat].sort(key=lambda x: x.rank)
    
    # Statistici
    total_acts = len(all_acts)
    total_relevant = len(relevant_acts)
    total_top = len(top_acts)
    total_high_interest = len(high_interest_top)
    
    monitors_sorted = sorted(monitors_info.keys())
    first_mo = monitors_sorted[0] if monitors_sorted else 0
    last_mo = monitors_sorted[-1] if monitors_sorted else 0
    
    html = f'''<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport MO IV nr. {first_mo}-{last_mo}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.5; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 30px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header .meta {{ margin-top: 15px; font-size: 13px; opacity: 0.8; }}
        .sumar {{ background: #f1f5f9; padding: 20px 30px; display: flex; gap: 25px; flex-wrap: wrap; border-bottom: 1px solid #e2e8f0; }}
        .sumar-item {{ text-align: center; }}
        .sumar-item .number {{ font-size: 28px; font-weight: 700; color: #1e3a5f; }}
        .sumar-item .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
        .sumar-item.highlight .number {{ color: #dc2626; }}
        .section {{ padding: 25px 30px; border-bottom: 1px solid #e2e8f0; }}
        .section-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }}
        .section-header h2 {{ font-size: 16px; font-weight: 600; color: #334155; text-transform: uppercase; }}
        .badge {{ background: #1e3a5f; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }}
        .badge.alert {{ background: #dc2626; }}
        .ca-category {{ margin-bottom: 25px; }}
        .ca-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
        .ca-dot {{ width: 14px; height: 14px; border-radius: 3px; }}
        .ca-dot.gigant {{ background: #dc2626; }}
        .ca-dot.mari {{ background: #ea580c; }}
        .ca-dot.medii-mari {{ background: #ca8a04; }}
        .ca-dot.medii {{ background: #16a34a; }}
        .ca-dot.medii-mici {{ background: #0891b2; }}
        .ca-dot.mici {{ background: #6b7280; }}
        .ca-title {{ font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; }}
        .ca-range {{ font-size: 12px; color: #94a3b8; }}
        .card {{ background: #fafafa; border-left: 4px solid #e2e8f0; border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 10px; transition: all 0.2s; }}
        .card:hover {{ background: #f1f5f9; transform: translateX(4px); }}
        .card.gigant {{ border-left-color: #dc2626; }}
        .card.mari {{ border-left-color: #ea580c; }}
        .card.medii-mari {{ border-left-color: #ca8a04; }}
        .card.medii {{ border-left-color: #16a34a; }}
        .card.medii-mici {{ border-left-color: #0891b2; }}
        .card.mici {{ border-left-color: #6b7280; }}
        .card.high-interest {{ background: #fef2f2; }}
        .card-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .card-name {{ font-size: 15px; font-weight: 600; color: #1e293b; }}
        .card-mo {{ background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
        .card-meta {{ font-size: 12px; color: #64748b; margin-bottom: 8px; }}
        .card-op {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .card-op.capital {{ background: #dbeafe; color: #1e40af; }}
        .card-op.structura {{ background: #fce7f3; color: #9d174d; }}
        .card-op.sediu {{ background: #d1fae5; color: #065f46; }}
        .card-op.admin {{ background: #fef3c7; color: #92400e; }}
        .card-op.activitate {{ background: #e0e7ff; color: #3730a3; }}
        .card-op.high {{ background: #dc2626; color: white; }}
        .empty {{ text-align: center; padding: 15px; color: #94a3b8; font-size: 13px; font-style: italic; }}
        .monitor-group {{ margin-bottom: 15px; }}
        .monitor-header {{ background: #f1f5f9; padding: 10px 15px; border-radius: 6px; font-size: 13px; font-weight: 600; color: #475569; cursor: pointer; display: flex; justify-content: space-between; }}
        .monitor-header:hover {{ background: #e2e8f0; }}
        .monitor-count {{ background: #cbd5e1; padding: 2px 8px; border-radius: 10px; font-size: 11px; }}
        .monitor-list {{ padding-left: 15px; max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }}
        .monitor-list.expanded {{ max-height: 5000px; }}
        .expand-icon {{ transition: transform 0.2s; display: inline-block; }}
        .monitor-header.expanded .expand-icon {{ transform: rotate(90deg); }}
        .monitor-item {{ padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px; display: flex; justify-content: space-between; gap: 10px; }}
        .monitor-item .name {{ color: #334155; flex: 1; }}
        .monitor-item .op {{ color: #64748b; font-size: 12px; text-align: right; white-space: nowrap; }}
        .monitor-item.top {{ background: #fef3c7; margin: 0 -15px; padding: 6px 15px; }}
        .monitor-item.high {{ background: #fecaca; margin: 0 -15px; padding: 6px 15px; }}
        .footer {{ background: #f1f5f9; padding: 15px 30px; text-align: center; font-size: 12px; color: #64748b; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }}
        .stat-card {{ background: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; }}
        .stat-card h4 {{ font-size: 12px; color: #64748b; margin-bottom: 5px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 20px; font-weight: 700; color: #1e3a5f; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>RAPORT MO IV nr. {first_mo}-{last_mo}</h1>
        <div class="meta">📅 Generat: {datetime.now().strftime("%d.%m.%Y, %H:%M")}</div>
    </div>
    
    <div class="sumar">
        <div class="sumar-item highlight"><div class="number">{total_high_interest}</div><div class="label">Interes major</div></div>
        <div class="sumar-item"><div class="number">{total_top}</div><div class="label">Companii TOP</div></div>
        <div class="sumar-item"><div class="number">{total_relevant}</div><div class="label">Acte relevante</div></div>
        <div class="sumar-item"><div class="number">{len(monitors_info)}</div><div class="label">Monitoare</div></div>
        <div class="sumar-item"><div class="number">{len(noise_acts)}</div><div class="label">Zgomot filtrat</div></div>
    </div>
    
    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 20px; margin: 0; font-size: 13px; color: #92400e;">
        ⚠️ <strong>Atenție:</strong> Filtrare &amp; etichetare realizată automat, verificați documentele originale!
    </div>
'''
    
    # Secțiunea de interes major (dacă există)
    if high_interest_top:
        html += f'''
    <div class="section">
        <div class="section-header">
            <h2>🔴 Operațiuni de interes major</h2>
            <span class="badge alert">{len(high_interest_top)} acte</span>
        </div>
'''
        for act in sorted(high_interest_top, key=lambda x: x.rank):
            css = act.categorie_ca.lower().replace(' ', '-').replace('din-top', '')
            op_css = "high"
            html += f'''
        <div class="card {css} high-interest">
            <div class="card-header">
                <span class="card-name">{act.denumire}</span>
                <span class="card-mo">MO {act.nr_monitor}</span>
            </div>
            <div class="card-meta">Rank #{act.rank} | CA: {format_ca(act.ca)} | {act.categorie_ca}</div>
            <span class="card-op {op_css}">{act.tip_operatiune}</span>
        </div>
'''
        html += '</div>'
    
    # Secțiunea A: Companii din TOP (doar dacă există)
    if total_top > 0:
        html += f'''
    <div class="section">
        <div class="section-header">
            <h2>Secțiunea A: Companii din TOP România</h2>
            <span class="badge">{total_top} companii</span>
        </div>
'''
    
        ca_info = {
            "GIGANT": ("gigant", "> 10 mld lei"),
            "MARI": ("mari", "1-10 mld lei"),
            "MEDII-MARI": ("medii-mari", "500M - 1 mld lei"),
            "MEDII": ("medii", "200M - 500M lei"),
            "MEDII-MICI": ("medii-mici", "100M - 200M lei"),
            "MICI DIN TOP": ("mici", "50M - 100M lei"),
        }
        
        op_css_map = {
            "Capital și finanțare": "capital",
            "Structură societate": "structura",
            "Sediu și puncte de lucru": "sediu",
            "Administrație și management": "admin",
            "Administrație": "admin",
            "Obiect de activitate": "activitate",
        }
        
        # Afișăm doar categoriile care au rezultate
        for cat_name, acts_list in ca_categories.items():
            if not acts_list:  # Skip categoriile goale
                continue
            css, ca_range = ca_info[cat_name]
            html += f'''
        <div class="ca-category">
            <div class="ca-header">
                <div class="ca-dot {css}"></div>
                <span class="ca-title">{cat_name}</span>
                <span class="ca-range">({ca_range})</span>
            </div>
'''
            for act in acts_list:
                op_css = op_css_map.get(act.categorie_operatiune, "")
                hi_class = " high-interest" if act.is_high_interest else ""
                html += f'''
            <div class="card {css}{hi_class}">
                <div class="card-header">
                    <span class="card-name">{act.denumire}</span>
                    <span class="card-mo">MO {act.nr_monitor}</span>
                </div>
                <div class="card-meta">Rank #{act.rank} | CA: {format_ca(act.ca)}</div>
                <span class="card-op {op_css}">{act.tip_operatiune}</span>
            </div>
'''
            html += '</div>'
        
        html += '</div>'
    
    # Secțiunea D: Listă completă (doar acte relevante)
    html += f'''
    <div class="section">
        <div class="section-header">
            <h2>Secțiunea D: Listă completă companii identificate și tipul operațiunii comunicate, per monitor</h2>
            <span class="badge">{total_relevant} acte relevante</span>
        </div>
        <p style="font-size: 12px; color: #64748b; margin-bottom: 15px;">
            Exclus: {len(noise_acts)} notificări ORC și actualizări CAEN
        </p>
'''
    
    acts_by_monitor = {}
    for act in relevant_acts:
        if act.nr_monitor not in acts_by_monitor:
            acts_by_monitor[act.nr_monitor] = []
        acts_by_monitor[act.nr_monitor].append(act)
    
    for nr_mo in sorted(acts_by_monitor.keys()):
        acts_list = acts_by_monitor[nr_mo]
        data_mo = monitors_info.get(nr_mo, "")
        html += f'''
        <div class="monitor-group">
            <div class="monitor-header" onclick="toggleMonitor(this)">
                <span><span class="expand-icon">▶</span> MO IV nr. {nr_mo} din {data_mo}</span>
                <span class="monitor-count">{len(acts_list)} acte</span>
            </div>
            <div class="monitor-list">
'''
        for act in acts_list:
            css_class = ''
            if act.is_high_interest and act.in_top:
                css_class = ' high'
            elif act.in_top:
                css_class = ' top'
            marker = ' 🔴' if act.is_high_interest else (' ⭐' if act.in_top else '')
            html += f'''
                <div class="monitor-item{css_class}">
                    <span class="name">{act.denumire}{marker}</span>
                    <span class="op">{act.tip_operatiune}</span>
                </div>
'''
        html += '</div></div>'
    
    html += '''
    </div>
    <div class="footer">MO IV Analyzer v4.0 | Pattern-uri din analiza 2.093 acte | Dezvoltare: Adrian Seceleanu</div>
</div>
<script>
function toggleMonitor(h) {
    h.classList.toggle('expanded');
    h.nextElementSibling.classList.toggle('expanded');
}
</script>
</body></html>'''
    
    return html


if __name__ == "__main__":
    monitors = [
        (129, "/mnt/user-data/uploads/monitor_129.html", "15.01.2026"),
        (130, "/mnt/user-data/uploads/monitor_130.html", "15.01.2026"),
        (131, "/mnt/user-data/uploads/monitor_131.html", "15.01.2026"),
        (132, "/mnt/user-data/uploads/monitor_132.html", "15.01.2026"),
    ]
    
    all_acts = []
    monitors_info = {}
    
    for nr, filepath, data in monitors:
        print(f"Procesez MO {nr}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
        acts = parse_monitor(html, nr)
        all_acts.extend(acts)
        monitors_info[nr] = data
        
        top_count = sum(1 for a in acts if a.in_top)
        high_count = sum(1 for a in acts if a.is_high_interest and a.in_top)
        noise_count = sum(1 for a in acts if a.is_noise)
        print(f"  -> {len(acts)} acte, {top_count} TOP, {high_count} interes major, {noise_count} zgomot")
    
    print(f"\n{'='*50}")
    print(f"Total: {len(all_acts)} acte")
    print(f"Din TOP: {sum(1 for a in all_acts if a.in_top)}")
    print(f"Interes major (TOP): {sum(1 for a in all_acts if a.is_high_interest and a.in_top)}")
    print(f"Zgomot filtrat: {sum(1 for a in all_acts if a.is_noise)}")
    
    # Statistici operațiuni
    from collections import Counter
    ops = Counter(a.tip_operatiune for a in all_acts if not a.is_noise)
    print(f"\nOperațiuni relevante (top 15):")
    for op, count in ops.most_common(15):
        print(f"  {op}: {count}")
    
    report = generate_html_report(all_acts, monitors_info)
    output_path = "/mnt/user-data/outputs/raport_mo_iv_v4.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nRaport salvat: {output_path}")
