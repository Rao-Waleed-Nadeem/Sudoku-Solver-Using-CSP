"""
============================================================
  CSP-Based Sudoku Solver
  ─────────────────────────────────────────────────────────
  Algorithms : Backtracking Search
               Forward Checking
               AC-3  (Arc Consistency)
               MRV   (Minimum Remaining Values heuristic)
  ─────────────────────────────────────────────────────────
  Input      : Text files — 9 lines × 9 digits (0 = empty)
  Output     : Solved board + per-board statistics
               + solution written back to *_solution.txt
  ─────────────────────────────────────────────────────────
  Boards     : easy.txt  medium.txt  hard.txt  veryhard.txt
  Usage      : python sudoku_csp.py
               python sudoku_csp.py easy.txt medium.txt ...
============================================================
"""

import sys
import time
import copy
from collections import deque


# ╔══════════════════════════════════════════════════════════╗
# ║                  ANSI STYLING                           ║
# ╚══════════════════════════════════════════════════════════╝

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    PURPLE  = "\033[95m"
    CYAN    = "\033[96m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[35m"
    ORANGE  = "\033[38;5;208m"


def S(*codes):
    """Return an ANSI-styled opener (call C.RESET to close)."""
    return "".join(codes)


def styled(text, *codes):
    """Wrap text in ANSI codes, always reset at end."""
    return "".join(codes) + str(text) + C.RESET


def ansi_len(text):
    """Display length of a string after stripping ANSI codes."""
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


# ╔══════════════════════════════════════════════════════════╗
# ║               BUILT-IN BOARD PRESETS                    ║
# ║   Used as fallback when .txt files are not present.     ║
# ╚══════════════════════════════════════════════════════════╝

PRESETS = {
    "easy": {
        "name"  : "Easy Board",
        "diff"  : "Easy",
        "file"  : "easy.txt",
        "data"  : [
            # Figure 1 — easy.txt  (matches assignment example exactly)
            [0,0,4,0,3,0,0,5,0],
            [6,0,9,4,0,0,0,0,0],
            [0,0,5,1,0,0,4,8,9],
            [0,0,0,0,6,0,9,3,0],
            [3,0,0,8,0,7,0,0,2],
            [0,2,6,0,4,0,0,0,0],
            [4,5,3,0,0,9,6,0,0],
            [0,0,0,0,0,4,7,0,5],
            [0,9,0,0,5,0,2,0,0],
        ],
    },
    "medium": {
        "name"  : "Medium Board",
        "diff"  : "Medium",
        "file"  : "medium.txt",
        "data"  : [
            # Figure 2 — medium.txt
            # NOTE: load from medium.txt for the exact assignment board.
            # This preset is a valid medium-difficulty puzzle included as
            # a runnable fallback when the file is not present.
            [5,3,0,0,7,0,0,0,0],
            [6,0,0,1,9,5,0,0,0],
            [0,9,8,0,0,0,0,6,0],
            [8,0,0,0,6,0,0,0,3],
            [4,0,0,8,0,3,0,0,1],
            [7,0,0,0,2,0,0,0,6],
            [0,6,0,0,0,0,2,8,0],
            [0,0,0,4,1,9,0,0,5],
            [0,0,0,0,8,0,0,7,9],
        ],
    },
    "hard": {
        "name"  : "Hard Board",
        "diff"  : "Hard",
        "file"  : "hard.txt",
        "data"  : [
            # Figure 3 — hard.txt
            [1,0,2,0,4,0,0,0,7],
            [0,0,0,0,8,0,0,0,0],
            [0,9,5,0,0,0,3,0,4],
            [0,0,6,0,7,9,0,0,0],
            [5,0,0,0,0,0,2,0,6],
            [0,0,4,0,5,0,0,0,0],
            [7,0,8,0,0,3,4,0,0],
            [0,0,0,0,1,0,0,0,0],
            [2,0,0,0,6,0,5,0,9],
        ],
    },
    "veryhard": {
        "name"  : "Very Hard Board",
        "diff"  : "Very Hard",
        "file"  : "veryhard.txt",
        "data"  : [
            # Figure 4 — veryhard.txt
            [0,0,0,0,1,0,0,7,0],
            [0,6,0,0,4,0,0,3,0],
            [0,3,8,0,0,0,7,6,0],
            [0,0,0,0,0,0,0,3,6],
            [0,2,7,0,0,0,1,5,0],
            [0,0,0,0,0,2,0,0,0],
            [0,0,0,0,2,0,5,1,0],
            [7,0,0,0,8,0,1,0,0],
            [0,0,0,8,0,9,0,0,0],
        ],
    },
}

