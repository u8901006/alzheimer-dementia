# Alzheimer Dementia Daily Report

阿茲海默症與失智症文獻日報，每日自動更新。

- 資料來源：PubMed
- AI 分析：NVIDIA NIM Nemotron 3（主要模型：`nvidia/nemotron-3-super-120b-a12b`；備用模型：`nvidia/nemotron-3-nano-30b-a3b`）
- 部署：GitHub Pages
- 排程：每天 GMT+8 19:20 自動執行

## 架構

```
scripts/
  fetch-papers.mjs     # 從 PubMed 抓取文獻
  generate-report.mjs  # AI 分析並生成 HTML 日報
  generate-index.mjs   # 生成首頁索引
```

## 本地測試

```bash
# 需要設定環境變數
export NVIDIA_API_KEY="your-api-key"

# 抓取文獻
node scripts/fetch-papers.mjs --days 7 --max-papers 40 --output papers.json

# 生成日報
node scripts/generate-report.mjs --input papers.json --output docs/alzheimer-2026-05-09.html

# 生成索引
node scripts/generate-index.mjs
```
