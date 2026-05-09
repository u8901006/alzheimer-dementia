#!/usr/bin/env python3
"""
Fetch latest Alzheimer's disease & dementia research papers from PubMed E-utilities API.
Uses search strategies from alzheimers_disease_literature_search_toolkit.md
"""

import json
import sys
import os
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

HEADERS = {"User-Agent": "AlzheimerDementiaBot/1.0 (research aggregator; +https://github.com/u8901006/alzheimer-dementia)"}

SEARCH_TOPICS = [
    {
        "name": "broad-overview",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR "AD dementia"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "biomarkers",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Biomarkers"[MeSH Terms] OR biomarker*[Title/Abstract] OR "blood biomarker*"[Title/Abstract] OR plasma[Title/Abstract] OR "p-tau"[Title/Abstract] OR "amyloid PET"[Title/Abstract] OR "tau PET"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "clinical-trials",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Randomized Controlled Trial"[Publication Type] OR randomized[Title/Abstract] OR placebo[Title/Abstract] OR lecanemab[Title/Abstract] OR donanemab[Title/Abstract] OR aducanumab[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "caregiving",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract]) AND ("Caregivers"[MeSH Terms] OR caregiver*[Title/Abstract] OR "caregiver burden"[Title/Abstract] OR "family caregiving"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "nutrition-exercise",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract] OR "cognitive decline"[Title/Abstract]) AND ("Diet"[MeSH Terms] OR "Exercise"[MeSH Terms] OR "Mediterranean diet"[Title/Abstract] OR "MIND diet"[Title/Abstract] OR "physical activity"[Title/Abstract] OR sleep[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "neuroimaging",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Neuroimaging"[MeSH Terms] OR MRI[Title/Abstract] OR PET[Title/Abstract] OR "amyloid PET"[Title/Abstract] OR "tau PET"[Title/Abstract] OR fMRI[Title/Abstract] OR "cortical thickness"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "mci",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract]) AND ("Mild Cognitive Impairment"[MeSH Terms] OR "mild cognitive impairment"[Title/Abstract] OR MCI[Title/Abstract] OR prodromal[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
    {
        "name": "social-determinants",
        "query": '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract]) AND ("Social Determinants of Health"[MeSH Terms] OR "Health Equity"[MeSH Terms] OR "socioeconomic status"[Title/Abstract] OR disparities[Title/Abstract] OR stigma[Title/Abstract] OR "social isolation"[Title/Abstract]) AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])',
    },
]


def get_taipei_date():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def get_date_n_days_ago(n):
    d = datetime.now(timezone.utc) - timedelta(days=n)
    return d.strftime("%Y/%m/%d")


def load_processed_pmids():
    docs_dir = os.path.join(os.getcwd(), "docs")
    pmids = set()
    if not os.path.isdir(docs_dir):
        return pmids
    files = sorted(
        [f for f in os.listdir(docs_dir) if f.startswith("alzheimer-") and f.endswith(".html")],
        reverse=True,
    )
    for f in files[:7]:
        try:
            content = open(os.path.join(docs_dir, f), encoding="utf-8").read()
            import re

            for m in re.finditer(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", content):
                pmids.add(m.group(1))
        except Exception:
            pass
    print(f"[INFO] Found {len(pmids)} previously processed PMIDs", file=sys.stderr)
    return pmids


def search_papers(query, retmax=50):
    params = f"?db=pubmed&term={quote_plus(query)}&retmax={retmax}&sort=date&retmode=json"
    url = PUBMED_SEARCH + params
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[ERROR] PubMed search failed: {e}", file=sys.stderr)
        return []


def fetch_details(pmids):
    if not pmids:
        return []
    ids = ",".join(pmids)
    params = f"?db=pubmed&id={ids}&retmode=xml"
    url = PUBMED_FETCH + params
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as resp:
            xml_data = resp.read().decode()
    except Exception as e:
        print(f"[ERROR] PubMed fetch failed: {e}", file=sys.stderr)
        return []

    papers = []
    try:
        root = ET.fromstring(xml_data)
        for article in root.findall(".//PubmedArticle"):
            medline = article.find(".//MedlineCitation")
            art = medline.find(".//Article") if medline is not None else None
            if art is None:
                continue

            title_el = art.find(".//ArticleTitle")
            title = (title_el.text or "").strip() if title_el is not None and title_el.text else ""

            abstract_parts = []
            for abs_el in art.findall(".//Abstract/AbstractText"):
                label = abs_el.get("Label", "")
                text = "".join(abs_el.itertext()).strip()
                if label and text:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)[:2000]

            journal_el = art.find(".//Journal/Title")
            journal = (journal_el.text or "").strip() if journal_el is not None and journal_el.text else ""

            pub_date = art.find(".//PubDate")
            date_str = ""
            if pub_date is not None:
                year = pub_date.findtext("Year", "")
                month = pub_date.findtext("Month", "")
                day = pub_date.findtext("Day", "")
                date_str = " ".join(p for p in [year, month, day] if p)

            pmid_el = medline.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            keywords = []
            for kw in medline.findall(".//KeywordList/Keyword"):
                if kw.text:
                    keywords.append(kw.text.strip())

            if title or abstract:
                papers.append(
                    {
                        "pmid": pmid,
                        "title": title,
                        "journal": journal,
                        "date": date_str,
                        "abstract": abstract,
                        "url": link,
                        "keywords": keywords,
                    }
                )
    except ET.ParseError as e:
        print(f"[ERROR] XML parse failed: {e}", file=sys.stderr)

    return papers


def main():
    parser = argparse.ArgumentParser(description="Fetch Alzheimer's disease papers from PubMed")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-papers", type=int, default=40)
    parser.add_argument("--output", default="papers.json")
    args = parser.parse_args()

    target_date = os.environ.get("TARGET_DATE", get_taipei_date())
    lookback = get_date_n_days_ago(args.days)
    print(f"[INFO] Searching PubMed for AD papers from last {args.days} days (since {lookback})...", file=sys.stderr)

    processed_pmids = load_processed_pmids()
    all_pmids = set()

    for topic in SEARCH_TOPICS:
        date_filter = f'"{lookback}"[Date - Publication] : "3000"[Date - Publication]'
        full_query = f"{topic['query']} AND {date_filter}"
        print(f"[INFO] Searching topic: {topic['name']}...", file=sys.stderr)
        pmids = search_papers(full_query, min(20, args.max_papers))
        for id in pmids:
            all_pmids.add(id)

    new_pmids = [id for id in all_pmids if id not in processed_pmids]
    print(f"[INFO] Total unique PMIDs: {len(all_pmids)}, new (unprocessed): {len(new_pmids)}", file=sys.stderr)

    if not new_pmids:
        print("[INFO] No new papers found", file=sys.stderr)
        output_data = {"date": target_date, "count": 0, "papers": []}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        return

    papers_to_fetch = new_pmids[: args.max_papers]
    papers = fetch_details(papers_to_fetch)
    print(f"[INFO] Fetched details for {len(papers)} papers", file=sys.stderr)

    output_data = {"date": target_date, "count": len(papers), "papers": papers}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
