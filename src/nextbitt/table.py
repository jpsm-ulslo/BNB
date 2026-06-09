import time
import logging
import re
import csv
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)

EXPECTED_HEADERS = [
    "Código","Descrição","Cód. Ativo Principal","Ativo Principal",
    "Cód. Localização","Localização","Cód. Setor","Setor",
    "Cód. Centro Custo","C. Custo","Família","Sub-Família",
    "Marca","Modelo","Série","Cód. Grau de Criticidade",
    "Grau de Criticidade","Etiqueta NFC/RFID","Classe",
    "Nível de Segurança","Estado","Relevante para o SGA",
    "Modificado Em","Inativo","Anulado","Data de Anulação"
]

# --------------------------------------------------
def _grid(driver):
    return driver.find_element(By.CSS_SELECTOR, ".rgDataDiv")

# --------------------------------------------------
def extract_table(driver, wait, output_prefix="ativos", filters=None):

    log.info("📥 Starting table extraction")

    data = []
    visited_pages = set()
    watchdog_counter = 0

    while True:

        current = _get_current_page(driver)
        total = _get_total_pages(driver)

        log.info(f"➡️ Page {current} / {total}")

        # ✅ WATCHDOG PAGINAÇÃO
        if current in visited_pages:
            watchdog_counter += 1
            if watchdog_counter > 2:
                raise RuntimeError("Pagination watchdog triggered (loop detected)")
        else:
            visited_pages.add(current)

        _wait_for_rows(driver)
        _reset_horizontal_scroll(driver)

        page_data = {}
        seen_headers = set()
        last_scroll = -1

        for _ in range(20):

            current_scroll = driver.execute_script(
                "return arguments[0].scrollLeft", _grid(driver)
            )

            visible_headers = _get_visible_headers(driver)

            ordered_headers = sorted(
                visible_headers.items(),
                key=lambda x: x[1]["center_x"]
            )

            header_names = [h for h, _ in ordered_headers]
            seen_headers.update(header_names)

            _reset_vertical_scroll(driver)

            view_data = _extract_rows_view(driver, ordered_headers)

            # ✅ MERGE ANTI-CORRUPÇÃO
            for k, v in view_data.items():

                if k not in page_data:
                    page_data[k] = {}

                for col, val in v.items():
                    if col not in page_data[k] or not page_data[k][col]:
                        page_data[k][col] = val

            # ✅ parar se já temos todos os headers
            if set(EXPECTED_HEADERS).issubset(seen_headers):
                break

            driver.execute_script(
                "arguments[0].scrollLeft += arguments[0].clientWidth",
                _grid(driver)
            )

            time.sleep(0.5)

            new_scroll = driver.execute_script(
                "return arguments[0].scrollLeft", _grid(driver)
            )

            if new_scroll == current_scroll or current_scroll == last_scroll:
                break

            last_scroll = current_scroll

        data.extend(page_data.values())

        # ✅ CHECKPOINT por página
        _checkpoint(page_data, current, output_prefix, filters)

        if current >= total:
            break

        _go_next(driver)

    data = _deduplicate(data)

    data = _validate_dataset(data)

    log.info(f"✅ Total rows: {len(data)}")

    _export_csv(data, output_prefix, filters)
    _export_excel(data, output_prefix, filters)

    return data


# --------------------------------------------------
def _extract_rows_view(driver, headers):

    data = {}
    seen_keys = set()
    last_count = -1

    _reset_vertical_scroll(driver)

    for _ in range(120):

        grid = _grid(driver)

        rows = grid.find_elements(
            By.XPATH,
            ".//tr[contains(@class,'rgRow') or contains(@class,'rgAltRow')]"
        )

        for r in rows:
            try:
                cells = r.find_elements(By.XPATH, ".//td")

                if len(cells) < 3:
                    continue

                values = [c.text.strip() for c in cells]

                # ✅ DETECTAR Código (apenas para identificar linha)
                key = None
                for val in values:
                    if re.match(r"[A-Z]{3,}[A-Z0-9]*\d{4,}", val):
                        key = val
                        break

                if not key:
                    continue

                if key not in data:
                    data[key] = {}

                # ✅ OFFSET FIXO (checkbox)
                start_idx = 1 if len(values) == len(headers) + 1 else 0

                # ✅ MAPEAMENTO DIRETO E ESTÁVEL
                for i, (header, _) in enumerate(headers):

                    idx = i + start_idx

                    if idx < len(values):
                        val = values[idx]
                    else:
                        val = ""

                    # ✅ merge seguro
                    if header not in data[key] or not data[key][header]:
                        data[key][header] = val

                seen_keys.add(key)

            except Exception:
                continue

        # ✅ SCROLL PEQUENO (CRÍTICO — NÃO alterar!)
        driver.execute_script(
            "arguments[0].scrollTop += 120",
            grid
        )

        time.sleep(0.3)

        # ✅ PARAGEM CORRETA
        if len(seen_keys) == last_count:
            break

        last_count = len(seen_keys)

    return data


