"""Streamlit UI for the Klondike draw-3 solver.

Run with: ``streamlit run solver_app.py``
"""

from __future__ import annotations

import json

import streamlit as st

from solitaire_solver.cards import Card
from solitaire_solver.deal import (
    Deal,
    build_custom_deal,
    deal_from_json,
    deal_to_json,
    make_random_deal,
)
from solitaire_solver.serialize import envelope, humanize
from solitaire_solver.solver import solve
from solitaire_solver.state import GameState
from solitaire_solver.visual import render_board, state_at_step


st.set_page_config(page_title="Klondike Solver", page_icon="\U0001F0CF", layout="wide")


_RANK_CODE = {1: "A", 10: "10", 11: "J", 12: "Q", 13: "K"}


def _fmt_code(card: Card) -> str:
    """Format a Card back into its input code (e.g. ``10H``, ``AS``, ``QD``)."""
    from solitaire_solver.cards import SUIT_CHARS

    r = int(card.rank)
    rank = _RANK_CODE.get(r, str(r))
    return rank + SUIT_CHARS[int(card.suit)]


def _load_deal_from_text(text: str) -> Deal | None:
    try:
        obj = json.loads(text)
        return deal_from_json(obj)
    except Exception as e:
        st.sidebar.error(f"Could not parse deal JSON: {e}")
        return None




# ---------- Sidebar controls ----------

with st.sidebar:
    st.header("Deal")
    source = st.radio(
        "Source",
        ["Random seed", "Build custom deal", "Upload JSON", "Paste JSON"],
        key="deal_source",
    )

    if source == "Random seed":
        seed = st.number_input("Seed", min_value=0, max_value=10_000_000, value=42, step=1)
        if st.button("Generate deal", use_container_width=True):
            st.session_state.deal = make_random_deal(int(seed))
            st.session_state.solution = None
            st.session_state.step = 0
            st.session_state.deal_label = f"Random seed {int(seed)}"

    elif source == "Build custom deal":
        st.caption(
            "Enter card codes (e.g. `AS 10H QD 7C`). Ranks: `A 2 3 4 5 6 7 8 9 "
            "10 J Q K`. Suits: `S H D C`. For each tableau pile, the **last** "
            "card is the face-up top; the rest are face-down. The solver needs "
            "the full 52-card deal."
        )
        tableau_texts: list[str] = []
        for i in range(7):
            tableau_texts.append(
                st.text_input(
                    f"T{i} ({i + 1} card{'s' if i else ''}, bottom -> top)",
                    key=f"custom_t_{i}",
                )
            )
        stock_text = st.text_area(
            "Stock (24 cards, draw order)",
            key="custom_stock",
            height=100,
        )
        cols = st.columns(2)
        if cols[0].button("Build deal", use_container_width=True):
            try:
                deal = build_custom_deal(tableau_texts, stock_text)
                st.session_state.deal = deal
                st.session_state.solution = None
                st.session_state.step = 0
                st.session_state.deal_label = "Custom deal"
                st.success("Deal built.")
            except ValueError as e:
                st.error(str(e))
        if cols[1].button("Prefill example", use_container_width=True):
            # Seed 42's deal, written out so you can see the expected format.
            example = make_random_deal(42)
            for i, pile in enumerate(example.tableau):
                cards = list(pile.face_down) + list(pile.face_up)
                st.session_state[f"custom_t_{i}"] = " ".join(
                    _fmt_code(c) for c in cards
                )
            st.session_state["custom_stock"] = " ".join(
                _fmt_code(c) for c in example.stock
            )
            st.rerun()

    elif source == "Upload JSON":
        f = st.file_uploader("Deal JSON", type=["json"], key="deal_upload")
        if f is not None:
            try:
                deal = deal_from_json(json.load(f))
                st.session_state.deal = deal
                st.session_state.solution = None
                st.session_state.step = 0
                st.session_state.deal_label = f.name
            except Exception as e:
                st.error(f"Could not load deal: {e}")

    else:
        text = st.text_area("Deal JSON", height=240, key="deal_paste")
        if st.button("Load pasted JSON", use_container_width=True) and text.strip():
            deal = _load_deal_from_text(text)
            if deal is not None:
                st.session_state.deal = deal
                st.session_state.solution = None
                st.session_state.step = 0
                st.session_state.deal_label = "Pasted deal"

    st.divider()
    st.header("Solver budget")
    budget_seconds = st.slider("Time budget (seconds)", 1, 120, 30)
    budget_nodes = st.number_input(
        "Max nodes",
        min_value=1_000,
        max_value=20_000_000,
        value=1_000_000,
        step=100_000,
    )

    if st.button("Solve", type="primary", use_container_width=True):
        if "deal" not in st.session_state:
            st.warning("Generate or load a deal first.")
        else:
            with st.spinner("Searching..."):
                result = solve(
                    st.session_state.deal,
                    budget_seconds=float(budget_seconds),
                    budget_nodes=int(budget_nodes),
                )
            st.session_state.solution = result
            st.session_state.step = 0


