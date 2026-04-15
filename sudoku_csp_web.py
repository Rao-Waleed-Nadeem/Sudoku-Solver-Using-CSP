import streamlit as st
import copy
import time
from collections import deque

st.set_page_config(page_title="Sudoku CSP Solver", layout="wide")
st.title("🔢 Sudoku CSP Solver")
st.markdown("**AC-3 • MRV • Forward Checking • Backtracking Search**  \n*All original logic preserved*")

# ====================== PRESETS ======================
PRESETS = {
    "easy": {"name": "Easy Board", "data": [[0,0,4,0,3,0,0,5,0],[6,0,9,4,0,0,0,0,0],[0,0,5,1,0,0,4,8,9],[0,0,0,0,6,0,9,3,0],[3,0,0,8,0,7,0,0,2],[0,2,6,0,4,0,0,0,0],[4,5,3,0,0,9,6,0,0],[0,0,0,0,0,4,7,0,5],[0,9,0,0,5,0,2,0,0]]},
    "medium": {"name": "Medium Board", "data": [[5,3,0,0,7,0,0,0,0],[6,0,0,1,9,5,0,0,0],[0,9,8,0,0,0,0,6,0],[8,0,0,0,6,0,0,0,3],[4,0,0,8,0,3,0,0,1],[7,0,0,0,2,0,0,0,6],[0,6,0,0,0,0,2,8,0],[0,0,0,4,1,9,0,0,5],[0,0,0,0,8,0,0,7,9]]},
    "hard": {"name": "Hard Board", "data": [[1,0,2,0,4,0,0,0,7],[0,0,0,0,8,0,0,0,0],[0,9,5,0,0,0,3,0,4],[0,0,6,0,7,9,0,0,0],[5,0,0,0,0,0,2,0,6],[0,0,4,0,5,0,0,0,0],[7,0,8,0,0,3,4,0,0],[0,0,0,0,1,0,0,0,0],[2,0,0,0,6,0,5,0,9]]},
    "veryhard": {
    "name": "Very Hard Board",
    "data": [
        [0,0,0,0,0,0,0,1,2],
        [0,0,0,0,0,3,4,0,0],
        [0,0,5,0,6,0,0,0,0],
        [0,7,0,0,0,0,0,0,0],
        [0,0,0,8,0,0,0,0,0],
        [0,0,0,0,0,0,0,9,0],
        [0,0,0,0,0,0,5,0,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0]
    ]
}
}

