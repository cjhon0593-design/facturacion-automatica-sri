from playwright.sync_api import sync_playwright
import os
from datetime import datetime

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")

URL = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

# DATOS CLIENTE (PRUEBA 1)
cliente = {
    "ruc": "1723041156001",
    "nombre": "PARDO AGURTO GLORIA ALEXANDRA",
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
    # LLENADO DE FACTURA
    # =========================

    # RUC cliente
    page.locator("input").nth(2).fill(cliente["ruc"])

    page.wait_for_timeout(2000)

    # Seleccionar tipo RUC
    page.get_by_text("Seleccione").first.click()
    page.get_by_text("RUC").click()

    page.wait_for_timeout(2000)

    # Buscar producto
    page.get_by_placeholder("Buscar en listado de productos").fill("A")

    page.wait_for_timeout(3000)

    page.get_by_text("ASESORIA CONTABILIDAD").click()

    page.wait_for_timeout(2000)

    # Precio unitario
    page.locator("input").last.fill(str(cliente["subtotal"]))

    page.wait_for_timeout(2000)

    print("FACTURA LLENADA (PRUEBA)")

    browser.close()
