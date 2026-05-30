"""Generic extractor for Taiwanese A1 data → per-city JSON.

Usage:
  python3 extract_city.py taitung    # 台東縣 (rural; districts use 鄉鎮市)
  python3 extract_city.py tainan     # 台南市 (urban; districts use 區)

Output dir matches the city slug. Both 105-114 years are processed; pre-2018
years lack lat/lon, so the map section degrades gracefully.
"""
import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path("/Users/yunching0513/Taitung_Mobility/資料")
YEARS = [
    (105, 2016, "105年度A1交通事故資料.csv", "simple"),
    (106, 2017, "106年度A1交通事故資料.csv", "simple"),
    (107, 2018, "2018年度A1交通事故資料.csv", "full"),
    (108, 2019, "2019年度A1交通事故資料.csv", "full"),
    (109, 2020, "2020年度A1交通事故資料.csv", "full"),
    (110, 2021, "110年度A1交通事故資料.csv", "simple"),
    (111, 2022, "111年度A1交通事故資料.csv", "full"),
    (112, 2023, "112年度A1交通事故資料.csv", "full"),
    (113, 2024, "113年度A1交通事故資料.csv", "full"),
    (114, 2025, "114年度A1交通事故資料.csv", "full"),
]

CITIES = {
    "taitung": {
        "match_substrings": ("台東縣", "臺東縣"),
        "district_re": re.compile(r"(?:台東縣|臺東縣)(.{1,4}?[鄉鎮市])"),
        "name_zh": "台東縣",
        "name_en": "Taitung County",
    },
    "tainan": {
        "match_substrings": ("台南市", "臺南市"),
        "district_re": re.compile(r"(?:台南市|臺南市)(.{1,4}?區)"),
        "name_zh": "台南市",
        "name_en": "Tainan City",
    },
    "taipei": {
        "match_substrings": ("台北市", "臺北市"),
        "district_re": re.compile(r"(?:台北市|臺北市)(.{1,4}?區)"),
        "name_zh": "台北市",
        "name_en": "Taipei City",
    },
    "yilan": {
        "match_substrings": ("宜蘭縣",),
        "district_re": re.compile(r"宜蘭縣(.{1,4}?[鄉鎮市])"),
        "name_zh": "宜蘭縣",
        "name_en": "Yilan County",
    },
    "taichung": {
        "match_substrings": ("台中市", "臺中市"),
        "district_re": re.compile(r"(?:台中市|臺中市)(.{1,4}?區)"),
        "name_zh": "台中市",
        "name_en": "Taichung City",
    },
}

def normalize_district(name: str) -> str:
    return name.replace("臺", "台") if name else "其他"

def parse_casualties(s: str) -> tuple[int, int]:
    deaths = injuries = 0
    if not s: return 0, 0
    m = re.search(r"死亡(\d+)", s); deaths = int(m.group(1)) if m else 0
    m = re.search(r"受傷(\d+)", s); injuries = int(m.group(1)) if m else 0
    return deaths, injuries

ROC_DT_RE = re.compile(r"(\d+)年(\d+)月(\d+)日\s+(\d+)時(\d+)分(\d+)秒")
def parse_simple_datetime(s: str):
    m = ROC_DT_RE.match(s)
    if not m: return "", "", 0, 0
    roc, mo, day, hh, mm, ss = map(int, m.groups())
    year = roc + 1911
    return f"{year:04d}{mo:02d}{day:02d}", f"{hh:02d}{mm:02d}{ss:02d}", year, mo

def classify_mode(vehicle_str: str) -> str:
    """Classify a single vehicle string into one of 機車 / 汽車 / 人 / 慢車 / 其他."""
    v = vehicle_str or ""
    if "機車" in v: return "機車"
    if "客車" in v or "貨車" in v or "曳引" in v: return "汽車"
    if "行人" in v or v.strip() == "人": return "人"
    if "自行車" in v or "慢車" in v: return "慢車"
    return "其他"

# Vulnerability ordering — lower index = more vulnerable.
# Used to attribute an event to its most vulnerable party, which more
# closely matches the road-safety question "who dies on the road?".
VULN_RANK = {"人": 0, "慢車": 1, "機車": 2, "汽車": 3, "其他": 4}

def victim_mode_from_parties(parties: list) -> str:
    """Most-vulnerable mode present among the event's parties."""
    if not parties:
        return "其他"
    modes = set()
    for p in parties:
        text = (p.get("vehicle_main","") or "") + (p.get("vehicle_sub","") or "")
        modes.add(classify_mode(text))
    return min(modes, key=lambda m: VULN_RANK.get(m, 9))

def primary_vehicle_simple(vehicle_field: str) -> str:
    return (vehicle_field or "").split(";")[0]

