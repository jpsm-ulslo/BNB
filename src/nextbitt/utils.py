# --------------------------------------------------
# utils (human interaction + robustness)
# --------------------------------------------------

import time
import random
import logging

from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)


# --------------------------------------------------
# HUMAN TYPE (SAFE)
# --------------------------------------------------
def human_type(element, text, min_delay=0.05, max_delay=0.12):
    """
    Escreve texto simulando digitação humana.
    NÃO faz click nem clear (isso deve ser feito fora)
    """

    for char in str(text):
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))

    # pequena pausa final
    time.sleep(random.uniform(0.2, 0.4))


# --------------------------------------------------
# CLEAR INPUT (ROBUST - Telerik safe)
# --------------------------------------------------
def clear_input(element):
    """
    Limpeza robusta de input (melhor que .clear())
    """
    element.send_keys("\u0001")  # CTRL + A
    element.send_keys("\u0008")  # BACKSPACE


# --------------------------------------------------
# SAFE FIND VISIBLE INPUTS
# --------------------------------------------------
def get_visible_inputs(driver):
    """
    Obtém inputs visíveis do grid (evita elementos ocultos)
    """
    inputs = driver.find_elements(By.XPATH, "//table//tr[2]//input")

    return [i for i in inputs if i.is_displayed()]


# --------------------------------------------------
# SAFE CLICK (ANTI-STALE)
# --------------------------------------------------
def safe_click(driver, element_getter, retries=3):
    """
    Click resiliente contra stale element

    element_getter = função que retorna o elemento (lambda)
    """

    for attempt in range(retries):
        try:
            element = element_getter()

            if element.is_displayed():
                element.click()
                return

        except Exception:
            time.sleep(0.5)

    raise Exception("❌ Failed to click element after retries")


# --------------------------------------------------
# WAIT SMALL HUMAN DELAY
# --------------------------------------------------
def human_pause(min_delay=0.2, max_delay=0.6):
    """
    Pequena pausa aleatória (simula comportamento humano)
    """
    time.sleep(random.uniform(min_delay, max_delay))


# --------------------------------------------------
# SAFE TYPE HIGH-LEVEL (RECOMENDADO PARA USO)
# --------------------------------------------------
def safe_type(driver, input_locator_fn, text):
    """
    Método completo e robusto para escrever num campo:

    - Re-localiza elemento (anti-stale)
    - Click seguro
    - Limpeza robusta
    - Escrita humana
    """

    try:
        element = input_locator_fn()

        element.click()

        clear_input(element)

        human_type(element, text)

    except Exception as e:
        log.warning(f"⚠️ safe_type failed, retrying: {e}")

        time.sleep(1)

        # retry (re-find)
        element = input_locator_fn()

        element.click()
        clear_input(element)
        human_type(element, text)


# --------------------------------------------------
# DEBUG HELP (opcional)
# --------------------------------------------------
def debug_element_position(element, label="element"):
    """
    Para debugging visual (posição no ecrã)
    """
    log.info(
        f"{label} → x:{element.location['x']} y:{element.location['y']} "
        f"w:{element.size['width']} h:{element.size['height']}"
    )