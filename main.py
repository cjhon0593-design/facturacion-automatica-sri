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
total = round(cliente["subtotal"] * 1.15, 2)

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

    inputs = page.locator("input:visible")

    inputs.nth(13).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    inputs.nth(14).fill(str(total))
    page.wait_for_timeout(2000)

    page.get_by_text("Añadir campo adicional").click(force=True)
    page.wait_for_timeout(3000)

    inputs = page.locator("input:visible")
    inputs.nth(15).fill("DETALLE")
    inputs.nth(16).fill(f"SERVICIOS MES DE {mes_actual}")
    page.wait_for_timeout(2000)

    print("ANTES DE FIRMAR:")
    print(page.locator("body").inner_text())

    page.get_by_text("Firmar y enviar").click(force=True)
    page.wait_for_timeout(15000)

    print("DESPUÉS DE FIRMAR:")
    print(page.locator("body").inner_text())

    print("INPUTS DESPUÉS DE FIRMAR:")
    inputs = page.locator("input:visible")
    for i in range(inputs.count()):
        item = inputs.nth(i)
        print(i, item.get_attribute("type"), item.get_attribute("name"), item.get_attribute("id"), item.get_attribute("placeholder"), item.input_value() if item.get_attribute("type") != "file" else "")

    print("BOTONES DESPUÉS DE FIRMAR:")
    botones = page.locator("button:visible")
    for i in range(botones.count()):
        print(i, botones.nth(i).inner_text())

    browser.close()
