# 🛠️ Troubleshooting Guide (Windows)

Common issues when setting up **MedLink** on Windows.

---

## ❌ `"python"` opens Microsoft Store

**Cause:** Windows doesn’t recognize Python properly.
**Fix:**

1. Uninstall the Microsoft Store **“App Installer” Python**.
2. Download and install Python 👉 [python.org/downloads/windows](https://www.python.org/downloads/windows/)
3. During installation, check **“Add Python to PATH”**.

---

## ❌ `"pip" is not recognized`

**Cause:** `pip` not added to PATH.
**Fix:**

* Reinstall Python and ensure **“Add Python to PATH”** is checked.
* Or run:

  ```bash
  python -m ensurepip --upgrade
  ```

---

## ❌ `"git" is not recognized`

**Cause:** Git is not installed, or PATH is missing.
**Fix:**

1. Install Git 👉 [git-scm.com/download/win](https://git-scm.com/download/win)
2. Restart the terminal.
3. Test with:

   ```bash
   git --version
   ```

---

## ❌ Pipenv errors (`command not found`)

**Cause:** Pipenv not installed globally.
**Fix:**

```bash
pip install pipenv
```

---

## ❌ Port already in use (when running server)

**Cause:** Port **8000** is already being used.
**Fix:** Run the server on a different port:

```bash
python manage.py runserver 8080
```

Then open 👉 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

---

## ❌ Virtual environment won’t activate

**Cause:** Windows restricts script execution.
**Fix:** Open PowerShell as **Administrator** and run:

```powershell
Set-ExecutionPolicy RemoteSigned
```

Then activate again:

```bash
pipenv shell
```

---

💡 **Still stuck?** Open an [issue on GitHub](https://github.com/Kintoyyy/MedLink/issues).
