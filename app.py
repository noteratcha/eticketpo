from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import os
from PyPDF2 import PdfReader
import pandas as pd
from datetime import datetime
import sqlite3  # ใช้สำหรับการจัดการฐานข้อมูล SQLite


app = Flask(__name__)

# กำหนดโฟลเดอร์สำหรับอัปโหลดและจัดเก็บผลลัพธ์
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
DATABASE = 'register.db'  # ฐานข้อมูล SQLite สำหรับการเก็บข้อมูลผู้ใช้งาน

# ตรวจสอบและสร้างโฟลเดอร์หากไม่มีอยู่
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# สร้างฐานข้อมูลและตารางผู้ใช้งาน
def create_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user TEXT NOT NULL,
                        password TEXT NOT NULL,
                        organization TEXT NOT NULL,
                        address TEXT NOT NULL,
                        district TEXT NOT NULL,
                        province TEXT NOT NULL,
                        zipcode TEXT NOT NULL,
                        phone TEXT NOT NULL,
                        referrer TEXT)''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# เส้นทางสำหรับหน้าเติมเครดิต
@app.route('/etc/topup.html')
def topup():
    return render_template('/etc/topup.html')  # แก้ไขโฟลเดอร์ที่ถูกต้อง

# เส้นทางสำหรับหน้าติดต่อผู้ดูแล
@app.route('/etc/contact.html')
def contact():
    return render_template('/etc/contact.html')  # แก้ไขโฟลเดอร์ที่ถูกต้อง

# เส้นทางสำหรับ Excel D-Post
@app.route('/pdf2xls/exceldpost.html')
def exceldpost():
    return render_template('/pdf2xls/exceldpost.html')  # ต้องสร้างไฟล์ exceldpost.html ไว้ในโฟลเดอร์ /pdf2xls

# เส้นทางสำหรับข้อมูลผู้ฝาก
@app.route('/user_info')
def user_info():
    return render_template('/etc/user_info.html')  # ต้องสร้างไฟล์ user_info.html ไว้ในโฟลเดอร์ /etc


# ส่วนการจัดการ PDF
@app.route('/pdf2xls/ticketpdf.html')
def ticketpdf():
    return render_template('/pdf2xls/ticketpdf.html')

@app.route('/pdf2xls/noticepdf.html')
def noticepdf():
    return render_template('/pdf2xls/noticepdf.html')

def extract_info(lines, page_num, line_number):
    output = []
    receiver_name = ""

    for line in lines:
        if "เลขที่ใบสั่ง" in line:
            continue
        if "-----หน้าใหม่-----" in line:
            output.append([f"-----หน้าใหม่----- {page_num + 1}"])
        elif "Receiver's name" in line:
            receiver_name = line
        elif "Receiver's address" in line:
            address_line = line
            for i in range(1, 4):
                address_line += " " + lines[lines.index(line) + i]
            output.append([f"{receiver_name} {address_line}"])
            line_number += 1
    return output, line_number

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf' not in request.files:
        return "ไม่มีไฟล์ PDF อัปโหลด", 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return "โปรดเลือกไฟล์ PDF", 400

    try:
        reader = PdfReader(pdf_file)
    except Exception as e:
        return f"ไม่สามารถอ่านไฟล์ PDF ได้: {e}", 400

    output_data = []
    line_number = 1

    for page_num, page in enumerate(reader.pages):
        if (page_num + 1) % 2 != 0:
            page_text = page.extract_text()
            if page_text is None:
                continue
            lines = page_text.splitlines()
            extracted_lines, line_number = extract_info(lines, page_num, line_number)
            output_data.extend(extracted_lines)

    df = pd.DataFrame(output_data, columns=["ข้อมูลใบสั่ง"])
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = f"Ticket_{current_time}.xlsx"
    output_file_path = os.path.join(OUTPUT_FOLDER, output_file_name)

    df.to_excel(output_file_path, index=False, engine='openpyxl')

    return send_file(output_file_path, as_attachment=True)

@app.route('/upload_notice', methods=['POST'])
def upload_notice_file():
    if 'pdf' not in request.files:
        return "ไม่มีไฟล์ PDF ที่อัปโหลด", 400

    pdf_file = request.files['pdf']
    if pdf_file.filename == '':
        return "โปรดเลือกไฟล์ PDF", 400

    file_path = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
    pdf_file.save(file_path)

    try:
        reader = PdfReader(file_path)
    except Exception as e:
        return f"ไม่สามารถอ่านไฟล์ PDF ได้: {e}", 400

    output_data = []

    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            lines = page_text.splitlines()
            for i, line in enumerate(lines):
                if "ชื่อ-นามสกุล :" in line:
                    name = line
                    address = " ".join(lines[i + 1:i + 4])
                    postal_code = lines[i + 4] if "รหัสไปรษณีย์ :" in lines[i + 4] else ""
                    ref_number = next((l for l in lines if "ใบสั่งเลขที่ (Ref1) :" in l), "")

                    full_info = f"{name} {address} {postal_code} {ref_number}"
                    output_data.append(full_info)

    if not output_data:
        return "ไม่พบข้อมูลที่ต้องการ", 400

    df = pd.DataFrame({'ข้อมูลใบแจ้งเตือน': output_data})
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_name = f"Notice_{current_time}.xlsx"
    output_file_path = os.path.join(OUTPUT_FOLDER, output_file_name)

    df.to_excel(output_file_path, index=False, engine='openpyxl')

    return send_file(output_file_path, as_attachment=True)

# ส่วนการสมัครผู้ใช้งาน
@app.route('/register', methods=['POST'])
def register():
    data = request.form  # รับข้อมูลจากฟอร์ม
    user = data.get('user')
    password = data.get('password')
    organization = data.get('organization')
    address = data.get('address')
    district = data.get('district')
    province = data.get('province')
    zipcode = data.get('zipcode')
    phone = data.get('phone')
    referrer = data.get('referrer')

    # ตรวจสอบความถูกต้องในฝั่งเซิร์ฟเวอร์
    if not user.isalnum() or len(password) < 8:
        return "ข้อมูลไม่ถูกต้อง", 400

    # บันทึกข้อมูลลงฐานข้อมูล
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (user, password, organization, address, district, province, zipcode, phone, referrer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (user, password, organization, address, district, province, zipcode, phone, referrer))
    conn.commit()
    conn.close()

    # ส่งข้อมูลกลับเป็น JSON หลังสมัครสำเร็จ
    return jsonify({'status': 'success', 'message': 'สมัครสมาชิกสำเร็จ!'})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

