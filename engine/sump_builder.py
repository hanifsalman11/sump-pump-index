import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/sump-pump-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4").strip()
CUSTOM_SUMP = os.environ.get("CUSTOM_SUMP", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_pumps.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Model / Basement Scenario, Motor HP, GPH @ 0ft, GPH @ 10ft Lift, Max Shutoff Head Ft, Pipe Inches, Amps 120V)
SEED_PUMPS = [
    ("Zoeller M53 Mighty-Mate 1/3 HP Cast Iron Sump Pump", 0.33, 2580, 2040, 19.2, 1.5, 4.8),
    ("Zoeller M98 Flow-Mate 1/2 HP Cast Iron Sump Pump", 0.50, 4320, 3660, 23.0, 1.5, 9.4),
    ("Zoeller M267 Waste-Mate 1/2 HP Heavy-Duty Sewage/Sump", 0.50, 7680, 5460, 21.5, 2.0, 10.4),
    ("Zoeller 508-0006 Aquanot Fit 508 ProPak 53 Combo", 0.33, 2580, 2040, 19.5, 1.5, 4.8),
    ("Wayne WSS30Vn 1/2 HP + 12V Smart Battery Backup Combo", 0.50, 5100, 4300, 22.0, 1.5, 7.6),
    ("Wayne CDU800 1/2 HP Cast Iron Submersible Sump Pump", 0.50, 5400, 4200, 22.0, 1.5, 7.6),
    ("Wayne CDU980E 3/4 HP Stainless & Cast Iron Sump Pump", 0.75, 5490, 4600, 26.0, 1.5, 8.5),
    ("Wayne ESP25 12V DC Battery Backup Sump Pump System", 0.33, 3300, 2300, 20.0, 1.5, 12.5),
    ("Liberty Pumps 257 1/3 HP Cast Iron Vertical Float Sump", 0.33, 3000, 2280, 21.5, 1.5, 5.2),
    ("Liberty Pumps 287 1/2 HP Cast Iron Submersible Sump", 0.50, 4500, 3720, 32.0, 1.5, 7.3),
    ("Liberty Pumps PC257-441 1/3 HP + 12V Battery Backup Combo", 0.33, 3000, 2280, 21.5, 1.5, 5.2),
    ("Liberty Pumps SJ10 SumpJet Water-Powered Backup Pump", 0.33, 1980, 1320, 20.0, 1.5, 0.0),
    ("Basement Watchdog Big Combo (CITE-33) 1/2 HP + Backup", 0.50, 4400, 3680, 22.0, 1.5, 5.0),
    ("Basement Watchdog BW4000 1/2 HP + Dual Float Backup", 0.50, 4400, 3700, 22.5, 1.5, 5.0),
    ("Superior Pump 92341 1/3 HP Cast Iron Vertical Switch", 0.33, 2760, 2100, 25.0, 1.5, 4.1),
    ("Superior Pump 92571 1/2 HP Cast Iron Vortex Sump Pump", 0.50, 3900, 3000, 25.0, 1.5, 4.9),
    ("Superior Pump 92911 1/2 HP + 12V Battery Backup Combo", 0.50, 3900, 3000, 25.0, 1.5, 4.9),
    ("Little Giant 6-CIA 1/3 HP Epoxy-Coated Cast Iron Sump", 0.33, 2760, 2160, 18.0, 1.5, 9.0),
    ("Little Giant 8-CIA 4/10 HP Submersible Cast Iron Sump", 0.40, 3240, 2520, 23.0, 1.5, 10.0),
    ("Little Giant 10-CIA 1/2 HP Heavy-Duty Cast Iron Sump", 0.50, 4200, 3660, 26.0, 1.5, 11.0),
    ("Goulds Water Technology GSP0311 1/3 HP Stainless Sump", 0.33, 3180, 2460, 23.0, 1.5, 6.5),
    ("Pentair Flotec FPZS50V 1/2 HP Zinc Dissipating Sump", 0.50, 4200, 3480, 22.0, 1.5, 6.8),
    (" Pentair Myers MCSP5 1/2 HP Cast Iron Sump Pump", 0.50, 4380, 3600, 24.0, 1.5, 7.2),
    ("1,500 Sq Ft Basement with Average Water Table Sizing", 0.33, 3000, 2280, 21.0, 1.5, 5.2),
    ("2,000 Sq Ft Basement with High Water Table & Clay Soil", 0.50, 4320, 3660, 24.0, 1.5, 7.5),
    ("2,500 Sq Ft Deep Basement (12 Ft Vertical Lift) Sizing", 0.50, 4500, 3720, 28.0, 1.5, 7.6),
    ("3,000 Sq Ft High-Inflow French Drain Basement Sizing", 0.75, 5490, 4600, 28.0, 2.0, 8.5),
    ("Crawlspace Encapsulation & Shallow Basin Sump Sizing", 0.33, 2760, 2100, 20.0, 1.5, 4.8),
    ("Duplex Alternating Twin 1/2 HP Sump Pump Pit Sizing", 0.50, 4500, 3720, 26.0, 2.0, 7.5),
    ("12V 100Ah AGM & LiFePO4 Sump Pump Battery Runtime", 0.33, 3300, 2300, 20.0, 1.5, 12.5)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=3000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_sump_queries():
    discovered = []
    seeds = [
        "what size sump pump for ",
        "zoeller sump pump ",
        "wayne sump pump ",
        "sump pump battery backup runtime "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        is_half = "1/2" in cleaned or "m98" in cleaned or "wss30" in cleaned
                        if is_half:
                            discovered.append((cleaned.title(), 0.50, 4320, 3660, 23.0, 1.5, 7.6))
                        else:
                            discovered.append((cleaned.title(), 0.33, 2800, 2150, 20.0, 1.5, 5.0))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_sump_data(pump_tuple):
    """Mesin Fisika Kurva TDH Sump Pump & Runtime Baterai 12V DC (100% bebas gagal)."""
    model_name, hp, gph_0ft, gph_10ft, shutoff_ft, pipe_in, amps_120v = pump_tuple

    # Perhitungan Total Dynamic Head (TDH) standar basement:
    # 9 ft vertical lift + 1.5 ft Check Valve loss + (2x 90-deg elbows = 3.0 ft) + (15 ft horizontal pipe = 1.5 ft) = 15.0 ft TDH
    std_tdh_ft = 14.5
    # Interpolasi debit GPH pada 14.5 ft TDH berdasarkan kurva pompa
    drop_per_ft = (gph_0ft - gph_10ft) / 10.0
    net_gph_at_14ft = max(600, int(round(gph_0ft - (drop_per_ft * std_tdh_ft), -1)))
    net_gpm_at_14ft = round(net_gph_at_14ft / 60.0, 1)

    # Perhitungan durasi baterai cadangan 12V 100Ah Deep-Cycle (pada siklus kerja badai 20% = menyala 12 menit per jam, arus DC 13A)
    continuous_100ah_hrs = round((100.0 * 0.85) / 13.0, 1)
    storm_20pct_cycle_hrs = round(continuous_100ah_hrs / 0.20, 1)

    hp_label = "1/3 HP" if hp <= 0.35 else ("1/2 HP" if hp <= 0.55 else "3/4 HP")

    return {
        "pump_name": model_name,
        "hp_label": hp_label,
        "seo_title": f"{model_name} GPH Head-Loss, TDH & Battery Backup Calculator (2026)",
        "meta_description": f"Calculate exact discharge flow ({gph_10ft:,} GPH @ 10ft / {net_gph_at_14ft:,} GPH @ 14.5ft TDH), check valve friction loss, and 12V 100Ah battery backup runtime ({storm_20pct_cycle_hrs} hrs) for {model_name}.",
        "specs": {
            "motor_hp": hp,
            "hp_label": hp_label,
            "gph_at_0ft": gph_0ft,
            "gph_at_10ft": gph_10ft,
            "gph_at_14ft_tdh": net_gph_at_14ft,
            "gpm_at_14ft_tdh": net_gpm_at_14ft,
            "shutoff_head_ft": shutoff_ft,
            "discharge_pipe_inches": pipe_in,
            "amps_120v": amps_120v,
            "backup_100ah_storm_hrs": storm_20pct_cycle_hrs
        },
        "hydraulic_verdict": f"Rated at {gph_10ft:,} GPH at a 10-foot vertical lift ({hp_label} / {amps_120v}A @ 120V, {shutoff_ft} ft shut-off head), the {model_name} delivers {net_gph_at_14ft:,} GPH ({net_gpm_at_14ft} GPM) through a real-world 14.5-foot Total Dynamic Head (TDH) basement plumbing run (9 ft vertical wall + check valve + two 90° elbows + 15 ft horizontal pipe). Pairing this primary unit with a 12V DC Backup Pump and a 100Ah Deep-Cycle AGM/LiFePO4 battery provides ~{storm_20pct_cycle_hrs} hours of flood protection during a power outage (at a 20% storm duty cycle).",
        "hardware_bundle": [
            {
                "badge": f"{hp_label} Primary / Combo",
                "title": f"{model_name} Cast-Iron Submersible Sump System",
                "price_range": "$189 - $699",
                "amazon_query": f"{model_name} Sump Pump",
                "sump_note": f"Hermetically sealed oil-filled cast iron housing dissipates motor heat and pumps {gph_10ft:,} GPH at 10-ft lift."
            },
            {
                "badge": "12V 100Ah Standby Battery",
                "title": "12V 100Ah Deep-Cycle AGM / LiFePO4 Maintenance-Free Sump Pump Backup Battery",
                "price_range": "$169 - $299",
                "amazon_query": "12V 100Ah AGM Deep Cycle Battery Sump Pump Backup",
                "sump_note": f"Powers a 12V DC backup pump for {continuous_100ah_hrs} hours continuously or {storm_20pct_cycle_hrs}+ hours of intermittent storm cycling."
            },
            {
                "badge": f"{pipe_in}\" Silent Check Valve",
                "title": f"{pipe_in}-Inch Clear Spring-Loaded Silent Sump Pump Check Valve (Stainless Clamps)",
                "price_range": "$29 - $54",
                "amazon_query": f"1-1/2 Inch Silent Check Valve Sump Pump Clear Spring Loaded",
                "sump_note": "Eliminates loud basement pipe-slamming water hammer and lets you visually inspect water flow and impeller operation."
            },
            {
                "badge": "Basin & WiFi Flood Alarm",
                "title": "18\" × 22\" Perforated Sump Basin w/ Airtight Radon Lid + Smart Wi-Fi Water Leak Alarm",
                "price_range": "$69 - $149",
                "amazon_query": "18x22 Perforated Sump Pump Basin Lid WiFi Water Leak Alarm",
                "sump_note": "Prevents gravel short-cycling and sends instant smartphone alerts if water rises above the primary float switch."
            }
        ],
        "plumber_checklist": [
            f"Drill a 3/16-inch (4.8mm) 'Weep Hole' at a 45-degree downward angle in the {pipe_in}\" PVC discharge pipe between the pump discharge port and the check valve; without a weep hole, trapped air causes 'Air-Lock' where the pump spins at 3,450 RPM but moves zero water.",
            "Use two 45-degree PVC sweeps instead of sharp 90-degree elbows on your vertical-to-horizontal basement transitions to cut friction head loss by 40%.",
            "Install a spring-loaded Silent Check Valve 12 to 18 inches above the sump basin lid so the weight of the vertical water column never back-flushes into the pit and causes short-cycling.",
            "Plug your sump pump into a dedicated 15A or 20A single-receptacle circuit (and test your 12V battery backup float switch monthly by pouring 5 gallons of water into the pit with AC power unplugged)."
        ],
        "faqs": [
            {
                "q": f"How many GPH does the {model_name} pump at 10 feet vs 15 feet of Total Dynamic Head?",
                "a": f"At a 10-foot vertical lift it delivers {gph_10ft:,} GPH ({round(gph_10ft/60, 1)} GPM). Once you add friction head from a check valve and two 90-degree PVC elbows (~14.5 feet Total Dynamic Head), real-world output is {net_gph_at_14ft:,} GPH ({net_gpm_at_14ft} GPM), with a maximum shut-off height of {shutoff_ft} feet."
            },
            {
                "q": f"How long will a 12V battery backup sump pump run during a power outage?",
                "a": f"A 12V DC backup pump draws ~12 to 14 Amps while actively pumping. Paired with a 100Ah Deep-Cycle AGM or LiFePO4 battery, it provides {continuous_100ah_hrs} hours of non-stop pumping, which equals {storm_20pct_cycle_hrs} hours (nearly 1.5 days) when cycling on for 30 seconds every 2.5 minutes (20% duty cycle)."
            },
            {
                "q": f"Should I get a 1/3 HP or 1/2 HP sump pump for my basement?",
                "a": f"For average water tables and vertical lifts under 8 feet, a 1/3 HP cast-iron pump ({gph_10ft:,} GPH class) is ideal. If your basement sits on clay soil, has a high water table, or pushes water up 10+ feet and out a long 25-foot buried yard pipe, upgrade to a 1/2 HP cast-iron pump."
            }
        ]
    }


def generate_sump_data(pump_tuple):
    if not GEMINI_API_KEY:
        return build_deterministic_sump_data(pump_tuple)

    model_name, hp, gph_0ft, gph_10ft, shutoff_ft, pipe_in, amps_120v = pump_tuple
    det_fallback = build_deterministic_sump_data(pump_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Master Licensed Plumber & Basement Waterproofing Hydraulic Engineer. Create an accurate 2026 sump pump GPH head-loss, Total Dynamic Head (TDH), and 12V battery backup runtime guide for: "{model_name}".
Baseline specs: Motor={sp['hp_label']} ({amps_120v}A @ 120V), Flow @ 0ft={gph_0ft} GPH, Flow @ 10ft={gph_10ft} GPH, Real-World Flow @ 14.5ft TDH={sp['gph_at_14ft_tdh']} GPH ({sp['gpm_at_14ft_tdh']} GPM), Shut-off Head={shutoff_ft} ft, Pipe={pipe_in} Inch PVC, 100Ah Battery Storm Runtime={sp['backup_100ah_storm_hrs']} hrs.
Return ONLY a valid JSON object matching this exact schema:
{{
  "pump_name": "{model_name}",
  "hp_label": "{sp['hp_label']}",
  "seo_title": "{model_name} GPH Head-Loss, TDH & Battery Backup Calculator (2026)",
  "meta_description": "Calculate exact sump pump GPH flow rate by vertical lift and elbow friction loss, pit sizing, and 12V battery backup runtime for {model_name}.",
  "specs": {{
    "motor_hp": {hp},
    "hp_label": "{sp['hp_label']}",
    "gph_at_0ft": {gph_0ft},
    "gph_at_10ft": {gph_10ft},
    "gph_at_14ft_tdh": {sp['gph_at_14ft_tdh']},
    "gpm_at_14ft_tdh": {sp['gpm_at_14ft_tdh']},
    "shutoff_head_ft": {shutoff_ft},
    "discharge_pipe_inches": {pipe_in},
    "amps_120v": {amps_120v},
    "backup_100ah_storm_hrs": {sp['backup_100ah_storm_hrs']}
  }},
  "hydraulic_verdict": "3-sentence technical summary stating GPH at 10ft lift, real-world GPH at 14.5ft TDH (including check valve and elbows), shutoff head, and 12V 100Ah battery backup runtime.",
  "hardware_bundle": [
    {{
      "badge": "{sp['hp_label']} Sump System",
      "title": "{model_name}",
      "price_range": "$189 - $699",
      "amazon_query": "{model_name} Sump Pump",
      "sump_note": "1-sentence cast-iron cooling and GPH performance note"
    }},
    {{
      "badge": "12V 100Ah Standby Battery",
      "title": "12V 100Ah Deep-Cycle AGM / LiFePO4 Sump Pump Backup Battery",
      "price_range": "$169 - $299",
      "amazon_query": "12V 100Ah AGM Deep Cycle Battery Sump Pump Backup",
      "sump_note": "1-sentence outage runtime and maintenance-free note"
    }},
    {{
      "badge": "Silent Check Valve",
      "title": "{pipe_in}-Inch Clear Spring-Loaded Silent Sump Check Valve",
      "price_range": "$29 - $54",
      "amazon_query": "1-1/2 Inch Silent Check Valve Sump Pump Clear",
      "sump_note": "1-sentence water hammer elimination note"
    }},
    {{
      "badge": "Basin & WiFi Flood Alarm",
      "title": "18x22 Perforated Sump Basin + Smart Wi-Fi High-Water Flood Alarm",
      "price_range": "$69 - $149",
      "amazon_query": "Perforated Sump Pump Basin Lid WiFi Water Leak Alarm",
      "sump_note": "1-sentence short-cycling prevention and mobile alert note"
    }}
  ],
  "plumber_checklist": [
    "Step 1 regarding 3/16-inch anti-airlock weep hole below check valve",
    "Step 2 regarding 45-degree PVC sweeps vs 90-degree elbows to reduce TDH",
    "Step 3 regarding silent check valve height above basin lid",
    "Step 4 regarding dedicated circuit and monthly 12V backup float test"
  ],
  "faqs": [
    {{"q": "How many GPH does the {model_name} pump at 10ft vs 15ft TDH?", "a": "Exact GPH and GPM numbers plus shut-off head height."}},
    {{"q": "How long will a 100Ah battery run a 12V backup sump pump?", "a": "Exact continuous hours vs 20% and 10% storm duty cycle hours."}},
    {{"q": "Why do I need a 3/16-inch weep hole in my sump discharge pipe?", "a": "Direct hydraulic explanation of impeller air-locking."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")

    return det_fallback


def build_sump_html_page(data, slug, mon_cfg):
    pump_name = data.get("pump_name", "Cast-Iron Sump Pump")
    sp = data.get("specs", {})
    hp_lbl = sp.get("hp_label", "1/2 HP")
    gph_0 = int(safe_float(sp.get("gph_at_0ft", 4320), 4320))
    gph_10 = int(safe_float(sp.get("gph_at_10ft", 3660), 3660))
    gph_14 = int(safe_float(sp.get("gph_at_14ft_tdh", 3150), 3150))
    shutoff_ft = round(safe_float(sp.get("shutoff_head_ft", 23.0), 23.0), 1)
    pipe_in = round(safe_float(sp.get("discharge_pipe_inches", 1.5), 1.5), 1)
    amps_ac = round(safe_float(sp.get("amps_120v", 7.6), 7.6), 1)
    storm_hrs = round(safe_float(sp.get("backup_100ah_storm_hrs", 32.5), 32.5), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Cast+Iron+Sump+Pump+12V+Battery+Backup+Combo"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{pump_name} GPH Head-Loss & Battery Backup Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Cast Iron Sump Pump")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-cyan-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Sump Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🌊 {item.get('sump_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Head Height vs GPH Pump Curve Table (5 ft, 10 ft, 12 ft, 15 ft, 18 ft, Shut-Off)
    slope_rate = (gph_0 - gph_10) / 10.0
    matrix_rows_html = ""
    for h_ft in [5, 10, 12, 15, 18]:
        est_flow = max(0, int(round(gph_0 - (slope_rate * h_ft), -1))) if h_ft < shutoff_ft else 0
        est_gpm = round(est_flow / 60.0, 1)
        status_s = "✅ Optimal Flow" if est_flow >= 1800 else ("⚠️ Moderate Flow" if est_flow > 0 else "❌ Exceeds Shut-Off Head")
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{h_ft} Feet TDH</td>
          <td class="py-3 px-4 font-bold text-cyan-400">{est_flow:,} GPH</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{est_gpm} GPM</td>
          <td class="py-3 px-4 text-xs text-slate-300">{status_s}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("plumber_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-cyan-500 rounded cursor-pointer sump-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>Plumbing Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', pump_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', pump_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">SUMP</span>FlowIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Sump Pumps & 12V Backups →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-cyan-500 text-slate-950 px-3 py-1 rounded-full">{hp_lbl} ({gph_10:,} GPH @ 10ft)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">14.5ft TDH: {gph_14:,} GPH | Max Head: {shutoff_ft} ft</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{pipe_in}" PVC | 100Ah Backup: ~{storm_hrs} hrs</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', pump_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-cyan-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>Master Plumber Hydraulic & Backup Verdict:</strong> {data.get('hydraulic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE VERTICAL LIFT, ELBOW TDH & 12V BATTERY BACKUP RUNTIME CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {pump_name} TDH Flow & Battery Backup Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your vertical basement wall height, horizontal discharge pipe run, 90° elbow count, and 12V backup battery Ah rating to compute exact Total Dynamic Head (TDH), net GPH flow, and outage runtime.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="vertSlider" class="text-slate-300">Vertical Discharge Height from Pit Floor (Feet)</label>
              <span class="text-cyan-400 font-bold"><span id="vertVal">9</span> ft Vertical</span>
            </div>
            <input id="vertSlider" type="range" min="4" max="20" step="1" value="9" class="w-full accent-cyan-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="horizSlider" class="text-slate-300">Horizontal Pipe Run + Check Valve & Elbows (Feet)</label>
              <span class="text-cyan-400 font-bold"><span id="horizVal">20</span> ft Horizontal</span>
            </div>
            <input id="horizSlider" type="range" min="5" max="80" step="5" value="20" class="w-full accent-cyan-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="battAhSelect" class="block text-xs font-medium text-slate-400 mb-1">12V Backup Battery Size</label>
              <select id="battAhSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="75">75Ah Group-24 AGM</option>
                <option value="100" selected>100Ah Group-27/31 AGM / LiFePO4</option>
                <option value="200">200Ah Dual-Battery Bank</option>
              </select>
            </div>
            <div>
              <label for="stormCycleSelect" class="block text-xs font-medium text-slate-400 mb-1">Storm Inflow Duty Cycle</label>
              <select id="stormCycleSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="0.10">Light Rain (10% — Runs 6m/hr)</option>
                <option value="0.20" selected>Heavy Storm (20% — Runs 12m/hr)</option>
                <option value="0.50">Severe Flood (50% — Runs 30m/hr)</option>
                <option value="1.00">Continuous Non-Stop (100%)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-cyan-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-cyan-400 font-bold">Net Discharge Flow</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="gphOut">{gph_14:,}</span> <span class="text-xs font-normal text-slate-400">GPH</span></div>
            <p id="tdhNoteOut" class="text-xs text-cyan-400 font-semibold mt-1">At 14.5 ft Total Head (TDH)</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">12V Outage Runtime</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1">~<span id="backupHrsOut">{storm_hrs}</span> <span class="text-xs font-normal text-slate-400">hrs</span></div>
            <p id="recHpOut" class="text-xs text-slate-300 font-semibold mt-1">Match: {hp_lbl} + 12V Combo</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-cyan-950/40 border border-cyan-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="sumpAdviceBanner" class="text-sm text-cyan-100 font-medium"></div>
        <a id="dynamicSumpBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Sump Combo on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {pump_name} Backup, Battery & Check Valve Kit</h2>
        <span class="text-xs text-slate-400">Cast-Iron Continuous Duty & Flood-Protected</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- PUMP HEAD CURVE MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{pump_name} GPH & GPM Flow Curve by Total Dynamic Head (TDH)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Total Dynamic Head (TDH)</th>
              <th class="py-3.5 px-4 text-cyan-400">Discharge Flow (GPH)</th>
              <th class="py-3.5 px-4 text-emerald-400">Gallons Per Minute (GPM)</th>
              <th class="py-3.5 px-4">Pump Curve Status</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- PLUMBER CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Master Plumber Anti-Airlock Weep Hole & Check Valve Checklist</h2>
        <span id="sumpBadge" class="text-xs font-bold bg-slate-800 text-cyan-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({pump_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} SumpFlowIndex. Independent Basement Waterproofing & Sump Pump Hydraulic Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const baseGph0 = {gph_0};
    const baseGph10 = {gph_10};
    const maxShutoffFt = {shutoff_ft};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const vertSlider = document.getElementById('vertSlider');
    const horizSlider = document.getElementById('horizSlider');
    const battAhSelect = document.getElementById('battAhSelect');
    const stormCycleSelect = document.getElementById('stormCycleSelect');
    const vertVal = document.getElementById('vertVal');
    const horizVal = document.getElementById('horizVal');
    const gphOut = document.getElementById('gphOut');
    const tdhNoteOut = document.getElementById('tdhNoteOut');
    const backupHrsOut = document.getElementById('backupHrsOut');
    const recHpOut = document.getElementById('recHpOut');
    const sumpAdviceBanner = document.getElementById('sumpAdviceBanner');
    const dynamicSumpBtn = document.getElementById('dynamicSumpBtn');

    function recalculateSump() {{
      const vFt = parseInt(vertSlider.value, 10);
      const hFt = parseInt(horizSlider.value, 10);
      const battAh = parseInt(battAhSelect.value, 10);
      const dutyCycle = parseFloat(stormCycleSelect.value);

      vertVal.textContent = vFt;
      horizVal.textContent = hFt;

      // TDH = Vertical Lift + Check Valve (1.5 ft) + 2x Elbows (3.0 ft) + Horizontal Friction (hFt * 0.12)
      const totalTdh = vFt + 4.5 + (hFt * 0.12);
      const dropPerFt = (baseGph0 - baseGph10) / 10.0;
      let netGph = Math.round((baseGph0 - (dropPerFt * totalTdh)) / 10) * 10;
      if (totalTdh >= maxShutoffFt || netGph < 200) netGph = 0;

      const contHrs = (battAh * 0.85) / 13.0;
      const outageHrs = (contHrs / dutyCycle).toFixed(1);

      let recHpTier = "1/3 HP";
      if (totalTdh > 16.5) recHpTier = "3/4 HP High-Head";
      else if (totalTdh > 12.5) recHpTier = "1/2 HP Cast-Iron";

      gphOut.textContent = netGph.toLocaleString();
      tdhNoteOut.textContent = `At ${{totalTdh.toFixed(1)}} ft Total Head (TDH)`;
      backupHrsOut.textContent = outageHrs;
      recHpOut.textContent = `Match: ${{recHpTier}} + 12V Combo`;

      sumpAdviceBanner.innerHTML = `🌊 <strong>Hydraulic Spec:</strong> Pushing water up <strong>${{vFt}} ft vertical + ${{hFt}} ft horizontal (${{totalTdh.toFixed(1)}} ft TDH)</strong> requires a <strong>${{recHpTier}} Primary + 12V Battery Backup Sump Combo</strong> paired with a <strong>12V ${{battAh}}Ah Deep-Cycle AGM Battery</strong> and a 1-1/2" Silent Check Valve.`;
      dynamicSumpBtn.href = `https://${{amzDomain}}/s?k=${{encodeURIComponent(recHpTier)}}+Cast+Iron+Sump+Pump+12V+Battery+Backup+Combo+Silent+Check+Valve&tag=${{amzTag}}`;
    }}

    vertSlider.addEventListener('input', recalculateSump);
    horizSlider.addEventListener('input', recalculateSump);
    battAhSelect.addEventListener('change', recalculateSump);
    stormCycleSelect.addEventListener('change', recalculateSump);
    recalculateSump();

    const checks = document.querySelectorAll('.sump-check');
    const badge = document.getElementById('sumpBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Cast+Iron+Sump+Pump+12V+Battery+Backup+Combo"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-cyan-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-cyan-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('hp_label', '1/2 HP')} | {item.get('gph_10', 3660):,} GPH</span>
            <span class="text-xs text-slate-400">14.5ft TDH: {item.get('gph_14', 3150):,} GPH</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-cyan-400 transition">{item['pump_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-cyan-400">Calculate TDH Head Loss & 12V Backup →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SumpFlowIndex — Basement Sump Pump GPH Head-Loss & 12V Battery Backup Calculator (2026)</title>
  <meta name="description" content="Calculate exact basement sump pump GPH flow rate by vertical lift and elbow friction head (TDH), pit basin sizing, and 12V AGM battery backup runtime for Zoeller, Wayne, Liberty, Basement Watchdog, and Superior pumps.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="SumpFlowIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">SUMP</span>FlowIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Sump Pumps & 12V Backups →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Basement Sump Pump GPH, TDH Head-Loss & 12V Backup Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your sump pump model or basement dimensions below to calculate net GPH flow after vertical lift and check-valve friction loss, plus 12V battery outage runtime.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search pump model or scenario (e.g. Zoeller M53, Zoeller M98, Wayne WSS30Vn, Liberty 257, 1/2 HP, Battery Backup...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-cyan-500">
      </div>
    </div>

    <div id="sumpGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} SumpFlowIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('sumpGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SumpFlowIndex Basement Sump Pump & Battery Backup Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Sump Pump GPH Head-Loss, TDH & 12V Battery Backup Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_SUMP:
        candidates.append((CUSTOM_SUMP.strip(), 0.50, 4320, 3660, 23.0, 1.5, 7.6))
    candidates.extend(SEED_PUMPS)
    candidates.extend(discover_google_sump_queries())

    new_urls = []
    count = 0

    for pump_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        p_name = pump_tuple[0]
        slug = slugify(f"{p_name}-gph-head-loss-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating sump pump GPH & 12V backup calculator for: {p_name}...")
        try:
            data = generate_sump_data(pump_tuple)
            build_sump_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "pump_name": data.get("pump_name", p_name),
                "slug": slug,
                "title": data.get("seo_title", f"{p_name} Sump Calculator"),
                "description": data.get("meta_description", ""),
                "hp_label": sp.get("hp_label", "1/2 HP"),
                "gph_10": int(safe_float(sp.get("gph_at_10ft", pump_tuple[3]), pump_tuple[3])),
                "gph_14": int(safe_float(sp.get("gph_at_14ft_tdh", 3150), 3150)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {p_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new sump pump GPH & battery backup calculator pages.")


if __name__ == "__main__":
    main()