def matches_city(loc: str, city_cfg) -> bool:
    return any(s in loc for s in city_cfg["match_substrings"])

def fix_coords(lon: float, lat: float) -> tuple[float, float]:
    """Some records have lat/lon swapped. Taiwan: lat 21-26, lon 119-123.
    Swap if lon looks like a latitude and vice versa."""
    if 21 <= lon <= 26 and 119 <= lat <= 123:
        return lat, lon  # swapped → return them swapped back
    return lon, lat

def extract(city_slug: str):
    city_cfg = CITIES[city_slug]
    district_re = city_cfg["district_re"]
    events = []
    for roc, cy, fname, schema in YEARS:
        path = BASE / f"{roc}年傷亡道路交通事故資料" / fname
        if not path.exists():
            print(f"MISSING: {path}", file=sys.stderr); continue
        with open(path, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        if schema == "simple":
            for row in rows:
                loc = row.get("發生地點", "")
                if not matches_city(loc, city_cfg): continue
                date, time, _, month = parse_simple_datetime(row.get("發生時間",""))
                deaths, injuries = parse_casualties(row.get("死亡受傷人數",""))
                dm = district_re.search(loc)
                district = normalize_district(dm.group(1)) if dm else "其他"
                try:
                    lon = float(row.get("經度") or 0); lat = float(row.get("緯度") or 0)
                    lon, lat = fix_coords(lon, lat)
                except ValueError:
                    lon = lat = 0.0
                veh_field = row.get("車種","")
                principal = primary_vehicle_simple(veh_field)
                # Simple schema has no per-party rows. Construct pseudo-parties
                # from the ';'-separated vehicle list so the same victim-mode
                # rule applies uniformly.
                pseudo_parties = [{"vehicle_main": v} for v in (veh_field or "").split(";") if v]
                event_mode = victim_mode_from_parties(pseudo_parties) if pseudo_parties else classify_mode(principal)
                events.append({
                    "schema": "simple", "roc": roc, "year": cy, "month": month,
                    "date": date, "time": time, "location": loc, "district": district,
                    "lon": lon, "lat": lat,
                    "deaths": deaths, "injuries": injuries,
                    "mode": event_mode,
                    "principal_mode": classify_mode(principal),
                    "principal_vehicle": principal,
                    "vehicles_raw": veh_field,
                    "weather":"", "light":"", "road_type":"", "speed_limit":"",
                    "road_shape_main":"", "road_shape_sub":"",
                    "surface":"", "signal":"", "accident_main":"", "accident_sub":"",
                    "cause_main":"", "parties":[],
                })
        else:
            by_key = {}
            for row in rows:
                loc = row.get("發生地點","")
                if not matches_city(loc, city_cfg): continue
                key = (row["發生日期"], row["發生時間"], row.get("經度",""), row.get("緯度",""), loc)
                by_key.setdefault(key, []).append(row)
            for key, group in by_key.items():
                first = group[0]
                try:
                    lon = float(first.get("經度") or 0); lat = float(first.get("緯度") or 0)
                    lon, lat = fix_coords(lon, lat)
                except ValueError:
                    lon = lat = 0.0
                dm = district_re.search(first.get("發生地點",""))
                district = normalize_district(dm.group(1)) if dm else "其他"
                deaths, injuries = parse_casualties(first.get("死亡受傷人數",""))
                month = int(first.get("發生月份") or 0)
                p1 = next((r for r in group if (r.get("當事者順位") or "")=="1"), group[0])
                principal_main = p1.get("當事者區分-類別-大類別名稱-車種","")
                principal_sub = p1.get("當事者區分-類別-子類別名稱-車種","")
                parties = []
                for r in group:
                    age_raw = r.get("當事者事故發生時年齡","")
                    try:
                        age = int(age_raw)
                        if age < 0: age = None
                    except ValueError:
                        age = None
                    parties.append({
                        "order": r.get("當事者順位",""),
                        "vehicle_main": r.get("當事者區分-類別-大類別名稱-車種",""),
                        "vehicle_sub": r.get("當事者區分-類別-子類別名稱-車種",""),
                        "gender": r.get("當事者屬-性-別名稱",""),
                        "age": age,
                        "protection": r.get("保護裝備名稱",""),
                        "action_main": r.get("當事者行動狀態大類別名稱",""),
                        "action_sub": r.get("當事者行動狀態子類別名稱",""),
                        "cause_individual": r.get("肇因研判子類別名稱-個別",""),
                    })
                events.append({
                    "schema":"full", "roc":roc, "year":cy, "month":month,
                    "date":first["發生日期"], "time":(first.get("發生時間","") or "").zfill(6),
                    "location":first["發生地點"], "district":district,
                    "lon":lon, "lat":lat,
                    "deaths":deaths, "injuries":injuries,
                    # victim-based (most vulnerable party) — primary classification
                    "mode": victim_mode_from_parties(parties),
                    # principal-party (P1) — kept for transparency / drill-downs
                    "principal_mode": classify_mode(principal_main + principal_sub),
                    "principal_vehicle": principal_main + (("·"+principal_sub) if principal_sub else ""),
                    "vehicles_raw":";".join(
                        (r.get("當事者區分-類別-大類別名稱-車種","") or "")
                        + ("-" + r.get("當事者區分-類別-子類別名稱-車種","") if r.get("當事者區分-類別-子類別名稱-車種") else "")
                        for r in group),
                    "weather":first.get("天候名稱",""), "light":first.get("光線名稱",""),
                    "road_type":first.get("道路類別-第1當事者-名稱",""),
                    "speed_limit":first.get("速限-第1當事者",""),
                    "road_shape_main":first.get("道路型態大類別名稱",""),
                    "road_shape_sub":first.get("道路型態子類別名稱",""),
                    "surface":first.get("路面狀況-路面狀態名稱",""),
                    "signal":first.get("號誌-號誌種類名稱",""),
                    "accident_main":first.get("事故類型及型態大類別名稱",""),
                    "accident_sub":first.get("事故類型及型態子類別名稱",""),
                    "cause_main":first.get("肇因研判子類別名稱-主要",""),
                    "parties":parties,
                })
    events.sort(key=lambda e:(e["date"], e["time"]))

    # Yearly summary
    yearly = {}
    for e in events:
        y = e["year"]
        s = yearly.setdefault(y, {
            "year":y, "roc":e["roc"], "schema":e["schema"],
            "events":0, "deaths":0, "injuries":0, "with_coords":0,
            "by_mode":Counter(), "by_district":Counter(),
            "by_month":Counter(), "by_hour":Counter(),
            "by_road":Counter(), "by_light":Counter(),
        })
        s["events"] += 1
        s["deaths"] += e["deaths"]; s["injuries"] += e["injuries"]
        if e["lon"] and e["lat"]: s["with_coords"] += 1
        s["by_mode"][e["mode"]] += 1
        s["by_district"][e["district"]] += e["deaths"]
        s["by_month"][e["month"]] += 1
        try: s["by_hour"][int(e["time"][:2])] += 1
        except ValueError: pass
        if e.get("road_type"): s["by_road"][e["road_type"]] += 1
        if e.get("light"): s["by_light"][e["light"]] += 1
    def ser(s):
        return {**{k:v for k,v in s.items() if not isinstance(v, Counter)},
                **{k:dict(v) for k,v in s.items() if isinstance(v, Counter)}}
    yearly_serial = [ser(yearly[y]) for y in sorted(yearly)]

    out_dir = Path(f"/Users/yunching0513/Taitung_Mobility/build_{city_slug}")
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"{city_slug}_a1.js").write_text(
        f"window.{city_slug.upper()}_A1 = " + json.dumps(events, ensure_ascii=False, separators=(",",":")) + ";\n"
        f"window.{city_slug.upper()}_YEARLY = " + json.dumps(yearly_serial, ensure_ascii=False, separators=(",",":")) + ";\n"
        # backward-compatible aliases used by the existing HTML
        f"window.TAITUNG_A1 = window.{city_slug.upper()}_A1;\n"
        f"window.TAITUNG_YEARLY = window.{city_slug.upper()}_YEARLY;\n"
    )
    # also a json snapshot
    (out_dir / "events.json").write_text(json.dumps(events, ensure_ascii=False, separators=(",",":")))
    (out_dir / "yearly.json").write_text(json.dumps(yearly_serial, ensure_ascii=False, separators=(",",":")))

    # Stats
    print(f"=== {city_cfg['name_zh']} ({city_cfg['name_en']}) ===")
    print(f"Total events: {len(events)} | Deaths: {sum(e['deaths'] for e in events)} | With coords: {sum(1 for e in events if e['lon'] and e['lat'])}")
    print(f"{'Year':<6}{'Events':>8}{'Deaths':>8}{'Coords':>8}  Top mode")
    for y in sorted(yearly):
        s = yearly[y]
        top = s["by_mode"].most_common(1)[0] if s["by_mode"] else ("-",0)
        print(f"{y:<6}{s['events']:>8}{s['deaths']:>8}{s['with_coords']:>8}  {top[0]} ({top[1]})")
    return events, yearly_serial

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CITIES:
        print("Usage: python3 extract_city.py [taitung|tainan]"); sys.exit(1)
    extract(sys.argv[1])
