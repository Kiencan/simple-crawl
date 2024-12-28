import requests
from bs4 import BeautifulSoup
import re
import psycopg2

regex = re.compile(r'[^\w\s.,!?@#&()\'"%;:<>/*-]')

# Hàm làm sạch văn bản
def clean_text(text):
    if text:
        text = text.replace('\n', ' ')  # Thay thế \n bằng khoảng trắng
        return regex.sub('', text).strip()
    return ''

# Hàm thêm dữ liệu vào PostgreSQL
def insert_into_database(data, connection):
    with connection.cursor() as cursor:
        for car in data:
            cursor.execute("""
                INSERT INTO cars (name, price, details, location, car_code, contact_info, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                car["name"], car["price"], car["details"],
                car["location"], car["car_code"], car["contact_info"],
                car["image_url"]
            ))
    connection.commit()

# Hàm lấy dữ liệu từ trang web
def get_car_data(url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        cars = soup.select("ul > li.car-item")
        car_data = []

        for car in cars:
            name = clean_text(car.select_one("div.cb2_02 h3").text if car.select_one("div.cb2_02 h3") else None)
            price = clean_text(car.select_one("div.cb3 b[itemprop='price']").text if car.select_one("div.cb3 b[itemprop='price']") else None)
            details = [clean_text(d.text) for d in car.select("div.cb6_02, div.cb6_02 p")]
            location = clean_text(car.select_one("div.cb4 b").text if car.select_one("div.cb4 b") else None)
            car_code = clean_text(car.select_one("span.car_code").text if car.select_one("span.car_code") else None)

            # Thông tin liên hệ
            contact_info = [clean_text(c.text if c else '') for c in car.select("div.cb7, div.cb7 br")]
            contact_info = " ".join([c for c in contact_info if c])

            # Xử lý số điện thoại
            phone_numbers = []
            phone_scripts = car.select("div.cb7 script")
            for phone_script in phone_scripts:
                script_text = phone_script.string
                if script_text:
                    match = re.search(r"document.write\('(.*?)'\)", script_text)
                    if match:
                        phone_numbers.append(clean_text(match.group(1)))

            if phone_numbers:
                contact_info += " " + " - ".join(phone_numbers)

            # Lấy URL hình ảnh
            image_url = car.select_one("div.cb5 img")['src'] if car.select_one("div.cb5 img") else None

            # Thêm dữ liệu vào danh sách
            car_data.append({
                "name": name,
                "price": price,
                "details": " ".join([d for d in details if d]),
                "location": location,
                "car_code": car_code,
                "contact_info": contact_info,
                "image_url": image_url,
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
    max_pages = int(input("Nhập số trang cần thu thập: "))
    connection = connect_to_postgres()

    try:
        scrape_all_pages(base_url, max_pages, connection)
    finally:
        connection.close()
