#!/usr/bin/env node

import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, join } from "node:path";
import { URL } from "node:url";

const PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi";
const PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi";
const HEADERS = {
  "User-Agent": "AlzheimerDementiaBot/1.0 (research aggregator)",
  "Accept": "application/json",
};

const JOURNALS = [
  "Alzheimer's & Dementia",
  "Alzheimer's & Dementia: Diagnosis, Assessment & Disease Monitoring",
  "Alzheimer's & Dementia: Translational Research & Clinical Interventions",
  "Alzheimer Disease & Associated Disorders",
  "Journal of Alzheimer's Disease",
  "Alzheimer's Research & Therapy",
  "Current Alzheimer Research",
  "Journal of Prevention of Alzheimer's Disease",
  "Neurodegenerative Diseases",
  "Neurology",
  "JAMA Neurology",
  "Lancet Neurology",
  "Brain",
  "Annals of Neurology",
  "Nature Neuroscience",
  "Nature Medicine",
  "Nature Aging",
  "Molecular Psychiatry",
  "Biological Psychiatry",
  "Neurobiology of Aging",
  "Molecular Neurodegeneration",
  "Acta Neuropathologica",
  "New England Journal of Medicine",
  "The Lancet",
  "JAMA",
  "BMJ",
  "eBioMedicine",
  "eClinicalMedicine",
  "Age and Ageing",
  "American Journal of Geriatric Psychiatry",
  "International Psychogeriatrics",
];

const SEARCH_TOPICS = [
  {
    name: "broad-overview",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR "AD dementia"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "biomarkers",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Biomarkers"[MeSH Terms] OR biomarker*[Title/Abstract] OR "blood biomarker*"[Title/Abstract] OR plasma[Title/Abstract] OR "p-tau"[Title/Abstract] OR "amyloid PET"[Title/Abstract] OR "tau PET"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "clinical-trials",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Randomized Controlled Trial"[Publication Type] OR randomized[Title/Abstract] OR placebo[Title/Abstract] OR lecanemab[Title/Abstract] OR donanemab[Title/Abstract] OR aducanumab[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "caregiving",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract]) AND ("Caregivers"[MeSH Terms] OR caregiver*[Title/Abstract] OR "caregiver burden"[Title/Abstract] OR "family caregiving"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "nutrition-exercise",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract] OR "cognitive decline"[Title/Abstract]) AND ("Diet"[MeSH Terms] OR "Exercise"[MeSH Terms] OR "Mediterranean diet"[Title/Abstract] OR "MIND diet"[Title/Abstract] OR "physical activity"[Title/Abstract] OR sleep[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "neuroimaging",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Neuroimaging"[MeSH Terms] OR MRI[Title/Abstract] OR PET[Title/Abstract] OR "amyloid PET"[Title/Abstract] OR "tau PET"[Title/Abstract] OR fMRI[Title/Abstract] OR "cortical thickness"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "mci",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Mild Cognitive Impairment"[MeSH Terms] OR "mild cognitive impairment"[Title/Abstract] OR MCI[Title/Abstract] OR prodromal[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
  {
    name: "social-determinants",
    query: '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract]) AND ("Social Determinants of Health"[MeSH Terms] OR "Health Equity"[MeSH Terms] OR "socioeconomic status"[Title/Abstract] OR disparities[Title/Abstract] OR stigma[Title/Abstract] OR "social isolation"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
  },
];

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = { days: 7, maxPapers: 40, output: "papers.json" };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--days" && args[i + 1]) opts.days = parseInt(args[++i], 10);
    else if (args[i] === "--max-papers" && args[i + 1]) opts.maxPapers = parseInt(args[++i], 10);
    else if (args[i] === "--output" && args[i + 1]) opts.output = args[++i];
  }
  return opts;
}

function getDateNDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split("T")[0].replace(/-/g, "/");
}

function getTaipeiDate() {
  const now = new Date();
  const taipei = new Date(now.getTime() + 8 * 60 * 60 * 1000);
  return taipei.toISOString().split("T")[0];
}

function loadProcessedPmids() {
  const docsDir = resolve(process.cwd(), "docs");
  const pmids = new Set();
  if (!existsSync(docsDir)) return pmids;
  const files = readdirSync(docsDir).filter((f) => f.startsWith("alzheimer-") && f.endsWith(".html"));
  for (const f of files.slice(0, 7)) {
    const filePath = join(docsDir, f);
    try {
      const content = readFileSync(filePath, "utf-8");
      const matches = content.matchAll(/pubmed\.ncbi\.nlm\.nih\.gov\/(\d+)/g);
      for (const m of matches) pmids.add(m[1]);
    } catch {}
  }
  console.error(`[INFO] Found ${pmids.size} previously processed PMIDs`);
  return pmids;
}

async function pubmedSearch(query, retmax = 50) {
  const params = new URLSearchParams();
  params.set("db", "pubmed");
  params.set("term", query);
  params.set("retmax", String(retmax));
  params.set("sort", "date");
  params.set("retmode", "json");
  params.set("tool", "AlzheimerDementiaBot");
  params.set("email", "alzheimer-dementia-bot@users.noreply.github.com");
  const url = `${PUBMED_SEARCH}?${params.toString()}`;
  console.error(`[DEBUG] Search URL: ${url.slice(0, 200)}...`);
  try {
    const resp = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(30000) });
    const text = await resp.text();
    if (!resp.ok || text.trim().startsWith("<!")) {
      console.error(`[ERROR] PubMed search returned ${resp.status}: ${text.slice(0, 300)}`);
      return [];
    }
    const data = JSON.parse(text);
    const ids = data?.esearchresult?.idlist || [];
    const errors = data?.esearchresult?.ERRORLIST?.ERROR;
    if (errors) console.error(`[WARN] PubMed warnings: ${JSON.stringify(errors)}`);
    console.error(`[DEBUG] PubMed returned ${ids.length} IDs`);
    return ids;
  } catch (e) {
    console.error(`[ERROR] PubMed search failed: ${e.message}`);
    return [];
  }
}

