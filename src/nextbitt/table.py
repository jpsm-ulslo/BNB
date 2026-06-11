import time
import logging
import re
import csv
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)

EXPECTED_HEADERS = [
    "Código", "Descrição", "Cód. Ativo Principal", "Ativo Principal",
    "Cód. Localização", "Localização", "Classe",
    "Família", "Sub-Família", "Marca", "Modelo",
    "Cód. Centro Custo", "C. Custo", "Série", "Etiqueta NFC/RFID",
    "Cód. Grau de Criticidade", "Grau de Criticidade"
]

# --------------------------------------------------
def _grid(driver):
    return driver.find_element(By.CSS_SELECTOR, ".rgDataDiv")

# --------------------------------------------------
def _safe_find_rows(driver):
    try:
        return driver.find_elements(
            By.XPATH,
            "//tr[contains(@class,'rgRow') or contains(@class,'rgAltRow')]"
        )
    except:
        return []

# --------------------------------------------------
def _extract_codigo(row):

    try:
        span = row.find_element(By.XPATH, ".//span[contains(@style,'display: none')]")
        txt = span.text.strip()
        if txt:
            return txt
    except:
        pass

    try:
        a = row.find_element(By.XPATH, ".//a[contains(@href,'/Assets/Disp.aspx')]")
        txt = a.text.strip()
        if txt:
            return txt
    except:
        pass

    return None

# --------------------------------------------------
def _safe_cell(cells, idx):
    try:
        return cells[idx].text.strip()
    except:
        return ""

# --------------------------------------------------
def _parse_row(row):

    try:
        cells = row.find_elements(By.XPATH, "./td")
        key = _extract_codigo(row)

        if not key:
            return None

        return {
            "Código": key,
            "Descrição": _safe_cell(cells, 2),
            "Cód. Ativo Principal": _safe_cell(cells, 3),
            "Ativo Principal": _safe_cell(cells, 4),
            "Cód. Localização": _safe_cell(cells, 7),
            "Localização": _safe_cell(cells, 8),
            "Classe": _safe_cell(cells, 9),
            "Família": _safe_cell(cells, 10),
            "Sub-Família": _safe_cell(cells, 11),
            "Marca": _safe_cell(cells, 12),
            "Modelo": _safe_cell(cells, 13),
            "Cód. Centro Custo": _safe_cell(cells, 14),
            "C. Custo": _safe_cell(cells, 15),
            "Série": _safe_cell(cells, 16),
            "Etiqueta NFC/RFID": _safe_cell(cells, 17),
            "Cód. Grau de Criticidade": _safe_cell(cells, 18),
            "Grau de Criticidade": _safe_cell(cells, 19),
        }

    except:
        # ✅ elemento ficou stale → ignorar
        return None

# --------------------------------------------------
def _extract_rows(driver):

    data = {}

    for pass_id in range(4):

        log.info(f"🔁 Scan pass {pass_id+1}")

        try:
            grid = _grid(driver)
            driver.execute_script("arguments[0].scrollTop = 0", grid)
        except:
            pass

        time.sleep(0.6)

        pass_start_total = len(data)
        last_seen = len(data)
        stable_steps = 0

        for step in range(200):

            rows = _safe_find_rows(driver)

            for r in rows:

                parsed = _parse_row(r)

                if not parsed:
                    continue

                key = parsed["Código"]

                if key not in data:
                    data[key] = parsed
                else:
                    # ✅ merge conservador
                    for k, v in parsed.items():
                        if data[key].get(k, "") == "":
                            data[key][k] = v

            current_total = len(data)

            if current_total == last_seen:
                stable_steps += 1
            else:
                stable_steps = 0

            last_seen = current_total

            if stable_steps >= 6:
                break

            # ✅ scroll seguro
            try:
                grid = _grid(driver)
                driver.execute_script(
                    "arguments[0].scrollTop += 220",
                    grid
                )
            except:
                pass

            time.sleep(0.2)

        log.info(f"📊 After pass {pass_id+1}: {len(data)}")

        # ✅ FAST EXIT
        if pass_id == 0 and len(data) >= 49:
            log.info("⚡ Full page captured in first pass")
            break

        # ✅ parar quando estabiliza
        if len(data) == pass_start_total:
            log.info("✅ Dataset stabilized across passes")
            break

    return data

# --------------------------------------------------
def extract_table(driver, wait, output_prefix="ativos", filters=None):

    log.info("📥 Starting extraction (FINAL ROBUST VERSION)")

    global_data = {}
    visited_pages = set()

    while True:

        current = _get_current_page(driver)
        total = _get_total_pages(driver)

        log.info(f"➡️ Page {current}/{total}")

        if current in visited_pages:
            break

        visited_pages.add(current)

        page_data = _extract_rows(driver)

        log.info(f"✅ Page {current} rows: {len(page_data)}")

        for key, row in page_data.items():

            if key not in global_data:
                global_data[key] = row
            else:
                for k, v in row.items():
                    if global_data[key].get(k, "") == "":
                        global_data[key][k] = v

        if current >= total:
            break

        _go_next(driver)
        time.sleep(1.3)

    final_data = list(global_data.values())

    log.info(f"✅ Final dataset: {len(final_data)}")

    if len(final_data) < 290:
        log.warning("⚠️ Dataset may be incomplete")

    _export_csv(final_data, output_prefix)
    _export_excel(final_data, output_prefix)

    return final_data

# --------------------------------------------------
def _go_next(driver):
    driver.find_element(
        By.XPATH,
        "//a[contains(@class,'rslIncrease')]"
    ).click()

# --------------------------------------------------
def _get_current_page(driver):
    for el in driver.find_elements(By.XPATH, "//*[contains(text(),'Página')]"):
        m = re.search(r"Página\s+(\d+)", el.text)
        if m:
            return int(m.group(1))
    return 1

def _get_total_pages(driver):
    for el in driver.find_elements(By.XPATH, "//*[contains(text(),'Página')]"):
        m = re.search(r"de\s+(\d+)", el.text)
        if m:
            return int(m.group(1))
    return 1

# --------------------------------------------------
def _build_output_path(prefix, ext):
    base = Path("data")
    base.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    return base / f"{prefix}_{date_str}.{ext}"

# --------------------------------------------------
def _export_csv(data, prefix):
    path = _build_output_path(prefix, "csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()
        for r in data:
            writer.writerow(r)

# --------------------------------------------------
def _export_excel(data, prefix):

    import pandas as pd

    path = _build_output_path(prefix, "xlsx")

    df = pd.DataFrame(data)
    df = df.reindex(columns=EXPECTED_HEADERS)

    df.to_excel(path, index=False)