# --------------------------------------------------
# nextbitt client (FINAL - orchestrator)
# --------------------------------------------------

from pathlib import Path
import yaml
import logging

import time


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.nextbitt.login import NextbittLogin
from src.nextbitt.filters import apply_filters
from src.nextbitt.table import extract_table

log = logging.getLogger(__name__)


class NextbittClient:

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(self, config_path="config/filters.yaml", timeout=20):

        self.config = self._load_config(config_path)
        self.timeout = timeout

        self.driver = None
        self.wait = None

    # --------------------------------------------------
    def _load_config(self, path):

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"❌ Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # --------------------------------------------------
    # BROWSER
    # --------------------------------------------------
    def _start(self):

        log.info("🚀 Starting browser")

        options = Options()
        options.add_argument("--start-maximized")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        self.wait = WebDriverWait(self.driver, self.timeout)

    # --------------------------------------------------
    def _stop(self):

        if self.driver:
            log.info("🛑 Closing browser")
            self.driver.quit()

    # --------------------------------------------------
    # RUN PIPELINE
    # --------------------------------------------------
    def run(self, output_csv="data/ativos.csv"):

        try:
            self._start()

            # --------------------------------------------------
            # LOGIN
            # --------------------------------------------------
            login = NextbittLogin(self.driver, self.wait, self.config)
            login.perform_login()

            # --------------------------------------------------
            # NAVIGATION
            # --------------------------------------------------
            assets_url = self.config["nextbitt"]["assets_url"]

            log.info(f"➡️ Navigating to Assets: {assets_url}")

            self.driver.get(assets_url)

            # garantir carregamento base
            self.wait.until(
                lambda d: len(d.find_elements("xpath", "//table")) > 0
            )

            self._prepare_view()

            # --------------------------------------------------
            # APPLY FILTERS
            # --------------------------------------------------
            apply_filters(self.driver, self.wait, self.config)

            # --------------------------------------------------
            # ✅ CRÍTICO: esperar a paginação (garante filtros aplicados)
            # --------------------------------------------------
            self._wait_pagination_ready()

            # --------------------------------------------------
            # EXTRACT TABLE
            # --------------------------------------------------
            
            data = extract_table(
                driver=self.driver,
                wait=self.wait,
                output_prefix="ativos",
                filters=self.config.get("filters", [])
            )


            log.info(f"✅ Total rows: {len(data)}")

            return data

        finally:
            self._stop()

    # --------------------------------------------------
    # ✅ PAGINATION READY GUARD (CRÍTICO)
    # --------------------------------------------------
    def _wait_pagination_ready(self):

        import time
        import re

        log.info("⏳ Waiting for pagination readiness")

        for _ in range(20):

            time.sleep(1)

            elems = self.driver.find_elements("xpath", "//div[contains(text(),'Página')]")

            for el in elems:

                txt = el.text.strip()

                if "Página" in txt and "de" in txt:

                    m = re.search(r"Página\s+(\d+)\s+de\s+(\d+)", txt)

                    if m:
                        current = int(m.group(1))
                        total = int(m.group(2))

                        # ✅ condição real do teu caso
                        if total >= 2:
                            log.info(f"✔ Pagination ready: {current}/{total}")
                            return

        log.warning("⚠️ Pagination readiness not confirmed")



    def _prepare_view(self):

        log.info("🔎 Adjusting viewport (zoom out)")

        driver = self.driver

        # ✅ zoom out robusto
        driver.execute_script("document.body.style.zoom='0.5'")
        time.sleep(1)
