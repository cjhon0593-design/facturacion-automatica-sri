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

    # =========================
    # LLENADO CORRECTO
    # =========================

    # RUC cliente (INPUT 5)
    page.locator("input:visible").nth(5).fill(cliente["ruc"])
    page.wait_for_timeout(3000)

    # Tipo identificación → RUC
    page.locator("input:visible").nth(6).click()
    page.get_by_text("RUC").click()
    page.wait_for_timeout(2000)

    # Buscar producto
    page.locator("input:visible").nth(11).fill("A")
    page.wait_for_timeout(3000)

    page.get_by_text("ASESORIA CONTABILIDAD").click()
    page.wait_for_timeout(2000)

    # Precio unitario
    page.locator("input:visible").last.fill(str(cliente["subtotal"]))
    page.wait_for_timeout(2000)

    print("FACTURA LLENADA CORRECTAMENTE")

    browser.close()
