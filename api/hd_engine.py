# SPDX-License-Identifier: AGPL-3.0-or-later
# Source code: https://github.com/fabibento09-web/danielle-bento-hd-engine
"""
Vercel Python Serverless Function — Human Design engine.

Endpoint: POST /api/hd-engine

Body (JSON):
  {
    "year": 1990, "month": 6, "day": 15,
    "hour": 14, "minute": 30,
    "city": "São Paulo, SP"          # required if no lat/lng
    // optional: "latitude": -23.5505, "longitude": -46.6333
    // optional: "timezone": "America/Sao_Paulo"  (override)
  }

Response (200):
  {
    "type": "Manifestor",
    "strategy": "Informar antes de agir",
    ...
    "_meta": { "timezone": "...", "lat": ..., "lng": ..., "geocoded_from": "city" }
  }

The function does its own geocoding (geopy/Nominatim) and timezone
resolution (timezonefinder) so the Next.js side can just send raw
city text. Lat/lng or timezone overrides are accepted for testing.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import traceback

# Make the vendored humandesign package importable.
_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)


def _geocode_city(city: str):
    """Resolve a free-text city to (lat, lng). Returns (None, None) on failure."""
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="atempus-hd/1.0")
    location = geolocator.geocode(city, language="pt", timeout=10)
    if location is None:
        return None, None
    return float(location.latitude), float(location.longitude)


def _timezone_from_coords(lat: float, lng: float) -> str:
    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lng)
    return tz or "UTC"


def calculate(payload: dict) -> dict:
    from humandesign.features.core import (
        get_utc_offset_from_tz,
        calc_single_hd_features,
    )

    year = int(payload["year"])
    month = int(payload["month"])
    day = int(payload["day"])
    hour = int(payload["hour"])
    minute = int(payload["minute"])

    # Resolve coordinates and timezone
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    geocoded_from = "coordinates"
    if lat is None or lng is None:
        city = payload.get("city")
        if not city:
            raise ValueError("Either 'city' or ('latitude' + 'longitude') is required")
        lat, lng = _geocode_city(city)
        if lat is None:
            raise ValueError(f"Could not geocode city: {city}")
        geocoded_from = "city"
    else:
        lat, lng = float(lat), float(lng)

    tz = payload.get("timezone") or _timezone_from_coords(lat, lng)
    offset = get_utc_offset_from_tz((year, month, day, hour, minute, 0), tz)

    r = calc_single_hd_features(
        (year, month, day, hour, minute, 0, offset),
        report=False,
        channel_meaning=False,
        day_chart_only=False,
    )

    type_en = r[0]
    auth_code = r[1]
    profile_tuple = r[4]
    definition_int = int(r[5]) if r[5] is not None else 0
    defined_centers = set(r[7] or [])

    chart_b64 = _generate_chart_image_b64(r)

    inc_cross_raw = r[2]
    inc_cross_type = r[3]

    inc_cross_label = {
        "RAC": "Cruz do Ângulo Direito",
        "LAC": "Cruz do Ângulo Esquerdo",
        "JXP": "Cruz da Justaposição",
    }.get(inc_cross_type, inc_cross_type)

    cross_gates = []
    try:
        parts = inc_cross_raw.split(")-")[0].replace("((", "").replace(")", "")
        cross_gates = [int(x.strip()) for x in parts.split(",")]
    except Exception:
        pass

    import pandas as pd
    gate_df = pd.DataFrame(r[6])
    PLANET_PT = {
        "Sun": "Sol", "Earth": "Terra", "Moon": "Lua",
        "North_Node": "Nodo Norte", "South_Node": "Nodo Sul",
        "Mercury": "Mercúrio", "Venus": "Vênus", "Mars": "Marte",
        "Jupiter": "Júpiter", "Saturn": "Saturno",
        "Uranus": "Urano", "Neptune": "Netuno", "Pluto": "Plutão",
    }

    def extract_planet_gates(df, label):
        rows = df[df["label"] == label]
        out = []
        for _, row in rows.iterrows():
            out.append({
                "planet": PLANET_PT.get(row["planets"], row["planets"]),
                "gate": int(row["gate"]),
                "line": int(row["line"]),
            })
        return out

    personality_gates = extract_planet_gates(gate_df, "prs")
    design_gates = extract_planet_gates(gate_df, "des")

    variables_raw = r[11] or {}
    variables = None
    if variables_raw:
        variables = {
            "digestion": variables_raw.get("top_left", {}).get("def_type", ""),
            "environment": variables_raw.get("bottom_left", {}).get("def_type", ""),
            "motivation": variables_raw.get("top_right", {}).get("def_type", ""),
            "perspective": variables_raw.get("bottom_right", {}).get("def_type", ""),
        }

    return {
        "type": _TYPE_PT.get(type_en, type_en),
        "strategy": _STRATEGY_PT.get(type_en, ""),
        "authority": _AUTHORITY_PT.get(auth_code, auth_code),
        "profile": _format_profile(profile_tuple),
        "definition": _DEFINITION_PT.get(definition_int, str(definition_int)),
        "signature": _SIGNATURE_PT.get(type_en, ""),
        "notSelfTheme": _NOT_SELF_PT.get(type_en, ""),
        "definedCenters": [_CENTER_PT[c] for c in defined_centers if c in _CENTER_PT],
        "openCenters": [_CENTER_PT[c] for c in (_ALL_CENTERS - defined_centers) if c in _CENTER_PT],
        "channels": _extract_channels(r[8]),
        "bodygraphImage": chart_b64,
        "incarnationCross": {
            "label": inc_cross_label,
            "gates": cross_gates,
            "type": inc_cross_type,
        },
        "personalityGates": personality_gates,
        "designGates": design_gates,
        "variables": variables,
        "_meta": {
            "type_en": type_en,
            "authority_code": auth_code,
            "utc_offset": offset,
            "timezone": tz,
            "lat": lat,
            "lng": lng,
            "geocoded_from": geocoded_from,
        },
    }


def _generate_chart_image_b64(r):
    import base64
    try:
        from humandesign.utils import serialization as cj
        from humandesign.utils.date_utils import (
            clean_birth_date_to_iso,
            clean_create_date_to_iso,
        )
        from humandesign.services import chart_renderer as chart
        from humandesign import hd_constants

        data = {
            "birth_date": clean_birth_date_to_iso(r[9], 0),
            "create_date": clean_create_date_to_iso(r[10]),
            "energy_type": r[0],
            "inner_authority": r[1],
            "inc_cross": r[2],
            "profile": r[4],
            "active_chakras": r[7],
            "inactive_chakras": set(hd_constants.CHAKRA_LIST) - set(r[7] or []),
            "definition": "{}".format(r[5]),
            "variables": r[11],
        }

        general_json_str = cj.general(data)
        gates_json_str = cj.gatesJSON(r[6])
        channels_json_str = cj.channelsJSON(r[8], False)

        final_result = {
            "general": json.loads(general_json_str),
            "gates": json.loads(gates_json_str),
            "channels": json.loads(channels_json_str),
        }

        img_bytes = chart.generate_bodygraph_image(final_result, fmt="png")
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        sys.stderr.write(f"[hd-engine] chart generation failed (non-fatal): {e}\n")
        return None


def _format_profile(profile_tuple):
    if not profile_tuple or len(profile_tuple) < 2:
        return ""
    line1, line2 = int(profile_tuple[0]), int(profile_tuple[1])
    nicknames = {
        1: "Investigador", 2: "Eremita", 3: "Mártir",
        4: "Oportunista", 5: "Herege", 6: "Modelo",
    }
    return f"{line1}/{line2} — {nicknames.get(line1, '')} / {nicknames.get(line2, '')}"


def _extract_channels(channels_dict):
    if not channels_dict:
        return []
    import numpy as np

    def to_list(v):
        return v.tolist() if isinstance(v, np.ndarray) else list(v or [])

    gates = to_list(channels_dict.get("gate", []))
    ch_gates = to_list(channels_dict.get("ch_gate", []))
    seen = set()
    out = []
    for g, cg in zip(gates, ch_gates):
        g, cg = int(g), int(cg)
        key = tuple(sorted([g, cg]))
        if key in seen:
            continue
        seen.add(key)
        out.append(f"Canal {key[0]}-{key[1]}")
    return out


_TYPE_PT = {
    "Projector": "Projetor",
    "Generator": "Gerador",
    "Manifesting Generator": "Gerador Manifestante",
    "Manifestor": "Manifestor",
    "Reflector": "Refletor",
}
_STRATEGY_PT = {
    "Projector": "Aguardar pelo convite",
    "Generator": "Aguardar para responder",
    "Manifesting Generator": "Aguardar para responder, então informar",
    "Manifestor": "Informar antes de agir",
    "Reflector": "Aguardar um ciclo lunar (28 dias)",
}
_SIGNATURE_PT = {
    "Projector": "Sucesso", "Generator": "Satisfação",
    "Manifesting Generator": "Satisfação e Paz", "Manifestor": "Paz",
    "Reflector": "Surpresa",
}
_NOT_SELF_PT = {
    "Projector": "Amargura", "Generator": "Frustração",
    "Manifesting Generator": "Frustração e Raiva", "Manifestor": "Raiva",
    "Reflector": "Decepção",
}
_AUTHORITY_PT = {
    "SP": "Autoridade Emocional", "SL": "Autoridade Sacral",
    "SN": "Autoridade Esplênica", "HT": "Autoridade do Ego/Coração",
    "GC": "Autoridade Autoprojetada", "AA": "Autoridade Mental/Ambiental",
    "HD": "Autoridade Mental/Ambiental", "none": "Autoridade Lunar",
}
_DEFINITION_PT = {
    0: "Sem Definição", 1: "Definição Única", 2: "Definição Dividida",
    3: "Tripla Divisão", 4: "Quádrupla Divisão",
}
_CENTER_PT = {
    "HD": "Cabeça", "AA": "Ajna", "TT": "Garganta", "GC": "G (Identidade)",
    "HT": "Coração", "SN": "Baço", "SP": "Plexo Solar", "SL": "Sacral", "RT": "Raiz",
}
_ALL_CENTERS = {"HD", "AA", "TT", "GC", "HT", "SN", "SP", "SL", "RT"}


# ── Vercel Python serverless handler ──
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_bytes = self.rfile.read(length)
            # Decode tolerante: tenta UTF-8 (default JSON) e cai pra latin-1
            # se o cliente enviar com encoding errado (Windows shells, curl).
            try:
                raw = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw = raw_bytes.decode("latin-1")
            payload = json.loads(raw) if raw else {}
            result = calculate(payload)
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            err = {"error": str(e), "trace": traceback.format_exc()}
            body = json.dumps(err, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_GET(self):
        # Health check
        body = json.dumps({"ok": True, "service": "hd-engine"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
