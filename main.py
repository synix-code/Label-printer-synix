"""
============================================================
  COSMO HYDRAULIC INDUSTRIES — TSC TE244 Label Printer App
  Version : 2.0 (Production-Ready)
  Purpose : Create & Print 4×4 inch industrial labels
  Printer : TSC TE244 (TSPL/TSPL2 commands)
  Python  : 3.8+
============================================================

INSTALLATION:
    pip install pillow qrcode[pil] python-barcode reportlab

OPTIONAL (for direct Windows printing without copy command):
    pip install pywin32

USAGE:
    python cosmo_label_printer.py

DEFAULT PRINT PASSWORD: cosmo123
============================================================
"""

# ── Standard Library ──────────────────────────────────────
import os
import sys
import io
import sqlite3
import hashlib
import json
import urllib.request
import urllib.error
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
from pathlib import Path

# ── Third-Party ───────────────────────────────────────────
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
except ImportError:
    import tkinter as _tk
    _r = _tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing Library",
        "Pillow library not found.\n\nInstall it:\n  pip install pillow")
    sys.exit(1)

try:
    import qrcode
except ImportError:
    messagebox.showerror("Missing Library",
        "qrcode library not found.\n\nInstall it:\n  pip install qrcode[pil]")
    sys.exit(1)

# Optional barcode library
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False


# ─────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────
APP_TITLE      = "Cosmo Hydraulic Industries — Label Printer v2.0"
COMPANY_NAME   = "COSMO HYDRAULIC INDUSTRIES"
LABEL_W_INCH   = 4
LABEL_H_INCH   = 4
DPI_PREVIEW    = 96
DPI_PRINT      = 203
PX_W           = LABEL_W_INCH * DPI_PREVIEW    # 384
PX_H           = LABEL_H_INCH * DPI_PREVIEW    # 384
PRINT_PX_W     = LABEL_W_INCH * DPI_PRINT      # 812
PRINT_PX_H     = LABEL_H_INCH * DPI_PRINT      # 812

# Default password hash (cosmo123)
DEFAULT_PASSWORD_HASH = hashlib.sha256(b"cosmo123").hexdigest()
DB_PATH        = Path("cosmo_labels.db")
LOGO_PATH_KEY  = "logo_path"

# ── Color palette: industrial dark theme ──────────────────
CLR_BG         = "#12121F"
CLR_PANEL      = "#1A1A30"
CLR_CARD       = "#0F2744"
CLR_ACCENT     = "#E8312A"
CLR_ACCENT2    = "#3A5BD9"
CLR_TEXT       = "#E8E8E8"
CLR_TEXT_DIM   = "#7A8099"
CLR_INPUT_BG   = "#0A1628"
CLR_INPUT_FG   = "#FFFFFF"
CLR_SUCCESS    = "#00C896"
CLR_WARNING    = "#F4C842"
CLR_BORDER     = "#253058"
CLR_HIGHLIGHT  = "#1E3A5F"
CLR_ROW_ALT    = "#0D2035"

# ── Fonts ─────────────────────────────────────────────────
FONT_TITLE     = ("Segoe UI", 18, "bold")
FONT_SUBTITLE  = ("Segoe UI", 11, "bold")
FONT_BODY      = ("Segoe UI", 10)
FONT_SMALL     = ("Segoe UI", 9)
FONT_MONO      = ("Consolas", 9)
FONT_LABEL_HDR = ("Segoe UI", 13, "bold")



# ─────────────────────────────────────────────────────────
#  LICENSE / KILL-SWITCH  (GitHub JSON check at startup)
# ─────────────────────────────────────────────────────────
LICENSE_URL     = "https://raw.githubusercontent.com/synix-code/Synix-payroll-management/main/status.json"
LICENSE_TIMEOUT = 6   # seconds


def fetch_license() -> dict:
    """
    Fetch license status from GitHub.

    Returns
    -------
    {"ok": True,  "enabled": True/False, "message": str}
    {"ok": False, "reason": "no_internet", "detail": str}
    """
    try:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE
        req = urllib.request.Request(
            LICENSE_URL,
            headers={"User-Agent": "CosmoLabelApp/2.0"},
        )
        with urllib.request.urlopen(req, timeout=LICENSE_TIMEOUT, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "ok":      True,
                "enabled": bool(data.get("enabled", True)),
                "message": str(data.get("message", "")),
            }
    except urllib.error.URLError as e:
        return {"ok": False, "reason": "no_internet", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "reason": "error", "detail": str(e)}


def show_license_check_window() -> bool:
    """
    Fetch license first (blocking), then show UI only if blocked/no-internet.
    Returns True if app should proceed, False if it should exit.
    """
    # ── Step 1: show "checking" splash ───────────────────
    splash = tk.Tk()
    splash.title(APP_TITLE)
    splash.configure(bg=CLR_BG)
    splash.resizable(False, False)
    splash.geometry("440x220")
    splash.update_idletasks()
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"440x220+{(sw-440)//2}+{(sh-220)//2}")
    tk.Frame(splash, bg=CLR_CARD, height=6).pack(fill="x")
    tk.Label(splash, text="⏳", font=("Segoe UI", 32),
             bg=CLR_BG, fg=CLR_TEXT).pack(pady=(24, 4))
    tk.Label(splash, text="Verifying License…",
             font=("Segoe UI", 15, "bold"),
             bg=CLR_BG, fg=CLR_TEXT).pack()
    tk.Label(splash, text="Please wait, connecting to server.",
             font=("Segoe UI", 10),
             bg=CLR_BG, fg=CLR_TEXT_DIM).pack(pady=(8, 0))
    splash.update()

    # ── Step 2: fetch license (blocking, in main thread) ─
    res = fetch_license()
    splash.destroy()

    # ── Step 3: if OK → return True immediately ──────────
    if res["ok"] and res["enabled"]:
        return True

    # ── Step 4: show error window ─────────────────────────
    result = {"value": False}
    root = tk.Tk()
    root.title(APP_TITLE)
    root.configure(bg=CLR_BG)
    root.resizable(False, False)
    root.geometry("440x280")
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"440x280+{(sw-440)//2}+{(sh-280)//2}")

    tk.Frame(root, bg=CLR_CARD, height=6).pack(fill="x")

    if not res["ok"]:
        icon, title, msg, clr = "🌐", "No Internet Connection",             "Could not connect to the license server.\nPlease connect to the internet and retry.",             CLR_WARNING
    else:
        icon, title, msg, clr = "🚫", "Access Blocked",             res.get("message") or "This application has been disabled by the administrator.",             CLR_ACCENT

    tk.Label(root, text=icon, font=("Segoe UI", 32),
             bg=CLR_BG, fg=CLR_TEXT).pack(pady=(20, 4))
    tk.Label(root, text=title, font=("Segoe UI", 15, "bold"),
             bg=CLR_BG, fg=clr, wraplength=380).pack()
    tk.Label(root, text=msg, font=("Segoe UI", 10),
             bg=CLR_BG, fg=CLR_TEXT_DIM, wraplength=380,
             justify="center").pack(pady=(8, 0))

    btn_frame = tk.Frame(root, bg=CLR_BG)
    btn_frame.pack(pady=20)

    def _retry():
        root.destroy()
        result["value"] = show_license_check_window()

    if not res["ok"]:
        # No internet — show Retry + Exit
        row = tk.Frame(btn_frame, bg=CLR_BG)
        row.pack()
        tk.Button(row, text="🔄  Retry",
                  font=("Segoe UI", 11, "bold"),
                  bg=CLR_ACCENT2, fg="white", relief="flat",
                  padx=16, pady=8, cursor="hand2",
                  command=_retry).pack(side="left", padx=8)
        tk.Button(row, text="  Exit  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  padx=16, pady=8, cursor="hand2",
                  command=root.destroy).pack(side="left", padx=8)
    else:
        # Disabled — Exit only
        tk.Button(btn_frame, text="  Exit  ",
                  font=("Segoe UI", 11, "bold"),
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  padx=20, pady=8, cursor="hand2",
                  command=root.destroy).pack()

    root.mainloop()
    return result["value"]

