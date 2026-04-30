# Purser User Manual

Purser is the DockLabs financial-close, submission-review, and
compliance-tracking product. State agencies and the programs they run
use Purser to file periodic financial reports, route them through
review and approval, attach supporting documentation, package the
results for sign-off in Manifest, and track ongoing compliance
obligations against grant recipients.

This manual covers the user-facing surface end to end. For operations,
see [CLAUDE.md](../CLAUDE.md).

---

## Contents

1. [Overview](#overview)
2. [Roles](#roles)
3. [Getting Started](#getting-started)
4. [Close Dashboard](#close-dashboard)
5. [Programs](#programs)
6. [Submissions](#submissions)
7. [Review Queue](#review-queue)
8. [Close Packages](#close-packages)
9. [Compliance](#compliance)
10. [External Submitter Portal](#external-submitter-portal)
11. [Helm Inbox Integration](#helm-inbox-integration)
12. [Notifications](#notifications)
13. [Manifest Signing Handoff](#manifest-signing-handoff)
14. [Status Reference](#status-reference)
15. [Keyboard Shortcuts](#keyboard-shortcuts)
16. [Support](#support)

---

## Overview

Purser has three coupled surfaces:

- **The Close Dashboard** (`/dashboard/`) — the canonical post-login
  page. A program-by-period grid for the active fiscal year, with a
  KPI strip showing how many programs have submitted, approved, or are
  still in draft for the current open period.
- **The Review Queue** (`/purser/review/`) — every submission in
  `submitted` or `under_review` status, ready for a reviewer to claim
  and act on.
- **Compliance** (`/purser/compliance/`) — obligations and items
  generated from `keel.compliance` templates, surfaced for compliance
  officers internally and grant recipients externally.

Around those, Purser provides:

- A program-admin surface for creating programs, assigning submitters
  and reviewers, and configuring the chart-of-accounts schema each
  program reports against.
- A close-package builder that aggregates approved submissions into a
  single signable artifact.
- A Manifest signing handoff for that artifact, with a local
  upload-signed-PDF fallback when Manifest isn't deployed.
- An external submitter portal for grant recipients filing compliance
  documents from outside the agency.

---

## Roles

Purser-specific roles are issued via Keel SSO and surfaced in your
sidebar profile.

| Role | Capability |
|---|---|
| **Admin** (`purser_admin`) | Full access. Manage programs, run any transition, close periods, send to Manifest, waive compliance items. |
| **Program Officer** (`purser_program_officer`) | Operate programs day-to-day inside the agency. Manage program rosters and review their assigned programs' submissions. |
| **Submitter** (`purser_submitter`) | File monthly submissions for programs you're rostered on. Edit line values, upload attachments, submit for review. |
| **Reviewer** (`purser_reviewer`) | Review submissions for programs you're rostered on. Begin review, approve, or request revisions. |
| **Compliance Officer** (`purser_compliance_officer`) | Triage compliance items submitted by external recipients. Accept, reject, escalate. |
| **Read-Only** (`purser_readonly`) | View dashboards and signed close packages. No edit. |
| **External Submitter** (`external_submitter`) | Grant recipients filing compliance documents from outside the agency. Restricted to their own agency's items. |

Suite-level `system_admin` inherits Admin behavior on Purser.

Program rostering is enforced separately. Even with the right role, a
user can only edit a submission for a program they are listed on as a
**submitter** or **reviewer** (M2M on `Program`).

---

## Getting Started

### Signing in

1. From any DockLabs product, click **Purser** in the fleet switcher,
   or visit `https://purser.docklabs.ai/`.
2. Click **Sign in with DockLabs** (the suite OIDC button).
3. You'll land on `/dashboard/` (the Close Dashboard).

If you're already signed in to another DockLabs product, the redirect
is seamless — no second login form.

### What you'll see first

- **Close Dashboard** — the program × period grid for the active
  fiscal year, plus current-period KPIs.
- **Review Queue** (sidebar) — submissions awaiting review.
- **Compliance** (sidebar) — overdue and upcoming compliance items.
- **Programs** (sidebar) — admin surface for program configuration.

External submitters land on a different surface — the
[External Submitter Portal](#external-submitter-portal) — scoped to
their own agency's compliance items.

---

## Close Dashboard

`/dashboard/` — the executive view of the current fiscal year close.

The dashboard renders:

- **KPI strip** — for the current open period: total programs,
  submitted count, approved count, and draft count. Each KPI card
  links through to the natural follow-up surface (the Review Queue,
  the program list, etc.).
- **Program × period grid** — rows are active programs grouped by
  `program_type` (Grant, Loan, Tax Credit, Bond, Federal Pass-Through,
  Other), columns are the most recent four fiscal periods of the
  active fiscal year. Each cell shows the submission's status badge
  and links into the [Submission form](#submissions) for that program
  and period.

The dashboard is read-only at the cell level — to act on a
submission, click into it.

---

## Programs

`/purser/admin/programs/` — the program-admin surface.

Each program carries:

| Field | Meaning |
|---|---|
| **Name** | "Manufacturing Assistance Act" |
| **Code** | Short unique code (e.g. `MAA`). Used in URLs. |
| **Program type** | Grant, Loan, Tax Credit, Bond, Federal Pass-Through, Other. |
| **Report schema** | `keel.reporting.ReportSchema` — the chart of accounts the program submits against each period. |
| **Submitters** | M2M set of users who can file the program's monthly submission. |
| **Reviewers** | M2M set of users who can review and approve. Also drives the Helm "Awaiting Me" inbox for those reviewers. |
| **Is active** | Toggle off to retire the program without deleting it. Inactive programs disappear from the Close Dashboard grid. |
| **Pulls from Harbor** | When set, submissions can be auto-populated from a Harbor API endpoint instead of typed by hand. |
| **Harbor API endpoint** | URL the auto-pull hits. Optional. |

### Creating or editing a program

1. **Programs → New program** (or click an existing program to edit).
2. Fill in name, code, type, and report schema.
3. Pick the submitters and reviewers from the user list. Both are M2M
   — a user can be on as many programs as you need.
4. Optionally enable Harbor auto-pull.
5. Save.

Roles are stitched together with rostering. A user with
`purser_submitter` can file submissions only for the programs they're
rostered on. Same for reviewers.

---

## Submissions

A **submission** is one program team's monthly financial report for a
single fiscal period.

`/purser/submit/<program_code>/<period_id>/` — the submission form.

### Anatomy

| Field | Meaning |
|---|---|
| **Program** | The program this submission belongs to. |
| **Fiscal period** | The reporting month. One submission per program per period (`unique_together`). |
| **Status** | `draft` → `submitted` → `under_review` → `approved` → `closed` (with `revision_requested` as a side branch). |
| **Source** | Manual entry, auto-pull from Harbor, or CSV import. |
| **Submitted by / at** | Stamped on the `submit` transition. |
| **Reviewed by / at** | Stamped on the `approve` or `request revision` transition. |
| **Reviewer notes** | The comment captured on the latest review action. |

### Filling in the form

The form renders the program's `ReportSchema` line items grouped and
ordered by the schema's sort order. For each line, you can enter a
**numeric value**, a **text value** (for narrative line items), or a
**per-line note** explaining variance.

The form persists changes inline via htmx — typing in a cell saves on
blur, with no full-page submit needed (`save-line/<value_id>/`). Only
**draft** and **revision_requested** submissions are editable; once
the submission moves to `submitted` or beyond, the cells lock.

The form also surfaces, for context:

- **Prior period values** — last month's value next to this month's
  cell, where available.
- **Budget baseline** — the monthly slice of the program's annual
  budget for the same line item, when a `BudgetBaseline` exists for
  the fiscal year.

### Attachments

Each submission can carry **supporting documents** (a
`SubmissionAttachment` per file) — invoices, journal exports, signed
narratives, anything a reviewer might ask for. Files run through
keel's `FileSecurityValidator` on upload.

### Workflow transitions

| From | To | Action | Required role | Notes |
|---|---|---|---|---|
| `draft` | `submitted` | Submit | submitter / admin | Stamps `submitted_by` + `submitted_at`. |
| `submitted` | `under_review` | Begin Review | reviewer / admin | Claims the submission. |
| `under_review` | `revision_requested` | Request Revision | reviewer / admin | **Comment required.** Reviewer notes captured. |
| `under_review` | `approved` | Approve | reviewer / admin | Stamps `reviewed_by` + `reviewed_at`. |
| `revision_requested` | `draft` | Revise | submitter / admin | Sends the form back to the submitter for edits. |
| `approved` | `closed` | Close | admin | Folds the submission into the period's close package. |

Every transition is recorded in `SubmissionStatusHistory` (immutable
audit trail).

---

## Review Queue

`/purser/review/` — every submission currently in `submitted` or
`under_review`, sorted oldest-first.

Click any row to open the **review detail** view at
`/purser/review/<id>/`. The detail view shows the same line-item grid
the submitter saw, plus the available transitions for the current
status. Reviewers can:

- **Begin Review** to claim the submission (`submitted` →
  `under_review`).
- **Approve** (`under_review` → `approved`).
- **Request Revision** with a required comment
  (`under_review` → `revision_requested`).

A submission with `reviewed_by` already filled in is "claimed" — only
the original reviewer plus admins continue to see it in their personal
[Helm Inbox](#helm-inbox-integration). Unclaimed submissions surface
to every program reviewer.

---

## Close Packages

`/purser/close/<period_id>/` — the per-period consolidated package.

A `ClosePackage` is auto-created when you visit the URL for a period
that doesn't have one yet. It carries:

| Field | Meaning |
|---|---|
| **Status** | `draft` → `complete` → `signing` → `signed` → `published`. |
| **Aggregated data** | JSON snapshot of the period's submissions, rolled up. |
| **Variance vs prior** | JSON snapshot of period-over-period variance. |
| **Variance vs budget** | JSON snapshot vs `BudgetBaseline`. |
| **Compliance summary** | JSON snapshot of compliance posture for the period. |
| **Executive summary** | Generated narrative shipped with the package. |
| **PDF export** | The pre-signing PDF. Distinct from the signed PDF returned by Manifest. |

### Signing the package

Two paths:

1. **Send to Manifest** —
   `/purser/close/<period_id>/sign/send/`. Available when
   `keel.signatures` is configured (`MANIFEST_URL` +
   `MANIFEST_API_TOKEN`). Creates a `SigningPacket` in Manifest, hands
   off ordered signers, and waits for the completion webhook. When the
   packet is approved, Manifest sends back the signed PDF and Purser
   files it on the close package as a `ClosePackageAttachment`
   (`source=MANIFEST_SIGNED`). The package status advances
   automatically.
2. **Local sign / upload signed PDF** —
   `/purser/close/<period_id>/sign/local/`. The fallback path when
   Manifest isn't available, or when the package was signed on paper.
   Upload the signed PDF directly; the package status advances the
   same way.

The Send-to-Manifest button is hidden when the integration isn't
configured — there are no silent no-ops.

### `ClosePackage` vs `ClosePackageAttachment`

- `ClosePackage.pdf_export` — the **pre-signing** PDF generated during
  close.
- `ClosePackageAttachment` (with `source=manifest_signed`) — the
  **signed** PDF returned from Manifest. Different file, different
  field, different lifecycle. Both are FOIA-discoverable.

---

## Compliance

`/purser/compliance/` — the internal compliance dashboard.

Compliance items are generated from `keel.compliance` templates and
obligations. Each item has a recipient (typically a state Agency or a
grant recipient), a due date, and a status that flows through the
compliance workflow.

### What you'll see

| Section | Contents |
|---|---|
| **Overdue** | Items whose status is `overdue`, ordered by due date. |
| **Upcoming** | Up to 20 items in `upcoming` or `pending`, ordered by due date. |
| **KPIs** | Active obligations, overdue count, upcoming count, items in `submitted` or `under_review`. |

### Compliance workflow

| From | To | Action | Notes |
|---|---|---|---|
| `upcoming` | `pending` | Due Soon | System-driven as the due date approaches. |
| `pending` | `submitted` | Submit | External submitter or staff. |
| `overdue` | `submitted` | Submit (Late) | Same target, just past due. |
| `submitted` | `under_review` | Review | Compliance officer claims. |
| `under_review` | `accepted` | Accept | Closes the loop. |
| `under_review` | `rejected` | Reject | **Comment required.** Sends back to the submitter. |
| `rejected` | `pending` | Resubmit | External submitter retries. |
| `pending` | `overdue` | Mark Overdue | System-driven once the due date passes. |
| `pending` / `overdue` | `waived` | Waive | **Admin only. Comment required.** |

### Item detail

`/purser/compliance/<item_id>/` shows the full record: template,
obligation, recipient, due date, status, and action history.

---

## External Submitter Portal

`/purser/portal/` — the surface for external grant recipients.

Recipients sign in with their DockLabs identity and see only their own
agency's compliance items. The portal scopes results by
`recipient_content_type` + `recipient_object_id` against the user's
linked Agency (a security boundary — without this filter, every
external submitter would see every agency's obligations).

The portal lists items in `upcoming`, `pending`, `overdue`,
`submitted`, `under_review`, `accepted`, or `rejected`, ordered by due
date. Recipients submit by uploading the requested document and
moving the item from `pending` → `submitted` (or `overdue` →
`submitted` for late filings).

---

## Helm Inbox Integration

Purser exposes `/api/v1/helm-feed/inbox/` so Helm's "Awaiting Me"
column can list the submissions you specifically need to review.

The predicate, per user:

- Submission status is `submitted` or `under_review`, **and**
- The user is in `program.reviewers` (M2M), **and**
- Either `reviewed_by IS NULL` (unclaimed) **or** `reviewed_by =
  user` (claimed by you).

Items carry the deep link
`/purser/review/<submission_id>/`, the `submitted_at` timestamp as
`waiting_since`, and a `type` of `review` (unclaimed) or `approval`
(claimed by you).

Aggregate Purser metrics (period status, program counts) flow through
the companion `/api/v1/helm-feed/` endpoint into Helm's "Across the
suite" tab.

---

## Notifications

Purser registers the following notification types with
`keel.notifications`:

### Financial Close

| Event | When it fires | Default audience |
|---|---|---|
| `purser_submission_due` | A program's monthly submission is due soon. | Submitters. |
| `purser_submission_overdue` | A submission is past its deadline. | Submitters + reviewers. Cannot be muted. |
| `purser_submission_ready_for_review` | A new submission is ready for review. | Reviewers. |
| `purser_revision_requested` | A submission has been sent back for revision. | The submitter. |
| `purser_close_package_ready` | All programs submitted for the period — the close package is ready. | Admins + reviewers. |
| `purser_variance_alert` | A line item exceeds the budget variance threshold. | Reviewers + admins. |
| `purser_close_package_signed` | The close package has been signed in Manifest. | Read-only audience. |

### Compliance

| Event | When it fires | Default audience |
|---|---|---|
| `purser_compliance_reminder` | Upcoming compliance deadline. | External submitters. |
| `purser_compliance_overdue` | A compliance item is past due. | External submitters + compliance officers. Cannot be muted. |
| `purser_compliance_escalation` | An item is past its grace period. | Admins. Cannot be muted. |
| `purser_compliance_submitted` | A recipient submitted a compliance document. | Compliance officers. |
| `purser_compliance_accepted` | A submission was accepted. | The external submitter. |
| `purser_compliance_rejected` | A submission was rejected and needs resubmission. | The external submitter. |

Channels (in-app + email) are user-configurable at
`/notifications/preferences/`. Notifications marked "cannot be muted"
override individual mute preferences but still respect channel-level
opt-outs.

---

## Manifest Signing Handoff

Purser uses `keel.signatures` for the close-package signing roundtrip.
The handoff follows the suite-wide DockLabs Project Lifecycle Standard:

1. The package reaches `complete` status.
2. **Send to Manifest** packages it as a `SigningPacket` with ordered
   signers; the source pointer is recorded in a `ManifestHandoff` row.
3. Manifest collects the signatures.
4. On approval, Manifest fires the completion webhook back to Purser's
   `keel.signatures` endpoint.
5. Purser files the signed PDF as a `ClosePackageAttachment`
   (`source=manifest_signed`, with the Manifest packet UUID), advances
   the close package to `signed`, and notifies subscribers via
   `purser_close_package_signed`.

The local-sign fallback (manual upload of a signed PDF) writes to the
same attachment table with `source=local_signed`, so the FOIA-export
trail is identical regardless of which path was taken.

---

## Status Reference

### Submission status

| Status | Meaning |
|---|---|
| **Draft** | Being filled in by the submitter. Editable. |
| **Submitted** | Filed for review. No further submitter edits. |
| **Under Review** | A reviewer has claimed it (`reviewed_by` set). |
| **Revision Requested** | Reviewer asked for changes. Returns to draft. |
| **Approved** | Approved. Eligible to roll into the close package. |
| **Closed** | Folded into the closed period. Terminal. |

### Close-package status

| Status | Meaning |
|---|---|
| **Draft** | Awaiting submissions. |
| **Complete** | All program submissions approved for the period. |
| **Signing** | In Manifest. |
| **Signed** | Approved. Signed PDF on file. |
| **Published** | Distributed to downstream consumers (Helm). |

### Compliance status

| Status | Meaning |
|---|---|
| **Upcoming** | Due in the future, no action required yet. |
| **Pending** | Due soon — submit. |
| **Overdue** | Past the due date, not submitted. |
| **Submitted** | Submitted by the recipient, awaiting review. |
| **Under Review** | A compliance officer has claimed it. |
| **Accepted** | Accepted — loop closed. |
| **Rejected** | Sent back. Recipient must resubmit. |
| **Waived** | Admin waived the obligation. Terminal. |

### Program type

Grant, Loan, Tax Credit, Bond Financing, Federal Pass-Through, Other.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| **⌘K** / **Ctrl+K** | Open the suite-wide search modal. |

---

## Support

- **Email** — info@docklabs.ai (1–2 business day response).
- **Feedback widget** — bottom-right corner of every page; routes to
  the shared support queue.
- **Per-product help** — for questions specific to Helm, Harbor,
  Admiralty, etc., open the help link inside that product.

---

*Last updated: 2026-04-30.*
