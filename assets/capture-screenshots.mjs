/**
 * สคริปต์แคปหน้าจอระบบจองคิวคลินิกทุกบทบาทผู้ใช้ พร้อมใส่คำอธิบายลงในภาพ
 *
 * รัน: node capture.mjs
 * ผลลัพธ์: <repo>/assets/screenshots/*.png และไฟล์ manifest.json
 *
 * สคริปต์นี้เป็นเครื่องมือทำเอกสาร ไม่ใช่ส่วนหนึ่งของระบบ จึงอยู่นอกโฟลเดอร์โปรเจกต์
 */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const BASE_URL = "http://localhost:3000";
const OUTPUT_DIR = "C:/Users/M/Desktop/clinic/assets/screenshots";
const PASSWORD = "ClinicDev!2026";
/** วันที่ที่มีคิวตัวอย่างในฐานข้อมูล (วันจันทร์) */
const DEMO_DATE = "2026-08-17";

const VIEWPORT = { width: 1440, height: 900 };

const ROLES = {
  super_admin: { email: "root@clinic.test", label: "Super Admin (ผู้ดูแลระบบสูงสุด)" },
  admin: { email: "admin.bkk@clinic.test", label: "Admin (ผู้จัดการสาขา)" },
  staff: { email: "staff.bkk@clinic.test", label: "Staff (เจ้าหน้าที่หน้าเคาน์เตอร์)" },
  doctor: { email: "doctor.ploy@clinic.test", label: "Doctor (แพทย์)" },
};

const manifest = [];
let figureNumber = 0;

/**
 * วาดแถบคำอธิบายลงบนหน้าเว็บก่อนแคป
 *
 * ใส่เป็น element จริงในหน้า (ไม่ใช่วาดทับภายหลัง) เพื่อให้ข้อความคมชัดตามความละเอียดจอ
 * และเลื่อนเนื้อหาหน้าเว็บลงมาไม่ให้ถูกแถบบัง
 */
