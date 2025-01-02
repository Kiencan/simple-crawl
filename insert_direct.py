import requests
from bs4 import BeautifulSoup
import re
import psycopg2

regex = re.compile(r'[^\w\s.,!?@#&()\'"%;:<>/*-]')

# Hàm làm sạch văn bản
def clean_text(text):
    if text:
        text = text.replace('\n', ' ')
        return regex.sub('', text).strip()
    return ''

# Hàm thêm dữ liệu vào PostgreSQL
def insert_into_database(data, connection):
    with connection.cursor() as cursor:
        for car in data:
            cursor.execute("""
                INSERT INTO cars (ma_xe, ten_xe, gia, dia_diem_ban, link_anh, nam_san_xuat, tinh_trang, so_km_da_di, xuat_xu, kieu_dang, hop_so, dong_co, mau_ngoai_that, mau_noi_that, so_cho_ngoi, so_cua, dan_dong, mo_ta, ten_nguoi_lien_he, so_dien_thoai, dia_chi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ma_xe) DO NOTHING
            """, (
                car["ma_xe"], car["ten_xe"], car["gia"], car["dia_diem_ban"], car["link_anh"],
                car["nam_san_xuat"], car["tinh_trang"], car["so_km_da_di"], car["xuat_xu"], car["kieu_dang"],
                car["hop_so"], car["dong_co"], car["mau_ngoai_that"], car["mau_noi_that"], car["so_cho_ngoi"],
                car["so_cua"], car["dan_dong"], car["mo_ta"], car["ten_nguoi_lien_he"], car["so_dien_thoai"], car["dia_chi"]
            ))
    connection.commit()

# Hàm chuyển đổi giá từ chuỗi sang số
def convert_price(price_text):
    if not price_text:
        return None
    price_text = price_text.lower().replace("tr.", "triệu")  # Chuẩn hóa viết tắt 'tr.' thành 'triệu'
    try:
        # Trường hợp chỉ có "x Triệu"
        if "triệu" in price_text and "tỷ" not in price_text:
            return int(float(price_text.replace("triệu", "").strip()) * 1_000_000)

        # Trường hợp chỉ có "x Tỷ"
        if "tỷ" in price_text and "triệu" not in price_text:
            return int(float(price_text.replace("tỷ", "").strip()) * 1_000_000_000)

        # Trường hợp "x Tỷ x Triệu"
        if "tỷ" in price_text and "triệu" in price_text:
            parts = price_text.split("tỷ")
            billion_part = float(parts[0].strip()) * 1_000_000_000
            million_part = float(parts[1].replace("triệu", "").strip()) * 1_000_000 if parts[1].strip() else 0
            return int(billion_part + million_part)

    except ValueError:
        return None
    return None

def extract_car_details(soup):
    details = {
        "nam_san_xuat": None,
        "tinh_trang": None,
        "so_km_da_di": None,
        "xuat_xu": None,
        "kieu_dang": None,
        "hop_so": None,
        "dong_co": None,
        "mau_ngoai_that": None,
        "mau_noi_that": None,
        "so_cho_ngoi": None,
        "so_cua": None,
        "dan_dong": None,
    }

    rows = soup.select("div.row, div.row_last")
    for row in rows:
        label = row.select_one("div.label label")
        value = row.select_one("div.txt_input span.inp") or row.select_one("div.inputbox span.inp")

        if label and value:
            label_text = label.get_text(strip=True)
            value_text = value.get_text(strip=True)

            if "Năm sản xuất" in label_text:
                details["nam_san_xuat"] = value_text
            elif "Tình trạng" in label_text:
                details["tinh_trang"] = value_text
            elif "Số Km đã đi" in label_text:
                details["so_km_da_di"] = int(value_text.replace("Km", "").replace(",", "").strip())
            elif "Xuất xứ" in label_text:
                details["xuat_xu"] = value_text
            elif "Kiểu dáng" in label_text:
                details["kieu_dang"] = value_text
            elif "Hộp số" in label_text:
                details["hop_so"] = value_text
            elif "Động cơ" in label_text:
                details["dong_co"] = value_text
            elif "Màu ngoại thất" in label_text:
                details["mau_ngoai_that"] = value_text
            elif "Màu nội thất" in label_text:
                details["mau_noi_that"] = value_text
            elif "Số chỗ ngồi" in label_text:
                details["so_cho_ngoi"] = int(value_text.replace("chỗ", "").strip())
            elif "Số cửa" in label_text:
                details["so_cua"] = int(value_text.replace("cửa", "").strip())
            elif "Dẫn động" in label_text:
                details["dan_dong"] = value_text

    return details

