# compare_geojson.py
# Укажи пути к файлам тут:
FILE_A = r"C:\Users\IVAN\Downloads\ДКР ГП Здравоохранение.ЦУ КГХ для форматирования на Json _5_.geojson"
FILE_B = r"E:\IAC_city_development\Create JSON\ДКР ГП Здравоохранение.ЦУ КГХ для форматирования на Json (5).geojson"
EPS_DIGITS = 6  # точность округления чисел при сравнении

import json, sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def norm_numbers(x: Any, ndigits: int) -> Any:
    """Рекурсивно округляет все числа до ndigits, чтобы сгладить микросдвиги."""
    if is_number(x):
        return round(float(x), ndigits)
    if isinstance(x, list):
        return [norm_numbers(v, ndigits) for v in x]
    if isinstance(x, dict):
        return {k: norm_numbers(v, ndigits) for k, v in x.items()}
    return x

def deep_diff(a: Any, b: Any, path: str = "$") -> List[str]:
    """Глубокое сравнение структур. Возвращает список строк-расхождений."""
    diffs: List[str] = []
    if type(a) != type(b):
        diffs.append(f"{path}: TYPE {type(a).__name__} != {type(b).__name__}")
        return diffs

    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            pa = f"{path}.{k}"
            if k not in a:
                diffs.append(f"{pa}: MISSING in A, value in B={b[k]!r}")
            elif k not in b:
                diffs.append(f"{pa}: MISSING in B, value in A={a[k]!r}")
            else:
                diffs.extend(deep_diff(a[k], b[k], pa))
        return diffs

    if isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: LEN {len(a)} != {len(b)}")
        for i in range(min(len(a), len(b))):
            diffs.extend(deep_diff(a[i], b[i], f"{path}[{i}]"))
        return diffs

    if a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
    return diffs

def feature_key(feat: Dict[str, Any]) -> Tuple[str, Any]:
    """Ключ сопоставления фич: по id или по свойствам, иначе без ключа."""
    if "id" in feat:
        return ("id", feat["id"])
    props = feat.get("properties") or {}
    for alt in ("object_id", "id", "AIS_DKR_ID", "ais_dkr_id"):
        if alt in props:
            return ("prop", props[alt])
    return ("idx", None)

def index_features(fc: Dict[str, Any]) -> Dict[Tuple[str, Any], Dict[str, Any]]:
    out: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for feat in fc.get("features", []):
        out[feature_key(feat)] = feat
    return out

def is_featurecollection(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("type") == "FeatureCollection"

def compare_geojson(a: Any, b: Any, float_eps_digits: int) -> List[str]:
    a = norm_numbers(a, float_eps_digits)
    b = norm_numbers(b, float_eps_digits)

    if not (is_featurecollection(a) and is_featurecollection(b)):
        return deep_diff(a, b, "$")

    diffs: List[str] = []
    # верхний уровень без features
    for meta_key in ("type", "name", "crs"):
        diffs += deep_diff(a.get(meta_key), b.get(meta_key), f"$.{meta_key}")

    feats_a = a.get("features", [])
    feats_b = b.get("features", [])
    if len(feats_a) != len(feats_b):
        diffs.append(f"$.features: COUNT {len(feats_a)} != {len(feats_b)}")

    ia = index_features(a)
    ib = index_features(b)
    keys = set(ia.keys()) | set(ib.keys())
    for k in keys:
        p = f"$.features[{k[0]}={k[1]}]"
        if k not in ia:
            diffs.append(f"{p}: MISSING in A")
            continue
        if k not in ib:
            diffs.append(f"{p}: MISSING in B")
            continue
        fa = {kk: ia[k].get(kk) for kk in ("type", "id", "geometry", "properties")}
        fb = {kk: ib[k].get(kk) for kk in ("type", "id", "geometry", "properties")}
        diffs += deep_diff(fa, fb, p)
    return diffs

def main():
    a_path = Path(FILE_A)
    b_path = Path(FILE_B)
    try:
        a = load_json(a_path)
        b = load_json(b_path)
    except Exception as e:
        print(f"Ошибка чтения: {e}", file=sys.stderr)
        sys.exit(2)

    diffs = compare_geojson(a, b, EPS_DIGITS)
    if not diffs:
        print("OK: GeoJSON совпадают")
        sys.exit(0)

    print("❌ Найдены различия:")
    for line in diffs:
        print(line)
    sys.exit(1)

if __name__ == "__main__":
    main()
