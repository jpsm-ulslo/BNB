import time
import logging
from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)


# ✅ MESMA LISTA DO table.py (CRÍTICO)
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
def apply_filters(driver, wait, config):

    log.info("🔍 Applying filters")

    for f in config.get("filters", []):
        field = f.get("field")
        value = f.get("value")

        log.info(f"➡️ {field} = {value}")

        _write_and_commit(driver, field, value)

    log.info("✅ Filters filled and committed")

    time.sleep(2)


# --------------------------------------------------
def _reset_scroll(driver):

    driver.execute_script("""
        var el = document.querySelector('.rgDataDiv');
        if (el) el.scrollLeft = 0;
    """)
    time.sleep(0.3)


def _scroll_table(driver):

    driver.execute_script("""
        var el = document.querySelector('.rgDataDiv');
        if (el) el.scrollLeft += 300;
    """)
    time.sleep(0.4)


# --------------------------------------------------
def _get_visible_headers(driver):

    headers = driver.find_elements(By.XPATH, "//table//th")

    visible = {}

    for h in headers:
        try:
            text = h.text.strip().replace("\n", "")
            if not text:
                continue

            for expected in EXPECTED_HEADERS:
                if text == expected or text.startswith(expected):

                    visible[expected] = {
                        "center_x": h.location["x"] + h.size["width"] / 2
                    }
                    break

        except:
            continue

    return visible


# --------------------------------------------------
def _find_input(driver, field_name):

    visible_headers = _get_visible_headers(driver)

    if field_name not in visible_headers:
        return None

    hx = visible_headers[field_name]["center_x"]

    cells = driver.find_elements(By.XPATH, "//table//tr[2]/td")

    best = None
    best_dist = float("inf")

    for cell in cells:
        try:
            cx = cell.location["x"] + cell.size["width"] / 2
            dist = abs(cx - hx)

            if dist < best_dist:

                inp = cell.find_element(By.XPATH, ".//input")

                if inp.is_displayed():
                    best = inp
                    best_dist = dist

        except:
            continue

    return best


# --------------------------------------------------
def _safe_focus(driver, element):

    driver.execute_script("""
        arguments[0].scrollIntoView({
            block: 'center',
            inline: 'center'
        });
    """, element)

    time.sleep(0.3)

    for _ in range(5):
        try:
            element.click()
            driver.execute_script("arguments[0].focus();", element)
            return
        except:
            time.sleep(0.3)

    log.warning("⚠️ Fallback JS focus")
    driver.execute_script("arguments[0].focus();", element)


# --------------------------------------------------
def _write_and_commit(driver, field_name, value):

    _reset_scroll(driver)

    target = _find_input(driver, field_name)

    attempts = 0

    # ✅ procurar com scroll horizontal
    while not target and attempts < 10:

        log.info(f"↔️ Scrolling to find '{field_name}'")

        _scroll_table(driver)

        target = _find_input(driver, field_name)

        attempts += 1

    if not target:
        raise Exception(f"❌ Field not found: {field_name}")

    _safe_focus(driver, target)

    time.sleep(0.3)

    # ✅ limpar corretamente (SEM clear)
    driver.execute_script("""
        arguments[0].value = '';
        arguments[0].dispatchEvent(new Event('input'));
    """, target)

    time.sleep(0.2)

    # ✅ escrever valor completo
    target.send_keys(str(value))

    time.sleep(0.5)

    log.info(f"✏️ Written '{value}' to '{field_name}'")

    # ✅ COMMIT REAL (Telerik)
    inputs = driver.find_elements(By.XPATH, "//table//tr[2]//input")

    for inp in inputs:
        try:
            if inp != target and inp.is_displayed():
                inp.click()
                break
        except:
            continue

    time.sleep(2.5)
