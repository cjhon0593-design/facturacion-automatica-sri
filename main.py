from playwright.sync_api import sync_playwright
import os
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CLIENTE_ID = os.getenv("CLIENTE_ID", "gloria_pardo")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

with Path("clientes.json").open("r", encoding="utf-8") as f:
    CLIENTES = json.load(f)

if CLIENTE_ID not in CLIENTES:
    raise RuntimeError(f"Cliente '{CLIENTE_ID}' no existe en clientes.json")

CLIENTE = CLIENTES[CLIENTE_ID]
if not CLIENTE.get("activo", False):
    raise RuntimeError(f"El cliente '{CLIENTE_ID}' está desactivado")

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
}

ahora_ec = datetime.now(ZoneInfo("America/Guayaquil"))
detalle_mes = CLIENTE.get(
    "campo_adicional_plantilla",
    "SERVICIOS MES DE {MES} {ANIO}"
).format(MES=MESES[ahora_ec.month], ANIO=ahora_ec.year)


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
            page.wait_for_timeout(1800)
            print(f"Seleccionado: {etiqueta} | valor={valor}")
            return etiqueta

    disponibles = [opciones.nth(i).inner_text().strip() for i in range(opciones.count())]
    raise RuntimeError(f"No se encontró '{texto}'. Opciones: {disponibles}")


def sobrescribir_campo(page, selector, valor, nombre):
    campo = page.locator(selector)
    campo.wait_for(state="visible", timeout=30000)
    campo.fill(str(valor))
    campo.press("Tab")
    page.wait_for_timeout(500)
    actual = campo.input_value().strip()
    if actual != str(valor).strip():
        raise RuntimeError(f"No se pudo guardar {nombre}. Esperado='{valor}' / Actual='{actual}'")
    print(f"{nombre}: {actual}")


def valor_float(locator):
    valor = locator.get_attribute("value")
    if valor is None:
        try:
            valor = locator.input_value()
        except Exception:
            valor = "0"
    return float(str(valor).replace(",", "."))


