from playwright.sync_api import sync_playwright
import os

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

if not SRI_RUC:
    raise Exception("No existe el secret SRI_RUC")

if not SRI_CLAVE:
    raise Exception("No existe el secret SRI_CLAVE")

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1920, "height": 1080}
    )

    # ==========================================================
    # 1. INICIAR SESIÓN
    # ==========================================================

    print("1. Ingresando al SRI...")

    page.goto(
        URL_LOGIN,
        wait_until="networkidle",
        timeout=60000
    )

    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').first.fill(SRI_CLAVE)

    page.get_by_role(
        "button",
        name="Ingresar"
    ).click()

    page.wait_for_timeout(6000)

    print("LOGIN COMPLETADO")
    print("URL:", page.url)

    # ==========================================================
    # 2. ABRIR FACTURA DIRECTAMENTE
    # ==========================================================

    print("2. Abriendo pantalla de factura...")

    page.goto(
        URL_FACTURA,
        wait_until="networkidle",
        timeout=60000
    )

    page.wait_for_timeout(6000)

    print("PANTALLA DE FACTURA ABIERTA")
    print("URL:", page.url)

    # ==========================================================
    # 3. MOSTRAR TODOS LOS INPUTS
    # ==========================================================

    print("")
    print("=" * 80)
    print("INPUTS ENCONTRADOS")
    print("=" * 80)

    inputs = page.locator("input")

    print("TOTAL INPUTS:", inputs.count())

    for i in range(inputs.count()):

        elemento = inputs.nth(i)

        try:
            print(
                i,
                "TYPE =", elemento.get_attribute("type"),
                "| ID =", elemento.get_attribute("id"),
                "| NAME =", elemento.get_attribute("name"),
                "| VALUE =", elemento.get_attribute("value"),
                "| PLACEHOLDER =", elemento.get_attribute("placeholder")
            )
        except:
            pass

    # ==========================================================
    # 4. MOSTRAR TODOS LOS SELECT
    # ==========================================================

    print("")
    print("=" * 80)
    print("SELECT ENCONTRADOS")
    print("=" * 80)

    selects = page.locator("select")

    print("TOTAL SELECT:", selects.count())

    for i in range(selects.count()):

        elemento = selects.nth(i)

        try:
            print(
                i,
                "ID =", elemento.get_attribute("id"),
                "| NAME =", elemento.get_attribute("name")
            )
        except:
            pass

    # ==========================================================
    # 5. MOSTRAR ELEMENTOS PRIMEFACES SELECTONEMENU
    # ==========================================================

    print("")
    print("=" * 80)
    print("SELECTORES PRIMEFACES")
    print("=" * 80)

    elementos = page.locator(
        ".ui-selectonemenu, "
        ".ui-selectonemenu-label, "
        ".ui-selectonemenu-trigger"
    )

    print("TOTAL:", elementos.count())

    for i in range(elementos.count()):

        elemento = elementos.nth(i)

        try:

            print(
                i,
                "TAG =", elemento.evaluate("(e) => e.tagName"),
                "| ID =", elemento.get_attribute("id"),
                "| CLASS =", elemento.get_attribute("class"),
                "| TEXTO =", elemento.inner_text(timeout=1000)
            )

        except:
            pass

    # ==========================================================
    # 6. BUSCAR TEXTO RELACIONADO CON IDENTIFICACIÓN
    # ==========================================================

    print("")
    print("=" * 80)
    print("ELEMENTOS RELACIONADOS CON IDENTIFICACIÓN")
    print("=" * 80)

    candidatos = page.locator(
        "[id*='Identificacion'], "
        "[id*='identificacion'], "
        "[id*='TipoIdentificacion'], "
        "[id*='tipoIdentificacion'], "
        "[id*='ruc'], "
        "[name*='Identificacion'], "
        "[name*='identificacion'], "
        "[name*='ruc']"
    )

    print("TOTAL CANDIDATOS:", candidatos.count())

    for i in range(candidatos.count()):

        elemento = candidatos.nth(i)

        try:

            print(
                i,
                "TAG =", elemento.evaluate("(e) => e.tagName"),
                "| ID =", elemento.get_attribute("id"),
                "| NAME =", elemento.get_attribute("name"),
                "| TYPE =", elemento.get_attribute("type"),
                "| CLASS =", elemento.get_attribute("class"),
                "| VALUE =", elemento.get_attribute("value")
            )

        except:
            pass

    # ==========================================================
    # 7. TEXTO DE LA PÁGINA
    # ==========================================================

    print("")
    print("=" * 80)
    print("TEXTO VISIBLE DE LA PÁGINA")
    print("=" * 80)

    print(page.locator("body").inner_text())

    print("")
    print("=" * 80)
    print("DIAGNÓSTICO TERMINADO CORRECTAMENTE")
    print("=" * 80)

    browser.close()
