from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SRI_RUC = os.getenv("SRI_RUC")
SRI_CLAVE = os.getenv("SRI_CLAVE")
CLIENTE_ID = os.getenv("CLIENTE_ID", "gloria_pardo")

WA_TOKEN = os.getenv("META_WHATSAPP_TOKEN")
WA_PHONE_NUMBER_ID = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
WA_DESTINO = os.getenv("META_WHATSAPP_DESTINO")
WA_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v23.0")

URL_LOGIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/inicio.html"
URL_ADMIN = "https://facturadorsri.sri.gob.ec/portal-facturadorsri-internet/pages/consultas/consultaComprobantesElectronicos.html"

DEBUG_DIR = Path("debug_whatsapp")
DEBUG_DIR.mkdir(exist_ok=True)
PDF_DIR = Path("facturas")
PDF_DIR.mkdir(exist_ok=True)

MESES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def log(titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)


def screenshot(page, nombre):
    try:
        page.screenshot(path=str(DEBUG_DIR / nombre), full_page=True)
    except Exception as e:
        print(f"No se pudo guardar captura {nombre}: {e}")


def cargar_emision():
    emisiones_path = Path("emisiones.json")
    if not emisiones_path.exists():
        raise RuntimeError("No existe emisiones.json")

    with emisiones_path.open("r", encoding="utf-8") as f:
        emisiones = json.load(f)

    candidatas = []
    for clave, datos in emisiones.items():
        if datos.get("cliente_id") == CLIENTE_ID and str(datos.get("estado", "")).upper() == "AUTORIZADA":
            candidatas.append((clave, datos))

    if not candidatas:
        raise RuntimeError(f"No existe una factura AUTORIZADA para {CLIENTE_ID}")

    candidatas.sort(key=lambda x: x[1].get("fecha_ejecucion", ""), reverse=True)
    clave, datos = candidatas[0]

    respuesta = datos.get("respuesta_sri", "")
    m_auth = re.search(r"Número de autorización:\s*([0-9*]+)", respuesta, re.I)
    m_comp = re.search(r"Número de comprobante:\s*([0-9-]+)", respuesta, re.I)

    autorizacion = m_auth.group(1).replace("*", "") if m_auth else ""
    comprobante = m_comp.group(1) if m_comp else ""

    if not autorizacion and not comprobante:
        raise RuntimeError("No se pudo extraer autorización ni número de comprobante de emisiones.json")

    return clave, datos, autorizacion, comprobante


def validar_configuracion():
    faltan = []
    for nombre, valor in [
        ("SRI_RUC", SRI_RUC),
        ("SRI_CLAVE", SRI_CLAVE),
        ("META_WHATSAPP_TOKEN", WA_TOKEN),
        ("META_WHATSAPP_PHONE_NUMBER_ID", WA_PHONE_NUMBER_ID),
        ("META_WHATSAPP_DESTINO", WA_DESTINO),
    ]:
        if not valor:
            faltan.append(nombre)

    if faltan:
        raise RuntimeError("Faltan Secrets para WhatsApp: " + ", ".join(faltan))

    destino = re.sub(r"\D", "", WA_DESTINO)
    if not destino.startswith("593"):
        raise RuntimeError("META_WHATSAPP_DESTINO debe estar en formato internacional Ecuador, por ejemplo 59399XXXXXXX")


def buscar_boton_visible(page, texto):
    for grupo in [page.get_by_role("button", name=texto, exact=True), page.get_by_text(texto, exact=True)]:
        for i in range(grupo.count()):
            try:
                if grupo.nth(i).is_visible():
                    return grupo.nth(i)
            except Exception:
                pass
    return None


