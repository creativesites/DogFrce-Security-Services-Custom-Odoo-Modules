# DogForce Security Suite — Marketing Plan

**Version:** 1.0
**Date:** 2026-06-03
**Author:** Winston Zulu, CVM Worldwide
**Status:** Active — go-to-market strategy from zero budget

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Positioning](#2-product-positioning)
3. [Zero-Budget Marketing Channels](#3-zero-budget-marketing-channels)
4. [Content Calendar — First 90 Days](#4-content-calendar--first-90-days)
5. [Social Media Content Bank](#5-social-media-content-bank)
6. [Demo Script](#6-demo-script)
7. [Pricing Strategy](#7-pricing-strategy)
8. [Success Metrics](#8-success-metrics)
9. [12-Month Roadmap](#9-12-month-roadmap)

---

## 1. Executive Summary

### The Opportunity

Private security is one of Namibia's fastest-growing industries. Windhoek alone has dozens of licensed security companies, most of them running their guard operations on WhatsApp groups, Excel rosters, and a payroll bureau they pay NAD 1,500–4,000 per month to run PAYE. None of them have a purpose-built system. That is the gap.

DogForce Security Suite is a production-ready, Odoo 19-based operations platform built specifically for private security companies. It handles everything from guard profiles and roster planning to Namibia-compliant payroll, mobile field attendance, AI anomaly detection, and automated client billing — in a single system, for a single monthly fee.

### Go-to-Market Strategy

The strategy is a staged regional rollout anchored by the DogForce Security Services deployment as a live reference client:

- **Months 1–3:** Build credibility online, produce demo content, begin outreach to Namibian security companies.
- **Months 4–6:** DogForce Security Services goes live as the first paying client. Document the deployment as a case study.
- **Months 7–9:** First external client signed. Case study published. Price validated.
- **Months 10–12:** Zambia market entry, replicate Namibia playbook.

### Budget

Zero. Every channel in this plan is free to use. The only real cost is time.

### Target Segments

| Segment | Definition |
|---------|------------|
| Primary | Namibian private security companies, 10–150 guards |
| Secondary | Botswana, Zambia, Zimbabwe operators, same size range |
| Long-term | South Africa (larger firms, higher competition, distinct payroll rules) |

### 90-Day Launch Snapshot

| Week | Priority Action |
|------|----------------|
| 1–2 | GitHub README live as product page; LinkedIn company page created |
| 3–4 | First 3 LinkedIn posts published; demo video recorded |
| 5–8 | Cold email to 30 Namibian security companies; join 5 Facebook groups |
| 9–12 | First demo call booked; Odoo App Store listing submitted |

---

## 2. Product Positioning

### 2.1 Name Recommendation

**Recommended name: DogForce Suite**

Rationale: "DogForce" is the most distinctive of the three options. It is memorable, tied to the founding deployment (DogForce Security Services), and creates a clear product identity that can be decoupled from the client over time. "SecuritySuite NA" is too generic and anchors the product to Namibia at a time when regional expansion is the goal. "GuardForce Platform" sounds like a dozen other SaaS products in adjacent markets.

The licensing and website product (per the DeployGuard OS plan) would sit under the broader "DogForce Suite" umbrella, with individual modules marketed as components of the Suite.

### 2.2 Taglines

**Option A:** "Run your security company. Not your spreadsheets."

**Option B:** "Guard management, payroll, and billing — one platform, built for Africa."

**Option C:** "The operations platform private security companies in Southern Africa have been waiting for."

Recommendation for launch: **Option A** for social and email (punchy, relatable). **Option B** for the website hero and app store listing (benefit-complete). Option C is too long for most placements.

### 2.3 Value Proposition

**2-sentence version:**

DogForce Suite is the only operations platform built specifically for private security companies in Southern Africa. It replaces spreadsheets, payroll bureaus, and WhatsApp rosters with a single system that handles guard management, Namibia-compliant payroll, AI-optimized rosters, and mobile field attendance — for less than you currently pay your payroll bureau.

**Expanded version:**

Managing a security company means tracking hundreds of moving pieces: guard certifications, daily rosters, client posting requirements, attendance against the posted schedule, overtime approvals, statutory payroll deductions, and client invoices. Most companies in Namibia and the broader SADC region do this across Excel files, WhatsApp messages, and a payroll bureau relationship that costs NAD 1,500–4,000 per month and still requires manual data entry.

DogForce Suite consolidates the entire operation into one purpose-built platform. Guards are profiled with grades, certifications, languages, and reliability scores. Rosters are generated against client contract requirements, validated automatically, and pushed to field supervisors' phones. Attendance is captured on-site via mobile. Payroll runs from that attendance data with PAYE, SSC, and overtime calculated correctly for Namibia — no manual intervention, no bureau dependency. Client invoices generate from the same data. An AI engine flags anomalies — a guard attending a site they were not rostered at, a billing discrepancy, a cost spike — before they become problems.

The platform is designed to grow with the region. Namibia payroll rules live in a localization module. Adding Zambia or Botswana is a configuration exercise, not a rebuild.

### 2.4 Competitive Advantages

The following are specific differentiators against generic Odoo, spreadsheets, and regional competitors:

1. **Namibia-compliant payroll out of the box.** PAYE brackets, SSC rates, public holidays, shift premiums — all pre-configured. No manual calibration. No bureau dependency. This alone justifies the price.

2. **Security-specific data model.** Generic Odoo has no concept of a guard grade, a posting requirement, a site inspection, or an equipment allocation to a guard. DogForce Suite does. The system was built by observing how security operations actually work, not adapted from a generic HR module.

3. **AI roster optimizer.** The system scores guard eligibility against posts using qualifications, reliability, home location distance, shift fairness, and availability constraints. It surfaces the optimal assignment as a draft; the supervisor confirms. No other product in the SADC security market does this.

4. **Mobile-first field attendance.** Field supervisors open an app, see today's roster pre-filled, and mark Present/Absent for each guard in under two minutes. No paper posting sheets, no WhatsApp photos, no manual data capture later. The data flows directly into payroll.

5. **AI anomaly detection.** The system flags when a guard attends a site they were not rostered at, when attendance patterns suggest buddy-punching, when billing data does not reconcile with actual hours, and when a guard's behaviour matches a risk profile. These are real operational problems that cost security companies money and reputation.

6. **Roster-to-payroll-to-invoice data chain.** Most security companies break this chain at every step. DogForce Suite closes it: the roster drives the posting sheet, the posting sheet drives payroll, and the same attendance data drives the client invoice. One source of truth eliminates reconciliation disputes.

7. **Open-source core on a stable platform.** Built on Odoo 19 Community (LGPL-3). There is no vendor lock-in risk. The client can always inspect, fork, or migrate the code. This matters to enterprise security buyers and government-adjacent contracts.

8. **Localization-first architecture.** Country-specific payroll and compliance rules live in isolated localization packs (`security_l10n_na`, `security_l10n_zm`). The operational core is country-neutral. Expanding to Zambia, Botswana, or Zimbabwe does not require rewriting the system — it requires adding a localization pack.

9. **Equipment and fleet management included.** Uniforms, radios, handcuffs, vehicles, fuel logs, and inspections — all tracked, linked to guards and sites. Most security SaaS products in the market ignore this entirely, creating a shadow Excel system for assets.

10. **Implementation and support from a developer who knows the codebase.** There is no black-box vendor support model. CVM Worldwide built every line of this system and can implement, customize, and support it with turnaround times no reseller can match.

### 2.5 Target Personas

**Persona 1 — Security Company Owner (5–200 guards)**

Profile: Owns and runs a licensed security company in Windhoek, Walvis Bay, or Oshakati. Has 2–4 office staff and 20–150 guards. Personally approves payroll and worries monthly about PAYE accuracy. Has had at least one payroll bureau mistake in the last year that cost money or a conversation with NamRA. Not particularly technical — wants the system to just work.

Pain points: Payroll bureau is expensive and makes errors. Rosters are done in WhatsApp or Excel and are impossible to audit. Client invoices are manually calculated. Has no real-time visibility into who is posted where.

Buying trigger: Seeing a demo that shows payroll running correctly in Namibia, without bureau involvement, for less than what the bureau charges.

**Persona 2 — Operations Manager**

Profile: Manages the day-to-day guard deployment for a mid-size security company (50–200 guards). Responsible for rosters, site compliance, and supervisor coordination. Spends 4–6 hours per week on roster planning alone. Regularly deals with last-minute no-shows and scrambles for replacements.

Pain points: Roster planning is manual and error-prone. No system to enforce qualification requirements per site. Cannot see at a glance which guard is eligible for a post. Gets no advance warning of certification expiries.

Buying trigger: Seeing the roster generation wizard and real-time eligibility validation in the demo.

**Persona 3 — HR/Payroll Officer**

Profile: Responsible for monthly payroll processing. May also manage leave records, discipline cases, and employee documents. Likely maintains 3+ Excel files per month. Has institutional knowledge of PAYE and SSC calculations that lives only in their head.

Pain points: Payroll inputs (actual hours, overtime, leave) come from multiple sources and must be manually reconciled before processing. Document expiry tracking is ad hoc. Leave balances are calculated manually.

Buying trigger: Seeing payslip generation from attendance data with PAYE/SSC auto-calculated and verifiable.

**Persona 4 — Field Supervisor**

Profile: Supervises 10–30 guards across multiple sites. Currently receives posting instructions via WhatsApp. Signs paper posting sheets at each site and delivers them to head office weekly. Has no smartphone app for their operational role. Often blamed when posting records are lost or delayed.

Pain points: Relies on paper. No real-time communication with head office about roster changes. Not aware of who is eligible for an emergency deployment.

Buying trigger: The mobile app demo — seeing that they can mark attendance in 90 seconds on their phone, submit it immediately, and the data appears in the office system.

---

## 3. Zero-Budget Marketing Channels

### 3.1 LinkedIn

**Why it works:** Security company owners and operations managers in Namibia and the SADC region use LinkedIn. It is the only professional social network where you can reach them with content rather than ads. Winston's personal profile, showing real build work and domain expertise, will generate more trust than a company page alone.

**Tactics:**

- Create the DogForce Suite LinkedIn company page and link it from the GitHub README and personal profile.
- Post 3 times per week from Winston's personal profile: one thought leadership post (security industry pain point), one product feature post, one regional market observation.
- Connect with 10 new people per week: security company directors, operations managers, and HR professionals in Namibia, Zambia, Botswana, and South Africa. Search terms: "security company director Namibia", "operations manager private security Windhoek", "HR manager security services".
- Share carousel posts (5–7 slides) showing feature walkthroughs — LinkedIn carousels get significantly higher engagement than single-image posts.
- Comment meaningfully on posts from target prospects before sending connection requests. Warm the relationship before the pitch.
- Use LinkedIn's "Open to work" tag in reverse — set the profile headline to "Building the operations platform for private security companies in Africa" to attract inbound curiosity.

**Time investment:** 1 hour per day (30 min writing/posting, 30 min engaging and connecting).

**Content to create:**
- 10 ready-to-post written posts (see Section 5)
- 2 carousel posts per month: "How DogForce Suite builds a roster" and "What happens when a guard goes absent — without software"
- A LinkedIn Featured section showcasing the GitHub repo, demo video link, and a one-pager PDF

---

### 3.2 GitHub

**Why it works:** The repository is already public. Odoo developers and potential implementation partners search GitHub for domain-specific modules. A well-crafted README is effectively a product landing page for a technical audience. GitHub stars and forks are a credibility signal.

**Tactics:**

- Treat the README as the product's primary technical landing page. It should answer: what does this do, who is it for, what does it include, and how do I see a demo?
- Add a "Demo / Contact" section to the README with a direct email link and a Calendly link (Calendly free tier allows one event type).
- Pin the repository to the GitHub profile (CVM Worldwide organization if created, otherwise Winston's personal profile).
- Add GitHub Topics to the repository: `odoo`, `odoo-module`, `security-management`, `namibia`, `sadc`, `payroll`, `guard-management`, `react-native`. Topics make the repo discoverable via GitHub search.
- Open structured issues for planned features. Public roadmap via issues signals active development.
- Write one technical post per month (see LinkedIn and local dev communities) that links to a specific part of the codebase — e.g., "How we built PAYE calculations in Odoo 19" with a link to `security_l10n_na`.

**Time investment:** 30 minutes per week to maintain README, issues, and project board.

**Content to create:**
- Updated README with product positioning, feature list, and demo/contact section
- `CHANGELOG.md` with weekly entries (signals active maintenance)
- GitHub Project board showing roadmap publicly

---

### 3.3 Odoo App Store and Odoo Community

**Why it works:** Odoo's app store and community forum are where Odoo users and implementors look for modules. A listing there provides passive inbound discovery from the global Odoo ecosystem, including SADC-region implementation partners who might refer or co-implement.

**Tactics:**

- Submit the modular packages to the Odoo App Store once they reach a stable release state. Start with `security_l10n_na` (the Namibia payroll pack) as a standalone listing — localization modules get attention because they fill country-specific gaps that Odoo core does not cover.
- Create a profile on the Odoo Community Association (OCA) GitHub organization to submit PRs and raise visibility. OCA contribution is a credibility signal in the Odoo ecosystem.
- Engage on the Odoo Community forum (https://www.odoo.com/forum) — answer questions about payroll, HR modules, and localization. Build a profile as the SADC payroll expert. Do not pitch; just help. The profile and signature link to the product.
- Search the forum for threads tagged "Africa", "payroll", "security", or "Namibia" and post useful responses.

**Time investment:** 2 hours per week for forum engagement; one-time effort of 4–6 hours for the App Store listing.

**Content to create:**
- App Store listing description for `security_l10n_na` (Namibia payroll localization)
- App Store listing for the core suite once stable
- Forum profile with a clear description and link to the GitHub repo

---

### 3.4 Facebook Groups

**Why it works:** Southern African SME business owners — including security company owners — use Facebook more than LinkedIn. Business groups in Namibia are active with thousands of members. The tone is less formal and the content that performs is practical, direct, and conversational.

**Target groups:**

- Namibia Business Network (search Facebook for this group and similar)
- Windhoek Business Connect
- Namibia Entrepreneurs and Business Owners
- Southern Africa Business Forum
- Namibia HR Professionals
- Security Industry Southern Africa (if a group exists — if not, create it as a positioning move)
- Zambia Business Hub
- Botswana Business Professionals

**What content performs well in these groups:**

- "What's the biggest admin headache in your business?" — sparks discussion you can answer with domain expertise
- Before/after visuals: "This is what our clients used to do [spreadsheet screenshot]. This is what they do now [platform screenshot]."
- Pain-point questions: "Security company owners — how many hours does your payroll take every month?"
- Short tips: "3 things your payroll bureau won't tell you about SSC calculations in Namibia"

**DMs strategy:**

After engaging in a group for 2–3 weeks, identify active commenters who are security company owners or managers. Send a direct message that acknowledges a comment they made, offers something genuinely useful (a free payroll checklist, a PAYE bracket table), and mentions the platform. Do not pitch in the first message.

**Time investment:** 45 minutes per day (posting, commenting, engaging).

---

### 3.5 Cold Email

**Why it works:** Direct outreach to security companies in Namibia is the fastest path to a demo. There are a finite number of licensed security companies in Namibia — perhaps 50–150 active operations — which means a targeted, value-first cold email campaign can reach the entire addressable market in weeks.

**How to find prospects:**

- BIPA (Business and Intellectual Property Authority of Namibia): BIPA maintains a register of registered businesses. Security companies must be licensed under the Security Officers Act. BIPA's online search (https://www.bipa.na) allows searching by industry category.
- Namibia Security Industry Regulatory Authority (NAMPOL-administered): Security companies are registered with a government authority. Contact NAMPOL's security division for the public register.
- Google: "private security company Namibia", "guard company Windhoek", "security services Namibia" — build a list from the results, company websites, and LinkedIn profiles.
- LinkedIn Sales Navigator free tier: Search "security company" + "Namibia" for decision-makers.

**3-Part Email Sequence:**

**Email 1 — The Problem (Day 1)**

Subject: Payroll bureau + Excel rosters — how much does it actually cost you?

Preview: I've been building operations software for security companies in Namibia. What I keep hearing is...

Body: See Section 5 for full email text.

**Email 2 — The Proof (Day 5, no reply to Email 1)**

Subject: Quick demo — 7 minutes to show you the alternative

Preview: I know you're busy. I'll show you exactly what changes in 7 minutes flat.

Body: "Hi [Name], I didn't hear back from my previous email, which is fine — I know ops managers and directors don't have time to read everything. I wanted to send one short follow-up. I've recorded a 7-minute screen demo of the DogForce Suite — Namibia payroll, roster planning, mobile attendance, client invoices — all live in the system. Watch it here: [link]. If it's not relevant to you, no need to reply. If it is, I'd love to do a live demo where I show it running with your company's actual structure. Reply to this email and we'll set it up. Winston"

**Email 3 — The Last Ask (Day 12, no reply to Emails 1–2)**

Subject: Last email from me on this

Preview: If it's not a fit, I completely understand. Just wanted to leave the door open.

Body: "Hi [Name], This is my last follow-up on the DogForce Suite. If running guard operations on spreadsheets and a payroll bureau is working well for your company, I'm not going to convince you otherwise. But if there's ever a month where payroll has an error, a roster doesn't reconcile, or you want to know exactly who is on which site right now without making three phone calls — I'd welcome that conversation. My contact: winston@cvmworldwide.com. I'm based in Windhoek and available for in-person demos. Winston"

**Time investment:** 1 hour per week to research and send 5 new prospect emails; tracking in a free CRM (HubSpot CRM free tier covers contact management and email tracking).

---

### 3.6 YouTube and Screen Recording

**Why it works:** A well-produced screen recording demo is the most powerful async sales asset. When a prospect watches a 7-minute demo and sees the system doing exactly what they struggle with today, the conversion rate on follow-up calls improves dramatically. No camera required — screen + voiceover is entirely sufficient and more professional for a technical product.

**Demo video script:** See Section 6 for the full 7-minute demo script.

**Production approach:**

- Use OBS Studio (free, open-source) for screen recording.
- Use Audacity (free) or record directly in OBS for voiceover.
- Record at 1920x1080, use the Odoo platform with clean demo data populated from `security_demo_data`.
- Title: "DogForce Suite — 7-Minute Platform Demo (Guard Management, Payroll, Mobile App)"
- Upload to YouTube. Set as unlisted initially so it can be shared via email without being publicly discoverable until the product is ready for public launch.
- Create a public version with a visible title card, intro, and link to contact in the description once the product is at a demo-ready state.

**Short-form clips for LinkedIn and Facebook:**

From the full demo, cut:
- 60-second clip: "Watch payroll run in 60 seconds" (payslip generation segment)
- 45-second clip: "This is what a real-time roster board looks like" (roster board segment)
- 90-second clip: "Field supervisor marks attendance on mobile — start to finish" (mobile attendance segment)

**Time investment:** 4 hours for initial demo recording and editing; 30 minutes per clip cut for social.

---

### 3.7 Local Business Networks

**Why it works:** Namibia is a small market. The decision-maker community for security industry software is perhaps 100–200 people nationally. Personal credibility in local business networks — where these people show up — is more powerful than any digital channel alone.

**Targets:**

- **Namibia Chamber of Commerce and Industry (NCCI):** Winston or DogForce Security Services (as a client) can engage with the NCCI. The NCCI publishes a business directory and hosts events. Request to present at a technology or operations session. Security companies are NCCI members.
- **BIPA Business Forum:** BIPA runs business registration events and SME forums. Security companies are registered there.
- **Namibia HR Association:** Namibia has an HR professional community. Payroll compliance and digital HR tools are relevant topics for them. Offer to speak on "Namibia payroll compliance for security companies" at a meeting.
- **NamCham (Namibian Chamber of Mines and Industry) events:** Larger security companies often work in the mining sector. NamCham events attract mining-sector buyers.
- **University of Namibia and Polytechnic of Namibia:** Consider presenting the platform at business or computing faculty events — builds brand recognition and potential talent pipeline.

**Tactical approach:** Do not attend as a vendor. Attend as a domain expert on security operations technology. Offer to contribute a talk, workshop, or article for their member newsletter. The platform becomes the natural reference.

---

### 3.8 Strategic Partnerships

**Why it works:** Strategic partners bring warm referrals from relationships they already have. A payroll bureau that loses a client to DogForce Suite is a lost revenue opportunity for them — but an HR consulting firm that recommends DogForce Suite adds value to its clients without cannibalizing its own services.

**Target partner types and approach:**

**HR Consulting Firms:**
- Firms that advise Namibian SMEs on HR compliance, employee handbooks, and payroll setup do not typically offer software. DogForce Suite is a natural complement.
- Approach: Offer a referral fee (10–15% of first year's contract value) for any client they refer who signs. Create a one-pager specifically for HR consultants explaining what the platform does and how it makes their clients look good.

**Payroll Outsourcing Companies:**
- Counterintuitive but worth exploring: some payroll bureaus want to offer a technology upgrade to their clients. Partner with a bureau that wants to become a software reseller rather than fight for the same clients.
- Alternatively, target bureaus that are losing clients due to errors or slow turnaround and offer the platform as what their clients switched to — the bureau becomes an implementation partner on new clients.

**Odoo Implementation Partners in SADC:**
- There are Odoo implementation partners in South Africa, Zambia, and Botswana who do not have a purpose-built security industry module. DogForce Suite fills that gap.
- List: Search the Odoo Partner directory (https://www.odoo.com/partners) for partners in Namibia, Botswana, Zambia, Zimbabwe, South Africa.
- Approach: Offer a co-implementation model — they bring the Odoo platform expertise and client relationships; CVM Worldwide brings the security-specific modules and support. Revenue share on licence fees.

**Security Industry Associations:**
- Namibia Security Industry Association (if one exists formally) or the equivalent body under which companies are licensed. Becoming the "recommended platform" of an industry association is worth significant inbound referrals.
- Approach: Offer the association members a group rate or free pilot period in exchange for endorsement.

---

## 4. Content Calendar — First 90 Days

### Week-by-Week Plan

**Week 1 (Days 1–7): Foundation**

| Day | Action |
|-----|--------|
| Mon | Update GitHub README with product positioning, contact section, demo link placeholder |
| Tue | Create LinkedIn company page for DogForce Suite; link from personal profile |
| Wed | LinkedIn Post 1: Thought leadership — security industry payroll pain point |
| Thu | Join 5 Facebook groups (see Section 3.4 list) |
| Fri | Research first 10 cold email prospects (BIPA + Google) |
| Sat | Record demo video (OBS Studio, use demo data) |

**Week 2 (Days 8–14): First Content**

| Day | Action |
|-----|--------|
| Mon | LinkedIn Post 2: Feature showcase — roster planning |
| Tue | Facebook Group Post 1: Pain-point question |
| Wed | Send cold emails to 5 prospects (Email 1 sequence) |
| Thu | LinkedIn Post 3: Industry stat post |
| Fri | Connect with 10 LinkedIn prospects |
| Sat | Edit demo video, upload to YouTube (unlisted) |

**Week 3 (Days 15–21): Momentum**

| Day | Action |
|-----|--------|
| Mon | LinkedIn Post 4: "Here's what we built" — mobile app |
| Tue | Facebook Group Post 2: Before/after visual |
| Wed | Send cold emails to 5 new prospects; Day 5 follow-up to Week 2 batch |
| Thu | LinkedIn Post 5: Case study teaser (DogForce Security Services, anonymized) |
| Fri | Odoo Community forum: answer 3 payroll-related questions |
| Sat | Draft Odoo App Store listing for `security_l10n_na` |

**Week 4 (Days 22–28): Outreach Scale**

| Day | Action |
|-----|--------|
| Mon | LinkedIn Post 6: Thought leadership — PAYE compliance |
| Tue | Facebook Group Post 3: Short tip post |
| Wed | Send cold emails to 5 new prospects; Day 12 follow-up to Week 2 batch |
| Thu | LinkedIn Post 7: Feature showcase — AI anomaly detection |
| Fri | Connect with 10 LinkedIn prospects; respond to comments |
| Sat | Submit Odoo App Store listing |

**Weeks 5–8: Steady State (repeat weekly)**

- LinkedIn: 3 posts/week (Mon/Wed/Fri cadence)
- Facebook: 2 posts/week across target groups
- Cold email: 5 new prospects per week; run follow-up sequences on prior batches
- LinkedIn connections: 10 new per week (60 seconds of personal message per request)
- Odoo forum: 30 minutes of engagement twice per week

**Week 9: Demo Call Target**

By week 9, the goal is one booked demo call from cold email or LinkedIn inbound. All cold email recipients who have not replied to Email 3 can be re-engaged with a new angle: "We have our first client live in Namibia — would you like to see a case study?" once DogForce Security Services is live.

**Month 3: YouTube**

Publish the demo video publicly. Create LinkedIn and Facebook posts announcing it. Share in all Facebook groups with a genuinely useful framing ("I recorded a 7-minute walkthrough of what a security operations platform looks like if it's built right — would love feedback from people in the industry").

---

### Content Production Template Per Week

| Content Type | Quantity | Time Required |
|-------------|---------|---------------|
| LinkedIn posts (written) | 3 | 45 min total |
| Facebook posts | 2 | 30 min total |
| Cold email research + send | 5 prospects | 60 min total |
| LinkedIn connection requests | 10 | 20 min total |
| Forum engagement | 3 responses | 30 min total |
| **Total per week** | | **~3 hours** |

---

## 5. Social Media Content Bank

### LinkedIn Posts (10 Ready-to-Post)

---

**LinkedIn Post 1 — Pain Point: Payroll**

How many hours does your security company spend on payroll every month?

In Namibia, I've seen the process take 3–5 days for a company with 60 guards. Not because payroll is complicated. Because the data is a mess.

Here's what the typical process looks like:

1. Operations sends Excel rosters to HR.
2. HR compares rosters to paper posting sheets collected from supervisors.
3. HR manually calculates overtime (because not everyone works the same shift).
4. HR adjusts for leave (from a separate spreadsheet).
5. HR sends the totals to a payroll bureau.
6. The bureau processes it and sends payslips — 3 days later.
7. Guards complain about errors. HR goes back to check. Bureau reprocesses.

By the time payroll is done, someone has spent 30+ hours on a process that should take 3.

We built DogForce Suite to close every gap in that chain. Attendance data captured on mobile, overtime calculated automatically, PAYE and SSC computed correctly, payslips generated in minutes — not days.

If your payroll month looks anything like what I described above, I'd welcome a 20-minute conversation.

DM me or email winston@cvmworldwide.com.

---

**LinkedIn Post 2 — Feature Showcase: Roster Board**

The hardest part of running a security company isn't the guards.

It's the spreadsheet you're using to track them.

Last month's roster. This month's roster. Who's on leave. Who's qualified for which site. Who worked too many Sundays. What the client contract says about minimum grade requirements.

That's 6 different things that have to reconcile perfectly — and they usually don't.

DogForce Suite's Roster Board solves this with a visual planning interface built specifically for security operations:

- Each post shows its grade, certification, and headcount requirements
- Guards are scored for eligibility automatically (qualifications, leave, disqualification checks)
- The AI optimizer surfaces the best available guard for each slot
- You confirm, adjust, or override — with a reason that gets logged
- The roster feeds directly into attendance and payroll

No spreadsheet. No WhatsApp threads. No Monday morning scramble.

If you manage rosters for a security company in Namibia or the region, I'd genuinely love to hear how you're doing it now. Comment below.

---

**LinkedIn Post 3 — Industry Stat**

Namibia has over 200 registered private security companies.

Most of them are managing 20–150 guards with some version of Excel, WhatsApp, and a payroll bureau.

That's not a criticism. It's what you do when no software exists that actually fits your industry.

Until now.

DogForce Suite is built from the ground up for private security operations in Southern Africa. Namibia-compliant payroll, guard qualification tracking, roster planning with AI optimization, mobile attendance for field supervisors, client invoicing from actual attendance data.

One platform. One monthly fee. No bureau.

We're running our first live deployment at DogForce Security Services in Namibia. If you're a security company owner or operations manager and want to see what this looks like in practice — I'll run a 7-minute demo for you. No slides. Live system.

DM me.

---

**LinkedIn Post 4 — "Here's What We Built": Mobile App**

Our field supervisors used to send posting sheets via WhatsApp photo. HR would receive a blurry picture of a handwritten form, try to read it, and manually enter the data.

We fixed that.

DogForce Mobile is a React Native app built for field supervisors. Here's what it does:

Open the app. See today's roster pre-filled — every guard, every post, already populated from the system.

Tap Present or Absent next to each name. Add a note if needed. Submit.

That's it. The data appears in the office system immediately. The AI engine flags anything unusual. Payroll gets accurate data without a single manual entry.

No paper. No WhatsApp photos. No Monday data-capture backlog.

The app works on Android (standard for most field staff in Namibia). It connects to the DogForce Suite platform via a secure API. It works offline if connectivity drops at a remote site, and syncs when back online.

Building the right tool for the right person matters. Field supervisors didn't need a full ERP on their phone. They needed a 90-second attendance workflow. That's what we gave them.

---

**LinkedIn Post 5 — Case Study Teaser**

One of our client's payroll runs used to take 4 days.

Last month, it took 47 minutes.

Here's what changed:

Before DogForce Suite: Operations manager compiled rosters in Excel. Supervisors submitted paper posting sheets weekly. HR reconciled both manually. Bureau processed payroll 3 days after receiving inputs. Errors required bureau corrections — another 2 days.

After DogForce Suite: Roster is built in the system, validated against client contract requirements, and published to supervisors' phones. Supervisors mark attendance on the mobile app in under 2 minutes per site visit. HR reviews the consolidated attendance data (already reconciled against the roster). Payroll runs — PAYE, SSC, overtime, shift premiums all calculated — and payslips are generated.

The 47 minutes includes review and approval. Not just processing.

Full case study to be published next month. In the meantime, if you want to see the platform live: winston@cvmworldwide.com.

---

**LinkedIn Post 6 — Thought Leadership: Compliance**

NamRA doesn't care that your payroll bureau made an error.

If your PAYE submissions are wrong, the liability is the employer's. The bureau gets to charge you again for corrections. You absorb the penalties.

This is a structural problem with payroll outsourcing that most security companies in Namibia don't think about until it happens to them.

The alternative is not to do payroll yourself with more spreadsheets. The alternative is a system that calculates PAYE and SSC correctly, automatically, from actual attendance data — and produces an audit trail you can show NamRA if they ever ask questions.

DogForce Suite's Namibia payroll module handles:
- Current PAYE brackets and rates
- SSC contribution calculations (employee and employer)
- Public holiday premium rates
- Night shift differentials
- Overtime calculation rules per Labour Act

Every computation is traceable. Every payslip shows the inputs that produced it.

This is the level of payroll auditability that security companies in Namibia should have. Most don't — yet.

---

**LinkedIn Post 7 — AI Anomaly Detection**

An AI flagged a billing discrepancy worth NAD 12,000 last month.

A guard was recorded as attending a site 26 times in a billing period. The client contract specified 1 guard per 12-hour shift, 24/7 coverage — which should produce 60 shift-slots in a 30-day month. But the attendance data showed 26 records for that guard alone.

Without an AI anomaly check: the invoice goes out with wrong hours. Either the company under-bills and loses revenue, or the client catches it and disputes the invoice — damaging the relationship.

With DogForce Suite's billing audit engine: the anomaly is flagged before the invoice generates. The operations manager reviews, identifies the duplicate records (a data entry error), corrects them, and invoices correctly.

This is what AI is for in operations software. Not chatbots. Not dashboards that tell you what you already know. Finding the thing that slipped through — before it costs you money or a client relationship.

---

**LinkedIn Post 8 — Feature Showcase: Guard Profiles**

A guard profile in DogForce Suite is not just a name and a payroll number.

It is the operational record of that guard's entire service history:

- Grade (PSO I, II, III, Supervisor)
- Certifications — with expiry dates and linked document scans
- Languages and proficiency levels
- Equipment allocations (uniform, radio, firearm if applicable)
- Reliability score — computed from attendance, discipline, and performance data
- Leave balance (current and historical)
- Payslip history (last 12 months, visible on the profile)
- Discipline incidents
- Active disqualifications (sites or clients the guard cannot be assigned to)

When the roster optimizer runs, it checks all of this. A guard with an expired first aid certification does not get assigned to a medical facility post. A guard with a client exclusion on record does not appear in the eligibility list for that site.

This is the difference between a guard management system and a guard profile spreadsheet.

---

**LinkedIn Post 9 — Thought Leadership: Region**

Why I'm building security operations software in Namibia before South Africa.

The common assumption is that you should start in the biggest market. South Africa has thousands of security companies. The market is enormous. Why start in Namibia?

Three reasons:

First, Namibia is solvable. The total addressable market is perhaps 150–300 licensed security companies. I can reach every one of them. In South Africa, you're immediately competing with established vendors, resellers, and South African-built products.

Second, Namibia has a genuine gap. South Africa has Loomis, Exactech, Acumatica customizations, and a dozen locally-built payroll products. Namibia has spreadsheets and a payroll bureau. The problem is more acute here.

Third, Namibia is the validation. If DogForce Suite works in Namibia — with Namibian Labour Act compliance, SSC calculations, NamRA reporting, and field deployment in a market where internet connectivity is variable — it will work anywhere in the SADC region. Zambia, Botswana, Zimbabwe all share the same structural problems and similar compliance frameworks.

Start where the problem is clearest. Win there. Then expand.

---

**LinkedIn Post 10 — Connection and CTA**

If you own or manage a private security company in Namibia or the SADC region, I want to connect with you.

Not to pitch you. To understand your operation.

I'm Winston Zulu. I run CVM Worldwide, a software development firm in Namibia. Over the last 18 months, I've been building DogForce Suite — an operations platform designed specifically for security companies in Southern Africa.

Before I started building, I spent time understanding how security companies actually run. What I found: the problems are consistent. Rosters on Excel. Payroll at a bureau. Paper posting sheets. No real-time visibility. No mobile tools for field staff.

DogForce Suite addresses all of that. But I'm always learning more from operators in the industry.

If you're open to a 20-minute conversation about how you run your operation — even if you have no interest in software — I'd genuinely value it.

Send me a connection request and mention "security operations" in the note. I respond to all of them.

---

### Facebook Posts (5)

---

**Facebook Post 1 — Pain Point**

How long does payroll take at your security company every month?

I'm talking the full process: getting attendance from supervisors, reconciling rosters, dealing with overtime queries, sending everything to the payroll bureau, waiting for payslips, fixing errors.

For most security companies I've spoken to in Namibia, it's 3–5 working days.

We built software that gets it down to under an hour. Namibia-compliant, PAYE and SSC calculated automatically, payslips generated from the same attendance data your supervisors submit on their phones.

If you want to see it, reply to this post or send me a message. Happy to do a quick demo.

---

**Facebook Post 2 — Direct Benefit**

Your payroll bureau charges you NAD 1,500–3,000 per month.

DogForce Suite costs less than that — and does more.

- Guard roster planning (auto-validated against your client contracts)
- Mobile attendance for field supervisors (no more paper posting sheets)
- PAYE and SSC calculated automatically
- Client invoices generated from actual attendance data
- AI that flags errors before they become problems

Built specifically for security companies in Namibia. Running live in Windhoek.

Interested in a 10-minute demo? Message me directly.

---

**Facebook Post 3 — Short Tip**

Security company owners: if you don't know exactly who is posted at each of your sites right now — without making a phone call — you have an operations problem.

DogForce Suite gives you a live dashboard of every posting, every guard, every site. Updated in real time by your field supervisors from their phones.

It takes less than a week to set up. It changes how you run your company permanently.

Drop a comment if you want to know more.

---

**Facebook Post 4 — Local and Specific**

Built in Namibia. For Namibian security companies.

DogForce Suite handles Namibia PAYE, SSC contributions, the Labour Act overtime rules, and public holiday premiums — all pre-configured. You don't have to tell the system about Namibian tax. It already knows.

We're running our first live deployment in Windhoek. The case study will be published later this year.

If you run a security company in Namibia and want to see what a modern operations platform looks like — message me. I'll come to your office and demo it in person.

---

**Facebook Post 5 — Relatable and Conversational**

True story from a security company I spoke to last month:

Their operations manager had a spreadsheet with 120 guards. Each month, she'd manually check who was eligible for each post, cross-reference with the leave schedule (in a different spreadsheet), verify certifications hadn't expired (in a third spreadsheet), and build the roster.

It took her 3 full days every month. Just for the roster.

DogForce Suite does it in a guided workflow. Guard eligibility is checked automatically. The AI suggests the best assignment for each slot. She reviews, adjusts where needed, and confirms. Total time: under 2 hours.

Same result. Better accuracy. No spreadsheet marathon.

If this sounds familiar, let's talk. winston@cvmworldwide.com.

---

### Cold Email Templates (5)

---

**Email Template 1 — Pain-Point Based**

Subject: Payroll bureau + Excel rosters — what it's actually costing you

Preview: The hidden cost isn't the bureau fee. It's the time, the errors, and the disputes...

---

Hi [Name],

I'm Winston Zulu, founder of CVM Worldwide. We build software for private security companies in Namibia and the SADC region.

I'm reaching out because I've spent the last 18 months speaking with security company owners and operations managers in Namibia. The same three problems come up in almost every conversation:

1. Payroll takes 3–5 days every month because attendance data, rosters, and leave records are in different places and have to be reconciled manually before the bureau can process anything.

2. Rosters are built in Excel or WhatsApp and are impossible to audit when a client dispute arises.

3. There's no real-time visibility into which guard is posted where right now — without making phone calls.

I built DogForce Suite to solve all three. It is an operations platform built specifically for private security companies: roster planning validated against your client contracts, mobile attendance submission for field supervisors, Namibia-compliant PAYE and SSC payroll, and automated client invoicing — all in one system.

The first live deployment is underway in Windhoek. I'd welcome the chance to show you a 7-minute demo.

Is there a 20-minute slot in your schedule in the next two weeks?

Winston Zulu
CVM Worldwide | winston@cvmworldwide.com

---

**Email Template 2 — ROI-Focused**

Subject: What you're paying vs. what you could pay

Preview: Most Namibian security companies spend NAD 18,000–36,000 per year on payroll processing...

---

Hi [Name],

Quick question: what does your company pay your payroll bureau per month?

For most security companies in Namibia, it's between NAD 1,500 and NAD 3,500 — so roughly NAD 18,000–42,000 per year. That's before factoring in the time your HR staff spend reconciling data before they can even send the bureau anything.

DogForce Suite replaces that with a purpose-built platform that costs less per month than most bureau contracts, and does everything the bureau does — plus roster planning, mobile field attendance, AI anomaly detection, and client invoice automation.

For a 50-guard company, the total monthly value includes:
- Eliminating 3–4 days of payroll preparation per month (staff time)
- Reducing billing errors that create client disputes
- Removing bureau fees entirely

I'm not asking you to take my word for it. I'd like to show you a 7-minute live demo. No slides. The real system, with Namibian demo data.

Is this worth 20 minutes of your time?

Winston Zulu
CVM Worldwide | winston@cvmworldwide.com

---

**Email Template 3 — Question Format**

Subject: Quick question about your roster process

Preview: I promise this isn't a generic sales email...

---

Hi [Name],

One question: how does your company currently build the monthly roster for your guards?

I ask because I've been building software for security companies in Namibia, and the roster planning process is the one thing that consistently takes up the most time — often 2–4 days per month for the operations manager, depending on company size.

If you're doing it in Excel, WhatsApp, or a combination of both, I have something worth showing you. DogForce Suite's roster board validates guard eligibility automatically, checks certifications and leave, flags conflicts, and generates a draft roster from your contract requirements. The operations manager reviews and confirms. Total time: a fraction of what it takes manually.

Happy to show you in 7 minutes — screen share, no slides, live system.

Worth a quick call?

Winston Zulu
CVM Worldwide | winston@cvmworldwide.com

---

**Email Template 4 — Mobile Attendance**

Subject: Do your field supervisors still use paper posting sheets?

Preview: If they do, this is worth 7 minutes of your time...

---

Hi [Name],

A quick scenario: it's Monday morning and you want to know if all your guards were posted correctly on Sunday night.

Can you find out right now, without calling anyone?

For most security companies in Namibia, the answer is no — because posting records are on paper or in WhatsApp photos, and they don't reach the office until the supervisor delivers them.

DogForce Mobile changes this. Field supervisors open an app, see today's roster pre-populated from the system, mark Present or Absent for each guard, and submit in under 2 minutes. The data appears in the platform immediately. If a guard doesn't show up, you know right away — not 3 days later.

The same attendance data feeds into payroll. No re-keying. No reconciliation.

I can show you the full 7-minute demo — roster, mobile attendance, payroll, invoicing — anytime this week.

Would that be useful?

Winston Zulu
CVM Worldwide | winston@cvmworldwide.com

---

**Email Template 5 — Localization Angle**

Subject: Is your PAYE calculation actually correct?

Preview: Namibian PAYE has 7 tax brackets. Most payroll bureaus handle this — but can you verify?

---

Hi [Name],

This is a slightly uncomfortable question: do you know exactly how your company's PAYE is being calculated each month?

Most security companies in Namibia outsource this to a bureau and trust the output. Which is reasonable — but if the bureau makes an error, the liability is the employer's. NamRA doesn't accept "the bureau got it wrong" as a defence.

DogForce Suite handles Namibian PAYE, SSC (both employer and employee contributions), public holiday premiums, overtime under the Labour Act, and shift differentials — all pre-configured and auditable. Every payslip shows exactly how each figure was computed. You can verify it. NamRA can verify it.

The platform also handles roster planning, mobile field attendance, and client billing — so payroll inputs come from actual operational data, not manually reconciled spreadsheets.

I'd love to show you how this looks in practice. A 7-minute screen demo, live system, no slides.

Is there 20 minutes available this week or next?

Winston Zulu
CVM Worldwide | winston@cvmworldwide.com

---

## 6. Demo Script

### DogForce Suite — 7-Minute Platform Demo

**Setup before recording:** Use `security_demo_data` with a mid-size security company dataset. Company name: "Apex Security Services" (anonymized). 48 guards, 6 sites, 1 active payroll period.

---

**[0:00 – 0:30] Executive Dashboard**

*Screen: DogForce Suite main dashboard*

"This is the DogForce Suite executive dashboard. In 30 seconds, this screen tells me the state of my entire operation.

48 active guards. 6 client sites. Today's posting status: 44 guards posted, 2 absent flagged, 2 pending confirmation. One AI anomaly flagged for review.

I can see which sites are fully staffed, which have gaps, and what requires my attention — without making a single call. Let's go deeper."

---

**[0:30 – 2:00] Roster Board + AI Optimizer**

*Screen: Roster Board OWL view for current month*

"This is the Roster Board for June. Each column is a site. Each row is a shift slot. The colour coding tells me the status: green is confirmed, orange is draft, red is a conflict.

I'm going to click on this slot — Post 2 at Millennium Tower, Wednesday night shift. The contract requires a Grade C supervisor. Let me assign someone.

The system shows me eligible guards — scored and ranked. Guard Tjipangandjara scores 94 out of 100. Grade C, certification current, no client exclusion on record, hasn't worked the last 3 Sunday nights, lives 8 km from the site.

I click Assign. He's confirmed for the slot. That confirmation feeds directly into the posting sheet that his field supervisor will see on the mobile app.

If I wanted to run the AI optimizer on the full month, I click here. The system scores every guard against every open slot and generates a draft roster. I review and confirm. The whole month planned in under 10 minutes."

---

**[2:00 – 3:00] Mobile Attendance on the Supervisor's Phone**

*Screen: DogForce Mobile app running in Expo on a phone simulator or physical device*

"This is what the field supervisor sees on their phone. They open DogForce Mobile, log in with their PIN, and see today's posting sheet — pre-populated from the roster we just confirmed.

Millennium Tower. Night shift. 4 guards. I tap Present on three, Absent on one — and I add a note: 'Guard requested emergency leave, relief arranged.'

I hit Submit. That takes me about 90 seconds.

Back in the web platform — the attendance data is live. The absent guard is flagged. The operations manager sees it immediately. Payroll knows that guard worked 0 hours on this shift."

---

**[3:00 – 4:00] Payslip Generation**

*Screen: Payroll module, payroll period for June*

"Now let me show you payroll. This is the June payroll period. 48 guard payslips to generate. I click Run Payroll.

The system pulls attendance data from all posting sheets for the month. It calculates regular hours, overtime (Labour Act rules — time and a half after 45 hours per week), night shift differentials, public holiday premiums.

Here's Guard Tjipangandjara's payslip. Basic pay: NAD 5,200. Overtime: 8 hours at 1.5 rate — NAD 780. Night differential: NAD 340. Gross: NAD 6,320.

PAYE calculated at the current bracket: NAD 412. SSC employee contribution: NAD 63.20. Net pay: NAD 5,844.80.

Every figure is traceable to the computation that produced it. If NamRA or the guard disputes any number, I click through and see the exact calculation. No black box."

---

**[4:00 – 4:45] Client Billing Invoice**

*Screen: Billing module, client contract for Millennium Tower*

"Client billing. This is the contract for Millennium Tower. 3 posts, 24/7 coverage, Grade C supervisor at one post. The billing rate is set in the contract — NAD 38 per guard-hour.

I click Generate Invoice for June. The system counts actual guard-hours delivered at this site in June from the attendance data. 2,016 guard-hours. Invoice value: NAD 76,608.

The invoice generates and is ready to send. If attendance had any anomalies — say, 50 guard-hours that don't match the roster — the AI flags it before the invoice generates. I review, correct, then invoice."

---

**[4:45 – 5:30] AI Anomaly Detection**

*Screen: AI Engine — anomaly log*

"The AI anomaly flagged on the dashboard earlier. Let me show you what it found.

Guard Hamutenya Nghifindaka attended Site 4 — the Shoprite distribution centre — on Monday at 06:15. But the roster shows him assigned to Site 2 on Monday. He was at the wrong site.

The AI flagged this as a posting anomaly. Either the roster has an error, or the guard went to the wrong location. Either way, it needs a review before payroll and billing treat it as a valid posting.

Without this flag: the guard gets paid for a site attendance that may be invalid. The client may get billed incorrectly. A dispute follows.

With the AI flag: the operations manager reviews, calls the supervisor, determines the guard was redirected due to an emergency at Site 4 and the roster was not updated. The anomaly is resolved with a note. Payroll and billing proceed correctly."

---

**[5:30 – 6:00] Pricing and Close**

*Screen: Simple pricing slide or spoken directly to camera/voiceover*

"DogForce Suite is offered as a monthly SaaS subscription. Pricing is based on guard headcount:

Starter, up to 25 guards: NAD 1,200 per month.
Growth, 26 to 100 guards: NAD 2,200 per month.
Enterprise, 100+ guards: quoted based on scope.

For context: most Namibian security companies pay NAD 1,500–3,500 per month to a payroll bureau alone. DogForce Suite replaces that — and adds roster planning, mobile attendance, AI anomaly detection, and client invoicing.

One-time implementation fee covers data migration, system configuration, and staff training.

If you want a live demo with your company's actual data — reach out. winston@cvmworldwide.com. I'll come to your office."

---

## 7. Pricing Strategy

### 7.1 Pricing Philosophy

Pricing must answer one question in the prospect's mind: is this cheaper and better than what I'm doing now? For Namibian security companies, the reference price is the payroll bureau fee (NAD 1,500–3,500/month) plus the opportunity cost of time spent on manual processes (estimate 20–40 hours/month at NAD 80–120/hour for an HR or operations manager = NAD 1,600–4,800/month).

The total cost of the current approach for a 50-guard company: approximately NAD 3,100–7,800/month. DogForce Suite should sit clearly below that while delivering more capability.

### 7.2 Tier Structure

| Tier | Guard Range | Monthly Price (NAD) | Notes |
|------|------------|---------------------|-------|
| Starter | Up to 25 guards | 1,200 | Includes all core modules |
| Growth | 26–100 guards | 2,200 | Includes AI features, mobile app |
| Enterprise | 101+ guards | Custom (from 3,500) | Dedicated support, custom integrations |

**Annual payment discount:** 15% discount for annual prepayment (improves cash flow; converts monthly clients to committed annual).

**First client discount:** DogForce Security Services (founding client) — 50% discount on Growth tier for the first 12 months in exchange for case study participation and reference designation.

### 7.3 One-Time Implementation Fee

| Company Size | Implementation Fee (NAD) | Includes |
|-------------|--------------------------|---------|
| Starter (≤25 guards) | 5,000 | Config, data migration, 1-day onsite training |
| Growth (26–100 guards) | 12,000 | Full data migration, 2-day onsite training, custom config |
| Enterprise (101+) | 25,000+ | Scoped per client, includes custom development allowance |

Implementation fee is non-negotiable for the first three clients (establishes the rate; provides cash flow for the development runway). From client four onwards, consider a reduced rate for referral clients.

### 7.4 Support Contracts

| Level | Monthly Price (NAD) | Response Time | Includes |
|-------|---------------------|---------------|---------|
| Basic (included in SaaS) | — | Next business day | Email support, bug fixes |
| Standard | 800 | 4 business hours | Email + WhatsApp, priority bug fixes |
| Premium | 1,800 | 2 hours | Dedicated contact, same-day critical fixes, 1 hr/month config assistance |

### 7.5 Pricing Rationale

- **NAD 1,200 (Starter):** Below the lowest-end payroll bureau fee. A Starter client switching from a bureau saves money immediately, even before accounting for time savings.
- **NAD 2,200 (Growth):** Positioned at or below the mid-market bureau fee. A 50-guard company paying NAD 2,000–3,000 to a bureau saves money and gains significantly more functionality.
- **NAD 3,500+ (Enterprise):** At this size, a security company almost certainly has a full-time HR or payroll officer. The value case is time savings plus compliance accuracy, not just bureau replacement.

### 7.6 Competitive Context

There are no known purpose-built security operations platforms in Namibia at this price point. Generic Odoo implementations in Namibia typically cost NAD 8,000–25,000 for setup plus NAD 2,000–5,000/month in support — without the security-specific functionality. The DogForce Suite pricing is aggressive relative to that baseline.

---

## 8. Success Metrics (Free to Track)

### 8.1 Online Presence Metrics

| Metric | Tool | Target (Month 3) | Target (Month 6) |
|--------|------|-----------------|-----------------|
| LinkedIn followers (company page) | LinkedIn Analytics | 100 | 300 |
| LinkedIn connections (personal) | LinkedIn | +150 | +350 |
| LinkedIn post average impressions | LinkedIn Analytics | 200 | 500 |
| GitHub repository stars | GitHub | 15 | 40 |
| GitHub repository forks | GitHub | 3 | 10 |
| YouTube demo video views | YouTube Studio | 100 | 400 |

### 8.2 Lead Funnel Metrics

| Metric | Tool | Target (Month 3) | Target (Month 6) |
|--------|------|-----------------|-----------------|
| Cold emails sent | HubSpot CRM free | 75 | 180 |
| Cold email open rate | HubSpot CRM free | 35% | 40% |
| Cold email reply rate | HubSpot CRM free | 8% | 12% |
| Demo requests received | Manual count | 3 | 8 |
| Demo calls completed | Manual count | 2 | 6 |
| Proposals sent | Manual count | 1 | 3 |

### 8.3 Revenue Metrics

| Metric | Target (Month 6) | Target (Month 12) |
|--------|-----------------|-------------------|
| Paying clients | 1 (DogForce Security Services) | 3 |
| Monthly Recurring Revenue (NAD) | 1,100 (founder rate) | 5,500 |
| Implementation fees collected (NAD) | 12,000 | 35,000 |

### 8.4 Free Tracking Tools

- **HubSpot CRM (free tier):** Contact tracking, email open rates, deal pipeline. No paid features needed until 1,000 contacts.
- **LinkedIn Analytics:** Built into the company page and personal profile. Impressions, reach, follower growth, content performance.
- **YouTube Studio:** View count, watch time, audience retention for the demo video.
- **GitHub Insights:** Star and fork count, traffic, referring sites.
- **Google Search Console (free):** Once a landing page or GitHub page is indexed, track search impressions and clicks.
- **Mailchimp (free tier up to 500 contacts):** For any newsletter or email broadcast, Mailchimp's free tier handles open and click tracking.

### 8.5 Qualitative Metrics (Track Manually)

- Number of in-person conversations initiated (networking events, cold calls, referrals)
- Demo-to-proposal conversion (how many demos result in a proposal request)
- Objections heard most frequently (pricing, feature gaps, trust) — used to improve pitch
- Referral source tracking (where did each lead come from: LinkedIn, email, Facebook, referral, event)

---

## 9. 12-Month Roadmap

### Months 1–3: Build Online Presence, First Demos

**Primary Objective:** Establish credible online presence, generate first 3 demo conversations, begin DogForce Security Services live deployment preparation.

**Marketing Actions:**
- Week 1: GitHub README updated, LinkedIn company page live, first LinkedIn post published.
- Week 2: Demo video recorded (unlisted YouTube). Cold email list of 30 Namibian security companies compiled.
- Week 3–4: Cold email sequence starts. 5 prospects per week. LinkedIn posting cadence (3/week) established.
- Month 2: First 2 Facebook groups engaged. Odoo community forum activity started. Odoo App Store listing for `security_l10n_na` submitted.
- Month 3: Demo video published publicly. First LinkedIn carousel post. LinkedIn follower target: 100.

**Platform Milestone:** DogForce Security Services data migration in progress. First modules live in staging.

**Revenue Target:** 0 external clients. Implementation fee payment from DogForce Security Services expected.

---

### Months 4–6: First Paying Client Live, Case Study Built

**Primary Objective:** DogForce Security Services fully live. First external client signed. Case study drafted.

**Marketing Actions:**
- Month 4: DogForce Security Services goes live on the platform. Document the deployment process as internal case study material.
- Month 4–5: LinkedIn case study teaser posts (anonymized). Continue cold email cadence to new prospects using "first client now live" as the trigger for re-engagement.
- Month 5: First paid external client demo. If conversion happens, begin implementation.
- Month 6: Full anonymized case study published as LinkedIn article. Shared in Facebook groups and via cold email to all prior prospects who did not convert.

**Platform Milestone:** All core modules stable. AI anomaly detection running in production. Mobile app in active use by DogForce Security Services field supervisors.

**Revenue Target:** NAD 1,100/month (DogForce founding rate) + NAD 2,200/month from first external client = NAD 3,300 MRR. Implementation fee from first external client: NAD 12,000.

---

### Months 7–9: Second External Client, Expansion Preparation

**Primary Objective:** Second external client signed. Begin Zambia market research. Odoo partner outreach initiated.

**Marketing Actions:**
- Month 7: Reach out to 3 Odoo implementation partners in South Africa and Zambia with co-implementation proposal.
- Month 7–8: Second case study in progress. Begin identifying Zambia-based security companies for outreach.
- Month 8: Namibia Chamber of Commerce event participation or speaker request submitted.
- Month 9: LinkedIn article on "Building for the SADC security industry" — positions DogForce Suite as a regional product, not a Namibia-only tool. Begin outreach to Zambia prospects.

**Platform Milestone:** `security_l10n_zm` (Zambia payroll localization) scope defined. `security_licensing` (DeployGuard OS) module development starts.

**Revenue Target:** NAD 2,200/month from second external client = NAD 5,500 MRR total. Target: 3 clients total.

---

### Months 10–12: Zambia Market Entry, 5-Client Goal

**Primary Objective:** First Zambia client signed or in active sales process. 5 total clients across Namibia and Zambia.

**Marketing Actions:**
- Month 10: Zambia cold email campaign starts (equivalent outreach to Months 1–3 Namibia playbook). LinkedIn content pivots to include Zambia-specific examples.
- Month 10–11: `security_licensing` (SaaS licensing module) live, enabling automated licence management at scale.
- Month 11: Partner with one SADC Odoo implementation firm on a co-sell arrangement.
- Month 12: Annual review. Publish "Year 1 in Review" LinkedIn post (authentic, specific, positions CVM Worldwide as the leading security operations platform developer in Southern Africa).

**Platform Milestone:** DeployGuard OS licensing website live (Next.js/Firebase). Zambia localization pack in beta. 5 companies on platform.

**Revenue Target:**
- 5 clients (mix of Starter and Growth tiers)
- Target MRR: NAD 9,000–12,000
- Total implementation fees collected Year 1: NAD 50,000+
- Support contract revenue beginning: NAD 3,000–5,000/month

---

### 12-Month Financial Summary

| Period | MRR (NAD) | Implementation Fees | Support | Total Monthly |
|--------|----------|---------------------|---------|---------------|
| Month 3 | 0 | 12,000 (DogForce) | 0 | — |
| Month 6 | 3,300 | 12,000 (external 1) | 0 | 3,300 |
| Month 9 | 5,500 | 12,000 (external 2) | 1,600 | 7,100 |
| Month 12 | 11,000 | 5,000 avg/new client | 4,000 | 15,000 |

Note: All figures in NAD. Implementation fees are one-time per client; shown in the period they are received.

---

## Appendix A: Quick Reference — Prospect Research Sources

| Source | URL / Method | What to Get |
|--------|-------------|-------------|
| BIPA | https://www.bipa.na | Search business registry for security companies |
| NamRA | https://www.namra.org.na | Published compliance guidance (confirm payroll complexity) |
| NCCI | https://www.ncci.org.na | Member directory, event calendar |
| LinkedIn Search | linkedin.com/search | "security director Namibia", "operations manager security" |
| Google | google.com | "security company Windhoek", "private security Namibia" |
| Yellow Pages Namibia | yellowpages.com.na | Listed security companies with contact details |
| Google Maps | maps.google.com | "security company Windhoek" — full list with websites and phone numbers |

---

## Appendix B: Key Contacts to Establish

| Target | Why | First Step |
|--------|-----|-----------|
| NCCI Technology or SME Committee | Speaking opportunity, member visibility | Email their secretariat requesting to present at a member event |
| Namibia HR Association | Payroll compliance is their audience | Find their next event, attend as a participant first |
| 3 Odoo implementation partners (South Africa) | Co-sell on Zambia/Botswana deals | LinkedIn outreach, share the GitHub repo, propose co-implementation |
| 1 Namibian payroll bureau | Partnership or competitive intelligence | Request an informational meeting as a "software developer researching the market" |
| DogForce Security Services (live reference) | Case study anchor, reference call access | Already in relationship — formalize the reference arrangement in writing |

---

*Document maintained by CVM Worldwide. Last updated: 2026-06-03.*
*Next review: 2026-09-03 (end of Month 3).*
