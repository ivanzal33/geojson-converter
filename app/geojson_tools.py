import pandas as pd
import re, ast
from datetime import date
from typing import Dict, List, Any

COLUMN_TYPES: Dict[str, type] = {
    "ais_dkr_id": int,
    "asu_ods_id": int,
    "uds_count_in_object": int,
    "district": str,
    "region": str,
    "state_program": str,
    "object_category": str,
    "inn_oiv_grbs": str,
    "oiv_grbs": str,
    "inn_state_customer": str,
    "state_customer": str,
    "object_name": str,
    "object_status_on_report_date": str,
    "discussion_with_residents": str,
    "measurement_unit": str,
    "indicator_volume_unit": float,
    "expertise_status_pir": str,
    "planned_auction_date_pir": date,
    "actual_auction_date_pir": date,
    "planned_contract_date_pir": date,
    "actual_contract_date_pir": date,
    "inn_project_organization": str,
    "project_organization_name": str,
    "psd_development_period": date,
    "expertise_status_smr": str,
    "planned_review_date_pre_mrg": date,
    "actual_review_date_pre_mrg": date,
    "planned_review_date_mrg": date,
    "actual_review_date_mrg": date,
    "planned_auction_date_smr": date,
    "actual_auction_date_smr": date,
    "planned_contract_date_smr": date,
    "actual_contract_date_smr": date,
    "work_cost_million_rub": float,
    "paid_work_cost_million_rub": float,
    "planned_start_date_smr": date,
    "planned_end_date_smr": date,
    "actual_start_date_smr": date,
    "actual_end_date_smr": date,
    "contract_end_date": date,
    "inn_contractor": str,
    "contractor": str,
    "object_readiness_percentage": int,
    "state_commission_approval_date": date,
    "last_work_year": int,
    "start_work_year": int,
    "current_work_year": int,
    "kbk": str,
    "workers_count": int,
    "machinery_count": int,
    "penalty_cost_million_rub": int,
    "building_repair_area_sq_m": float,
    "road_repair_area_uds_sq_m": float,
    "other_road_repair_area_sq_m": float,
    "soft_covering_area_sq_m": float,
    "granite_paving_area_sq_m": float,
    "concrete_paving_area_sq_m": float,
    "granite_bordure_area_m": float,
    "concrete_bordure_area_m": float,
    "lawn_area_sq_m": float,
    "tree_planting_count": int,
    "bush_planting_count": int,
    "maf_installation_count": int,
    "lighting_pole_installation_count": int,
    "storm_water_network_development_m": float,
    "cable_channel_installation_m": float,
    "public_transport_stop_count": int,
    "bicycle_parking_count": int,
    "navigation_stellas_count": int,
    "demolition_work_volume_cubic_m": float,
    "floor_screed_area_sq_m": float,
    "interior_finishing_area_sq_m": float,
    "ventilation_system_installation_m": float,
    "electrical_panel_installation_count": int,
    "water_supply_system_installation_count": int,
    "heating_system_installation_count": int,
    "ac_unit_installation_count": int,
    "surveillance_system_installation_count": int,
    "fence_installation_m": float,
    "barrier_installation_count": int,
    "parking_space_installation_count": int,
    "lift_platform_installation_count": int,
}

def convert_value(value, target_type):
    if pd.isna(value) or value == "":
        return None
    try:
        if target_type is int:
            f = float(str(value).replace(",", ".").strip())
            return int(f)
        if target_type is float:
            return float(str(value).replace(",", ".").strip())
        if target_type is str:
            return str(value).strip()
        if target_type is date:
            dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
            return None if pd.isna(dt) else dt.strftime("%d.%m.%Y")
    except:
        return None

def apply_column_types(df: pd.DataFrame, column_types: Dict[str, type]) -> pd.DataFrame:
    for col, t in column_types.items():
        if col in df.columns:
            df[col] = df[col].apply(lambda x: convert_value(x, t))
            if t is int:
                df[col] = df[col].astype("Int64")
    return df

def parse_coordinates(coord_value):
    if pd.isna(coord_value):
        return [0, 0]
    try:
        if isinstance(coord_value, str) and coord_value.strip().startswith("{"):
            coord_dict = ast.literal_eval(coord_value)
            if isinstance(coord_dict, dict) and "coordinates" in coord_dict:
                coords = coord_dict["coordinates"]
            else:
                return [0, 0]
        elif isinstance(coord_value, str):
            match = re.findall(r"[-+]?\d*\.\d+|\d+", coord_value)
            if len(match) == 2:
                coords = [float(match[0]), float(match[1])]
            else:
                return [0, 0]
        elif isinstance(coord_value, list) and len(coord_value) == 2:
            coords = coord_value
        else:
            return [0, 0]

        a, b = float(coords[0]), float(coords[1])
        # Москва: lon≈37, lat≈55
        if 36 <= a <= 39 and 54 <= b <= 56:
            return [a, b]          # [lon, lat]
        if 54 <= a <= 56 and 36 <= b <= 39:
            return [b, a]          # перестановка
        return [0, 0]
    except Exception:
        return [0, 0]

def df_to_geojson(df: pd.DataFrame, collection_name: str) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        coords = parse_coordinates(row.get("coordinates"))
        props = {}
        for col in df.columns:
            if col == "coordinates":
                continue
            val = row[col]
            props[col] = None if pd.isna(val) else val
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": coords}
        })
    return {
        "type": "FeatureCollection",
        "name": collection_name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features
    }