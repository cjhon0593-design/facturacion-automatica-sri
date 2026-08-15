from playwright.sync_api import sync_playwright
import os
from datetime import datetime


# ============================================================
# CONFIGURACIÓN
# ============================================================

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"

URL_FACTURA = (
    "https://facturadorsri.sri.gob.ec/"
    "portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"
)

CLIENTE = {
    "ruc": "1723041156001",
    "nombre": "PARDO AGURTO GLORIA ALEXANDRA",
    "subtotal": 230.00,
    "total": 264.50,
}

MESES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


def esperar(page, ms=1500):
    page.wait_for_timeout(ms)


def seleccionar_option_por_texto(page, selector, texto_buscado):
    select = page.locator(selector)

    select.wait_for(
        state="attached",
        timeout=30000
    )

    opciones = select.locator("option")

    for i in range(opciones.count()):
        opcion = opciones.nth(i)

        texto = opcion.inner_text().strip()
        valor = opcion.get_attribute("value")

        if texto_buscado.upper() in texto.upper():
            select.select_option(value=valor)
            select.dispatch_event("change")
            esperar(page, 1500)

            print(
                f"Seleccionado: {texto} | valor={valor}"
            )

            return True

    return False


# ============================================================
# VALIDAR VARIABLES
# ============================================================

if not SRI_RUC:
    raise Exception("Falta el Secret SRI_RUC")

if not SRI_CLAVE:
    raise Exception("Falta el Secret SRI_CLAVE")

if not CERT_PASS:
    raise Exception("Falta el Secret CERT_PASS")


hoy = datetime.now()

mes_facturado = (
    f"{MESES[hoy.month]} {hoy.year}"
)

detalle_factura = (
    f"SERVICIOS MES DE {mes_facturado}"
)


# ============================================================
# EJECUCIÓN
# ============================================================

