# MedLink

Welcome to **MedLink** — a web application for managing health services and appointments.
This README is written for **new developers** joining the project.

---

## 🚀 Tech stack

* **Next.js** (Page Router) — React framework for frontend + backend API routes
* **React** — frontend UI library
* **Tailwind CSS** — styling
* **MongoDB** + **Mongoose** — database + ORM
* **ESLint** — linting & code style

---

## 📂 Project structure

```
/pages
  index.js            # Home page
  appointments.js     # Appointments page
  api/
    test-db.js        # Test DB connection
/lib
  mongodb.js          # DB connection helper
/models
  Appointment.js      # Example Mongoose model
/public
/styles
package.json
tailwind.config.js
README.md
.env.example
```

---

## 🛠️ Setup instructions

### 1. Prerequisites

* Install **Node.js v20+**
* Install **npm** (comes with Node)

### 2. Clone repo

```bash
git clone git@github.com:Kintoyyy/MedLink.git
cd MedLink
```

### 3. Configure environment

Copy the example env file:

```bash
cp .env.example .env.local
```

Update `.env.local` with your MongoDB URI and any required secrets.

Example:

```env
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster0.xxxxx.mongodb.net/medlink
NEXT_PUBLIC_API_URL=http://localhost:3000
```

⚠️ Never commit `.env.local`.

### 4. Install dependencies

```bash
npm ci
```

---

## ▶️ Running the app

### Development mode

```bash
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

### Production build

```bash
npm run build
npm start
```

---

## ✅ Testing DB connection

Visit the test API route:

```
http://localhost:3000/api/test-db
```

If the DB is connected, you’ll see a list of collections.

---

## 👩‍💻 Contribution workflow (branch-based, step by step)

⚠️ **Never commit directly to `main`. Always work on your own branch.**

### 1. Sync `main` branch

```bash
git checkout main
git pull origin main
```

### 2. Switch to your own branch

If you already have a branch:

```bash
git checkout feature/add-appointments
```

If you need to create a new one:

```bash
git checkout -b feature/<short-description>
```

### 3. Update your branch with main

```bash
git checkout feature/add-appointments
git pull origin main
```

### 4. Do your work

* Run `npm run dev` while coding
* Run `npm run lint` to check style

### 5. Commit your changes

Use clear commit messages (Conventional Commit style):

Examples:

```bash
git add .
git commit -m "feat(appointments): add booking button"
git commit -m "fix(api): handle missing appointment date"
git commit -m "docs(readme): update branch workflow"
```

### 6. Push your branch

```bash
git push origin feature/add-appointments
```

### 7. Open a Pull Request (PR)

* PR target: `main`
* Title: short & descriptive (`feat: add appointments page`)
* Description: explain

  * What you changed
  * How to test
  * Screenshots if UI changed

### 8. Review & merge

* Reviewer checks code & functionality
* Fix issues if asked → commit & push again:

  ```bash
  git add .
  git commit -m "fix(appointments): update button color"
  git push origin feature/add-appointments
  ```
* After approval, PR is merged into `main` via GitHub/GitLab

### 9. Update your local main

After merge:

```bash
git checkout main
git pull origin main
```

---

## 🔍 Checklist before opening PR

* [ ] App builds without errors: `npm run build`
* [ ] Lint passes: `npm run lint`
* [ ] `.env.local` not committed
* [ ] PR description explains changes

---

## 🆘 Need help?

If you get stuck:

1. Share your branch name
2. Include error logs or screenshots
3. Describe the steps you tried

Post this info in Teams or tag your reviewer.
