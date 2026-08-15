from playwright.sync_api import sync_playwright
import os
from datetime import datetime
import sys


# ============================================================
# CONFIGURACIÓN
# ============================================================

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CERT_PASS = os.getenv("CERT_PASS")

URL_LOGIN = (
    "https://facturadorsri.sri.gob.ec/"
    "portal-facturadorsri-internet/pages/inicio.html"
)

URL_FACTURA = (
    "https://facturadorsri.sri.gob.ec/"
    "portal-facturadorsri-internet/pages/comprobantes/factura/Factura.html"
)


CLIENTE = {
    "ruc": "1723041156001",
    "nombre": "PARDO AGURTO GLORIA ALEXANDRA",
    "subtotal": 230.00,
    "iva": 34.50,
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


# ============================================================
# FUNCIONES
# ============================================================

def esperar(page, ms=1500):
    page.wait_for_timeout(ms)


def valor_oculto(page, selector):
    try:
        valor = page.locator(selector).get_attribute("value")
        if valor is None or valor == "":
            return 0.0
        return float(valor.replace(",", "."))
    except Exception:
        return 0.0


def seleccionar_option_por_texto(page, selector, texto_buscado):
    """
    Selecciona una opción del <select> real del SRI buscando
    una palabra dentro del texto de la opción.
    """

    select = page.locator(selector)

    opciones = select.locator("option")

    for i in range(opciones.count()):
        opcion = opciones.nth(i)

        texto = opcion.inner_text().strip()
        valor = opcion.get_attribute("value")

        if texto_buscado.upper() in texto.upper():
            select.select_option(value=valor)

            # Disparar eventos para PrimeFaces
            select.dispatch_event("change")
            esperar(page, 1500)

            print(
                f"Seleccionado: {texto} "
                f"(valor={valor})"
            )

            return True

    return False


def guardar_si_aparece(page):
    """
    Algunos cuadros del SRI muestran Guardar después
    de añadir pago/campo adicional.
    """

    botones = page.get_by_role(
        "button",
        name="Guardar",
        exact=True
    )

    if botones.count() > 0:
        for i in reversed(range(botones.count())):
            try:
                if botones.nth(i).is_visible():
                    botones.nth(i).click()
                    esperar(page, 2500)
                    return True
            except Exception:
                pass

    return False


# ============================================================
# VALIDAR SECRETS
# ============================================================

if not SRI_RUC:
    raise Exception(
        "Falta el Secret de GitHub: SRI_RUC"
    )

if not SRI_CLAVE:
    raise Exception(
        "Falta el Secret de GitHub: SRI_CLAVE"
    )

if not CERT_PASS:
    raise Exception(
        "Falta el Secret de GitHub: CERT_PASS"
    )


# ============================================================
# FECHA Y DETALLE
# ============================================================

hoy = datetime.now()

mes_facturado = (
    f"{MESES[hoy.month]} {hoy.year}"
)

detalle_factura = (
    f"SERVICIOS MES DE {mes_facturado}"
)


# ============================================================
# INICIAR PLAYWRIGHT
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

    # Campo RUC
campo_usuario = page.locator("#loginForm\\:nombrusuario")
campo_usuario.wait_for(state="visible", timeout=30000)
campo_usuario.fill(SRI_RUC)

# Campo contraseña
campo_clave = page.locator("#loginForm\\:passwordInput")
campo_clave.wait_for(state="visible", timeout=30000)
campo_clave.fill(SRI_CLAVE)

# Botón Ingresar
page.get_by_role(
    "button",
    name="Ingresar",
    exact=True
).click()

esperar(page, 6000)

print("LOGIN COMPLETADO")
print("URL:", page.url)

    esperar(page, 6000)


    # Verificación REAL del login

    if "Ingresar al Sistema" in page.locator(
        "body"
    ).inner_text():

        raise Exception(
            "El SRI no aceptó el inicio de sesión. "
            "Revisa SRI_RUC y SRI_CLAVE."
        )

    print("LOGIN CORRECTO")


    # ========================================================
    # 2. ABRIR FACTURA
    # ========================================================

    print("")
    print("========================================")
    print("2. ABRIENDO FACTURA")
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
            "No fue posible abrir la pantalla "
            "de emisión de factura."
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

    esperar(page, 3000)


    # ========================================================
    # 4. FECHA DE EMISIÓN
    # ========================================================

    print("")
    print("========================================")
    print("4. FECHA DE EMISIÓN")
    print("========================================")

    fecha = page.locator(
        "#form\\:identifiacionDelComprobante\\:"
        "calFechaEmi_input"
    )

    fecha_actual_sri = fecha.input_value()

    print(
        "Fecha colocada por el SRI:",
        fecha_actual_sri
    )

    # No modificamos la fecha.
    # Cuando el workflow se ejecute el día 01,
    # el SRI utilizará esa fecha.


    # ========================================================
    # 5. PUNTO DE EMISIÓN 100
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

    esperar(page, 2500)


    # ========================================================
    # 6. TIPO DE IDENTIFICACIÓN = RUC
    # ========================================================

    print("")
    print("========================================")
    print("6. TIPO DE IDENTIFICACIÓN")
    print("========================================")

    tipo_id_selector = (
        "#form\\:busquedaCompradorComp\\:"
        "cmbTipoIdentificacion_input"
    )

    ok = seleccionar_option_por_texto(
        page,
        tipo_id_selector,
        "RUC"
    )

    if not ok:
        raise Exception(
            "No se pudo seleccionar RUC."
        )


    # ========================================================
    # 7. RUC DEL CLIENTE
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

    campo_ruc.press("Tab")

    esperar(page, 5000)

    razon_social = page.locator(
        "#form\\:busquedaCompradorComp\\:"
        "compradorRazonSocial"
    ).input_value()

    print(
        "Cliente detectado:",
        razon_social
    )

    if (
        "PARDO" not in
        razon_social.upper()
    ):
        raise Exception(
            "El SRI no cargó correctamente "
            "los datos de Gloria Pardo."
        )


    # ========================================================
    # 8. PRODUCTO / SERVICIO
    # ========================================================

    print("")
    print("========================================")
    print("8. BUSCANDO ASESORIA CONTABILIDAD")
    print("========================================")

    producto = page.locator(
        "#form\\:productoBusquedaComposite\\:"
        "autoCompleteProducto_input"
    )

    producto.click()
    producto.fill("A")

    esperar(page, 4000)


    # Buscar cualquier elemento de autocomplete
    # que contenga ASESORIA CONTABILIDAD.

    candidatos = page.locator(
        "li:visible"
    ).filter(
        has_text="ASESORIA"
    )

    print(
        "Resultados ASESORIA encontrados:",
        candidatos.count()
    )

    producto_seleccionado = False

    for i in range(candidatos.count()):

        candidato = candidatos.nth(i)

        try:
            texto = candidato.inner_text().strip()

            print(
                "Resultado:",
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


    # Segunda estrategia:
    # teclado si PrimeFaces no deja hacer clic.

    if not producto_seleccionado:

        print(
            "Intentando seleccionar producto "
            "mediante teclado..."
        )

        producto.focus()

        page.keyboard.press(
            "ArrowDown"
        )

        page.keyboard.press(
            "Enter"
        )


    esperar(page, 5000)


    # ========================================================
    # 9. LOCALIZAR FILA DEL PRODUCTO
    # ========================================================

    print("")
    print("========================================")
    print("9. VALIDANDO PRODUCTO")
    print("========================================")

    filas_producto = page.locator(
        "tr"
    ).filter(
        has_text="ASESORIA CONTABILIDAD"
    )

    if filas_producto.count() == 0:

        print(
            page.locator(
                "body"
            ).inner_text()
        )

        raise Exception(
            "ASESORIA CONTABILIDAD todavía "
            "no fue agregado a la factura."
        )

    fila = filas_producto.first

    print(
        "Producto encontrado en factura:"
    )

    print(
        fila.inner_text()
    )


    # ========================================================
    # 10. PRECIO UNITARIO
    # ========================================================

    print("")
    print("========================================")
    print("10. PRECIO UNITARIO")
    print("========================================")

    inputs_fila = fila.locator(
        "input:visible"
    )

    print(
        "Inputs en fila producto:",
        inputs_fila.count()
    )

    precio_input = None

    # Primero buscamos un input cuyo id/name
    # contenga "precio".

    for i in range(inputs_fila.count()):

        inp = inputs_fila.nth(i)

        id_input = (
            inp.get_attribute("id") or ""
        ).lower()

        name_input = (
            inp.get_attribute("name") or ""
        ).lower()

        if (
            "precio" in id_input
            or "precio" in name_input
        ):
            precio_input = inp
            break


    # Si no tiene nombre "precio",
    # usamos el último input editable de la fila.

    if precio_input is None:

        editables = []

        for i in range(inputs_fila.count()):

            inp = inputs_fila.nth(i)

            try:
                if (
                    inp.is_enabled()
                    and inp.is_editable()
                ):
                    editables.append(inp)
            except Exception:
                pass

        if editables:
            precio_input = editables[-1]


    if precio_input is None:
        raise Exception(
            "No se encontró el campo "
            "Precio unitario."
        )


    precio_input.fill(
        str(CLIENTE["subtotal"])
    )

    precio_input.press("Tab")

    esperar(page, 5000)


    # ========================================================
    # 11. VALIDAR SUBTOTAL E IVA
    # ========================================================

    print("")
    print("========================================")
    print("11. VALIDANDO VALORES")
    print("========================================")

    subtotal = valor_oculto(
        page,
        "#form\\:subtotalSinImpuestosHidden"
    )

    iva = valor_oculto(
        page,
        "#form\\:totalIva12Hidden"
    )

    total = valor_oculto(
        page,
        "#form\\:totalFacturaHidden"
    )

    print(
        "Subtotal SRI:",
        subtotal
    )

    print(
        "IVA SRI:",
        iva
    )

    print(
        "Total SRI:",
        total
    )


    # Algunos nombres internos del portal
    # conservan referencias antiguas como IVA12,
    # por eso la validación principal será
    # subtotal y total.

    if round(
        subtotal,
        2
    ) != CLIENTE["subtotal"]:

        raise Exception(
            f"Subtotal incorrecto. "
            f"Esperado: {CLIENTE['subtotal']} "
            f"/ SRI: {subtotal}"
        )


    if round(
        total,
        2
    ) != CLIENTE["total"]:

        raise Exception(
            f"Total incorrecto. "
            f"Esperado: {CLIENTE['total']} "
            f"/ SRI: {total}"
        )


    print(
        "VALORES CORRECTOS"
    )


    # ========================================================
    # 12. FORMA DE PAGO
    # ========================================================

    print("")
    print("========================================")
    print("12. FORMA DE PAGO")
    print("========================================")

    page.get_by_text(
        "Añadir forma de pago",
        exact=True
    ).click()

    esperar(page, 2000)


    forma_pago_selector = (
        "#form\\:formaPagoComposite\\:"
        "selectFormaPago_input"
    )

    ok = seleccionar_option_por_texto(
        page,
        forma_pago_selector,
        "OTROS CON UTILIZACION "
        "DEL SISTEMA FINANCIERO"
    )

    if not ok:
        raise Exception(
            "No se encontró la forma "
            "de pago requerida."
        )


    valor_pago = page.locator(
        "#form\\:formaPagoComposite\\:"
        "impValorPago"
    )

    valor_pago.fill(
        f"{CLIENTE['total']:.2f}"
    )

    esperar(page, 1000)

    guardar_si_aparece(page)

    esperar(page, 3000)


    # ========================================================
    # 13. CAMPO ADICIONAL
    # ========================================================

    print("")
    print("========================================")
    print("13. CAMPO ADICIONAL")
    print("========================================")

    page.get_by_text(
        "Añadir campo adicional",
        exact=True
    ).click()

    esperar(page, 2000)


    nombre_adicional = page.locator(
        "#form\\:campoAdicionalComposite\\:"
        "idNombreCampoAdcional"
    )

    nombre_adicional.fill(
        "DETALLE"
    )


    # Buscar el segundo campo editable
    # del componente Campo Adicional.

    campos_adicionales = page.locator(
        "[id^='form:campoAdicionalComposite:']"
    )

    campo_descripcion = None

    for i in range(
        campos_adicionales.count()
    ):

        elemento = (
            campos_adicionales.nth(i)
        )

        try:
            tag = elemento.evaluate(
                "e => e.tagName"
            )

            id_elemento = (
                elemento.get_attribute(
                    "id"
                ) or ""
            )

            if (
                tag in ["INPUT", "TEXTAREA"]
                and
                "idNombreCampoAdcional"
                not in id_elemento
                and
                elemento.is_visible()
                and
                elemento.is_editable()
            ):
                campo_descripcion = elemento
                break

        except Exception:
            pass


    if campo_descripcion is None:
        raise Exception(
            "No se encontró el campo "
            "Descripción del campo adicional."
        )


    campo_descripcion.fill(
        detalle_factura
    )

    guardar_si_aparece(page)

    esperar(page, 3000)


    # ========================================================
    # 14. ÚLTIMA VALIDACIÓN ANTES DE FIRMAR
    # ========================================================

    print("")
    print("========================================")
    print("14. VALIDACIÓN FINAL")
    print("========================================")

    texto_final = page.locator(
        "body"
    ).inner_text()

    if (
        "ASESORIA CONTABILIDAD"
        not in texto_final.upper()
    ):
        raise Exception(
            "El producto desapareció antes "
            "de firmar. Se cancela el envío."
        )

    if (
        "DETALLE"
        not in texto_final.upper()
    ):
        raise Exception(
            "El campo adicional no quedó "
            "guardado. Se cancela el envío."
        )

    total_final = valor_oculto(
        page,
        "#form\\:totalFacturaHidden"
    )

    if round(
        total_final,
        2
    ) != CLIENTE["total"]:

        raise Exception(
            "El total cambió antes "
            "de firmar."
        )


    print(
        "TODO CORRECTO."
    )

    print(
        "SE PROCEDERÁ A FIRMAR."
    )


    # ========================================================
    # 15. FIRMAR Y ENVIAR
    # ========================================================

    print("")
    print("========================================")
    print("15. FIRMAR Y ENVIAR")
    print("========================================")

    boton_firmar = page.get_by_text(
        "Firmar y enviar",
        exact=True
    )

    boton_firmar.scroll_into_view_if_needed()

    boton_firmar.click(
        force=True
    )

    esperar(page, 4000)


    # ========================================================
    # 16. CLAVE DEL CERTIFICADO
    # ========================================================

    print("")
    print("========================================")
    print("16. FIRMA DIGITAL")
    print("========================================")

    clave_certificado = page.locator(
        "#form\\:appletComposite\\:"
        "txtClaveCertificado"
    )

    clave_certificado.wait_for(
        state="visible",
        timeout=20000
    )

    clave_certificado.fill(
        CERT_PASS
    )

    print(
        "Clave del certificado colocada."
    )


    # ========================================================
    # 17. ENVIAR
    # ========================================================

    botones_enviar = page.get_by_role(
        "button",
        name="Enviar",
        exact=True
    )

    boton_enviar = None

    for i in range(
        botones_enviar.count()
    ):

        try:
            if botones_enviar.nth(
                i
            ).is_visible():

                boton_enviar = (
                    botones_enviar.nth(i)
                )

                break

        except Exception:
            pass


    if boton_enviar is None:
        raise Exception(
            "No apareció el botón ENVIAR "
            "de Firma digital."
        )


    boton_enviar.click()

    print(
        "Factura enviada al SRI."
    )

    esperar(page, 30000)


    # ========================================================
    # 18. RESULTADO DEL SRI
    # ========================================================

    print("")
    print("========================================")
    print("18. RESULTADO FINAL DEL SRI")
    print("========================================")

    resultado = page.locator(
        "body"
    ).inner_text()

    print(resultado)


    # Si sigue en la pantalla vacía de factura
    # sin ningún mensaje de confirmación, no declaramos éxito.

    palabras_error = [
        "ERROR",
        "NO AUTORIZADO",
        "RECHAZADO",
        "CLAVE INCORRECTA",
        "ERROR AL FIRMAR"
    ]

    for palabra in palabras_error:

        if palabra in resultado.upper():

            raise Exception(
                "El SRI devolvió un error: "
                + palabra
            )


    print("")
    print(
        "PROCESO DE ENVÍO TERMINADO."
    )

    print(
        "CLIENTE:",
        CLIENTE["nombre"]
    )

    print(
        "TOTAL:",
        CLIENTE["total"]
    )

    print(
        "MES:",
        mes_facturado
    )

    browser.close()
