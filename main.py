from playwright.sync_api import sync_playwright
import os

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL, wait_until="networkidle", timeout=60000)

    page.wait_for_selector('input[type="text"]', timeout=60000)
    page.locator('input[type="text"]').first.fill(RUC)

    page.wait_for_selector('input[type="password"]', timeout=60000)
    page.locator('input[type="password"]').fill(CLAVE)

    page.get_by_role("button", name="Ingresar").click()

    page.wait_for_timeout(8000)

    print("URL después del login:", page.url)
    print("Título después del login:", page.title())

    page.screenshot(path="despues_login.png", full_page=True)

    browser.close()