# ---------- Main area ----------

st.title("\U0001F0CF Klondike Draw-3 Solver")

if "deal" not in st.session_state:
    st.info(
        "Generate a random deal, upload a Deal JSON file, or paste one into the "
        "sidebar to begin. Then click **Solve**."
    )
    st.stop()

deal: Deal = st.session_state.deal
solution = st.session_state.get("solution")
step: int = st.session_state.get("step", 0)
deal_label = st.session_state.get("deal_label", "current deal")

st.caption(f"**Deal:** {deal_label}")

if solution is not None and solution.solved:
    current_state = state_at_step(deal, solution.moves, step)
else:
    current_state = GameState.from_deal(deal)

st.markdown(render_board(current_state), unsafe_allow_html=True)
st.markdown("<div style='height:64px;'></div>", unsafe_allow_html=True)

if solution is None:
    st.info("Click **Solve** in the sidebar.")
elif not solution.solved:
    st.error(
        f"No solution found. {solution.reason} "
        f"(Searched {solution.node_count:,} nodes in {solution.elapsed_seconds:.2f}s.)"
    )
else:
    n = len(solution.moves)
    st.success(
        f"Solved in {solution.elapsed_seconds:.2f}s \u2014 "
        f"{solution.node_count:,} nodes searched, {n} moves in solution."
    )

    cols = st.columns([1, 1, 1, 1, 2])
    if cols[0].button("\u23EE Reset", use_container_width=True):
        st.session_state.step = 0
        st.rerun()
    if cols[1].button("\u25C0 Prev", use_container_width=True, disabled=step == 0):
        st.session_state.step = max(0, step - 1)
        st.rerun()
    if cols[2].button("Next \u25B6", use_container_width=True, disabled=step >= n):
        st.session_state.step = min(n, step + 1)
        st.rerun()
    if cols[3].button("\u23ED Final", use_container_width=True):
        st.session_state.step = n
        st.rerun()

    new_step = cols[4].slider(
        "Step",
        min_value=0,
        max_value=n,
        value=step,
        key="step_slider",
        label_visibility="collapsed",
    )
    if new_step != step:
        st.session_state.step = new_step
        st.rerun()

    if step == 0:
        st.markdown(f"**Step 0 / {n}** \u2014 initial deal")
    else:
        st.markdown(
            f"**Step {step} / {n}** \u2014 "
            f"{humanize(solution.moves[step - 1], step).strip()}"
        )

    with st.expander("Full move list"):
        st.code(
            "\n".join(humanize(m, i + 1) for i, m in enumerate(solution.moves)),
            language=None,
        )

    env = envelope(
        deal_digest=deal.digest(),
        moves=solution.moves,
        solved=True,
        node_count=solution.node_count,
        elapsed_seconds=solution.elapsed_seconds,
    )
    st.download_button(
        "\U0001F4E5 Download solution JSON",
        data=json.dumps(env, indent=2),
        file_name="solution.json",
        mime="application/json",
    )

with st.expander("Inspect / download the deal"):
    deal_json = json.dumps(deal_to_json(deal), indent=2)
    st.code(deal_json, language="json")
    st.download_button(
        "\U0001F4E5 Download deal JSON",
        data=deal_json,
        file_name="deal.json",
        mime="application/json",
    )