# ─────────────────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────────────────
class Database:
    """All SQLite persistence logic in one place."""

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        """Create/upgrade tables — safe to call on every startup."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS labels (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT    NOT NULL,
                product_code  TEXT    NOT NULL,
                part_size     TEXT    NOT NULL,
                part_qty      TEXT    NOT NULL,
                material      TEXT    NOT NULL,
                qr_text       TEXT    NOT NULL,
                code_type     TEXT    NOT NULL DEFAULT 'qr',
                inv_sign_type TEXT    NOT NULL DEFAULT 'text',
                inv_sign_data TEXT,
                logo_path     TEXT,
                copies        INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    NOT NULL,
                updated_at    TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Add code_type column if upgrading from v1
        try:
            self.conn.execute("ALTER TABLE labels ADD COLUMN code_type TEXT DEFAULT 'qr'")
        except Exception:
            pass
        self.conn.commit()

    # ── CRUD ──────────────────────────────────────────────
    def save_label(self, data: dict) -> int:
        now = datetime.now().isoformat()
        cur = self.conn.execute("""
            INSERT INTO labels
              (customer_name, product_code, part_size, part_qty,
               material, qr_text, code_type, inv_sign_type,
               inv_sign_data, logo_path, copies, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["customer_name"], data["product_code"],
            data["part_size"],     data["part_qty"],
            data["material"],      data["qr_text"],
            data.get("code_type", "qr"),
            data.get("inv_sign_type", "text"),
            data.get("inv_sign_data", ""),
            data.get("logo_path", ""),
            data.get("copies", 1),
            now, now,
        ))
        self.conn.commit()
        return cur.lastrowid

    def update_label(self, label_id: int, data: dict):
        now = datetime.now().isoformat()
        self.conn.execute("""
            UPDATE labels SET
              customer_name=?, product_code=?, part_size=?, part_qty=?,
              material=?, qr_text=?, code_type=?, inv_sign_type=?,
              inv_sign_data=?, logo_path=?, copies=?, updated_at=?
            WHERE id=?
        """, (
            data["customer_name"], data["product_code"],
            data["part_size"],     data["part_qty"],
            data["material"],      data["qr_text"],
            data.get("code_type", "qr"),
            data.get("inv_sign_type", "text"),
            data.get("inv_sign_data", ""),
            data.get("logo_path", ""),
            data.get("copies", 1),
            now, label_id,
        ))
        self.conn.commit()

    def delete_label(self, label_id: int):
        self.conn.execute("DELETE FROM labels WHERE id=?", (label_id,))
        self.conn.commit()

    def get_all_labels(self) -> list:
        return self.conn.execute(
            "SELECT * FROM labels ORDER BY updated_at DESC"
        ).fetchall()

    def get_label(self, label_id: int):
        return self.conn.execute(
            "SELECT * FROM labels WHERE id=?", (label_id,)
        ).fetchone()

    def search_labels(self, query: str) -> list:
        q = f"%{query}%"
        return self.conn.execute(
            """SELECT * FROM labels
               WHERE customer_name LIKE ? OR product_code LIKE ?
                  OR material LIKE ? OR part_size LIKE ?
               ORDER BY updated_at DESC""",
            (q, q, q, q)
        ).fetchall()

    # ── Settings ──────────────────────────────────────────
    def get_setting(self, key: str, default=None) -> str:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, value)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


