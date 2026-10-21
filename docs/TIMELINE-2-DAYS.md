# Two-Day Timeline

A tight sprint plan for when you need QR Attendance working fast. It assumes the code in this folder is your starting point, so the two days go to setup, verification, adjusting it to your school, and getting it in front of users, not to writing it from scratch.

Plan for about eight working hours each day. If you only have a few hours per day, cut the Python version or the customizing and keep the rest.

---

## Day 1: Get it running and prove it works

### Morning

**08:00 to 09:00 Setup**
- Install Java 17 or newer and Maven, or Python 3.10 or newer. You only need the stack you plan to use.
- Install MySQL if you are using the Java version. Skip it for the Python version, which can use SQLite.

**09:00 to 10:30 Database and accounts**
- Java route: run `schema.sql` then `accounts.sql`.
- Python route: run `python seed.py`.
- Confirm you can see the three starter accounts.

**10:30 to 12:00 First run**
- Start the app and log in as each of the three roles.
- Fix any setup trouble using the README's troubleshooting section.

### Afternoon

**13:00 to 14:30 Walk through the main flow**
- Teacher generates a code for Room 101.
- Staff scans it.
- Teacher times out.
- Administrator finds the record in the report.

**14:30 to 16:00 Try to break it**
- Scan the same code twice.
- Wait for a code to expire, then scan it.
- Sign up a new staff member and approve them.
- Suspend someone while they are logged in.

**16:00 to 17:00 Write down findings**
- List anything confusing or wrong. Mark each one as must fix now or can wait.

**End of day 1:** the system runs on your machine and you know what needs changing.

---

## Day 2: Make it yours and hand it over

### Morning

**08:00 to 09:30 Fix the must-do list**
- Handle only the items you marked as must fix now.

**09:30 to 11:00 Customize**
- Replace the sample rooms with your real rooms, using the administrator screen.
- Create real teacher and staff accounts, or let people sign up and approve them.
- Change the default passwords for the three starter accounts.

**11:00 to 12:00 Phone check**
- Open the app on a phone. If staff will scan with a phone camera, confirm it works over HTTPS or the upload option.

### Afternoon

**13:00 to 14:30 Dry run with real people**
- Have one teacher and one staff member use it for a pretend class while you watch.
- Note every place they hesitate.

**14:30 to 15:30 Adjust**
- Fix quick wording or workflow problems from the dry run.
- Run the Python tests if you are using that version.

**15:30 to 16:30 Package and share**
- Zip the project.
- Write a half-page guide for teachers and a half-page guide for staff, based on the README walkthrough.

**16:30 to 17:00 Handover**
- Show the administrator how to approve accounts and read the reports.

**End of day 2:** real accounts, real rooms, tested with real users, and a zip file anyone can set up from the README.

---

## Checklist

Day 1
- [ ] Tools installed
- [ ] Database created and accounts added
- [ ] App starts and all three roles log in
- [ ] Full attendance cycle works
- [ ] Break-it list completed and issues recorded

Day 2
- [ ] Must-fix items resolved
- [ ] Real rooms added
- [ ] Default passwords changed
- [ ] Phone scanning confirmed
- [ ] Dry run completed
- [ ] Zip created and handover done

## What to cut if time runs short

1. The second implementation. Use only the Java or only the Python version.
2. Custom wording changes.
3. The user guides. Point people at the README walkthrough instead.

Do not cut the break-it testing or the password change. Those are the two things that cause real problems later.
