# QR Attendance

A small system for tracking when teachers start and finish class in a room.

A teacher picks a room and generates a QR code that lives for five minutes. A staff member scans it, and the teacher is timed in. When class is over the teacher presses Time Out. An administrator approves accounts, manages rooms, and reads the attendance reports.

There are two versions of the same app in this folder. They do the same job and share the same database design, so pick whichever one fits your setup. You do not need to run both.

| | Java version | Python version |
|---|---|---|
| Folder | `java/` | `python/` |
| Stack | Javalin, MySQL, plain HTML and JavaScript | Flask, server-rendered pages, no JavaScript |
| Database | MySQL only | SQLite out of the box, MySQL if you want it |
| Staff scanning | Live camera in the browser | Upload or photograph the code, or paste it |
| Best for | Matching the original build | The quickest way to see it working |

If you just want to see it run in two minutes, use the Python version with SQLite.

---

## The accounts you can log in with

These exist after you finish setup. Change the passwords before anyone else uses the system.

| Role | Email | Password |
|---|---|---|
| Administrator | admin124@attendance.ph | Admin@12345 |
| Teacher | teacher@attendance.ph | Teacher@12345 |
| Staff | staff@attendance.ph | Staff@12345 |

On the login screen, choose the matching role from the dropdown, because the same email only works for its own role.

New teachers who sign up can log in right away. New staff accounts wait until an administrator approves them.

---

## Option A: Python version (fastest)

You need Python 3.10 or newer.

1. Open a terminal in the `python` folder.

2. Make a virtual environment and install the packages.

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   On Windows, activate with `.venv\Scripts\activate` instead.

3. Create the database and the three accounts.

   ```
   python seed.py
   ```

   You will see the three accounts printed back. Running it again is safe. It resets those passwords and leaves your other data alone. Use `python seed.py --reset` only if you want to wipe everything and start clean.

4. Start the app.

   ```
   python app.py
   ```

5. Open http://localhost:8080 and log in.

### Using MySQL with the Python version

Skip this unless you want MySQL. Set up the database first (see the MySQL section below), then start the app like this:

```
export DB_BACKEND=mysql
export DB_USER=root
export DB_PASS=your_password
python app.py
```

The other optional settings are `DB_HOST` (default `localhost`), `DB_PORT` (default `3306`) and `DB_NAME` (default `qr_attendance`).

### Running the tests

```
pip install pytest
python -m pytest tests
```

---

## Option B: Java version

You need Java 17 or newer, Maven, and a running MySQL server.

1. Set up the database (see the next section).

2. Open a terminal in the `java` folder and build.

   ```
   mvn package
   ```

3. Tell the app how to reach MySQL, then start it.

   ```
   export DB_URL=jdbc:mysql://localhost:3306/qr_attendance
   export DB_USER=root
   export DB_PASS=your_password
   java -jar target/qr-attendance.jar
   ```

   On Windows PowerShell, use `$env:DB_USER="root"` style lines instead of `export`.

4. Open http://localhost:8080 and log in.

The staff camera only works on `localhost` or on a site served over HTTPS. If you put the app on a real server, put HTTPS in front of it and set `COOKIE_SECURE=true`.

---

## Setting up MySQL

Both versions use the same two files in the `database` folder. Run them in this order.

```
mysql -u root -p < database/schema.sql
mysql -u root -p < database/accounts.sql
```

`schema.sql` builds the tables and adds five sample rooms. It drops and recreates the tables, so do not run it on a database that already holds real data.

`accounts.sql` adds the three accounts from the table above. It is safe to run more than once.

---

## Trying it out

The whole flow takes about a minute. Use two browser windows, or one normal window and one private window, so the two logins do not collide.

1. In window one, log in as the teacher. Pick Room 101 and press Generate QR code.
2. In window two, log in as staff. In the Java version, press Start camera and show the code to your webcam. In the Python version, upload a screenshot of the code, or copy the long text shown under the code and paste it into the manual box.
3. Staff will see a message saying the Time In was recorded. Room 101 now shows up under Rooms in use.
4. Back in window one, press Time Out on the attendance table.
5. Log in as the administrator to see the record in the reports, filter it, and export it.

