#!/usr/bin/env python3
import sys
import time


class Stack:
    def __init__(self):
        self.d = []

    def push(self, x):
        self.d.append(x)

    def pop(self):
        return self.d.pop()

    def top(self):
        return self.d[-1]

    def empty(self):
        return not self.d


class BaseParser:
    def __init__(self):
        self.common = Stack()
        self.done = 0
        self.active = 0
        self.peak = 0
        self.peak_line = 0
        self.errs = []

    def open_sess(self, u, ln):
        self.common.push((u, ln))
        self.active += 1
        if self.active > self.peak:
            self.peak = self.active
            self.peak_line = ln

    def close_sess(self):
        self.common.pop()
        self.done += 1
        self.active -= 1

    def process(self, ln, line):
        tok = line.split()
        if not tok:
            return
        if len(tok) != 2 or tok[0] not in ("LOGIN", "LOGOUT") or not tok[1].isalnum():
            self.errs.append((ln, "bad_event"))
            return
        cmd, u = tok
        if cmd == "LOGIN":
            self.open_sess(u, ln)
            return
        if self.common.empty():
            self.errs.append((ln, "logout_without_login"))
        elif self.common.top()[0] != u:
            self.errs.append((ln, "order_violation"))
        else:
            self.close_sess()

    def finish(self):
        unfinished = []
        while not self.common.empty():
            _, l = self.common.pop()
            unfinished.append(l)
        for l in sorted(unfinished):
            self.errs.append((l, "session_not_closed"))

    def output(self):
        out = [f"ERROR {l} {c}" for l, c in self.errs]
        out.append(f"SESSIONS {self.done}")
        return "\n".join(out) + "\n"


class AdvParser:
    def __init__(self):
        self.stacks = {}
        self.done = 0
        self.active = 0
        self.peak = 0
        self.peak_line = 0
        self.errs = []

    def open_sess(self, u, ln):
        self.stacks.setdefault(u, Stack()).push(ln)
        self.active += 1
        if self.active > self.peak:
            self.peak = self.active
            self.peak_line = ln

    def close_sess(self, u):
        self.stacks[u].pop()
        self.done += 1
        self.active -= 1

    def process(self, ln, line):
        tok = line.split()
        if not tok:
            return
        if len(tok) != 2 or tok[0] not in ("LOGIN", "LOGOUT") or not tok[1].isalnum():
            self.errs.append((ln, "bad_event"))
            return
        cmd, u = tok
        if cmd == "LOGIN":
            self.open_sess(u, ln)
            return
        st = self.stacks.get(u)
        if not st or st.empty():
            self.errs.append((ln, "logout_without_login"))
        else:
            self.close_sess(u)

    def finish(self):
        unfinished = []
        for u, st in self.stacks.items():
            while not st.empty():
                unfinished.append(st.pop())
        for l in sorted(unfinished):
            self.errs.append((l, "session_not_closed"))

    def output(self):
        out = [f"ERROR {l} {c}" for l, c in self.errs]
        out.append(f"SESSIONS {self.done}")
        out.append(f"PEAK {self.peak} {self.peak_line}")
        return "\n".join(out) + "\n"


def read_lines(path):
    with open(path, "rb") as f:
        for raw in f:
            if len(raw) > 1_000_000:
                raw = raw[:1_000_000]
            yield raw.decode("utf-8", "replace").rstrip("\r\n")


def run(inp, outp, advanced=False):
    p = AdvParser() if advanced else BaseParser()
    ln = 0
    for line in read_lines(inp):
        ln += 1
        try:
            p.process(ln, line)
        except Exception:
            p.errs.append((ln, "bad_event"))
    p.finish()
    with open(outp, "w", encoding="utf-8") as f:
        f.write(p.output())


def bench(inp, advanced=False):
    t0 = time.perf_counter()
    lines = list(read_lines(inp))
    t1 = time.perf_counter()
    p = AdvParser() if advanced else BaseParser()
    ln = 0
    for line in lines:
        ln += 1
        try:
            p.process(ln, line)
        except Exception:
            p.errs.append((ln, "bad_event"))
    p.finish()
    t2 = time.perf_counter()
    print(f"read:  {t1 - t0:.6f} s")
    print(f"parse: {t2 - t1:.6f} s")


def main():
    args = sys.argv[1:]
    advanced = False
    if "--advanced" in args:
        advanced = True
        args.remove("--advanced")
    if len(args) == 2 and args[0] == "--bench":
        bench(args[1], advanced)
        return
    if len(args) != 2:
        sys.stderr.write(
            "usage: solution.py [--advanced] input.txt output.txt | "
            "--bench [--advanced] input.txt\n"
        )
        sys.exit(2)
    try:
        run(args[0], args[1], advanced)
    except OSError as e:
        sys.stderr.write(f"io error: {e}\n")
        sys.exit(1)
    except MemoryError:
        sys.stderr.write("out of memory\n")
        sys.exit(1)


if __name__ == "__main__":
    main()