# --------------------------------------------------
def _validate_dataset(data):

    log.info("🔎 Running data integrity checks")

    valid = []

    for row in data:

        key = row.get("Código")

        # ✅ descartar linhas incompletas
        if not key or len(key) < 5:
            continue

        # ✅ proteger contra corrupção
        corrupted = False
        for k, v in row.items():
            if k != "Código" and v == key:
                log.warning(f"⚠️ Código duplicated in {k}")
                corrupted = True

        if not corrupted:
            valid.append(row)

    log.info(f"✅ Valid rows after integrity check: {len(valid)}")

    return valid


# --------------------------------------------------
def _checkpoint(page_data, page, prefix, filters):

    log.info(f"💾 Checkpoint page {page} ({len(page_data)} rows)")

    path = _build_output_path(prefix + f"_page{page}", filters, "csv")

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()

        for r in page_data.values():
            writer.writerow({k: r.get(k, "") for k in EXPECTED_HEADERS})


# --------------------------------------------------
def _reset_horizontal_scroll(driver):
    driver.execute_script("arguments[0].scrollLeft = 0", _grid(driver))
    time.sleep(0.5)


def _reset_vertical_scroll(driver):
    driver.execute_script("arguments[0].scrollTop = 0", _grid(driver))
    time.sleep(0.5)


# --------------------------------------------------
def _get_visible_headers(driver):

    headers = driver.find_elements(By.XPATH, "//table//th")
    visible = {}

    for h in headers:
        try:
            text = h.text.strip().replace("\n", "")

            for expected in EXPECTED_HEADERS:
                if text == expected or text.startswith(expected):
                    visible[expected] = {
                        "center_x": h.location["x"] + h.size["width"]/2
                    }
        except:
            continue

    return visible


# --------------------------------------------------
def _wait_for_rows(driver, timeout=10):

    start = time.time()

    while time.time() - start < timeout:
        rows = driver.find_elements(
            By.XPATH,
            "//tr[contains(@class,'rgRow') or contains(@class,'rgAltRow')]"
        )
        if rows:
            return
        time.sleep(0.4)


# --------------------------------------------------
def _go_next(driver):
    driver.find_element(By.XPATH, "//a[contains(@class,'rslIncrease')]").click()
    time.sleep(2)


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
def _deduplicate(data):

    seen = set()
    result = []

    for r in data:
        key = r.get("Código")

        if key in seen:
            continue

        seen.add(key)
        result.append(r)

    return result


# --------------------------------------------------
def _build_output_path(prefix, filters, ext):

    base = Path("data")
    base.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d_%H%M")

    filter_str = ""
    if filters:
        filter_str = "_".join(f["value"] for f in filters if f.get("value"))

    filename = f"{prefix}_{date_str}"

    if filter_str:
        filename += f"_{filter_str}"

    filename += f".{ext}"

    return base / filename


def _export_csv(data, prefix, filters):

    path = _build_output_path(prefix, filters, "csv")

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()

        for r in data:
            writer.writerow({k: r.get(k, "") for k in EXPECTED_HEADERS})


def _export_excel(data, prefix, filters):

    import pandas as pd

    path = _build_output_path(prefix, filters, "xlsx")

    df = pd.DataFrame(data)
    df = df.reindex(columns=EXPECTED_HEADERS)

    df.to_excel(path, index=False)