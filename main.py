from playwright.sync_api import sync_playwright
import os
from datetime import datetime

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

cliente = {
    "ruc": "1723041156001",
    "subtotal": "230"
}

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # LOGIN
    page.goto(URL_LOGIN, wait_until="networkidle", timeout=60000)
    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(6000)

    # IR DIRECTO A FACTURA
    page.goto(URL_FACTURA, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(6000)

    # SELECCIONAR TIPO IDENTIFICACIÓN RUC
    page.locator("#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_focus").click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC CLIENTE
    page.locator("#form\\:busquedaCompradorComp\\:ruc").fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(5000)

    # PRODUCTO
    page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input").fill("ASESORIA")
    page.wait_for_timeout(5000)

    # SELECCIONAR PRODUCTO DEL AUTOCOMPLETE
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)

    # SI NO AGREGA, INTENTAR CON CLIC EN RESULTADO
    try:
        page.locator("li").filter(has_text="ASESORIA").first.click(timeout=5000)
        page.wait_for_timeout(4000)
    except:
        pass

    print("=== RESULTADO DESPUÉS DE INTENTAR AGREGAR PRODUCTO ===")
    texto = page.locator("body").inner_text()
    print(texto)

    if "No existen productos" in texto:
        raise Exception("EL PRODUCTO NO SE AGREGÓ. HAY QUE VER LA LISTA REAL DEL AUTOCOMPLETE.")

    print("PRODUCTO AGREGADO CORRECTAMENTE")

    browser.close()
