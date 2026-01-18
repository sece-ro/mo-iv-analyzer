"""
Pattern-uri relaxate pentru operațiuni MO IV
Combină structura din analiza 2.093 acte cu matching mai permisiv
"""

import re
from typing import Dict, List, Tuple, Optional


# Ordinea de verificare (de la specific la general)
PATTERN_CHECK_ORDER: List[str] = [
    # PRIORITATE 1: Operațiuni combinate
    "majorare_capital_conversie_creanta",
    "dizolvare_lichidare",
    "cesiune_cooptare",
    
    # PRIORITATE 2: Capital și finanțare
    "majorare_capital",
    "reducere_capital",
    "aport_natura",
    "cesiune_parti_sociale",
    "contractare_credit",
    "constituire_garantii",
    "repartizare_dividende",
    
    # PRIORITATE 3: Structură societate
    "fuziune_absorbtie",
    "fuziune",
    "divizare",
    "dizolvare",
    "lichidare",
    "transformare_forma",
    
    # PRIORITATE 4: Sediu și puncte de lucru
    "schimbare_sediu",
    "deschidere_punct_lucru",
    "inchidere_punct_lucru",
    
    # PRIORITATE 5: Administrație
    "numire_administrator",
    "revocare_administrator",
    "prelungire_mandat",
    "schimbare_reprezentant",
    "retragere_asociat",
    "cooptare_asociat",
    
    # PRIORITATE 6: Obiect de activitate
    "actualizare_caen",
    "completare_activitati",
    "radiere_activitati",
    "modificare_obiect_activitate",
    
    # PRIORITATE 7: Alte operațiuni
    "actualizare_date",
    "modificare_durata",
    "schimbare_denumire",
]


OPERATION_NAMES: Dict[str, str] = {
    "majorare_capital_conversie_creanta": "Majorare capital prin conversie creanță",
    "dizolvare_lichidare": "Dizolvare și lichidare",
    "cesiune_cooptare": "Cesiune și cooptare asociat",
    "majorare_capital": "Majorare capital",
    "reducere_capital": "Reducere capital",
    "aport_natura": "Aport în natură",
    "cesiune_parti_sociale": "Cesiune părți sociale",
    "contractare_credit": "Contractare credit",
    "constituire_garantii": "Constituire garanții",
    "repartizare_dividende": "Repartizare dividende",
    "fuziune_absorbtie": "Fuziune prin absorbție",
    "fuziune": "Fuziune",
    "divizare": "Divizare",
    "dizolvare": "Dizolvare",
    "lichidare": "Lichidare",
    "transformare_forma": "Transformare formă juridică",
    "schimbare_sediu": "Schimbare sediu social",
    "deschidere_punct_lucru": "Deschidere punct de lucru",
    "inchidere_punct_lucru": "Închidere punct de lucru",
    "numire_administrator": "Numire administrator",
    "revocare_administrator": "Revocare administrator",
    "prelungire_mandat": "Prelungire mandat",
    "schimbare_reprezentant": "Schimbare reprezentant",
    "retragere_asociat": "Retragere asociat",
    "cooptare_asociat": "Cooptare asociat",
    "actualizare_caen": "Actualizare CAEN Rev.3",
    "completare_activitati": "Completare activități",
    "radiere_activitati": "Radiere activități",
    "modificare_obiect_activitate": "Modificare obiect activitate",
    "actualizare_date": "Actualizare date identificare",
    "modificare_durata": "Modificare durată societate",
    "schimbare_denumire": "Schimbare denumire",
    "hotarare_aga": "Hotărâre AGA",
    "decizie_asociat": "Decizie asociat",
}


OPERATION_CATEGORIES: Dict[str, str] = {
    "majorare_capital_conversie_creanta": "Capital și finanțare",
    "dizolvare_lichidare": "Structură societate",
    "cesiune_cooptare": "Capital și finanțare",
    "majorare_capital": "Capital și finanțare",
    "reducere_capital": "Capital și finanțare",
    "aport_natura": "Capital și finanțare",
    "cesiune_parti_sociale": "Capital și finanțare",
    "contractare_credit": "Capital și finanțare",
    "constituire_garantii": "Capital și finanțare",
    "repartizare_dividende": "Capital și finanțare",
    "fuziune_absorbtie": "Structură societate",
    "fuziune": "Structură societate",
    "divizare": "Structură societate",
    "dizolvare": "Structură societate",
    "lichidare": "Structură societate",
    "transformare_forma": "Structură societate",
    "schimbare_sediu": "Sediu și puncte de lucru",
    "deschidere_punct_lucru": "Sediu și puncte de lucru",
    "inchidere_punct_lucru": "Sediu și puncte de lucru",
    "numire_administrator": "Administrație",
    "revocare_administrator": "Administrație",
    "prelungire_mandat": "Administrație",
    "schimbare_reprezentant": "Administrație",
    "retragere_asociat": "Administrație",
    "cooptare_asociat": "Administrație",
    "actualizare_caen": "Obiect de activitate",
    "completare_activitati": "Obiect de activitate",
    "radiere_activitati": "Obiect de activitate",
    "modificare_obiect_activitate": "Obiect de activitate",
    "actualizare_date": "Alte operațiuni",
    "modificare_durata": "Alte operațiuni",
    "schimbare_denumire": "Alte operațiuni",
    "hotarare_aga": "Alte operațiuni",
    "decizie_asociat": "Alte operațiuni",
}


