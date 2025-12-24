# CDX Web Scan  
**Internal Intake & Scan Application (PWA)**

## Overview

`cdx-web-scan` is the **internal-facing intake application** for the CDX platform.  
It provides a mobile-friendly, utility-first interface for capturing physical “widgets” (CDs) and submitting them into an enterprise-style intake pipeline.

While CDs are the concrete input, this application is intentionally designed to model a **generic enterprise intake UI**, similar to those used for:

- inventory receiving
- asset onboarding
- order entry
- warehouse intake
- document capture systems

The focus is on **intake mechanics, batching, validation, and durability**, not media playback.

---

## Purpose

The primary goal of `cdx-web-scan` is to model the **front edge of an enterprise intake workflow**:

> **Capture → Validate → Batch → Submit → Queue**

It is optimized for **speed, accuracy, and operational efficiency**, rather than rich client-side behavior.

---

## Key Responsibilities

- Mobile-friendly **Progressive Web App (PWA)** interface
- Camera-based barcode scanning
- Manual barcode entry fallback
- Batch intake sessions
- Intake metadata and tagging
- Submission of validated intake jobs to the cloud intake API
- Clear operator feedback (accepted / rejected / pending)

---

## What This App Is *Not*

- ❌ A public-facing application  
- ❌ A streaming or playback interface  
- ❌ A heavy single-page application (SPA)  

This is an **internal utility**, intentionally simple and task-focused.

---

## Technology Stack

### Application Layer
- **Python**
- **Flask**
- **HTMX**
- **Jinja2 templates**

### Front-End Behavior
- **Minimal JavaScript**
  - Camera access
  - Barcode decoding
  - PWA support
- Server-rendered HTML with HTMX-driven updates

### PWA Features
- Installable on mobile devices
- App manifest and service worker
- Offline-aware design (future phase)

---

## Deployment Model

- Runs **on-prem / homelab**
- Served behind **NGINX**
- Accessible only via **NetBird (Zero Trust VPN)**
- No public exposure
- Communicates outbound to the cloud intake API

This mirrors modern enterprise patterns where **intake tools are private, internal systems**.

---

## Role in the CDX Platform

`cdx-web-scan` is one of four deployment-aligned components in CDX:

[ cdx-web-scan ] → [ cdx-intake-api ] → [ AWS SQS ] → [ cdx-enrich-worker ] → [ PostgreSQL ] → [ cdx-web-user ]


This separation ensures:
- clear security boundaries
- independent scaling
- realistic enterprise architecture modeling

---

## Enterprise Pattern Modeled

This repository intentionally models an **enterprise intake / receiving application**, such as:

- warehouse receiving UI
- asset registration portal
- order intake system
- document ingestion front-end

The use of CDs is incidental; the **workflow and architecture** are the core focus.

---

## Repository Structure (Initial)

```cdx-web-scan/
├── cdx_web_scan/
│ ├── app.py
│ ├── routes/
│ ├── templates/
│ └── static/
│ └── brand/
├── docs/
│ └── roadmap.md
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Roadmap

### Phase 1 (Current)
- Vision and UX definition
- Repository scaffolding
- Branding and UI mockups

### Phase 2
- Camera-based barcode scanning
- Batch intake sessions
- Intake API integration
- Operator feedback and validation

### Phase 3
- Offline-aware batching
- Enhanced intake metadata
- Error handling and retry visibility

See `docs/roadmap.md` for details.

---

## Design Philosophy

> **Boring, predictable, and reliable — in the best possible way.**

This application favors:
- clarity over cleverness
- server-rendered HTML over heavy client frameworks
- explicit workflows over implicit magic

These are deliberate choices aligned with how real enterprise intake systems are built and maintained.

---

## License

MIT License


