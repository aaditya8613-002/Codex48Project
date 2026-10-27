# BrandGuard — Intelligent Brand Governance & Pre-Publication Review Platform

**Problem Statement by Inkloom AI**  
**Team Name:** Brand New Minds  
**Team Members:** Advait Sachin Keskar & Aaditya Gupta  
**College:** CMRIT, Bengaluru  

---

## 🌟 Executive Summary

Growing organisations publish content across distributed teams, external marketing agencies, and generative AI tools. Outdated statistics, inconsistent terminology, misleading promotional claims, and inaccessible designs often slip into production before anyone catches them.

**BrandGuard** is a brand governance platform that reviews content *before* publication, checking it against approved guidelines, verified facts, and WCAG accessibility standards. Rather than functioning as a black-box censor, BrandGuard explains every flagged issue, cites the exact source evidence, and suggests human-centered corrections that preserve creator intent.

---

## 🚀 Key Capabilities & Modules

### 1. Pre-Flight Content Studio & Multi-Format Review
- **Exact Code Rules Engine (No AI Needed):**
  - **Terminology Protection:** Ensures protected product naming (e.g. `FlowDesk`, catching variants like `flowdesk`, `Flow Desk`, `FLOWDESK`).
  - **Prohibited Words & Metaphors:** Detects violent idioms (e.g., `killer feature`), aggressive hype words (`revolutionary`), and risky absolute guarantees (`100% secure`, `guaranteed`).
  - **WCAG 2.2 Color Contrast Formula:** Audits HTML inline styles and hex combinations against AA (4.5:1) and AAA (7.0:1) thresholds.
  - **Accessibility Alt-Text Scanner:** Checks image tags and markdown embeddings for missing or placeholder descriptions.
  - **Brand Palette Validator:** Scans dominant graphic colors against approved corporate palette hex codes.
- **Claim & Metric Adjudication:**
  - Extracts numeric claims and temporal metrics from copy, comparing them with dated fact sheets.
  - Returns explicit verdicts: `supported`, `contradicted`, or `cannot_verify` (safeguard against uncorroborated superlatives).
- **Grounded AI Tone & Messaging (Google Gemini):**
  - Evaluates brand tone bounded strictly by retrieved brand guideline passages.
  - Code-level validation: any finding that cites non-existent passages or quotes absent from the copy is discarded or downgraded.

### 2. Review & Approval Collaboration Pipeline
- **Multi-Role Simulation:**
  - ✍️ **Maya (Content Creator):** Runs pre-flight scans, accepts 1-click suggested fixes, provides rationales when dismissing findings, and submits drafts.
  - 👔 **Jordan (Brand Marketing Manager):** Reviews drafts in the pipeline, audits tone alignment, approves copy, or requests revisions with feedback notes.
  - ⚖️ **Rachel (Legal & Compliance Reviewer):** Verifies claims against approved fact sheets and checks statutory disclosures.
  - 🛡️ **Aaditya (Brand Governance Admin):** Maintains facts, terms, documents, and monitors organizational brand health.
- **Revision History Timeline:**
  - Every draft modification creates a numbered revision (`v1`, `v2`, ...) with change summaries and diff tracking.
- **Threaded Collaboration:**
  - Real-time discussion threads between creators, managers, and legal reviewers on drafts and specific rules.
- **Tamper-Evident Audit Trail:**
  - Complete log recording timestamps, actor identities, roles, and action types (`CREATED`, `SUBMITTED`, `CHANGES_REQUESTED`, `APPROVED`, `PUBLISHED`).

### 3. Brand Kit & Knowledge Base
- **Approved Fact Sheet:** Dated, versioned facts with normalized numbers, units, and proof sources.
- **Interactive WCAG Contrast Simulator:** Live playground to test foreground/background pairs with instant ratio readouts and suggested brand palette alternatives.
- **Terminology & Banned Phrases Dictionary:** Configurable rule base with severity ratings and rationale.
- **Guideline Document Ingestion:** Parses `.pdf`, `.docx`, `.txt`, `.md` files into vector embeddings for semantic retrieval.

