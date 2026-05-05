from playwright.sync_api import sync_playwright
import os

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

cliente = {
    "ruc": "1723041156001",
    "subtotal": 230
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # LOGIN
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.locator('input[type="text"]').first.fill(RUC)
    page.locator('input[type="password"]').fill(CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(5000)

    # IR A FACTURA
    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Factura", exact=True).click()
    page.wait_for_timeout(6000)

    inputs = page.locator("input:visible")

    # Tipo identificación → RUC (por teclado)
    inputs.nth(6).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC cliente
    inputs.nth(5).fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(3000)

    # BUSCAR PRODUCTO (SOLUCIÓN ESTABLE)
    inputs.nth(11).fill("A")
    page.wait_for_timeout(5000)

    print("Texto después de buscar producto:")
    print(page.locator("body").inner_text())

    # Seleccionar primer resultado con teclado
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)

    print("FACTURA LLENADA HASTA PRODUCTO")

    browser.close()
