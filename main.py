from playwright.sync_api import sync_playwright
import os

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

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

    # MOSTRAR INPUTS VISIBLES PARA IDENTIFICAR EL CAMPO CORRECTO
    print("INPUTS VISIBLES:")
    inputs = page.locator("input:visible")
    count = inputs.count()

    for i in range(count):
        item = inputs.nth(i)
        print(
            i,
            "type=", item.get_attribute("type"),
            "name=", item.get_attribute("name"),
            "id=", item.get_attribute("id"),
            "placeholder=", item.get_attribute("placeholder"),
            "value=", item.input_value() if item.get_attribute("type") != "file" else ""
        )

    print("TOTAL INPUTS VISIBLES:", count)

    browser.close()
