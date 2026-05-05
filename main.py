from playwright.sync_api import sync_playwright
import os
from datetime import datetime

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

cliente = {
    "ruc": "1723041156001",
    "subtotal": 230
}

mes_actual = datetime.now().strftime("%B %Y").upper()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.locator('input[type="text"]').first.fill(RUC)
    page.locator('input[type="password"]').fill(CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(5000)

    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Factura", exact=True).click()
    page.wait_for_timeout(6000)

    inputs = page.locator("input:visible")

    inputs.nth(6).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    inputs.nth(5).fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(3000)

    inputs.nth(11).fill("A")
    page.wait_for_timeout(5000)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)

    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.keyboard.type(str(cliente["subtotal"]))
    page.wait_for_timeout(2000)

    page.get_by_text("Añadir forma de pago").click(force=True)
    page.wait_for_timeout(3000)

    print("=== TEXTO DESPUÉS DE AÑADIR FORMA DE PAGO ===")
    print(page.locator("body").inner_text())

    print("=== INPUTS VISIBLES DESPUÉS DE FORMA DE PAGO ===")
    inputs = page.locator("input:visible")
    for i in range(inputs.count()):
        item = inputs.nth(i)
        print(
            i,
            "type=", item.get_attribute("type"),
            "name=", item.get_attribute("name"),
            "id=", item.get_attribute("id"),
            "placeholder=", item.get_attribute("placeholder"),
            "value=", item.input_value() if item.get_attribute("type") != "file" else ""
        )

    print("PROCESO LLEGÓ HASTA FORMA DE PAGO")

    browser.close()
