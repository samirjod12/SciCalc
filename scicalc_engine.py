"""SciCalc math engine: exact-fraction expression evaluator (no GUI)."""
import math
import re
from decimal import Decimal
from fractions import Fraction


class SyntaxErr(Exception):
    pass


class MathErr(Exception):
    pass


PI = math.pi
ZERO = Fraction(0)


class Context:
    def __init__(self):
        self.angle = "DEG"  # DEG / RAD / GRA
        self.ans = Fraction(0)
        self.mem = Fraction(0)


# ---------------------------------------------------------------- numbers
def _check(v):
    if isinstance(v, float) and not math.isfinite(v):
        raise MathErr()
    return v


def norm(v, tol=1e-12, maxden=10000):
    """Snap a float that is (numerically) a simple fraction back to a Fraction."""
    if isinstance(v, float):
        _check(v)
        r = Fraction(v).limit_denominator(maxden)
        if abs(float(r) - v) <= tol * max(1.0, abs(v)):
            return r
    return v


def _isfr(*a):
    return all(isinstance(x, Fraction) for x in a)


def add(a, b):
    return a + b if _isfr(a, b) else _check(float(a) + float(b))


def sub(a, b):
    return a - b if _isfr(a, b) else _check(float(a) - float(b))


def mul(a, b):
    return a * b if _isfr(a, b) else _check(float(a) * float(b))


def div(a, b):
    if b == 0:
        raise MathErr()
    return a / b if _isfr(a, b) else _check(float(a) / float(b))


def neg(a):
    return -a


def _iroot(i, n):
    if i < 0:
        return None
    if i < 2:
        return i
    if i.bit_length() > 1000:
        return None
    r = int(round(i ** (1.0 / n)))
    for c in (r - 1, r, r + 1):
        if c >= 0 and c ** n == i:
            return c
    return None


def exact_root(x, n):
    if x < 0:
        if n % 2 == 0:
            return None
        r = exact_root(-x, n)
        return -r if r is not None else None
    a = _iroot(x.numerator, n)
    b = _iroot(x.denominator, n)
    if a is None or b is None:
        return None
    return Fraction(a, b)


def _fpow(a, b):
    try:
        if a < 0 and b != int(b):
            fr = Fraction(b).limit_denominator(1000)
            if fr.denominator % 2 == 1 and abs(float(fr) - b) < 1e-12:
                r = abs(a) ** b
                return _check(-r if fr.numerator % 2 else r)
            raise MathErr()
        if a == 0 and b <= 0:
            raise MathErr()
        return _check(float(a) ** b)
    except (OverflowError, ZeroDivisionError):
        raise MathErr()


def power(a, b):
    if _isfr(a, b):
        if b.denominator == 1:
            n = b.numerator
            if a == 0:
                if n <= 0:
                    raise MathErr()
                return Fraction(0)
            bits = max(a.numerator.bit_length(), a.denominator.bit_length(), 1)
            if abs(n) * bits <= 20000:
                return a ** n
            return _fpow(float(a), float(n))
        if a == 0:
            if b > 0:
                return Fraction(0)
            raise MathErr()
        r = exact_root(a, b.denominator)
        if r is not None:
            return power(r, Fraction(b.numerator))
    return _fpow(float(a), float(b))


def f_sqrt(x):
    if x < 0:
        raise MathErr()
    if isinstance(x, Fraction):
        r = exact_root(x, 2)
        if r is not None:
            return r
    return math.sqrt(float(x))


def f_cbrt(x):
    if isinstance(x, Fraction):
        r = exact_root(x, 3)
        if r is not None:
            return r
    return math.copysign(abs(float(x)) ** (1.0 / 3.0), float(x))


def _to_rad(ctx, x):
    x = float(x)
    if ctx.angle == "DEG":
        return math.radians(x)
    if ctx.angle == "GRA":
        return x * PI / 200.0
    return x


def _from_rad(ctx, r):
    if ctx.angle == "DEG":
        return math.degrees(r)
    if ctx.angle == "GRA":
        return r * 200.0 / PI
    return r


def f_sin(ctx, x):
    return norm(math.sin(_to_rad(ctx, x)))


def f_cos(ctx, x):
    return norm(math.cos(_to_rad(ctx, x)))


def f_tan(ctx, x):
    r = _to_rad(ctx, x)
    c = math.cos(r)
    if abs(c) < 1e-12:
        raise MathErr()
    return norm(math.sin(r) / c)


def _dom1(x):
    if abs(float(x)) > 1:
        raise MathErr()
    return float(x)


def f_asin(ctx, x):
    return norm(_from_rad(ctx, math.asin(_dom1(x))))


def f_acos(ctx, x):
    return norm(_from_rad(ctx, math.acos(_dom1(x))))


def f_atan(ctx, x):
    return norm(_from_rad(ctx, math.atan(float(x))))


def f_log(ctx, x):
    if x <= 0:
        raise MathErr()
    return norm(math.log10(float(x)))


def f_ln(ctx, x):
    if x <= 0:
        raise MathErr()
    return norm(math.log(float(x)))


