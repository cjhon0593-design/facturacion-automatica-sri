from playwright.sync_api import sync_playwright
import os
from datetime import datetime

RUC = os.getenv("SRI_RUC")
CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")

clientes = [
    {
        "nombre": "PARDO AGURTO GLORIA ALEXANDRA",
        "ruc": "1723041156001",
        "subtotal": 230
    },
    {
        "nombre": "FACILITADORES DE COMERCIO EXTERIOR FCOMEX S.A.S.",
        "ruc": "1793149405001",
        "subtotal": 200
    }
]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html")

        # Login
        page.fill('input[name="usuario"]', RUC)
        page.fill('input[name="password"]', CLAVE)
        page.click('button[type="submit"]')

        for cliente in clientes:
            # Aquí luego se completa navegación y llenado (te lo ajusto después exacto)
            print(f"Facturando a {cliente['nombre']}")

        browser.close()

if __name__ == "__main__":
    run()
