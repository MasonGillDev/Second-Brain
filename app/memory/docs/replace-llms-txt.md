# Replace wwwroot/llms.txt with New Version

**Project:** SLYD Website
**Date:** 2026-08-17
**Author:** 5b5d96b1-e0cc-451d-9017-b8a5cf0808d2
**Directory:** /Users/masongill/Slyd-Platform/website

## What Was Done
Replaced `wwwroot/llms.txt` with the new version Mason provided at `/Users/masongill/Slyd/llms.txt` (the source file still lives there). The new file is a leaner discovery map (75 lines vs 160): positions SLYD as an "AI infrastructure intelligence and transaction platform", adds explicit source/answer guidance for LLMs (treat pricing as indicative, don't imply approvals/availability, don't restate demo data as live metrics), and organizes links into Start Here / Transaction Paths / Hardware / Financing / Marketplace / Tools / Docs sections.

Before replacing, verified all 36 linked paths against the site's `@page` routes — every one resolves, and none reference the pages removed earlier today (/case-studies, /platform/ecosystem, /platform/architecture). The old version contained outdated claims (e.g. "/partners" which now 301s to /broker, "120+ users with $1.2M+ pipeline").

## To Do Next
- Commit and push the full session batch to `development` when Mason approves.
