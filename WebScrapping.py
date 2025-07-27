from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import urllib.parse  # Para codificar correctamente el término de búsqueda

# Pedir al usuario el término de búsqueda en Amazon
termino_busqueda = input("¿Qué producto deseas buscar en Amazon?: ")
termino_codificado = urllib.parse.quote_plus(termino_busqueda)

# Configurar Chrome
options = Options()
options.add_argument("--headless")  # Quita comentario si no quieres ver el navegador
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service()
driver = webdriver.Chrome(service=service, options=options)

# termino_codificado es lo que vamos a añadir para la página de amazon
url = f"https://www.amazon.es/s?k={termino_codificado}"
driver.get(url)

time.sleep(1)  

productos = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
encontrados = 0
print(f"Primeras 3 búsquedas de Amazon para '{termino_busqueda}':")
with open("productos.txt", "w", encoding="utf-8") as f:
    f.write(f"Amazon\n")
    f.write(url)
    for producto in productos:
        if encontrados >= 3:
            break
        try:
            ##Nombre
            nombre = producto.find_element(By.XPATH, ".//h2//span").text.strip()
        
            ##Precio
            try:
                precio_element = producto.find_element(By.XPATH, ".//span[@class='a-price']")
                precio = precio_element.find_element(By.XPATH, ".//span[@class='a-offscreen']").get_attribute("innerHTML").replace("&nbsp;", " ").strip()
            except:
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

driver.quit()
