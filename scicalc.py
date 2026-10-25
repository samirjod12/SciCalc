"""SciCalc - a scientific calculator for Windows (Tkinter)."""
import re
import sys
import tkinter as tk
from tkinter import font as tkfont, messagebox
from fractions import Fraction

import scicalc_engine as eng

LCD_BG = "#d6e0cf"
LCD_FG = "#1c2a1c"
APP_BG = "#1b1e25"

# label, label_2nd, action, action_2nd, style
KEYS = [
    [("2nd", "2nd", "@shift", None, "fn"), ("DEG", "DEG", "@angle", None, "fn"),
     ("S⇔D", "S⇔D", "@sd", None, "fn"), ("◀", "◀", "@left", None, "fn"),
     ("▶", "▶", "@right", None, "fn"), ("Hist", "Hist", "@hist", None, "fn")],
    [("sin", "sin⁻¹", "sin(", "asin(", "fn"), ("cos", "cos⁻¹", "cos(", "acos(", "fn"),
     ("tan", "tan⁻¹", "tan(", "atan(", "fn"), ("log", "10ˣ", "log(", "10^(", "fn"),
     ("ln", "eˣ", "ln(", "e^(", "fn"), ("√", "∛", "√(", "∛(", "fn")],
    [("x²", "x³", "^2", "^3", "fn"), ("xʸ", "ʸ√x", "^", "^(1÷", "fn"),
     ("x⁻¹", "x⁻¹", "^(-1)", None, "fn"), ("(", "(", "(", None, "fn"),
     (")", ")", ")", None, "fn"), ("n!", "n!", "!", None, "fn")],
    [("nCr", "nPr", "nCr", "nPr", "fn"), ("∫", "d/dx", "∫(", "d/dx(", "fn"),
     ("X", ",", "X", ",", "fn"), ("|x|", "|x|", "abs(", None, "fn"),
     ("%", "%", "%", None, "fn"), ("Ans", "Ans", "Ans", None, "fn")],
    [("7", "7", "7", None, "num"), ("8", "8", "8", None, "num"), ("9", "9", "9", None, "num"),
     ("DEL", "DEL", "@del", None, "ac"), ("AC", "AC", "@ac", None, "ac"),
     ("M+", "M−", "@m+", "@m-", "fn")],
    [("4", "4", "4", None, "num"), ("5", "5", "5", None, "num"), ("6", "6", "6", None, "num"),
     ("×", "×", "×", None, "op"), ("÷", "÷", "÷", None, "op"), ("M", "M", "M", None, "fn")],
    [("1", "1", "1", None, "num"), ("2", "2", "2", None, "num"), ("3", "3", "3", None, "num"),
     ("+", "+", "+", None, "op"), ("−", "−", "-", None, "op"), ("π", "e", "π", "e", "fn")],
    [("0", "0", "0", None, "num"), (".", ".", ".", None, "num"),
     ("×10ˣ", "×10ˣ", "×10^", None, "fn"), ("(−)", "(−)", "-", None, "op"),
     ("=", "=", "@eq", None, "eq")],
]

STYLES = {  # bg, fg, active bg
    "num": ("#3b414e", "#ffffff", "#4d5566"),
    "op": ("#566074", "#ffffff", "#697590"),
    "fn": ("#272b34", "#dfe5f0", "#363c49"),
    "ac": ("#d9742f", "#ffffff", "#ec8a45"),
    "eq": ("#2e9c6c", "#ffffff", "#3bb582"),
}
TOKEN_DEL = re.compile(
    r"(asin\(|acos\(|atan\(|sinh\(|cosh\(|tanh\(|sin\(|cos\(|tan\(|log\(|ln\(|abs\(|"
    r"d/dx\(|Ans|nPr|nCr|10\^\(|e\^\(|∫\(|√\(|∛\(|.)$", re.S)
OPERATOR_START = "+-−×÷^!%"