# ====================== CORE SOLVER (Your Original Logic) ======================
def _compute_peers(r, c):
    peers = set()
    for i in range(9):
        if i != c: peers.add((r, i))
        if i != r: peers.add((i, c))
    br, bc = (r // 3) * 3, (c // 3) * 3
    for dr in range(3):
        for dc in range(3):
            nb = (br + dr, bc + dc)
            if nb != (r, c): peers.add(nb)
    return frozenset(peers)

PEERS = {(r, c): _compute_peers(r, c) for r in range(9) for c in range(9)}

def build_domains(board):
    domains = {}
    for r in range(9):
        for c in range(9):
            if board[r][c] != 0:
                domains[(r, c)] = {board[r][c]}
            else:
                used = {board[pr][pc] for (pr, pc) in PEERS[(r, c)] if board[pr][pc] != 0}
                domains[(r, c)] = set(range(1, 10)) - used
    return domains

def ac3(board, domains):
    queue = deque([(r, c, pr, pc) for r in range(9) for c in range(9) if board[r][c] == 0 
                   for (pr, pc) in PEERS[(r, c)] if board[pr][pc] == 0])
    arc_iterations = 0
    while queue:
        r1, c1, r2, c2 = queue.popleft()
        arc_iterations += 1
        if _revise(domains, r1, c1, r2, c2):
            if not domains[(r1, c1)]:
                return False, arc_iterations
            for (pr, pc) in PEERS[(r1, c1)]:
                if (pr, pc) != (r2, c2) and board[pr][pc] == 0:
                    queue.append((pr, pc, r1, c1))
    return True, arc_iterations

def _revise(domains, r1, c1, r2, c2):
    revised = False
    for v in list(domains[(r1, c1)]):
        if not any(w != v for w in domains[(r2, c2)]):
            domains[(r1, c1)].discard(v)
            revised = True
    return revised

def select_mrv(board, domains):
    best, best_size = None, 10
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                sz = len(domains[(r, c)])
                if sz < best_size:
                    best_size, best = sz, (r, c)
    return best

def forward_check(board, domains, r, c, v):
    for (pr, pc) in PEERS[(r, c)]:
        if board[pr][pc] == 0:
            domains[(pr, pc)].discard(v)
            if not domains[(pr, pc)]:
                return False
    return True

def backtrack(board, domains, stats):
    stats["calls"] += 1
    cell = select_mrv(board, domains)
    if cell is None:
        return True
    r, c = cell
    for v in sorted(domains[(r, c)]):
        board[r][c] = v
        domains_copy = copy.deepcopy(domains)
        domains_copy[(r, c)] = {v}
        if forward_check(board, domains_copy, r, c, v):
            if backtrack(board, domains_copy, stats):
                return True
        board[r][c] = 0
    stats["failures"] += 1
    return False

def solve(board):
    stats = {"calls": 0, "failures": 0, "ac3_iters": 0, "time_ms": 0.0}
    working = copy.deepcopy(board)
    domains = build_domains(working)
    start = time.perf_counter()

    consistent, ac3_iters = ac3(working, domains)
    stats["ac3_iters"] = ac3_iters
    if not consistent:
        stats["time_ms"] = (time.perf_counter() - start) * 1000
        return None, stats

    for r in range(9):
        for c in range(9):
            if working[r][c] == 0 and len(domains[(r, c)]) == 1:
                working[r][c] = next(iter(domains[(r, c)]))

    solved = backtrack(working, domains, stats)
    stats["time_ms"] = (time.perf_counter() - start) * 1000
    return (working if solved else None), stats

# ====================== UI ======================
tab1, tab2 = st.tabs(["Preset Boards", "Upload Custom Board"])

with tab1:
    if st.button("Solve All 4 Preset Boards", type="primary"):
        for key in PRESETS:
            preset = PRESETS[key]
            original = preset["data"]
            
            st.subheader(preset["name"])
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Initial Board**")
                st.table(original)
            
            solution, stats = solve(original)
            
            with col2:
                st.write("**Solution**" if solution else "**No Solution**")
                if solution:
                    st.table(solution)
                else:
                    st.error("No solution found!")
            
            st.write(f"**Statistics**")
            st.json({
                "Status": "SOLVED ✓" if solution else "NO SOLUTION ✗",
                "BACKTRACK calls": stats["calls"],
                "BACKTRACK failures": stats["failures"],
                "AC-3 iterations": stats["ac3_iters"],
                "Time": f"{stats['time_ms']:.2f} ms"
            })
            st.divider()

with tab2:
    st.info("Upload a 9x9 Sudoku puzzle (9 lines, 9 digits each, 0 = empty)")
    uploaded_file = st.file_uploader("Upload Sudoku .txt file", type=["txt"])
    
    if uploaded_file:
        try:
            lines = uploaded_file.read().decode("utf-8").strip().splitlines()
            board = [[int(ch) for ch in line.strip()] for line in lines if line.strip()]
            if len(board) == 9 and all(len(row) == 9 for row in board):
                st.success("Board loaded successfully!")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Uploaded Board**")
                    st.table(board)
                
                solution, stats = solve(board)
                with col2:
                    st.write("**Solution**")
                    if solution:
                        st.table(solution)
                    else:
                        st.error("No solution found!")
                
                st.json({
                    "Status": "SOLVED ✓" if solution else "NO SOLUTION ✗",
                    "BACKTRACK calls": stats["calls"],
                    "BACKTRACK failures": stats["failures"],
                    "AC-3 iterations": stats["ac3_iters"],
                    "Time": f"{stats['time_ms']:.2f} ms"
                })
            else:
                st.error("Invalid board format. Must be 9 lines with 9 digits each.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

st.caption("Original Python logic preserved | Running locally on http://localhost")