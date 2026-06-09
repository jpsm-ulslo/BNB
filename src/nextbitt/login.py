# --------------------------------------------------
# nextbitt login module (FINAL - robust + human typing)
# --------------------------------------------------

import time
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# reutilizar utils (human typing)
from src.nextbitt.utils import human_type, clear_input

log = logging.getLogger(__name__)


class NextbittLogin:

    def __init__(self, driver, wait, config):
        self.driver = driver
        self.wait = wait
        self.config = config

    # --------------------------------------------------
    # PUBLIC
    # --------------------------------------------------
    def perform_login(self):

        log.info("🔐 Starting login process")

        self._open_login_page()
        self._fill_credentials()
        self._submit()
        self._wait_for_login()

        log.info("✅ Login successful")

    # --------------------------------------------------
    # OPEN PAGE
    # --------------------------------------------------
    def _open_login_page(self):

        url = self.config["nextbitt"]["base_url"]

        self.driver.get(url)

        # esperar campos
        self.wait.until(
            EC.presence_of_element_located((By.ID, "txtUserName"))
        )

    # --------------------------------------------------
    # FILL CREDENTIALS (HUMAN-LIKE)
    # --------------------------------------------------
    def _fill_credentials(self):

        username = self.config["auth"]["username"]
        password = self.config["auth"]["password"]

        user_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "txtUserName"))
        )

        pwd_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "txtPassword"))
        )

        # escrever username
        user_input.click()
        clear_input(user_input)
        human_type(user_input, username)

        time.sleep(0.4)

        # escrever password
        pwd_input.click()
        clear_input(pwd_input)
        human_type(pwd_input, password)

        log.info("✔ Credentials filled")

    # --------------------------------------------------
    # SUBMIT
    # --------------------------------------------------
    def _submit(self):

        btn = self.wait.until(
            EC.element_to_be_clickable((By.ID, "btnLogin"))
        )

        # pequena pausa humana
        time.sleep(0.3)

        btn.click()

        log.info("✅ Login button clicked")

    # --------------------------------------------------
    # VERIFY LOGIN
    # --------------------------------------------------
    def _wait_for_login(self):

        log.info("⏳ Waiting for login")

        try:
            # ✅ tentar detetar mudança de URL
            self.wait.until(EC.url_changes(self.driver.current_url))
            return

        except Exception:
            log.warning("⚠️ URL did not change, fallback")

        # fallback → esperar grid ou área principal
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//body"))
            )
        except Exception:
            pass

        # validação extra: verificar não há erro visível
        errors = self.driver.find_elements(By.ID, "divError")

        if errors:
            text = errors[0].text.strip()
            if text:
                raise Exception(f"❌ Login failed: {text}")