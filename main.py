from playwright.sync_api import sync_playwright
import os
import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")
CLIENTE_ID = os.getenv("CLIENTE_ID", "gloria_pardo")
MODO_ENVIO = os.getenv("MODO_ENVIO", "PRUEBA").upper().strip()

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_FACTURA = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

with Path("clientes.json").open("r", encoding="utf-8") as f:
    CLIENTES = json.load(f)

EMISIONES_PATH = Path("emisiones.json")
if EMISIONES_PATH.exists():
    with EMISIONES_PATH.open("r", encoding="utf-8") as f:
        EMISIONES = json.load(f)
else:
    EMISIONES = {}

if CLIENTE_ID not in CLIENTES:
    raise RuntimeError(f"Cliente '{CLIENTE_ID}' no existe en clientes.json")

CLIENTE = CLIENTES[CLIENTE_ID]
if not CLIENTE.get("activo", False):
    raise RuntimeError(f"El cliente '{CLIENTE_ID}' está desactivado")

MESES = {1:"ENERO",2:"FEBRERO",3:"MARZO",4:"ABRIL",5:"MAYO",6:"JUNIO",7:"JULIO",8:"AGOSTO",9:"SEPTIEMBRE",10:"OCTUBRE",11:"NOVIEMBRE",12:"DICIEMBRE"}
ahora_ec = datetime.now(ZoneInfo("America/Guayaquil"))
CLAVE_PERIODO = f"{CLIENTE_ID}-{ahora_ec.year:04d}-{ahora_ec.month:02d}"
detalle_mes = CLIENTE.get("campo_adicional_plantilla", "SERVICIOS MES DE {MES} {ANIO}").format(MES=MESES[ahora_ec.month], ANIO=ahora_ec.year)


def log(titulo):
    print("\n" + "="*70)
    print(titulo)
    print("="*70)


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
    raise RuntimeError(f"No se encontró la opción: {texto}")


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
    for candidatos in [page.get_by_role("button", name=texto, exact=True), page.get_by_text(texto, exact=True)]:
        for i in range(candidatos.count()):
            try:
                if candidatos.nth(i).is_visible():
                    return candidatos.nth(i)
            except Exception:
                pass
    return None


def validar_fecha_sri(texto_fecha):
    texto_fecha = texto_fecha.strip()
    for formato in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            fecha = datetime.strptime(texto_fecha, formato).date()
            if fecha != ahora_ec.date():
                raise RuntimeError(f"Fecha de emisión incorrecta. SRI={fecha} / Ecuador={ahora_ec.date()}")
            return
        except ValueError:
            continue
    raise RuntimeError(f"Formato de fecha del SRI no reconocido: {texto_fecha}")


def controles_estaticos():
    log("CONTROL 0. VALIDACIONES DE CONFIGURACIÓN")

    if not SRI_RUC:
        raise RuntimeError("Falta el secret SRI_RUC")
    if not SRI_CLAVE:
        raise RuntimeError("Falta el secret SRI_CLAVE")
    if MODO_ENVIO not in {"PRUEBA", "PRODUCCION"}:
        raise RuntimeError("MODO_ENVIO debe ser PRUEBA o PRODUCCION")
    if MODO_ENVIO == "PRODUCCION" and not CERT_PASS:
        raise RuntimeError("En PRODUCCION falta el secret CERT_PASS")

    ruc = str(CLIENTE.get("ruc", "")).strip()
    correo = str(CLIENTE.get("correo", "")).strip()
    telefono = re.sub(r"\D", "", str(CLIENTE.get("telefono", "")))
    direccion = str(CLIENTE.get("direccion", "")).strip()

    if not (ruc.isdigit() and len(ruc) == 13):
        raise RuntimeError(f"RUC inválido en clientes.json: {ruc}")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        raise RuntimeError(f"Correo inválido en clientes.json: {correo}")
    if len(telefono) < 7:
        raise RuntimeError(f"Teléfono inválido en clientes.json: {CLIENTE.get('telefono')}")
    if len(direccion) < 5:
        raise RuntimeError("Dirección vacía o demasiado corta")

    subtotal = round(float(CLIENTE["subtotal"]), 2)
    iva = round(float(CLIENTE["iva"]), 2)
    total = round(float(CLIENTE["total"]), 2)
    pago = round(float(CLIENTE["forma_pago_valor"]), 2)

    if round(subtotal + iva, 2) != total:
        raise RuntimeError(f"Configuración inconsistente: subtotal {subtotal} + IVA {iva} != total {total}")
    if pago != total:
        raise RuntimeError(f"Forma de pago {pago} no coincide con total {total}")
    if not CLIENTE.get("forma_pago"):
        raise RuntimeError("Falta forma_pago en clientes.json")
    if not CLIENTE.get("producto"):
        raise RuntimeError("Falta producto en clientes.json")

    existente = EMISIONES.get(CLAVE_PERIODO)
    if existente and str(existente.get("estado", "")).upper() in {"AUTORIZADA", "ENVIADA", "EMITIDA"}:
        raise RuntimeError(f"CONTROL ANTI-DUPLICADO: ya existe emisión para {CLAVE_PERIODO}: {existente}")

    print("Modo:", MODO_ENVIO)
    print("Periodo controlado:", CLAVE_PERIODO)
    print("Información adicional esperada:", detalle_mes)
    print("CONFIGURACIÓN SUPERADA")