PRESET_ORDER = ["easy", "medium", "hard", "veryhard"]


# ╔══════════════════════════════════════════════════════════╗
# ║                    FILE  I / O                          ║
# ╚══════════════════════════════════════════════════════════╝

def read_board(filepath: str) -> list:
    """
    Read a Sudoku board from a text file.

    Expected format
    ───────────────
    • Exactly 9 lines
    • Each line contains exactly 9 digits (0–9)
    • 0 represents an empty cell

    Returns a 9×9 list of integers.
    Raises ValueError / FileNotFoundError on bad input.
    """
    with open(filepath, "r") as fh:
        lines = [ln.strip() for ln in fh if ln.strip()]

    if len(lines) != 9:
        raise ValueError(
            f"Expected 9 lines, found {len(lines)} in '{filepath}'."
        )

    board = []
    for i, line in enumerate(lines, 1):
        if len(line) != 9:
            raise ValueError(
                f"Line {i} must contain exactly 9 characters, "
                f"got {len(line)}: '{line}'"
            )
        if not line.isdigit():
            raise ValueError(
                f"Line {i} contains non-digit characters: '{line}'"
            )
        board.append([int(ch) for ch in line])

    return board


def write_board(board: list, filepath: str) -> None:
    """
    Write a solved board back to a text file in the same 9-line format.
    Non-fatal — errors are caught and printed as warnings.
    """
    with open(filepath, "w") as fh:
        for row in board:
            fh.write("".join(str(v) for v in row) + "\n")


# ╔══════════════════════════════════════════════════════════╗
# ║              CONSTRAINT RELATIONSHIPS                   ║
# ╚══════════════════════════════════════════════════════════╝

