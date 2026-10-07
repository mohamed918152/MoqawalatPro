# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, os, hashlib, secrets, csv, shutil, subprocess, sys, zipfile
from pathlib import Path
from datetime import datetime

APP_NAME = "برنامج إدارة المقاولات"
VERSION = "6.3.1"
OWNER = "محمد ممدوح"
COPYRIGHT = "© 2026 محمد ممدوح — جميع الحقوق محفوظة"
BASE = os.path.dirname(os.path.abspath(__file__))
# بيانات البرنامج تحفظ في مجلد Windows دائم حتى مع تشغيل EXE بنظام --onefile
DATA_DIR = os.path.join(os.getenv("APPDATA") or BASE, "MoqawalatPro")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "moqawalat.db")

# ---------------- Database ----------------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=3000")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA cache_size=-12000")
    return con

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password, stored):
    try:
        s, d = stored.split(":")
        x = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(s), 120000)
        return secrets.compare_digest(x.hex(), d)
    except Exception:
        return False

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    con = db(); c = con.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS login_log(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, success INTEGER, created_at TEXT);
    CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS workers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, job TEXT, project TEXT, salary REAL DEFAULT 0, status TEXT DEFAULT 'نشط', notes TEXT);
    CREATE TABLE IF NOT EXISTS drivers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, license_no TEXT, vehicle TEXT, plate TEXT, project TEXT, status TEXT DEFAULT 'نشط', notes TEXT);
    CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle TEXT NOT NULL, plate TEXT, type TEXT, driver TEXT, project TEXT, model_year TEXT, status TEXT DEFAULT 'متاح', notes TEXT);
    CREATE TABLE IF NOT EXISTS vehicle_maintenance(id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle TEXT NOT NULL, maintenance_date TEXT, maintenance_type TEXT, cost REAL DEFAULT 0, odometer REAL DEFAULT 0, supplier TEXT, project TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, client TEXT, location TEXT, start_date TEXT, end_date TEXT, budget REAL DEFAULT 0, status TEXT DEFAULT 'جاري', manager TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS contracts(id INTEGER PRIMARY KEY AUTOINCREMENT, contract_no TEXT UNIQUE, project TEXT, client TEXT, contract_date TEXT, start_date TEXT, end_date TEXT, value REAL DEFAULT 0, retention REAL DEFAULT 0, status TEXT DEFAULT 'نشط', notes TEXT);
    CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT NOT NULL, category TEXT, unit TEXT, quantity REAL DEFAULT 0, min_qty REAL DEFAULT 0, price REAL DEFAULT 0, supplier TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS material_moves(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT NOT NULL, move_type TEXT NOT NULL, qty REAL DEFAULT 0, unit_price REAL DEFAULT 0, project TEXT, move_date TEXT, reference TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT NOT NULL, supplier TEXT, qty REAL DEFAULT 0, unit_price REAL DEFAULT 0, total REAL DEFAULT 0, purchase_date TEXT, project TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, description TEXT, amount REAL DEFAULT 0, expense_date TEXT, project TEXT, paid_by TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS revenues(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, description TEXT, amount REAL DEFAULT 0, revenue_date TEXT, project TEXT, received_from TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS invoices(id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT UNIQUE, project TEXT, customer TEXT, invoice_date TEXT, due_date TEXT, subtotal REAL DEFAULT 0, tax REAL DEFAULT 0, total REAL DEFAULT 0, status TEXT DEFAULT 'غير مدفوعة', notes TEXT);
    CREATE TABLE IF NOT EXISTS invoice_items(id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL, description TEXT NOT NULL, qty REAL DEFAULT 1, unit_price REAL DEFAULT 0, discount REAL DEFAULT 0, tax_rate REAL DEFAULT 0, line_total REAL DEFAULT 0, FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS receipts(id INTEGER PRIMARY KEY AUTOINCREMENT, receipt_no TEXT UNIQUE, project TEXT, customer TEXT, receipt_date TEXT, amount REAL DEFAULT 0, method TEXT, reference TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, payment_no TEXT UNIQUE, project TEXT, payee TEXT, payment_date TEXT, amount REAL DEFAULT 0, method TEXT, reference TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, worker TEXT NOT NULL, project TEXT, attendance_date TEXT, status TEXT DEFAULT 'حاضر', hours REAL DEFAULT 8, overtime REAL DEFAULT 0, notes TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, title TEXT NOT NULL, assigned_to TEXT, due_date TEXT, status TEXT DEFAULT 'جديدة', priority TEXT DEFAULT 'متوسطة', notes TEXT);
    CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS company_profile(id INTEGER PRIMARY KEY CHECK(id=1), name TEXT, legal_name TEXT, phone TEXT, email TEXT, address TEXT, tax_no TEXT, logo_path TEXT, footer TEXT);
    CREATE TABLE IF NOT EXISTS branches(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, address TEXT, manager TEXT, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS permissions(id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, module TEXT NOT NULL, can_view INTEGER DEFAULT 1, can_add INTEGER DEFAULT 1, can_edit INTEGER DEFAULT 1, can_delete INTEGER DEFAULT 1, UNIQUE(role,module));
    CREATE TABLE IF NOT EXISTS doc_sequences(doc_type TEXT PRIMARY KEY, prefix TEXT, next_no INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, phone TEXT, email TEXT, address TEXT, tax_no TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS warehouses(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, location TEXT, manager TEXT, active INTEGER DEFAULT 1, notes TEXT);
    CREATE TABLE IF NOT EXISTS stock_transfers(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT NOT NULL, from_warehouse TEXT, to_warehouse TEXT, qty REAL DEFAULT 0, transfer_date TEXT, reference TEXT, notes TEXT);
    CREATE TABLE IF NOT EXISTS db_backups(id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL, created_at TEXT NOT NULL, size_bytes INTEGER DEFAULT 0, kind TEXT DEFAULT 'manual');
    CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
    ''')
    # v5 migrations for existing v4 databases
    for col, typ in [('discount','REAL DEFAULT 0'),('tax_rate','REAL DEFAULT 0'),('paid','REAL DEFAULT 0')]:
        try: c.execute(f'ALTER TABLE invoices ADD COLUMN {col} {typ}')
        except sqlite3.OperationalError: pass
    defaults = [('admin','admin123','مدير النظام','admin'),('محمد','123','محمد أحمد','user'),('علي','pass1234','علي محمود','user')]
    for u,p,n,r in defaults:
        if not c.execute('SELECT id FROM users WHERE username=?',(u,)).fetchone():
            c.execute('INSERT INTO users(username,password_hash,name,role) VALUES(?,?,?,?)',(u,hash_password(p),n,r))
    setting_defaults = {
        'language':'العربية','theme':'فاتح','company_name':'برنامج إدارة المقاولات','owner':'محمد ممدوح',
        'currency':'ر.س','date_format':'YYYY-MM-DD','font_size':'10','confirm_delete':'نعم',
        'notifications':'نعم','auto_backup':'نعم','backup_interval':'يومي','startup_page':'لوحة التحكم',
        'show_owner':'نعم','compact_mode':'لا','page_size':'100'
    }
    for sk,sv in setting_defaults.items():
        c.execute('INSERT OR IGNORE INTO app_settings(key,value) VALUES(?,?)',(sk,sv))
    c.execute('INSERT OR IGNORE INTO company_profile(id,name,legal_name,phone,email,address,tax_no,logo_path,footer) VALUES(1,?,?,?,?,?,?,?,?)',('برنامج إدارة المقاولات','محمد ممدوح للمقاولات','','','','','',COPYRIGHT))
    for typ,prefix in [('invoice','INV'),('receipt','REC'),('payment','PAY'),('contract','CON')]:
        c.execute('INSERT OR IGNORE INTO doc_sequences(doc_type,prefix,next_no) VALUES(?,?,1)',(typ,prefix))
    modules=['customers','workers','drivers','vehicles','maintenance','projects','contracts','inventory','material_moves','purchases','expenses','revenues','invoices','receipts','payments','attendance','tasks','reports','users','branches','company']
    for role in ('admin','user'):
        for m in modules:
            vals=(1,1,1,1) if role=='admin' else (1,1,1,0)
            c.execute('INSERT OR IGNORE INTO permissions(role,module,can_view,can_add,can_edit,can_delete) VALUES(?,?,?,?,?,?)',(role,m,*vals))
    # Performance indexes: speed up search, dashboards and financial reports as data grows.
    indexes = [
      'CREATE INDEX IF NOT EXISTS idx_workers_name ON workers(name)',
      'CREATE INDEX IF NOT EXISTS idx_drivers_name ON drivers(name)',
      'CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)',
      'CREATE INDEX IF NOT EXISTS idx_inventory_item ON inventory(item)',
      'CREATE INDEX IF NOT EXISTS idx_purchases_supplier ON purchases(supplier)',
      'CREATE INDEX IF NOT EXISTS idx_purchases_project ON purchases(project)',
      'CREATE INDEX IF NOT EXISTS idx_expenses_project ON expenses(project)',
      'CREATE INDEX IF NOT EXISTS idx_revenues_project ON revenues(project)',
      'CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer)',
      'CREATE INDEX IF NOT EXISTS idx_invoices_project ON invoices(project)',
      'CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)',
      'CREATE INDEX IF NOT EXISTS idx_receipts_customer ON receipts(customer)',
      'CREATE INDEX IF NOT EXISTS idx_payments_payee ON payments(payee)',
      'CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project)',
      'CREATE INDEX IF NOT EXISTS idx_material_moves_item ON material_moves(item)',
      'CREATE INDEX IF NOT EXISTS idx_login_log_user_date ON login_log(username,created_at)'
    ]
    for sql in indexes: c.execute(sql)
    c.execute('INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(?,?)',(VERSION,now()))
    con.commit(); con.close()

# ---------------- Settings ----------------
def get_setting(key, default=''):
    try:
        con=db(); row=con.execute('SELECT value FROM app_settings WHERE key=?',(key,)).fetchone(); con.close()
        return row['value'] if row else default
    except Exception:
        return default

def set_setting(key, value):
    con=db(); con.execute('INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)',(key,str(value))); con.commit(); con.close()

def all_settings():
    con=db(); rows=con.execute('SELECT key,value FROM app_settings').fetchall(); con.close(); return {r['key']:r['value'] for r in rows}

# ---------------- Localization ----------------
TRANSLATIONS = {
    'العربية':'العربية','English':'English','نعم':'Yes','لا':'No','فاتح':'Light','داكن':'Dark',
    'لوحة التحكم':'Dashboard','لوحة التحكم الرئيسية':'Main Dashboard','إعدادات البرنامج':'Program Settings',
    'التقارير':'Reports','التقارير والإحصائيات':'Reports & Statistics','الرئيسية':'Home','تسجيل الخروج':'Logout','حول البرنامج':'About',
    'الإعدادات':'Settings','مركز الإعدادات':'Settings Center','حفظ وتطبيق الإعدادات':'Save & Apply Settings',
    'تسجيل الدخول':'Login','دخول':'Login','خروج':'Exit','اسم المستخدم':'Username','كلمة المرور':'Password',
    'مرحباً بك في نظام إدارة المقاولات':'Welcome to the Construction Management System','تنظيم • متابعة • إنجاز':'Organize • Track • Deliver',
    'المشاريع والعقود':'Projects & Contracts','العملاء والعمالة':'Clients & Workforce','المركبات والصيانة':'Vehicles & Maintenance',
    'المواد والمخزون':'Materials & Inventory','الفواتير والتحصيل':'Invoices & Collections','المصروفات والمدفوعات':'Expenses & Payments',
    'الحضور والمهام والتقارير':'Attendance, Tasks & Reports','المستخدمون':'Users','مدير النظام':'Administrator','مستخدم':'User',
    'العملاء':'Clients','العقود':'Contracts','المركبات':'Vehicles','الصيانة':'Maintenance','سندات القبض':'Receipts','سندات الصرف':'Payments','الحضور والانصراف':'Attendance','التاريخ':'Date','الساعات':'Hours','طريقة التحصيل':'Collection Method','الاستحقاق':'Due Date','الاسم':'Name','الصلاحية':'Role','نشط':'Active','الحضور':'Attendance','حركة المواد':'Material Movements',
    'الفواتير':'Invoices','سندات قبض':'Receipts','سندات صرف':'Payments','العمال':'Workers','السائقون':'Drivers','المشاريع':'Projects',
    'أصناف المخزون':'Inventory Items','المهام المفتوحة':'Open Tasks','إجمالي الفواتير':'Total Invoices','المقبوضات':'Receipts',
    'المدفوعات':'Payments','الإيرادات':'Revenue','المصروفات':'Expenses','المهام':'Tasks','المخزون':'Inventory','المشتريات':'Purchases',
    'إضافة ':'Add ','تعديل ':'Edit ','إضافة جديد':'Add New','تعديل':'Edit','حذف':'Delete','تصدير CSV':'Export CSV','بحث':'Search','حفظ البيانات':'Save',
    'نسخة احتياطية الآن':'Backup Now','استعادة نسخة':'Restore Backup','مجلد البيانات':'Data Folder','إعادة الإعدادات':'Reset Settings',
    'البيانات محفوظة في:':'Data is stored in:','تحكم كامل في شكل البرنامج\nوالبيانات والطباعة والنسخ الاحتياطي':'Control the interface, data, printing and backups',
    'اللغة والمظهر':'Language & Appearance','لغة البرنامج':'Program Language','المظهر':'Theme','حجم الخط':'Font Size','الوضع المضغوط':'Compact Mode',
    'معلومات البرنامج':'Program Information','اسم البرنامج / الشركة':'Program / Company Name','اسم المالك':'Owner Name','إظهار حقوق الملكية':'Show Ownership Notice','العملة':'Currency',
    'التاريخ والطباعة':'Date & Display','تنسيق التاريخ':'Date Format','عدد السجلات في الشاشة':'Rows per Screen',
    'التشغيل والتنبيهات':'Startup & Notifications','التنبيهات':'Notifications','صفحة البداية':'Startup Page','تأكيد الحذف':'Confirm Delete',
    'النسخ الاحتياطي':'Backup','النسخ الاحتياطي التلقائي':'Automatic Backup','الفترة':'Interval',
    'تم الحفظ':'Saved','تم حفظ الإعدادات وتطبيقها.':'Settings saved and applied.','إعادة جميع إعدادات البرنامج إلى الوضع الافتراضي؟':'Reset all program settings to defaults?',
    'تم إنشاء نسخة احتياطية':'Backup created','تمت الاستعادة':'Restored','فشل الاستعادة':'Restore Failed','تعذر الحفظ':'Save Failed',
    'تأكيد الحذف':'Confirm Delete','هل تريد حذف السجل المحدد؟':'Delete the selected record?','تم':'Done','تم تصدير البيانات بنجاح':'Data exported successfully','تم حفظ التقرير':'Report saved',
    'اختيار نسخة احتياطية':'Choose a backup','تصدير البيانات':'Export Data','حفظ التقرير':'Save Report','سيتم استبدال قاعدة البيانات الحالية. هل تريد المتابعة؟':'The current database will be replaced. Continue?',
    'سيتم إعادة تشغيل البرنامج.':'The program will restart.','بيانات ناقصة':'Missing Data','يرجى إدخال اسم المستخدم وكلمة المرور':'Please enter username and password',
    'خطأ':'Error','اسم المستخدم أو كلمة المرور غير صحيحة':'Incorrect username or password','حول البرنامج':'About',
    'المالك:':'Owner:','إغلاق':'Close','نظام إدارة المقاولات والمشاريع والمالية والمخزون':'Construction, Projects, Finance & Inventory Management',
    'الإصدار':'Version','العملة':'Currency','ر.س':'SAR','ر.ق':'QAR','د.إ':'AED','نقدي':'Cash','تحويل بنكي':'Bank Transfer','شيك':'Cheque','بطاقة':'Card',
    'جاري':'In Progress','مكتمل':'Completed','متوقف':'Stopped','مخطط':'Planned','نشط':'Active','غير نشط':'Inactive','منتهي':'Expired','ملغي':'Cancelled','معلق':'Pending',
    'متاح':'Available','في الموقع':'On Site','صيانة':'Maintenance','خارج الخدمة':'Out of Service','إدخال':'In','إخراج':'Out','تسوية':'Adjustment',
    'غير مدفوعة':'Unpaid','جزئي':'Partial','مدفوعة':'Paid','ملغاة':'Cancelled','حاضر':'Present','غائب':'Absent','إجازة':'Leave','مأمورية':'Mission',
    'جديدة':'New','قيد التنفيذ':'In Progress','مكتملة':'Completed','مؤجلة':'Deferred','منخفضة':'Low','متوسطة':'Medium','عالية':'High',
    'يومي':'Daily','أسبوعي':'Weekly','شهري':'Monthly','YYYY-MM-DD':'YYYY-MM-DD','DD/MM/YYYY':'DD/MM/YYYY','MM/DD/YYYY':'MM/DD/YYYY',
    'اسم العميل':'Client Name','الهاتف':'Phone','البريد الإلكتروني':'Email','العنوان':'Address','ملاحظات':'Notes','اسم العامل':'Worker Name','الوظيفة':'Job','المشروع':'Project','الراتب':'Salary','الحالة':'Status',
    'اسم السائق':'Driver Name','رقم الرخصة':'License No.','المركبة':'Vehicle','رقم اللوحة':'Plate No.','اسم/نوع المركبة':'Vehicle / Type','التصنيف':'Category','السائق':'Driver','سنة الصنع':'Model Year',
    'تاريخ الصيانة':'Maintenance Date','نوع الصيانة':'Maintenance Type','التكلفة':'Cost','العداد':'Odometer','الورشة/المورد':'Workshop / Supplier',
    'اسم المشروع':'Project Name','العميل':'Client','الموقع':'Location','تاريخ البداية':'Start Date','تاريخ النهاية':'End Date','الميزانية':'Budget','المسؤول':'Manager',
    'رقم العقد':'Contract No.','رقم العقد':'Contract No.','تاريخ العقد':'Contract Date','البداية':'Start','النهاية':'End','قيمة العقد':'Contract Value','الاحتجاز':'Retention',
    'الصنف':'Item','الوحدة':'Unit','الكمية الحالية':'Current Quantity','الحد الأدنى':'Minimum Quantity','سعر الوحدة':'Unit Price','المورد':'Supplier',
    'نوع الحركة':'Movement Type','الكمية':'Quantity','تاريخ الحركة':'Movement Date','المرجع':'Reference','الكمية':'Quantity','سعر الوحدة':'Unit Price',
    'الكمية':'Quantity','إجمالي':'Total','تاريخ الشراء':'Purchase Date','الفئة':'Category','الوصف':'Description','المبلغ':'Amount','تاريخ المصروف':'Expense Date','دفع بواسطة':'Paid By',
    'المصدر':'Source','تاريخ الإيراد':'Revenue Date','استلم من':'Received From','رقم الفاتورة':'Invoice No.','تاريخ الفاتورة':'Invoice Date','تاريخ الاستحقاق':'Due Date','قبل الضريبة':'Subtotal','الضريبة':'Tax',
    'الإجمالي':'Total','رقم السند':'Receipt No.','تاريخ السند':'Receipt Date','طريقة الدفع':'Payment Method','رقم المرجع':'Reference No.','المستفيد':'Payee','تاريخ الدفع':'Payment Date',
    'رقم الموظف':'Employee No.','تاريخ الحضور':'Attendance Date','ساعات العمل':'Work Hours','الإضافي':'Overtime','عنوان المهمة':'Task Title','المسند إليه':'Assigned To','موعد الاستحقاق':'Due Date','الأولوية':'Priority',
    'كلمة المرور (مطلوبة عند الإضافة)':'Password (required when adding)','ملخص مالي وتشغيلي':'Financial & Operational Summary','تصدير التقرير CSV':'Export Report CSV',
    'تاريخ التقرير:':'Report Date:','إجمالي قيمة الفواتير:':'Total Invoice Value:','إجمالي المقبوضات:':'Total Receipts:','إجمالي المدفوعات:':'Total Payments:',
    'صافي التدفق:':'Net Cash Flow:','المشاريع النشطة:':'Active Projects:','أصناف تحت الحد الأدنى:':'Items Below Minimum:','عدد المشاريع':'Projects Count','عدد العملاء':'Clients Count','عدد العمال':'Workers Count','عدد المركبات':'Vehicles Count',
    'الفواتير':'Invoices','المقبوضات':'Receipts','المدفوعات':'Payments','مشاريع نشطة':'Active Projects','أصناف منخفضة':'Low Stock Items',
}
def tr(text):
    if get_setting('language','العربية') != 'English': return text
    return TRANSLATIONS.get(text, text)

def tr_choice(value):
    return tr(value)

# ---------------- UI ----------------
FONT='Arial'; BLUE='#0b477e'; LIGHT='#eef3f8'; BORDER='#d7e1eb'; TEXT='#173f63'; GREEN='#16804a'; RED='#b42318'; GOLD='#b77a00'

def money(x):
    try: return f"{float(x or 0):,.2f} {get_setting('currency','ر.س')}"
    except: return "0.00"

def as_number(value):
    if value is None or str(value).strip() == '': return 0
    return float(str(value).replace(',',''))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.current_user=None
        self.apply_window_settings()
        self.style()
        self.login_screen()

    def apply_window_settings(self):
        self.option_add('*Font', f'{FONT} {get_setting("font_size","10")}')
        self.title(get_setting('company_name', APP_NAME))
        self.geometry('1536x974'); self.minsize(1100,700)
        self.configure(bg=('#17212b' if get_setting('theme','فاتح')=='داكن' else LIGHT))

    def backup_database(self, silent=False, kind='manual'):
        try:
            os.makedirs(os.path.join(DATA_DIR,'backups'), exist_ok=True)
            stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
            dest=os.path.join(DATA_DIR,'backups',f'moqawalat_{stamp}_{kind}.db')
            con=sqlite3.connect(DB_PATH); con.execute('PRAGMA wal_checkpoint(FULL)'); bcon=sqlite3.connect(dest); con.backup(bcon); bcon.close(); con.close()
            size=os.path.getsize(dest)
            con=db(); con.execute('INSERT INTO db_backups(file_path,created_at,size_bytes,kind) VALUES(?,?,?,?)',(dest,now(),size,kind)); rows=con.execute('SELECT id,file_path FROM db_backups ORDER BY id DESC').fetchall()
            for r in rows[30:]:
                try:
                    if os.path.exists(r['file_path']): os.remove(r['file_path'])
                except OSError: pass
                con.execute('DELETE FROM db_backups WHERE id=?',(r['id'],))
            con.commit(); con.close()
            if not silent: messagebox.showinfo('النسخ الاحتياطي',f'تم إنشاء نسخة احتياطية:\n{dest}')
            return dest
        except Exception as ex:
            if not silent: messagebox.showerror('النسخ الاحتياطي',str(ex))
            return None

    def restore_database(self):
        path=filedialog.askopenfilename(title='اختيار نسخة احتياطية',initialdir=os.path.join(DATA_DIR,'backups'),filetypes=[('SQLite','*.db')])
        if not path:return
        if not messagebox.askyesno('استعادة البيانات','سيتم استبدال قاعدة البيانات الحالية. هل تريد المتابعة؟'): return
        try:
            self.backup_database(silent=True)
            shutil.copy2(path,DB_PATH)
            messagebox.showinfo('تمت الاستعادة','تمت استعادة قاعدة البيانات. سيتم إعادة تشغيل البرنامج.')
            self.destroy(); os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as ex: messagebox.showerror('فشل الاستعادة',str(ex))

    def open_data_folder(self):
        try:
            if os.name=='nt': os.startfile(DATA_DIR)
            elif sys.platform=='darwin': subprocess.Popen(['open',DATA_DIR])
            else: subprocess.Popen(['xdg-open',DATA_DIR])
        except Exception as ex: messagebox.showerror('المجلد',str(ex))

    def reset_settings(self):
        if not messagebox.askyesno(tr('إعادة الإعدادات'),tr('إعادة جميع إعدادات البرنامج إلى الوضع الافتراضي؟')): return
        defaults={'language':'العربية','theme':'فاتح','company_name':'برنامج إدارة المقاولات','owner':'محمد ممدوح','currency':'ر.س','date_format':'YYYY-MM-DD','font_size':'10','confirm_delete':'نعم','notifications':'نعم','auto_backup':'نعم','backup_interval':'يومي','startup_page':'لوحة التحكم','show_owner':'نعم','compact_mode':'لا','page_size':'100'}
        con=db()
        for k,v in defaults.items(): con.execute('INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)',(k,v))
        con.commit(); con.close(); self.apply_window_settings(); self.style(); self.settings()

    def clear(self):
        for w in self.winfo_children(): w.destroy()
        self._shell_top = None
        self._shell_body = None
        self._shell_title = None
        self._login_canvas = None

    def style(self):
        s=ttk.Style(self); s.theme_use('clam')
        s.configure('Treeview',font=(FONT,10),rowheight=29,background='white',fieldbackground='white')
        s.configure('Treeview.Heading',font=(FONT,10,'bold'),background='#dfeaf5',foreground=TEXT)
        s.configure('TButton',font=(FONT,10,'bold'),padding=7)
        s.configure('TEntry',font=(FONT,10),padding=6)
        s.configure('TCombobox',font=(FONT,10),padding=5)

    # ---------- Login ----------
    def login_screen(self):
        # شاشة الدخول الأصلية للبرنامج: بدون صورة الخلفية الجديدة
        self.clear()
        outer=tk.Frame(self,bg=LIGHT); outer.pack(fill='both',expand=True)
        self._login_outer = outer
        side=tk.Frame(outer,bg=BLUE,width=430); side.pack(side='right',fill='y'); side.pack_propagate(False)
        tk.Label(side,text='🏗️',font=('Segoe UI Emoji',55),bg=BLUE,fg='white').pack(pady=(70,5))
        tk.Label(side,text=get_setting('company_name',APP_NAME),font=(FONT,25,'bold'),bg=BLUE,fg='white').pack()
        tk.Label(side,text='تنظيم • متابعة • إنجاز',font=(FONT,14),bg=BLUE,fg='#dcecff').pack(pady=8)
        tk.Label(side,text='المشاريع والعقود\nالعملاء والعمالة\nالمركبات والصيانة\nالمواد والمخزون\nالفواتير والتحصيل\nالمصروفات والمدفوعات\nالحضور والمهام والتقارير',justify='right',font=(FONT,13),bg=BLUE,fg='white').pack(pady=42,padx=35,fill='x')
        card=tk.Frame(outer,bg='white',highlightthickness=1,highlightbackground=BORDER); card.place(relx=.43,rely=.5,anchor='center',width=500,height=485)
        tk.Label(card,text=tr('تسجيل الدخول'),font=(FONT,27,'bold'),bg='white',fg=TEXT).pack(pady=(42,7))
        tk.Label(card,text=tr('مرحباً بك في نظام إدارة المقاولات'),font=(FONT,11),bg='white',fg='#65788b').pack(pady=(0,25))
        self.user=self.field(card,'اسم المستخدم'); self.pwd=self.field(card,'كلمة المرور',True)
        ttk.Button(card,text=tr('دخول'),command=self.login).pack(fill='x',padx=50,pady=(12,7),ipady=6)
        tk.Button(card,text=tr('خروج'),command=self.destroy,bg='#e8eef5',fg='#24415d',bd=0,font=(FONT,11)).pack(fill='x',padx=50,pady=6,ipady=7)
        tk.Label(card,text=f'الإصدار {VERSION} • SQLite',bg='white',fg='#9aa9b7',font=(FONT,9)).pack(side='bottom',pady=(0,3))
        tk.Label(card,text=(f"© 2026 {get_setting('owner',OWNER)} — جميع الحقوق محفوظة" if get_setting('show_owner','نعم')=='نعم' else ''),bg='white',fg='#65788b',font=(FONT,9,'bold')).pack(side='bottom',pady=(0,12))
        self.user.focus_set(); self.user.bind('<Return>',lambda e:self.pwd.focus_set()); self.pwd.bind('<Return>',lambda e:self.login())

    def field(self,parent,label,password=False):
        tk.Label(parent,text=label,anchor='e',font=(FONT,11,'bold'),bg='white').pack(fill='x',padx=50)
        e=ttk.Entry(parent,justify='right',show='*' if password else ''); e.pack(fill='x',padx=50,pady=(5,13),ipady=4); return e

    def login(self):
        u=self.user.get().strip(); p=self.pwd.get()
        if not u or not p: messagebox.showwarning('بيانات ناقصة','يرجى إدخال اسم المستخدم وكلمة المرور'); return
        con=db(); row=con.execute('SELECT * FROM users WHERE username=? AND active=1',(u,)).fetchone(); ok=bool(row and verify_password(p,row['password_hash']))
        con.execute('INSERT INTO login_log(username,success,created_at) VALUES(?,?,?)',(u,int(ok),now())); con.commit(); con.close()
        if not ok: self.pwd.delete(0,'end'); messagebox.showerror('خطأ','اسم المستخدم أو كلمة المرور غير صحيحة'); return
        self.current_user=dict(row)
        if get_setting('startup_page','لوحة التحكم')=='التقارير': self.reports()
        else: self.dashboard()

    def about(self):
        win=tk.Toplevel(self)
        win.title(tr('حول البرنامج'))
        win.geometry('480x300')
        win.resizable(False,False)
        win.configure(bg='white')
        tk.Label(win,text='🏗️',font=('Segoe UI Emoji',42),bg='white').pack(pady=(22,4))
        tk.Label(win,text=get_setting('company_name',APP_NAME),font=(FONT,20,'bold'),bg='white',fg=TEXT).pack()
        tk.Label(win,text=f'الإصدار {VERSION}',font=(FONT,11),bg='white',fg='#65788b').pack(pady=4)
        tk.Label(win,text=f"المالك: {get_setting('owner',OWNER)}",font=(FONT,12,'bold'),bg='white',fg=BLUE).pack(pady=7)
        tk.Label(win,text=COPYRIGHT,font=(FONT,10),bg='white',fg='#65788b').pack(pady=4)
        tk.Label(win,text='نظام إدارة المقاولات والمشاريع والمالية والمخزون',font=(FONT,10),bg='white',fg='#65788b').pack(pady=3)
        ttk.Button(win,text=tr('إغلاق'),command=win.destroy).pack(pady=18,ipadx=25)

    # ---------- Shell ----------
    def shell(self,title):
        # Reuse the application shell instead of destroying/recreating the entire window
        # on every navigation. This removes a major source of UI lag.
        # Remove the login screen before creating the main application shell.
        # Keeping the login container alive causes it to remain visible behind/above
        # the main pages after a successful login.
        login_outer = getattr(self, '_login_outer', None)
        if login_outer is not None:
            try:
                if login_outer.winfo_exists():
                    login_outer.destroy()
            except tk.TclError:
                pass
            self._login_outer = None

        if getattr(self, '_shell_body', None) is not None and self._shell_body.winfo_exists():
            # Keep the persistent page title; only clear the previous page content.
            # The previous implementation destroyed the title label and then tried
            # to update it, causing a TclError immediately after the first navigation.
            for w in self._shell_body.winfo_children():
                if w is not getattr(self, '_shell_title', None):
                    w.destroy()
            if getattr(self, '_shell_title', None) is not None and self._shell_title.winfo_exists():
                self._shell_title.configure(text=title)
            return self._shell_body
        top=tk.Frame(self,bg=BLUE,height=68); top.pack(fill='x'); top.pack_propagate(False)
        tk.Label(top,text=get_setting('company_name',APP_NAME),font=(FONT,19,'bold'),bg=BLUE,fg='white').pack(side='right',padx=22)
        tk.Label(top,text=f"{self.current_user['name']} • {tr('مدير النظام' if self.current_user['role']=='admin' else 'مستخدم')}",font=(FONT,10),bg=BLUE,fg='#dcecff').pack(side='left',padx=12)
        tk.Button(top,text=tr('الرئيسية'),command=self.dashboard,bg='white',fg=BLUE,bd=0,font=(FONT,10,'bold')).pack(side='left',padx=5)
        tk.Button(top,text=tr('تسجيل الخروج'),command=self.login_screen,bg='#e8eef5',fg=BLUE,bd=0,font=(FONT,10,'bold')).pack(side='left',padx=5)
        tk.Button(top,text=tr('حول البرنامج'),command=self.about,bg='#dcecff',fg=BLUE,bd=0,font=(FONT,10,'bold')).pack(side='left',padx=5)
        tk.Button(top,text='⚙ '+tr('الإعدادات'),command=self.settings,bg='#fff7e0',fg=GOLD,bd=0,font=(FONT,10,'bold')).pack(side='left',padx=5)
        body=tk.Frame(self,bg=LIGHT); body.pack(fill='both',expand=True,padx=18,pady=15)
        title_label=tk.Label(body,text=title,font=(FONT,21,'bold'),bg=LIGHT,fg=TEXT)
        title_label.pack(anchor='e',pady=(0,12))
        self._shell_top=top; self._shell_body=body; self._shell_title=title_label
        return body

    def dashboard(self):
        body=self.shell(tr('لوحة التحكم الرئيسية'))
        con=db()
        counts={
          'workers':con.execute('SELECT COUNT(*) FROM workers').fetchone()[0],
          'drivers':con.execute('SELECT COUNT(*) FROM drivers').fetchone()[0],
          'vehicles':con.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0],
          'projects':con.execute('SELECT COUNT(*) FROM projects').fetchone()[0],
          'contracts':con.execute('SELECT COUNT(*) FROM contracts').fetchone()[0],
          'inventory':con.execute('SELECT COUNT(*) FROM inventory').fetchone()[0],
          'tasks':con.execute("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('مكتملة','مكتمل')").fetchone()[0],
          'expenses':con.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0],
          'revenues':con.execute('SELECT COALESCE(SUM(amount),0) FROM revenues').fetchone()[0],
          'invoices':con.execute('SELECT COALESCE(SUM(total),0) FROM invoices').fetchone()[0],
          'receipts':con.execute('SELECT COALESCE(SUM(amount),0) FROM receipts').fetchone()[0],
          'payments':con.execute('SELECT COALESCE(SUM(amount),0) FROM payments').fetchone()[0]
        }; con.close()
        cards=[('👷','العمال',counts['workers'],'workers'),('🚚','السائقون',counts['drivers'],'drivers'),('🚛','المركبات',counts['vehicles'],'vehicles'),('🏗️','المشاريع',counts['projects'],'projects'),('📄','العقود',counts['contracts'],'contracts'),('📦','أصناف المخزون',counts['inventory'],'inventory'),('📝','المهام المفتوحة',counts['tasks'],'tasks'),('🧾','إجمالي الفواتير',money(counts['invoices']),'invoices'),('💰','المقبوضات',money(counts['receipts']),'receipts'),('💸','المدفوعات',money(counts['payments']),'payments'),('📈','الإيرادات',money(counts['revenues']),'revenues'),('📉','المصروفات',money(counts['expenses']),'expenses')]
        grid=tk.Frame(body,bg=LIGHT); grid.pack(fill='both',expand=True)
        for i,(ico,n,val,key) in enumerate(cards):
            r,c=divmod(i,4); grid.rowconfigure(r,weight=1); grid.columnconfigure(c,weight=1)
            f=tk.Frame(grid,bg='white',highlightthickness=1,highlightbackground=BORDER,cursor='hand2'); f.grid(row=r,column=c,padx=5,pady=5,sticky='nsew')
            f.bind('<Button-1>',lambda e,k=key:self.crud(k))
            for w in [tk.Label(f,text=ico,font=('Segoe UI Emoji',25),bg='white'),tk.Label(f,text=tr(n),font=(FONT,11,'bold'),bg='white',fg=TEXT),tk.Label(f,text=str(val),font=(FONT,16,'bold'),bg='white',fg=BLUE)]:
                w.pack(pady=(8,2)); w.bind('<Button-1>',lambda e,k=key:self.crud(k))
        menu=tk.Frame(body,bg=LIGHT); menu.pack(fill='x',pady=7)
        buttons=[('العملاء','customers'),('الموردون','suppliers'),('المستودعات','warehouses'),('العقود','contracts'),('الصيانة','maintenance'),('الحضور','attendance'),('حركة المواد','material_moves'),('الفواتير','invoices'),('سندات قبض','receipts'),('سندات صرف','payments'),('التقارير','reports')]
        for text,key in buttons: tk.Button(menu,text=tr(text),command=(self.reports if key=='reports' else lambda k=key:self.crud(k)),bg='white',fg=TEXT,bd=0,font=(FONT,9,'bold'),padx=8,pady=7).pack(side='right',padx=2)
        if self.current_user['role']=='admin': tk.Button(menu,text=tr('المستخدمون'),command=lambda:self.crud('users'),bg='#fff7e0',fg=GOLD,bd=0,font=(FONT,9,'bold'),padx=8,pady=7).pack(side='right',padx=2)

    # ---------- v4 Administration ----------
    def permission(self,module,action='view'):
        if not self.current_user: return False
        if self.current_user['role']=='admin': return True
        con=db(); row=con.execute('SELECT * FROM permissions WHERE role=? AND module=?',(self.current_user['role'],module)).fetchone(); con.close()
        return bool(row and row['can_'+action])

    def company_editor(self):
        if self.current_user['role']!='admin': messagebox.showwarning(tr('صلاحيات'),'هذه الشاشة للمدير فقط'); return
        con=db(); r=con.execute('SELECT * FROM company_profile WHERE id=1').fetchone(); con.close()
        win=tk.Toplevel(self); win.title(tr('بيانات الشركة')); win.geometry('620x650'); win.configure(bg='white'); win.grab_set()
        fields=[('name','اسم الشركة'),('legal_name','الاسم القانوني'),('phone','الهاتف'),('email','البريد الإلكتروني'),('address','العنوان'),('tax_no','الرقم الضريبي'),('logo_path','مسار الشعار'),('footer','تذييل المستندات')]
        es={}
        for n,l in fields:
            tk.Label(win,text=tr(l),anchor='e',bg='white',fg=TEXT,font=(FONT,10,'bold')).pack(fill='x',padx=30,pady=(10,2))
            e=ttk.Entry(win,justify='right'); e.pack(fill='x',padx=30,ipady=4); e.insert(0,r[n] or ''); es[n]=e
        def browse():
            f=filedialog.askopenfilename(filetypes=[('Images','*.png;*.jpg;*.jpeg;*.ico')]);
            if f: es['logo_path'].delete(0,'end'); es['logo_path'].insert(0,f)
        ttk.Button(win,text=tr('اختيار الشعار'),command=browse).pack(pady=8)
        def save():
            con=db(); con.execute('UPDATE company_profile SET name=?,legal_name=?,phone=?,email=?,address=?,tax_no=?,logo_path=?,footer=? WHERE id=1',tuple(es[x].get().strip() for x,_ in fields)); con.commit(); con.close(); win.destroy(); self.dashboard()
        ttk.Button(win,text=tr('حفظ البيانات'),command=save).pack(fill='x',padx=30,pady=18)

    def branches(self):
        self.crud_custom('branches','الفروع',[('name','اسم الفرع'),('phone','الهاتف'),('address','العنوان'),('manager','المدير'),('active','نشط')],'name')

    def permissions_screen(self):
        if self.current_user['role']!='admin': messagebox.showwarning(tr('صلاحيات'),'هذه الشاشة للمدير فقط'); return
        win=tk.Toplevel(self); win.title(tr('صلاحيات المستخدمين')); win.geometry('950x650'); win.configure(bg=LIGHT); win.grab_set()
        modules=['customers','workers','drivers','vehicles','maintenance','projects','contracts','inventory','material_moves','purchases','expenses','revenues','invoices','receipts','payments','attendance','tasks','reports','suppliers','warehouses','stock_transfers']
        labels={m:tr(self.SPECS[m][0]) if m in self.SPECS else tr(m) for m in modules}
        role=tk.StringVar(value='user'); ttk.Combobox(win,textvariable=role,values=['user','admin'],state='readonly').pack(pady=10)
        tree=ttk.Treeview(win,columns=['module','view','add','edit','delete'],show='headings');
        for c,l in [('module','الوحدة'),('view','عرض'),('add','إضافة'),('edit','تعديل'),('delete','حذف')]: tree.heading(c,text=tr(l)); tree.column(c,width=150,anchor='center')
        tree.pack(fill='both',expand=True,padx=15,pady=10)
        vars_={}
        def load(*_):
            for i in tree.get_children(): tree.delete(i)
            con=db(); rows=con.execute('SELECT * FROM permissions WHERE role=?',(role.get(),)).fetchall(); con.close(); vars_.clear()
            for r in rows:
                vals=[r['can_view'],r['can_add'],r['can_edit'],r['can_delete']]; iid=tree.insert('', 'end',values=[labels.get(r['module'],r['module'])]+['✓' if x else '—' for x in vals]); vars_[iid]=(r['module'],vals)
        def toggle(_=None):
            s=tree.selection()
            if not s:return
            iid=s[0]; m,vals=vars_[iid]; idx=tree.identify_column(tree.winfo_pointerx()-tree.winfo_rootx())
            if idx in ('#2','#3','#4','#5'):
                j=int(idx[1:])-2; vals[j]=0 if vals[j] else 1; tree.item(iid,values=[labels.get(m,m)]+['✓' if x else '—' for x in vals]); vars_[iid]=(m,vals)
        tree.bind('<Double-1>',toggle); role.bind('<<ComboboxSelected>>',load)
        def save():
            con=db()
            for m,vals in vars_.values(): con.execute('UPDATE permissions SET can_view=?,can_add=?,can_edit=?,can_delete=? WHERE role=? AND module=?',(*vals,role.get(),m))
            con.commit(); con.close(); win.destroy()
        ttk.Button(win,text=tr('حفظ البيانات'),command=save).pack(pady=12); load()

    def crud_custom(self,key,title,fields,searchcol):
        # temporary adapter for administration tables
        old=getattr(self,'_extra_specs',{}); self._extra_specs=old.copy(); self._extra_specs[key]=(title,[(n,l,'text' if n!='active' else 'active') for n,l in fields],key,searchcol); self.SPECS[key]=self._extra_specs[key]; self.crud(key)

    def next_doc_no(self,typ):
        con=db(); r=con.execute('SELECT prefix,next_no FROM doc_sequences WHERE doc_type=?',(typ,)).fetchone(); n=f"{r['prefix']}-{int(r['next_no']):05d}"; con.execute('UPDATE doc_sequences SET next_no=next_no+1 WHERE doc_type=?',(typ,)); con.commit(); con.close(); return n

    def invoice_items_dialog(self, rid):
        if not rid: messagebox.showwarning('الفواتير','اختر فاتورة أولاً'); return
        win=tk.Toplevel(self); win.title('بنود الفاتورة'); win.geometry('900x600'); win.configure(bg='white')
        cols=('id','description','qty','unit_price','discount','tax_rate','line_total')
        tree=ttk.Treeview(win,columns=cols,show='headings'); labels={'id':'#','description':'الوصف','qty':'الكمية','unit_price':'سعر الوحدة','discount':'الخصم','tax_rate':'الضريبة %','line_total':'الإجمالي'}
        for c in cols: tree.heading(c,text=labels[c]); tree.column(c,width=90,anchor='center')
        tree.column('description',width=260); tree.pack(fill='both',expand=True,padx=12,pady=12)
        def load():
            tree.delete(*tree.get_children()); con=db(); rows=con.execute('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(rid,)).fetchall(); con.close()
            for r in rows: tree.insert('', 'end', values=[r[c] for c in cols])
        def edit(item_id=None):
            d=tk.Toplevel(win); d.title('إضافة/تعديل بند'); d.geometry('420x430'); d.configure(bg='white'); vals={}
            old=None
            if item_id:
                con=db(); old=con.execute('SELECT * FROM invoice_items WHERE id=?',(item_id,)).fetchone(); con.close()
            fields=[('description','الوصف'),('qty','الكمية'),('unit_price','سعر الوحدة'),('discount','الخصم'),('tax_rate','الضريبة %')]
            for n,l in fields:
                tk.Label(d,text=l,bg='white',anchor='e').pack(fill='x',padx=20,pady=(8,2)); e=ttk.Entry(d,justify='right'); e.pack(fill='x',padx=20); vals[n]=e
                if old: e.insert(0,str(old[n] or ''))
            def save():
                try:
                    data={n:(e.get().strip()) for n,e in vals.items()}; q=as_number(data['qty'] or 1); price=as_number(data['unit_price']); disc=as_number(data['discount'] or 0); rate=as_number(data['tax_rate'] or 0)
                    line=max(0,q*price-disc); tax=line*rate/100; total=line+tax
                    con=db()
                    if item_id: con.execute('UPDATE invoice_items SET description=?,qty=?,unit_price=?,discount=?,tax_rate=?,line_total=? WHERE id=?',(data['description'],q,price,disc,rate,total,item_id))
                    else: con.execute('INSERT INTO invoice_items(invoice_id,description,qty,unit_price,discount,tax_rate,line_total) VALUES(?,?,?,?,?,?,?)',(rid,data['description'],q,price,disc,rate,total))
                    rows=con.execute('SELECT COALESCE(SUM(qty*unit_price-discount),0), COALESCE(SUM((qty*unit_price-discount)*tax_rate/100),0) FROM invoice_items WHERE invoice_id=?',(rid,)).fetchone()
                    subtotal,tax=rows[0],rows[1]; inv=con.execute('SELECT paid FROM invoices WHERE id=?',(rid,)).fetchone(); paid=float(inv['paid'] or 0)
                    total=max(0,subtotal+tax); status='مدفوعة' if paid>=total and total>0 else ('جزئي' if paid>0 else 'غير مدفوعة')
                    con.execute('UPDATE invoices SET subtotal=?,discount=0,tax_rate=0,tax=?,total=?,status=? WHERE id=?',(subtotal,tax,total,status,rid)); con.commit(); con.close(); d.destroy(); load()
                except Exception as ex: messagebox.showerror('خطأ',str(ex),parent=d)
            ttk.Button(d,text='حفظ',command=save).pack(pady=18)
        def selected():
            s=tree.selection(); return int(tree.item(s[0])['values'][0]) if s else None
        bar=tk.Frame(win,bg='white'); bar.pack(fill='x',padx=12)
        ttk.Button(bar,text='إضافة بند',command=lambda:edit()).pack(side='right',padx=4); ttk.Button(bar,text='تعديل',command=lambda:edit(selected())).pack(side='right',padx=4)
        ttk.Button(bar,text='حذف',command=lambda:self.delete_invoice_item(selected(),load)).pack(side='right',padx=4); ttk.Button(bar,text='إغلاق',command=win.destroy).pack(side='left')
        load()

    def delete_invoice_item(self,item_id,reload):
        if not item_id:return
        con=db(); inv=con.execute('SELECT invoice_id FROM invoice_items WHERE id=?',(item_id,)).fetchone(); con.execute('DELETE FROM invoice_items WHERE id=?',(item_id,));
        if inv:
            rid=inv['invoice_id']; rows=con.execute('SELECT COALESCE(SUM(qty*unit_price-discount),0), COALESCE(SUM((qty*unit_price-discount)*tax_rate/100),0) FROM invoice_items WHERE invoice_id=?',(rid,)).fetchone(); subtotal,tax=rows[0],rows[1]; paid=float(con.execute('SELECT paid FROM invoices WHERE id=?',(rid,)).fetchone()['paid'] or 0); total=subtotal+tax; status='مدفوعة' if paid>=total and total>0 else ('جزئي' if paid>0 else 'غير مدفوعة'); con.execute('UPDATE invoices SET subtotal=?,tax=?,total=?,status=? WHERE id=?',(subtotal,tax,total,status,rid))
        con.commit(); con.close(); reload()

    def financial_statement(self, kind):
        title='كشف حساب عميل' if kind=='customer' else 'كشف حساب مورد'; win=tk.Toplevel(self); win.title(title); win.geometry('900x600'); win.configure(bg='white')
        tk.Label(win,text=title,bg='white',font=(FONT,16,'bold')).pack(pady=10); top=tk.Frame(win,bg='white'); top.pack(fill='x',padx=20)
        e=ttk.Entry(top,justify='right'); e.pack(side='right',fill='x',expand=True); ttk.Button(top,text='عرض',command=lambda:load()).pack(side='right',padx=6)
        text=tk.Text(win,font=(FONT,11),bg='#fbfdff'); text.pack(fill='both',expand=True,padx=20,pady=15)
        def load():
            name=e.get().strip(); con=db(); lines=[]; debit=credit=0
            if kind=='customer':
                invs=con.execute('SELECT invoice_no,invoice_date,total FROM invoices WHERE customer LIKE ? ORDER BY invoice_date',(f'%{name}%',)).fetchall(); recs=con.execute('SELECT receipt_no,receipt_date,amount FROM receipts WHERE customer LIKE ? ORDER BY receipt_date',(f'%{name}%',)).fetchall()
                for r in invs: debit+=r['total']; lines.append((r['invoice_date'],'فاتورة '+str(r['invoice_no']),r['total'],0))
                for r in recs: credit+=r['amount']; lines.append((r['receipt_date'],'قبض '+str(r['receipt_no']),0,r['amount']))
            else:
                pur=con.execute('SELECT item,purchase_date,total FROM purchases WHERE supplier LIKE ? ORDER BY purchase_date',(f'%{name}%',)).fetchall(); pay=con.execute('SELECT payment_no,payment_date,amount FROM payments WHERE payee LIKE ? ORDER BY payment_date',(f'%{name}%',)).fetchall()
                for r in pur: debit+=r['total']; lines.append((r['purchase_date'],'شراء '+str(r['item']),r['total'],0))
                for r in pay: credit+=r['amount']; lines.append((r['payment_date'],'صرف '+str(r['payment_no']),0,r['amount']))
            con.close(); text.delete('1.0','end'); text.insert('end',f'الحساب: {name}\n\nالتاريخ | البيان | مدين | دائن\n'+'-'*75+'\n');
            for d,desc,de,cr in lines: text.insert('end',f'{d or ""} | {desc} | {money(de)} | {money(cr)}\n')
            text.insert('end',f'\nإجمالي المدين: {money(debit)}\nإجمالي الدائن: {money(credit)}\nالرصيد: {money(debit-credit)}\n')
        load()

    def project_profitability(self):
        win=tk.Toplevel(self); win.title('ربحية المشاريع'); win.geometry('1000x620'); win.configure(bg='white'); tree=ttk.Treeview(win,columns=('project','sales','purchases','expenses','maintenance','profit'),show='headings')
        heads={'project':'المشروع','sales':'الفواتير','purchases':'المشتريات','expenses':'المصروفات','maintenance':'الصيانة','profit':'الربح'}
        for c in heads: tree.heading(c,text=heads[c]); tree.column(c,width=140,anchor='center')
        tree.pack(fill='both',expand=True,padx=15,pady=15)
        con=db(); projects=con.execute('SELECT name FROM projects ORDER BY name').fetchall()
        for p in projects:
            n=p['name']; sales=con.execute('SELECT COALESCE(SUM(total),0) FROM invoices WHERE project=?',(n,)).fetchone()[0]; pur=con.execute('SELECT COALESCE(SUM(total),0) FROM purchases WHERE project=?',(n,)).fetchone()[0]; exp=con.execute('SELECT COALESCE(SUM(amount),0) FROM expenses WHERE project=?',(n,)).fetchone()[0]; maint=con.execute('SELECT COALESCE(SUM(cost),0) FROM vehicle_maintenance WHERE project=?',(n,)).fetchone()[0]; tree.insert('', 'end', values=(n,money(sales),money(pur),money(exp),money(maint),money(sales-pur-exp-maint)))
        con.close()

    def print_invoice(self,rid):
        con=db(); r=con.execute('SELECT * FROM invoices WHERE id=?',(rid,)).fetchone(); profile=con.execute('SELECT * FROM company_profile WHERE id=1').fetchone(); con.close()
        if not r:return
        html=f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{r['invoice_no']}</title><style>body{{font-family:Arial;padding:40px;color:#173f63}}table{{width:100%;border-collapse:collapse;margin-top:30px}}td,th{{border:1px solid #ccc;padding:12px}}.head{{display:flex;justify-content:space-between}}.total{{font-size:20px;font-weight:bold;margin-top:25px}}</style></head><body><div class="head"><div><h1>{profile['name'] or APP_NAME}</h1><p>{profile['phone']} — {profile['email']}</p><p>{profile['address']}</p></div><div><h2>فاتورة</h2><p>رقم: {r['invoice_no']}</p><p>التاريخ: {r['invoice_date']}</p></div></div><hr><p><b>العميل:</b> {r['customer'] or ''}</p><p><b>المشروع:</b> {r['project'] or ''}</p><table><tr><th>الوصف</th><th>قبل الضريبة</th><th>الضريبة</th><th>الإجمالي</th></tr><tr><td>فاتورة مشروع</td><td>{r['subtotal']:.2f}</td><td>{r['tax']:.2f}</td><td>{r['total']:.2f}</td></tr></table><div class="total">الإجمالي: {money(r['total'])}</div><p>{profile['footer'] or COPYRIGHT}</p><script>window.onload=()=>window.print()</script></body></html>'''
        path=os.path.join(DATA_DIR,f"invoice_{r['invoice_no']}.html"); Path(path).write_text(html,encoding='utf-8')
        if os.name=='nt': os.startfile(path)
        else: subprocess.Popen(['xdg-open',path])

    # ---------- v6 Database Center ----------
    def database_center(self):
        if self.current_user['role']!='admin': messagebox.showwarning('صلاحيات','هذه الشاشة للمدير فقط'); return
        win=tk.Toplevel(self); win.title('مركز قاعدة البيانات'); win.geometry('980x680'); win.configure(bg=LIGHT); win.grab_set()
        tk.Label(win,text='🗄️ مركز قاعدة البيانات',bg=BLUE,fg='white',font=(FONT,18,'bold'),anchor='e').pack(fill='x',pady=15,padx=0)
        con=db(); tables=con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall(); total=sum(con.execute(f"SELECT COUNT(*) FROM [{r['name']}]").fetchone()[0] for r in tables); integrity=con.execute('PRAGMA integrity_check').fetchone()[0]; con.close()
        info=tk.Frame(win,bg='white'); info.pack(fill='x',padx=18,pady=12)
        for k,v in [('مسار قاعدة البيانات',DB_PATH),('الحجم',f"{os.path.getsize(DB_PATH)/1024/1024:.2f} MB"),('الجداول',len(tables)),('السجلات',total),('سلامة القاعدة',integrity)]:
            tk.Label(info,text=f'{k}: {v}',bg='white',fg=TEXT,font=(FONT,10,'bold'),anchor='e').pack(fill='x',padx=15,pady=4)
        bar=tk.Frame(win,bg=LIGHT); bar.pack(fill='x',padx=18,pady=5)
        def export_db():
            dest=filedialog.asksaveasfilename(title='تصدير قاعدة البيانات',defaultextension='.db',initialfile=f'moqawalat_{datetime.now():%Y%m%d_%H%M%S}.db',filetypes=[('SQLite','*.db')])
            if not dest:return
            con=sqlite3.connect(DB_PATH); b=sqlite3.connect(dest); con.backup(b); b.close(); con.close(); messagebox.showinfo('تم','تم تصدير قاعدة البيانات',parent=win)
        def import_db():
            src=filedialog.askopenfilename(title='استيراد قاعدة البيانات',filetypes=[('SQLite','*.db')])
            if not src or os.path.abspath(src)==os.path.abspath(DB_PATH): return
            if not messagebox.askyesno('تأكيد','سيتم استبدال البيانات الحالية، وسيتم إنشاء نسخة احتياطية قبل ذلك. متابعة؟',parent=win): return
            try:
                self.backup_database(silent=True,kind='before_import'); t=sqlite3.connect(src); ok=t.execute('PRAGMA integrity_check').fetchone()[0]; t.close()
                if ok!='ok': raise ValueError('قاعدة البيانات المستوردة غير سليمة')
                shutil.copy2(src,DB_PATH); messagebox.showinfo('تم','تم الاستيراد. سيتم إعادة تشغيل البرنامج.',parent=win); self.destroy(); os.execl(sys.executable,sys.executable,*sys.argv)
            except Exception as ex: messagebox.showerror('خطأ',str(ex),parent=win)
        for txt,cmd in [('💾 نسخة احتياطية',lambda:self.backup_database()),('📤 تصدير DB',export_db),('📥 استيراد DB',import_db),('📂 مجلد البيانات',self.open_data_folder)]: ttk.Button(bar,text=txt,command=cmd).pack(side='right',padx=4)
        tree=ttk.Treeview(win,columns=('created','kind','size','path'),show='headings')
        for c,h,w in [('created','التاريخ',160),('kind','النوع',110),('size','الحجم',100),('path','الملف',560)]: tree.heading(c,text=h); tree.column(c,width=w,anchor='center')
        tree.pack(fill='both',expand=True,padx=18,pady=12)
        con=db(); rows=con.execute('SELECT * FROM db_backups ORDER BY id DESC LIMIT 30').fetchall(); con.close()
        for r in rows: tree.insert('', 'end',values=(r['created_at'],r['kind'],f"{r['size_bytes']/1024:.1f} KB",r['file_path']))

    # ---------- Application Settings ----------
    def settings(self):
        body=self.shell(tr('إعدادات البرنامج'))
        outer=tk.Frame(body,bg=LIGHT); outer.pack(fill='both',expand=True)
        left=tk.Frame(outer,bg='white',highlightthickness=1,highlightbackground=BORDER); left.pack(side='left',fill='both',expand=True,padx=(0,8))
        right=tk.Frame(outer,bg='#f8fbfe',width=300); right.pack(side='right',fill='y'); right.pack_propagate(False)
        tk.Label(right,text='⚙',font=('Segoe UI Symbol',38),bg='#f8fbfe',fg=BLUE).pack(pady=(35,5))
        tk.Label(right,text=tr('مركز الإعدادات'),font=(FONT,18,'bold'),bg='#f8fbfe',fg=TEXT).pack()
        tk.Label(right,text='تحكم كامل في شكل البرنامج\nوالبيانات والطباعة والنسخ الاحتياطي',justify='center',font=(FONT,10),bg='#f8fbfe',fg='#66788a').pack(pady=12)
        for txt,cmd in [('🏢 بيانات الشركة',self.company_editor),('🏬 الفروع',self.branches),('🔐 الصلاحيات',self.permissions_screen),('🗄️ قاعدة البيانات',self.database_center),('💾 نسخة احتياطية الآن',lambda:self.backup_database()),('♻ استعادة نسخة',self.restore_database),('📁 مجلد البيانات',self.open_data_folder),('↩ إعادة الإعدادات',self.reset_settings)]:
            tk.Button(right,text=tr(txt),command=cmd,bg='white',fg=TEXT,bd=0,font=(FONT,10,'bold'),pady=9).pack(fill='x',padx=25,pady=4)
        tk.Label(right,text=f"البيانات محفوظة في:\n{DATA_DIR}",wraplength=250,justify='left',bg='#f8fbfe',fg='#7b8b99',font=(FONT,8)).pack(side='bottom',pady=20,padx=15)

        canvas=tk.Canvas(left,bg='white',highlightthickness=0); canvas.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(left,orient='vertical',command=canvas.yview); scroll.pack(side='right',fill='y'); canvas.configure(yscrollcommand=scroll.set)
        frm=tk.Frame(canvas,bg='white'); canvas.create_window((0,0),window=frm,anchor='nw',width=690); frm.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        vals={}
        sections=[
          ('🌐 اللغة والمظهر',[('language','لغة البرنامج',['العربية','English']),('theme','المظهر',['فاتح','داكن']),('font_size','حجم الخط',['9','10','11','12','13']),('compact_mode','الوضع المضغوط',['لا','نعم'])]),
          ('🏢 معلومات البرنامج',[('company_name','اسم البرنامج / الشركة',None),('owner','اسم المالك',None),('show_owner','إظهار حقوق الملكية',['نعم','لا']),('currency','العملة',['ر.س','ر.ق','$','€','د.إ'])]),
          ('📅 التاريخ والطباعة',[('date_format','تنسيق التاريخ',['YYYY-MM-DD','DD/MM/YYYY','MM/DD/YYYY']),('page_size','عدد السجلات في الشاشة',['50','100','200','500'])]),
          ('🔔 التشغيل والتنبيهات',[('notifications','التنبيهات',['نعم','لا']),('startup_page','صفحة البداية',['لوحة التحكم','التقارير']),('confirm_delete','تأكيد الحذف',['نعم','لا'])]),
          ('💾 النسخ الاحتياطي',[('auto_backup','النسخ الاحتياطي التلقائي',['نعم','لا']),('backup_interval','الفترة',['يومي','أسبوعي','شهري'])])]
        current=all_settings()
        for title,items in sections:
            tk.Label(frm,text=tr(title),anchor='e',bg='white',fg=BLUE,font=(FONT,13,'bold')).pack(fill='x',padx=25,pady=(18,5))
            box=tk.Frame(frm,bg='#f8fbfe'); box.pack(fill='x',padx=20,pady=3)
            for key,label,choices in items:
                row=tk.Frame(box,bg='#f8fbfe'); row.pack(fill='x',padx=12,pady=7)
                tk.Label(row,text=tr(label),bg='#f8fbfe',fg=TEXT,font=(FONT,10,'bold')).pack(side='right',padx=8)
                if choices:
                    e=ttk.Combobox(row,values=[tr_choice(x) for x in choices],state='readonly',justify='right',width=28); e.set(tr_choice(current.get(key,choices[0])))
                    e._internal_choices=choices
                else:
                    e=ttk.Entry(row,justify='right',width=32); e.insert(0,current.get(key,''))
                e.pack(side='left',padx=8,pady=2)
                vals[key]=e
        def save_settings():
            for key,e in vals.items():
                value=e.get().strip()
                if hasattr(e,'_internal_choices'):
                    choices=e._internal_choices
                    mapped={tr_choice(x):x for x in choices}
                    value=mapped.get(value,value)
                set_setting(key,value)
            self.apply_window_settings(); self.style()
            if get_setting('auto_backup','نعم')=='نعم': self.backup_database(silent=True)
            messagebox.showinfo(tr('تم الحفظ'),tr('تم حفظ الإعدادات وتطبيقها.'))
            self.settings()
        ttk.Button(frm,text=tr('حفظ وتطبيق الإعدادات'),command=save_settings).pack(fill='x',padx=25,pady=22,ipady=6)

    # ---------- CRUD specs ----------
    SPECS={
      'customers':('العملاء',[('name','اسم العميل','text'),('phone','الهاتف','text'),('email','البريد الإلكتروني','text'),('address','العنوان','text'),('notes','ملاحظات','multiline')],'customers','name'),
      'workers':('العمال',[('name','اسم العامل','text'),('phone','الهاتف','text'),('job','الوظيفة','text'),('project','المشروع','text'),('salary','الراتب','number'),('status','الحالة','status'),('notes','ملاحظات','multiline')],'workers','name'),
      'drivers':('السائقون',[('name','اسم السائق','text'),('phone','الهاتف','text'),('license_no','رقم الرخصة','text'),('vehicle','المركبة','text'),('plate','رقم اللوحة','text'),('project','المشروع','text'),('status','الحالة','status'),('notes','ملاحظات','multiline')],'drivers','name'),
      'vehicles':('المركبات',[('vehicle','اسم/نوع المركبة','text'),('plate','رقم اللوحة','text'),('type','التصنيف','text'),('driver','السائق','text'),('project','المشروع','text'),('model_year','سنة الصنع','text'),('status','الحالة','vehicle_status'),('notes','ملاحظات','multiline')],'vehicles','vehicle'),
      'maintenance':('صيانة المركبات',[('vehicle','المركبة','text'),('maintenance_date','تاريخ الصيانة','text'),('maintenance_type','نوع الصيانة','text'),('cost','التكلفة','number'),('odometer','العداد','number'),('supplier','الورشة/المورد','text'),('project','المشروع','text'),('notes','ملاحظات','multiline')],'vehicle_maintenance','vehicle'),
      'projects':('المشاريع',[('name','اسم المشروع','text'),('client','العميل','text'),('location','الموقع','text'),('start_date','تاريخ البداية','text'),('end_date','تاريخ النهاية','text'),('budget','الميزانية','number'),('status','الحالة','project_status'),('manager','المسؤول','text'),('notes','ملاحظات','multiline')],'projects','name'),
      'contracts':('العقود',[('contract_no','رقم العقد','text'),('project','المشروع','text'),('client','العميل','text'),('contract_date','تاريخ العقد','text'),('start_date','البداية','text'),('end_date','النهاية','text'),('value','قيمة العقد','number'),('retention','الاحتجاز','number'),('status','الحالة','contract_status'),('notes','ملاحظات','multiline')],'contracts','contract_no'),
      'inventory':('المخزون',[('item','الصنف','text'),('category','التصنيف','text'),('unit','الوحدة','text'),('quantity','الكمية الحالية','number'),('min_qty','الحد الأدنى','number'),('price','سعر الوحدة','number'),('supplier','المورد','text'),('notes','ملاحظات','multiline')],'inventory','item'),
      'material_moves':('حركة المواد',[('item','الصنف','text'),('move_type','نوع الحركة','move_type'),('qty','الكمية','number'),('unit_price','سعر الوحدة','number'),('project','المشروع','text'),('move_date','التاريخ','text'),('reference','المرجع','text'),('notes','ملاحظات','multiline')],'material_moves','item'),
      'purchases':('المشتريات',[('item','الصنف','text'),('supplier','المورد','text'),('qty','الكمية','number'),('unit_price','سعر الوحدة','number'),('total','الإجمالي','number'),('purchase_date','التاريخ','text'),('project','المشروع','text'),('notes','ملاحظات','multiline')],'purchases','item'),
      'expenses':('المصروفات',[('category','التصنيف','text'),('description','الوصف','text'),('amount','المبلغ','number'),('expense_date','التاريخ','text'),('project','المشروع','text'),('paid_by','دفع بواسطة','text'),('notes','ملاحظات','multiline')],'expenses','description'),
      'revenues':('الإيرادات',[('source','المصدر','text'),('description','الوصف','text'),('amount','المبلغ','number'),('revenue_date','التاريخ','text'),('project','المشروع','text'),('received_from','مستلم من','text'),('notes','ملاحظات','multiline')],'revenues','description'),
      'invoices':('الفواتير',[('invoice_no','رقم الفاتورة','text'),('project','المشروع','text'),('customer','العميل','text'),('invoice_date','تاريخ الفاتورة','text'),('due_date','تاريخ الاستحقاق','text'),('subtotal','قبل الضريبة','number'),('discount','الخصم','number'),('tax_rate','نسبة الضريبة','number'),('tax','الضريبة','number'),('total','الإجمالي','number'),('paid','المدفوع','number'),('status','الحالة','invoice_status'),('notes','ملاحظات','multiline')],'invoices','invoice_no'),
      'receipts':('سندات القبض',[('receipt_no','رقم السند','text'),('project','المشروع','text'),('customer','العميل','text'),('receipt_date','التاريخ','text'),('amount','المبلغ','number'),('method','طريقة التحصيل','method'),('reference','المرجع','text'),('notes','ملاحظات','multiline')],'receipts','receipt_no'),
      'payments':('سندات الصرف',[('payment_no','رقم السند','text'),('project','المشروع','text'),('payee','المستفيد','text'),('payment_date','التاريخ','text'),('amount','المبلغ','number'),('method','طريقة الدفع','method'),('reference','المرجع','text'),('notes','ملاحظات','multiline')],'payments','payment_no'),
      'attendance':('الحضور والانصراف',[('worker','العامل','text'),('project','المشروع','text'),('attendance_date','التاريخ','text'),('status','الحالة','attendance_status'),('hours','الساعات','number'),('overtime','الإضافي','number'),('notes','ملاحظات','multiline')],'attendance','worker'),
      'tasks':('المهام',[('project','المشروع','text'),('title','المهمة','text'),('assigned_to','المسؤول','text'),('due_date','الاستحقاق','text'),('status','الحالة','task_status'),('priority','الأولوية','priority'),('notes','ملاحظات','multiline')],'tasks','title'),
      'suppliers':('الموردون',[('name','اسم المورد','text'),('phone','الهاتف','text'),('email','البريد الإلكتروني','text'),('address','العنوان','text'),('tax_no','الرقم الضريبي','text'),('notes','ملاحظات','multiline')],'suppliers','name'),
      'warehouses':('المستودعات',[('name','اسم المستودع','text'),('location','الموقع','text'),('manager','المسؤول','text'),('active','نشط','active'),('notes','ملاحظات','multiline')],'warehouses','name'),
      'stock_transfers':('تحويلات المخزون',[('item','الصنف','text'),('from_warehouse','من مستودع','text'),('to_warehouse','إلى مستودع','text'),('qty','الكمية','number'),('transfer_date','التاريخ','text'),('reference','المرجع','text'),('notes','ملاحظات','multiline')],'stock_transfers','item'),
      'users':('المستخدمون',[('username','اسم المستخدم','text'),('name','الاسم','text'),('role','الصلاحية','role'),('active','نشط','active')],'users','username')
    }

    def crud(self,key):
        if not self.permission(key,'view'):
            messagebox.showwarning(tr('صلاحيات'),'ليس لديك صلاحية لعرض هذه الوحدة'); return
        if key=='users' and self.current_user['role']!='admin': messagebox.showwarning('صلاحيات','هذه الوحدة للمدير فقط'); return
        title,fields,table,searchcol=self.SPECS[key]; body=self.shell(tr(title))
        toolbar=tk.Frame(body,bg=LIGHT); toolbar.pack(fill='x',pady=(0,8))
        search=tk.Entry(toolbar,font=(FONT,11),justify='right',bd=1,relief='solid'); search.pack(side='right',fill='x',expand=True,padx=(0,6),ipady=6)
        tk.Label(toolbar,text=tr('بحث'),bg=LIGHT,fg=TEXT,font=(FONT,10,'bold')).pack(side='right',padx=5)
        ttk.Button(toolbar,text=tr('إضافة جديد'),command=lambda:self.edit_record(key,None,tree),state=('normal' if self.permission(key,'add') else 'disabled')).pack(side='right',padx=4)
        ttk.Button(toolbar,text=tr('تعديل'),command=lambda:self.edit_record(key,self.selected_id(tree),tree),state=('normal' if self.permission(key,'edit') else 'disabled')).pack(side='right',padx=4)
        ttk.Button(toolbar,text=tr('حذف'),command=lambda:self.delete_record(key,self.selected_id(tree),tree),state=('normal' if self.permission(key,'delete') else 'disabled')).pack(side='right',padx=4)
        ttk.Button(toolbar,text=tr('تصدير CSV'),command=lambda:self.export_tree(tree,title)).pack(side='left',padx=4)
        if key=='invoices': ttk.Button(toolbar,text='🖨 طباعة الفاتورة',command=lambda:self.print_invoice(self.selected_id(tree))).pack(side='left',padx=4)
        if key=='invoices': ttk.Button(toolbar,text='📋 بنود الفاتورة',command=lambda:self.invoice_items_dialog(self.selected_id(tree))).pack(side='left',padx=4)
        cols=['id']+[f[0] for f in fields]; tree=ttk.Treeview(body,columns=cols,show='headings')
        tree.heading('id',text='ID'); tree.column('id',width=50,anchor='center')
        for name,label,_ in fields: tree.heading(name,text=tr(label)); tree.column(name,width=max(95,145 if len(label)<10 else 120),anchor='center')
        tree.pack(fill='both',expand=True)
        vs=ttk.Scrollbar(body,orient='vertical',command=tree.yview); tree.configure(yscrollcommand=vs.set); vs.pack(side='left',fill='y')
        def refresh(*_):
            if getattr(self,'_search_after_id',None):
                try: self.after_cancel(self._search_after_id)
                except Exception: pass
            self._search_after_id=self.after(220, lambda: self.fill_tree(tree,key,search.get()))
        search.bind('<KeyRelease>',refresh); self.after_idle(lambda: self.fill_tree(tree,key,''))

    def fill_tree(self,tree,key,term=''):
        for x in tree.get_children(): tree.delete(x)
        _,fields,table,searchcol=self.SPECS[key]; cols=['id']+[f[0] for f in fields]
        limit=max(50,min(int(get_setting('page_size','100') or 100),500))
        con=db(); rows=con.execute(f"SELECT * FROM {table} WHERE CAST({searchcol} AS TEXT) LIKE ? ORDER BY id DESC LIMIT ?",('%'+term+'%',limit)).fetchall(); con.close()
        for r in rows: tree.insert('', 'end',values=[r[c] for c in cols])

    def selected_id(self,tree):
        s=tree.selection()
        if not s: messagebox.showwarning('اختيار','اختر سجلًا أولاً'); return None
        return tree.item(s[0])['values'][0]

    def edit_record(self,key,rid,tree):
        title,fields,table,_=self.SPECS[key]
        win=tk.Toplevel(self); win.title((tr('إضافة ') if rid is None else tr('تعديل '))+tr(title)); win.geometry('570x690'); win.configure(bg='white'); win.transient(self); win.grab_set()
        canvas=tk.Canvas(win,bg='white',highlightthickness=0); canvas.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(win,orient='vertical',command=canvas.yview); scroll.pack(side='right',fill='y'); canvas.configure(yscrollcommand=scroll.set)
        frm=tk.Frame(canvas,bg='white'); canvas.create_window((0,0),window=frm,anchor='nw',width=540); frm.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        vals={}; old=None
        if rid is not None:
            con=db(); old=con.execute(f'SELECT * FROM {table} WHERE id=?',(rid,)).fetchone(); con.close()
        for name,label,kind in fields:
            tk.Label(frm,text=tr(label),anchor='e',bg='white',fg=TEXT,font=(FONT,10,'bold')).pack(fill='x',padx=25,pady=(7,2))
            if kind=='multiline': e=tk.Text(frm,height=3,font=(FONT,10)); e.pack(fill='x',padx=25)
            elif kind in ('role','active','status','vehicle_status','project_status','contract_status','move_type','invoice_status','method','attendance_status','task_status','priority'):
                choices={
                  'role':['admin','user'],'active':['1','0'],'status':['نشط','غير نشط','جاري','مكتملة','مؤجلة','جديدة','قيد التنفيذ'],
                  'vehicle_status':['متاح','في الموقع','صيانة','خارج الخدمة'], 'project_status':['جاري','مكتمل','متوقف','مخطط'],
                  'contract_status':['نشط','منتهي','ملغي','معلق'],'move_type':['إدخال','إخراج','تسوية'], 'invoice_status':['غير مدفوعة','جزئي','مدفوعة','ملغاة'],
                  'method':['نقدي','تحويل بنكي','شيك','بطاقة'], 'attendance_status':['حاضر','غائب','إجازة','مأمورية'],
                  'task_status':['جديدة','قيد التنفيذ','مكتملة','مؤجلة'], 'priority':['منخفضة','متوسطة','عالية']
                }[kind]
                e=ttk.Combobox(frm,values=[tr_choice(x) for x in choices],state='readonly',justify='right') ; e._internal_choices=choices; e.pack(fill='x',padx=25); 
            else: e=ttk.Entry(frm,justify='right'); e.pack(fill='x',padx=25,ipady=3)
            vals[name]=e
            if old is not None and old[name] is not None:
                v=str(old[name]);
                if isinstance(e,tk.Text): e.insert('1.0',v)
                else: e.set(tr_choice(v)) if isinstance(e,ttk.Combobox) else e.insert(0,v)
        password_entry=None
        if key=='users':
            tk.Label(frm,text='كلمة المرور (مطلوبة عند الإضافة)',anchor='e',bg='white',fg=TEXT,font=(FONT,10,'bold')).pack(fill='x',padx=25,pady=(7,2))
            password_entry=ttk.Entry(frm,show='*',justify='right'); password_entry.pack(fill='x',padx=25,ipady=3)
        def save():
            data={}
            for n,e in vals.items():
                data[n]=e.get('1.0','end-1c').strip() if isinstance(e,tk.Text) else e.get().strip()
                if hasattr(e,'_internal_choices'):
                    data[n]={tr_choice(x):x for x in e._internal_choices}.get(data[n],data[n])
            try:
                con=db(); c=con.cursor()
                numeric={'salary','budget','quantity','min_qty','price','qty','unit_price','total','amount','value','retention','subtotal','discount','tax_rate','tax','paid','cost','odometer','hours','overtime'}
                for n in numeric:
                    if n in data: data[n]=as_number(data[n])
                if key=='material_moves': self.adjust_inventory(c,data,rid,old)
                if key=='purchases':
                    data['total']=data['qty']*data['unit_price']
                    if old is not None: c.execute('UPDATE inventory SET quantity=quantity-? WHERE item=?',(float(old['qty'] or 0),old['item']))
                    c.execute('INSERT INTO inventory(item,quantity,price,supplier) SELECT ?,0,?,? WHERE NOT EXISTS (SELECT 1 FROM inventory WHERE item=?)',(data['item'],data['unit_price'],data['supplier'],data['item']))
                    c.execute('UPDATE inventory SET quantity=quantity+?,price=?,supplier=? WHERE item=?',(float(data['qty'] or 0),data['unit_price'],data['supplier'],data['item']))
                if key=='invoices':
                    data['discount']=data.get('discount',0) or 0
                    data['tax_rate']=data.get('tax_rate',0) or 0
                    data['subtotal']=max(0, data.get('subtotal',0) or 0)
                    data['tax']=max(0, (data['subtotal']-data['discount']) * data['tax_rate'] / 100)
                    data['total']=max(0, data['subtotal']-data['discount']+data['tax'])
                    data['paid']=max(0, min(data.get('paid',0) or 0, data['total']))
                    data['status']='مدفوعة' if data['paid']>=data['total'] and data['total']>0 else ('جزئي' if data['paid']>0 else 'غير مدفوعة')
                if rid is None and key=='invoices' and not data.get('invoice_no'): data['invoice_no']=self.next_doc_no('invoice')
                if rid is None and key=='receipts' and not data.get('receipt_no'): data['receipt_no']=self.next_doc_no('receipt')
                if rid is None and key=='payments' and not data.get('payment_no'): data['payment_no']=self.next_doc_no('payment')
                if rid is None and key=='contracts' and not data.get('contract_no'): data['contract_no']=self.next_doc_no('contract')
                if rid is None:
                    if key=='users':
                        if not password_entry.get(): raise ValueError('أدخل كلمة المرور')
                        c.execute('INSERT INTO users(username,password_hash,name,role,active) VALUES(?,?,?,?,?)',(data['username'],hash_password(password_entry.get()),data['name'],data['role'] or 'user',int(data['active'] or 1)))
                    else:
                        cols=[n for n,_,_ in fields]; ph=','.join('?' for _ in cols); c.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({ph})",[data[x] for x in cols])
                else:
                    cols=[n for n,_,_ in fields]; sets=','.join(f'{x}=?' for x in cols); params=[data[x] for x in cols]; c.execute(f'UPDATE {table} SET {sets} WHERE id=?',params+[rid])
                    if key=='users' and password_entry and password_entry.get(): c.execute('UPDATE users SET password_hash=? WHERE id=?',(hash_password(password_entry.get()),rid))
                con.commit(); con.close(); win.destroy(); self.fill_tree(tree,key)
            except Exception as ex:
                try: con.rollback(); con.close()
                except: pass
                messagebox.showerror('تعذر الحفظ',str(ex),parent=win)
        ttk.Button(frm,text='حفظ البيانات',command=save).pack(fill='x',padx=25,pady=20)

    def adjust_inventory(self,c,data,rid,old=None):
        # Reverse the old movement on edit, then apply the new movement.
        if old is not None:
            old_item = old['item']; old_qty = float(old['qty'] or 0)
            if old['move_type'] == 'إخراج': old_qty = -old_qty
            if old['move_type'] == 'تسوية':
                # Rebuild the affected item from its previous base is ambiguous; keep edit safe by not changing it twice.
                pass
            else:
                c.execute('UPDATE inventory SET quantity=quantity-? WHERE item=?',(old_qty,old_item))
        c.execute('INSERT INTO inventory(item,quantity) SELECT ?,0 WHERE NOT EXISTS (SELECT 1 FROM inventory WHERE item=?)',(data['item'],data['item']))
        qty=float(data['qty'] or 0)
        if data['move_type']=='إخراج': qty=-qty
        if data['move_type']=='تسوية':
            c.execute('UPDATE inventory SET quantity=? WHERE item=?',(data['qty'],data['item']))
        else:
            c.execute('UPDATE inventory SET quantity=quantity+? WHERE item=?',(qty,data['item']))

    def delete_record(self,key,rid,tree):
        if rid is None:return
        if get_setting('confirm_delete','نعم')=='نعم' and not messagebox.askyesno(tr('تأكيد الحذف'),tr('هل تريد حذف السجل المحدد؟')): return
        table=self.SPECS[key][2]; con=db()
        if key=='material_moves':
            old=con.execute('SELECT * FROM material_moves WHERE id=?',(rid,)).fetchone()
            if old and old['move_type'] != 'تسوية':
                q=float(old['qty'] or 0); q = -q if old['move_type']=='إخراج' else q
                con.execute('UPDATE inventory SET quantity=quantity-? WHERE item=?',(q,old['item']))
        if key=='purchases':
            old=con.execute('SELECT * FROM purchases WHERE id=?',(rid,)).fetchone()
            if old: con.execute('UPDATE inventory SET quantity=quantity-? WHERE item=?',(float(old['qty'] or 0),old['item']))
        con.execute(f'DELETE FROM {table} WHERE id=?',(rid,)); con.commit(); con.close(); self.fill_tree(tree,key)

    def export_tree(self,tree,title):
        path=filedialog.asksaveasfilename(title='تصدير البيانات',defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f); w.writerow([tree.heading(c)['text'] for c in tree['columns']]);
            for item in tree.get_children(): w.writerow(tree.item(item)['values'])
        messagebox.showinfo(tr('تم'),tr('تم تصدير البيانات بنجاح'))

    # ---------- Reports ----------
    def reports(self):
        body=self.shell(tr('التقارير والإحصائيات'))
        con=db();
        rev=con.execute('SELECT COALESCE(SUM(amount),0) FROM revenues').fetchone()[0]
        exp=con.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]
        receipts=con.execute('SELECT COALESCE(SUM(amount),0) FROM receipts').fetchone()[0]
        payments=con.execute('SELECT COALESCE(SUM(amount),0) FROM payments').fetchone()[0]
        invoices=con.execute('SELECT COALESCE(SUM(total),0) FROM invoices').fetchone()[0]
        active=con.execute("SELECT COUNT(*) FROM projects WHERE status='جاري'").fetchone()[0]
        low=con.execute('SELECT COUNT(*) FROM inventory WHERE quantity <= min_qty').fetchone()[0]
        con.close()
        stats=[('الفواتير',invoices),('المقبوضات',receipts),('المدفوعات',payments),('الإيرادات',rev),('المصروفات',exp),('الصافي',rev-exp),('مشاريع نشطة',active),('أصناف منخفضة',low)]
        grid=tk.Frame(body,bg=LIGHT); grid.pack(fill='x')
        for i,(n,v) in enumerate(stats):
            f=tk.Frame(grid,bg='white',highlightthickness=1,highlightbackground=BORDER); f.grid(row=0,column=i,padx=3,sticky='nsew'); grid.columnconfigure(i,weight=1)
            tk.Label(f,text=tr(n),bg='white',fg='#6b7e90',font=(FONT,9)).pack(pady=(12,2)); tk.Label(f,text=money(v) if isinstance(v,(int,float)) else str(v),bg='white',fg=TEXT,font=(FONT,14,'bold')).pack(pady=(0,12))
        box=tk.Frame(body,bg='white',highlightthickness=1,highlightbackground=BORDER); box.pack(fill='both',expand=True,pady=16)
        tk.Label(box,text=tr('ملخص مالي وتشغيلي'),bg='white',fg=TEXT,font=(FONT,15,'bold')).pack(anchor='e',padx=20,pady=12)
        ttk.Button(box,text=tr('تصدير التقرير CSV'),command=self.export_report).pack(anchor='e',padx=20)
        b=tk.Frame(box,bg='white'); b.pack(anchor='e',padx=20,pady=8); ttk.Button(b,text='كشف حساب عميل',command=lambda:self.financial_statement('customer')).pack(side='right',padx=4); ttk.Button(b,text='كشف حساب مورد',command=lambda:self.financial_statement('supplier')).pack(side='right',padx=4); ttk.Button(b,text='ربحية المشاريع',command=self.project_profitability).pack(side='right',padx=4)
        text=tk.Text(box,font=(FONT,11),bg='#fbfdff',relief='flat'); text.pack(fill='both',expand=True,padx=20,pady=15)
        text.insert('1.0',f"تاريخ التقرير: {now()}\n\nإجمالي قيمة الفواتير: {money(invoices)}\nإجمالي المقبوضات: {money(receipts)}\nإجمالي المدفوعات: {money(payments)}\nالإيرادات: {money(rev)}\nالمصروفات: {money(exp)}\nصافي التدفق: {money(rev-exp)}\nالمشاريع النشطة: {active}\nأصناف تحت الحد الأدنى: {low}\n")
        text.configure(state='disabled')

    def export_report(self):
        path=filedialog.asksaveasfilename(title='حفظ التقرير',defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        con=db(); rows=[
          ('إجمالي الفواتير',con.execute('SELECT COALESCE(SUM(total),0) FROM invoices').fetchone()[0]),
          ('إجمالي المقبوضات',con.execute('SELECT COALESCE(SUM(amount),0) FROM receipts').fetchone()[0]),
          ('إجمالي المدفوعات',con.execute('SELECT COALESCE(SUM(amount),0) FROM payments').fetchone()[0]),
          ('إجمالي الإيرادات',con.execute('SELECT COALESCE(SUM(amount),0) FROM revenues').fetchone()[0]),
          ('إجمالي المصروفات',con.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]),
          ('عدد المشاريع',con.execute('SELECT COUNT(*) FROM projects').fetchone()[0]),
          ('عدد العملاء',con.execute('SELECT COUNT(*) FROM customers').fetchone()[0]),
          ('عدد العمال',con.execute('SELECT COUNT(*) FROM workers').fetchone()[0]),
          ('عدد المركبات',con.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0])]
        con.close()
        with open(path,'w',newline='',encoding='utf-8-sig') as f: csv.writer(f).writerows([['البند','القيمة']]+rows)
        messagebox.showinfo(tr('تم'),tr('تم حفظ التقرير'))

if __name__=='__main__':
    init_db(); App().mainloop()
