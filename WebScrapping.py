from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# Configurar Chrome
options = Options()
options.add_argument("--headless")  # Quita comentario si no quieres ver el navegador
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service()
driver = webdriver.Chrome(service=service, options=options)

# Abrir la página de búsqueda en Amazon
url = "https://www.amazon.es/s?k=donkey+kong"
driver.get(url)

time.sleep(1)  # Esperar que cargue

productos = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
encontrados = 0
print(f"Primeras 3 busquedas de Amazon:")
with open("productos.txt", "w", encoding="utf-8") as f:
    for producto in productos:
        if encontrados >= 3:
            break
        try:
            nombre = producto.find_element(By.XPATH, ".//h2//span").text.strip()
            
            # Nuevo enfoque para el precio
            try:
                # Primero intentamos con el precio completo
                precio_element = producto.find_element(By.XPATH, ".//span[@class='a-price']")
                precio = precio_element.find_element(By.XPATH, ".//span[@class='a-offscreen']").get_attribute("innerHTML").replace("&nbsp;"," ").strip()

            except:
                # Si falla, intentamos con las partes del precio
                try:
                    parte_entera = producto.find_element(By.XPATH, ".//span[@class='a-price-whole']").text.strip()
                    parte_decimal = producto.find_element(By.XPATH, ".//span[@class='a-price-fraction']").text.strip()
                    simbolo = producto.find_element(By.XPATH, ".//span[@class='a-price-symbol']").text.strip()
                    simbolo_limpio = simbolo.replace("&nbsp;"," ")
                    precio = f"{simbolo}{parte_entera},{parte_decimal}"
                except:
                    precio = "Precio no disponible"
            
            print(f"{nombre} -> {precio}")
            f.write(f"Amazon")
            f.write(f"{nombre} -> {precio}\n")
            encontrados += 1
        except Exception as e:
            print(f"Error procesando producto: {str(e)}")
            continue

driver.quit()