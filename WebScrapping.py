from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse

# =========================
#  FUNCIONES AUXILIARES (MEDIAMARKT)
# =========================

def aceptar_cookies_mm(driver, timeout=6):
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
                    btn = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((by, xp)))
                    btn.click()
                    return
                except:
                    pass
            time.sleep(0.5)
    except:
        pass

def _normaliza_precio(txt: str) -> str:
    return (txt or "").replace("\xa0", " ").replace("&nbsp;", " ").strip()

def extraer_precios_mediamarkt(price_box):
    strike_blocks = price_box.find_elements(
        By.XPATH, ".//div[starts-with(@data-test,'mms-strike-price-type')]"
    )

    def _primer_span_con_euro(scope):
        spans = scope.find_elements(By.XPATH, ".//span[contains(normalize-space(.),'€') or contains(., '€')]")
        for sp in spans:
            txt = _normaliza_precio(sp.text)
            if "€" in txt and txt:
                return txt
        spans = scope.find_elements(By.XPATH, ".//span[@aria-hidden='true']")
        for sp in spans:
            txt = _normaliza_precio(sp.text)
            if "€" in txt and txt:
                return txt
        return ""

    if strike_blocks:
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
        if not precio_actual:
            precio_actual = _primer_span_con_euro(price_box) or "Precio no disponible"
        return (precio_actual, precio_original, True)
    else:
        unico = _primer_span_con_euro(price_box) or "Precio no disponible"
        return (unico, unico, False)

# =========================
#  AMAZON
# =========================
def scrape_amazon(driver, termino_busqueda):
    termino_codificado_amazon = urllib.parse.quote_plus(termino_busqueda)
    url = f"https://www.amazon.es/s?k={termino_codificado_amazon}"
    driver.get(url)
    time.sleep(1)

    productos = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
    encontrados = 0
    print(f"\nPrimeras 3 búsquedas de Amazon para '{termino_busqueda}':")
    with open("productos.txt", "w", encoding="utf-8") as f:
        f.write("Amazon\n")
        print(url)
        for producto in productos:
            if encontrados >= 3:
                break
            try:
                nombre = producto.find_element(By.XPATH, ".//h2//span").text.strip()
                try:
                    precio_element = producto.find_element(By.XPATH, ".//span[@class='a-price']")
                    precio = precio_element.find_element(By.XPATH, ".//span[@class='a-offscreen']").get_attribute("innerHTML").replace("&nbsp;", " ").strip()
                except:
                    try:
                        parte_entera = producto.find_element(By.XPATH, ".//span[@class='a-price-whole']").text.strip()
                        parte_decimal = producto.find_element(By.XPATH, ".//span[@class='a-price-fraction']").text.strip()
                        simbolo = producto.find_element(By.XPATH, ".//span[@class='a-price-symbol']").text.strip()
                        simbolo_limpio = simbolo.replace("&nbsp;", " ")
                        precio = f"{simbolo_limpio}{parte_entera},{parte_decimal}"
                    except:
                        precio = "Precio no disponible"

                print(f"{nombre} -> {precio}")
                f.write(f"{nombre} -> {precio}\n")
                encontrados += 1
            except Exception as e:
                print(f"Error procesando producto: {str(e)}")
                continue

# =========================
#  MEDIAMARKT
# =========================
def scrape_mediamarkt(driver, termino_busqueda):
    termino_codificado_mediamarkt = urllib.parse.quote_plus(termino_busqueda)
    url = f"https://www.mediamarkt.es/es/search.html?query={termino_codificado_mediamarkt}"
    driver.get(url)

    aceptar_cookies_mm(driver)

    try:
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
        for titulo_el in titulos[:3]:
            try:
                nombre = titulo_el.text.strip()
                try:
                    card = titulo_el.find_element(
                        By.XPATH,
                        "./ancestor::*[.//div[@data-test='mms-price']][1]"
                    )
                except:
                    card = titulo_el.find_element(By.XPATH, "./ancestor::*[1]")

                try:
                    price_box = card.find_element(By.XPATH, ".//div[@data-test='mms-price']")
                    precio_actual, precio_original, hay_oferta = extraer_precios_mediamarkt(price_box)
                except:
                    precio_actual, precio_original, hay_oferta = ("Precio no disponible", "Precio no disponible", False)

                if hay_oferta:
                    print(f"{nombre} -> {precio_actual} (antes: {precio_original})")
                    f.write(f"{nombre} -> {precio_actual} (antes: {precio_original})\n")
                else:
                    print(f"{nombre} -> {precio_original}")
                    f.write(f"{nombre} -> {precio_original}\n")
            except Exception as e:
                print("Error en MediaMarkt:", repr(e))
                continue


#=====================
#  FNAC
#=====================
def scrape_fnac(driver,termino_busqueda):
    print("Por implementar")


#==================
#  MENÚ
#==================

tiendas_fisicas = ["Amazon", "Mediamarkt"]
tiendas_digitales = []

def menu(driver):
    while True:
        print("\nSeleccione tu opción:")
        print("1. Juegos físicos")
        print("2. Juegos digitales")
        print("3. ¿Cuáles son las tiendas?")
        print("0. Salir")

        opcion = input("Ingrese una opción: ")

        if opcion == "1":
            termino_busqueda = input("¿Qué producto deseas buscar en Amazon y MediaMarkt?: ").strip()
            if not termino_busqueda:
                print("No escribiste nada. Intenta de nuevo.")
                continue
            scrape_amazon(driver, termino_busqueda) #Aqui nos vamos a Amazon
            scrape_mediamarkt(driver, termino_busqueda)#MediaMarkt
            scrape_fnac(driver,termino_busqueda)

        elif opcion == "2":
            print("\n\nHas elegido Juegos digitales:")
            print("No implementado aún")

        elif opcion == "3":
            print("Has elegido las tiendas")
            print("\nTiendas físicas:")
            for tienda in tiendas_fisicas:
                print(f"- {tienda}")
            print("\nTiendas digitales:")
            for tienda2 in tiendas_digitales:
                print(f"- {tienda2}")

        elif opcion == "0":
            print("Saliendo del programa...")
            break
        else:
            print("Opción inválida, intenta de nuevo.")

#==================
#  MAIN
#==================

if __name__ == "__main__":
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    #Todo lo de aqui es para activar el servicio con Google antes de la busqueda
    try:
        menu(driver) #Activamos el menu con el 
    finally:
        driver.quit()
