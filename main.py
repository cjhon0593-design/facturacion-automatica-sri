from playwright.sync_api import sync_playwright
import os

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL, wait_until="networkidle", timeout=60000)

    page.locator('input[type="text"]').first.fill(RUC)
    page.locator('input[type="password"]').fill(CLAVE)
    page.get_by_role("button", name="Ingresar").click()

    page.wait_for_timeout(5000)

    # Clic exacto en el menú Emisión
    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)

    # Clic exacto en Factura
    page.get_by_text("Factura", exact=True).click()
    page.wait_for_timeout(8000)

    print("URL actual:", page.url)
    print("Título actual:", page.title())
    print("Texto visible:")
    print(page.locator("body").inner_text())

    browser.close()
