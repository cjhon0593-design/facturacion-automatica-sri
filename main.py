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

    page.goto("https://facturadorsri.sri.gob.ec/", timeout=60000)

    # LOGIN
    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(5000)

    # IR A FACTURA
    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Factura").click()
    page.wait_for_timeout(6000)

    inputs = page.locator("input:visible")

    # TIPO IDENTIFICACIÓN
    inputs.nth(6).click()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC CLIENTE
    inputs.nth(5).fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(4000)

    # === BUSCAR PRODUCTO ===
    buscador = inputs.nth(11)
    buscador.fill("ASESORIA")
    page.wait_for_timeout(4000)

    # SELECCIONAR PRODUCTO
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(4000)

    # === LLENAR CANTIDAD ===
    page.keyboard.press("Tab")  # cantidad
    page.keyboard.type("1")
    page.wait_for_timeout(1000)

    # === LLENAR PRECIO ===
    page.keyboard.press("Tab")
    page.keyboard.type(cliente["precio"])
    page.wait_for_timeout(3000)

    # VALIDACIÓN CLAVE
    texto = page.locator("body").inner_text()

    print("=== VALIDACIÓN FINAL ===")
    print(texto)

    if "No existen productos" in texto or "0.00" in texto:
        raise Exception("❌ ERROR: Producto NO agregado correctamente")

    print("✅ PRODUCTO AGREGADO CORRECTAMENTE")

    browser.close()
