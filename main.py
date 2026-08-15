from playwright.sync_api import sync_playwright
import os

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1920, "height": 1080}
    )

    # =========================================================
    # 1. INGRESAR AL FACTURADOR SRI
    # =========================================================
    print("1. Ingresando al SRI...")

    page.goto(
        URL_LOGIN,
        wait_until="networkidle",
        timeout=60000
    )

    page.locator('input[type="text"]').first.fill(SRI_RUC)
    page.locator('input[type="password"]').fill(SRI_CLAVE)

    page.get_by_role("button", name="Ingresar").click()

    page.wait_for_timeout(6000)

    # =========================================================
    # 2. IR DIRECTAMENTE A FACTURA
    # =========================================================
    print("2. Abriendo pantalla de factura...")

    page.goto(
        URL_FACTURA,
        wait_until="networkidle",
        timeout=60000
    )

    page.wait_for_timeout(6000)

    # =========================================================
    # 3. TIPO DE IDENTIFICACIÓN = RUC
    # =========================================================
    print("3. Seleccionando RUC...")

    tipo_identificacion = page.locator(
        "#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_focus"
    )

    tipo_identificacion.click(force=True)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    page.wait_for_timeout(1500)

    # =========================================================
    # 4. CLIENTE
    # =========================================================
    print("4. Colocando cliente...")

    campo_ruc = page.locator(
        "#form\\:busquedaCompradorComp\\:ruc"
    )

    campo_ruc.fill("1723041156001")

    page.keyboard.press("Tab")

    page.wait_for_timeout(5000)

    print("Razón social encontrada:")

    try:
        razon_social = page.locator(
            "#form\\:busquedaCompradorComp\\:compradorRazonSocial"
        ).input_value()

        print(razon_social)

    except Exception as e:
        print("No se pudo leer la razón social:", e)

    # =========================================================
    # 5. BUSCAR PRODUCTO
    # =========================================================
    print("5. Buscando ASESORIA CONTABILIDAD...")

    producto = page.locator(
        "#form\\:productoBusquedaComposite\\:autoCompleteProducto_input"
    )

    producto.click(force=True)

    # Escribimos como una persona, no usamos fill()
    producto.press_sequentially(
        "A",
        delay=300
    )

    page.wait_for_timeout(6000)

    # =========================================================
    # 6. ANALIZAR QUÉ MOSTRÓ EL AUTOCOMPLETE
    # =========================================================
    print("")
    print("========================================")
    print("RESULTADOS DEL AUTOCOMPLETE")
    print("========================================")

    # Buscar paneles visibles relacionados al autocomplete
    posibles_paneles = page.locator(
        "[id*='autoCompleteProducto']:visible"
    )

    print(
        "Elementos visibles relacionados con autoCompleteProducto:",
        posibles_paneles.count()
    )

    for i in range(posibles_paneles.count()):
        elemento = posibles_paneles.nth(i)

        try:
            print("")
            print("ELEMENTO", i)
            print("TAG:", elemento.evaluate("el => el.tagName"))
            print("ID:", elemento.get_attribute("id"))
            print("CLASE:", elemento.get_attribute("class"))
            print("TEXTO:")
            print(elemento.inner_text())

        except Exception as e:
            print("No se pudo leer elemento", i, e)

    # =========================================================
    # 7. MOSTRAR TODOS LOS LI VISIBLES
    # =========================================================
    print("")
    print("========================================")
    print("TODOS LOS <li> VISIBLES")
    print("========================================")

    items = page.locator("li:visible")

    print("Cantidad de LI visibles:", items.count())

    for i in range(items.count()):
        item = items.nth(i)

        try:
            texto = item.inner_text().strip()

            if texto:
                print(
                    i,
                    "| ID:",
                    item.get_attribute("id"),
                    "| CLASE:",
                    item.get_attribute("class"),
                    "| TEXTO:",
                    texto
                )

        except:
            pass

    # =========================================================
    # 8. BUSCAR TEXTO ASESORIA EN CUALQUIER PARTE
    # =========================================================
    print("")
    print("========================================")
    print("ELEMENTOS QUE CONTIENEN ASESORIA")
    print("========================================")

    asesorias = page.get_by_text(
        "ASESORIA",
        exact=False
    )

    print("Cantidad encontrada:", asesorias.count())

    for i in range(asesorias.count()):
        elemento = asesorias.nth(i)

        try:
            print("")
            print("ASESORIA ELEMENTO", i)
            print("TAG:", elemento.evaluate("el => el.tagName"))
            print("ID:", elemento.get_attribute("id"))
            print("CLASE:", elemento.get_attribute("class"))
            print("TEXTO:", elemento.inner_text())

        except:
            pass

    # =========================================================
    # 9. MOSTRAR TEXTO GENERAL
    # =========================================================
    print("")
    print("========================================")
    print("TEXTO GENERAL DE LA PÁGINA")
    print("========================================")

    print(page.locator("body").inner_text())

    browser.close()