# Hàm kiểm tra mã xe đã tồn tại trong cơ sở dữ liệu
def car_exists(car_code, connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM cars WHERE ma_xe = %s", (car_code,))
        return cursor.fetchone() is not None

def get_contact_info(soup):
    contact_div = soup.select_one("div.contact-txt")
    if contact_div:
        # Tên người liên hệ
        contact_name = contact_div.select_one("span.cname").get_text(strip=True) if contact_div.select_one("span.cname") else None
        if not contact_name:
            contact_name = contact_div.select_one("a.cname").get_text(strip=True) if contact_div.select_one("a.cname") else None
        
        # Số điện thoại liên hệ (tất cả số)
        phone_numbers = [phone.get_text(strip=True).strip() for phone in contact_div.select("a.cphone")]
        phone_numbers = ' '.join(phone_numbers) if phone_numbers else None
        
        # Địa chỉ cụ thể
        address_match = re.search(r"Địa chỉ:\s*(.*?)(?:Website:|$)", contact_div.get_text(separator=" ",strip=True))
        address = address_match.group(1).strip() if address_match else None
        
        return {
            "contact_name": contact_name,
            "phone_numbers": phone_numbers,
            "address": address
        }
    return None

# Hàm lấy dữ liệu từ trang web
def get_car_data(url):
    
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        cars = soup.select("ul > li.car-item")
        car_data = []

        for car in cars:
            car_code_text = clean_text(car.select_one("span.car_code").text if car.select_one("span.car_code") else None)
            car_code = re.search(r'\d+', car_code_text).group() if car_code_text and re.search(r'\d+', car_code_text) else None
            # Kiểm tra mã xe đã tồn tại chưa
            if car_code and car_exists(car_code, connection):
                print(f"Mã xe {car_code} đã tồn tại, bỏ qua.")
                continue
            name = clean_text(car.select_one("div.cb2_02 h3").text if car.select_one("div.cb2_02 h3") else None)

            price_text = clean_text(car.select_one("div.cb3 b[itemprop='price']").text if car.select_one("div.cb3 b[itemprop='price']") else None)
            price = convert_price(price_text)

            location = clean_text(car.select_one("div.cb4 b").text if car.select_one("div.cb4 b") else None)

            car_link = 'https://bonbanh.com/' + car.select_one("a")['href'] if car.select_one("a") else None
            new_response = requests.get(car_link)
            if new_response.status_code == 200:
                new_soup = BeautifulSoup(new_response.text, 'lxml')
                car_image = new_soup.select_one("a#lnk1")['href'] if new_soup.select_one("a#lnk1") else None

                # Thông số kỹ thuật
                car_details = extract_car_details(new_soup)
                
                car_description = None
                car_des = new_soup.select_one("div.des_txt")
                if car_des:
                    # Lấy toàn bộ văn bản, nối bằng ký tự xuống dòng
                    car_description = car_des.get_text(separator=" ", strip=True)
                # Thông tin liên hệ
                contact_info = get_contact_info(new_soup)


            # Thêm dữ liệu vào danh sách
            car_data.append({
                "ma_xe": car_code,
                "ten_xe": name,
                "gia": price,
                "dia_diem_ban": location,
                "link_anh": car_image,
                "nam_san_xuat": car_details["nam_san_xuat"],
                "tinh_trang": car_details["tinh_trang"],
                "so_km_da_di": car_details["so_km_da_di"],
                "xuat_xu": car_details["xuat_xu"],
                "kieu_dang": car_details["kieu_dang"],
                "hop_so": car_details["hop_so"],
                "dong_co": car_details["dong_co"],
                "mau_ngoai_that": car_details["mau_ngoai_that"],
                "mau_noi_that": car_details["mau_noi_that"],
                "so_cho_ngoi": car_details["so_cho_ngoi"],
                "so_cua": car_details["so_cua"],
                "dan_dong": car_details["dan_dong"],
                "mo_ta": car_description,
                "ten_nguoi_lien_he": contact_info["contact_name"] if contact_info else None,
                "so_dien_thoai": contact_info["phone_numbers"] if contact_info else None,
                "dia_chi": contact_info["address"] if contact_info else None
            })

        return car_data
    else:
        print("Không thể kết nối tới trang web!")
        return []

# Thu thập dữ liệu và thêm vào PostgreSQL
def scrape_all_pages(base_url, max_pages, connection):
    print("Kết nối tới cơ sở dữ liệu...")
    all_data = []
    print(f"Đang thu thập dữ liệu từ trang 1...")
    all_data.extend(get_car_data(base_url))
    page = 2

    while page <= max_pages:
        print(f"Đang thu thập dữ liệu từ trang {page}...")
        url = f"{base_url}/page,{page}"
        page_data = get_car_data(url)
        if not page_data:
            break
        all_data.extend(page_data)
        page += 1

    print("Thêm dữ liệu vào cơ sở dữ liệu...")
    insert_into_database(all_data, connection)
    print("Hoàn thành!")

# Kết nối tới PostgreSQL
def connect_to_postgres():
    return psycopg2.connect(
        dbname="car_database",
        user="postgres",
        password="mysecretpassword",
        host="localhost",
        port="5431"
    )

# Chạy chương trình
if __name__ == "__main__":
    base_url = "https://bonbanh.com/oto"
    # max_pages = int(input("Nhập số trang cần thu thập: "))
    max_pages = 10
    connection = connect_to_postgres()

    try:
        scrape_all_pages(base_url, max_pages, connection)
    finally:
        connection.close()