def f_fact(x):
    if not isinstance(x, Fraction) or x.denominator != 1 or x < 0 or x > 170:
        raise MathErr()
    return Fraction(math.factorial(int(x)))


def _int(x):
    if not isinstance(x, Fraction) or x.denominator != 1:
        raise MathErr()
    return int(x)


def f_npr(n, r):
    n, r = _int(n), _int(r)
    if n < 0 or r < 0 or r > n:
        raise MathErr()
    return Fraction(math.perm(n, r))


def f_ncr(n, r):
    n, r = _int(n), _int(r)
    if n < 0 or r < 0 or r > n:
        raise MathErr()
    return Fraction(math.comb(n, r))


FUNCS = {
    "sin": f_sin, "cos": f_cos, "tan": f_tan,
    "asin": f_asin, "acos": f_acos, "atan": f_atan,
    "sinh": lambda c, x: norm(math.sinh(float(x))),
    "cosh": lambda c, x: norm(math.cosh(float(x))),
    "tanh": lambda c, x: norm(math.tanh(float(x))),
    "log": f_log, "ln": f_ln,
    "sqrt": lambda c, x: f_sqrt(x),
    "cbrt": lambda c, x: f_cbrt(x),
    "abs": lambda c, x: abs(x),
    "exp": lambda c, x: norm(math.exp(float(x))),
}


# ------------------------------------------------------------- calculus
def _evalf(f, env, x):
    e = dict(env)
    e["X"] = x
    return float(f(e))


def integrate(f, a, b, env):
    a, b = float(a), float(b)
    if a == b:
        return Fraction(0)
    n = 2000
    h = (b - a) / n
    s = _evalf(f, env, a) + _evalf(f, env, b)
    for i in range(1, n):
        s += (4 if i % 2 else 2) * _evalf(f, env, a + i * h)
    return norm(s * h / 3.0, 1e-9, 1000)


def derivative(f, a, env):
    a = float(a)
    h = 1e-3
    d = (-_evalf(f, env, a + 2 * h) + 8 * _evalf(f, env, a + h)
         - 8 * _evalf(f, env, a - h) + _evalf(f, env, a - 2 * h)) / (12 * h)
    return norm(d, 1e-9, 1000)


# -------------------------------------------------------------- tokenizer
_TOK = re.compile(r"(\d+\.?\d*|\.\d+)|(d/dx|[A-Za-z]+)|([+\-−×÷*/^(),!%π√∛∫²³])")


def tokenize(s):
    toks = []
    i, n = 0, len(s)
    while i < n:
        if s[i].isspace():
            i += 1
            continue
        m = _TOK.match(s, i)
        if not m:
            raise SyntaxErr()
        if m.group(1):
            toks.append(("num", Fraction(Decimal(m.group(1)))))
        elif m.group(2):
            toks.append(("name", m.group(2)))
        else:
            c = {"−": "-", "×": "*", "÷": "/"}.get(m.group(3), m.group(3))
            toks.append(("sym", c))
        i = m.end()
    return toks


# ----------------------------------------------------------------- parser
def _mk(op, l, r):
    return lambda env: op(l(env), r(env))


