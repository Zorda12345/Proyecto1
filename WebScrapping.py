from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse  # Para codificar correctamente el término de búsqueda

# Pedir al usuario el término de búsqueda
termino_busqueda = input("¿Qué producto deseas buscar en Amazon y MediaMarkt?: ")
termino_codificado_amazon = urllib.parse.quote_plus(termino_busqueda) #quote plus transforma lo que escribes en lenguaje html , _ -> +
termino_codificado_mediamarkt = urllib.parse.quote_plus(termino_busqueda) 

# Configurar Chrome
options = Options()
options.add_argument("--headless")  # Quita comentario si no quieres ver el navegador
options.add_argument("--no-sandbox") # (Contenedres,CI)
options.add_argument("--disable-dev-shm-usage") 

service = Service()
driver = webdriver.Chrome(service=service, options=options)

# =========================
#  FUNCIONES AUXILIARES (MEDIAMARKT)
# =========================

def aceptar_cookies_mm(driver, timeout=6): #Las cookies nos suelen tocar los cojones, las aceptamos para que nos dejen buscar con libertad
    """Intenta aceptar el banner de cookies de MediaMarkt si aparece."""
    try:
        posibles_botones = [
            (By.XPATH, "//button[contains(., 'Aceptar') or contains(., 'ACEPTAR') or contains(., 'Aceptar todo') or contains(., 'Aceptar todas')]"),
            (By.XPATH, "//button[@id='privacy-accept-button']"),
            (By.XPATH, "//div[contains(@class,'cookie') or contains(@id,'cookie')]//button")
        ]
        fin = time.time() + timeout
        while time.time() < fin:
            for by, xp in posibles_botones:
                try:
                    btn = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((by, xp))) #webdriverWait sirve para hacer click al boton
                    btn.click()
                    return
                except:
                    pass
            time.sleep(0.5)
    except:
        pass

def _normaliza_precio(txt: str) -> str:
    return (txt or "").replace("\xa0", " ").replace("&nbsp;", " ").strip() #Los precios tienen el mismo problema que amazon que sale el &nbs, lo que hace la funcion es reemplazarlo y reescribirlo

def extraer_precios_mediamarkt(price_box):
    """
    Devuelve (precio_actual, precio_original, hay_oferta) a partir del contenedor
    <div data-test="mms-price">…</div>
    - Si hay oferta: precio_actual = rebajado, precio_original = tachado.
    - Si no hay oferta: ambos iguales al único precio mostrado.
    """
    #(precio original)
    strike_blocks = price_box.find_elements(
        By.XPATH, ".//div[starts-with(@data-test,'mms-strike-price-type')]"
    )

    def _primer_span_con_euro(scope): #Para buscar el precio, Separamos al estar precio tachado y precio oferta
        spans = scope.find_elements(By.XPATH, ".//span[contains(normalize-space(.),'€') or contains(., '€')]")
        for sp in spans:
            txt = _normaliza_precio(sp.text)
            if "€" in txt and txt:
                return txt
        # Fallback: algunos precios duplican valor en aria-hidden
        spans = scope.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
        for sp in spans:
            txt = _normaliza_precio(sp.text)
            if "€" in txt and txt:
                return txt
        return ""

    if strike_blocks: #Comprueba si existen dos bloques (oferta y original)
        # Hay oferta: extraer original (tachado) y actual (rojo)
        precio_original = _primer_span_con_euro(strike_blocks[0]) or "Precio no disponible"
        candidatos_actual = price_box.find_elements(
            By.XPATH, ".//span[contains(., '€')][not(ancestor::div[starts-with(@data-test,'mms-strike-price-type')])]"
        )
        precio_actual = ""
        for sp in candidatos_actual:
            txt = _normaliza_precio(sp.text)
            if "€" in txt and txt:
                precio_actual = txt
                break
        if not precio_actual: #En caso no de encontrar ninguno...
            precio_actual = _primer_span_con_euro(price_box) or "Precio no disponible"
        return (precio_actual, precio_original, True)
    else:
        unico = _primer_span_con_euro(price_box) or "Precio no disponible"
        return (unico, unico, False)

