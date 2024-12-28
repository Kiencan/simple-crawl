# simple-crawl

# Cách để thu thập dữ liệu từ trang web bất kỳ sử dụng Beautiful Soup

## Bước 1: Cài đặt thư viện:

```
pip install -r requirements.txt
```

## Bước 2: Cài đặt postgres

Có nhiều cách để cài đặt khác nhau. Bạn có thể sử dụng cách như tôi. Đầu tiên tôi tải Docker Desktop về máy. Sau đó kéo một image từ trên docker hub về:

```
docker pull postgres
docker run --name some-postgres -e -p 5431:5432 POSTGRES_PASSWORD=mysecretpassword -d postgres
```

Bạn có thể cài thêm một IDE để quan sát trực quan về database. Ở đây tôi sử dụng Dbeaver.

## Bước 3: Chạy code

Trước khi chạy code, ta cần chỉnh sửa cấu hình trong các file phần database:

```
def connect_to_postgres():
    return psycopg2.connect(
        dbname="car_database",
        user="postgres",
        password="mysecretpassword",
        host="localhost",
        port="5431"
    )
```

Có hai cách chạy:

- Cách 1: Thêm trực tiếp lên database

```
python insert_direct.py
```

- Cách 2: Xuất ra file json rồi mới đẩy lên database

```
python insert_from_json.py
```

Cách đầu tiên có ưu điểm là thời gian ít hơn, không qua nhiều bước tuy nhiên khi mà có lỗi xảy ra giữa quá trình thu thập dữ liệu, quá trình sẽ phải thực hiện lại từ đầu. Cách hai sẽ an toàn hơn khi ta có xuất ra file json trước rồi sau đó đẩy lên database, nó sẽ giảm thiểu lỗi hơn và file json có thể sử dụng với các mục đích khác nữa.
