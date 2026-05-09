#!/usr/bin/env node

import { readdirSync, writeFileSync, readFileSync } from "node:fs";
import { resolve, join } from "node:path";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
const DOCS_DIR = resolve(process.cwd(), "docs");

function generateIndex() {
  let files = [];
  try {
    files = readdirSync(DOCS_DIR)
      .filter((f) => f.startsWith("alzheimer-") && f.endsWith(".html") && f !== "index.html")
      .sort()
      .reverse();
  } catch {
    console.error("[WARN] docs/ directory not found or empty");
    return;
  }

  const links = files.slice(0, 60).map((f) => {
    const date = f.replace("alzheimer-", "").replace(".html", "");
    let display = date;
    let weekday = "";
    try {
      const d = new Date(date);
      const y = d.getFullYear();
      const m = d.getMonth() + 1;
      const day = d.getDate();
      display = `${y}年${m}月${day}日`;
      weekday = `（週${WEEKDAYS[d.getDay()]}）`;
    } catch {}
    return `<li><a href="${f}">&#x1F4C5; ${display}${weekday}</a></li>`;
  }).join("\n");

  const total = files.length;

  const html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Alzheimer Dementia Daily &middot; 阿茲海默症文獻日報</title>
<style>
  :root { --bg: #f6f1e8; --surface: #fffaf2; --line: #d8c5ab; --text: #2b2118; --muted: #766453; --accent: #8c4f2b; --accent-soft: #ead2bf; }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: radial-gradient(circle at top, #fff6ea 0, var(--bg) 55%, #ead8c6 100%); color: var(--text); font-family: "Noto Sans TC", "PingFang TC", "Helvetica Neue", Arial, sans-serif; min-height: 100vh; }
  .container { position: relative; z-index: 1; max-width: 640px; margin: 0 auto; padding: 80px 24px; }
  .logo { font-size: 48px; text-align: center; margin-bottom: 16px; }
  h1 { text-align: center; font-size: 24px; color: var(--text); margin-bottom: 8px; }
  .subtitle { text-align: center; color: var(--accent); font-size: 14px; margin-bottom: 48px; }
  .count { text-align: center; color: var(--muted); font-size: 13px; margin-bottom: 32px; }
  ul { list-style: none; }
  li { margin-bottom: 8px; }
  a { color: var(--text); text-decoration: none; display: block; padding: 14px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; transition: all 0.2s; font-size: 15px; }
  a:hover { background: var(--accent-soft); border-color: var(--accent); transform: translateX(4px); }
  .links-section { margin-top: 48px; }
  .link-card { display: flex; align-items: center; gap: 14px; padding: 18px 24px; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; text-decoration: none; color: var(--text); transition: all 0.2s; margin-bottom: 10px; }
  .link-card:hover { border-color: var(--accent); transform: translateX(4px); background: var(--accent-soft); }
  .link-icon { font-size: 24px; flex-shrink: 0; }
  .link-name { font-size: 14px; font-weight: 600; flex: 1; }
  .link-arrow { font-size: 16px; color: var(--accent); }
  footer { margin-top: 56px; text-align: center; font-size: 12px; color: var(--muted); }
  footer a { display: inline; padding: 0; background: none; border: none; color: var(--muted); }
  footer a:hover { color: var(--accent); }
</style>
</head>
<body>
<div class="container">
  <div class="logo">&#x1F9E0;</div>
  <h1>Alzheimer Dementia Daily</h1>
  <p class="subtitle">阿茲海默症文獻日報 &middot; 每日自動更新</p>
  <p class="count">共 ${total} 期日報</p>
  <ul>${links}</ul>
  <div class="links-section">
    <a href="https://www.leepsyclinic.com/" class="link-card" target="_blank">
      <span class="link-icon">&#x1F3E5;</span>
      <span class="link-name">李政洋身心診所首頁</span>
      <span class="link-arrow">&#8594;</span>
    </a>
    <a href="https://blog.leepsyclinic.com/" class="link-card" target="_blank">
      <span class="link-icon">&#x1F4E8;</span>
      <span class="link-name">訂閱電子報</span>
      <span class="link-arrow">&#8594;</span>
    </a>
    <a href="https://buymeacoffee.com/CYlee" class="link-card" target="_blank">
      <span class="link-icon">&#x2615;</span>
      <span class="link-name">Buy Me a Coffee</span>
      <span class="link-arrow">&#8594;</span>
    </a>
  </div>
  <footer>
    <p>Powered by PubMed + Zhipu AI &middot; <a href="https://github.com/u8901006/alzheimer-dementia">GitHub</a></p>
  </footer>
</div>
</body>
</html>`;

  writeFileSync(join(DOCS_DIR, "index.html"), html, "utf-8");
  console.error("[INFO] Index page generated");
}

generateIndex();
