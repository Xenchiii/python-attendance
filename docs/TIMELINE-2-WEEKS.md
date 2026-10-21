# Two-Week Timeline

A relaxed plan for building QR Attendance from nothing to something you can demo, with time for testing and fixing what you find. It assumes one or two people working a normal school-day schedule, Monday to Friday, with the weekend as buffer.

The deliverable at the end of week two is a working system, both role dashboards, an administrator panel, a test pass, and documentation.

---

## Week 1: Foundation and core features

### Day 1 (Monday): Planning and setup
- Agree on the three roles and what each one may do.
- Write down the attendance rules: a QR code lasts 5 minutes, works once, and a teacher can only be timed in to one room at a time.
- Install Java, Maven, Python, and MySQL. Confirm each runs.
- Create the project folder and a Git repository.

**Done when:** the rules are written on one page and every tool runs on every machine.

### Day 2 (Tuesday): Database
- Design the five tables: users, rooms, qr_sessions, attendance, auth_sessions.
- Write `schema.sql` with the sample rooms.
- Add the rule that stops a teacher from having two active records at once, enforced in the database itself.
- Create the starter accounts.

**Done when:** the schema loads on a clean MySQL server with no errors.

### Day 3 (Wednesday): Accounts and login
- Password hashing and verification.
- Sign up, log in, log out, and the "who am I" check.
- Session cookies that expire after 8 hours.
- Teacher sign-ups are active immediately. Staff sign-ups wait for approval.

**Done when:** all three seeded accounts can log in and a wrong password is refused.

### Day 4 (Thursday): QR generation and Time In
- Generate a QR token for a teacher and room, store only its hash.
- Cancel any older unused code when a new one is made.
- Staff scan endpoint: check the code exists, is unused, has not expired, and the room is free.
- Mark the room occupied and create the attendance record in one transaction.

**Done when:** a code can be generated, scanned once, and a second scan is refused.

### Day 5 (Friday): Time Out and review
- Teacher Time Out: close the record, calculate minutes (minimum one), free the room.
- Attendance list with filters for search text, status, and date.
- Review the week. Write down anything that felt wrong.

**Done when:** a full cycle of generate, scan, time out leaves the room free and the record complete.

### Weekend: buffer
Catch up on anything unfinished. Do not start new features.

---

## Week 2: Interface, administrator tools, and polish

### Day 6 (Monday): Teacher and staff screens
- Login and sign-up page.
- Teacher dashboard: room picker, QR display with a countdown, own history, Time Out button.
- Staff dashboard: scan input, rooms currently in use, history table.

**Done when:** a teacher and a staff member can complete the whole flow using only the screens.

### Day 7 (Tuesday): Administrator panel
- Summary counts: teachers, staff, pending approvals, rooms in use, records today.
- Approve, suspend, and reactivate accounts. Suspending ends the person's sessions at once.
- Add rooms, with a clear message when a code is already taken.
- Reports with filters, plus print or CSV export.

**Done when:** an administrator can approve a new staff account and that person can then log in.

### Day 8 (Wednesday): Python version
- Rebuild the browser logic in Python so the pages are produced on the server.
- Replace the live camera with image upload and manual entry.
- Add SQLite support so it runs with no database server.
- Add the CSV export in place of browser printing.

**Done when:** the Python version passes the same walkthrough as the Java version.

### Day 9 (Thursday): Testing and fixes
- Automated tests for login, sign-up rules, the full attendance cycle, expired codes, replayed codes, and role restrictions.
- Manual pass on a phone and a laptop.
- Try to break it: two tabs, two teachers on one room, expired codes, suspended users mid-session.
- Fix what you find.

**Done when:** all tests pass and the known-issues list is empty or consciously deferred.

### Day 10 (Friday): Documentation and handover
- Write the README so a stranger can set it up without asking you anything.
- Have someone who did not build it follow the README from scratch. Fix every step where they get stuck.
- Package the project into a zip.
- Demo to the people who will use it.

**Done when:** a new person can go from zip file to a working login in under ten minutes.

### Weekend: buffer
Held back for anything that slipped.

---

## Summary table

| Day | Focus | Output |
|---|---|---|
| 1 | Planning, setup | Rules page, tools installed |
| 2 | Database | schema.sql |
| 3 | Accounts and login | Working authentication |
| 4 | QR and Time In | Generate and scan |
| 5 | Time Out and lists | Complete attendance cycle |
| 6 | Teacher and staff screens | Usable dashboards |
| 7 | Administrator panel | Accounts, rooms, reports |
| 8 | Python version | Second implementation |
| 9 | Testing and fixes | Passing test suite |
| 10 | Documentation and demo | README, zip, demo |

## Risks to watch

- **Time zones.** Store everything in UTC and convert only when displaying.
- **Two scans at the same moment.** Rely on the database rule, not just a check in code.
- **Camera access.** Browsers only allow it on localhost or HTTPS, so plan for this before demo day.
- **Staff approval confusion.** Tell new staff plainly that they must wait for approval.
