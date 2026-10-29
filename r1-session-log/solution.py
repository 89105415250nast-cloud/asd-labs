import sys

class Stack:
    def __init__(self):
        self._top = None
    def push(self, x):
        self._top = (x, self._top)
    def pop(self):
        if self._top is None:
            raise IndexError("pop from empty stack")
        value, self._top = self._top
        return value
    def top(self):
        if self._top is None:
            raise IndexError("top of empty stack")
        return self._top[0]
    def empty(self):
        return self._top is None
    def __iter__(self):
        node = self._top
        while node is not None:
            yield node[0]
            node = node[1]

def parse_event(raw_line, expected_tokens):
    tokens = raw_line.split()
    if not tokens or len(tokens) not in (2, 3):
        return None
    kind, name = tokens[0], tokens[1]
    if kind not in ("LOGIN", "LOGOUT"):
        return None
    if len(tokens) == 2:
        return None if expected_tokens == 3 else (kind, name, None, 2)
    if expected_tokens == 2 or not tokens[2].isdigit():
        return None
    return (kind, name, int(tokens[2]), 3)

class Analizer:
    def __init__(self, per_user=False, force_times=False):
        self.per_user = per_user
        self.stacks = {} if per_user else None
        self.stack = None if per_user else Stack()
        self.expected_tokens = 3 if force_times else None
        self.sessions_closed = 0
        self.errors = []
        self.active = self.peak = self.peak_line = 0
        self.duration_sum = self.duration_count = 0

    def _handle_login(self, name, line_no, t):
        rec = (name, line_no, t)
        if self.per_user:
            st = self.stacks.get(name) or Stack()
            self.stacks[name] = st
            st.push(rec)
        else:
            self.stack.push(rec)
        self.active += 1
        if self.active > self.peak:
            self.peak, self.peak_line = self.active, line_no

    def _handle_logout(self, name, line_no, t):
        if self.per_user:
            st = self.stacks.get(name)
            if not st or st.empty():
                self.errors.append((line_no, "logout_without_login"))
                return
            popped = st.pop()
        else:
            if self.stack.empty():
                self.errors.append((line_no, "logout_without_login"))
                return
            if self.stack.top()[0] != name:
                self.errors.append((line_no, "order_violation"))
                return
            popped = self.stack.pop()
        self.sessions_closed += 1
        self.active -= 1
        _, _, open_t = popped
        if self.expected_tokens == 3 and open_t is not None and t is not None:
            self.duration_sum += t - open_t
            self.duration_count += 1

    def process_line(self, line, line_no):
        if not line.strip():
            return
        ev = parse_event(line, self.expected_tokens)
        if ev is None:
            self.errors.append((line_no, "bad_event"))
            return
        kind, name, t, n = ev
        if self.expected_tokens is None:
            self.expected_tokens = n
        elif n != self.expected_tokens:
            self.errors.append((line_no, "bad_event"))
            return
        if kind == "LOGIN":
            self._handle_login(name, line_no, t)
        else:
            self._handle_logout(name, line_no, t)

    def finalize(self):
        if self.per_user:
            opened = [item for st in self.stacks.values() for item in st]
        else:
            opened = list(self.stack)
        opened.sort(key=lambda r: r[1])
        for _n, line_no, _t in opened:
            self.errors.append((line_no, "session_not_closed"))
        return self.errors

def main():
    args = sys.argv[1:]
    per_user = "--per-user" in args
    show_stats = "--stats" in args
    force_times = "--times" in args
    args = [a for a in args if a not in ("--per-user", "--stats", "--times")]
    if len(args) != 2:
        print("usage: session_analizer.py <input> <output> [--per-user] [--stats] [--times]")
        return
    in_path, out_path = args
    an = Analizer(per_user, force_times)
    with open(in_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for i, line in enumerate(f, 1):
            an.process_line(line, i)
    an.finalize()
    with open(out_path, "w", encoding="utf-8") as f:
        for line_no, code in an.errors:
            f.write(f"ERROR {line_no} {code}\n")
        f.write(f"SESSIONS {an.sessions_closed}\n")
        if show_stats and an.peak > 0:
            f.write(f"PEAK {an.peak} {an.peak_line}\n")
        if show_stats and an.duration_count > 0:
            f.write(f"AVG_DURATION {an.duration_sum / an.duration_count}\n")

if __name__ == "__main__":
    main()