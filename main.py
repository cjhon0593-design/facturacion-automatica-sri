from playwright.sync_api import sync_playwright
import os
from pathlib import Path

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

CLIENTE_RUC = "1723041156001"
PRODUCTO_BUSQUEDA = "ASESORIA"
PRODUCTO_ESPERADO = "ASESORIA CONTABILIDAD"

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


def log(titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)


def screenshot(page, nombre):
    try:
        page.screenshot(path=str(DEBUG_DIR / nombre), full_page=True)
    except Exception as e:
        print(f"No se pudo guardar captura {nombre}: {e}")


def seleccionar_option_por_texto(page, selector, texto):
    select = page.locator(selector)
    select.wait_for(state="attached", timeout=30000)
    opciones = select.locator("option")

    for i in range(opciones.count()):
        opcion = opciones.nth(i)
        etiqueta = opcion.inner_text().strip()
        valor = opcion.get_attribute("value")
        if texto.upper() in etiqueta.upper():
            select.select_option(value=valor)
            select.dispatch_event("change")
            page.wait_for_timeout(2000)
            print(f"Seleccionado: {etiqueta} | valor={valor}")
            return

    raise RuntimeError(f"No se encontró la opción: {texto}")


if not SRI_RUC:
    raise RuntimeError("Falta el secret SRI_RUC")
if not SRI_CLAVE:
    raise RuntimeError("Falta el secret SRI_CLAVE")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_default_timeout(30000)

    try:
        # 1. LOGIN
        log("1. INICIANDO SESIÓN EN EL SRI")
        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        usuario = page.locator('input[type="text"]:visible').first
        clave = page.locator('input[type="password"]:visible').first
        usuario.fill(SRI_RUC)
        clave.fill(SRI_CLAVE)
        page.get_by_role("button", name="Ingresar", exact=True).click()
        page.wait_for_timeout(5000)

        cuerpo = page.locator("body").inner_text()
        if "Ingresar al Sistema" in cuerpo:
            screenshot(page, "01_login_fallido.png")
            raise RuntimeError("El SRI no aceptó el inicio de sesión")

        print("LOGIN CORRECTO")

        # 2. FACTURA
        log("2. ABRIENDO PANTALLA DE FACTURA")
        page.goto(URL_FACTURA, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        if "Emisión - Factura" not in page.locator("body").inner_text():
            raise RuntimeError("No se abrió la pantalla de factura")
        print("PANTALLA DE FACTURA CORRECTA")

        # 3. ESTABLECIMIENTO
        log("3. ESTABLECIMIENTO")
        seleccionar_option_por_texto(
            page,
            "#form\\:cabeceraComprobanteDlg\\:j_idt61_input",
            "001 - AV ELOY ALFARO",
        )

        # 4. FECHA
        log("4. FECHA DE EMISIÓN")
        fecha = page.locator("#form\\:identifiacionDelComprobante\\:calFechaEmi_input")
        print("Fecha SRI:", fecha.input_value())

        # 5. PUNTO EMISION
        log("5. PUNTO DE EMISIÓN")
        seleccionar_option_por_texto(
            page,
            "#form\\:identifiacionDelComprobante\\:selectsecuencial_input",
            "100",
        )

        # 6. TIPO ID
        log("6. TIPO DE IDENTIFICACIÓN")
        seleccionar_option_por_texto(
            page,
            "#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_input",
            "RUC",
        )

        # 7. CLIENTE
        log("7. CLIENTE")
        campo_ruc = page.locator("#form\\:busquedaCompradorComp\\:ruc")
        campo_ruc.fill(CLIENTE_RUC)
        campo_ruc.press("Tab")
        page.wait_for_timeout(4500)

        razon = page.locator("#form\\:busquedaCompradorComp\\:compradorRazonSocial").input_value()
        print("Razón social cargada:", razon)
        if not razon.strip():
            raise RuntimeError("El SRI no cargó el cliente")

        # 8. PRODUCTO
        log("8. PRODUCTO ASESORIA CONTABILIDAD")
        producto = page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input")
        producto.click()
        producto.fill("")
        producto.press_sequentially(PRODUCTO_BUSQUEDA, delay=160)
        page.wait_for_timeout(4000)
        screenshot(page, "04_autocomplete_abierto.png")

        # La captura real del SRI mostró el texto visible ASESORIA CONTABILIDAD,
        # aunque PrimeFaces no lo expone como li.ui-autocomplete-item.
        resultado = page.get_by_text(PRODUCTO_ESPERADO, exact=True)
        print("Coincidencias visuales exactas:", resultado.count())

        elegido = None
        for i in range(resultado.count()):
            candidato = resultado.nth(i)
            try:
                if candidato.is_visible():
                    elegido = candidato
                    print(
                        "Elemento encontrado:",
                        candidato.evaluate("e => e.tagName"),
                        candidato.get_attribute("id"),
                        candidato.get_attribute("class"),
                    )
                    break
            except Exception:
                pass

        if elegido is None:
            # Fallback: cualquier elemento visible cuyo texto contenga ASESORIA CONTABILIDAD.
            candidatos = page.locator(":text('ASESORIA CONTABILIDAD')")
            for i in range(candidatos.count()):
                candidato = candidatos.nth(i)
                try:
                    if candidato.is_visible():
                        elegido = candidato
                        break
                except Exception:
                    pass

        if elegido is None:
            screenshot(page, "05_producto_no_encontrado.png")
            raise RuntimeError("El SRI muestra el autocomplete, pero Playwright no pudo localizar el texto visible")

        print("Haciendo clic en ASESORIA CONTABILIDAD")
        elegido.click(force=True)
        page.wait_for_timeout(5000)
        screenshot(page, "06_despues_click_producto.png")

        # 9. VALIDAR PRODUCTO EN TABLA
        log("9. VALIDANDO PRODUCTO EN LA FACTURA")
        filas = page.locator("tr").filter(has_text="ASESORIA CONTABILIDAD")
        print("Filas ASESORIA encontradas:", filas.count())

        if filas.count() == 0:
            screenshot(page, "07_producto_no_agregado.png")
            raise RuntimeError("Se hizo clic en ASESORIA CONTABILIDAD, pero no se agregó a la tabla")

        fila = filas.first
        print("PRODUCTO AGREGADO CORRECTAMENTE")
        print("Fila:", fila.inner_text())
        screenshot(page, "07_producto_agregado.png")

        # 10. CAPTURAR CAMPOS DEL PRODUCTO
        log("10. CAMPOS REALES DEL PRODUCTO")
        inputs = fila.locator("input")
        print("Total inputs en la fila:", inputs.count())

        for i in range(inputs.count()):
            inp = inputs.nth(i)
            print(
                i,
                "| id=", inp.get_attribute("id"),
                "| name=", inp.get_attribute("name"),
                "| type=", inp.get_attribute("type"),
                "| value=", inp.get_attribute("value"),
            )

        log("AVANCE REAL CONFIRMADO: PRODUCTO AGREGADO")

    except Exception as e:
        screenshot(page, "99_error_final.png")
        print("\nERROR CONTROLADO:", str(e))
        raise

    finally:
        browser.close()
