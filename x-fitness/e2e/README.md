# X Fitness Chatbot — ทดสอบผ่านหน้าเว็บด้วย Playwright

ใช้หน้าเว็บจริงเหมือนลูกค้า: เปิดเว็บ → ยืนยันสมาชิก (ถ้ามี) → เปิดแชต → แนบภาพ/พิมพ์ → รอคำตอบ → ตรวจข้อความที่ขึ้นบนจอ → ถ่ายภาพหน้าจอ

- **ชุดทดสอบ (อ่าน):** `qa/report/x-fitness-test-cases.md` นอก `x-fitness/` (หยิบจากคลังกลาง `qa/1-questions.md` `qa/2-images.md` `qa/3-safety.md` — แก้/เพิ่มแถวในคลังแล้วรัน `python qa/tools/build_report_set.py` ไม่ต้องแก้โค้ดที่นี่) · ทั้งคลัง: `E2E_CASES=../../qa npm test` → ผลไปที่ `qa/system/results/`
- **ผล (เขียน):** `qa/report/results/x-fitness-ui-results.md` (ผลตอบ · ผ่าน/ไม่ผ่าน · เวลาตอบ · ลิงก์ภาพหน้าจอ) · `qa/report/results/screenshots/` · `qa/report/results/x-fitness-ui-results.json`
- **ไม่แตะโค้ดแชตบอท:** ไม่ import อะไรจาก `backend/` รู้จักเว็บจากสิ่งที่ลูกค้าเห็นเท่านั้น (id ของปุ่มและช่องพิมพ์) · ภาพทดสอบอ่านจาก `qa/test-images/`

```text
e2e/
├── playwright.config.js   ตั้งค่า: เว็บที่ทดสอบ · เปิด backend ให้ถ้ายังไม่เปิด · รันทีละกรณี
├── tests/chatbot.spec.js  หนึ่งกรณีต่อหนึ่ง test: ขั้นตอนที่ลูกค้าทำบนหน้าเว็บ + การตรวจผล
└── lib/
    ├── testcases.js       อ่านตารางใน qa/report/x-fitness-test-cases.md (หรือ E2E_CASES)
    ├── run-file.js        เก็บผลทีละกรณี แล้วสร้างรายงานตอนจบ
    └── report.js          เขียน qa/report/results/x-fitness-ui-results.md
```

## รัน

ต้องมี Node.js 18+ และ backend ที่ตั้ง `TYPHOON_API_KEY` แล้ว (ดู `x-fitness/README.md`) — ถ้าไม่มี key หน้าเว็บจะอยู่โหมดจำลอง และทุกกรณีจะไม่ผ่านตั้งแต่ขั้นแรก

```bash
cd x-fitness/e2e
npm install                     # ครั้งแรก
npx playwright install chromium # ครั้งแรก
npm test                        # 40 กรณี ~3 นาที · เปิด backend ที่ localhost:8000 ให้เองถ้ายังไม่เปิด
```

| ต้องการ | คำสั่ง |
|---|---|
| ดูเบราว์เซอร์ทำงานจริง | `npm run test:headed` |
| เฉพาะบางชุด | `E2E_SUITES=questions,images npm test` (ชุด: questions · images · safety) |
| สุ่มหมวดละ N ข้อ (เช่น ทั้งคลัง) | `E2E_CASES=../../qa E2E_SAMPLE=20 npm test` · รันชุดเดิมซ้ำด้วย `E2E_SEED=<เลขที่รายงานบอก>` |
| ทดสอบเว็บที่ deploy แล้ว | `E2E_BASE_URL=https://x-fitness-chatbot.onrender.com npm test` |
| ชุดที่เก็บไว้ที่อื่น เช่น ชุด guardrail | `E2E_CASES=../../qa/guardrail/x-fitness-guardrail-test-cases.md E2E_OUT=../../qa/guardrail/results E2E_GAP_MS=2500 npm test` · `E2E_OUT` = โฟลเดอร์ผล · `E2E_GAP_MS` = รอระหว่างกรณี ไม่ให้ทั้งรอบชนตัวจำกัด 30 ข้อความ/นาที |
| ดูกรณีที่ไม่ผ่านแบบละเอียด | `npx playwright show-trace test-results/<โฟลเดอร์ของกรณีนั้น>/trace.zip` |

PowerShell ตั้งตัวแปรแบบนี้: `$env:E2E_SUITES="questions"; npm test`

## ตรวจอะไรบ้าง

ตามคอลัมน์ในเอกสาร test case: **ต้องมีทุกคำ** · **ต้องมีอย่างน้อย 1 คำ** · **ห้ามมี** (เทียบกับข้อความคำตอบบนจอ ตัวเลขไม่สนจุลภาค) · `guard=` (ป้ายรหัสกฎใต้คำตอบ) · `อ้างอิง=` (ป้าย KB-xx) · `หมวดอันตราย=ไม่มี` (ต้องไม่มีป้าย S1–S14) · `หน้าเว็บแจ้ง=<ข้อความ>` (ต้องขึ้นข้อความแจ้งเตือนนี้ เช่น ส่งถี่เกิน) · `ภาพ.<ช่อง>=` (JSON ผลวิเคราะห์ภาพที่หน้าเว็บแสดง) · หน้าเว็บต้องไม่แสดง error

ช่องข้อความส่งหลายข้อความในแชตเดียวได้: `ข้อความ 1 ⏎ ข้อความ 2` ส่งต่อกัน · `ข้อความ ×N` ส่งซ้ำ N ครั้ง · ตรวจที่คำตอบสุดท้าย

`สลิปผ่าน=` ตรวจจากหน้าเว็บไม่ได้ (หน้าเว็บไม่แสดงผลตรวจแยก) รายงานจะหมายเหตุไว้ — ใช้สคริปต์ API (`cd x-fitness/backend && python -m eval.run`) ตรวจข้อนี้

เวลาตอบ = จากกดส่งถึงคำตอบขึ้นจอ จึงมากกว่าเวลาของสคริปต์ API เล็กน้อย (รวมการแสดงผลและการบันทึกแชต)