### 4. Governance Insights & Guideline Confusion Index
- **Brand Health Index:** Aggregate compliance score reflecting resolved vs open issues across content.
- **Guideline Confusion Index:** Ranks brand guidelines by creator dismissal rate. High dismissal indicates ambiguous, outdated, or overly restrictive rules requiring clarification.
- **Violation Breakdown by Category:** Visual distribution across Terminology, Claims, Accessibility, and Voice.

---

## 📊 Empirical Evaluation Benchmark

BrandGuard was evaluated on an automated benchmark test set of 30 items (`eval/testset.json`):
- **20 Planted Mistake Items (22 expected errors):** Terminology drift, outdated metrics, banned hype, contrast failures, and missing alt text.
- **10 Clean Control Items:** Compliant copy passing all brand rules.

```text
Planted mistakes found : 22/22 (Recall: 100%)
False alarms on clean  : 0
Extra findings         : 1
```

---

## 🛠️ Technology Stack

| Layer | Technologies | Role |
|---|---|---|
| **Frontend** | React, Vite, Vanilla CSS Design System, Lucide Icons | Responsive governance workspace with role switching, diffs, and live contrast simulator |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | REST API, rules engine, claim extraction, and review orchestration |
| **Database** | SQLAlchemy 2.0, SQLite / TiDB Cloud (MySQL compatible) | Relational storage for orgs, reviews, revisions, findings, comments, and audit trails |
| **AI / Grounding** | Google Gemini API (`gemini-2.5-flash`), `google-genai` | Grounded tone review and semantic claim adjudication |
| **Document Parsing** | `pdfplumber`, `python-docx`, `Pillow` | Guideline extraction and image palette analysis |

---

## ⚡ Quick Start & Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# In Codex48Project-main:
python -m venv venv
.\venv\Scripts\activate      # Windows (or source venv/bin/activate on Unix)
pip install -r requirements.txt

# Initialize database and seed sample kit & reviews:
python -m app.seed

# Run tests:
pytest

# Run FastAPI server on port 8000:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open **`http://127.0.0.1:5173/`** in your browser.

*(Note: FastAPI also serves the built static frontend directly at `http://127.0.0.1:8000/` when built with `npm run build`.)*

---

## 🎬 1-Click Judging Demo Scenarios

In the **Demo Presets** tab of the web app, judges can test 4 scenarios with a single click:

1. **Scenario #1: Outdated Customer Metrics & Hype**  
   *Flags:* Outdated customer count ("5 million" vs 3M in fact sheet), prohibited phrase `100% secure`, `guaranteed`, `revolutionary`, and violent idiom `killer feature`.
2. **Scenario #2: Inaccessible Web Hero & Bad Contrast**  
   *Flags:* `#cccccc` on `#ffffff` contrast ratio 1.6:1 (fails WCAG AA 4.5:1), casing variant `flowdesk`, prohibited word `cheap`, contradicted price `$9`, missing image alt text.
3. **Scenario #3: Unverified Market Superlatives**  
   *Flags:* Superlative `fastest cloud workspace` (cannot verify), `Revenue grew 45%` (cannot verify), `60 countries` (contradicts 40 countries).
4. **Scenario #4: Official Benchmark Control**  
   *Result:* 100% verified, 0 violations against Northwind Fact Sheet v3.

---

## 👥 Team Responsibilities

- **Advait Sachin Keskar:** Knowledge base & semantic retrieval, exact rules engine, claim verification, Gemini grounded review prompts, database schema, and accuracy evaluation harness.
- **Aaditya Gupta:** Frontend architecture & UI design system, review and approval pipeline, revision history and diff tracking, threaded collaboration comments, governance insights dashboard, and demo scenarios.

---

## ⚖️ Responsible AI & Ethical Declarations
- **Human-in-the-Loop:** Suggestions are advisory. Decisions are made and approved by human creators and managers.
- **Explainability:** Every finding cites the specific brand guideline passage or dated fact sheet item.
- **Confidentiality:** Bounded context retrieval prevents leakage, and data is partitioned strictly per organization.
- Code developed with AI pair-programming assistance as permitted by hackathon guidelines.
