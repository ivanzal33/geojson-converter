# app/routes.py
import uuid
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse
from .excel_tools import extract_combined_headers, diff_headers
from .reference_headers import REFERENCE_HEADERS
from .target_headers import TARGET_HEADERS
import pandas as pd
import json
from fastapi.responses import FileResponse
from .geojson_tools import COLUMN_TYPES, apply_column_types, df_to_geojson
import urllib.parse
import re
from fastapi import BackgroundTasks

router = APIRouter()
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _safe_stem(filename: str) -> str:
    # базовое имя без расширения
    stem = Path(filename).stem
    # аккуратная очистка: буквы/цифры/пробел/подчёркивание/дефис/точка
    return re.sub(r"[^0-9A-Za-zА-Яа-я _\.-]", "_", stem).strip()
def _unique_path(dir_: Path, filename: str) -> Path:
    p = dir_ / filename
    if not p.exists():
        return p
    stem = Path(filename).stem
    suf  = Path(filename).suffix
    i = 1
    while True:
        p = dir_ / f"{stem}({i}){suf}"
        if not p.exists():
            return p
        i += 1


@router.get("/health")
def health(): return {"status": "ok"}

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    for pattern in ("*.xlsx", "*.geojson", "*-renamed.csv", "*-no_number_col.csv"):
        for p in DATA_DIR.glob(pattern):
            try:
                p.unlink()
            except Exception:
                pass
    t = request.app.state.templates
    return t.TemplateResponse("index.html", {"request": request})

@router.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Ожидается .xlsx")

    job_id = str(uuid.uuid4())
    dst = DATA_DIR / f"{job_id}.xlsx"
    content = await file.read()
    with dst.open("wb") as f: f.write(content)

    # 1) проверка шапки
    actual_headers = extract_combined_headers(dst, sheet_name=0, n_header_rows=3)
    report = diff_headers(actual_headers, REFERENCE_HEADERS)
    if not report["ok"]:
        t = request.app.state.templates
        return t.TemplateResponse(
            "result.html",
            {
                "request": request,
                "ok": False,
                "message": f"Столбцов: факт {report['actual_len']}, эталон {report['expected_len']}",
                "report": report,
                "download_url": None,
                "job_id": job_id,             
                "orig_name": file.filename
            }
        )
    
    # 2) читаем данные с теми же именами колонок
    df = pd.read_excel(dst, sheet_name=0, header=[0,1,2])
    df.columns = actual_headers  # ВАЖНО: убрать MultiIndex

    # 3) удалить № (инвариант: после проверки она обязана быть)
    if "№" not in df.columns:
        raise HTTPException(status_code=500, detail="Инвариант нарушен: колонка '№' не найдена после проверки.")
    df = df.drop(columns=["№"])
    removed = "№"

    # контроль количества
    if len(df.columns) != len(TARGET_HEADERS):
        raise HTTPException(
            status_code=500,
            detail=f"После удаления столбцов: {len(df.columns)} != {len(TARGET_HEADERS)} (ожидалось)."
        )

    # присвоить итоговые имена
    df.columns = TARGET_HEADERS

    df.columns = [c.lower() for c in df.columns]  # теперь совпадает с COLUMN_TYPES (coordinates тоже станет lowercase)

    # привести типы по твоим правилам
    df = apply_column_types(df, COLUMN_TYPES)

    # имя коллекции оставляй как у исходника
    collection_name = Path(file.filename).stem
    geo = df_to_geojson(df, collection_name)

    # имя файла GeoJSON = как у исходного XLSX
    safe_stem = _safe_stem(file.filename)
    out_name = f"{safe_stem}.geojson"
    out_path = _unique_path(DATA_DIR, out_name)  # чтобы не перетирать, если имя совпало
    out_path.write_text(json.dumps(geo, ensure_ascii=False, indent=2), encoding="utf-8")

    # ссылка на скачивание (URL-энкодинг имени)
    download_url = "/download/" + urllib.parse.quote(out_path.name)

    t = request.app.state.templates
    return t.TemplateResponse(
        "result.html",
        {
            "request": request,
            "ok": True,
            "message": f"Шапка совпала. Удалено: №. Переименовано: {len(TARGET_HEADERS)}. GeoJSON готов.",
            "report": None,
            "headers": df.columns.tolist(),
            "download_url": download_url
        }
    )

@router.get("/download/{filename}")
def download(filename: str, background_tasks: BackgroundTasks):
    path = DATA_DIR / filename
    if not (path.exists() and path.suffix.lower() == ".geojson"):
        raise HTTPException(status_code=404, detail="Файл не найден")
    # опционально удалить после выдачи
    # background_tasks.add_task(path.unlink, missing_ok=True)
    return FileResponse(path, media_type="application/geo+json", filename=path.name)

@router.post("/force", response_class=HTMLResponse)
async def force_convert(request: Request, job_id: str = Form(...), orig_name: str = Form(...)):
    t = request.app.state.templates
    xlsx_path = DATA_DIR / f"{job_id}.xlsx"
    if not xlsx_path.exists():
        raise HTTPException(status_code=404, detail="Исходный файл не найден")

    # читаем шапку и данные, НО не сравниваем с эталоном
    actual_headers = extract_combined_headers(xlsx_path, sheet_name=0, n_header_rows=3)
    df = pd.read_excel(xlsx_path, sheet_name=0, header=[0,1,2])
    df.columns = actual_headers

    # удалить номерную колонку, если она есть
    if "№" in df.columns:
        df = df.drop(columns=["№"])

    # проверка количества перед переименованием
    if len(df.columns) != len(TARGET_HEADERS):
        return t.TemplateResponse(
            "result.html",
            {
                "request": request,
                "ok": False,
                "message": f"Форс-режим: количество столбцов {len(df.columns)} ≠ {len(TARGET_HEADERS)}. Нужна ручная правка.",
                "report": None,
                "download_url": None
            }
        )

    # переименовать по позиции, привести типы, собрать GeoJSON
    df.columns = TARGET_HEADERS
    df.columns = [c.lower() for c in df.columns]
    df = apply_column_types(df, COLUMN_TYPES)

    collection_name = Path(orig_name).stem
    geo = df_to_geojson(df, collection_name)

    safe_stem = _safe_stem(orig_name)
    out_name = f"{safe_stem}.geojson"
    out_path = _unique_path(DATA_DIR, out_name)
    out_path.write_text(json.dumps(geo, ensure_ascii=False, indent=2), encoding="utf-8")

    download_url = "/download/" + urllib.parse.quote(out_path.name)

    return t.TemplateResponse(
        "result.html",
        {
            "request": request,
            "ok": True,
            "message": f"Форс-режим: GeoJSON готов.",
            "report": None,
            "headers": df.columns.tolist(),
            "download_url": download_url
        }
    )