class App:
    def __init__(self, root):
        self.root = root
        self.ctx = eng.Context()
        self.exact = True
        self.shift = False
        self.fresh = False
        self.history = []
        self.hist_idx = None
        self.result_text = ""
        self.result_err = False
        self.font_delta = 0
        self.hist_win = None
        self.buttons = []

        fam = "Segoe UI" if sys.platform.startswith("win") else "DejaVu Sans"
        self.f_btn = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_in = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "DejaVu Sans Mono", size=20)
        self.f_res = tkfont.Font(family=fam, size=30)
        self.f_stat = tkfont.Font(family=fam, size=9, weight="bold")
        self.f_tool = tkfont.Font(family=fam, size=9)

        root.title("SciCalc – Scientific Calculator")
        root.configure(bg=APP_BG)
        root.minsize(340, 520)
        root.geometry("420x680")
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=2)
        root.grid_rowconfigure(2, weight=5)

        self.build_menu()
        self.build_toolbar()
        self.build_display()
        self.build_keys()
        self.bind_keys()
        self.refresh_status()
        root.bind("<Configure>", self.on_resize)
        self.text.focus_set()

    # ------------------------------------------------------------- UI build
    def build_menu(self):
        r = self.root
        m = tk.Menu(r)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Copy expression", command=self.copy_expr)
        f.add_command(label="Copy result", command=self.copy_result)
        f.add_command(label="Copy expression = result", command=self.copy_all)
        f.add_command(label="Paste", command=self.paste)
        f.add_separator()
        f.add_command(label="Exit", command=r.destroy)
        m.add_cascade(label="File", menu=f)

        s = tk.Menu(m, tearoff=0)
        self.angle_var = tk.StringVar(value="DEG")
        for a, name in (("DEG", "Degree"), ("RAD", "Radian"), ("GRA", "Gradian")):
            s.add_radiobutton(label=name, value=a, variable=self.angle_var,
                              command=lambda: self.set_angle(self.angle_var.get()))
        s.add_separator()
        self.exact_var = tk.BooleanVar(value=True)
        s.add_checkbutton(label="Natural results (fractions, √, π)", variable=self.exact_var,
                          command=self.toggle_sd)
        s.add_separator()
        s.add_command(label="Larger text   Ctrl +", command=lambda: self.change_font(2))
        s.add_command(label="Smaller text   Ctrl −", command=lambda: self.change_font(-2))
        self.top_var = tk.BooleanVar(value=False)
        s.add_checkbutton(label="Always on top", variable=self.top_var,
                          command=lambda: r.attributes("-topmost", self.top_var.get()))
        m.add_cascade(label="Settings", menu=s)

        h = tk.Menu(m, tearoff=0)
        h.add_command(label="History", command=self.show_history)
        h.add_command(label="Keyboard & function guide", command=self.show_guide)
        h.add_command(label="About", command=lambda: messagebox.showinfo(
            "About SciCalc", "SciCalc 1.0\nAn independent scientific calculator for Windows."))
        m.add_cascade(label="Help", menu=h)
        r.config(menu=m)

    def build_toolbar(self):
        tb = tk.Frame(self.root, bg=APP_BG)
        tb.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 0))
        for text, cmd in (("Copy expr", self.copy_expr), ("Copy result", self.copy_result),
                          ("Copy all", self.copy_all), ("Paste", self.paste),
                          ("A+", lambda: self.change_font(2)), ("A−", lambda: self.change_font(-2))):
            tk.Button(tb, text=text, command=cmd, font=self.f_tool, bg="#2c313b", fg="#dfe5f0",
                      activebackground="#3a4150", activeforeground="#fff", relief="flat",
                      bd=0, padx=8, pady=2, highlightthickness=0).pack(side="left", padx=2)

    def build_display(self):
        d = tk.Frame(self.root, bg=LCD_BG, bd=0)
        d.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        self.status = tk.Label(d, text="", bg=LCD_BG, fg="#4a5a48", font=self.f_stat, anchor="w")
        self.status.pack(fill="x", padx=8, pady=(4, 0))
        self.text = tk.Text(d, height=2, wrap="char", font=self.f_in, bg=LCD_BG, fg=LCD_FG,
                            relief="flat", bd=0, highlightthickness=0, insertwidth=2,
                            insertbackground=LCD_FG, undo=False, padx=8, pady=4)
        self.text.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(d, bg=LCD_BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.draw_result())

    def build_keys(self):
        kf = tk.Frame(self.root, bg=APP_BG)
        kf.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 8))
        for c in range(6):
            kf.grid_columnconfigure(c, weight=1, uniform="k")
        for r, row in enumerate(KEYS):
            kf.grid_rowconfigure(r, weight=1, uniform="r")
            col = 0
            for spec in row:
                label, label2, a1, a2, style = spec
                bg, fg, abg = STYLES[style]
                b = tk.Button(kf, text=label, font=self.f_btn, bg=bg, fg=fg,
                              activebackground=abg, activeforeground=fg, relief="flat",
                              bd=0, highlightthickness=0, takefocus=0,
                              command=lambda s=spec: self.press(s))
                span = 2 if a1 == "@eq" else 1
                b.grid(row=r, column=col, columnspan=span, sticky="nsew", padx=2, pady=2)
                self.buttons.append((b, spec, bg, fg))
                col += span

    def bind_keys(self):
        t = self.text
        t.bind("<KeyPress>", self.on_key)
        t.bind("<Button-1>", lambda e: setattr(self, "fresh", False))
        for seq in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.root.bind(seq, lambda e: self.change_font(2))
        for seq in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.root.bind(seq, lambda e: self.change_font(-2))
        self.root.bind("<Control-Shift-C>", lambda e: self.copy_all())

    # ------------------------------------------------------------ resizing
    def on_resize(self, event):
        if event.widget is self.root:
            self.rescale()

    def rescale(self):
        w, h = self.root.winfo_width(), self.root.winfo_height()
        s = max(0.6, min(w / 420.0, h / 680.0))
        self.f_btn.configure(size=max(8, int(13 * s)))
        self.f_in.configure(size=max(10, int(20 * s) + self.font_delta))
        self.f_res.configure(size=max(12, int(30 * s) + self.font_delta))
        self.f_stat.configure(size=max(7, int(9 * s)))
        self.draw_result()

    def change_font(self, d):
        self.font_delta = max(-8, min(40, self.font_delta + d))
        self.rescale()

    # ------------------------------------------------------------- display
    def refresh_status(self):
        parts = [self.ctx.angle, "NATURAL" if self.exact else "DECIMAL"]
        if self.shift:
            parts.append("2nd")
        if self.ctx.mem != 0:
            parts.append("M")
        self.status.config(text="   ".join(parts))
        for b, spec, bg, fg in self.buttons:
            if spec[2] == "@angle":
                b.config(text=self.ctx.angle)
            elif spec[2] == "@shift":
                b.config(bg="#e8c13a" if self.shift else bg, fg="#000" if self.shift else fg)
            elif spec[3] and spec[0] != spec[1]:
                b.config(text=spec[1] if self.shift else spec[0],
                         fg="#ffd76a" if self.shift else fg)

    def draw_result(self):
        c = self.canvas
        c.delete("all")
        t = self.result_text
        if not t:
            return
        w = max(c.winfo_width(), 50)
        h = max(c.winfo_height(), 20)
        f = self.f_res
        color = "#a02020" if self.result_err else LCD_FG
        pad = 12
        if "/" in t and not self.result_err:
            num, den = t.split("/", 1)
            ww = max(f.measure(num), f.measure(den)) + 10
            cx, cy = w - pad - ww / 2, h / 2
            c.create_text(cx, cy - 2, text=num, font=f, fill=color, anchor="s")
            c.create_text(cx, cy + 2, text=den, font=f, fill=color, anchor="n")
            c.create_line(cx - ww / 2, cy, cx + ww / 2, cy, fill=color,
                          width=max(1, int(f.cget("size") / 12)))
        else:
            c.create_text(w - pad, h / 2, text=t, font=f, fill=color, anchor="e")

    def show_result(self):
        try:
            self.result_text = eng.format_value(self.last, self.exact)
            self.result_err = False
        except eng.MathErr:
            self.result_text, self.result_err = "Math ERROR", True
        self.draw_result()

    def show_error(self, msg):
        self.result_text, self.result_err = msg, True
        self.draw_result()

    # --------------------------------------------------------------- input
    def clear_result(self):
        self.result_text = ""
        self.draw_result()

    def insert_text(self, s):
        if self.fresh:
            self.fresh = False
            if s[0] in OPERATOR_START:
                self.text.delete("1.0", "end")
                self.text.insert("1.0", "Ans")
            else:
                self.text.delete("1.0", "end")
            self.clear_result()
        elif self.result_err:
            self.clear_result()
        self.text.insert("insert", s)
        self.text.see("insert")

    def on_key(self, event):
        if event.state & 0x4:  # Ctrl combos (copy, paste, select all...) use defaults
            return None
        ks, ch = event.keysym, event.char
        if ks in ("Return", "KP_Enter"):
            self.evaluate()
            return "break"
        if ks == "Escape":
            self.all_clear()
            return "break"
        if ks == "BackSpace":
            self.delete()
            return "break"
        if ks == "Up":
            self.browse_history(-1)
            return "break"
        if ks == "Down":
            self.browse_history(1)
            return "break"
        if ks in ("Left", "Right", "Home", "End", "Delete"):
            if self.fresh:
                self.fresh = False
                self.clear_result()
            return None
        if ch == "=":
            self.evaluate()
            return "break"
        if ch and ch.isprintable():
            self.insert_text({"*": "×", "/": "÷"}.get(ch, ch))
            return "break"
        return "break" if ks == "Tab" else None

    def press(self, spec):
        label, label2, a1, a2, style = spec
        action = a2 if (self.shift and a2) else a1
        if action == "@shift":
            self.shift = not self.shift
            self.refresh_status()
            return
        was_shift = self.shift
        self.run(action)
        if was_shift:
            self.shift = False
        self.refresh_status()
        self.text.focus_set()

    def run(self, a):
        if not a.startswith("@"):
            self.insert_text(a)
            return
        if a == "@eq":
            self.evaluate()
        elif a == "@ac":
            self.all_clear()
        elif a == "@del":
            self.delete()
        elif a == "@angle":
            order = ["DEG", "RAD", "GRA"]
            self.set_angle(order[(order.index(self.ctx.angle) + 1) % 3])
        elif a == "@sd":
            self.exact_var.set(not self.exact)
            self.toggle_sd()
        elif a in ("@left", "@right"):
            if self.fresh:
                self.fresh = False
                self.clear_result()
            self.text.mark_set("insert", "insert-1c" if a == "@left" else "insert+1c")
        elif a == "@hist":
            self.show_history()
        elif a in ("@m+", "@m-"):
            expr = self.text.get("1.0", "end").strip()
            if expr and not self.fresh:
                self.evaluate()
            if self.fresh and not self.result_err:
                self.ctx.mem = (eng.add if a == "@m+" else eng.sub)(self.ctx.mem, self.last)
                self.ctx.mem = eng.norm(self.ctx.mem) if isinstance(self.ctx.mem, float) else self.ctx.mem

    def set_angle(self, a):
        self.ctx.angle = a
        self.angle_var.set(a)
        self.refresh_status()

    def toggle_sd(self):
        self.exact = self.exact_var.get()
        if self.result_text and not self.result_err and hasattr(self, "last"):
            self.show_result()
        self.refresh_status()

    def all_clear(self):
        self.text.delete("1.0", "end")
        self.fresh = False
        self.hist_idx = None
        self.clear_result()

    def delete(self):
        if self.fresh:
            self.fresh = False
            self.clear_result()
        before = self.text.get("1.0", "insert")
        if not before:
            return
        m = TOKEN_DEL.search(before)
        n = len(m.group(0)) if m else 1
        self.text.delete(f"insert-{n}c", "insert")

    # ---------------------------------------------------------- evaluation
    def evaluate(self):
        expr = self.text.get("1.0", "end").strip()
        if not expr or self.fresh:
            return
        try:
            v = eng.calculate(expr, self.ctx)
            self.last = v
            self.ctx.ans = v
            self.show_result()
            if not self.result_err:
                self.history.append((expr, self.result_text))
            self.fresh = True
            self.hist_idx = None
        except eng.SyntaxErr:
            self.show_error("Syntax ERROR")
            self.fresh = False
        except eng.MathErr:
            self.show_error("Math ERROR")
            self.fresh = False
        self.refresh_status()

    def browse_history(self, d):
        if not self.history:
            return
        if self.hist_idx is None:
            idx = len(self.history) - 1 if d < 0 else None
        else:
            idx = self.hist_idx + d
            if idx < 0:
                idx = 0
            if idx >= len(self.history):
                idx = None
        self.hist_idx = idx
        self.text.delete("1.0", "end")
        if idx is not None:
            self.text.insert("1.0", self.history[idx][0])
        self.fresh = False
        self.clear_result()

    # ----------------------------------------------------- copy and paste
    def _clip(self, s):
        self.root.clipboard_clear()
        self.root.clipboard_append(s)

    def copy_expr(self):
        self._clip(self.text.get("1.0", "end").strip())

    def copy_result(self):
        if self.result_text:
            self._clip(self.result_text)

    def copy_all(self):
        e = self.text.get("1.0", "end").strip()
        if e and self.result_text:
            self._clip(f"{e} = {self.result_text}")

    def paste(self):
        try:
            s = self.root.clipboard_get().replace("\n", "").strip()
        except tk.TclError:
            return
        if s:
            self.insert_text(s)

    # ------------------------------------------------------------- windows
    def show_history(self):
        if self.hist_win and self.hist_win.winfo_exists():
            self.hist_win.lift()
            return
        w = tk.Toplevel(self.root)
        w.title("History")
        w.geometry("360x300")
        lb = tk.Listbox(w, font=self.f_tool, activestyle="none")
        lb.pack(fill="both", expand=True)
        for e, r in reversed(self.history):
            lb.insert("end", f"{e}  =  {r}")
        items = list(reversed(self.history))

        def pick(_):
            sel = lb.curselection()
            if sel:
                self.text.delete("1.0", "end")
                self.text.insert("1.0", items[sel[0]][0])
                self.fresh = False
                self.clear_result()
                self.text.focus_set()

        lb.bind("<Double-Button-1>", pick)
        self.hist_win = w

    def show_guide(self):
        messagebox.showinfo("Guide", (
            "Keyboard: type numbers and + - * / ^ ( ) ! %\n"
            "Enter or =  calculate     Esc  clear     Up/Down  previous entries\n"
            "You can type: sin( cos( tan( asin( acos( atan( log( ln( sqrt( abs( pi e\n"
            "nCr / nPr : 5nCr2     Integral: ∫(X^2,0,1)     Derivative: d/dx(X^3,2)\n"
            "Ans = last result, M = memory (M+ / 2nd M+ = M−)\n"
            "2nd + a key  = the gold function printed on it\n"
            "S⇔D switches between natural (fractions, √, π) and decimal results.\n"
            "DEG/RAD/GRA button cycles the angle unit."))


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    try:
        import os
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        root.iconbitmap(os.path.join(base, "scicalc.ico"))
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