class Parser:
    def __init__(self, toks, ctx):
        self.t = toks
        self.i = 0
        self.ctx = ctx

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def adv(self):
        tok = self.peek()
        self.i += 1
        return tok

    def is_sym(self, s):
        k, v = self.peek()
        return k == "sym" and v == s

    def expect(self, s):
        if not self.is_sym(s):
            raise SyntaxErr()
        self.i += 1

    def close(self):
        if self.is_sym(")"):
            self.i += 1
        elif self.i >= len(self.t):
            pass
        else:
            raise SyntaxErr()

    def parse(self):
        node = self.expr()
        if self.i != len(self.t):
            raise SyntaxErr()
        return node

    def expr(self):
        left = self.term()
        while True:
            if self.is_sym("+"):
                self.i += 1
                left = _mk(add, left, self.term())
            elif self.is_sym("-"):
                self.i += 1
                left = _mk(sub, left, self.term())
            else:
                return left

    def term(self):
        left = self.factor()
        while True:
            if self.is_sym("*"):
                self.i += 1
                left = _mk(mul, left, self.factor())
            elif self.is_sym("/"):
                self.i += 1
                left = _mk(div, left, self.factor())
            else:
                return left

    def factor(self):
        if self.is_sym("-"):
            self.i += 1
            f = self.factor()
            return lambda env: neg(f(env))
        if self.is_sym("+"):
            self.i += 1
            return self.factor()
        return self.comb()

    def comb(self):
        left = self.implicit()
        while True:
            k, v = self.peek()
            if k == "name" and v in ("nPr", "nCr"):
                self.i += 1
                right = self.implicit()
                left = _mk(f_npr if v == "nPr" else f_ncr, left, right)
            else:
                return left

    def starts_operand(self):
        k, v = self.peek()
        if k == "num":
            return True
        if k == "name":
            return v not in ("nPr", "nCr")
        if k == "sym":
            return v in ("(", "π", "√", "∛", "∫")
        return False

    def implicit(self):
        left = self.power()
        while self.starts_operand():
            left = _mk(mul, left, self.power())
        return left

    def power(self):
        base = self.postfix()
        if self.is_sym("^"):
            self.i += 1
            ex = self.pow_operand()
            return lambda env: power(base(env), ex(env))
        return base

    def pow_operand(self):
        if self.is_sym("-"):
            self.i += 1
            f = self.pow_operand()
            return lambda env: neg(f(env))
        if self.is_sym("+"):
            self.i += 1
            return self.pow_operand()
        return self.power()

    def postfix(self):
        a = self.atom()
        while True:
            if self.is_sym("!"):
                self.i += 1
                a = (lambda x: lambda env: f_fact(x(env)))(a)
            elif self.is_sym("%"):
                self.i += 1
                a = (lambda x: lambda env: div(x(env), Fraction(100)))(a)
            elif self.is_sym("²"):
                self.i += 1
                a = (lambda x: lambda env: power(x(env), Fraction(2)))(a)
            elif self.is_sym("³"):
                self.i += 1
                a = (lambda x: lambda env: power(x(env), Fraction(3)))(a)
            else:
                return a

    def func_arg(self):
        if self.is_sym("("):
            self.i += 1
            e = self.expr()
            self.close()
            return e
        return self.postfix()

    def atom(self):
        k, v = self.adv()
        ctx = self.ctx
        if k is None:
            raise SyntaxErr()
        if k == "num":
            return lambda env: v
        if k == "sym":
            if v == "(":
                e = self.expr()
                self.close()
                return e
            if v == "π":
                return lambda env: PI
            if v == "√":
                a = self.func_arg()
                return lambda env: f_sqrt(a(env))
            if v == "∛":
                a = self.func_arg()
                return lambda env: f_cbrt(a(env))
            if v == "∫":
                self.expect("(")
                f = self.expr()
                self.expect(",")
                a = self.expr()
                self.expect(",")
                b = self.expr()
                self.close()
                return lambda env: integrate(f, a(env), b(env), env)
            raise SyntaxErr()
        if k == "name":
            if v in FUNCS:
                a = self.func_arg()
                fn = FUNCS[v]
                return lambda env: fn(ctx, a(env))
            if v == "pi":
                return lambda env: PI
            if v == "e":
                return lambda env: math.e
            if v == "Ans":
                return lambda env: ctx.ans
            if v == "M":
                return lambda env: ctx.mem
            if v == "X":
                return lambda env: env.get("X", ZERO)
            if v == "d/dx":
                self.expect("(")
                f = self.expr()
                self.expect(",")
                a = self.expr()
                self.close()
                return lambda env: derivative(f, a(env), env)
        raise SyntaxErr()


def calculate(text, ctx):
    toks = tokenize(text)
    if not toks:
        raise SyntaxErr()
    try:
        node = Parser(toks, ctx).parse()
        v = node({})
        if isinstance(v, float):
            _check(v)
        return norm(v)
    except (SyntaxErr, MathErr):
        raise
    except RecursionError:
        raise SyntaxErr()
    except Exception:
        raise MathErr()


# ------------------------------------------------------------- formatting
def fmt_dec(x):
    try:
        x = float(x)
    except OverflowError:
        raise MathErr()
    if x == 0:
        return "0"
    s = f"{x:.10g}"
    if "e" in s:
        m, e = s.split("e")
        return f"{m}×10^{int(e)}"
    return s


def _split_square(n):
    k, m, p = 1, n, 2
    while p * p <= m:
        while m % (p * p) == 0:
            m //= p * p
            k *= p
        p += 1
    return k, m


def closed_form(v):
    a = abs(v)
    if a == 0:
        return None
    sign = "-" if v < 0 else ""
    q = Fraction(a / PI).limit_denominator(120)
    if q != 0 and abs(float(q) * PI - a) <= 1e-10 * max(1.0, a):
        num = "π" if q.numerator == 1 else f"{q.numerator}π"
        return sign + num + (f"/{q.denominator}" if q.denominator != 1 else "")
    r2 = a * a
    fr = Fraction(r2).limit_denominator(500)
    if fr > 0 and abs(float(fr) - r2) <= 1e-10 * max(1.0, r2):
        n, d = fr.numerator, fr.denominator
        if n * d <= 10 ** 9:
            k, m = _split_square(n * d)
            if m > 1:
                g = math.gcd(k, d)
                k //= g
                d //= g
                top = (str(k) if k != 1 else "") + f"√{m}"
                return sign + top + (f"/{d}" if d != 1 else "")
    return None


def format_value(v, exact=True):
    """Return display text. Fractions come back as 'n/d' (drawn stacked by the UI)."""
    if isinstance(v, Fraction):
        if v.denominator == 1:
            s = str(v.numerator)
            return s if len(s.lstrip("-")) <= 10 else fmt_dec(v)
        n, d = v.numerator, v.denominator
        if exact and len(str(abs(n))) <= 8 and len(str(d)) <= 8:
            return f"{n}/{d}"
        return fmt_dec(v)
    if exact:
        cf = closed_form(v)
        if cf:
            return cf
    return fmt_dec(v)