# Operațiuni de zgomot (frecvente dar neinteresante)
NOISE_OPERATIONS = {"actualizare_caen"}

# Operațiuni de interes major
HIGH_INTEREST_OPERATIONS = {
    "majorare_capital", "majorare_capital_conversie_creanta",
    "contractare_credit", "constituire_garantii",
    "fuziune_absorbtie", "fuziune", "divizare",
    "repartizare_dividende", "dizolvare_lichidare",
}


def detect_operation(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detectează operațiunea din text folosind keyword matching simplu.
    Returnează (op_id, op_name, category) sau (None, None, None)
    """
    text_lower = text.lower()
    
    # 1. CONVERSIE CREANȚĂ (foarte specific)
    if 'capital' in text_lower and ('conversie' in text_lower or 'capitalizare' in text_lower):
        if 'creanț' in text_lower or 'creant' in text_lower or 'împrumut' in text_lower or 'imprumut' in text_lower:
            return ("majorare_capital_conversie_creanta", 
                    OPERATION_NAMES["majorare_capital_conversie_creanta"],
                    OPERATION_CATEGORIES["majorare_capital_conversie_creanta"])
    
    # 2. DIZOLVARE ȘI LICHIDARE (combinat)
    if ('dizolv' in text_lower and 'lichid' in text_lower) or 'fără lichidator' in text_lower:
        return ("dizolvare_lichidare",
                OPERATION_NAMES["dizolvare_lichidare"],
                OPERATION_CATEGORIES["dizolvare_lichidare"])
    
    # 3. CESIUNE + COOPTARE
    if 'cesiune' in text_lower and 'cooptar' in text_lower:
        return ("cesiune_cooptare",
                OPERATION_NAMES["cesiune_cooptare"],
                OPERATION_CATEGORIES["cesiune_cooptare"])
    
    # 4. MAJORARE CAPITAL
    if 'capital' in text_lower and ('majorar' in text_lower or 'mărir' in text_lower or 'marir' in text_lower):
        return ("majorare_capital",
                OPERATION_NAMES["majorare_capital"],
                OPERATION_CATEGORIES["majorare_capital"])
    
    # 5. REDUCERE CAPITAL
    if 'capital' in text_lower and ('reducere' in text_lower or 'diminuar' in text_lower):
        return ("reducere_capital",
                OPERATION_NAMES["reducere_capital"],
                OPERATION_CATEGORIES["reducere_capital"])
    
    # 6. APORT ÎN NATURĂ
    if 'aport' in text_lower and ('natur' in text_lower or 'teren' in text_lower or 'imobil' in text_lower):
        return ("aport_natura",
                OPERATION_NAMES["aport_natura"],
                OPERATION_CATEGORIES["aport_natura"])
    
    # 7. CESIUNE PĂRȚI SOCIALE
    if 'cesiune' in text_lower or 'cesiona' in text_lower or 'cedent' in text_lower:
        if 'părți' in text_lower or 'parti' in text_lower or 'sociale' in text_lower or '100%' in text_lower:
            return ("cesiune_parti_sociale",
                    OPERATION_NAMES["cesiune_parti_sociale"],
                    OPERATION_CATEGORIES["cesiune_parti_sociale"])
    
    # 8. CONTRACTARE CREDIT
    if 'credit' in text_lower and ('contract' in text_lower or 'obține' in text_lower or 'obtine' in text_lower):
        return ("contractare_credit",
                OPERATION_NAMES["contractare_credit"],
                OPERATION_CATEGORIES["contractare_credit"])
    
    # 9. GARANȚII
    if 'garanți' in text_lower or 'garanti' in text_lower or 'ipotec' in text_lower or 'gaj' in text_lower:
        return ("constituire_garantii",
                OPERATION_NAMES["constituire_garantii"],
                OPERATION_CATEGORIES["constituire_garantii"])
    
    # 10. DIVIDENDE
    if 'dividend' in text_lower or ('repartiz' in text_lower and 'profit' in text_lower):
        return ("repartizare_dividende",
                OPERATION_NAMES["repartizare_dividende"],
                OPERATION_CATEGORIES["repartizare_dividende"])
    
    # 11. FUZIUNE PRIN ABSORBȚIE
    if 'fuziune' in text_lower and ('absorbți' in text_lower or 'absorbt' in text_lower):
        return ("fuziune_absorbtie",
                OPERATION_NAMES["fuziune_absorbtie"],
                OPERATION_CATEGORIES["fuziune_absorbtie"])
    
    # 12. FUZIUNE (simplă)
    if 'fuziune' in text_lower:
        return ("fuziune",
                OPERATION_NAMES["fuziune"],
                OPERATION_CATEGORIES["fuziune"])
    
    # 13. DIVIZARE
    if 'divizare' in text_lower or 'diviza' in text_lower:
        return ("divizare",
                OPERATION_NAMES["divizare"],
                OPERATION_CATEGORIES["divizare"])
    
    # 14. DIZOLVARE (singură)
    if 'dizolv' in text_lower:
        return ("dizolvare",
                OPERATION_NAMES["dizolvare"],
                OPERATION_CATEGORIES["dizolvare"])
    
    # 15. LICHIDARE (singură)
    if 'lichid' in text_lower:
        return ("lichidare",
                OPERATION_NAMES["lichidare"],
                OPERATION_CATEGORIES["lichidare"])
    
    # 16. TRANSFORMARE FORMĂ JURIDICĂ
    if 'transform' in text_lower and ('formă' in text_lower or 'forma' in text_lower or 'juridic' in text_lower):
        return ("transformare_forma",
                OPERATION_NAMES["transformare_forma"],
                OPERATION_CATEGORIES["transformare_forma"])
    
    # 17. SCHIMBARE SEDIU
    if 'sediu' in text_lower:
        # Verificăm să nu fie doar mențiune
        if any(kw in text_lower for kw in ['schimbar', 'mutar', 'muta', 'transfer', 'nou sediu', 'noul sediu']):
            return ("schimbare_sediu",
                    OPERATION_NAMES["schimbare_sediu"],
                    OPERATION_CATEGORIES["schimbare_sediu"])
    
    # 18. PUNCT DE LUCRU - DESCHIDERE
    if 'punct' in text_lower and 'lucru' in text_lower:
        if any(kw in text_lower for kw in ['deschid', 'înființ', 'infiint', 'înregistr']):
            return ("deschidere_punct_lucru",
                    OPERATION_NAMES["deschidere_punct_lucru"],
                    OPERATION_CATEGORIES["deschidere_punct_lucru"])
        if any(kw in text_lower for kw in ['închid', 'inchid', 'radier', 'desființ']):
            return ("inchidere_punct_lucru",
                    OPERATION_NAMES["inchidere_punct_lucru"],
                    OPERATION_CATEGORIES["inchidere_punct_lucru"])
    
    # 19. RETRAGERE ASOCIAT
    if 'retragere' in text_lower or 'retras' in text_lower:
        if 'asociat' in text_lower or 'societate' in text_lower:
            return ("retragere_asociat",
                    OPERATION_NAMES["retragere_asociat"],
                    OPERATION_CATEGORIES["retragere_asociat"])
    
    # 20. COOPTARE ASOCIAT
    if 'cooptar' in text_lower:
        return ("cooptare_asociat",
                OPERATION_NAMES["cooptare_asociat"],
                OPERATION_CATEGORIES["cooptare_asociat"])
    
    # 21. ADMINISTRATOR - NUMIRE
    if 'administrator' in text_lower:
        if any(kw in text_lower for kw in ['numir', 'numit', 'desemn']):
            if any(kw in text_lower for kw in ['revocar', 'înlocui', 'inlocui']):
                return ("revocare_administrator",
                        OPERATION_NAMES["revocare_administrator"],
                        OPERATION_CATEGORIES["revocare_administrator"])
            return ("numire_administrator",
                    OPERATION_NAMES["numire_administrator"],
                    OPERATION_CATEGORIES["numire_administrator"])
        if any(kw in text_lower for kw in ['revocar', 'încetar', 'incetar', 'demisie']):
            return ("revocare_administrator",
                    OPERATION_NAMES["revocare_administrator"],
                    OPERATION_CATEGORIES["revocare_administrator"])
        if any(kw in text_lower for kw in ['prelungir', 'reînnoi', 'reinnoi']):
            return ("prelungire_mandat",
                    OPERATION_NAMES["prelungire_mandat"],
                    OPERATION_CATEGORIES["prelungire_mandat"])
    
    # 22. SCHIMBARE REPREZENTANT
    if 'reprezentant' in text_lower and ('schimbar' in text_lower or 'înlocui' in text_lower):
        return ("schimbare_reprezentant",
                OPERATION_NAMES["schimbare_reprezentant"],
                OPERATION_CATEGORIES["schimbare_reprezentant"])
    
    # 23. CAEN / ACTUALIZARE
    if 'caen' in text_lower:
        if 'rev' in text_lower or 'actuali' in text_lower or 'recodific' in text_lower or 'declar' in text_lower:
            return ("actualizare_caen",
                    OPERATION_NAMES["actualizare_caen"],
                    OPERATION_CATEGORIES["actualizare_caen"])
    
    # 24. COMPLETARE ACTIVITĂȚI
    if 'activit' in text_lower:
        if 'completar' in text_lower or 'adăugar' in text_lower or 'adaug' in text_lower or 'extind' in text_lower:
            return ("completare_activitati",
                    OPERATION_NAMES["completare_activitati"],
                    OPERATION_CATEGORIES["completare_activitati"])
        if 'radier' in text_lower or 'elimina' in text_lower or 'renunț' in text_lower or 'renunt' in text_lower:
            return ("radiere_activitati",
                    OPERATION_NAMES["radiere_activitati"],
                    OPERATION_CATEGORIES["radiere_activitati"])
    
    # 25. OBIECT DE ACTIVITATE (generic)
    if 'obiect' in text_lower and 'activitate' in text_lower:
        return ("modificare_obiect_activitate",
                OPERATION_NAMES["modificare_obiect_activitate"],
                OPERATION_CATEGORIES["modificare_obiect_activitate"])
    
    # 26. ACTUALIZARE DATE
    if 'actuali' in text_lower and ('date' in text_lower or 'identificare' in text_lower or 'c.i.' in text_lower):
        return ("actualizare_date",
                OPERATION_NAMES["actualizare_date"],
                OPERATION_CATEGORIES["actualizare_date"])
    
    # 27. DURATĂ SOCIETATE
    if 'durată' in text_lower or 'durata' in text_lower:
        if 'nedeterminat' in text_lower or 'modificar' in text_lower:
            return ("modificare_durata",
                    OPERATION_NAMES["modificare_durata"],
                    OPERATION_CATEGORIES["modificare_durata"])
    
    # 28. SCHIMBARE DENUMIRE
    if 'denumir' in text_lower and ('schimbar' in text_lower or 'noua' in text_lower):
        return ("schimbare_denumire",
                OPERATION_NAMES["schimbare_denumire"],
                OPERATION_CATEGORIES["schimbare_denumire"])
    
    # 29. FALLBACK: Hotărâre AGA / Decizie asociat (când nu se detectează altceva specific)
    if 'adunării generale' in text_lower or 'adunarea generală' in text_lower or 'a.g.a' in text_lower:
        return ("hotarare_aga", "Hotărâre AGA", "Alte operațiuni")
    
    if 'decizie' in text_lower or 'hotărâre' in text_lower or 'hotarare' in text_lower:
        if 'asociat' in text_lower:
            return ("decizie_asociat", "Decizie asociat", "Alte operațiuni")
        return ("hotarare_aga", "Hotărâre AGA", "Alte operațiuni")
    
    return (None, None, None)


if __name__ == "__main__":
    # Teste
    test_cases = [
        "Schimbarea sediului social din municipiul Pitești în comuna Ghimpați",
        "Art. 1. Schimbarea sediului social din București în Cluj",
        "Majorare capital social cu 3.533.000 lei prin conversie creanță",
        "Dizolvare și lichidare fără lichidator",
        "Actualizare obiect de activitate conform CAEN Rev. 3",
        "Numire administrator nou pentru mandat de 4 ani",
        "Cesiune părți sociale de la POPESCU către IONESCU",
        "Retragerea din societate a asociatului",
        "Completarea obiectului secundar de activitate",
    ]
    
    print("TESTE PATTERNS RELAXATE")
    print("=" * 60)
    
    for text in test_cases:
        op_id, op_name, category = detect_operation(text)
        print(f"\nText: {text[:50]}...")
        if op_id:
            print(f"  → {op_name} ({category})")
        else:
            print("  → Nu s-a detectat")
