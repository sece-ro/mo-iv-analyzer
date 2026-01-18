# MO IV Analyzer v4.0

Sistem automat de analiză a **Monitorului Oficial Partea IV** (publicații ale agenților economici).

## Funcționalități

- ✅ Parsare monitoare HTML din Monitorul Oficial
- ✅ Identificare companii din TOP 10.000 România (după CUI și denumire)
- ✅ Detecție automată tipuri operațiuni (25+ categorii)
- ✅ Filtrare zgomot (actualizări CAEN, notificări ORC)
- ✅ Generare raport HTML cu:
  - Secțiune "Interes major" (majorări capital, credite, fuziuni)
  - Companii TOP grupate pe categorii cifră de afaceri
  - Listă completă acte per monitor

## Tehnologii

- Python 3.11+
- Flask
- Gunicorn
- Pattern matching cu regex

## Deploy pe Railway

1. Fork/clone repository
2. Conectează la Railway
3. Deploy automat

## API Endpoints

- `GET /` - Interfață web pentru upload
- `GET /api/health` - Health check
- `GET /api/stats` - Statistici sistem
- `POST /api/process` - Procesare monitoare (multipart/form-data)

## Autor

**Adrian Seceleanu** - Ziarul Financiar

## Licență

Proprietar - Ziarul Financiar