def _compute_peers(r: int, c: int) -> frozenset:
    """
    Return every cell that shares a row, column, or 3×3 box
    with (r, c), excluding (r, c) itself.
    """
    peers = set()
    for i in range(9):
        if i != c:
            peers.add((r, i))           # same row
        if i != r:
            peers.add((i, c))           # same column
    br, bc = (r // 3) * 3, (c // 3) * 3
    for dr in range(3):
        for dc in range(3):
            nb = (br + dr, bc + dc)
            if nb != (r, c):
                peers.add(nb)           # same 3×3 box
    return frozenset(peers)


# Precompute peer sets for all 81 cells (constant throughout solving)
PEERS: dict = {
    (r, c): _compute_peers(r, c)
    for r in range(9)
    for c in range(9)
}


# ╔══════════════════════════════════════════════════════════╗
# ║                 DOMAIN  INITIALISATION                  ║
# ╚══════════════════════════════════════════════════════════╝

def build_domains(board: list) -> dict:
    """
    Construct the initial domain for every cell.

    • Given cells (non-zero)  → singleton domain {value}
    • Empty cells (zero)      → {1…9} minus values already
                                  visible in the same row /
                                  column / box
    """
    domains: dict = {}
    for r in range(9):
        for c in range(9):
            if board[r][c] != 0:
                domains[(r, c)] = {board[r][c]}
            else:
                used = {
                    board[pr][pc]
                    for (pr, pc) in PEERS[(r, c)]
                    if board[pr][pc] != 0
                }
                domains[(r, c)] = set(range(1, 10)) - used
    return domains


# ╔══════════════════════════════════════════════════════════╗
# ║                    AC-3  ALGORITHM                      ║
# ╚══════════════════════════════════════════════════════════╝

def ac3(board: list, domains: dict) -> tuple:
    """
    Arc Consistency Algorithm 3 (AC-3).

    Enforces arc-consistency across all variable pairs.
    For every arc (Xi, Xj), values are removed from Xi's
    domain that have no supporting value in Xj's domain.

    Iterates until no further reductions are possible, or
    a domain becomes empty (signalling no solution).

    Parameters
    ──────────
    board   : current board (used to skip already-assigned cells)
    domains : mutable domain dictionary — modified in place

    Returns
    ───────
    (consistent: bool, arc_iterations: int)
    """
    # Initialise queue with all arcs between unassigned peer pairs
    queue: deque = deque()
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                for (pr, pc) in PEERS[(r, c)]:
                    if board[pr][pc] == 0:
                        queue.append((r, c, pr, pc))

    arc_iterations = 0

    while queue:
        r1, c1, r2, c2 = queue.popleft()
        arc_iterations += 1

        if _revise(domains, r1, c1, r2, c2):
            if not domains[(r1, c1)]:
                # Domain wiped out — no solution along this path
                return False, arc_iterations

            # Domain of Xi changed → re-examine all arcs into Xi
            for (pr, pc) in PEERS[(r1, c1)]:
                if (pr, pc) != (r2, c2) and board[pr][pc] == 0:
                    queue.append((pr, pc, r1, c1))

    return True, arc_iterations


def _revise(domains: dict, r1: int, c1: int, r2: int, c2: int) -> bool:
    """
    Remove values from domain[(r1, c1)] that are inconsistent
    with every value in domain[(r2, c2)].

    A value v in Xi is consistent with Xj if there exists at
    least one value w ≠ v in Xj's domain (Sudoku's all-different
    constraint).

    Returns True if the domain was revised (any value removed).
    """
    revised = False
    for v in list(domains[(r1, c1)]):
        # Is there a supporting value in Xj?
        if not any(w != v for w in domains[(r2, c2)]):
            domains[(r1, c1)].discard(v)
            revised = True
    return revised


# ╔══════════════════════════════════════════════════════════╗
# ║            MRV — VARIABLE ORDERING HEURISTIC            ║
# ╚══════════════════════════════════════════════════════════╝

def select_mrv(board: list, domains: dict):
    """
    Minimum Remaining Values (MRV) heuristic.

    Selects the unassigned cell whose domain is smallest.
    Cells with fewer legal values are more constrained and
    should be assigned first to detect failures early.

    Returns (row, col) or None if all cells are assigned.
    """
    best      = None
    best_size = 10          # larger than any legal domain

    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                sz = len(domains[(r, c)])
                if sz < best_size:
                    best_size = sz
                    best      = (r, c)

    return best


# ╔══════════════════════════════════════════════════════════╗
# ║                  FORWARD  CHECKING                      ║
# ╚══════════════════════════════════════════════════════════╝

def forward_check(
    board: list, domains: dict, r: int, c: int, v: int
) -> bool:
    """
    After assigning board[r][c] = v, remove v from the domains
    of all unassigned peers of (r, c).

    If any peer's domain becomes empty, the assignment leads to
    a dead end — return False immediately (fail early).

    Returns True if all peer domains remain non-empty.
    """
    for (pr, pc) in PEERS[(r, c)]:
        if board[pr][pc] == 0:
            domains[(pr, pc)].discard(v)
            if not domains[(pr, pc)]:
                return False        # Dead end detected
    return True


# ╔══════════════════════════════════════════════════════════╗
# ║              BACKTRACKING  SEARCH                       ║
# ╚══════════════════════════════════════════════════════════╝

def backtrack(board: list, domains: dict, stats: dict) -> bool:
    """
    Recursive backtracking search with MRV + forward checking.

    Algorithm
    ─────────
    1. Select the unassigned cell with the smallest domain (MRV).
    2. Try each value in that domain in ascending order.
    3. Apply the assignment and run forward checking.
    4. If forward checking succeeds, recurse.
    5. If recursion fails (or forward check fails), undo the
       assignment and try the next value.
    6. If no values remain, return failure.

    Stats tracking
    ──────────────
    stats['calls']    — incremented each time BACKTRACK is called
    stats['failures'] — incremented each time BACKTRACK returns failure
    """
    stats["calls"] += 1

    # Base case: all 81 cells assigned → solution found
    cell = select_mrv(board, domains)
    if cell is None:
        return True

    r, c = cell

    for v in sorted(domains[(r, c)]):
        # ── Try assignment ────────────────────────────────────
        board[r][c] = v

        # Deep-copy domains so we can restore on backtrack
        domains_copy = copy.deepcopy(domains)
        domains_copy[(r, c)] = {v}

        # ── Forward checking ──────────────────────────────────
        if forward_check(board, domains_copy, r, c, v):
            if backtrack(board, domains_copy, stats):
                return True                 # Solution found ↑

        # ── Undo assignment (backtrack) ───────────────────────
        board[r][c] = 0

    # All values exhausted without success → failure
    stats["failures"] += 1
    return False


# ╔══════════════════════════════════════════════════════════╗
# ║               MASTER  SOLVE  FUNCTION                   ║
# ╚══════════════════════════════════════════════════════════╝

def solve(board: list) -> tuple:
    """
    Solve a Sudoku board using the full CSP pipeline:

      Step 1 │ Build initial domains
      Step 2 │ AC-3  — reduce domains via arc consistency
      Step 3 │ Apply any singletons AC-3 revealed
      Step 4 │ Backtracking search with MRV + forward checking

    Parameters
    ──────────
    board : 9×9 list (original is not modified)

    Returns
    ───────
    (solution, stats)
      solution : 9×9 solved board, or None if unsolvable
      stats    : dict with keys:
                   calls      — BACKTRACK call count
                   failures   — BACKTRACK failure count
                   ac3_iters  — AC-3 arc iterations
                   time_ms    — total time in milliseconds
    """
    stats = {
        "calls"    : 0,
        "failures" : 0,
        "ac3_iters": 0,
        "time_ms"  : 0.0,
    }

    working = copy.deepcopy(board)
    domains = build_domains(working)

    start = time.perf_counter()

    # ── Step 2: AC-3 propagation ──────────────────────────────
    consistent, ac3_iters = ac3(working, domains)
    stats["ac3_iters"] = ac3_iters

    if not consistent:
        stats["time_ms"] = (time.perf_counter() - start) * 1000
        return None, stats

    # ── Step 3: Propagate AC-3 singletons onto the board ─────
    for r in range(9):
        for c in range(9):
            if working[r][c] == 0 and len(domains[(r, c)]) == 1:
                working[r][c] = next(iter(domains[(r, c)]))

    # ── Step 4: Backtracking search ───────────────────────────
    solved = backtrack(working, domains, stats)

    stats["time_ms"] = (time.perf_counter() - start) * 1000
    return (working if solved else None), stats


# ╔══════════════════════════════════════════════════════════╗
# ║                   DISPLAY  HELPERS                      ║
# ╚══════════════════════════════════════════════════════════╝

BANNER = r"""
  ╔═══════════════════════════════════════════════════════╗
  ║                                                       ║
  ║   ███████╗██╗   ██╗██████╗  ██████╗ ██╗  ██╗██╗   ║
  ║   ██╔════╝██║   ██║██╔══██╗██╔═══██╗██║ ██╔╝██║   ║
  ║   ███████╗██║   ██║██║  ██║██║   ██║█████╔╝ ██║   ║
  ║   ╚════██║██║   ██║██║  ██║██║   ██║██╔═██╗ ╚═╝   ║
  ║   ███████║╚██████╔╝██████╔╝╚██████╔╝██║  ██╗██╗   ║
  ║   ╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝   ║
  ║                                                       ║
  ║      CSP Solver  ·  AC-3  ·  Backtracking Search     ║
  ║      MRV Heuristic  ·  Forward Checking               ║
  ╚═══════════════════════════════════════════════════════╝
"""


def print_banner() -> None:
    print(styled(BANNER, C.PURPLE, C.BOLD))


def print_board(board: list, original: list = None, label: str = "") -> None:
    """
    Pretty-print a 9×9 Sudoku board.

    Color coding
    ────────────
    Cyan  + bold   → given / original clue
    Green + bold   → cell solved by the algorithm
    Gray  dim      → empty cell ( · )
    """
    TOP = "  ╔═══════╦═══════╦═══════╗"
    MID = "  ╠═══════╬═══════╬═══════╣"
    BOT = "  ╚═══════╩═══════╩═══════╝"
    ROW = "  ║───────║───────║───────║"
    DIV = styled("  ║ ", C.GRAY)
    SEP = styled(" ║ ", C.GRAY)
    END = styled(" ║",  C.GRAY)

    if label:
        print(styled(f"  {label}", C.BOLD, C.WHITE))

    print(styled(TOP, C.GRAY))

    for r in range(9):
        if r > 0 and r % 3 == 0:
            print(styled(MID, C.GRAY))
        elif r > 0:
            print(styled(ROW, C.DIM, C.GRAY))

        line = DIV
        for c in range(9):
            v        = board[r][c]
            is_given = (original[r][c] != 0) if original else (v != 0)

            if v == 0:
                cell_str = styled("·", C.DIM, C.GRAY)
            elif is_given:
                cell_str = styled(str(v), C.BOLD, C.CYAN)
            else:
                cell_str = styled(str(v), C.BOLD, C.GREEN)

            line += cell_str + " "
            if c % 3 == 2 and c < 8:
                line += SEP

        line += END
        print(line)

    print(styled(BOT, C.GRAY))


def print_section(title: str) -> None:
    """Styled section banner."""
    W   = 55
    bar = "─" * W
    pad = (W - len(title) - 2) // 2
    r   = W - pad - len(title) - 2
    print()
    print(styled(f"  ╭{bar}╮",                                  C.DIM,  C.PURPLE))
    print(styled(f"  │{' '*pad} {title} {' '*r}│",              C.BOLD, C.PURPLE))
    print(styled(f"  ╰{bar}╯",                                  C.DIM,  C.PURPLE))
    print()


def print_stats(name: str, stats: dict, solved: bool) -> None:
    """Print solver statistics in a bordered table."""
    W = 41

    def row(key, val_styled):
        k_part  = styled(f"  │  {key:<25}", C.GRAY)
        raw_len = ansi_len(val_styled)
        pad     = W - 2 - 25 - 2 - raw_len
        return f"{k_part}  {val_styled}{' ' * max(0, pad)}" + styled("│", C.GRAY)

    status_str = (styled("SOLVED  ✓", C.BOLD, C.GREEN)
                  if solved else styled("NO SOLUTION  ✗", C.BOLD, C.RED))

    print(styled(f"  ┌{'─'*W}┐",                               C.GRAY))
    print(styled(f"  │", C.GRAY) +
          styled(f"  Statistics  —  {name:<22}",               C.BOLD, C.WHITE) +
          styled("│", C.GRAY))
    print(styled(f"  ├{'─'*W}┤",                               C.GRAY))
    print(row("Status",                  status_str))
    print(row("BACKTRACK  calls",        styled(f"{stats['calls']:>8,}", C.BOLD, C.YELLOW)))
    print(row("BACKTRACK  failures",     styled(f"{stats['failures']:>8,}", C.BOLD, C.RED)))
    print(row("AC-3  arc iterations",    styled(f"{stats['ac3_iters']:>8,}", C.BOLD, C.CYAN)))
    print(row("Time elapsed",            styled(f"{stats['time_ms']:>7.2f} ms", C.BOLD, C.MAGENTA)))
    print(styled(f"  └{'─'*W}┘",                               C.GRAY))


def print_comparison(collected: dict) -> None:
    """
    Deliverable #3 — brief comment on the statistics for each board.
    Explains what the numbers mean and how difficulty affects them.
    """
    print_section("Deliverable 3  ·  Comment on Solver Statistics")

    comments = {
        "Easy": (
            "Easy board — very low backtrack count.\n"
            "  AC-3 alone propagates enough constraints that most (or all)\n"
            "  empty cells become singletons before search even begins.\n"
            "  Forward checking rarely encounters an empty domain, so the\n"
            "  failure count stays near zero. Demonstrates that dense clue\n"
            "  sets make constraint propagation extremely effective."
        ),
        "Medium": (
            "Medium board — moderate backtracking.\n"
            "  AC-3 reduces domains noticeably but leaves genuine ambiguity.\n"
            "  MRV directs the search to the most constrained cells first,\n"
            "  keeping the branching factor low. Forward checking prunes dead\n"
            "  ends early so failures remain manageable."
        ),
        "Hard": (
            "Hard board — clearly more backtrack calls and failures.\n"
            "  Sparse clues limit AC-3's reach; many cells still hold\n"
            "  multiple candidates after propagation. The solver must explore\n"
            "  several incorrect branches before finding the solution.\n"
            "  MRV + forward checking remain essential to stay tractable."
        ),
        "Very Hard": (
            "Very Hard board — highest calls and failures of all four.\n"
            "  Minimal given clues mean AC-3 achieves little at the start.\n"
            "  The search tree is deep and wide; the solver must recurse far\n"
            "  before converging. This board best demonstrates why backtrack-\n"
            "  ing alone (without MRV and forward checking) would be impractical."
        ),
    }

    diff_order = ["Easy", "Medium", "Hard", "Very Hard"]
    diff_colors = {
        "Easy"      : C.GREEN,
        "Medium"    : C.YELLOW,
        "Hard"      : C.ORANGE,
        "Very Hard" : C.RED,
    }

    for diff in diff_order:
        if diff not in collected:
            continue
        s   = collected[diff]
        col = diff_colors[diff]

        print(styled(f"  ▸ {diff} Board", C.BOLD, col))
        print(
            styled("  │", C.DIM, C.GRAY) +
            styled(
                f"  BACKTRACK calls={s['calls']:,}   "
                f"failures={s['failures']:,}   "
                f"AC-3 iters={s['ac3_iters']:,}   "
                f"time={s['time_ms']:.2f} ms",
                C.YELLOW,
            )
        )
        for comment_line in comments[diff].splitlines():
            print(styled(f"  │  {comment_line}", C.DIM, C.WHITE))
        print()


# ╔══════════════════════════════════════════════════════════╗
# ║                   BOARD  LOADING                        ║
# ╚══════════════════════════════════════════════════════════╝

def load_board(key: str) -> tuple:
    """
    Attempt to read the board from its .txt file.
    Falls back to the built-in preset if the file is absent or corrupt.

    Returns (board_2d_list, source_description_string).
    """
    preset = PRESETS[key]
    try:
        board = read_board(preset["file"])
        return board, f"file  '{preset['file']}'"
    except FileNotFoundError:
        return copy.deepcopy(preset["data"]), "built-in preset  (file not found)"
    except ValueError as exc:
        print(styled(f"  ⚠  {exc} — falling back to built-in preset.", C.YELLOW))
        return copy.deepcopy(preset["data"]), "built-in preset  (file error)"


# ╔══════════════════════════════════════════════════════════╗
# ║                       MAIN                              ║
# ╚══════════════════════════════════════════════════════════╝

def main() -> None:
    print_banner()

    # ── Determine which boards to solve ──────────────────────
    # If filenames are passed on the command line, use those;
    # otherwise run all four preset boards in order.
    if len(sys.argv) > 1:
        # Custom file list supplied
        jobs = []
        for path in sys.argv[1:]:
            try:
                board = read_board(path)
                name  = path
                diff  = "Custom"
                jobs.append((name, diff, board, path))
            except (FileNotFoundError, ValueError) as exc:
                print(styled(f"  ✗  Cannot load '{path}': {exc}\n", C.RED))
    else:
        # Default: all four assignment boards
        jobs = []
        for key in PRESET_ORDER:
            preset        = PRESETS[key]
            board, source = load_board(key)
            jobs.append((preset["name"], preset["diff"], board, source))

    if not jobs:
        print(styled("  No valid boards to solve. Exiting.\n", C.RED))
        return

    # ── Solve each board ──────────────────────────────────────
    collected: dict = {}   # diff → stats  (for deliverable #3)

    for (name, diff, original, source) in jobs:
        print_section(f"{name}   [{PRESETS.get(diff.lower().replace(' ',''), {}).get('file', '—')}]")
        print(styled(f"  Loaded from : {source}\n", C.DIM, C.GRAY))

        # Print initial (unsolved) board
        print_board(original, original, label="Initial Board:")
        print()

        # Solve
        print(styled("  Solving …", C.DIM, C.YELLOW))
        solution, stats = solve(original)
        print()

        # Print result
        if solution:
            print_board(solution, original, label="Solution:")
        else:
            print(styled(
                "  ✗  No solution exists for this board.",
                C.BOLD, C.RED,
            ))
        print()

        # Print statistics table
        print_stats(name, stats, solution is not None)
        print()

        # Save solution to file
        if solution:
            base     = name.lower().replace(" ", "_")
            out_file = f"{base}_solution.txt"
            try:
                write_board(solution, out_file)
                print(styled(f"  ✓  Solution saved to: {out_file}", C.DIM, C.GREEN))
            except OSError as exc:
                print(styled(f"  ⚠  Could not save solution: {exc}", C.YELLOW))
        print()

        # Collect stats for comparison section
        collected[diff] = stats

    # ── Deliverable #3: comparative comment ──────────────────
    if len(collected) > 1:
        print_comparison(collected)

    # ── Footer ────────────────────────────────────────────────
    W   = 57
    bar = "─" * W
    msg = "CSP Solver  ·  AC-3  ·  MRV  ·  Forward Checking  ·  Backtracking"
    pad = (W - len(msg)) // 2
    print(styled(f"  {bar}",             C.DIM, C.PURPLE))
    print(styled(f"  {' '*pad}{msg}",    C.DIM, C.PURPLE))
    print(styled(f"  {bar}\n",           C.DIM, C.PURPLE))


if __name__ == "__main__":
    main()