async function annotate(page, { figure, title, role, description, callouts = [] }) {
  await page.evaluate(
    ({ figure, title, role, description, callouts }) => {
      document.querySelectorAll(".__doc_annotation").forEach((el) => el.remove());

      const banner = document.createElement("div");
      banner.className = "__doc_annotation";
      banner.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
        background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 100%); color: #fff;
        padding: 10px 18px; font-family: "Segoe UI", "Sarabun", sans-serif;
        box-shadow: 0 2px 10px rgba(0,0,0,.25);
      `;
      banner.innerHTML = `
        <div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap">
          <span style="background:#fff;color:#1e3a8a;font-weight:700;padding:2px 10px;border-radius:999px;font-size:13px">
            ${figure}
          </span>
          <span style="font-size:17px;font-weight:600">${title}</span>
          <span style="font-size:13px;opacity:.9">· บทบาท: ${role}</span>
        </div>
        <div style="font-size:13px;opacity:.95;margin-top:3px">${description}</div>
      `;
      document.body.appendChild(banner);

      // เว้นที่ด้านบนให้แถบคำอธิบาย ไม่ให้บังเนื้อหาจริงของหน้าจอ
      const spacerHeight = banner.offsetHeight;
      document.body.style.paddingTop = `${spacerHeight}px`;

      // วาดกรอบไฮไลต์ + หมายเลขชี้จุดสำคัญของหน้าจอ
      callouts.forEach((callout, index) => {
        const target = document.querySelector(callout.selector);
        if (!target) return;
        const rect = target.getBoundingClientRect();

        const box = document.createElement("div");
        box.className = "__doc_annotation";
        box.style.cssText = `
          position: absolute; z-index: 2147483646; pointer-events: none;
          left: ${rect.left + window.scrollX - 4}px; top: ${rect.top + window.scrollY - 4}px;
          width: ${rect.width + 8}px; height: ${rect.height + 8}px;
          border: 2px solid #dc2626; border-radius: 8px;
        `;
        document.body.appendChild(box);

        const badge = document.createElement("div");
        badge.className = "__doc_annotation";
        badge.style.cssText = `
          position: absolute; z-index: 2147483647; pointer-events: none;
          left: ${rect.left + window.scrollX - 14}px; top: ${rect.top + window.scrollY - 14}px;
          background: #dc2626; color: #fff; font-family: "Segoe UI", "Sarabun", sans-serif;
          font-size: 12px; font-weight: 700; width: 22px; height: 22px; border-radius: 999px;
          display: flex; align-items: center; justify-content: center;
        `;
        badge.textContent = String(index + 1);
        document.body.appendChild(badge);

        // วางป้ายไว้ขวาของเป้าหมายเป็นค่าเริ่มต้น แต่ถ้าจะล้นขอบจอให้ย้ายไปด้านล่างแทน
        // มิฉะนั้นป้ายจะไปทับปุ่มอื่นและอ่านภาพไม่รู้เรื่อง
        const LABEL_WIDTH = 260;
        const willOverflowRight = rect.left + rect.width + LABEL_WIDTH + 20 > window.innerWidth;
        const labelLeft = willOverflowRight
          ? Math.max(8, rect.left + rect.width - LABEL_WIDTH)
          : rect.left + rect.width + 10;
        const labelTop = willOverflowRight ? rect.top + rect.height + 10 : rect.top - 4;

        const label = document.createElement("div");
        label.className = "__doc_annotation";
        label.style.cssText = `
          position: absolute; z-index: 2147483647; pointer-events: none;
          left: ${labelLeft + window.scrollX}px;
          top: ${labelTop + window.scrollY}px; max-width: ${LABEL_WIDTH}px;
          background: #dc2626; color: #fff; font-family: "Segoe UI", "Sarabun", sans-serif;
          font-size: 12px; padding: 4px 8px; border-radius: 6px; line-height: 1.4;
        `;
        label.textContent = `${index + 1}. ${callout.text}`;
        document.body.appendChild(label);
      });
    },
    { figure, title, role, description, callouts },
  );
  await page.waitForTimeout(150);
}

async function capture(page, fileName, meta) {
  figureNumber += 1;
  const figure = `ภาพที่ ${String(figureNumber).padStart(2, "0")}`;
  await annotate(page, { ...meta, figure });

  const filePath = path.join(OUTPUT_DIR, `${String(figureNumber).padStart(2, "0")}-${fileName}.png`);
  await page.screenshot({ path: filePath, fullPage: false });

  // ลบคำอธิบายออกเพื่อไม่ให้ค้างไปยังภาพถัดไป
  await page.evaluate(() => {
    document.querySelectorAll(".__doc_annotation").forEach((el) => el.remove());
    document.body.style.paddingTop = "";
  });

  manifest.push({ figure, file: path.basename(filePath), ...meta });
  console.log(`  ${figure}  ${path.basename(filePath)}`);
}

async function login(page, email) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 20000 });
  await page.waitForTimeout(1200);
}

/** เลือกสาขาให้ Super Admin (บทบาทอื่นถูกล็อกที่สาขาตัวเองอยู่แล้ว) */
async function selectBranch(page, value = "1") {
  const selector = page.locator("header select").first();
  if (await selector.count()) {
    await selector.selectOption(value);
    await page.waitForTimeout(1200);
  }
}

/** ตั้งค่าช่องวันที่ให้เป็นวันที่มีข้อมูลตัวอย่าง */
async function setDate(page, isoDate = DEMO_DATE) {
  const dateInput = page.locator('input[type="date"]').first();
  if (await dateInput.count()) {
    await dateInput.fill(isoDate);
    await page.waitForTimeout(1500);
  }
}

/**
 * ปิดกล่องโต้ตอบด้วยปุ่ม ✕ ของ modal เท่านั้น
 *
 * ห้ามค้นปุ่มจากข้อความอย่าง "ยกเลิก" เพราะหน้าจอคิวมีปุ่มชื่อเดียวกันอยู่ด้านหลัง
 * แล้ว overlay ของ modal จะบังการคลิกจนสคริปต์ค้าง
 */
async function closeModal(page) {
  const closeButton = page.locator('button[aria-label="ปิด"]').first();
  if (await closeButton.count()) {
    await closeButton.click();
    await page.waitForTimeout(700);
  }
}

async function gotoPage(page, urlPath) {
  await page.goto(`${BASE_URL}${urlPath}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
}

async function run() {
  await mkdir(OUTPUT_DIR, { recursive: true });
  const browser = await chromium.launch();

  // ---------------------------------------------------------------- หน้าเข้าสู่ระบบ
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    console.log("[ทุกบทบาท] หน้าเข้าสู่ระบบ");
    await capture(page, "login", {
      title: "หน้าเข้าสู่ระบบ",
      role: "ทุกบทบาท",
      description:
        "ยืนยันตัวตนด้วยอีเมลและรหัสผ่าน ระบบออก JWT แล้วเก็บไว้ใน httpOnly cookie ซึ่ง JavaScript อ่านไม่ได้",
      callouts: [
        { selector: 'input[type="email"]', text: "อีเมลที่ใช้เป็นชื่อผู้ใช้" },
        { selector: 'input[type="password"]', text: "รหัสผ่าน (จำกัดการเดา 10 ครั้ง/นาที)" },
      ],
    });
    await context.close();
  }

  // ---------------------------------------------------------------- Super Admin
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    console.log(`[${ROLES.super_admin.label}]`);
    await login(page, ROLES.super_admin.email);

    await capture(page, "superadmin-select-branch", {
      title: "สถานะเริ่มต้นของผู้ดูแลระบบสูงสุด",
      role: ROLES.super_admin.label,
      description:
        "Super Admin ไม่ได้สังกัดสาขาใด ระบบจึงขอให้เลือกสาขาที่ต้องการทำงานด้วยก่อน แทนการเดาสาขาให้",
      callouts: [{ selector: "header select", text: "ตัวเลือกสาขา (เห็นเฉพาะ Super Admin)" }],
    });

    await selectBranch(page, "1");
    await setDate(page);
    await capture(page, "superadmin-queue", {
      title: "หน้าจอคิวหน้างาน (เลือกสาขากรุงเทพ)",
      role: ROLES.super_admin.label,
      description: "เมื่อเลือกสาขาแล้ว ระบบแสดงคิวของสาขานั้นทันที พร้อมการ์ดสรุปจำนวนคิวแยกตามสถานะ",
      callouts: [{ selector: "header select", text: "สลับสาขาได้ทุกเมื่อ ข้อมูลทั้งระบบเปลี่ยนตาม" }],
    });

    await gotoPage(page, "/branches");
    await capture(page, "superadmin-branches", {
      title: "หน้าจัดการสาขา",
      role: ROLES.super_admin.label,
      description:
        "เฉพาะ Super Admin ที่เพิ่ม/แก้สาขาได้ ค่าที่ตั้งที่นี่ (เวลาทำการ ความละเอียดตาราง ความจุ) มีผลต่อการคำนวณคิวโดยตรง",
    });

    await gotoPage(page, "/reports");
    await page.waitForTimeout(2500);
    await capture(page, "superadmin-reports", {
      title: "รายงานเชิงบริหาร (ภาพรวมทุกสาขา)",
      role: ROLES.super_admin.label,
      description:
        "สรุปยอดจอง อัตราการผิดนัด เวลารอเฉลี่ย และ heatmap ช่วงเวลาที่มีผู้ใช้บริการหนาแน่น คำนวณด้วย ORM aggregation",
    });

    await context.close();
  }

  // ---------------------------------------------------------------- Admin
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    console.log(`[${ROLES.admin.label}]`);
    await login(page, ROLES.admin.email);
    await setDate(page);

    await capture(page, "admin-queue", {
      title: "หน้าจอคิวหน้างานของผู้จัดการสาขา",
      role: ROLES.admin.label,
      description:
        "ผู้จัดการสาขาถูกล็อกไว้ที่สาขาตนเองโดยอัตโนมัติ ไม่มีตัวเลือกสาขา และเห็นเฉพาะข้อมูลสาขาของตน",
      callouts: [{ selector: "aside nav", text: "เมนูจัดการแพทย์และรายงานเปิดให้เฉพาะผู้จัดการขึ้นไป" }],
    });

    await gotoPage(page, "/doctors");
    await capture(page, "admin-doctors", {
      title: "หน้าจัดการแพทย์",
      role: ROLES.admin.label,
      description:
        "แสดงแพทย์ทั้งหมดในสาขา พร้อมเตือนแพทย์ที่ยังไม่ได้ตั้งตารางออกตรวจ ซึ่งจะยังจองคิวให้ไม่ได้",
    });

    // เปิดกล่องรับแพทย์ใหม่
    const addDoctorButton = page.locator("button", { hasText: "รับแพทย์ใหม่" }).first();
    if (await addDoctorButton.count()) {
      await addDoctorButton.click();
      await page.waitForTimeout(900);
      await capture(page, "admin-doctor-create", {
        title: "กล่องรับแพทย์ใหม่เข้าทำงาน",
        role: ROLES.admin.label,
        description:
          "กรอกครั้งเดียว ระบบสร้างทั้งบัญชีล็อกอินและโปรไฟล์แพทย์ในทรานแซกชันเดียว รหัสผ่านถูกเข้ารหัสแบบ hash",
      });
      await closeModal(page);
    }

    // หน้ารายละเอียดแพทย์ (ตารางออกตรวจ + วันลา)
    const doctorLink = page.locator('a[href^="/doctors/"]').first();
    if (await doctorLink.count()) {
      await doctorLink.click();
      await page.waitForTimeout(2000);
      await capture(page, "admin-doctor-schedule", {
        title: "ตารางออกตรวจและวันลาของแพทย์",
        role: ROLES.admin.label,
        description:
          "ตารางออกตรวจคือข้อมูลตั้งต้นที่ระบบใช้คำนวณเวลาว่างทั้งหมด เพิ่มได้หลายช่วงต่อวัน และบล็อกวันลาแบบซ้ำได้",
      });
    }

    await gotoPage(page, "/reports");
    await page.waitForTimeout(2500);
    await capture(page, "admin-reports", {
      title: "รายงานของสาขา",
      role: ROLES.admin.label,
      description: "ผู้จัดการเห็นเฉพาะข้อมูลสาขาตนเอง ใช้วางแผนกำลังแพทย์ในช่วงเวลาที่มีคิวหนาแน่น",
    });

    await context.close();
  }

  // ---------------------------------------------------------------- Staff
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    console.log(`[${ROLES.staff.label}]`);
    await login(page, ROLES.staff.email);
    await setDate(page);

    await capture(page, "staff-queue", {
      title: "หน้าจอคิวหน้างาน (จอหลักของเจ้าหน้าที่)",
      role: ROLES.staff.label,
      description:
        "รายการคิวเรียงตามเวลา พร้อมปุ่มเปลี่ยนสถานะที่กดได้จริงเท่านั้นตามลำดับสถานะที่ระบบกำหนด",
      callouts: [
        { selector: "table tbody tr:first-child td:last-child", text: "ปุ่มสถานะถัดไปที่อนุญาต" },
      ],
    });

    // กล่องรับคิว walk-in
    const walkInButton = page.locator("button", { hasText: "Walk-in" }).first();
    if (await walkInButton.count()) {
      await walkInButton.click();
      await page.waitForTimeout(1200);
      await capture(page, "staff-walkin", {
        title: "กล่องรับคิว Walk-in",
        role: ROLES.staff.label,
        description:
          "ระบบจัดคิวให้ในช่วงเวลาว่างที่เร็วที่สุด ถ้าไม่มีเวลาว่างจริงจะปฏิเสธ (409) ห้ามแทรกคิวเกินความจุเด็ดขาด",
      });
      await closeModal(page);
    }

    await gotoPage(page, "/calendar");
    await setDate(page);
    await capture(page, "staff-calendar", {
      title: "ตารางแพทย์รายวัน",
      role: ROLES.staff.label,
      description:
        "คอลัมน์ละหนึ่งแพทย์ แถวละครึ่งชั่วโมง ช่องสีเทาคือเวลาที่ถูกบล็อก ช่องว่างกดเพื่อจองคิวได้ทันที",
    });

    const bookButton = page.locator("button", { hasText: "จองคิวล่วงหน้า" }).first();
    if (await bookButton.count()) {
      await bookButton.click();
      await page.waitForTimeout(1200);
      await capture(page, "staff-booking", {
        title: "กล่องจองคิวล่วงหน้า",
        role: ROLES.staff.label,
        description:
          "เลือกคนไข้ บริการ แพทย์ และวันที่ จากนั้นระบบจะแสดงเฉพาะเวลาที่ว่างจริงเท่านั้นให้กดเลือก",
      });
      await closeModal(page);
    }

    await gotoPage(page, "/patients");
    // ต้องยาวอย่างน้อย 3 หลักจึงจะเข้าเงื่อนไขค้นหาด้วยเบอร์โทร
    await page.fill('input[placeholder*="0812345678"]', "081");
    const searchButton = page.locator('button[type="submit"]', { hasText: "ค้นหา" }).first();
    if (await searchButton.count()) {
      await searchButton.click();
      await page.waitForTimeout(1500);
    }
    await capture(page, "staff-patients", {
      title: "หน้าค้นหาคนไข้",
      role: ROLES.staff.label,
      description:
        "ค้นด้วยเบอร์โทร ชื่อ หรือรหัสคนไข้ และค้นข้ามสาขาได้ เพื่อไม่ให้เกิดประวัติซ้ำเมื่อลูกค้าไปคนละสาขา",
    });

    const patientLink = page.locator('a[href^="/patients/"]').first();
    if (await patientLink.count()) {
      await patientLink.click();
      await page.waitForTimeout(2000);
      await capture(page, "staff-patient-detail", {
        title: "ประวัติคนไข้และโน้ตสะสม",
        role: ROLES.staff.label,
        description:
          "แสดงข้อมูลติดต่อ โน้ตที่ปักหมุด (เช่น ประวัติแพ้ยา) และประวัติการจองทั้งหมดของคนไข้รายนั้น",
      });
    }

    await context.close();
  }

  // ---------------------------------------------------------------- Doctor
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    console.log(`[${ROLES.doctor.label}]`);
    await login(page, ROLES.doctor.email);
    await setDate(page);

    await capture(page, "doctor-queue", {
      title: "หน้าจอคิวของแพทย์",
      role: ROLES.doctor.label,
      description:
        "แพทย์เห็นเฉพาะคิวที่ตนเองเป็นผู้ตรวจ และเปลี่ยนสถานะได้เฉพาะคิวของตนเอง (คิวของแพทย์ท่านอื่นจะถูกปฏิเสธ 403)",
      callouts: [{ selector: "aside nav", text: "เมนูจัดการแพทย์/รายงาน/สาขา ไม่แสดงสำหรับบทบาทนี้" }],
    });

    await gotoPage(page, "/calendar");
    await setDate(page);
    await capture(page, "doctor-calendar", {
      title: "ตารางแพทย์ที่แพทย์เปิดดูเอง",
      role: ROLES.doctor.label,
      description: "แพทย์ตรวจสอบตารางและช่วงเวลาที่ถูกบล็อกของตนเองได้ แต่ไม่มีสิทธิ์แก้ไขข้อมูลตั้งค่าของสาขา",
    });

    await context.close();
  }

  // ---------------------------------------------------------------- เอกสาร API
  {
    const context = await browser.newContext({ viewport: VIEWPORT, locale: "th-TH" });
    const page = await context.newPage();
    console.log("[เอกสารประกอบ] OpenAPI / Swagger UI");
    await page.goto("http://127.0.0.1:8000/api/docs/", { waitUntil: "networkidle" });
    await page.waitForTimeout(2500);
    await capture(page, "api-docs-swagger", {
      title: "เอกสาร API อัตโนมัติ (OpenAPI 3 / Swagger UI)",
      role: "ผู้พัฒนา",
      description:
        "ระบบสร้างเอกสาร API จากโค้ดโดยอัตโนมัติด้วย drf-spectacular ครอบคลุมทั้ง 30 endpoint พร้อมทดสอบเรียกใช้ได้ในหน้าเดียวกัน",
    });
    await context.close();
  }

  await browser.close();

  await writeFile(
    path.join(OUTPUT_DIR, "manifest.json"),
    JSON.stringify(manifest, null, 2),
    "utf-8",
  );
  console.log(`\nแคปเสร็จทั้งหมด ${manifest.length} ภาพ → ${OUTPUT_DIR}`);
}

run().catch((error) => {
  console.error("เกิดข้อผิดพลาด:", error.message);
  process.exit(1);
});
