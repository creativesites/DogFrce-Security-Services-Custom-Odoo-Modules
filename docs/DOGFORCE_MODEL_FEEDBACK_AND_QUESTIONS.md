# Dogforce Model Feedback And Questions

## Decisions From Current Feedback

### Clients, Sites, And Posts

Security posts should belong under a client structure. The clean model is:

1. Client
2. Site or contract location
3. Post position
4. Shift requirement
5. Roster slot

Example:

- Client: ABC Mall
- Site: ABC Mall Windhoek
- Post positions: Main Gate, Control Room, Perimeter Patrol
- Shift requirements: Main Gate day shift 1 guard, Main Gate night shift 1 guard, Control Room night shift 2 guards

This means a site does not need duplicate posts only because it has day and night shifts. A post position can have multiple shift requirements, and each requirement can define its own shift template, guard count, days of week, rate, and requirements.

### Multiple Post Types At One Site

A single client site can have many post positions. Each position should have its own type and guard count.

Example:

- Main Gate: Access Control, 1 guard
- Control Room: CCTV / Control Room, 2 guards
- Perimeter: Patrol, 5 guards

This should be represented as separate post positions under the same site, because the requirements, rate, supervision, and attendance checks can differ.

### Shift Fairness

Night shifts and overtime create favoritism risk because they can pay more. The system should track:

- Night shift allocation count per guard
- Overtime hours per guard
- High-rate shift allocation by supervisor
- Rotation fairness score
- Exceptions with approval reason

Auto-rostering should later include fairness rules, such as maximum night shifts per period, balanced overtime distribution, and supervisor override tracking.

### Rates

Rates should not only live on employee grade. The final pricing/pay model should support:

- Guard base rate by grade
- Site or client premium
- Shift template premium
- Post type premium
- Certification premium
- Overtime multiplier
- Public holiday multiplier
- Night shift multiplier

This matters because some client requirements raise billing rates and guard pay rates.

### Site Requirements

Site requirements should support more than grade and certification. They should include:

- Minimum grade
- Required certifications
- Optional preferred certifications
- Required languages
- Required attributes
- Minimum reliability score
- Minimum experience
- Medical fitness
- Firearm eligibility
- Site-specific exclusion rules

Some requirements affect whether a guard can be assigned. Others affect pay or billing rate.

### Grade Hierarchy

Grades should be hierarchical. A higher grade should qualify for lower-grade posts unless a post has a specific certification or attribute requirement.

Grades should also be rule-based:

- Required certifications
- Optional certifications
- Minimum experience
- Minimum time at company
- Minimum reliability score
- Required attributes

Firearm training should be a certification or attribute, not a grade by itself.

### Flexible Rostering

Roster slots should be generated in bulk from shift requirements instead of created one by one. The target workflow is:

1. Define client site.
2. Define post positions.
3. Define shift requirements and days of week.
4. Generate roster for a week or month.
5. Auto-fill eligible guards where possible.
6. Review conflicts, fairness, leave, overtime, and approvals.

### Attendance And Overtime

Attendance must remain tied to scheduled shift template times. Overtime should be explicit and auditable:

- Scheduled hours
- Actual worked hours
- Valid paid hours
- Overtime hours
- Overtime approval
- Overtime reason
- Overtime rate multiplier

The system should make guard income visible over a period so overtime favoritism and payroll surprises are easier to detect.

### Guard Check Devices

Some sites may need periodic proof that a guard is awake and on post. The system should later support device logs such as:

- Checkpoint scans
- NFC / RFID tags
- QR code checkpoint scans
- GPS pings
- Panic button events
- Supervisor patrol inspections
- Missed checkpoint alerts

This should probably become a later module: `security_patrol_checks`.

## Questions For Dogforce WhatsApp Group

### Client And Site Setup

1. Do your contracts normally have one site per client, or can one client have multiple sites?
2. For each client site, can you list the normal post positions you use, such as gate, control room, reception, patrol, cash office, or supervisor?
3. Do you bill clients per guard, per post, per shift, per month, or a mixture?
4. Do different client sites have different VAT or invoice wording requirements, or is it standard for all?

### Shifts And Schedules

1. What are your standard shift templates today, for example 06:00-18:00 and 18:00-06:00?
2. Are some posts only active Monday to Friday?
3. Are some posts active only during business hours?
4. Do any sites have special weekend or public holiday schedules?
5. How far ahead do you normally prepare rosters: weekly, fortnightly, or monthly?

### Guard Assignment Rules

1. What grades do you use, and which grade is highest?
2. Should higher-grade guards automatically qualify for lower-grade posts?
3. Which certifications or training records matter for assignment, for example firearm, first aid, dog handling, driving, control room, or radio procedure?
4. Which client sites require English, Afrikaans, Oshiwambo, or another language?
5. Are there guards who must never be sent to specific clients or sites?

### Pay, Overtime, And Fairness

1. Which shifts pay more: night shift, Sunday, public holiday, overtime, or special site shifts?
2. Is overtime always double rate, or are there different overtime rules?
3. Who approves overtime before payroll?
4. Do supervisors currently decide who gets night shifts?
5. Do you want the system to warn when one guard receives too many high-paying shifts compared with others?

### Attendance And Checkpoints

1. How do guards currently check in and check out?
2. Do you use biometric devices, RFID, QR checkpoints, WhatsApp, paper registers, or supervisor calls?
3. Do some posts require guards to check in periodically during a shift?
4. What happens if a guard misses a checkpoint?
5. Do you need GPS location evidence for check-in or patrol checks?

### Payroll And Guard Income

1. Are guards paid hourly, daily, monthly, or by shift?
2. Do different guards have different rates within the same grade?
3. Which deductions are common: loans, uniforms, damages, absences, lateness, disciplinary deductions?
4. Should guards be able to see or receive a breakdown of their earnings?
5. What payroll reports does management check every month?

### Reports And Dashboards

1. Which report do managers ask for most often?
2. Do you need reports by client, site, supervisor, guard, or period?
3. Which KPIs matter most: attendance, absences, overtime, incidents, payroll cost, invoice value, payment status, or profit by site?
4. Should clients receive their own attendance or service reports?
5. Should reports be exported to Excel or PDF?
