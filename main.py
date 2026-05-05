from playwright.sync_api import sync_playwright
import os

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL_LOGIN, wait_until="networkidle", timeout=60000)

    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(6000)

    page.goto(URL_FACTURA, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(6000)

    # Tipo identificación RUC
    page.locator("#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_focus").click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC cliente
    page.locator("#form\\:busquedaCompradorComp\\:ruc").fill("1723041156001")
    page.keyboard.press("Tab")
    page.wait_for_timeout(4000)

    # Producto
    producto = page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input")
    producto.click(force=True)
    producto.fill("A")
    page.wait_for_timeout(5000)

    # Seleccionar opción real del desplegable
    opciones = page.locator("li.ui-autocomplete-item:visible")
    opciones.filter(has_text="ASESORIA").first.click(force=True)
    page.wait_for_timeout(5000)

    # Validar si el producto se agregó
    texto = page.locator("body").inner_text()

    print("RESULTADO DESPUÉS DE SELECCIONAR PRODUCTO:")
    print(texto)

    if "No existen productos" in texto:
        raise Exception("Todavía no se agregó el producto. El SRI no está mostrando el autocomplete en GitHub.")

    print("PRODUCTO AGREGADO CORRECTAMENTE")

    browser.close()
