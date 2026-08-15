from playwright.sync_api import sync_playwright
import os
from pathlib import Path

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")

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
            return etiqueta

    disponibles = [opciones.nth(i).inner_text().strip() for i in range(opciones.count())]
    raise RuntimeError(f"No se encontró '{texto}'. Opciones: {disponibles}")


if not SRI_RUC:
    raise RuntimeError("Falta el secret SRI_RUC")
if not SRI_CLAVE:
    raise RuntimeError("Falta el secret SRI_CLAVE")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_default_timeout(30000)

    try:
        # ====================================================
        # 1. LOGIN ROBUSTO
        # ====================================================
        log("1. INICIANDO SESIÓN EN EL SRI")

        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        # El portal ha cambiado atributos del login entre ejecuciones.
        # Usamos los campos visibles, que es la estrategia que ya funcionó.
        usuario = page.locator('input[type="text"]:visible').first
        clave = page.locator('input[type="password"]:visible').first

        usuario.wait_for(state="visible", timeout=30000)
        clave.wait_for(state="visible", timeout=30000)

        usuario.fill(SRI_RUC)
        clave.fill(SRI_CLAVE)
        page.get_by_role("button", name="Ingresar", exact=True).click()

        # Esperar hasta que desaparezca realmente el formulario de acceso.
        page.wait_for_timeout(5000)
        cuerpo = page.locator("body").inner_text()

        if "Ingresar al Sistema" in cuerpo or "*RUC:" in cuerpo and "*Clave:" in cuerpo:
            screenshot(page, "01_login_fallido.png")
            raise RuntimeError(
                "El SRI no aceptó el inicio de sesión. Revisa SRI_RUC/SRI_CLAVE o un mensaje mostrado por el portal."
            )

        print("LOGIN CORRECTO")
        print("URL después del login:", page.url)
        screenshot(page, "01_login_correcto.png")

        # ====================================================
        # 2. ABRIR FACTURA
        # ====================================================
        log("2. ABRIENDO PANTALLA DE FACTURA")

        page.goto(URL_FACTURA, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        cuerpo = page.locator("body").inner_text()
        if "Emisión - Factura" not in cuerpo:
            screenshot(page, "02_factura_no_abre.png")
            raise RuntimeError("No se abrió la pantalla Emisión - Factura después del login.")

        print("PANTALLA DE FACTURA CORRECTA")
        screenshot(page, "02_factura_abierta.png")

        # ====================================================
        # 3. ESTABLECIMIENTO
        # ====================================================
        log("3. ESTABLECIMIENTO")
        seleccionar_option_por_texto(
            page,
            "#form\\:cabeceraComprobanteDlg\\:j_idt61_input",
            "001 - AV ELOY ALFARO",
        )

        # ====================================================
        # 4. FECHA
        # ====================================================
        log("4. FECHA DE EMISIÓN")
        fecha = page.locator("#form\\:identifiacionDelComprobante\\:calFechaEmi_input")
        fecha.wait_for(state="visible", timeout=30000)
        print("Fecha SRI:", fecha.input_value())

        # ====================================================
        # 5. PUNTO DE EMISIÓN
        # ====================================================
        log("5. PUNTO DE EMISIÓN")
        seleccionar_option_por_texto(
            page,
            "#form\\:identifiacionDelComprobante\\:selectsecuencial_input",
            "100",
        )

        # ====================================================
        # 6. TIPO IDENTIFICACIÓN = RUC
        # ====================================================
        log("6. TIPO DE IDENTIFICACIÓN")
        seleccionar_option_por_texto(
            page,
            "#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_input",
            "RUC",
        )

        # ====================================================
        # 7. CLIENTE
        # ====================================================
        log("7. CLIENTE")
        campo_ruc = page.locator("#form\\:busquedaCompradorComp\\:ruc")
        campo_ruc.wait_for(state="visible", timeout=30000)
        campo_ruc.fill(CLIENTE_RUC)
        campo_ruc.press("Tab")
        page.wait_for_timeout(4500)

        razon = page.locator("#form\\:busquedaCompradorComp\\:compradorRazonSocial")
        razon_social = razon.input_value()
        print("Razón social cargada:", razon_social)

        if not razon_social.strip():
            screenshot(page, "03_cliente_no_cargado.png")
            raise RuntimeError("El SRI no cargó la razón social del cliente.")

        # ====================================================
        # 8. PRODUCTO - AUTOCOMPLETE PRIMEFACES
        # ====================================================
        log("8. PRODUCTO ASESORIA CONTABILIDAD")

        producto = page.locator(
            "#form\\:productoBusquedaComposite\\:autoCompleteProducto_input"
        )
        producto.wait_for(state="visible", timeout=30000)
        producto.click()
        producto.fill("")
        producto.press_sequentially(PRODUCTO_BUSQUEDA, delay=160)

        # PrimeFaces crea un panel dinámico para el autocomplete.
        panel = page.locator(
            "#form\\:productoBusquedaComposite\\:autoCompleteProducto_panel"
        )

        try:
            panel.wait_for(state="visible", timeout=15000)
        except Exception:
            # Fallback por si el id del panel cambia, pero la clase PrimeFaces se mantiene.
            panel = page.locator(".ui-autocomplete-panel:visible").last
            panel.wait_for(state="visible", timeout=10000)

        screenshot(page, "04_autocomplete_abierto.png")

        items = panel.locator("li.ui-autocomplete-item")
        print("Resultados del autocomplete:", items.count())

        elegido = None
        for i in range(items.count()):
            item = items.nth(i)
            texto = item.inner_text().strip()
            print(f"  - {texto}")
            if PRODUCTO_ESPERADO in texto.upper():
                elegido = item
                break

        if elegido is None:
            # Aceptamos una coincidencia con ASESORIA si el texto exacto cambia ligeramente.
            for i in range(items.count()):
                item = items.nth(i)
                texto = item.inner_text().strip()
                if "ASESORIA" in texto.upper():
                    elegido = item
                    break

        if elegido is None:
            screenshot(page, "05_producto_no_encontrado.png")
            raise RuntimeError("El autocomplete abrió, pero no devolvió ASESORIA CONTABILIDAD.")

        print("Seleccionando:", elegido.inner_text().strip())
        elegido.click(force=True)
        page.wait_for_timeout(5000)

        # ====================================================
        # 9. VALIDAR QUE EL PRODUCTO SE AGREGÓ A LA TABLA
        # ====================================================
        log("9. VALIDANDO PRODUCTO EN LA FACTURA")

        fila = page.locator("tr").filter(has_text="ASESORIA").first
        try:
            fila.wait_for(state="visible", timeout=15000)
        except Exception:
            screenshot(page, "06_producto_no_agregado.png")
            print(page.locator("body").inner_text())
            raise RuntimeError(
                "Se seleccionó ASESORIA en el autocomplete, pero el SRI no la agregó a la tabla de detalle."
            )

        texto_fila = fila.inner_text().strip()
        print("PRODUCTO AGREGADO CORRECTAMENTE")
        print("Fila:", texto_fila)
        screenshot(page, "06_producto_agregado.png")

        # ====================================================
        # 10. IDENTIFICAR CAMPOS REALES DE LA FILA
        # ====================================================
        log("10. CAMPOS REALES DEL PRODUCTO")
        inputs_fila = fila.locator("input")
        print("Total inputs en fila:", inputs_fila.count())

        for i in range(inputs_fila.count()):
            inp = inputs_fila.nth(i)
            print(
                i,
                "| id=", inp.get_attribute("id"),
                "| name=", inp.get_attribute("name"),
                "| type=", inp.get_attribute("type"),
                "| value=", inp.get_attribute("value"),
            )

        log("AVANCE CONFIRMADO: LOGIN + FACTURA + CLIENTE + PRODUCTO FUNCIONAN")
        print("En la siguiente etapa se fijará precio, pago, campo adicional y firma usando los campos reales obtenidos arriba.")

    except Exception as e:
        screenshot(page, "99_error_final.png")
        print("\nERROR CONTROLADO:", str(e))
        raise

    finally:
        browser.close()
