import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
import json

# ---------- CONFIG ----------
TOTAL_WEEKS = 16
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
PERIODS = 7

# ----------------------------
attendance_data = {"major": "", "weeks": TOTAL_WEEKS, "students": []}

# Keep references
notebook = None
week_trees = []
major_name_var = None
major_title_var = None

# ---------- Global flags ----------
file_modified = False
current_filename = None
auto_save_delay = 3000  # 3 seconds
auto_save_job = None
allow_save_as = False  # Allow Save As only for real edits
app_startup = True     # True during initial startup

# ---------- Utilities ----------
def make_empty_attendance():
    return [[[None]*PERIODS for _ in range(len(DAYS))] for _ in range(TOTAL_WEEKS)]

def calc_total_percent(student):
    total = TOTAL_WEEKS * len(DAYS) * PERIODS
    present = sum(sum(sum(1 for v in period if v==1) for period in day) for day in student["attendance"])
    return (present / total * 100) if total else 0.0

def calc_week_percent(student, week_index):
    total = len(DAYS) * PERIODS
    present = sum(sum(1 for v in period if v==1) for period in student["attendance"][week_index])
    return (present / total * 100) if total else 0.0

def calc_monthly_percent(student, current_week_index):
    block_start = (current_week_index // 4) * 4
    block_end = min(block_start + 4, TOTAL_WEEKS)
    total = (block_end - block_start) * len(DAYS) * PERIODS
    present = 0
    for w in range(block_start, block_end):
        present += sum(sum(1 for v in period if v==1) for period in student["attendance"][w])
    return (present / total * 100) if total else 0.0

def day_status(day_list):
    if all(v is None for v in day_list):
        return "-"
    if all(v==1 for v in day_list if v is not None):
        return "P"
    if all(v==0 for v in day_list if v is not None):
        return "A"
    return "Mix"

def ensure_attendance_shape():
    for s in attendance_data.get("students", []):
        att = s.get("attendance", [])
        while len(att) < TOTAL_WEEKS:
            att.append([[None]*PERIODS for _ in range(len(DAYS))])
        while len(att) > TOTAL_WEEKS:
            att = att[:TOTAL_WEEKS]
        for w in range(TOTAL_WEEKS):
            while len(att[w]) < len(DAYS):
                att[w].append([None]*PERIODS)
            while len(att[w]) > len(DAYS):
                att[w] = att[w][:len(DAYS)]
            for d in range(len(DAYS)):
                while len(att[w][d]) < PERIODS:
                    att[w][d].append(None)
                while len(att[w][d]) > PERIODS:
                    att[w][d] = att[w][d][:PERIODS]
        s["attendance"] = att

# ---------- Font helpers ----------
def choose_font(root):
    """Pick the first available font that supports Myanmar + English."""
    candidates = ["Pyidaungsu", "Myanmar Text", "Noto Sans Myanmar", "Noto Sans", "Segoe UI"]
    available = set(tkFont.families(root))
    for fam in candidates:
        if fam in available:
            return fam
    return "TkDefaultFont"

# ---------- Simple text dialog (Myanmar-friendly) ----------
def ask_text(title, prompt, initial=""):
    """A tiny dialog that uses our app font so Myanmar renders correctly."""
    win = tk.Toplevel(root)
    win.title(title)
    win.transient(root)

    tk.Label(win, text=prompt, font=app_font).pack(padx=12, pady=(12, 6), anchor="w")
    var = tk.StringVar(value=initial)
    entry = tk.Entry(win, textvariable=var, font=app_font, width=40)
    entry.pack(padx=12, pady=(0, 10), fill=tk.X)
    entry.icursor("end")
    entry.focus_set()

    btns = tk.Frame(win); btns.pack(padx=12, pady=(0, 12))
    result = {"value": None}

    def ok():
        result["value"] = var.get()
        win.destroy()
    def cancel():
        win.destroy()

    tk.Button(btns, text="OK", command=ok, font=app_font).pack(side=tk.LEFT, padx=4)
    tk.Button(btns, text="Cancel", command=cancel, font=app_font).pack(side=tk.LEFT, padx=4)

    win.bind("<Return>", lambda e: ok())
    win.bind("<Escape>", lambda e: cancel())

    # center
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    ww, wh = max(win.winfo_reqwidth(), 320), max(win.winfo_reqheight(), 140)
    x = (sw // 2) - (ww // 2)
    y = (sh // 2) - (wh // 2)
    win.geometry(f"{ww}x{wh}+{x}+{y}")
    win.grab_set()
    win.wait_window()
    return result["value"]

# ---------- Core actions ----------
def schedule_auto_save():
    global auto_save_job
    if auto_save_job:
        root.after_cancel(auto_save_job)
    auto_save_job = root.after(auto_save_delay, auto_save)

#---------- Auto save function ---------
def auto_save():
    global auto_save_job, file_modified, current_filename
    auto_save_job = None
    if file_modified:
        if not current_filename:
            if not allow_save_as:
                return
            filename = filedialog.asksaveasfilename(
                defaultextension=".attend",
                filetypes=[("Attendance Files", "*.attend")],
                initialfile=attendance_data.get("major","Attendance")
            )
            if not filename:
                return
            current_filename = filename
        try:
            with open(current_filename, "w", encoding="utf-8") as f:
                json.dump(attendance_data, f, ensure_ascii=False, indent=2)
            file_modified = False
            update_title()
            print(f"Auto-saved to {current_filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to auto-save:\n{e}")

#Add Student into array format
def add_student():
    global file_modified, allow_save_as
    name = ask_text("Add Student", "Enter student name :", "")
    if not name:
        return
    student = {"name": name.strip(), "attendance": make_empty_attendance()}
    attendance_data["students"].append(student)
    file_modified = True
    allow_save_as = True
    update_title()
    schedule_auto_save()
    refresh_all_weeks()

def confirm_major():
    global file_modified, allow_save_as, app_startup
    name = major_name_var.get().strip()
    if name:
        attendance_data["major"] = name
        major_title_var.set(f"{name} - Attendance")
    else:
        major_title_var.set("")
    if not app_startup:
        file_modified = True
        allow_save_as = True
        update_title()
        schedule_auto_save()

def save_file():
    global file_modified, current_filename
    attendance_data["major"] = major_name_var.get().strip()
    default_name = attendance_data.get("major","Attendance")
    filename = current_filename
    if not filename:
        filename = filedialog.asksaveasfilename(
            defaultextension=".attend",
            filetypes=[("Attendance Files", "*.attend")],
            initialfile=default_name
        )
        if not filename:
            return
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(attendance_data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Saved", f"Saved to:\n{filename}")
        file_modified = False
        current_filename = filename
        update_title()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save:\n{e}")

def load_file():
    global attendance_data, file_modified, current_filename, allow_save_as
    filename = filedialog.askopenfilename(filetypes=[("Attendance Files", "*.attend")])
    if not filename:
        return
    try:
        allow_save_as = False
        with open(filename, "r", encoding="utf-8") as f:
            attendance_data = json.load(f)
        ensure_attendance_shape()
        major_name_var.set(attendance_data.get("major",""))
        global app_startup
        confirm_major()
        refresh_all_weeks()
        current_filename = filename
        file_modified = False
        update_title()
        messagebox.showinfo("Loaded", f"Loaded from:\n{filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load:\n{e}")
    finally:
        allow_save_as = True
        app_startup = False

# ---------- Update title ----------
def update_title():
    major_name = major_name_var.get().strip()
    title = major_name + " - Attendance" if major_name else "Attendance"
    if file_modified:
        title = "*" + title
    root.title(title)

# ---------- Day editor ----------
def open_day_editor(student_idx, week_index, day_index):
    global file_modified, allow_save_as
    student = attendance_data["students"][student_idx]
    current = student["attendance"][week_index][day_index][:]

    win = tk.Toplevel(root)
    win.title(f"Edit Periods — {student['name']} — Week {week_index+1} {DAYS[day_index]}")
    win.transient(root)

    tk.Label(win, text="Select status for each period: Not Edited / Present / Absent", font=app_font)\
        .pack(padx=10, pady=(10,0), anchor="w")
    grid = tk.Frame(win)
    grid.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    options = ["Not Edited", "Present", "Absent"]
    vars_ = []

    # Table header
    for i in range(PERIODS):
        tk.Label(grid, text=f"Period {i+1}", font=(app_font.actual('family'), 10, "bold"))\
            .grid(row=0, column=i, padx=5, pady=5)

    # Dropdowns row
    for i in range(PERIODS):
        value = "Not Edited"
        if current[i] == 1:
            value = "Present"
        elif current[i] == 0:
            value = "Absent"

        v = tk.StringVar(value=value)
        cb = ttk.Combobox(grid, textvariable=v, values=options, state="readonly", width=12)
        cb.grid(row=1, column=i, padx=5, pady=5, sticky="ew")
        vars_.append(v)

    # Buttons UI
    btns = tk.Frame(win)
    btns.pack(padx=10, pady=(0,10), fill=tk.X)
    tk.Button(btns, text="All Present", command=lambda: [v.set("Present") for v in vars_], font=app_font)\
        .pack(side=tk.LEFT, padx=4)
    tk.Button(btns, text="All Absent", command=lambda: [v.set("Absent") for v in vars_], font=app_font)\
        .pack(side=tk.LEFT, padx=4)
    tk.Button(btns, text="All Not Edited", command=lambda: [v.set("Not Edited") for v in vars_], font=app_font)\
        .pack(side=tk.LEFT, padx=4)

    #--------- EDIT PERIOD WINDOW CLOSE AND SAVE INTO ARRAY FORMAT -----------
    def save_and_close():
        mapped = []
        for v in vars_:
            #PRESENT ADD
            if v.get() == "Present":
                mapped.append(1)
            #ABSENT ADD
            elif v.get() == "Absent":
                mapped.append(0)
            else:
                mapped.append(None)
        student["attendance"][week_index][day_index] = mapped
        file_modified = True
        allow_save_as = True
        update_title()
        schedule_auto_save()
        refresh_week(week_index)
        win.destroy()

    tk.Button(btns, text="Save", command=save_and_close, font=app_font).pack(side=tk.RIGHT, padx=4)
    tk.Button(btns, text="Cancel", command=win.destroy, font=app_font).pack(side=tk.RIGHT, padx=4)

    # Center window
    win.update_idletasks()
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    win_width = max(int(screen_width * 0.7), 600)
    win_height = max(win.winfo_reqheight(), 150)
    x = (screen_width // 2) - (win_width // 2)
    y = (screen_height // 2) - (win_height // 2)
    win.geometry(f"{win_width}x{win_height}+{x}+{y}")
    win.minsize(600, win_height)
    win.grab_set()

# ---------- Treeview helpers ----------
def build_week_tab(parent, week_index):
    if (week_index + 1) % 4 == 0:
        columns = ["RollNo", "Name"] + DAYS + ["Week%", "Monthly%", "Total%"]
    else:
        columns = ["RollNo", "Name"] + DAYS + ["Week%", "Total%"]

    tree = ttk.Treeview(parent, columns=columns, show="headings")
    tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)

    for col in columns:
        tree.heading(col, text=col, anchor="center")
        if col in ["Week%", "Monthly%", "Total%"]:
            tree.column(col, width=70, anchor="center", minwidth=50)
        elif col =="RollNo":
            tree.column(col, width=10, anchor="center", minwidth=10)
        elif col == "Name":
            tree.column(col, width=200, anchor="center", minwidth=100)
        else:
            tree.column(col, width=80, anchor="center", minwidth=50)

    tree.tag_configure("odd", background="#dbdbdb")
    tree.tag_configure("even", background="#ebebeb")

    tree.bind("<Double-1>", lambda e, w=week_index, t=tree: on_tree_double_click(e, w, t))
    return tree

def on_tree_double_click(event, week_index, tree):
    region = tree.identify("region", event.x, event.y)
    if region != "cell":
        return
    item_id = tree.identify_row(event.y)
    col_id = tree.identify_column(event.x)
    if not item_id or not col_id:
        return
    row_idx = int(item_id)
    col_num = int(col_id[1:])
    if col_num == 2:  # Name
        old = attendance_data["students"][row_idx]["name"]
        new = ask_text("Rename Student", "Enter new name :", initial=old)
        if new is not None and new.strip() != "":
            attendance_data["students"][row_idx]["name"] = new.strip()
            global file_modified, allow_save_as
            file_modified = True
            allow_save_as = True
            update_title()
            schedule_auto_save()
            refresh_all_weeks()
        return
    if 3 <= col_num <= 7:  # Days
        day_index = col_num - 3
        open_day_editor(row_idx, week_index, day_index)
        return

def refresh_week(week_index):
    tree = week_trees[week_index]
    if not tree:
        return
    tree.delete(*tree.get_children())

    show_monthly = (week_index + 1) % 4 == 0

    for idx, student in enumerate(attendance_data["students"]):
        values = [idx+1, student["name"]]
        for d in range(len(DAYS)):
            values.append(day_status(student["attendance"][week_index][d]))
        values.append(f"{calc_week_percent(student, week_index):.0f}%")

        if show_monthly:
            values.append(f"{calc_monthly_percent(student, week_index):.0f}%")

        values.append(f"{calc_total_percent(student):.0f}%")
        tag = "odd" if idx % 2 else "even"
        tree.insert("", "end", iid=str(idx), values=values, tags=(tag,))

def refresh_all_weeks():
    for w in range(TOTAL_WEEKS):
        refresh_week(w)

# ---------- Build UI ----------
root = tk.Tk()
root.title("Attendance — Major / Weekly View")
root.state('zoomed')

root.iconbitmap("Attendance_icon.ico")
# Fonts (Myanmar + English)
chosen_family = choose_font(root)
app_font = tkFont.Font(family=chosen_family, size=12)
root.option_add("*Font", app_font)

# Global ttk styles (Treeview + Notebook)
style = ttk.Style()
style.theme_use("default")

# Treeview font/style
style.configure("Treeview", font=app_font, rowheight=30, borderwidth=1, relief="solid")
style.configure("Treeview.Heading", font=(app_font.actual('family'), 12, "bold"), borderwidth=1, relief="solid")

# Notebook: make selected tab blue with white text
style.configure("Blue.TNotebook", tabmargins=[4, 2, 4, 0])
style.configure("Blue.TNotebook.Tab", padding=[10, 6])
style.map("Blue.TNotebook.Tab",
          background=[("selected", "#D219A7")],
          foreground=[("selected", "white")])

# Close warning
def on_close():
    if file_modified:
        if messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Do you want to save before exiting?"):
            save_file()
    root.destroy()
root.protocol("WM_DELETE_WINDOW", on_close)

# Top frame
top = tk.Frame(root)
top.pack(fill=tk.X, padx=8, pady=6)

left = tk.Frame(top); left.pack(side=tk.LEFT, anchor="w")
tk.Button(left, text="Add Student", command=add_student, font=app_font).pack(side=tk.LEFT, padx=4)
tk.Button(left, text="Save", command=save_file, font=app_font).pack(side=tk.LEFT, padx=4)
tk.Button(left, text="Load", command=load_file, font=app_font).pack(side=tk.LEFT, padx=4)

center = tk.Frame(top); center.pack(side=tk.LEFT, fill=tk.X, expand=True)
major_title_var = tk.StringVar()
tk.Label(center, textvariable=major_title_var, font=(app_font.actual('family'), 16, "bold")).pack(expand=True)

right = tk.Frame(top); right.pack(side=tk.RIGHT, anchor="e")
tk.Label(right, text="Major Name:", font=app_font).pack(side=tk.LEFT, padx=(0,6))
major_name_var = tk.StringVar(value=attendance_data.get("major",""))
tk.Entry(right, textvariable=major_name_var, width=30, font=app_font).pack(side=tk.LEFT)
tk.Button(right, text="Confirm", command=confirm_major, font=app_font).pack(side=tk.LEFT, padx=4)

# Notebook
notebook = ttk.Notebook(root, style="Blue.TNotebook")
notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
week_trees = []
for w in range(TOTAL_WEEKS):
    # each tab inherits "Blue.TNotebook.Tab" style automatically
    tab = tk.Frame(notebook)
    notebook.add(tab, text=f"Week {w+1}")
    tree = build_week_tab(tab, w)
    week_trees.append(tree)

# Keyboard shortcuts
root.bind("<Control-s>", lambda e: save_file())
root.bind("<Control-a>", lambda e: add_student())
root.bind("<Control-l>", lambda e: load_file())

# ---------- Startup ----------
def initial_title():
    major_name = major_name_var.get().strip()
    major_title_var.set(f"{major_name} - Attendance" if major_name else "")
initial_title()

refresh_all_weeks()
app_startup = False  # Now edits will trigger auto-save

root.mainloop()