def buscar_boton_visible(page, texto):
    candidatos = page.get_by_role("button", name=texto, exact=True)
    for i in range(candidatos.count()):
        try:
            if candidatos.nth(i).is_visible():
                return candidatos.nth(i)
        except Exception:
            pass
    candidatos = page.get_by_text(texto, exact=True)
    for i in range(candidatos.count()):
        try:
            if candidatos.nth(i).is_visible():
                return candidatos.nth(i)
        except Exception:
            pass
    return None


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
        print("RUC:", CLIENTE["ruc"])
        print("Razón social esperada:", CLIENTE["razon_social"])
        print("Subtotal:", CLIENTE["subtotal"])
        print("IVA:", CLIENTE["iva"])
        print("Total:", CLIENTE["total"])
        print("Información adicional:", detalle_mes)

        # 1. LOGIN
        log("1. INICIANDO SESIÓN EN EL SRI")
        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        page.locator('input[type="text"]:visible').first.fill(SRI_RUC)
        page.locator('input[type="password"]:visible').first.fill(SRI_CLAVE)
        page.get_by_role("button", name="Ingresar", exact=True).click()
        page.wait_for_timeout(5000)
        if "Ingresar al Sistema" in page.locator("body").inner_text():
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
        campo_ruc.fill(CLIENTE["ruc"])
        campo_ruc.press("Tab")
        page.wait_for_timeout(4500)
        razon = page.locator("#form\\:busquedaCompradorComp\\:compradorRazonSocial").input_value()
        print("Razón social cargada por SRI:", razon)
        if not razon.strip():
            raise RuntimeError("El SRI no cargó el cliente")

        # 8. DATOS MANUALES
        log("8. DATOS MANUALES DEL CLIENTE")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorDireccion", CLIENTE["direccion"], "Dirección")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorTelefono", CLIENTE["telefono"], "Teléfono")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorEmail", CLIENTE["correo"], "Correo")
        screenshot(page, "03_cliente_datos_manual.png")

        # 9. PRODUCTO
        log("9. PRODUCTO ASESORIA CONTABILIDAD")
        producto = page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input")
        producto.click()
        producto.fill("")
        producto.press_sequentially(CLIENTE["producto"], delay=140)
        page.wait_for_timeout(4000)

        resultado = page.get_by_text(CLIENTE["producto"], exact=True)
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
            raise RuntimeError("No se pudo localizar ASESORIA CONTABILIDAD")

        elegido.click(force=True)
        page.wait_for_timeout(5000)

        # 10. VALIDAR FILA
        log("10. VALIDANDO PRODUCTO EN LA FACTURA")
        filas = page.locator("tr").filter(has_text="ASESORIA CONTABILIDAD")
        if filas.count() == 0:
            raise RuntimeError("El producto no se agregó a la tabla")
        fila = filas.first
        print("PRODUCTO AGREGADO CORRECTAMENTE")

        # 11. PRECIO
        log("11. PRECIO UNITARIO")
        precio = fila.locator("input[id*='precioUnitarioOutputText']")
        precio.wait_for(state="visible", timeout=30000)
        precio.fill(f"{float(CLIENTE['subtotal']):.2f}")
        precio.press("Tab")
        page.wait_for_timeout(4500)
        print("Precio ingresado:", precio.input_value())

        # 12. VALIDAR IMPUESTOS Y TOTAL DEL PRODUCTO
        log("12. VALIDANDO SUBTOTAL, IVA Y TOTAL")
        base = valor_float(fila.locator("input[id*='baseImponibleInputHidden']"))
        iva = valor_float(fila.locator("input[id*='valorImpuestoInputHidden']"))
        total_producto = valor_float(fila.locator("input[id*='valorTotalInputHidden']"))

        print("Base imponible:", base)
        print("IVA producto:", iva)
        print("Total producto:", total_producto)

        if round(base, 2) != round(float(CLIENTE["subtotal"]), 2):
            raise RuntimeError(f"Subtotal incorrecto: {base}")
        if round(iva, 2) != round(float(CLIENTE["iva"]), 2):
            raise RuntimeError(f"IVA incorrecto: {iva}")
        if round(total_producto, 2) != round(float(CLIENTE["total"]), 2):
            raise RuntimeError(f"Total incorrecto: {total_producto}")

        print("VALORES CORRECTOS")
        screenshot(page, "08_valores_correctos.png")

        # 13. FORMA DE PAGO
        log("13. FORMA DE PAGO")
        boton_pago = buscar_boton_visible(page, "Añadir forma de pago")
        if boton_pago is None:
            raise RuntimeError("No se encontró Añadir forma de pago")
        boton_pago.click(force=True)
        page.wait_for_timeout(2000)

        seleccionar_option_por_texto(
            page,
            "#form\\:formaPagoComposite\\:selectFormaPago_input",
            CLIENTE["forma_pago"],
        )

        valor_pago = page.locator("#form\\:formaPagoComposite\\:impValorPago")
        valor_pago.fill(f"{float(CLIENTE['forma_pago_valor']):.2f}")
        valor_pago.press("Tab")
        page.wait_for_timeout(1000)

        guardar = buscar_boton_visible(page, "Guardar")
        if guardar is not None:
            guardar.click(force=True)
            page.wait_for_timeout(3000)

        print("Forma de pago configurada:", CLIENTE["forma_pago"])
        print("Valor forma de pago:", CLIENTE["forma_pago_valor"])

        # 14. INFORMACIÓN ADICIONAL
        log("14. INFORMACIÓN ADICIONAL")
        boton_adicional = buscar_boton_visible(page, "Añadir campo adicional")
        if boton_adicional is None:
            raise RuntimeError("No se encontró Añadir campo adicional")
        boton_adicional.click(force=True)
        page.wait_for_timeout(2000)

        nombre_adicional = page.locator("#form\\:campoAdicionalComposite\\:idNombreCampoAdcional")
        nombre_adicional.wait_for(state="visible", timeout=20000)
        nombre_adicional.fill(CLIENTE.get("campo_adicional_nombre", "DETALLE"))

        candidatos = page.locator("[id^='form:campoAdicionalComposite:']")
        descripcion = None
        for i in range(candidatos.count()):
            el = candidatos.nth(i)
            try:
                tag = el.evaluate("e => e.tagName")
                el_id = el.get_attribute("id") or ""
                if (
                    tag in ["INPUT", "TEXTAREA"]
                    and "idNombreCampoAdcional" not in el_id
                    and el.is_visible()
                    and el.is_editable()
                ):
                    descripcion = el
                    break
            except Exception:
                pass

        if descripcion is None:
            screenshot(page, "09_campo_adicional_no_encontrado.png")
            raise RuntimeError("No se encontró el campo Descripción de información adicional")

        descripcion.fill(detalle_mes)
        descripcion.press("Tab")

        guardar = buscar_boton_visible(page, "Guardar")
        if guardar is not None:
            guardar.click(force=True)
            page.wait_for_timeout(3000)

        print("Nombre adicional:", CLIENTE.get("campo_adicional_nombre", "DETALLE"))
        print("Descripción adicional:", detalle_mes)
        screenshot(page, "10_factura_preparada.png")

        # 15. VALIDACIÓN FINAL SIN FIRMAR
        log("15. VALIDACIÓN FINAL - SIN FIRMAR")
        texto = page.locator("body").inner_text()
        if CLIENTE["producto"].upper() not in texto.upper():
            raise RuntimeError("El producto no aparece al final")
        if detalle_mes.upper() not in texto.upper():
            raise RuntimeError("La información adicional no aparece al final")

        print("FACTURA PREPARADA CORRECTAMENTE")
        print("Cliente:", CLIENTE["razon_social"])
        print("Subtotal:", CLIENTE["subtotal"])
        print("IVA:", CLIENTE["iva"])
        print("Total:", CLIENTE["total"])
        print("Forma de pago:", CLIENTE["forma_pago"])
        print("Información adicional:", detalle_mes)
        print("NO SE FIRMÓ NI ENVIÓ EN ESTA PRUEBA")

        log("AVANCE CONFIRMADO: FACTURA COMPLETA LISTA PARA FIRMA")

    except Exception as e:
        screenshot(page, "99_error_final.png")
        print("\nERROR CONTROLADO:", str(e))
        raise
    finally:
        browser.close()
