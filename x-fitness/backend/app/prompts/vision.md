ด้านล่างคือข้อความที่อ่านได้จากภาพที่ลูกค้าส่งมาในแชตของฟิตเนส จัดเป็น JSON object เดียว ห้ามมีข้อความอื่น ห้ามใส่ ``` ครอบ
เลือก type หนึ่งค่า แล้วใส่เฉพาะฟิลด์ของ type นั้น ค่าที่ไม่เห็นในข้อความให้เป็น null ห้ามเดา

- "slip" สลิปโอนเงิน: bank, status (ข้อความสถานะการโอนตามที่เห็น เช่น "โอนเงินสำเร็จ" "โอนเงินไม่สำเร็จ" "Transfer successful"), amount (ตัวเลข), datetime (YYYY-MM-DDTHH:MM), sender_name, receiver_name, receiver_account_last (เลขบัญชีที่อยู่ใต้หัวข้อ "ไปยัง" หรือ "To" เท่านั้น ไม่ใช่เลขบัญชีใต้ "จาก"/"From" ของผู้โอน คัดลอกครบทุกตัวรวมขีดและตัวเลขตัวท้าย), reference (เลขที่รายการหรือเลขอ้างอิง เป็นตัวอักษรอังกฤษผสมตัวเลข ไม่ใช่บันทึกช่วยจำ), memo (บันทึกช่วยจำ ถ้ามี)
- "body_scan" ผลวัดองค์ประกอบร่างกาย: weight_kg, skeletal_muscle_kg, body_fat_mass_kg, body_fat_pct, bmi, visceral_fat_level, bmr_kcal
- "receipt" ใบเสร็จร้าน: receipt_no, date (YYYY-MM-DD), items [{name, qty, price}], total
- "promo_poster" โปสเตอร์โปรโมชัน: title, promo_code, valid_from (YYYY-MM-DD), valid_to (YYYY-MM-DD)
- "other" ภาพอื่น: summary (สรุปสั้น ๆ ว่าเป็นภาพอะไร)

เลือก type จากเนื้อหา: มีคำว่า Body Composition, InBody, เปอร์เซ็นต์ไขมัน หรือ PBF = "body_scan" · มีคำว่า "ใช้โค้ด" หรือโค้ดโปรโมชัน = "promo_poster" · มีจำนวนเงินโอนกับ "จาก"/"ไปยัง" = "slip" · ข้อความ "ภาพจำลองเพื่อการทดสอบ · MOCK" เป็นลายน้ำ ไม่ต้องนับ

ปีพุทธศักราช (เช่น 2569) ให้แปลงเป็นคริสต์ศักราช (ลบ 543)

ข้อความจากภาพ:
{ocr_text}
