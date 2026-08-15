from playwright.sync_api import sync_playwright
import os
import json
from pathlib import Path

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CLIENTE_ID = os.getenv("CLIENTE_ID", "gloria_pardo")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

CLIENTES_PATH = Path("clientes.json")
if not CLIENTES_PATH.exists():
    raise RuntimeError("No existe clientes.json")

with CLIENTES_PATH.open("r", encoding="utf-8") as f:
    CLIENTES = json.load(f)

if CLIENTE_ID not in CLIENTES:
    raise RuntimeError(f"Cliente '{CLIENTE_ID}' no existe en clientes.json")

CLIENTE = CLIENTES[CLIENTE_ID]

if not CLIENTE.get("activo", False):
    raise RuntimeError(f"El cliente '{CLIENTE_ID}' está desactivado")

CLIENTE_RUC = CLIENTE["ruc"]
PRODUCTO_BUSQUEDA = CLIENTE.get("producto", "ASESORIA CONTABILIDAD")
PRODUCTO_ESPERADO = CLIENTE.get("producto", "ASESORIA CONTABILIDAD")


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


def sobrescribir_campo(page, selector, valor, nombre):
    campo = page.locator(selector)
    campo.wait_for(state="visible", timeout=30000)

    if not campo.is_editable():
        raise RuntimeError(f"El campo {nombre} no está editable en el SRI")

    campo.fill("")
    campo.fill(str(valor))
    campo.press("Tab")
    page.wait_for_timeout(500)

    valor_final = campo.input_value().strip()
    if valor_final != str(valor).strip():
        raise RuntimeError(
            f"No se pudo guardar {nombre}. Esperado='{valor}' / Actual='{valor_final}'"
        )

    print(f"{nombre}: {valor_final}")


if not SRI_RUC:
    raise RuntimeError("Falta el secret SRI_RUC")
if not SRI_CLAVE:
    raise RuntimeError("Falta el secret SRI_CLAVE")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_default_timeout(30000)

    try:
        log(f"CLIENTE SELECCIONADO: {CLIENTE_ID}")
        print("RUC:", CLIENTE_RUC)
        print("Razón social esperada:", CLIENTE["razon_social"])
        print("Subtotal configurado:", CLIENTE["subtotal"])

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
            CLIENTE.get("tipo_identificacion", "RUC"),
        )

        # 7. CLIENTE
        log("7. CLIENTE")
        campo_ruc = page.locator("#form\\:busquedaCompradorComp\\:ruc")
        campo_ruc.fill(CLIENTE_RUC)
        campo_ruc.press("Tab")
        page.wait_for_timeout(4500)

        razon = page.locator("#form\\:busquedaCompradorComp\\:compradorRazonSocial").input_value()
        print("Razón social cargada por SRI:", razon)
        if not razon.strip():
            raise RuntimeError("El SRI no cargó el cliente")

        # 8. SOBRESCRIBIR DATOS MANUALES DEL CLIENTE
        log("8. DATOS MANUALES DEL CLIENTE")
        sobrescribir_campo(
            page,
            "#form\\:busquedaCompradorComp\\:compradorDireccion",
            CLIENTE["direccion"],
            "Dirección",
        )
        sobrescribir_campo(
            page,
            "#form\\:busquedaCompradorComp\\:compradorTelefono",
            CLIENTE["telefono"],
            "Teléfono",
        )
        sobrescribir_campo(
            page,
            "#form\\:busquedaCompradorComp\\:compradorEmail",
            CLIENTE["correo"],
            "Correo",
        )
        screenshot(page, "03_cliente_datos_manual.png")
        print("DATOS MANUALES DEL CLIENTE CONFIRMADOS")

        # 9. PRODUCTO
        log("9. PRODUCTO ASESORIA CONTABILIDAD")
        producto = page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input")
        producto.click()
        producto.fill("")
        producto.press_sequentially(PRODUCTO_BUSQUEDA, delay=160)
        page.wait_for_timeout(4000)
        screenshot(page, "04_autocomplete_abierto.png")

        resultado = page.get_by_text(PRODUCTO_ESPERADO, exact=True)
        print("Coincidencias visuales exactas:", resultado.count())

        elegido = None
        for i in range(resultado.count()):
            candidato = resultado.nth(i)
            try:
                if candidato.is_visible():
                    elegido = candidato
                    break
            except Exception:
                pass

        if elegido is None:
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
            raise RuntimeError("No se pudo localizar ASESORIA CONTABILIDAD")

        print("Haciendo clic en ASESORIA CONTABILIDAD")
        elegido.click(force=True)
        page.wait_for_timeout(5000)

        # 10. VALIDAR PRODUCTO EN TABLA
        log("10. VALIDANDO PRODUCTO EN LA FACTURA")
        filas = page.locator("tr").filter(has_text="ASESORIA CONTABILIDAD")
        print("Filas ASESORIA encontradas:", filas.count())

        if filas.count() == 0:
            screenshot(page, "07_producto_no_agregado.png")
            raise RuntimeError("El producto no se agregó a la tabla")

        fila = filas.first
        print("PRODUCTO AGREGADO CORRECTAMENTE")
        print("Fila:", fila.inner_text())
        screenshot(page, "07_producto_agregado.png")

        # 11. CAMPOS DEL PRODUCTO
        log("11. CAMPOS REALES DEL PRODUCTO")
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

        log("AVANCE CONFIRMADO: CLIENTE + DATOS MANUALES + PRODUCTO")

    except Exception as e:
        screenshot(page, "99_error_final.png")
        print("\nERROR CONTROLADO:", str(e))
        raise

    finally:
        browser.close()
