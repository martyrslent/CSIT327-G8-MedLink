# 🛠️ Troubleshooting Guide (Windows)

Common issues when setting up **MedLink** on Windows.

---

## ❌ `"python"` opens Microsoft Store

**Cause:** Windows doesn’t recognize Python properly.
**Fix:**

1. Uninstall the Microsoft Store **“App Installer” Python** app if installed.
2. Download and install Python 👉 [python.org/downloads/windows](https://www.python.org/downloads/windows/)
3. During installation, make sure to check **“Add Python to PATH”**.

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

## ❌ Virtual environment won’t activate (PowerShell script execution restricted)

**Cause:** Windows restricts running scripts due to Execution Policy, and you **do not have admin rights** to change it.
**Fix:**

* Use **Command Prompt** instead of PowerShell, then activate with:

  ```cmd
  venv\Scripts\activate.bat
  ```

* Alternatively, in PowerShell, you can run the Python interpreter inside the virtual environment without activating it:

  ```powershell
  .\venv\Scripts\python.exe manage.py runserver
  ```

* If you *do* have admin rights on another machine, you can open PowerShell **as Administrator** and run:

  ```powershell
  Set-ExecutionPolicy RemoteSigned
  ```

  Then activate with:

  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

---

## ❌ Port already in use (when running server)

**Cause:** Port **8000** is already in use.
**Fix:** Run the Django development server on a different port:

```bash
python manage.py runserver 8080
```

Then open 👉 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)

---

## ❌ Pipenv errors (`command not found`)

**Cause:** Pipenv is not installed or unavailable on your system.
**Fix:**

* We recommend switching to the built-in `venv` for virtual environments (see setup guide).

* If you still want to use pipenv, install it with:

  ```bash
  pip install --user pipenv
  ```

* Make sure your user-level `Scripts` directory is added to PATH.

---

💡 **Still stuck?** Open an [issue on GitHub](https://github.com/Kintoyyy/MedLink/issues).