controles_estaticos()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":1920,"height":1080})
    page.set_default_timeout(30000)

    try:
        log(f"CLIENTE SELECCIONADO: {CLIENTE_ID}")
        print("RUC:", CLIENTE["ruc"])
        print("Razón social esperada:", CLIENTE["razon_social"])
        print("Subtotal:", CLIENTE["subtotal"])
        print("IVA:", CLIENTE["iva"])
        print("Total:", CLIENTE["total"])
        print("Información adicional:", detalle_mes)

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

        log("2. ABRIENDO PANTALLA DE FACTURA")
        page.goto(URL_FACTURA, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        if "Emisión - Factura" not in page.locator("body").inner_text():
            raise RuntimeError("No se abrió la pantalla de factura")
        print("PANTALLA DE FACTURA CORRECTA")

        log("3. ESTABLECIMIENTO")
        seleccionar_option_por_texto(page, "#form\\:cabeceraComprobanteDlg\\:j_idt61_input", "001 - AV ELOY ALFARO")

        log("4. FECHA DE EMISIÓN")
        fecha_sri = page.locator("#form\\:identifiacionDelComprobante\\:calFechaEmi_input").input_value()
        print("Fecha SRI:", fecha_sri)
        validar_fecha_sri(fecha_sri)
        print("CONTROL FECHA SUPERADO")

        log("5. PUNTO DE EMISIÓN")
        seleccionar_option_por_texto(page, "#form\\:identifiacionDelComprobante\\:selectsecuencial_input", "100")

        log("6. TIPO DE IDENTIFICACIÓN")
        seleccionar_option_por_texto(page, "#form\\:busquedaCompradorComp\\:cmbTipoIdentificacion_input", CLIENTE.get("tipo_identificacion", "RUC"))

        log("7. CLIENTE")
        campo_ruc = page.locator("#form\\:busquedaCompradorComp\\:ruc")
        campo_ruc.fill(CLIENTE["ruc"])
        campo_ruc.press("Tab")
        page.wait_for_timeout(4500)
        razon = page.locator("#form\\:busquedaCompradorComp\\:compradorRazonSocial").input_value()
        print("Razón social cargada por SRI:", razon)
        if not razon.strip():
            raise RuntimeError("El SRI no cargó el cliente")

        log("8. DATOS MANUALES DEL CLIENTE")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorDireccion", CLIENTE["direccion"], "Dirección")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorTelefono", CLIENTE["telefono"], "Teléfono")
        sobrescribir_campo(page, "#form\\:busquedaCompradorComp\\:compradorEmail", CLIENTE["correo"], "Correo")
        screenshot(page, "03_cliente_datos_manual.png")

        log("9. PRODUCTO ASESORIA CONTABILIDAD")
        producto = page.locator("#form\\:productoBusquedaComposite\\:autoCompleteProducto_input")
        producto.click()
        producto.fill("")
        producto.press_sequentially(CLIENTE["producto"], delay=140)
        page.wait_for_timeout(4000)

        resultado = page.get_by_text(CLIENTE["producto"], exact=True)
        elegido = None
        for i in range(resultado.count()):
            try:
                if resultado.nth(i).is_visible():
                    elegido = resultado.nth(i)
                    break
            except Exception:
                pass

        if elegido is None:
            candidatos = page.locator(":text('ASESORIA CONTABILIDAD')")
            for i in range(candidatos.count()):
                try:
                    if candidatos.nth(i).is_visible():
                        elegido = candidatos.nth(i)
                        break
                except Exception:
                    pass

        if elegido is None:
            raise RuntimeError("No se pudo localizar ASESORIA CONTABILIDAD")

        elegido.click(force=True)
        page.wait_for_timeout(5000)

        log("10. VALIDANDO PRODUCTO EN LA FACTURA")
        filas = page.locator("tr").filter(has_text="ASESORIA CONTABILIDAD")
        if filas.count() == 0:
            raise RuntimeError("El producto no se agregó a la tabla")
        fila = filas.first
        print("PRODUCTO AGREGADO CORRECTAMENTE")

        log("11. PRECIO UNITARIO")
        precio = fila.locator("input[id*='precioUnitarioOutputText']")
        precio.wait_for(state="visible", timeout=30000)
        precio.fill(f"{float(CLIENTE['subtotal']):.2f}")
        precio.press("Tab")
        page.wait_for_timeout(4500)
        print("Precio ingresado:", precio.input_value())

        log("12. VALIDANDO SUBTOTAL, IVA Y TOTAL")
        base = valor_float(fila.locator("input[id*='baseImponibleInputHidden']"))
        iva = valor_float(fila.locator("input[id*='valorImpuestoInputHidden']"))
        total_sin_iva = valor_float(fila.locator("input[id*='valorTotalInputHidden']"))
        total_con_iva = round(base + iva, 2)

        print("Base imponible:", base)
        print("IVA producto:", iva)
        print("Valor línea sin IVA:", total_sin_iva)
        print("TOTAL CALCULADO CON IVA:", total_con_iva)

        if round(base, 2) != round(float(CLIENTE["subtotal"]), 2):
            raise RuntimeError(f"Subtotal incorrecto: {base}")
        if round(iva, 2) != round(float(CLIENTE["iva"]), 2):
            raise RuntimeError(f"IVA incorrecto: {iva}")
        if round(total_sin_iva, 2) != round(float(CLIENTE["subtotal"]), 2):
            raise RuntimeError(f"Valor de línea sin IVA incorrecto: {total_sin_iva}")
        if total_con_iva != round(float(CLIENTE["total"]), 2):
            raise RuntimeError(f"Total con IVA incorrecto: {total_con_iva}")

        print("VALORES CORRECTOS: SUBTOTAL + IVA = TOTAL")
        screenshot(page, "08_valores_correctos.png")

        log("13. FORMA DE PAGO")
        boton_pago = buscar_boton_visible(page, "Añadir forma de pago")
        if boton_pago is None:
            raise RuntimeError("No se encontró Añadir forma de pago")
        boton_pago.click(force=True)
        page.wait_for_timeout(2000)

        seleccionar_option_por_texto(page, "#form\\:formaPagoComposite\\:selectFormaPago_input", CLIENTE["forma_pago"])
        valor_pago = page.locator("#form\\:formaPagoComposite\\:impValorPago")
        valor_pago.fill(f"{float(CLIENTE['forma_pago_valor']):.2f}")
        valor_pago.press("Tab")
        page.wait_for_timeout(1000)

        guardar = buscar_boton_visible(page, "Guardar")
        if guardar is not None:
            guardar.click(force=True)
            page.wait_for_timeout(3000)

        if round(float(CLIENTE["forma_pago_valor"]), 2) != round(float(CLIENTE["total"]), 2):
            raise RuntimeError("Control forma de pago vs total falló")

        print("Forma de pago configurada:", CLIENTE["forma_pago"])
        print("Valor forma de pago:", CLIENTE["forma_pago_valor"])
        print("CONTROL FORMA DE PAGO SUPERADO")

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
                if tag in ["INPUT", "TEXTAREA"] and "idNombreCampoAdcional" not in el_id and el.is_visible() and el.is_editable():
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

        log("15. CONTROLES PRE-FIRMA")
        texto = page.locator("body").inner_text()

        controles = {
            "producto": CLIENTE["producto"].upper() in texto.upper(),
            "informacion_adicional": detalle_mes.upper() in texto.upper(),
            "cliente": razon.strip() != "",
            "subtotal": round(base, 2) == round(float(CLIENTE["subtotal"]), 2),
            "iva": round(iva, 2) == round(float(CLIENTE["iva"]), 2),
            "total": total_con_iva == round(float(CLIENTE["total"]), 2),
            "forma_pago": round(float(CLIENTE["forma_pago_valor"]), 2) == round(float(CLIENTE["total"]), 2),
            "anti_duplicado": not (EMISIONES.get(CLAVE_PERIODO) and str(EMISIONES[CLAVE_PERIODO].get("estado", "")).upper() in {"AUTORIZADA", "ENVIADA", "EMITIDA"}),
        }

        for nombre, ok in controles.items():
            print(f"{nombre}: {'OK' if ok else 'ERROR'}")

        fallos = [nombre for nombre, ok in controles.items() if not ok]
        if fallos:
            raise RuntimeError("Controles pre-firma fallidos: " + ", ".join(fallos))

        screenshot(page, "11_controles_prefirma_ok.png")

        print("FACTURA PREPARADA CORRECTAMENTE")
        print("Cliente:", CLIENTE["razon_social"])
        print("Subtotal:", CLIENTE["subtotal"])
        print("IVA:", CLIENTE["iva"])
        print("Total:", CLIENTE["total"])
        print("Forma de pago:", CLIENTE["forma_pago"])
        print("Información adicional:", detalle_mes)
        print("Periodo anti-duplicado:", CLAVE_PERIODO)
        print("Modo actual:", MODO_ENVIO)

        log("CONTROLES PRE-FIRMA SUPERADOS")

        if MODO_ENVIO == "PRUEBA":
            print("MODO PRUEBA ACTIVO: no se firmará ni enviará ninguna factura.")
            print("Para producción se habilitará MODO_ENVIO=PRODUCCION cuando incorporemos la firma.")
        else:
            print("MODO PRODUCCION ACTIVO, pero la firma todavía no está habilitada en esta versión.")

    except Exception as e:
        screenshot(page, "99_error_final.png")
        print("\nERROR CONTROLADO:", str(e))
        raise
    finally:
        browser.close()