with sync_playwright() as p:

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={
            "width": 1920,
            "height": 1080
        }
    )

    page.set_default_timeout(30000)

    # ========================================================
    # 1. LOGIN
    # ========================================================

    print("")
    print("========================================")
    print("1. INICIANDO SESIÓN EN EL SRI")
    print("========================================")

    page.goto(
        URL_LOGIN,
        wait_until="networkidle",
        timeout=60000
    )

    campo_usuario = page.locator(
        "#loginForm\\:nombrusuario"
    )

    campo_usuario.wait_for(
        state="visible",
        timeout=30000
    )

    campo_usuario.fill(
        SRI_RUC
    )

    campo_clave = page.locator(
        "#loginForm\\:passwordInput"
    )

    campo_clave.wait_for(
        state="visible",
        timeout=30000
    )

    campo_clave.fill(
        SRI_CLAVE
    )

    page.get_by_role(
        "button",
        name="Ingresar",
        exact=True
    ).click()

    esperar(page, 6000)

    print("LOGIN COMPLETADO")
    print("URL:", page.url)

    cuerpo_login = page.locator(
        "body"
    ).inner_text()

    if "Ingresar al Sistema" in cuerpo_login:
        raise Exception(
            "El SRI no aceptó el inicio de sesión."
        )

    # ========================================================
    # 2. ABRIR FACTURA
    # ========================================================

    print("")
    print("========================================")
    print("2. ABRIENDO PANTALLA DE FACTURA")
    print("========================================")

    page.goto(
        URL_FACTURA,
        wait_until="networkidle",
        timeout=60000
    )

    esperar(page, 5000)

    cuerpo = page.locator(
        "body"
    ).inner_text()

    if "Emisión - Factura" not in cuerpo:
        raise Exception(
            "No se pudo abrir la pantalla de factura."
        )

    print("PANTALLA DE FACTURA CORRECTA")

    # ========================================================
    # 3. ESTABLECIMIENTO
    # ========================================================

    print("")
    print("========================================")
    print("3. ESTABLECIMIENTO")
    print("========================================")

    establecimiento_selector = (
        "#form\\:cabeceraComprobanteDlg\\:"
        "j_idt61_input"
    )

    ok = seleccionar_option_por_texto(
        page,
        establecimiento_selector,
        "001 - AV ELOY ALFARO"
    )

    if not ok:
        raise Exception(
            "No se encontró el establecimiento 001."
        )

    esperar(page, 2500)

    # ========================================================
    # 4. FECHA
    # ========================================================

    print("")
    print("========================================")
    print("4. FECHA DE EMISIÓN")
    print("========================================")

    fecha = page.locator(
        "#form\\:identifiacionDelComprobante\\:"
        "calFechaEmi_input"
    )

    print(
        "Fecha SRI:",
        fecha.input_value()
    )

    # ========================================================
    # 5. PUNTO DE EMISIÓN
    # ========================================================

    print("")
    print("========================================")
    print("5. PUNTO DE EMISIÓN")
    print("========================================")

    punto_selector = (
        "#form\\:identifiacionDelComprobante\\:"
        "selectsecuencial_input"
    )

    ok = seleccionar_option_por_texto(
        page,
        punto_selector,
        "100"
    )

    if not ok:
        raise Exception(
            "No se encontró el punto de emisión 100."
        )

    esperar(page, 2000)

    # ========================================================
    # 6. TIPO IDENTIFICACIÓN
    # ========================================================

    print("")
    print("========================================")
    print("6. TIPO IDENTIFICACIÓN")
    print("========================================")

    tipo_selector = (
        "#form\\:busquedaCompradorComp\\:"
        "cmbTipoIdentificacion_input"
    )

    ok = seleccionar_option_por_texto(
        page,
        tipo_selector,
        "RUC"
    )

    if not ok:
        raise Exception(
            "No se pudo seleccionar RUC."
        )

    # ========================================================
    # 7. CLIENTE
    # ========================================================

    print("")
    print("========================================")
    print("7. CLIENTE")
    print("========================================")

    campo_ruc = page.locator(
        "#form\\:busquedaCompradorComp\\:ruc"
    )

    campo_ruc.fill(
        CLIENTE["ruc"]
    )

    campo_ruc.press(
        "Tab"
    )

    esperar(page, 5000)

    razon_social = page.locator(
        "#form\\:busquedaCompradorComp\\:"
        "compradorRazonSocial"
    ).input_value()

    print(
        "Cliente detectado:",
        razon_social
    )

    if "PARDO" not in razon_social.upper():
        raise Exception(
            "No se cargó correctamente el cliente."
        )

    # ========================================================
    # 8. PRODUCTO
    # ========================================================

    print("")
    print("========================================")
    print("8. PRODUCTO")
    print("========================================")

    producto = page.locator(
        "#form\\:productoBusquedaComposite\\:"
        "autoCompleteProducto_input"
    )

    producto.click()
    producto.fill("A")

    esperar(page, 4000)

    candidatos = page.locator(
        "li:visible"
    ).filter(
        has_text="ASESORIA"
    )

    print(
        "Resultados encontrados:",
        candidatos.count()
    )

    producto_seleccionado = False

    for i in range(candidatos.count()):

        candidato = candidatos.nth(i)

        try:
            texto = candidato.inner_text().strip()

            print(
                "Opción:",
                texto
            )

            if (
                "ASESORIA CONTABILIDAD"
                in texto.upper()
            ):
                candidato.click(
                    force=True
                )

                producto_seleccionado = True
                break

        except Exception:
            pass

    if not producto_seleccionado:
        producto.focus()
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")

    esperar(page, 5000)

    # ========================================================
    # 9. VALIDAR PRODUCTO
    # ========================================================

    print("")
    print("========================================")
    print("9. VALIDANDO PRODUCTO")
    print("========================================")

    filas = page.locator(
        "tr"
    ).filter(
        has_text="ASESORIA CONTABILIDAD"
    )

    if filas.count() == 0:
        print(
            page.locator(
                "body"
            ).inner_text()
        )

        raise Exception(
            "ASESORIA CONTABILIDAD no fue agregado."
        )

    fila = filas.first

    print(
        "Producto agregado:"
    )

    print(
        fila.inner_text()
    )

    # ========================================================
    # 10. MOSTRAR CAMPOS DEL PRODUCTO
    # ========================================================

    print("")
    print("========================================")
    print("10. CAMPOS DEL PRODUCTO")
    print("========================================")

    inputs_producto = fila.locator(
        "input"
    )

    for i in range(
        inputs_producto.count()
    ):

        inp = inputs_producto.nth(i)

        try:
            print(
                i,
                "| ID:",
                inp.get_attribute("id"),
                "| NAME:",
                inp.get_attribute("name"),
                "| VALUE:",
                inp.get_attribute("value"),
                "| TYPE:",
                inp.get_attribute("type")
            )

        except Exception:
            pass

    print("")
    print("========================================")
    print("PRUEBA TERMINADA HASTA PRODUCTO")
    print("========================================")

    browser.close()