async function pubmedFetch(pmids) {
  if (!pmids.length) return [];
  const params = new URLSearchParams();
  params.set("db", "pubmed");
  params.set("id", pmids.join(","));
  params.set("retmode", "xml");
  params.set("tool", "AlzheimerDementiaBot");
  params.set("email", "alzheimer-dementia-bot@users.noreply.github.com");
  const url = `${PUBMED_FETCH}?${params.toString()}`;
  console.error(`[DEBUG] Fetching ${pmids.length} PMIDs...`);
  try {
    const resp = await fetch(url, { headers: HEADERS, signal: AbortSignal.timeout(60000) });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      console.error(`[ERROR] PubMed fetch HTTP ${resp.status}: ${text.slice(0, 200)}`);
      return [];
    }
    const xml = await resp.text();
    const papers = parseXmlPapers(xml);
    console.error(`[DEBUG] Parsed ${papers.length} papers from XML`);
    return papers;
  } catch (e) {
    console.error(`[ERROR] PubMed fetch failed: ${e.message}`);
    return [];
  }
}

function parseXmlPapers(xml) {
  const papers = [];
  const articleRegex = /<PubmedArticle>([\s\S]*?)<\/PubmedArticle>/g;
  let match;
  while ((match = articleRegex.exec(xml)) !== null) {
    const block = match[1];
    const pmid = extractTag(block, "PMID");
    const title = extractTag(block, "ArticleTitle");
    const abstract = extractAbstract(block);
    const journal = extractTag(block, "<Title>");
    const dateStr = extractPubDate(block);
    const keywords = extractKeywords(block);
    const link = pmid ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : "";
    if (title || abstract) {
      papers.push({ pmid, title, journal, date: dateStr, abstract, url: link, keywords });
    }
  }
  return papers;
}

function extractTag(block, tag) {
  const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag.split(" ")[0]}>`, "m");
  const m = block.match(re);
  if (!m) return "";
  return m[1].replace(/<[^>]+>/g, "").trim();
}

function extractAbstract(block) {
  const parts = [];
  const re = /<AbstractText[^>]*Label="([^"]*)"[^>]*>([\s\S]*?)<\/AbstractText>/g;
  let m;
  while ((m = re.exec(block)) !== null) {
    const label = m[1];
    const text = m[2].replace(/<[^>]+>/g, "").trim();
    if (text) parts.push(label ? `${label}: ${text}` : text);
  }
  if (!parts.length) {
    const simpleRe = /<AbstractText>([\s\S]*?)<\/AbstractText>/g;
    while ((m = simpleRe.exec(block)) !== null) {
      const text = m[1].replace(/<[^>]+>/g, "").trim();
      if (text) parts.push(text);
    }
  }
  return parts.join(" ").slice(0, 2000);
}

function extractPubDate(block) {
  const year = extractTag(block, "Year");
  const month = extractTag(block, "Month");
  const day = extractTag(block, "Day");
  return [year, month, day].filter(Boolean).join(" ");
}

function extractKeywords(block) {
  const kws = [];
  const re = /<Keyword>([\s\S]*?)<\/Keyword>/g;
  let m;
  while ((m = re.exec(block)) !== null) {
    const t = m[1].trim();
    if (t) kws.push(t);
  }
  return kws;
}

async function main() {
  const opts = parseArgs();
  const targetDate = process.env.TARGET_DATE || getTaipeiDate();
  const lookback = getDateNDaysAgo(opts.days);
  console.error(`[INFO] Searching PubMed for AD papers from last ${opts.days} days (since ${lookback})...`);

  const processedPmids = loadProcessedPmids();
  const allPmids = new Set();

  for (const topic of SEARCH_TOPICS) {
    const dateFilter = `"${lookback}"[Date - Publication] : "3000"[Date - Publication]`;
    const fullQuery = `${topic.query} AND ${dateFilter}`;
    console.error(`[INFO] Searching topic: ${topic.name}...`);
    const pmids = await pubmedSearch(fullQuery, Math.min(20, opts.maxPapers));
    for (const id of pmids) allPmids.add(id);
  }

  const newPmids = [...allPmids].filter((id) => !processedPmids.has(id));
  console.error(`[INFO] Total unique PMIDs: ${allPmids.size}, new (unprocessed): ${newPmids.length}`);

  if (!newPmids.length) {
    console.error("[INFO] No new papers found");
    const output = { date: targetDate, count: 0, papers: [] };
    writeFileSync(opts.output, JSON.stringify(output, null, 2), "utf-8");
    return;
  }

  const papersToFetch = newPmids.slice(0, opts.maxPapers);
  const papers = await pubmedFetch(papersToFetch);
  console.error(`[INFO] Fetched details for ${papers.length} papers`);

  const output = { date: targetDate, count: papers.length, papers };
  writeFileSync(opts.output, JSON.stringify(output, null, 2), "utf-8");
  console.error(`[INFO] Saved to ${opts.output}`);
}

main().catch((e) => {
  console.error(`[FATAL] ${e.message}`);
  process.exit(1);
});
