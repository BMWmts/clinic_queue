/**
 * ตรวจไวยากรณ์และเรนเดอร์แผนภาพ Mermaid ทั้งหมดใน thesis.md ออกเป็นไฟล์ SVG/PNG
 *
 * ใช้ Chromium ของ Playwright ที่ติดตั้งอยู่แล้ว จึงไม่ต้องดาวน์โหลดเบราว์เซอร์เพิ่ม
 * รัน: node render-diagrams.mjs
 */
import { chromium } from "playwright";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const THESIS_PATH = "C:/Users/M/Desktop/clinic/thesis.md";
const OUTPUT_DIR = "C:/Users/M/Desktop/clinic/assets/diagrams";
const MERMAID_PATH = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "node_modules/mermaid/dist/mermaid.min.js",
);

/** ดึงบล็อก mermaid พร้อมหัวข้อที่อยู่เหนือบล็อกนั้น เพื่อใช้ตั้งชื่อไฟล์ */
function extractDiagrams(markdown) {
  const lines = markdown.split(/\r?\n/);
  const diagrams = [];
  let currentHeading = "diagram";

  for (let index = 0; index < lines.length; index += 1) {
    const headingMatch = lines[index].match(/^#{3,4}\s+([\d.]+)\s+(.+)$/);
    if (headingMatch) {
      currentHeading = `${headingMatch[1].replace(/\.$/, "")} ${headingMatch[2]}`;
    }

    if (lines[index].trim() === "```mermaid") {
      const body = [];
      let cursor = index + 1;
      while (cursor < lines.length && lines[cursor].trim() !== "```") {
        body.push(lines[cursor]);
        cursor += 1;
      }
      diagrams.push({ heading: currentHeading, code: body.join("\n"), line: index + 1 });
      index = cursor;
    }
  }
  return diagrams;
}

function toFileName(heading, order) {
  const slug = heading
    .replace(/[^\u0E00-\u0E7Fa-zA-Z0-9. ]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .slice(0, 60);
  return `${String(order).padStart(2, "0")}-${slug}`;
}

async function run() {
  const markdown = await readFile(THESIS_PATH, "utf-8");
  const diagrams = extractDiagrams(markdown);
  console.log(`พบแผนภาพ Mermaid ${diagrams.length} รายการใน thesis.md\n`);

  await mkdir(OUTPUT_DIR, { recursive: true });
  const mermaidSource = await readFile(MERMAID_PATH, "utf-8");

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
  await page.setContent("<!doctype html><html><body></body></html>");
  await page.addScriptTag({ content: mermaidSource });
  await page.evaluate(() => {
    window.mermaid.initialize({ startOnLoad: false, theme: "default", fontFamily: "Segoe UI, Sarabun, sans-serif" });
  });

  let failures = 0;

  for (const [index, diagram] of diagrams.entries()) {
    const order = index + 1;
    const result = await page.evaluate(
      async ({ code, id }) => {
        try {
          await window.mermaid.parse(code);
          const { svg } = await window.mermaid.render(id, code);
          return { ok: true, svg };
        } catch (error) {
          return { ok: false, message: String(error.message ?? error) };
        }
      },
      { code: diagram.code, id: `diagram_${order}` },
    );

    if (!result.ok) {
      failures += 1;
      console.log(`  ✗ [${order}] บรรทัด ${diagram.line} — ${diagram.heading}`);
      console.log(`      ${result.message.split("\n")[0]}`);
      continue;
    }

    const baseName = toFileName(diagram.heading, order);
    await writeFile(path.join(OUTPUT_DIR, `${baseName}.svg`), result.svg, "utf-8");

    // แปลงเป็น PNG ความละเอียดสูงสำหรับนำไปวางในเอกสาร Word
    const svgPage = await browser.newPage({ viewport: { width: 2000, height: 1400 }, deviceScaleFactor: 2 });
    await svgPage.setContent(
      `<html><body style="margin:0;background:#fff;display:inline-block">${result.svg}</body></html>`,
    );
    // Mermaid ใส่ max-width ไว้ทำให้ภาพเล็กและความละเอียดต่ำ
    // จึงบังคับความกว้างตามสัดส่วนจริงของ viewBox ก่อนแคปภาพ
    await svgPage.evaluate(() => {
      const svg = document.querySelector("svg");
      const viewBox = svg.getAttribute("viewBox").split(/\s+/).map(Number);
      const [, , boxWidth, boxHeight] = viewBox;
      const targetWidth = Math.min(1800, Math.max(900, boxWidth));
      svg.style.maxWidth = "none";
      svg.style.width = `${targetWidth}px`;
      svg.style.height = `${(boxHeight / boxWidth) * targetWidth}px`;
    });
    const element = await svgPage.$("svg");
    await element.screenshot({ path: path.join(OUTPUT_DIR, `${baseName}.png`) });
    await svgPage.close();

    console.log(`  ✓ [${order}] ${baseName}`);
  }

  await browser.close();

  console.log(
    failures === 0
      ? `\nแผนภาพทั้ง ${diagrams.length} รายการมีไวยากรณ์ถูกต้อง และบันทึกเป็น SVG/PNG แล้ว`
      : `\nมีแผนภาพที่ไวยากรณ์ผิด ${failures} รายการ`,
  );
  process.exit(failures === 0 ? 0 : 1);
}

run().catch((error) => {
  console.error("เกิดข้อผิดพลาด:", error);
  process.exit(1);
});
