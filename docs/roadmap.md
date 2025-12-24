# CDX Web Scan – Roadmap

This roadmap outlines the phased development of **cdx-web-scan**, the internal
scan and intake application for the CDX platform.

The goal of this application is to model a **realistic enterprise intake
workflow**, emphasizing reliability, batching, validation, and clear operator
feedback rather than rich client-side behavior.

---

## Phase 1 – Vision & Scaffolding

**Objective:**  
Define the product vision, UX direction, and repository structure before
implementation begins.

### Scope
- Product vision and problem statement
- UX/UI mockups for scan and intake flows
- Branding and design language
- Repository scaffolding and documentation
- High-level architecture definition

### Deliverables
- Vision blog post
- UI mockups (scan, batch, intake)
- README.md
- roadmap.md

---

## Phase 2 – Intake MVP

**Objective:**  
Implement a functional intake pipeline capable of capturing and submitting
barcodes in batch.

### Scope
- Mobile-friendly scan interface
- Camera-based barcode scanning
- Manual barcode entry fallback
- Batch intake sessions
- Intake metadata and tagging
- Client-side validation
- Submission to the cloud intake API

### Deliverables
- Working scan UI
- Batch review and submission flow
- Integration with `cdx-intake-api`
- Clear operator feedback (accepted / rejected)

---

## Phase 3 – Operational Hardening

**Objective:**  
Improve reliability, resiliency, and usability under real-world conditions.

### Scope
- Offline-aware batching
- Local persistence of pending batches
- Retry and resubmission flows
- Enhanced validation and error handling
- Improved feedback and status visibility
- UX refinements based on usage

### Deliverables
- Offline-capable intake flow
- Robust retry and recovery handling
- Improved operator experience

---

## Future Considerations

These items are intentionally out of scope for the initial phases but may be
explored later:

- Advanced intake metadata schemas
- Role-based access controls
- Audit logging and traceability
- Metrics and operational dashboards
- Device and session management

---

## Guiding Principles

- Keep intake workflows simple and explicit
- Favor server-rendered UI over heavy client frameworks
- Optimize for speed and accuracy
- Model real enterprise intake systems, not consumer apps
- Avoid premature optimization or abstraction

---

## Notes

This roadmap is expected to evolve as implementation progresses. Phases are
intentionally incremental to ensure each step delivers a stable and meaningful
capability before moving forward.
