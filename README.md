# 🪟 MedLink Setup & Contribution Guide (Windows)

This step-by-step guide will help you:
- ✔ Install **Python** & **Git**
- ✔ Clone the **MedLink repo**
- ✔ Open the project in **VS Code**
- ✔ Run the **Django app** locally
- ✔ Create a branch & contribute on **GitHub**

---

## 1. Install Python 🐍

1. Download Python 👉 [Python 3.13.7](https://www.python.org/downloads/release/python-3137/)
2. Choose **Windows installer (64-bit)** and run the installer.
3. On the first screen, make sure to check:
   ✅ **Add Python to PATH**
   ✅ **Install launcher for all users**
4. After installation, verify Python:

   ```bash
   python --version
   ```

   Expected output:

   ```
   Python 3.x.x
   ```

---

## 2. Install Git 🔧

1. Download Git 👉 [Git for Windows](https://git-scm.com/download/win)
2. During installation:

   * Keep defaults (recommended).
   * Ensure **“Git from the command line and also from 3rd-party software”** is selected.
3. Verify Git:

   ```bash
   git --version
   ```

   Example:

   ```
   git version 2.x.x.windows.1
   ```

---

## 3. Clone the Repository 📂

1. Open **Command Prompt** (or **PowerShell**).
2. Run:

   ```bash
   git clone https://github.com/Kintoyyy/MedLink.git
   cd MedLink
   ```

* `git clone` downloads the project
* `cd MedLink` moves you into the folder

---

## 4. Open in VS Code 🖥️

1. Install **Visual Studio Code** 👉 [Download VS Code](https://code.visualstudio.com/download)
2. Open the project folder:

   ```bash
   code .
   ```

   *(Run this inside the `MedLink` folder. If `code` is not recognized, enable **“Add to PATH”** during VS Code installation, or enable the `code` command inside VS Code.)*

👉 Now you can edit and run the project directly in VS Code.

---

## 5. Install Recommended Extensions 🔌

Inside VS Code, install these extensions for a smoother workflow:

* **Python** (by Microsoft) → syntax highlighting, linting, debugging
* **Pylance** → smart autocomplete & IntelliSense for Python
* **Django** → template and model highlighting
* **GitLens** → better Git integration and history tracking
* **Prettier** → consistent code formatting
* **.env files support** → makes managing environment variables easier

👉 To install:

1. Press `Ctrl + Shift + X` to open **Extensions Marketplace**.
2. Search for each name above and click **Install**.

---

## 6. Set Up Virtual Environment (`venv`) 💻

We’ll use Python’s built-in `venv` to manage dependencies.

### ➤ Step 1: Create a Virtual Environment

In the project folder (`IMDC-Management-System`):

```bash
python -m venv venv
```

This creates a `venv/` folder with your isolated environment.

---

### ➤ Step 2: Activate the Virtual Environment

#### ✅ If using **Command Prompt**:

```cmd
venv\Scripts\activate.bat
```

#### ✅ If using **PowerShell**:

```powershell
.\venv\Scripts\Activate.ps1
```

#### ✅ If using **Linux**:

```bash
. venv/bin/activate
```

> ⚠️ If you see an error about script execution policy, use **Command Prompt** instead of PowerShell — it works without changing security settings.

---

### ➤ Step 3: Install Django

Once the environment is activated:

```bash
pip install django
```

---

### ➤ Step 4: Freeze Dependencies (for sharing with others)

```bash
pip freeze > requirements.txt
```

---

## 7. Run the Django App 🚀

Start the development server:

```bash
python manage.py runserver
```

Output should look like:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL+C.
```

👉 Open your browser: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
🎉 You should see the MedLink app running locally.

---

## 8. Create a New Branch 🌱

Before making changes, create a feature branch:

```bash
git checkout -b your-feature-name
```

Example:

```bash
git checkout -b add-login-page
```

---

## 9. Save & Commit Changes ✅

1. Edit files inside **VS Code**.
2. In terminal, stage and commit changes:

   ```bash
   git add .
   git commit -m "Added login page feature"
   ```

---

## 10. Push Your Branch to GitHub ☁️

Upload your branch:

```bash
git push origin your-feature-name
```

Example:

```bash
git push origin add-login-page
```

---

## 11. Open a Pull Request (PR) 🔄

1. Go to the [MedLink GitHub Repo](https://github.com/Kintoyyy/MedLink).
2. You’ll see a banner: **“Compare & Pull Request”**.
3. Click → describe your changes → **Create Pull Request**.

Done ✅ You’ve contributed to MedLink!

---

## 🔎 Quick Recap (Windows)

1. Install Python → `python --version`
2. Install Git → `git --version`
3. Clone repo → `git clone ...`
4. Open project in VS Code → `code .`
5. Install extensions → Python, Django, GitLens, Prettier
6. Install Pipenv → `pip install pipenv`
7. Enter env → `pipenv shell`
8. Run server → `python manage.py runserver`
9. Branch → `git checkout -b feature-name`
10. Commit → `git commit -m "msg"`
11. Push & PR 🚀

---

## ⚠️ Having Trouble?

Check the [Troubleshooting Guide](/TROUBLESHOOTING_WINDOWS.md).
