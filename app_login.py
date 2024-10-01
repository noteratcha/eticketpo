from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')
        
        # ตรวจสอบข้อมูลผู้ใช้จากฐานข้อมูลหรือ Google Sheets
        return 'เข้าสู่ระบบสำเร็จ'  # หรือ redirect ไปยังหน้าอื่น

    return render_template('member/login.html')

if __name__ == '__main__':
    app.run(debug=True)