# ─────────────────────────────────────────────────────────
#  LABEL RENDERER  (PIL/Pillow based)
# ─────────────────────────────────────────────────────────
class LabelRenderer:
    """
    Renders the complete 4×4 label as a PIL Image.
    FIXED: Proper 4x4 scaling and pure white background for TSC TE244.
    """

    def __init__(self, dpi: int = DPI_PREVIEW):
        self.dpi = dpi
        # Strictly 4x4 inch scaling
        self.w   = int(4 * dpi)
        self.h   = int(4 * dpi)
        self._load_fonts()

    def _load_fonts(self):
        ppi = self.dpi
        def px(pt): return max(10, int(pt * ppi / 72))

        # Fonts setup (Arial family best for thermal)
        def get_font(name_list, pt, is_bold=False):
            for name in name_list:
                try: return ImageFont.truetype(name, px(pt))
                except: pass
            return ImageFont.load_default()

        bold_fonts = ["arialbd.ttf", "Arial_Bold.ttf", "DejaVuSans-Bold.ttf"]
        reg_fonts  = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]

        self.f_company = get_font(bold_fonts, 14)
        self.f_label   = get_font(bold_fonts, 11)
        self.f_value   = get_font(reg_fonts, 11)
        self.f_sign    = get_font(reg_fonts, 10)
        self.f_small   = get_font(reg_fonts, 8)
        self.f_tiny    = get_font(reg_fonts, 7)

    def _make_qr(self, text: str, size: int) -> Image.Image:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=max(2, size // 25),
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        # Force Black on White
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        return img.resize((size, size), Image.LANCZOS)

    def _make_barcode(self, text: str, width: int, height: int) -> Image.Image:
        if BARCODE_AVAILABLE:
            try:
                buf = io.BytesIO()
                code = barcode.get("code128", text, writer=ImageWriter())
                code.write(buf, options={
                    "module_height": height / (self.dpi / 25.4),
                    "quiet_zone": 2,
                    "write_text": True,
                })
                buf.seek(0)
                img = Image.open(buf).convert("RGB")
                return img.resize((width, height), Image.LANCZOS)
            except: pass
        return self._make_qr(text, min(width, height))

    def render(self, data: dict) -> Image.Image:
        W, H, DPI = self.w, self.h, self.dpi
        def ip(inches): return int(inches * DPI)
        def mp(mm):     return int(mm * DPI / 25.4)

        # 1. PURE WHITE BACKGROUND
        img  = Image.new("RGB", (W, H), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Padding aur Layout logic
        PAD = ip(0.1) 
        y = PAD

        # 2. Outer border
        bw = max(2, mp(1))

        # Extra safe margin taaki border cut na ho
        MARGIN = mp(2)

        draw.rectangle(
            [MARGIN, MARGIN, W - MARGIN - 1, H - MARGIN - 1],
            outline=(0, 0, 0),
            width=bw
        )

        y += mp(2)

        # 3. Logo
        LOGO_H = ip(0.45)
        lp = data.get("logo_path", "")
        if lp and os.path.isfile(lp):
            try:
                logo_img = Image.open(lp).convert("RGBA")
                ratio = LOGO_H / logo_img.height
                logo_w = int(logo_img.width * ratio)
                logo_img = logo_img.resize((logo_w, LOGO_H), Image.LANCZOS)
                # Logo ko white par paste karna zaroori hai
                bg = Image.new("RGB", (logo_w, LOGO_H), (255, 255, 255))
                mask = logo_img.split()[3] if logo_img.mode == "RGBA" else None
                bg.paste(logo_img, mask=mask)
                img.paste(bg, ((W - logo_w) // 2, y))
                y += LOGO_H + mp(2)
            except: pass

        # Dividers
        LINE_W = max(2, mp(0.5))
        draw.line([(PAD+mp(2), y), (W-PAD-mp(2), y)], fill=(0, 0, 0), width=LINE_W)
        y += mp(2)

        # 4. Company Name
        bbox = draw.textbbox((0, 0), COMPANY_NAME, font=self.f_company)
        draw.text(((W - (bbox[2]-bbox[0])) // 2, y), COMPANY_NAME, fill=(0, 0, 0), font=self.f_company)
        y += (bbox[3]-bbox[1]) + mp(3)
        draw.line([(PAD+mp(2), y), (W-PAD-mp(2), y)], fill=(0, 0, 0), width=LINE_W)
        y += mp(2)

        # 5. Data Fields Table
        TBL_X = PAD + mp(2)
        TBL_W = W - 2 * PAD - mp(4)
        COL_W = int(TBL_W * 0.38)
        VAL_X = TBL_X + COL_W
        ROW_H = ip(0.28) # Clean row height for 4x4

        fields = [
            ("Customer Name", data.get("customer_name", "")),
            ("Product Code",  data.get("product_code",  "")),
            ("Part Size",     data.get("part_size",     "")),
            ("Part Qty",      data.get("part_qty",      "")),
            ("Material",      data.get("material",      "")),
        ]

        for i, (lbl, val) in enumerate(fields):
            # Subtle alternate rows for readability
            row_bg = (250, 250, 250) if i % 2 == 0 else (255, 255, 255)
            draw.rectangle([TBL_X, y, TBL_X + TBL_W, y + ROW_H], fill=row_bg, outline=(200, 200, 200))
            draw.line([(VAL_X, y), (VAL_X, y + ROW_H)], fill=(200, 200, 200), width=1)
            
            draw.text((TBL_X + mp(3), y + mp(2)), lbl, fill=(0, 0, 0), font=self.f_label)
            # Value Truncation logic
            val_str = str(val)
            draw.text((VAL_X + mp(3), y + mp(2)), val_str[:30], fill=(0, 0, 0), font=self.f_value)
            y += ROW_H

        y += mp(4)

        # 6. QR/Barcode Section
        qr_text = data.get("qr_text", "COSMO").strip()
        code_type = data.get("code_type", "qr")
        
        if code_type == "barcode":
            bc_h, bc_w = ip(0.5), TBL_W
            img.paste(self._make_barcode(qr_text, bc_w, bc_h), (TBL_X, y))
            y += bc_h + mp(5)
        else:
            qr_size = ip(1.1) # Optimized for 4x4
            img.paste(self._make_qr(qr_text, qr_size), ((W - qr_size) // 2, y))
            y += qr_size + mp(5)

        # 7. Investigator Sign (FIXED: Ab input text print hoga)
        draw.line([(PAD + mp(2), y), (W - PAD - mp(2), y)], fill=(0, 0, 0), width=1)
        y += mp(2)

        # "Investigator Sign:" Label draw karein
        draw.text((TBL_X, y), "Investigator Sign:", fill=(0, 0, 0), font=self.f_label)

        # UI se data uthayein
        sign_type = data.get("inv_sign_type", "text")
        sign_data = data.get("inv_sign_data", "")

        # Value kahan print karni hai (VAL_X par, jahan table ki values aati hain)
        sign_val_x = VAL_X + mp(2)

        if sign_type == "image" and sign_data and os.path.isfile(sign_data):
            try:
                simg = Image.open(sign_data).convert("RGBA")
                s_h = mp(10) # Sign image ki height
                s_ratio = s_h / simg.height
                s_w = int(simg.width * s_ratio)
                simg = simg.resize((s_w, s_h), Image.LANCZOS)
                
                s_bg = Image.new("RGB", (s_w, s_h), (255, 255, 255))
                s_mask = simg.split()[3] if simg.mode == "RGBA" else None
                s_bg.paste(simg, mask=s_mask)
                img.paste(s_bg, (sign_val_x, y - mp(2)))
            except:
                draw.text((sign_val_x, y), "[Image Error]", fill=(0,0,0), font=self.f_tiny)
        elif sign_data:
            # AGAR TEXT HAI TOH YAHAN PRINT HOGA
            draw.text((sign_val_x, y), str(sign_data), fill=(0, 0, 0), font=self.f_value)
        else:
            # Agar kuch nahi hai toh khali line
            draw.line([(sign_val_x, y + ip(0.12)), (W - PAD - mp(4), y + ip(0.12))], fill=(0, 0, 0), width=1)

        # 8. Footer (Always at bottom)
        footer_y = H - mp(6)
        footer_txt = f"{datetime.now().strftime('%d-%b-%Y')} | {COMPANY_NAME}"
        # Footer text ko center karne ke liye
        f_bbox = draw.textbbox((0, 0), footer_txt, font=self.f_tiny)
        draw.text(((W - (f_bbox[2]-f_bbox[0])) // 2, footer_y), footer_txt, fill=(120, 120, 120), font=self.f_tiny)

        return img

    def render_to_bytes(self, data: dict, fmt: str = "PNG") -> bytes:
        img = self.render(data)
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()


# ─────────────────────────────────────────────────────────
#  TSPL PRINTER
# ─────────────────────────────────────────────────────────
class TSPLPrinter:
    """
    FIXED: Generates TSPL/TSPL2 commands for TSC TE244.
    Fixes: 4x4 inch size restriction & White Background logic.
    """

    PRINTER_NAME = "TSC TE244"

    @staticmethod
    def _find_printer() -> str:
        """Printer auto-detect logic (Same as before)."""
        try:
            import win32print
            printers = [p[2] for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )]
            for p in printers:
                pu = p.upper()
                if "TSC" in pu or "TE244" in pu:
                    return p
        except Exception:
            pass
        return TSPLPrinter.PRINTER_NAME

    @staticmethod
    def build_tspl(data: dict, copies: int = 1) -> bytes:
        """
        Builds the binary TSPL packet with fixed Color Inversion for White BG.
        """
        # 203 DPI settings for 4x4 inch
        w_dot = 812  
        h_dot = 812  

        # 1. Render at high resolution (203 DPI)
        renderer  = LabelRenderer(dpi=203)
        label_pil = renderer.render(data)
        
        # 2. Convert to 1-bit monochrome
        # PIL '1' mode: 0 is Black, 1 is White.
        label_1bt = label_pil.convert("1") 

        row_bytes = (w_dot + 7) // 8
        raw_bytes = label_1bt.tobytes() 
        
        rows = []
        for r in range(h_dot):
            start = r * row_bytes
            row = list(raw_bytes[start: start + row_bytes])
            
            # Padding check
            if len(row) < row_bytes:
                row += [0xFF] * (row_bytes - len(row))
            
            # --- CRITICAL FIX FOR BLACK BG ---
            # Hum XOR (b ^ 0xFF) isliye kar rahe hain kyunki:
            # PIL: 255 (White) -> XOR -> 0 (TSC White)
            # PIL: 0 (Black) -> XOR -> 255 (TSC Black)
            # Agar abhi bhi ulta aaye, toh niche wali line ko 'bytes(row)' kar dena.
            rows.append(bytes(row))

        # 3. TSPL2 HEADER - Force White Background through CLS
        header = (
            f"SIZE 4, 4\r\n"         # Explicit size
            f"GAP 0.12, 0\r\n"       
            f"DIRECTION 1,0\r\n"     
            f"REFERENCE 0,0\r\n"
            f"CLS\r\n"               # CLS command buffer clear karke white karta hai
        ).encode("ascii")

        # BITMAP command (mode 0 for standard)
        bitmap_cmd = f"BITMAP 0,0,{row_bytes},{h_dot},0,".encode("ascii")
        footer = f"\r\nPRINT {copies},1\r\n".encode("ascii")

        return header + bitmap_cmd + b"".join(rows) + footer

    @staticmethod
    def print_label(data: dict, copies: int = 1) -> bool:
        """Sends data to printer."""
        printer_name = TSPLPrinter._find_printer()
        tspl_packet = TSPLPrinter.build_tspl(data, copies)

        # Method 1: win32print (RAW Spooling)
        try:
            import win32print
            hp = win32print.OpenPrinter(printer_name)
            try:
                job_name = f"Cosmo-{datetime.now().strftime('%H%M%S')}"
                win32print.StartDocPrinter(hp, 1, (job_name, None, "RAW"))
                win32print.StartPagePrinter(hp)
                win32print.WritePrinter(hp, tspl_packet)
                win32print.EndPagePrinter(hp)
                win32print.EndDocPrinter(hp)
            finally:
                win32print.ClosePrinter(hp)
            return True
        except Exception:
            # Method 2: CMD Fallback
            tmp = tempfile.NamedTemporaryFile(suffix=".prn", delete=False, mode="wb")
            tmp.write(tspl_packet)
            tmp.close()
            try:
                subprocess.run(["cmd", "/c", f'copy /b "{tmp.name}" "\\\\localhost\\{printer_name}"'], 
                               shell=True, capture_output=True)
                return True
            finally:
                if os.path.exists(tmp.name): os.unlink(tmp.name)


# ─────────────────────────────────────────────────────────
#  TOOLTIP HELPER
# ─────────────────────────────────────────────────────────
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text   = text
        self.tip    = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text,
                 bg="#1C1C3A", fg=CLR_WARNING,
                 font=FONT_SMALL, relief="flat",
                 padx=8, pady=4).pack()

    def _hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ─────────────────────────────────────────────────────────
#  PRINT PREVIEW WINDOW
# ─────────────────────────────────────────────────────────
class PreviewWindow(tk.Toplevel):
    """
    Full WYSIWYG 4×4 print preview modal.
    Buttons: Edit | Save PNG | Confirm & Print | Cancel
    """

    def __init__(self, parent, data: dict, on_confirm_print):
        super().__init__(parent)
        self.title("🖨  Print Preview — 4×4 Inch Label")
        self.configure(bg=CLR_BG)
        self.resizable(False, False)
        self.grab_set()

        self.data             = data
        self.on_confirm_print = on_confirm_print
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=CLR_CARD, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  PRINT PREVIEW",
                 font=FONT_TITLE, fg=CLR_ACCENT, bg=CLR_CARD).pack()
        tk.Label(hdr,
                 text="This preview exactly matches the 4×4 inch thermal print output",
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_CARD).pack()

        # Label canvas with drop shadow
        cf = tk.Frame(self, bg=CLR_BG, padx=24, pady=18)
        cf.pack()
        shadow = tk.Frame(cf, bg="#000000", width=PX_W + 8, height=PX_H + 8)
        shadow.pack()
        shadow.pack_propagate(False)
        self.canvas = tk.Canvas(shadow, width=PX_W, height=PX_H,
                                highlightthickness=0, bg="white")
        self.canvas.place(x=3, y=3)
        self._render()

        # Info bar
        info = tk.Frame(self, bg=CLR_PANEL, pady=6)
        info.pack(fill="x")
        copies = self.data.get("copies", 1)
        code_t = self.data.get("code_type", "qr").upper()
        tk.Label(info,
                 text=(f"Size: 4×4 in  |  DPI: {DPI_PRINT}  |  "
                       f"Copies: {copies}  |  Code: {code_t}"),
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_PANEL).pack()

        # Buttons
        bf = tk.Frame(self, bg=CLR_BG, pady=14)
        bf.pack()
        btns = [
            ("✏  Edit",            CLR_ACCENT2,  self._edit),
            ("🖼  Save PNG",        "#2D6A4F",    self._save_png),
            ("🖨  Confirm & Print", CLR_SUCCESS,  self._confirm),
            ("✕  Cancel",          "#555555",    self.destroy),
        ]
        for txt, clr, cmd in btns:
            tk.Button(bf, text=txt, font=FONT_SUBTITLE,
                      bg=clr, fg="white", relief="flat",
                      padx=16, pady=8, cursor="hand2",
                      activebackground=clr, activeforeground="white",
                      command=cmd).pack(side="left", padx=6)

    def _render(self):
        r = LabelRenderer(dpi=DPI_PREVIEW)
        lbl = r.render(self.data)
        self._tk_img = ImageTk.PhotoImage(lbl)
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

    def _edit(self):
        self.destroy()

    def _save_png(self):
        path = filedialog.asksaveasfilename(
            title="Save Label as PNG",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if path:
            try:
                r = LabelRenderer(dpi=DPI_PRINT)
                img = r.render(self.data)
                img.save(path, "PNG")
                messagebox.showinfo("Saved", f"High-res label saved:\n{path}",
                                    parent=self)
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=self)

    def _confirm(self):
        self.destroy()
        self.on_confirm_print()


# ─────────────────────────────────────────────────────────
#  HISTORY WINDOW
# ─────────────────────────────────────────────────────────
class HistoryWindow(tk.Toplevel):
    """Browse, search, load, and delete saved label records."""

    def __init__(self, parent, db: Database, on_load):
        super().__init__(parent)
        self.title("📂  Saved Labels — History")
        self.configure(bg=CLR_BG)
        self.geometry("900x520")
        self.grab_set()
        self.db      = db
        self.on_load = on_load
        self._row_ids = []
        self._build_ui()
        self._load_all()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w,  h  = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=CLR_CARD, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📂  LABEL HISTORY",
                 font=FONT_TITLE, fg=CLR_ACCENT, bg=CLR_CARD).pack()

        # Search bar
        sf = tk.Frame(self, bg=CLR_BG, padx=14, pady=8)
        sf.pack(fill="x")
        tk.Label(sf, text="🔍 Search:", font=FONT_BODY,
                 fg=CLR_TEXT, bg=CLR_BG).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        se = tk.Entry(sf, textvariable=self.search_var,
                      font=FONT_BODY, bg=CLR_INPUT_BG, fg=CLR_INPUT_FG,
                      insertbackground=CLR_ACCENT, relief="flat",
                      highlightthickness=1, highlightbackground=CLR_BORDER,
                      highlightcolor=CLR_ACCENT)
        se.pack(side="left", fill="x", expand=True, ipady=5, padx=6)
        tk.Button(sf, text="Clear", font=FONT_SMALL,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat",
                  padx=8, pady=4, cursor="hand2",
                  command=lambda: self.search_var.set("")
                  ).pack(side="left")

        # Treeview
        tf = tk.Frame(self, bg=CLR_BG)
        tf.pack(fill="both", expand=True, padx=14)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("H.Treeview",
                        background=CLR_INPUT_BG,
                        foreground=CLR_TEXT,
                        rowheight=30,
                        fieldbackground=CLR_INPUT_BG,
                        font=FONT_BODY,
                        borderwidth=0)
        style.configure("H.Treeview.Heading",
                        background=CLR_CARD,
                        foreground=CLR_ACCENT,
                        font=FONT_SUBTITLE,
                        relief="flat")
        style.map("H.Treeview",
                  background=[("selected", CLR_HIGHLIGHT)],
                  foreground=[("selected", CLR_TEXT)])

        cols = ("#", "Customer", "Product Code", "Part Size",
                "Qty", "Material", "Code", "Copies", "Saved")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 style="H.Treeview")
        widths = [38, 130, 110, 80, 60, 100, 55, 55, 130]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(tf, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _: self._load_selected())

        # Buttons
        bf = tk.Frame(self, bg=CLR_BG, pady=10)
        bf.pack()
        btn_cfg = [
            ("📥  Load Selected",   CLR_SUCCESS, self._load_selected),
            ("🗑  Delete Selected", CLR_ACCENT,  self._delete_selected),
            ("🔄  Refresh",         CLR_CARD,    self._load_all),
            ("✕  Close",           "#555555",   self.destroy),
        ]
        for txt, clr, cmd in btn_cfg:
            tk.Button(bf, text=txt, font=FONT_BODY,
                      bg=clr, fg="white", relief="flat",
                      padx=12, pady=6, cursor="hand2",
                      command=cmd).pack(side="left", padx=6)

        # Count label
        self.count_var = tk.StringVar()
        tk.Label(self, textvariable=self.count_var,
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_BG
                 ).pack(pady=(0, 6))

    def _populate(self, records):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._row_ids.clear()
        for rec in records:
            dt = rec["updated_at"][:16].replace("T", " ")
            code_t = rec["code_type"].upper() if rec["code_type"] else "QR"
            self.tree.insert("", "end", values=(
                rec["id"], rec["customer_name"], rec["product_code"],
                rec["part_size"], rec["part_qty"], rec["material"],
                code_t, rec["copies"], dt,
            ))
            self._row_ids.append(rec["id"])
        self.count_var.set(f"{len(records)} record(s) found")

    def _load_all(self):
        self._populate(self.db.get_all_labels())

    def _on_search(self):
        q = self.search_var.get().strip()
        if q:
            self._populate(self.db.search_labels(q))
        else:
            self._load_all()

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select a record first.",
                                   parent=self)
            return None
        return self._row_ids[self.tree.index(sel[0])]

    def _load_selected(self):
        db_id = self._selected_id()
        if db_id is None:
            return
        rec = self.db.get_label(db_id)
        self.on_load(dict(rec), db_id)
        self.destroy()

    def _delete_selected(self):
        db_id = self._selected_id()
        if db_id is None:
            return
        if messagebox.askyesno("Confirm Delete",
                               f"Delete record #{db_id}?\nThis cannot be undone.",
                               parent=self):
            self.db.delete_label(db_id)
            self._on_search()


# ─────────────────────────────────────────────────────────
#  STYLED ENTRY WIDGET
# ─────────────────────────────────────────────────────────
class PlaceholderEntry(tk.Entry):
    """
    Entry widget with placeholder text that disappears on focus.
    """
    def __init__(self, master, placeholder="", **kwargs):
        self._ph   = placeholder
        self._real = False
        super().__init__(master, **kwargs)
        self.config(fg=CLR_TEXT_DIM)
        self.insert(0, placeholder)
        self.bind("<FocusIn>",  self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, _=None):
        if not self._real:
            self.delete(0, "end")
            self.config(fg=CLR_INPUT_FG)
            self._real = True

    def _on_focus_out(self, _=None):
        if not self.get():
            self.insert(0, self._ph)
            self.config(fg=CLR_TEXT_DIM)
            self._real = False

    def get_value(self) -> str:
        """Return actual value, empty string if only placeholder."""
        return self.get() if self._real else ""

    def set_value(self, val: str):
        self.delete(0, "end")
        if val:
            self.insert(0, val)
            self.config(fg=CLR_INPUT_FG)
            self._real = True
        else:
            self.insert(0, self._ph)
            self.config(fg=CLR_TEXT_DIM)
            self._real = False


# ─────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────
class CosmoLabelApp(tk.Tk):
    """
    Main application window.
    Layout:
        Top      → header + toolbar
        Left     → logo, form, copies, action buttons
        Right    → live mini-preview
        Bottom   → status bar
    """

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=CLR_BG)
        self.resizable(True, True)
        self.minsize(980, 820)
        self.geometry("1200x850")
        self.state("zoomed")

        # State
        self.db            = Database()
        self.logo_path     = tk.StringVar(
            value=self.db.get_setting(LOGO_PATH_KEY, ""))
        self.copies_var    = tk.IntVar(value=1)
        self.inv_sign_type = tk.StringVar(value="text")
        self.inv_sign_img  = tk.StringVar(value="")
        self.code_type     = tk.StringVar(value="qr")
        self.current_id    = None
        self._preview_job  = None   # debounce timer for live preview
        self._logo_tk_img  = None

        # Password
        self.password_hash = self.db.get_setting(
            "print_password_hash", DEFAULT_PASSWORD_HASH)

        self._build_menu()
        self._build_ui()
        self._apply_style()
        self._center()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(300, self._refresh_mini_preview)

    # ─────────────────────────────────────────────────────
    #  Styling
    # ─────────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TScrollbar",
                        background=CLR_CARD,
                        troughcolor=CLR_BG,
                        arrowcolor=CLR_ACCENT)

    # ─────────────────────────────────────────────────────
    #  Menu
    # ─────────────────────────────────────────────────────
    def _build_menu(self):
        m_kw = dict(bg=CLR_PANEL, fg=CLR_TEXT,
                    activebackground=CLR_HIGHLIGHT,
                    activeforeground=CLR_ACCENT,
                    tearoff=0)
        menubar = tk.Menu(self, **m_kw)
        self.config(menu=menubar)

        file_m = tk.Menu(menubar, **m_kw)
        file_m.add_command(label="🆕  New Label",    command=self._clear_form)
        file_m.add_command(label="💾  Save Entry",   command=self._save_entry)
        file_m.add_command(label="📂  Open History", command=self._open_history)
        file_m.add_separator()
        file_m.add_command(label="📤  Export TSPL",  command=self._export_tspl)
        file_m.add_command(label="🖼  Export PNG",   command=self._export_png)
        file_m.add_separator()
        file_m.add_command(label="Exit",             command=self._on_close)
        menubar.add_cascade(label="File", menu=file_m)

        set_m = tk.Menu(menubar, **m_kw)
        set_m.add_command(label="🔑  Change Print Password",
                          command=self._change_password)
        set_m.add_command(label="🖨  Set Printer Name",
                          command=self._set_printer_name)
        menubar.add_cascade(label="Settings", menu=set_m)

        hlp_m = tk.Menu(menubar, **m_kw)
        hlp_m.add_command(label="ℹ  About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=hlp_m)

    # ─────────────────────────────────────────────────────
    #  UI Layout
    # ─────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()

        body = tk.Frame(self, bg=CLR_BG)
        body.pack(fill="both", expand=True, padx=16, pady=(4, 70))

        # ── Right column (mini preview) — fixed, no scroll needed ──
        right = tk.Frame(body, bg=CLR_BG, padx=10)
        right.pack(side="right", fill="y")

        # ── Left column — scrollable canvas wrapper ──────────────
        left_outer = tk.Frame(body, bg=CLR_BG)
        left_outer.pack(side="left", fill="both", expand=True)

        # Scrollbar
        left_scroll = ttk.Scrollbar(left_outer, orient="vertical")
        left_scroll.pack(side="right", fill="y")

        # Canvas acts as the scrollable viewport
        left_canvas = tk.Canvas(
            left_outer, bg=CLR_BG,
            yscrollcommand=left_scroll.set,
            highlightthickness=0
        )
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.config(command=left_canvas.yview)

        # Inner frame that holds all form widgets
        left = tk.Frame(left_canvas, bg=CLR_BG)
        left_canvas_window = left_canvas.create_window(
            (0, 0), window=left, anchor="nw"
        )

        # Resize inner frame width to match canvas width
        def _on_canvas_configure(event):
            left_canvas.itemconfig(left_canvas_window, width=event.width)
        left_canvas.bind("<Configure>", _on_canvas_configure)

        # Update scroll region whenever inner frame size changes
        def _on_frame_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        left.bind("<Configure>", _on_frame_configure)

        # Mouse-wheel scrolling (Windows + Linux)
        def _on_mousewheel(event):
            if event.num == 4:          # Linux scroll up
                left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:        # Linux scroll down
                left_canvas.yview_scroll(1, "units")
            else:                       # Windows / macOS
                left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left_canvas.bind("<MouseWheel>", _on_mousewheel)
        left_canvas.bind("<Button-4>",   _on_mousewheel)
        left_canvas.bind("<Button-5>",   _on_mousewheel)
        left.bind("<MouseWheel>", _on_mousewheel)
        left.bind("<Button-4>",   _on_mousewheel)
        left.bind("<Button-5>",   _on_mousewheel)

        # Bind mouse-wheel when pointer enters/leaves canvas area
        def _bind_mousewheel(event):
            left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            left_canvas.bind_all("<Button-4>",   _on_mousewheel)
            left_canvas.bind_all("<Button-5>",   _on_mousewheel)
        def _unbind_mousewheel(event):
            left_canvas.unbind_all("<MouseWheel>")
            left_canvas.unbind_all("<Button-4>")
            left_canvas.unbind_all("<Button-5>")
        left_canvas.bind("<Enter>", _bind_mousewheel)
        left_canvas.bind("<Leave>", _unbind_mousewheel)

        self._build_logo_section(left)
        self._build_form(left)
        self._build_copies_section(left)
        self._build_action_buttons(left)
        self._build_mini_preview(right)
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=CLR_CARD, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  COSMO HYDRAULIC INDUSTRIES",
                 font=("Segoe UI", 20, "bold"),
                 fg=CLR_ACCENT, bg=CLR_CARD).pack()
        tk.Label(hdr,
                 text="TSC TE244 Thermal Label Printer   •   Fixed 4×4 Inch",
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_CARD).pack()

    # ── Logo Section ──────────────────────────────────────
    def _build_logo_section(self, parent):
        card = self._card(parent, "🖼  Company Logo")
        row  = tk.Frame(card, bg=CLR_PANEL)
        row.pack(fill="x", pady=4)

        self.logo_lbl = tk.Label(
            row, text="No logo", bg=CLR_INPUT_BG, fg=CLR_TEXT_DIM,
            font=FONT_SMALL, width=16, height=4, relief="flat"
        )
        self.logo_lbl.pack(side="left", padx=(0, 10))

        bc = tk.Frame(row, bg=CLR_PANEL)
        bc.pack(side="left", fill="y")
        tk.Button(bc, text="📁 Upload Logo", font=FONT_SMALL,
                  bg=CLR_ACCENT2, fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  command=self._upload_logo).pack(pady=2)
        tk.Button(bc, text="✕ Remove Logo", font=FONT_SMALL,
                  bg="#555555", fg="white", relief="flat",
                  padx=10, pady=5, cursor="hand2",
                  command=self._remove_logo).pack(pady=2)

        if self.logo_path.get():
            self._refresh_logo_thumb()

    # ── Main Form ─────────────────────────────────────────
    def _build_form(self, parent):
        card = self._card(parent, "📝  Label Fields")

        # Main fields
        fields_def = [
            ("Customer Name", "customer_name", "e.g. ABC Pvt Ltd"),
            ("Product Code",  "product_code",  "e.g. CHI-2024-001"),
            ("Part Size",     "part_size",      "e.g. 50mm × 30mm"),
            ("Part Qty",      "part_qty",       "e.g. 500 pcs"),
            ("Material",      "material",       "e.g. Stainless Steel 304"),
        ]
        self.entries = {}   # key → PlaceholderEntry

        for label, key, ph in fields_def:
            row = tk.Frame(card, bg=CLR_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=FONT_BODY,
                     fg=CLR_TEXT, bg=CLR_PANEL,
                     width=16, anchor="w").pack(side="left")
            ent = PlaceholderEntry(
                row, placeholder=ph,
                font=FONT_BODY, bg=CLR_INPUT_BG, fg=CLR_INPUT_FG,
                insertbackground=CLR_ACCENT, relief="flat", bd=0,
                highlightthickness=1,
                highlightbackground=CLR_BORDER,
                highlightcolor=CLR_ACCENT
            )
            ent.pack(side="left", fill="x", expand=True, ipady=6, padx=4)
            ent.bind("<KeyRelease>", self._schedule_preview_refresh)
            self.entries[key] = ent

        # Separator
        tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", pady=6)

        # QR / Code section
        qr_row = tk.Frame(card, bg=CLR_PANEL)
        qr_row.pack(fill="x", pady=2)
        tk.Label(qr_row, text="Code Text:", font=FONT_BODY,
                 fg=CLR_ACCENT, bg=CLR_PANEL,
                 width=16, anchor="w").pack(side="left")
        self.qr_entry = PlaceholderEntry(
            qr_row, placeholder="Text to encode in QR/Barcode",
            font=FONT_BODY, bg=CLR_INPUT_BG, fg=CLR_INPUT_FG,
            insertbackground=CLR_ACCENT, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=CLR_BORDER,
            highlightcolor=CLR_ACCENT
        )
        self.qr_entry.pack(side="left", fill="x", expand=True,
                           ipady=6, padx=4)
        self.qr_entry.bind("<KeyRelease>", self._schedule_preview_refresh)

        # Code type radio
        ct_row = tk.Frame(card, bg=CLR_PANEL)
        ct_row.pack(fill="x", pady=2)
        tk.Label(ct_row, text="Code Type:", font=FONT_BODY,
                 fg=CLR_TEXT, bg=CLR_PANEL,
                 width=16, anchor="w").pack(side="left")
        for lbl, val in [("QR Code", "qr"), ("Barcode (Code128)", "barcode")]:
            rb = tk.Radiobutton(
                ct_row, text=lbl, variable=self.code_type, value=val,
                bg=CLR_PANEL, fg=CLR_TEXT, selectcolor=CLR_CARD,
                activebackground=CLR_PANEL, font=FONT_SMALL,
                command=self._schedule_preview_refresh
            )
            rb.pack(side="left", padx=(0, 12))
            if val == "barcode" and not BARCODE_AVAILABLE:
                rb.config(state="disabled")
                ToolTip(rb, "Install python-barcode:\n  pip install python-barcode")

        # Separator
        tk.Frame(card, bg=CLR_BORDER, height=1).pack(fill="x", pady=6)

        # Investigator Sign
        sign_row = tk.Frame(card, bg=CLR_PANEL)
        sign_row.pack(fill="x", pady=2)
        tk.Label(sign_row, text="Investigator Sign:", font=FONT_BODY,
                 fg=CLR_TEXT, bg=CLR_PANEL,
                 width=16, anchor="w").pack(side="left")

        inner = tk.Frame(sign_row, bg=CLR_PANEL)
        inner.pack(side="left", fill="x", expand=True)

        for lbl, val in [("Text", "text"), ("Image", "image")]:
            tk.Radiobutton(
                inner, text=lbl, variable=self.inv_sign_type, value=val,
                bg=CLR_PANEL, fg=CLR_TEXT, selectcolor=CLR_CARD,
                activebackground=CLR_PANEL, font=FONT_SMALL,
                command=self._toggle_sign_mode
            ).pack(side="left")

        self.sign_text_var = tk.StringVar()
        self.sign_entry = tk.Entry(
            inner, textvariable=self.sign_text_var,
            font=FONT_BODY, bg=CLR_INPUT_BG, fg=CLR_INPUT_FG,
            insertbackground=CLR_ACCENT, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=CLR_BORDER,
            highlightcolor=CLR_ACCENT
        )
        self.sign_entry.pack(side="left", fill="x", expand=True,
                             ipady=6, padx=(8, 4))
        self.sign_entry.bind("<KeyRelease>", self._schedule_preview_refresh)

        self.sign_img_btn = tk.Button(
            inner, text="📁 Upload Image", font=FONT_SMALL,
            bg=CLR_ACCENT2, fg="white", relief="flat",
            padx=8, pady=3, cursor="hand2",
            command=self._upload_sign_image
        )
        self.sign_img_lbl = tk.Label(
            inner, text="", font=FONT_SMALL, fg=CLR_SUCCESS, bg=CLR_PANEL
        )
        self._toggle_sign_mode()

    # ── Copies Section ────────────────────────────────────
    def _build_copies_section(self, parent):
        card = self._card(parent, "📄  Number of Copies")
        row  = tk.Frame(card, bg=CLR_PANEL)
        row.pack()

        tk.Button(row, text=" − ", font=("Segoe UI", 14, "bold"),
                  bg=CLR_ACCENT, fg="white", relief="flat",
                  padx=12, cursor="hand2",
                  command=self._dec_copies).pack(side="left", padx=4)

        # Copies spinbox (direct entry allowed)
        self.copies_spin = tk.Spinbox(
            row, from_=1, to=999, textvariable=self.copies_var,
            font=("Segoe UI", 18, "bold"),
            bg=CLR_INPUT_BG, fg=CLR_ACCENT,
            buttonbackground=CLR_CARD,
            insertbackground=CLR_ACCENT,
            relief="flat", bd=0, width=4,
            highlightthickness=1,
            highlightbackground=CLR_BORDER,
            highlightcolor=CLR_ACCENT,
            justify="center",
            command=self._on_copies_change
        )
        self.copies_spin.pack(side="left", padx=10, ipady=4)

        tk.Button(row, text=" + ", font=("Segoe UI", 14, "bold"),
                  bg=CLR_SUCCESS, fg="white", relief="flat",
                  padx=12, cursor="hand2",
                  command=self._inc_copies).pack(side="left", padx=4)

        tk.Label(card, text="copies will be printed",
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_PANEL).pack()

    # ── Action Buttons ────────────────────────────────────
    def _build_action_buttons(self, parent):
        row = tk.Frame(parent, bg=CLR_BG, pady=8)
        row.pack(fill="x")
        btns = [
            ("🔍 Preview",     CLR_ACCENT2,  self._show_preview),
            ("🖨  Print",      CLR_ACCENT,   self._on_print),
            ("💾 Save",        CLR_CARD,     self._save_entry),
            ("📂 History",     CLR_CARD,     self._open_history),
            ("🗑  Clear",      "#555555",    self._clear_form),
        ]
        for txt, clr, cmd in btns:
            tk.Button(row, text=txt, font=FONT_BODY,
                      bg=clr, fg="white", relief="flat",
                      padx=12, pady=8, cursor="hand2",
                      activebackground=clr, activeforeground="white",
                      command=cmd).pack(side="left", padx=4)

    # ── Mini Preview ──────────────────────────────────────
    def _build_mini_preview(self, parent):
        tk.Label(parent, text="Live Preview",
                 font=FONT_SUBTITLE, fg=CLR_TEXT_DIM, bg=CLR_BG
                 ).pack(pady=(8, 4))

        self.mini_canvas = tk.Canvas(
            parent, width=200, height=200,
            bg="white", highlightthickness=2,
            highlightbackground=CLR_BORDER
        )
        self.mini_canvas.pack()

        tk.Button(parent, text="↻ Refresh", font=FONT_SMALL,
                  bg=CLR_CARD, fg=CLR_TEXT, relief="flat",
                  padx=8, pady=4, cursor="hand2",
                  command=self._refresh_mini_preview
                  ).pack(pady=6)

        # Mini info
        self.mini_info_var = tk.StringVar(value="Fill form to see preview")
        tk.Label(parent, textvariable=self.mini_info_var,
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_BG,
                 wraplength=200, justify="center").pack()

    # ── Status Bar ────────────────────────────────────────
    def _build_status_bar(self):
        bar = tk.Frame(self, bg=CLR_PANEL, pady=4)
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Ready  •  TSC TE244")
        tk.Label(bar, textvariable=self.status_var,
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_PANEL,
                 anchor="w", padx=10).pack(side="left")
        tk.Label(bar,
                 text=f"Label: {LABEL_W_INCH}×{LABEL_H_INCH} in  |  "
                      f"Print DPI: {DPI_PRINT}  |  "
                      f"DB: {DB_PATH.name}",
                 font=FONT_SMALL, fg=CLR_TEXT_DIM, bg=CLR_PANEL,
                 anchor="e", padx=10).pack(side="right")

    # ─────────────────────────────────────────────────────
    #  Card helper
    # ─────────────────────────────────────────────────────
    def _card(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=CLR_BG, pady=3)
        outer.pack(fill="x")
        tk.Label(outer, text=title, font=FONT_SUBTITLE,
                 fg=CLR_ACCENT, bg=CLR_BG).pack(anchor="w", padx=2)
        inner = tk.Frame(outer, bg=CLR_PANEL, padx=12, pady=8,
                         highlightthickness=1,
                         highlightbackground=CLR_BORDER)
        inner.pack(fill="x")
        return inner

    # ─────────────────────────────────────────────────────
    #  Logo handlers
    # ─────────────────────────────────────────────────────
    def _upload_logo(self):
        path = filedialog.askopenfilename(
            title="Select Company Logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"),
                       ("All Files", "*.*")]
        )
        if path:
            self.logo_path.set(path)
            self.db.set_setting(LOGO_PATH_KEY, path)
            self._refresh_logo_thumb()
            self._schedule_preview_refresh()
            self._set_status(f"Logo loaded: {os.path.basename(path)}")

    def _remove_logo(self):
        self.logo_path.set("")
        self.db.set_setting(LOGO_PATH_KEY, "")
        self.logo_lbl.config(image="", text="No logo",
                              fg=CLR_TEXT_DIM)
        self._logo_tk_img = None
        self._schedule_preview_refresh()

    def _refresh_logo_thumb(self):
        lp = self.logo_path.get()
        if not lp or not os.path.isfile(lp):
            return
        try:
            img = Image.open(lp).convert("RGBA")
            img.thumbnail((90, 52), Image.LANCZOS)
            self._logo_tk_img = ImageTk.PhotoImage(img)
            self.logo_lbl.config(image=self._logo_tk_img,
                                  text="", bg=CLR_PANEL)
        except Exception as ex:
            messagebox.showerror("Logo Error",
                                 f"Could not load logo:\n{ex}")

    # ─────────────────────────────────────────────────────
    #  Sign mode
    # ─────────────────────────────────────────────────────
    def _toggle_sign_mode(self):
        if self.inv_sign_type.get() == "text":
            self.sign_entry.pack(side="left", fill="x", expand=True,
                                 ipady=6, padx=(8, 4))
            self.sign_img_btn.pack_forget()
            self.sign_img_lbl.pack_forget()
        else:
            self.sign_entry.pack_forget()
            self.sign_img_btn.pack(side="left", padx=4)
            self.sign_img_lbl.pack(side="left")
        self._schedule_preview_refresh()

    def _upload_sign_image(self):
        path = filedialog.askopenfilename(
            title="Select Signature Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"),
                       ("All Files", "*.*")]
        )
        if path:
            self.inv_sign_img.set(path)
            short = os.path.basename(path)[:22]
            self.sign_img_lbl.config(text=f"✔ {short}", fg=CLR_SUCCESS)
            self._schedule_preview_refresh()

    # ─────────────────────────────────────────────────────
    #  Copies
    # ─────────────────────────────────────────────────────
    def _inc_copies(self):
        self.copies_var.set(self.copies_var.get() + 1)
        self._on_copies_change()

    def _dec_copies(self):
        v = self.copies_var.get()
        if v > 1:
            self.copies_var.set(v - 1)
            self._on_copies_change()
        else:
            messagebox.showwarning("Minimum Copies",
                                   "Copies cannot be less than 1.")

    def _on_copies_change(self):
        try:
            v = int(self.copies_var.get())
            if v < 1:
                self.copies_var.set(1)
        except Exception:
            self.copies_var.set(1)

    # ─────────────────────────────────────────────────────
    #  Collect & Validate form data
    # ─────────────────────────────────────────────────────
    def _collect_data(self, validate: bool = True) -> dict | None:
        """
        Gather all form values into a dict.
        If validate=True, returns None and shows error if any field empty.
        """
        data = {}

        for key, ent in self.entries.items():
            val = ent.get_value().strip()
            if validate and not val:
                field_name = key.replace("_", " ").title()
                messagebox.showerror("Validation Error",
                                     f"'{field_name}' cannot be empty.")
                ent.focus_set()
                return None
            data[key] = val

        qr = self.qr_entry.get_value().strip()
        if validate and not qr:
            messagebox.showerror("Validation Error",
                                 "Code Text (QR/Barcode) cannot be empty.")
            self.qr_entry.focus_set()
            return None
        data["qr_text"]   = qr
        data["code_type"] = self.code_type.get()

        data["inv_sign_type"] = self.inv_sign_type.get()
        data["inv_sign_data"] = (
            self.sign_text_var.get().strip()
            if data["inv_sign_type"] == "text"
            else self.inv_sign_img.get().strip()
        )

        try:
            copies = int(self.copies_var.get())
            if copies < 1:
                raise ValueError
        except Exception:
            if validate:
                messagebox.showerror("Validation Error",
                                     "Copies must be a positive integer.")
            copies = 1
        data["copies"]    = copies
        data["logo_path"] = self.logo_path.get()

        return data

    def _collect_for_preview(self) -> dict:
        """Collect data without validation for live preview."""
        data = {
            "customer_name": self.entries["customer_name"].get_value() or "—",
            "product_code":  self.entries["product_code"].get_value()  or "—",
            "part_size":     self.entries["part_size"].get_value()     or "—",
            "part_qty":      self.entries["part_qty"].get_value()      or "—",
            "material":      self.entries["material"].get_value()      or "—",
            "qr_text":       self.qr_entry.get_value() or "PREVIEW",
            "code_type":     self.code_type.get(),
            "inv_sign_type": self.inv_sign_type.get(),
            "inv_sign_data": (
                self.sign_text_var.get()
                if self.inv_sign_type.get() == "text"
                else self.inv_sign_img.get()
            ),
            "logo_path": self.logo_path.get(),
            "copies":    self.copies_var.get(),
        }
        return data

    # ─────────────────────────────────────────────────────
    #  Live preview (debounced)
    # ─────────────────────────────────────────────────────
    def _schedule_preview_refresh(self, _=None):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(400, self._refresh_mini_preview)

    def _refresh_mini_preview(self):
        self._preview_job = None
        try:
            data      = self._collect_for_preview()
            r         = LabelRenderer(dpi=DPI_PREVIEW)
            lbl_img   = r.render(data)
            lbl_img   = lbl_img.resize((200, 200), Image.LANCZOS)
            self._mini_tk = ImageTk.PhotoImage(lbl_img)
            self.mini_canvas.create_image(0, 0, anchor="nw",
                                          image=self._mini_tk)
            self.mini_info_var.set(
                f"Customer: {data['customer_name']}\n"
                f"Code: {data['product_code']}"
            )
        except Exception:
            pass

    # ─────────────────────────────────────────────────────
    #  Password dialog
    # ─────────────────────────────────────────────────────
    def _ask_password(self) -> bool:
        pwd = simpledialog.askstring(
            "🔒  Print Password",
            "Enter the print password to continue:",
            show="*", parent=self
        )
        if pwd is None:
            return False
        if hashlib.sha256(pwd.encode()).hexdigest() == self.password_hash:
            return True
        messagebox.showerror("❌  Access Denied",
                             "Incorrect password. Printing cancelled.")
        return False

    # ─────────────────────────────────────────────────────
    #  Print flow
    # ─────────────────────────────────────────────────────
    def _show_preview(self):
        data = self._collect_data()
        if data is None:
            return
        PreviewWindow(self, data,
                      on_confirm_print=lambda: self._do_print(data))

    def _on_print(self):
        """Full print flow: validate → password → preview → print."""
        data = self._collect_data()
        if data is None:
            return
        if not self._ask_password():
            self._set_status("Print cancelled — wrong password.")
            return
        PreviewWindow(self, data,
                      on_confirm_print=lambda: self._do_print(data))

    def _do_print(self, data: dict):
        """Spawn background thread to avoid blocking UI."""
        self._set_status("🖨  Sending to printer…")

        def _thread():
            try:
                TSPLPrinter.print_label(data, data.get("copies", 1))
                msg = (f"✔  Label sent to TSC TE244.\n"
                       f"Copies: {data.get('copies', 1)}")
                self.after(0, lambda: messagebox.showinfo(
                    "Print Successful", msg))
                self.after(0, lambda: self._set_status("Print successful ✔"))
            except Exception as ex:
                err = str(ex)
                self.after(0, lambda: messagebox.showerror(
                    "⚠  Print Error",
                    f"Could not print:\n\n{err}\n\n"
                    "• Ensure TSC TE244 is online and installed.\n"
                    "• Use File → Export TSPL to print manually.\n"
                    "• Install pywin32 for best compatibility."
                ))
                self.after(0, lambda: self._set_status("Print failed ✕"))

        threading.Thread(target=_thread, daemon=True).start()

    # ─────────────────────────────────────────────────────
    #  Save / Load / Clear
    # ─────────────────────────────────────────────────────
    def _save_entry(self):
        data = self._collect_data()
        if data is None:
            return
        if self.current_id:
            self.db.update_label(self.current_id, data)
            self._set_status(f"Entry #{self.current_id} updated.")
            messagebox.showinfo("Saved",
                                f"Entry #{self.current_id} updated successfully.")
        else:
            new_id = self.db.save_label(data)
            self.current_id = new_id
            self._set_status(f"New entry saved — ID #{new_id}.")
            messagebox.showinfo("Saved",
                                f"Label saved with ID #{new_id}.")

    def _open_history(self):
        HistoryWindow(self, self.db, on_load=self._load_entry)

    def _load_entry(self, rec: dict, db_id: int):
        """Populate all form fields from a saved record."""
        self.current_id = db_id
        for key, ent in self.entries.items():
            ent.set_value(rec.get(key, ""))

        self.qr_entry.set_value(rec.get("qr_text", ""))
        self.code_type.set(rec.get("code_type", "qr"))
        self.inv_sign_type.set(rec.get("inv_sign_type", "text"))

        if rec.get("inv_sign_type") == "text":
            self.sign_text_var.set(rec.get("inv_sign_data", ""))
        else:
            self.inv_sign_img.set(rec.get("inv_sign_data", ""))
            name = os.path.basename(rec.get("inv_sign_data", ""))
            self.sign_img_lbl.config(text=f"✔ {name}", fg=CLR_SUCCESS)

        self.logo_path.set(rec.get("logo_path", ""))
        if rec.get("logo_path"):
            self._refresh_logo_thumb()
        self.copies_var.set(rec.get("copies", 1))
        self._toggle_sign_mode()
        self._refresh_mini_preview()
        self._set_status(f"Loaded record #{db_id}")

    def _clear_form(self):
        for ent in self.entries.values():
            ent.set_value("")
        self.qr_entry.set_value("")
        self.sign_text_var.set("")
        self.inv_sign_img.set("")
        self.sign_img_lbl.config(text="")
        self.inv_sign_type.set("text")
        self.code_type.set("qr")
        self.copies_var.set(1)
        self.current_id = None
        self._toggle_sign_mode()
        self._refresh_mini_preview()
        self._set_status("Form cleared — new label")

    # ─────────────────────────────────────────────────────
    #  Export
    # ─────────────────────────────────────────────────────
    def _export_tspl(self):
        data = self._collect_data()
        if data is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save TSPL Print File",
            defaultextension=".prn",
            filetypes=[("TSPL File", "*.prn"), ("All Files", "*.*")]
        )
        if path:
            try:
                TSPLPrinter.save_tspl(data, data.get("copies", 1), path)
                self._set_status(f"TSPL exported: {path}")
                messagebox.showinfo("Exported",
                    f"TSPL file saved:\n{path}\n\n"
                    "Send directly to printer port:\n"
                    f'  copy /b "{path}" "\\\\localhost\\{TSPLPrinter.PRINTER_NAME}"')
            except Exception as ex:
                messagebox.showerror("Export Error", str(ex))

    def _export_png(self):
        data = self._collect_data()
        if data is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save Label as PNG",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if path:
            try:
                r = LabelRenderer(dpi=DPI_PRINT)
                r.render(data).save(path, "PNG")
                self._set_status(f"PNG exported: {path}")
                messagebox.showinfo("Exported",
                                    f"High-resolution label PNG saved:\n{path}")
            except Exception as ex:
                messagebox.showerror("Export Error", str(ex))

    # ─────────────────────────────────────────────────────
    #  Settings
    # ─────────────────────────────────────────────────────
    def _change_password(self):
        old = simpledialog.askstring("Current Password",
                                     "Enter current password:",
                                     show="*", parent=self)
        if old is None:
            return
        if hashlib.sha256(old.encode()).hexdigest() != self.password_hash:
            messagebox.showerror("Error", "Current password is incorrect.")
            return
        new = simpledialog.askstring("New Password",
                                     "Enter new password (min 4 characters):",
                                     show="*", parent=self)
        if not new or len(new) < 4:
            messagebox.showwarning("Warning",
                                   "Password must be at least 4 characters.")
            return
        confirm = simpledialog.askstring("Confirm Password",
                                         "Re-enter new password:",
                                         show="*", parent=self)
        if new != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        self.password_hash = hashlib.sha256(new.encode()).hexdigest()
        self.db.set_setting("print_password_hash", self.password_hash)
        messagebox.showinfo("Success", "Print password changed successfully.")
        self._set_status("Password updated.")

    def _set_printer_name(self):
        name = simpledialog.askstring(
            "Printer Name",
            "Enter the exact Windows printer name for TSC TE244:",
            initialvalue=TSPLPrinter.PRINTER_NAME,
            parent=self
        )
        if name:
            TSPLPrinter.PRINTER_NAME = name
            self.db.set_setting("printer_name", name)
            self._set_status(f"Printer set to: {name}")

    # ─────────────────────────────────────────────────────
    #  About
    # ─────────────────────────────────────────────────────
    def _show_about(self):
        bc_status = ("✔ Available" if BARCODE_AVAILABLE
                     else "✕ Not installed — pip install python-barcode")
        messagebox.showinfo(
            "About — Cosmo Label Printer v2.0",
            f"Cosmo Hydraulic Industries\n"
            f"TSC TE244 Label Printer Application\n"
            f"Version 2.0 — Production Ready\n\n"
            f"Label Size    : {LABEL_W_INCH}×{LABEL_H_INCH} inches (fixed)\n"
            f"Printer DPI   : {DPI_PRINT}\n"
            f"Commands      : TSPL / TSPL2\n"
            f"Database      : {DB_PATH}\n"
            f"Barcode Lib   : {bc_status}\n\n"
            f"Default password: cosmo123\n"
            f"(Change via Settings → Change Print Password)"
        )

    # ─────────────────────────────────────────────────────
    #  Utilities
    # ─────────────────────────────────────────────────────
    def _set_status(self, msg: str):
        ts  = datetime.now().strftime("%H:%M:%S")
        self.status_var.set(f"[{ts}]  {msg}")

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w,  h  = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _on_close(self):
        self.db.close()
        self.destroy()


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── License check — must pass before app opens ────────
    if not show_license_check_window():
        sys.exit(0)

    app = CosmoLabelApp()
    app.mainloop()