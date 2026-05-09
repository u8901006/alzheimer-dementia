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
EUROPEPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

HEADERS = {"User-Agent": "AlzheimerDementiaBot/1.0 (research aggregator; +https://github.com/u8901006/alzheimer-dementia)"}

JOURNALS = [
    "Alzheimer's & Dementia",
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
    "Age and Ageing",
    "American Journal of Geriatric Psychiatry",
    "New England Journal of Medicine",
    "The Lancet",
    "JAMA",
    "BMJ",
    "eBioMedicine",
    "eClinicalMedicine",
    "International Psychogeriatrics",
    "Frontiers in Dementia",
]


def build_journal_query(journals, days):
    journal_part = " OR ".join([f'"{j}"[Journal]' for j in journals[:15]])
    lookback = get_date_n_days_ago(days)
    date_part = f'"{lookback}"[Date - Publication] : "3000"[Date - Publication]'
    ad_terms = '("Alzheimer Disease"[MeSH Terms] OR "Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] OR dementia[Title/Abstract] OR "mild cognitive impairment"[Title/Abstract])'
    return f"({journal_part}) AND {date_part} AND {ad_terms} AND NOT (animals[MeSH Terms] NOT humans[MeSH Terms])"


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
            body = resp.read().decode()
            if not body or not body.strip():
                print(f"[WARN] PubMed returned empty body for query (len={len(query)})", file=sys.stderr)
                return []
            if body.strip().startswith("<!") or body.strip().startswith("<html"):
                print(f"[ERROR] PubMed returned HTML: {body[:200]}", file=sys.stderr)
                return []
            data = json.loads(body)
            ids = data.get("esearchresult", {}).get("idlist", [])
            print(f"[INFO] PubMed returned {len(ids)} IDs", file=sys.stderr)
            return ids
    except json.JSONDecodeError as e:
        print(f"[ERROR] PubMed JSON parse failed: {e} (body[:200]={body[:200] if 'body' in dir() else 'N/A'})", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[ERROR] PubMed search failed: {e}", file=sys.stderr)
        return []


def search_europepmc(days, max_papers=40):
    query = 'Alzheimer OR dementia OR "mild cognitive impairment"'
    params = f"?query={quote_plus(query)}&resultType=core&pageSize={max_papers}&format=json&cursorMark=*&sort={quote_plus('DATE desc')}"
    url = EUROPEPMC_SEARCH + params
    print(f"[INFO] Searching Europe PMC...", file=sys.stderr)
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
        if not body or not body.strip():
            print("[WARN] Europe PMC returned empty body", file=sys.stderr)
            return []
        if body.strip().startswith("<"):
            print(f"[ERROR] Europe PMC returned HTML: {body[:200]}", file=sys.stderr)
            return []
        data = json.loads(body)
        hit_count = data.get("hitCount", 0)
        print(f"[INFO] Europe PMC total hit count: {hit_count}", file=sys.stderr)
        results = data.get("resultList", {}).get("result", [])
        papers = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for r in results:
            pub_date_str = r.get("firstPublicationDate", "")
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                    if pub_date < cutoff:
                        continue
                except Exception:
                    pass
            pmid = r.get("pmid", "")
            title = r.get("title", "")
            journal = r.get("journalTitle", "")
            abstract = r.get("abstractText", "")[:2000] if r.get("abstractText") else ""
            date_str = pub_date_str
            url_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            if not url_link and r.get("doi"):
                url_link = f"https://doi.org/{r['doi']}"
            keywords = r.get("keywordList", {}).get("keyword", [])
            if isinstance(keywords, str):
                keywords = [keywords]
            if title:
                papers.append({
                    "pmid": pmid or r.get("id", ""),
                    "title": title,
                    "journal": journal,
                    "date": date_str,
                    "abstract": abstract,
                    "url": url_link,
                    "keywords": keywords,
                })
        print(f"[INFO] Europe PMC returned {len(papers)} recent papers", file=sys.stderr)
        return papers
    except Exception as e:
        print(f"[ERROR] Europe PMC search failed: {e}", file=sys.stderr)
        return []
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

    print(f"[INFO] Attempting PubMed with journal-based query...", file=sys.stderr)
    query = build_journal_query(JOURNALS, args.days)
    pmids = search_papers(query, args.max_papers)
    all_pmids = set(pmids)

    if not all_pmids:
        print("[INFO] PubMed returned no results, trying Europe PMC...", file=sys.stderr)
        papers = search_europepmc(args.days, args.max_papers)
        if not papers:
            print("[INFO] No papers from any source", file=sys.stderr)
            output_data = {"date": target_date, "count": 0, "papers": []}
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            return

        new_papers = [p for p in papers if p["pmid"] not in processed_pmids]
        print(f"[INFO] Europe PMC: {len(new_papers)} new papers (filtered from {len(papers)})", file=sys.stderr)

        output_data = {"date": target_date, "count": len(new_papers), "papers": new_papers[:args.max_papers]}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Saved to {args.output}", file=sys.stderr)
        return

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
