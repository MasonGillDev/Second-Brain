---
title: Contact sales (customer flow)
route: /contact-sales
audience: revenue-ops, support, deal-ops
slug: user-contact-sales
surface: user
---

# Contact sales — customer flow

End-to-end walkthrough of what an anonymous web visitor sees on the public `slyd.com/contact-sales` form. The page is public — no sign-in required — and every submission lands on the admin side as both a Form Submission (in **[Forms](/admin/forms)**) and a routing **Lead** in **[Leads Inbox](/v3/crm/leads)** with channel = **Form**.

## Where the visitor starts

The visitor lands on `slyd.com/contact-sales`. They get there from:

- The top-nav **Contact Sales** link on any marketing page
- A `?source=…` deep link from a V3 marketing page (the source tag rides along on the submission so ops knows which page sent them)
- A direct URL

The page has two columns:

- **Left** — sales contact info (phone, email) + the *"Let's Talk AI Infrastructure"* hero copy
- **Right** — the **Get in Touch** form card

## Contact options shown above the form

Before the form, the page shows:

- **Call Us** — `1-312-416-8438`
- **Email** — `sales@slyd.com`
- A promise: **"Response within 24 hours."**

A visitor who prefers not to fill the form can use those two channels directly. Admin doesn't see those touchpoints unless ops manually creates a **Lead** in **[Leads Inbox](/v3/crm/leads)** via **+ New Lead** with channel = `Phone` or `Email`.

## The form

The card is titled **Get in Touch**. Fields, all in the order they appear:

- **First Name *** — required
- **Last Name *** — required
- **Work Email *** — required, email-format validated
- **Company *** — required
- **Phone** — optional
- **What are you interested in? *** — required dropdown. Placeholder *"Select an option."* Options:
  - **GPU Hardware Purchase** (`gpu-hardware`)
  - **Compute Rental** (`compute-rental`)
  - **SLYD Platform** (`platform`)
  - **AI Development Services** (`ai-development`)
  - **Equipment Financing** (`financing`)
  - **Partnership Inquiry** (`partnership`)
  - **Other** (`other`)
- **How can we help? *** — required textarea. Placeholder *"Tell us about your project or requirements…"*

Required fields show inline red error text below the field if left blank when the visitor hits submit. Email field also validates format.

## Submitting

1. The visitor fills the required fields and clicks **Send Message** (paper-plane icon).
2. The button shows a spinner while submitting.
3. On success, a green banner reads *"Thank you! A SLYD specialist will contact you within 24 hours."* (or whatever message the backend returns), the form clears, and the visitor stays on the page.
4. On failure, a red banner reads *"There was an error sending your message. Please try again or email us directly at sales@slyd.com."*

There is no email confirmation step, no claim flow, no sign-in. A successful submission is fire-and-forget from the visitor's side — the next touch is from a SLYD specialist within 24 hours.

## The `?source=…` query param

Marketing pages link to this form with a `?source=<tag>` query param so ops can route inbound by origin. Examples from internal V3 pages: `sell`, `energy`, `financing`, `trust-diligence`, `cloud-license`, `cloud-connect`.

The page captures the param, sanitizes it (clamped to 64 chars, only `[A-Za-z0-9_-]` allowed), and forwards it to the submission as a `source` field. The admin email subject also includes the tag — `Sales Inquiry [<sourceTag>]: <interest>`.

When ops opens the resulting record:

- In **[Forms](/admin/forms)** — the full payload including `source`
- In **[Leads Inbox](/v3/crm/leads)** — the corresponding Lead row will carry the same `source` value in its **Source** column

## What happens next (visible to the visitor)

Below the form, the page shows a four-step *"What Happens Next?"* strip:

1. **We Review** — the team reviews the inquiry and picks the best expert.
2. **We Connect** — within 24 hours a SLYD specialist reaches out.
3. **We Consult** — the specialist discusses the project and answers technical questions.
4. **We Deliver** — if there's a fit, they provide a detailed proposal.

This is marketing copy, not a state machine. The visitor doesn't get any tracking page — the next touch comes through whichever channel the specialist chooses (email or phone).

## What the visitor *doesn't* see

- No tracking page or "where is my inquiry?" status
- No claim link, no sign-in step (unlike [Post a need](/need) or [Sell hardware](/hardware-sales))
- No email-confirmation step
- No automatic acknowledgement email visible from the form (one may be sent server-side, but the page itself shows only the in-page success banner)

## Things to know

- **Public, anonymous.** No login required. Anyone can submit.
- **Two records per submission on the admin side.** Every submission creates a **Form Submission** (in **[Forms](/admin/forms)**) with the full payload, *and* a routing **Lead** in **[Leads Inbox](/v3/crm/leads)** with channel = `Form`. If ops asks "which record do I work?" — the Lead is the routing record; the Form is the source-of-truth payload.
- **Phone and email contacts skip the form.** A visitor who calls `1-312-416-8438` or emails `sales@slyd.com` does not generate a Lead on its own — ops must create one manually in **[Leads Inbox](/v3/crm/leads)** via **+ New Lead** with channel = `Phone` or `Email`.
- **Source-tag routing.** The `?source=…` query param is preserved on the submission and is the cleanest way to route inbound by which marketing page sent the visitor. The tag also lands in the admin email subject.
- **24-hour promise.** The page promises a response within 24 hours, in three separate places (hero subhead, contact info, the four-step strip). Treat 24 hours as the SLA the visitor expects.
- **No state machine on the visitor side.** Unlike Need (which gives the visitor a banded match preview) or Sell (which gives them a quote band), Contact Sales is a flat form with no in-page preview, valuation, or tracking. It's the catch-all channel.
- **Interest dropdown is fixed.** The seven options are hard-coded — there's no free-text alternative. A visitor with a unique need must pick **Other** and explain in the **How can we help?** textarea.
