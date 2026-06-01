**Cosmo Hydraulic Industries — Label Printer (v2.0)**

A small desktop app to design, save and print 4×4 inch industrial labels optimized for the TSC TE244 thermal printer.

**Overview**
- **Purpose:** Create high-quality 4×4 inch labels with company logo, QR/barcode, product and inventory data.
- **Printer:** Targeted for TSC TE244 (TSPL/TSPL2) at 203 DPI.
- **UI:** Built with `tkinter` for a lightweight GUI.

**Features**
- Render precise 4×4 inch labels (PIL/Pillow) with pure white background suitable for thermal printing.
- QR code generation (via `qrcode`) and fallback barcode support (optional `python-barcode`).
- Save, edit and search labels in a local SQLite database (`cosmo_labels.db`).
- Logo support (paste a PNG/JPG logo onto the label).
- Settings persistence and basic access control (default password: `cosmo123`).
- Optional direct Windows printing support via `pywin32`.
- License/kill-switch check at startup (fetches status from a GitHub-hosted JSON).

**Repository Contents**
- `main.py` — application entry point and full source (GUI, renderer, DB layer).
- `main.bat` — optional launcher for Windows.
- `SynixPayroll.spec` — PyInstaller spec (if you build a single-file executable).

If you add files (icons, logos), place them next to `main.py` or set a path in the app settings.

**Requirements**
- Python 3.8 or newer
- Required Python packages:
  - `Pillow`
  - `qrcode[pil]`
  - `reportlab`
  - `python-barcode` (optional — enables barcode images)

Optional (Windows printing):
- `pywin32`

Install recommended packages with pip:

```bash
pip install pillow qrcode[pil] reportlab python-barcode
# Optional for Windows printing
pip install pywin32
```

**Run (development)**
- From the repository root run:

```bash
py main.py
# or
python main.py
```

**Build (create single executable)**
- Example PyInstaller command used during development:

```bash
pyinstaller --onefile --windowed --icon=logo.ico --name SynixPayroll main.py
```

Notes about building:
- Ensure `logo.ico` exists in the working directory when using `--icon`.
- The generated executable will be placed in `dist/SynixPayroll.exe` by default.
- Use the included `SynixPayroll.spec` if you want to reproduce the same build options.

**Configuration & Data**
- Database: `cosmo_labels.db` will be created in the app directory.
- Default password: `cosmo123` (the app stores a hashed password). Change it in settings after first run.
- License check URL is embedded in the app; if you need an offline-only build, remove or modify the license check code in `main.py`.

**Security & Privacy**
- The app performs a network request to check a JSON status on GitHub at startup — this is used to enable/disable the app remotely. If this is a concern, remove the call to `fetch_license()` in `main.py`.

**Troubleshooting**
- Missing Pillow or qrcode: install with pip as shown above.
- Barcode images fall back to QR codes if `python-barcode` is not installed.
- If printing to a Windows printer fails, install `pywin32` and restart the app.

**Next steps / Contribution**
- Add a `requirements.txt` if you want reproducible installs:

```text
Pillow
qrcode[pil]
reportlab
python-barcode
# pywin32  # optional
```
- Consider adding automated tests, an installer, or a packaged release on GitHub Releases.

**License**
- Add your preferred license file (e.g., `LICENSE`) before publishing to GitHub.

---
Created from the project files in this repository. If you want, I can also:
- generate a `requirements.txt`
- add a simple `README` badge list
- prepare a commit message and git commands to push to GitHub
