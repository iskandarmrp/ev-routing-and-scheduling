import time
import csv
import re
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.interaction import Interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder

# Step 1: Set Up Desired Capabilities
options = UiAutomator2Options()
options.platform_name = "Android"
options.device_name = "emulator-5554"  # Change if using a real device
options.app_package = "com.icon.pln123"
options.app_activity = "io.flutter.embedding.android.FlutterActivity"  # Flutter's main activity
options.automation_name = "UiAutomator2"
options.no_reset = True

# Step 2: Start Appium Driver
try:
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    wait = WebDriverWait(driver, 30)  # ⏳ Increased timeout for slow loading

    print("✅ Appium connection established successfully!")

    # Step 3: Click the 'Electric Vehicle' Button
    try:
        ev_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//android.widget.ImageView[@content-desc='Electric Vehicle']")))
        ev_button.click()
        print("✅ Clicked 'Electric Vehicle' button!")

        # 🕵️‍♂️ Tampilkan semua elemen setelah klik tombol Electric Vehicle
        time.sleep(3)  # Tunggu beberapa detik sebelum mencari elemen

        # Cari semua elemen yang bisa diklik
        elements = driver.find_elements(By.XPATH, "//*[@clickable='true']")

        # Menekan tombol iklan
        if elements:
            print(f"🟢 Ditemukan {len(elements)} tombol yang bisa diklik. Mencoba menekan semuanya...\n")

            for index, el in enumerate(elements):
                try:
                    # Ambil deskripsi atau teks tombol
                    content_desc = el.get_attribute("content-desc")
                    text = el.text.strip() if el.text.strip() else "Tanpa Teks"

                    print(f"➡️ Menekan tombol {index+1}: Content-desc='{content_desc}', Text='{text}'")

                    # Klik tombol
                    el.click()
                    print(f"✅ Berhasil menekan tombol {index+1}\n")

                    # Tunggu sebentar untuk melihat perubahan UI
                    driver.implicitly_wait(2)

                except Exception as e:
                    print(f"❌ Gagal menekan tombol {index+1}: {e}")

        else:
            print("⚠️ Tidak ditemukan tombol yang bisa diklik di layar.")

    except Exception as e:
        print(f"❌ Failed to click 'Electric Vehicle' button: {e}")

    # Step 4: Click the '3561 Charger' Button
    try:
        # Cari semua elemen yang memiliki atribut content-desc
        charger_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//android.widget.ImageView[@content-desc]")))

        for button in charger_buttons:
            content_desc = button.get_attribute("content-desc")
            match = re.search(r"\b3[0-9]{3}\b", content_desc)  # Cari angka antara 3000-3999
            if match:
                button.click()
                print(f"✅ Clicked '{content_desc}' button!")
                break  # Hentikan setelah menemukan dan mengklik tombol
        else:
            print("❌ No charger button found with number between 3000 and 3999!")
    except Exception as e:
        print(f"❌ Failed to click charger button: {e}")

    spklu_data = set()  # Using a set to avoid duplicates

    # 🕒 Step 5: Wait for Data to Load
    try:
        print("⏳ Waiting for SPKLU data to load...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//android.view.View[@content-desc and contains(@content-desc, 'Konektor')]")))
        time.sleep(5)  # ⏳ Extra wait to ensure full loading
        print("✅ SPKLU data loaded!")
    except Exception as e:
        print(f"❌ Timeout waiting for SPKLU data: {e}")

    # Step 6: Scroll and Extract Data
    previous_data_count = 0
    max_scroll_attempts = 360  # Prevent infinite loops #1300
    scroll_attempt = 0

    visited_names = set()

    # Cari Central Java

    while scroll_attempt < max_scroll_attempts:
        try:
            time.sleep(1)
            spklu_elements = driver.find_elements(By.XPATH, "//android.view.View[@content-desc]")
            for element in spklu_elements:
                content_desc = element.get_attribute("content-desc")
                print(f"🔍 Found content-desc: {content_desc}")  # Tambahkan ini untuk debugging
                if "Konektor" in content_desc and "Semua" not in content_desc:
                    spklu_tuple = tuple(content_desc.split('\n')) 
                    if (len(spklu_tuple) > 1):
                        print("Nama SPKLu:",spklu_tuple[0])
                        xpath = f"//android.view.View[@content-desc[starts-with(., '{spklu_tuple[0]}')]]"
                        if spklu_tuple[0] not in visited_names:
                            visited_names.add(spklu_tuple[0])
                            try:
                                print("Pencet:", content_desc)
                                # Dapatkan posisi dan ukuran elemen
                                loc = element.location
                                x = loc['x'] + 5
                                y = loc['y'] + 10
                                driver.execute_script("mobile: shell", {
                                    "command": "input",
                                    "args": ["tap", str(x), str(y)]
                                })
                                # element.click()
                                time.sleep(2)  # Tunggu detail SPKLU terbuka
                                try:
                                    screen = driver.get_window_size()
                                    start_x = screen['width'] // 2
                                    start_y = screen['height'] * 3 // 4
                                    end_y = screen['height'] // 4

                                    driver.swipe(start_x, start_y, start_x, end_y, 800)

                                    charging_slots = []
                                    availability = []

                                    time.sleep(1)

                                    # 1. Cari elemen berdasarkan isi content-desc
                                    boxes = driver.find_elements(
                                        By.XPATH,
                                        "//android.widget.ImageView[" +
                                        "contains(@content-desc, 'KW') or " +
                                        "contains(@content-desc, 'AC') or " +
                                        "contains(@content-desc, 'DC') or " +
                                        "contains(@content-desc, 'Charger')]"
                                    )

                                    print(f"📦 Ditemukan {len(boxes)} kotak yang cocok")

                                    for idx, box in enumerate(boxes):
                                        desc = box.get_attribute("content-desc")
                                        print(f"🔍 Klik box ke-{idx+1}: {desc}")

                                    for idx, box in enumerate(boxes):
                                        try:
                                            desc = box.get_attribute("content-desc")
                                            print(f"🔍 Klik box ke-{idx+1}: {desc}")

                                            box.click()

                                            driver.swipe(start_x, start_y, start_x, end_y, 800)

                                            time.sleep(1)

                                            harga_elements = driver.find_elements(By.XPATH, "//android.view.View[contains(@content-desc, 'Rp')]")
                                            for el in harga_elements:
                                                detail = el.get_attribute("content-desc")
                                                if "kWh" in detail:
                                                    detail_list = detail.split("\n")
                                                    print(f"📋 Harga ditemukan: {detail}")

                                                    # 1. Ekstrak string kapasitas dengan satuan, misalnya "50 kW"
                                                    match_kw = re.search(r"(\d+\s*kW)", detail_list[0], re.IGNORECASE)
                                                    if match_kw:
                                                        charging_slots.append(match_kw.group(1))
                                                    else:
                                                        charging_slots.append(detail_list[0])  # fallback

                                                    # 2. Cek status "Tersedia"
                                                    available = 0
                                                    if detail_list[1] == "Tidak Tersedia":
                                                        available = 0
                                                    elif detail_list[1] == "Tersedia":
                                                        available = 1
                                                    else:
                                                        available = 0

                                                    availability.append(available)

                                            time.sleep(1)

                                        except Exception as e:
                                            print(f"❌ Gagal proses box ke-{idx+1}: {e}")

                                    snapshot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    spklu_data.add(
                                        spklu_tuple +
                                        (tuple(charging_slots),) +
                                        (tuple(availability),) +
                                        (snapshot_time,)  # string harus dibungkus tuple juga
                                    )


                                except Exception as e:
                                    print(f"❌ Gagal menemukan Kotak Pengisian: {e}")


                                driver.back()  # Kembali ke halaman sebelumnya
                                time.sleep(2)  # Tunggu halaman daftar kembali

                            except Exception as e:
                                print(f"❌ Gagal menekan SPKLU '{spklu_data}': {e}")

            print(f"📊 Extracted {len(spklu_data)} SPKLU entries so far...")
            print(spklu_data)

            previous_data_count = len(spklu_data)

            # 📜 Perform scroll (Swipe Up)
            screen_size = driver.get_window_size()
            start_x, start_y = screen_size["width"] // 3, screen_size["height"] *7// 10
            end_x, end_y = start_x, screen_size["height"]*2// 10


            driver.swipe(start_x, start_y, start_x, end_y,1000)
            time.sleep(3)  # Wait for new content to load
            print(f"🔄 Scrolled {scroll_attempt + 1} time(s)")

        except Exception as e:
            print(f"❌ Error during scrolling and extraction: {e}")
            break

        scroll_attempt += 1

    # Step 7: Write Data into CSV File
    try:
        with open("spklu_data_new.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Nama SPKLU","Alamat","Waktu Operasi","Jam Buka","Jarak","Konektor", "Charging Slots", "Ketersediaan", "Timestamp"])  # CSV Header
            writer.writerows(spklu_data)  # Write extracted data
        print("✅ SPKLU data saved to 'spklu_data_new.csv'!")
    except Exception as e:
        print(f"❌ Failed to save data to CSV: {e}")

finally:
    if 'driver' in locals():
        driver.quit()