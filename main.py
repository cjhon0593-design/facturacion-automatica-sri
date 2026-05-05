from playwright.sync_api import sync_playwright
import os

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

cliente = {
    "ruc": "1723041156001",
    "precio": "230"
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html", timeout=60000)

    # LOGIN
    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(5000)

    # IR A FACTURA
    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Factura", exact=True).first.click()
    page.wait_for_timeout(6000)

    inputs = page.locator("input:visible")

    # TIPO IDENTIFICACIÓN
    inputs.nth(6).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC CLIENTE
    inputs.nth(5).fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(4000)

    # BUSCAR PRODUCTO
    inputs.nth(11).fill("ASESORIA")
    page.wait_for_timeout(5000)

    # SELECCIONAR PRODUCTO
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    # LLENAR CANTIDAD Y PRECIO
    page.keyboard.press("Tab")
    page.keyboard.type("1")
    page.wait_for_timeout(1000)

    page.keyboard.press("Tab")
    page.keyboard.type(cliente["precio"])
    page.wait_for_timeout(4000)

    print("=== VALIDACIÓN FINAL ===")
    print(page.locator("body").inner_text())

    browser.close()