def descargar_ride(page, browser_context, datos, autorizacion, comprobante):
    log("3. DESCARGANDO RIDE")

    page.goto(URL_ADMIN, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    if "Ingresar al Sistema" in page.locator("body").inner_text():
        raise RuntimeError("La sesión del SRI se perdió al abrir Administración")

    boton_buscar = buscar_boton_visible(page, "Buscar")
    if boton_buscar is None:
        screenshot(page, "03_sin_boton_buscar.png")
        raise RuntimeError("No se encontró el botón Buscar en Administración")

    boton_buscar.click(force=True)
    page.wait_for_timeout(5000)
    screenshot(page, "04_resultados_administracion.png")

    filas = page.locator("tr")
    fila_objetivo = None
    for i in range(filas.count()):
        fila = filas.nth(i)
        try:
            texto = fila.inner_text().strip()
            if (comprobante and comprobante in texto) or (autorizacion and autorizacion in texto) or datos.get("ruc", "") in texto:
                if "Factura" in texto:
                    fila_objetivo = fila
                    print("Factura encontrada en Administración:", texto.replace("\n", " | "))
                    break
        except Exception:
            pass

    if fila_objetivo is None:
        screenshot(page, "05_factura_no_encontrada.png")
        raise RuntimeError("No se encontró la factura autorizada en Administración del SRI")

    botones = fila_objetivo.locator("button")
    if botones.count() == 0:
        screenshot(page, "06_sin_acciones.png")
        raise RuntimeError("La fila de la factura no contiene botón de acciones")

    paginas_antes = len(browser_context.pages)
    descargas = []
    page.on("download", lambda d: descargas.append(d))

    botones.last.click(force=True)
    page.wait_for_timeout(1000)

    ride = None
    candidatos = page.get_by_text("Ver RIDE", exact=True)
    for i in range(candidatos.count()):
        try:
            if candidatos.nth(i).is_visible():
                ride = candidatos.nth(i)
                break
        except Exception:
            pass

    if ride is None:
        screenshot(page, "07_menu_sin_ride.png")
        raise RuntimeError("No apareció la opción Ver RIDE")

    nombre_pdf = f"Factura_{comprobante or CLIENTE_ID}.pdf".replace("/", "-")
    destino_pdf = PDF_DIR / nombre_pdf

    ride.click(force=True)
    page.wait_for_timeout(8000)

    if descargas:
        descargas[-1].save_as(str(destino_pdf))
        print("RIDE descargado:", destino_pdf)
        return destino_pdf

    paginas_nuevas = browser_context.pages[paginas_antes:]
    if paginas_nuevas:
        popup = paginas_nuevas[-1]
        try:
            popup.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

        url_pdf = popup.url
        print("Ventana RIDE URL:", url_pdf)

        if url_pdf.startswith("http"):
            respuesta = browser_context.request.get(url_pdf, timeout=30000)
            content_type = (respuesta.headers.get("content-type") or "").lower()
            if respuesta.ok and ("pdf" in content_type or respuesta.body().startswith(b"%PDF")):
                destino_pdf.write_bytes(respuesta.body())
                print("RIDE descargado desde ventana:", destino_pdf)
                return destino_pdf

        try:
            popup.pdf(path=str(destino_pdf), format="A4", print_background=True)
            if destino_pdf.exists() and destino_pdf.stat().st_size > 1000:
                print("RIDE guardado como PDF desde ventana:", destino_pdf)
                return destino_pdf
        except Exception:
            pass

    screenshot(page, "08_ride_no_descargado.png")
    raise RuntimeError("El SRI mostró Ver RIDE, pero no se pudo obtener el PDF")


def enviar_whatsapp_pdf(pdf_path, datos):
    log("4. ENVIANDO A WHATSAPP PERSONAL")

    destino = re.sub(r"\D", "", WA_DESTINO)
    periodo = datos.get("periodo", "")
    anio, mes = periodo.split("-")
    texto_mes = f"{MESES[int(mes)]} {anio}"
    mensaje = f"Buenos días, adjunto factura correspondiente a servicios mes de {texto_mes}. Gracias."

    base_url = f"https://graph.facebook.com/{WA_GRAPH_VERSION}/{WA_PHONE_NUMBER_ID}"
    headers = {"Authorization": f"Bearer {WA_TOKEN}"}

    with pdf_path.open("rb") as archivo:
        resp_media = requests.post(
            f"{base_url}/media",
            headers=headers,
            data={"messaging_product": "whatsapp", "type": "application/pdf"},
            files={"file": (pdf_path.name, archivo, "application/pdf")},
            timeout=60,
        )

    if not resp_media.ok:
        raise RuntimeError(f"Meta rechazó la carga del PDF: {resp_media.status_code} {resp_media.text[:1000]}")

    media_id = resp_media.json().get("id")
    if not media_id:
        raise RuntimeError("Meta no devolvió media_id para el PDF")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": destino,
        "type": "document",
        "document": {
            "id": media_id,
            "caption": mensaje,
            "filename": pdf_path.name,
        },
    }

    resp_msg = requests.post(
        f"{base_url}/messages",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if not resp_msg.ok:
        raise RuntimeError(f"Meta rechazó el mensaje de WhatsApp: {resp_msg.status_code} {resp_msg.text[:1200]}")

    respuesta = resp_msg.json()
    mensajes = respuesta.get("messages") or []
    wamid = mensajes[0].get("id") if mensajes else None
    print("WHATSAPP ENVIADO CORRECTAMENTE")
    print("Destino:", destino)
    print("Mensaje:", mensaje)
    print("WhatsApp message id:", wamid)
    return wamid


def main():
    validar_configuracion()
    clave, datos, autorizacion, comprobante = cargar_emision()

    log("FACTURA AUTORIZADA SELECCIONADA")
    print("Registro:", clave)
    print("Cliente:", datos.get("razon_social"))
    print("Comprobante:", comprobante)
    print("Autorización:", autorizacion)
    print("Total:", datos.get("total"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, accept_downloads=True)
        context = browser.new_context(accept_downloads=True, viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            log("1. INGRESANDO AL SRI")
            page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            page.locator('input[type="text"]:visible').first.fill(SRI_RUC)
            page.locator('input[type="password"]:visible').first.fill(SRI_CLAVE)
            page.get_by_role("button", name="Ingresar", exact=True).click()
            page.wait_for_timeout(5000)

            if "Ingresar al Sistema" in page.locator("body").inner_text():
                raise RuntimeError("El SRI no aceptó el inicio de sesión")

            print("LOGIN CORRECTO")
            pdf_path = descargar_ride(page, context, datos, autorizacion, comprobante)
        except Exception:
            screenshot(page, "99_error_whatsapp.png")
            raise
        finally:
            browser.close()

    wamid = enviar_whatsapp_pdf(pdf_path, datos)

    log("PROCESO WHATSAPP COMPLETADO")
    print("Factura:", pdf_path.name)
    print("WhatsApp ID:", wamid)


if __name__ == "__main__":
    main()