---

## What each role can do

**Teacher** picks an available room, generates a QR code, and sees their own attendance history. A code expires after five minutes and can only be used once. A teacher cannot generate a new code while they are still timed in.

**Staff** scans codes, watches which rooms are in use right now, and searches the full attendance history.

**Administrator** approves, suspends, or reactivates teacher and staff accounts, adds rooms, sees the summary counts, and reviews reports. Suspending someone logs them out immediately.

The Java version prints a report from the browser. The Python version downloads a CSV instead, which opens in Excel or Google Sheets.

---

## Settings

| Setting | Used by | What it does | Default |
|---|---|---|---|
| `PORT` | both | Port the app listens on | 8080 |
| `DB_URL` | Java | JDBC address of the database | `jdbc:mysql://localhost:3306/qr_attendance` |
| `DB_USER` | both | Database user | `root` |
| `DB_PASS` | both | Database password | empty |
| `DB_BACKEND` | Python | `sqlite` or `mysql` | `sqlite` |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | Python | MySQL connection details | localhost, 3306, qr_attendance |
| `SQLITE_PATH` | Python | Where the SQLite file lives | `python/qr_attendance.db` |
| `APP_TZ` | Python | Time zone used for displayed times | `Asia/Manila` |
| `SECRET_KEY` | Python | Signs the short-lived QR display cookie | random each start |
| `COOKIE_SECURE` | both | Set to `true` when serving over HTTPS | off |

Times are stored in UTC. The Java version shows them in each browser's own time zone. The Python version shows them in `APP_TZ`.

---

## If something goes wrong

**"Could not reach the server" or a blank page.** The app is not running, or you are on the wrong port. Check the terminal where you started it.

**The Java app crashes on start with a connection error.** MySQL is not running, or `DB_USER` and `DB_PASS` are wrong. Try logging in with `mysql -u root -p` using the same credentials.

**"Incorrect email, password or role".** Check the role dropdown. An administrator email will not work with Teacher selected.

**"Your account is waiting for administrator approval".** New staff accounts need an administrator to approve them first.

**"This QR code has expired".** Codes last five minutes. Generate a new one.

**"Time out of your current class before generating a new code".** The teacher is still timed in. Press Time Out first.

**The camera will not start.** Allow camera access in the browser, and make sure you are on `localhost` or HTTPS. The manual box always works as a fallback.

**Python says `No module named ...`.** The virtual environment is not active. Run the activate command again and reinstall with `pip install -r requirements.txt`.

**The Python upload says no QR code could be read.** Use a sharper, well-lit image with the whole code in frame, or paste the text instead.

---

## Before you put this in front of real users

- Change the three default passwords, or delete those accounts and create your own.
- Serve the app over HTTPS and set `COOKIE_SECURE=true`.
- Set a fixed `SECRET_KEY` for the Python version so QR displays survive a restart.
- Do not leave the database password empty.
- Back up the database. The attendance table is the record that matters.

---

## What is in the folder

```
qr-attendance/
  README.md
  database/
    schema.sql          tables and sample rooms (MySQL)
    accounts.sql        the three starter accounts (MySQL)
  docs/
    TIMELINE-2-WEEKS.md  full build plan across two weeks
    TIMELINE-2-DAYS.md   compressed plan for a two-day sprint
  java/
    pom.xml
    src/main/java/ph/attendance/   server code
    src/main/resources/public/     pages, scripts, styles
  python/
    app.py              routes
    services.py         the attendance rules
    db.py               database access (SQLite and MySQL)
    security.py         password hashing and tokens
    seed.py             creates the database and accounts
    accounts.py         the starter account list
    templates/          the pages
    static/app.css
    tests/
```

Passwords are hashed with PBKDF2 and the same format in both versions, so an account created in one can log in to the other if they share a MySQL database.
