from playwright.sync_api import sync_playwright
import os

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 1. Login
    page.goto(URL, wait_until="networkidle", timeout=60000)

    page.locator('input[type="text"]').first.fill(RUC)
    page.locator('input[type="password"]').fill(CLAVE)
    page.get_by_role("button", name="Ingresar").click()

    page.wait_for_timeout(5000)

    # 2. Ir a "Emisión"
    page.get_by_text("Emisión").click()

    page.wait_for_timeout(3000)

    # 3. Ir a "Factura"
    page.get_by_text("Factura").click()

    page.wait_for_timeout(8000)

    print("URL actual:", page.url)
    print("Título actual:", page.title())

    page.screenshot(path="pantalla_factura.png", full_page=True)

    browser.close()
