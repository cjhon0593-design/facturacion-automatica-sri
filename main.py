from playwright.sync_api import sync_playwright
import os
from datetime import datetime

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

cliente = {
    "ruc": "1723041156001",
    "subtotal": 230
}

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

hoy = datetime.now()
mes_actual = f"{MESES[hoy.month]} {hoy.year}"
total = round(cliente["subtotal"] * 1.15, 2)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # LOGIN
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)
    page.get_by_role("button", name="Ingresar").click()
    page.wait_for_timeout(5000)

    # IR A FACTURA
    page.get_by_role("button", name="Emisión").click()
    page.wait_for_timeout(2000)
    page.get_by_role("link", name="Factura", exact=True).click()
    page.wait_for_timeout(6000)

    inputs = page.locator("input:visible")

    # TIPO IDENTIFICACIÓN: RUC
    inputs.nth(6).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    # RUC CLIENTE
    inputs.nth(5).fill(cliente["ruc"])
    page.keyboard.press("Tab")
    page.wait_for_timeout(3000)

    # PRODUCTO
    inputs.nth(11).fill("A")
    page.wait_for_timeout(5000)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(2000)

    # PRECIO
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.keyboard.type(str(cliente["subtotal"]))
    page.wait_for_timeout(2000)

    # FORMA DE PAGO
    page.get_by_text("Añadir forma de pago").click(force=True)
    page.wait_for_timeout(3000)

    inputs = page.locator("input:visible")

    inputs.nth(13).click(force=True)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)

    inputs.nth(14).fill(str(total))
    page.wait_for_timeout(2000)

    # CAMPO ADICIONAL
    page.get_by_text("Añadir campo adicional").click(force=True)
    page.wait_for_timeout(3000)

    inputs = page.locator("input:visible")

    inputs.nth(15).fill("DETALLE")
    inputs.nth(16).fill(f"SERVICIOS MES DE {mes_actual}")
    page.wait_for_timeout(2000)

    # FIRMAR Y ENVIAR
    btn_firmar = page.get_by_text("Firmar y enviar")
    btn_firmar.scroll_into_view_if_needed()
    page.wait_for_timeout(2000)
    btn_firmar.click(force=True)

    # CLAVE DEL CERTIFICADO
    page.wait_for_selector("text=Clave del certificado", timeout=20000)
    page.locator("input[type='password']").fill(CERT_PASS)
    page.wait_for_timeout(1000)

    # ENVIAR FIRMA
    page.get_by_role("button", name="Enviar").click()

    # ESPERAR RESPUESTA DEL SRI
    page.wait_for_timeout(25000)

    print("RESULTADO FINAL:")
    print(page.locator("body").inner_text())

    browser.close()
