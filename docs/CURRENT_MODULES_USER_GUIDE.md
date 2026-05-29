# Current Modules User Guide

Date: 2026-05-27

This guide explains the current custom Odoo modules in simple terms for a beginner user.

At the moment, the following custom modules are installed in the `odoo-security` database:

- `security_base`
- `security_operations`
- `security_attendance`

These modules are the foundation of the future Dogforce Security Suite.

## 1. What These Modules Do

### `security_base`

This module stores the core information about security guards.

It adds:

- guard profiles on employees
- grade levels
- certifications
- language skills
- physical or medical attributes
- reliability score
- disqualification reasons

In simple terms:

This is where you define **who a guard is** and **what they are qualified to do**.

### `security_operations`

This module stores the core field operations setup.

It adds:

- post types
- security posts
- shift templates
- site requirements
- roster slots

In simple terms:

This is where you define **where guards work**, **what type of post it is**, and **which shifts must be filled**.

### `security_attendance`

This module stores actual attendance against planned roster slots.

It adds:

- attendance records linked to roster slots
- scheduled shift start and end
- actual check-in and check-out
- late minutes
- early departure minutes
- worked hours
- missing check-out flag

In simple terms:

This is where you compare **what was planned** against **what actually happened**.

## 2. How These Modules Fit a Security Company

Security companies do not operate like ordinary office businesses.

They usually need to manage:

- many guards
- many client sites
- different post types
- day and night shifts
- certification-based assignments
- guard reliability and discipline
- shift-by-shift attendance accuracy

The current modules already match that operating model:

- `security_base` defines the guard
- `security_operations` defines the work to be done
- `security_attendance` checks whether the work was actually done

This is the correct order for a security company system.

## 3. How These Modules Fit Dogforce Requirements

Dogforce asked for:

- guard characteristics and grading
- post-based rostering
- 12-hour shift structure
- attendance based on scheduled shifts
- late, early, and absent detection

The current modules already cover the beginning of that scope:

- guard profile and grading: `security_base`
- posts, post types, roster structure: `security_operations`
- scheduled vs actual attendance: `security_attendance`

The later modules will extend this into:

- leave
- payroll
- loans
- behavioral deductions
- invoicing
- banking and reconciliation

## 4. Where To Find The Menus In Odoo

In the `odoo-security` database, look for the top menu:

- `Security`

Under that, you should see:

- `Configuration`
- `Operations`

### Under `Security > Configuration`

You should find:

- `Grades`
- `Certifications`
- `Language Skills`
- `Attributes`
- `Disqualification Reasons`

### Under `Security > Operations`

You should find:

- `Post Types`
- `Shift Templates`
- `Security Posts`
- `Site Requirements`
- `Roster Slots`
- `Attendance Records`

## 5. Beginner Workflow

If you are using the system for the first time, do the setup in this order.

### Step 1: Create Guard Master Data

Go to:

- `Security > Configuration > Grades`
- `Security > Configuration > Certifications`
- `Security > Configuration > Language Skills`
- `Security > Configuration > Attributes`
- `Security > Configuration > Disqualification Reasons`

Create records such as:

- Grade A
- Grade B1
- Firearm Certified
- First Aid Certified
- CCTV Trained
- English
- Afrikaans

This creates the rule vocabulary the business will use later.

### Step 2: Prepare Employee Guard Profiles

Open an employee record in HR.

Go to the `Security Profile` tab.

Set:

- `Security Guard`
- grade
- certifications
- language skills
- attributes
- reliability score
- home location
- medical fitness grade if needed

If a guard is not allowed to work certain posts, mark them as disqualified and set a reason.

### Step 3: Create Post Types

Go to:

- `Security > Operations > Post Types`

Create the post types used by the company, for example:

- Main Gate
- Control Room
- Cash-in-Transit
- Reception

For each post type, define:

- minimum grade
- required certifications

This is what makes later rostering rules possible.

### Step 4: Create Shift Templates

Go to:

- `Security > Operations > Shift Templates`

Create shift templates such as:

- Day Shift: `06:00` to `18:00`
- Night Shift: `18:00` to `06:00`

The system calculates duration automatically.

### Step 5: Create Security Posts

Go to:

- `Security > Operations > Security Posts`

Create actual deployment points such as:

- Dogforce HQ Main Gate
- Warehouse Gate 2
- Client A Control Room

For each post, set:

- client
- post type
- required guard count
- shift template
- location

### Step 6: Define Site Requirements

Go to:

- `Security > Operations > Site Requirements`

Use this to state what a client site needs, for example:

- Client A needs 2 Control Room guards
- Client B needs 1 Cash-in-Transit crew

You can also set preferred guards.

### Step 7: Create Roster Slots

Go to:

- `Security > Operations > Roster Slots`

Create the actual planned shift entries.

For each slot, set:

- date
- post
- shift template
- assigned guard

The system will check:

- disqualification
- minimum grade
- required certifications

This means an unsuitable guard cannot be assigned without fixing the data first.

### Step 8: Record Attendance

Go to:

- `Security > Operations > Attendance Records`

Create an attendance record linked to the roster slot.

Set:

- check-in time
- check-out time

The system will automatically calculate:

- scheduled hours
- worked hours
- valid hours
- late minutes
- early departure minutes
- missing check-out
- attendance status

## 6. Example Real-World Flow

Here is a simple daily operational example.

1. HR creates a guard and marks them as a security guard.
2. HR assigns Grade B1 and Firearm Certified.
3. Operations creates a post type called `Cash-in-Transit`.
4. Operations sets minimum grade `B1` and required certification `Firearm Certified`.
5. Operations creates a shift template for `06:00-18:00`.
6. Operations creates a security post for a client.
7. Operations creates a roster slot for tomorrow.
8. Operations assigns the qualified guard.
9. On duty day, supervisor records check-in and check-out.
10. Odoo calculates whether the guard was late, left early, or completed the shift correctly.

That is the base workflow of a real security company.

## 7. Current Limitations

The current modules do **not** yet cover:

- leave balances
- approved leave integration
- payroll
- overtime premiums
- loans
- behavioral deductions
- auto-roster
- invoicing
- bank reconciliation

Those will be added in later modules.

## 8. What Comes Next

The next recommended module is:

- `security_leave`

That is the next logical step because Dogforce needs attendance, leave, and payroll to work together.