# =========================
#  AMAZON
# =========================
def scrape_amazon():
    url = f"https://www.amazon.es/s?k={termino_codificado_amazon}"
    driver.get(url)
    time.sleep(1)  

    productos = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
    encontrados = 0
    print(f"\nPrimeras 3 búsquedas de Amazon para '{termino_busqueda}':")
    with open("productos.txt", "w", encoding="utf-8") as f:
        f.write(f"Amazon\n") #Escribimos en la notita
        print(url)
        for producto in productos: #Recorremos 3 primeros productos
            if encontrados >= 3:
                break
            try:
                ##Nombre
                nombre = producto.find_element(By.XPATH, ".//h2//span").text.strip()
            
                ##Precio
                try:
                    precio_element = producto.find_element(By.XPATH, ".//span[@class='a-price']")
                    precio = precio_element.find_element(By.XPATH, ".//span[@class='a-offscreen']").get_attribute("innerHTML").replace("&nbsp;", " ").strip()
                except: #En caso que no se encuentre el precio se crea uno por uno
                    try:
                        parte_entera = producto.find_element(By.XPATH, ".//span[@class='a-price-whole']").text.strip()
                        parte_decimal = producto.find_element(By.XPATH, ".//span[@class='a-price-fraction']").text.strip()
                        simbolo = producto.find_element(By.XPATH, ".//span[@class='a-price-symbol']").text.strip()
                        simbolo_limpio = simbolo.replace("&nbsp;", " ")
                        precio = f"{simbolo}{parte_entera},{parte_decimal}"
                    except:
                        precio = "Precio no disponible"
                
                print(f"{nombre} -> {precio}")
                f.write(f"{nombre} -> {precio}\n")
                encontrados += 1
            except Exception as e:
                print(f"Error procesando producto: {str(e)}")
                continue

# =========================
#  MEDIAMARKT (CON OFERTAS)
# =========================
def scrape_mediamarkt():
    url = f"https://www.mediamarkt.es/es/search.html?query={termino_codificado_mediamarkt}"
    driver.get(url)

    # Aceptar cookies si bloquean
    aceptar_cookies_mm(driver)

    try:
        # Espera a que aparezcan títulos de productos (selector estable)
        titulos = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//p[@data-test='product-title']"))
        )
    except Exception as e:
        print("No se encontraron productos en MediaMarkt (títulos).")
        print("Detalle:", repr(e))
        return

    print(f"\nPrimeras 3 búsquedas de MediaMarkt para '{termino_busqueda}':")
    with open("productos.txt", "a", encoding="utf-8") as f:
        f.write("\nMediaMarkt\n")

        # Tomamos los 3 primeros títulos y desde ahí localizamos el precio
        for titulo_el in titulos[:3]:
            try:
                nombre = titulo_el.text.strip()

                # Subir al contenedor de la tarjeta que contenga el bloque de precio
                try:
                    card = titulo_el.find_element(
                        By.XPATH,
                        "./ancestor::*[.//div[@data-test='mms-price']][1]"
                    )
                except:
                    card = titulo_el.find_element(By.XPATH, "./ancestor::*[1]")

                # Precio dentro del contenedor de precio (manejo de oferta u original)
                try:
                    price_box = card.find_element(By.XPATH, ".//div[@data-test='mms-price']")
                    precio_actual, precio_original, hay_oferta = extraer_precios_mediamarkt(price_box)
                except:
                    precio_actual, precio_original, hay_oferta = ("Precio no disponible", "Precio no disponible", False)

                # Mostrar/guardar según haya oferta
                if hay_oferta:
                    print(f"{nombre} -> {precio_actual} (antes: {precio_original})")
                    f.write(f"{nombre} -> {precio_actual} (antes: {precio_original})\n")
                else:
                    print(f"{nombre} -> {precio_original}")
                    f.write(f"{nombre} -> {precio_original}\n")

            except Exception as e:
                print("Error en MediaMarkt:", repr(e))
                continue

# Ejecutar ambas funciones
scrape_amazon()
scrape_mediamarkt()

driver.quit()
