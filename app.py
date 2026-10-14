# -*- coding: utf-8 -*-
import os
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="항공안전법령 RAG 검증 진행 현황", layout="wide")

# ══════════════════════════════════════════════════════════════
#  데이터 소스
#  · 태스크 표: 전용 구글시트를 "웹에 게시(CSV)"한 URL을 아래에 붙여넣으세요.
#    (구글시트 → 파일 → 공유 → 웹에 게시 → 전체문서/CSV → 게시 → URL 복사)
#    원우들이 그 시트를 고치면 대시보드가 자동으로 따라갑니다.
#    URL을 비워두면 저장소에 있는 task_grid.csv(백업본)를 읽습니다.
#  · 보강 항목(논문·저자·요약·TT21 표·TT29~32 결과): extras.json (저장소).
# ══════════════════════════════════════════════════════════════
SHEET_CSV_URL = ""          # 예: "https://docs.google.com/spreadsheets/d/e/....../pub?gid=0&single=true&output=csv"
LOCAL_GRID = "task_grid.csv"
EXTRAS = "extras.json"

STATUS_COLOR = {"완료": "🟢", "검토중": "🟡", "진행중": "🔵", "미착수": "⚪"}

# ── TT36 Pilot 성능 지표 (Google Drive TT36_Pilot_ABCD_Review_Metrics_20261014.json) ──
TT36_METRICS = {
    "A": {
        5:  {"hit_rate": 0.70, "micro_recall": 0.375,  "mrr": 0.4667, "ndcg": 0.3587, "valid": 81,  "future": 19,  "expired": 0},
        10: {"hit_rate": 0.75, "micro_recall": 0.5208, "mrr": 0.475,  "ndcg": 0.4081, "valid": 158, "future": 42,  "expired": 0},
        20: {"hit_rate": 0.75, "micro_recall": 0.5417, "mrr": 0.475,  "ndcg": 0.4161, "valid": 315, "future": 78,  "expired": 0},
    },
    "B": {
        5:  {"hit_rate": 0.20, "micro_recall": 0.0833, "mrr": 0.135,  "ndcg": 0.0975, "valid": 10,  "future": 13,  "expired": 77},
        10: {"hit_rate": 0.30, "micro_recall": 0.125,  "mrr": 0.1471, "ndcg": 0.1145, "valid": 14,  "future": 21,  "expired": 165},
        20: {"hit_rate": 0.40, "micro_recall": 0.1667, "mrr": 0.1543, "ndcg": 0.1302, "valid": 19,  "future": 41,  "expired": 340},
    },
    "C": {
        5:  {"hit_rate": 0.70, "micro_recall": 0.3958, "mrr": 0.4917, "ndcg": 0.3822, "valid": 100, "future": 0,   "expired": 0},
        10: {"hit_rate": 0.75, "micro_recall": 0.5625, "mrr": 0.500,  "ndcg": 0.4377, "valid": 199, "future": 0,   "expired": 0},
        20: {"hit_rate": 0.75, "micro_recall": 0.6042, "mrr": 0.500,  "ndcg": 0.4529, "valid": 368, "future": 0,   "expired": 0},
    },
    "D": {
        5:  {"hit_rate": 0.60, "micro_recall": 0.3125, "mrr": 0.3892, "ndcg": 0.3070, "valid": 100, "future": 0,   "expired": 0},
        10: {"hit_rate": 0.75, "micro_recall": 0.4792, "mrr": 0.4069, "ndcg": 0.3631, "valid": 199, "future": 0,   "expired": 0},
        20: {"hit_rate": 0.75, "micro_recall": 0.6042, "mrr": 0.4069, "ndcg": 0.4048, "valid": 368, "future": 0,   "expired": 0},
    },
}

TT36_D_DIAGNOSTICS = [
    {"id":"Q001","type":"현행·단일규정","scope":4,"fallback":False,"c@5":1,"d@5":1,"c@10":1,"d@10":1,"c@20":1,"d@20":1},
    {"id":"Q002","type":"현행·상하위연결","scope":3,"fallback":False,"c@5":1,"d@5":1,"c@10":2,"d@10":2,"c@20":2,"d@20":2},
    {"id":"Q003","type":"현행·단일규정","scope":41,"fallback":False,"c@5":1,"d@5":1,"c@10":1,"d@10":1,"c@20":1,"d@20":1},
    {"id":"Q004","type":"현행·기술기준","scope":14,"fallback":False,"c@5":0,"d@5":0,"c@10":1,"d@10":1,"c@20":1,"d@20":1},
    {"id":"Q005","type":"현행·기술기준","scope":97,"fallback":True,"c@5":1,"d@5":1,"c@10":2,"d@10":2,"c@20":2,"d@20":2},
    {"id":"Q006","type":"현행·기술기준","scope":0,"fallback":True,"c@5":2,"d@5":2,"c@10":3,"d@10":3,"c@20":3,"d@20":3},
    {"id":"Q007","type":"조건·예외","scope":26,"fallback":False,"c@5":2,"d@5":0,"c@10":2,"d@10":1,"c@20":2,"d@20":2},
    {"id":"Q008","type":"조건·예외","scope":26,"fallback":False,"c@5":1,"d@5":0,"c@10":2,"d@10":1,"c@20":2,"d@20":2},
    {"id":"Q009","type":"복합조건","scope":0,"fallback":True,"c@5":1,"d@5":1,"c@10":1,"d@10":1,"c@20":1,"d@20":1},
    {"id":"Q010","type":"기술기준·훈련","scope":66,"fallback":False,"c@5":2,"d@5":1,"c@10":5,"d@10":3,"c@20":5,"d@20":5},
    {"id":"Q011","type":"기술기준·훈련","scope":0,"fallback":True,"c@5":1,"d@5":1,"c@10":1,"d@10":1,"c@20":2,"d@20":2},
    {"id":"Q012","type":"별표18·표","scope":3,"fallback":True,"c@5":1,"d@5":1,"c@10":1,"d@10":1,"c@20":1,"d@20":1},
    {"id":"Q013","type":"위임관계","scope":3,"fallback":False,"c@5":2,"d@5":2,"c@10":2,"d@10":2,"c@20":2,"d@20":2},
    {"id":"Q014","type":"위임관계","scope":7,"fallback":False,"c@5":1,"d@5":2,"c@10":1,"d@10":2,"c@20":2,"d@20":2},
    {"id":"Q015","type":"시행관계·별표17","scope":26,"fallback":False,"c@5":2,"d@5":1,"c@10":2,"d@10":1,"c@20":2,"d@20":2},
    {"id":"Q016","type":"시행관계·별표9","scope":36,"fallback":False,"c@5":0,"d@5":0,"c@10":0,"d@10":0,"c@20":0,"d@20":0},
    {"id":"Q017","type":"과거시점","scope":0,"fallback":True,"c@5":0,"d@5":0,"c@10":0,"d@10":0,"c@20":0,"d@20":0},
    {"id":"Q018","type":"과거시점","scope":0,"fallback":True,"c@5":0,"d@5":0,"c@10":0,"d@10":0,"c@20":0,"d@20":0},
    {"id":"Q019","type":"시간·유효기간","scope":0,"fallback":True,"c@5":0,"d@5":0,"c@10":0,"d@10":0,"c@20":0,"d@20":0},
    {"id":"Q020","type":"미래시행","scope":0,"fallback":True,"c@5":0,"d@5":0,"c@10":0,"d@10":0,"c@20":0,"d@20":0},
]


@st.cache_data(ttl=120)     # 구글시트를 2분에 한 번 재조회
def load_data():
    # 1) 태스크 표 — 구글시트 URL 우선, 실패하면 로컬 백업본
    source_label = "구글시트(실시간)"
    src = SHEET_CSV_URL.strip()
    try:
        if not src:
            raise ValueError("no url")
        df = pd.read_csv(src, dtype=str)
    except Exception:
        df = pd.read_csv(LOCAL_GRID, dtype=str)
        source_label = "로컬 백업본(task_grid.csv)"
    df = df.fillna("")
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").fillna(0).astype(int)

    # 2) 보강 항목 병합
    extras = {}
    if os.path.exists(EXTRAS):
        with open(EXTRAS, encoding="utf-8") as f:
            extras = json.load(f)
    df["results"] = df["id"].map(extras.get("results", {}))
    df["table"] = df["id"].map(extras.get("tables", {}))

    return source_label, extras.get("project_due", ""), extras.get("manuscript"), extras.get("action_plan"), extras.get("research_questions", []), df


@st.cache_data(ttl=120)
def read_bytes(path):
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


def manuscript_section(m):
    if not m:
        return
    st.subheader("📄 최신 원고")
    st.markdown(f"**{m['title']}**")
    st.markdown(
        f"- **주저자**: {m.get('lead_author','')}\n"
        f"- **공동저자**: {m.get('co_authors','')}\n"
        f"- **교신저자**: {m.get('corresponding_author','')}\n"
        f"- **투고학회(예정)**: {m.get('target_journal','')}"
    )
    if m.get("summary"):
        st.markdown(f"**연구내용 요약**: {m['summary']}")
    if m.get("note"):
        st.caption("⚠️ " + m["note"])

    pdf_bytes = read_bytes(m.get("pdf_path"))
    hwp_bytes = read_bytes(m.get("hwp_path"))
    c1, c2 = st.columns(2)
    if pdf_bytes:
        c1.download_button(
            f"⬇️ PDF 다운로드 · {m.get('pdf_label','')} ({m.get('pdf_updated','')})",
            data=pdf_bytes, file_name=m.get("pdf_download_name", "manuscript.pdf"),
            mime="application/pdf", use_container_width=True,
        )
    else:
        c1.info("PDF 파일이 static 폴더에 없습니다.")
    if hwp_bytes:
        c2.download_button(
            f"⬇️ HWP 다운로드 · {m.get('hwp_label','')} ({m.get('hwp_updated','')})",
            data=hwp_bytes, file_name=m.get("hwp_download_name", "manuscript.hwp"),
            mime="application/x-hwp", use_container_width=True,
        )
    else:
        c2.info("HWP 파일이 static 폴더에 없습니다.")
    st.divider()


def detail_block(r):
    st.markdown(f"**핵심목표**  {r['goal']}")
    if r.get("detail"):
        st.markdown(f"**작업내용 / 인계 노트**  {r['detail']}")
    if r.get("blocker"):
        st.warning(f"**차단/보류 사유**  {r['blocker']}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**선행 Task**  {r.get('pred') or '—'}")
        st.markdown(f"**산출물**  {r.get('outputs') or '—'}")
    with c2:
        st.markdown(f"**후속 Task**  {r.get('succ') or '—'}")
        st.markdown(f"**협업/검토**  {r.get('collab') or '—'}")
    st.caption(f"담당 {r['owner']}  ·  작업종료 {r['due']}  ·  진행률 {int(r['progress'])}%")
    st.progress(int(r["progress"]) / 100)

    res = r.get("results")
    if isinstance(res, dict):
        ver = res.get("version", "")
        frozen = "✅ CLOSED/FROZEN" if "FROZEN" in res.get("basis", "") else "⚠️ 잠정"
        st.markdown(f"**개발파일럿 결과 {ver} {frozen}** — {res.get('system','')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Coverage (pass)", res.get("pass", "—"))
        m2.metric("Abstain", res.get("abstain", "—"))
        m3.metric("Error", res.get("error", "—"))
        if res.get("note"):
            st.caption(res["note"])
        if res.get("basis"):
            st.caption("🔒 " + res["basis"])

    tbl = r.get("table")
    if isinstance(tbl, dict):
        st.markdown("**청킹 후보 비교 결과**")
        tdf = pd.DataFrame(tbl["rows"], columns=tbl["columns"])
        st.dataframe(tdf, use_container_width=True, hide_index=True)
        if tbl.get("caption"):
            st.caption(tbl["caption"])


RQ_STATUS_COLOR = {
    "본실험 대기": "🟡",
    "Discussion 집필 대기": "⚪",
    "확정": "🟢",
}

def rq_section(rqs):
    if not rqs:
        return
    st.subheader("🔬 연구 질문(RQ) 및 예상 답변")
    for rq in rqs:
        sid = rq.get("id", "")
        status = rq.get("status", "")
        icon = "🟡"
        for k, v in RQ_STATUS_COLOR.items():
            if status.startswith(k):
                icon = v
                break
        header = f"{icon} **{sid}** — {rq.get('linked_comparison','')}  ·  _{status}_"
        with st.expander(header, expanded=False):
            st.markdown(f"**연구 질문**")
            st.markdown(f"> {rq.get('question','')}")
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f"**예상 답변 방향**  {rq.get('expected_direction','—')}")
                st.markdown(f"**예상 답변 시기**  {rq.get('answer_timing','—')}")
                st.markdown(f"**연계 Task**  {', '.join(rq.get('linked_tasks', []))}")
            with col2:
                st.markdown(f"**현재 파일럿 신호**")
                signal = rq.get("current_signal", "—")
                st.info(signal)
            if rq.get("rationale"):
                st.markdown(f"**예상 근거**  {rq['rationale']}")
    st.divider()


def action_plan_section(ap):
    if not ap:
        return
    status = ap.get("status", "")
    color = "🟢" if "FROZEN" in status else "🟡"
    with st.expander(f"{color} **TT29~32 개발파일럿 종결 현황** — {status}", expanded=False):
        st.markdown(ap.get("summary", ""))
        rows = ap.get("tasks", [])
        if rows:
            tdf = pd.DataFrame(rows, columns=["Task", "내용", "상태"])
            st.dataframe(tdf, use_container_width=True, hide_index=True)
        if ap.get("checklist"):
            st.caption(ap["checklist"])
        nxt = ap.get("next", [])
        if nxt:
            st.markdown("**다음 단계**")
            for n in nxt:
                st.markdown(f"- {n}")


def tt36_pilot_section():
    """TT36 Pilot A/B/C/D 성능 비교 섹션"""
    st.subheader("🧪 TT36 Pilot 성능 비교 (20문항 × 4시스템)")
    st.caption(
        "출처: TT36_Pilot_ABCD_Review_Metrics_20261014.json  ·  "
        "⚠️ POSTHOC_DIAGNOSTIC_REVIEW_NOT_FINAL_PAPER_METRICS  ·  "
        "Retrieval-only (No LLM), NOT FROZEN"
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Top-K 성능 비교", "↔️ 시스템 간 비교", "🔍 System D 문항별 진단", "📋 버전 유효성"
    ])

    # ── Tab 1: Top-K 성능 비교 ──────────────────────────────────────
    with tab1:
        st.markdown("#### Hit Rate · Micro Recall · MRR · nDCG  (A / B / C / D)")

        for k in [5, 10, 20]:
            st.markdown(f"##### Top-{k}")
            rows = []
            for sys in ["A", "B", "C", "D"]:
                m = TT36_METRICS[sys][k]
                rows.append({
                    "시스템": f"System {sys}",
                    f"Hit@{k}": f"{m['hit_rate']*100:.0f}%",
                    f"Micro Recall@{k}": f"{m['micro_recall']*100:.1f}%",
                    f"MRR@{k}": f"{m['mrr']:.3f}",
                    f"nDCG@{k}": f"{m['ndcg']:.3f}",
                })
            tdf = pd.DataFrame(rows)
            st.dataframe(tdf, use_container_width=True, hide_index=True)

        st.caption(
            "Gold TU 총 48건 (20문항). "
            "Hit@K = 해당 문항의 Gold TU 중 1개 이상이 Top-K에 포함된 문항 비율. "
            "Micro Recall@K = 전체 Gold TU 중 Top-K에 포함된 비율."
        )

    # ── Tab 2: 시스템 간 비교 (A-B, B-C, C-D) ──────────────────────
    with tab2:
        st.markdown("#### 시스템 간 성능 차이 (Δ = 후자 − 전자)")

        pairs = [("A", "B"), ("B", "C"), ("A", "C"), ("C", "D")]
        pair_labels = {"AB": "A → B", "BC": "B → C", "AC": "A → C", "CD": "C → D"}

        for k in [5, 10, 20]:
            st.markdown(f"##### Top-{k}")
            rows = []
            for s1, s2 in pairs:
                m1 = TT36_METRICS[s1][k]
                m2 = TT36_METRICS[s2][k]
                dh = m2["hit_rate"] - m1["hit_rate"]
                dr = m2["micro_recall"] - m1["micro_recall"]
                dm = m2["mrr"] - m1["mrr"]
                dn = m2["ndcg"] - m1["ndcg"]
                lbl = pair_labels.get(s1+s2, f"{s1}→{s2}")
                rows.append({
                    "비교": lbl,
                    f"ΔHit@{k}": f"{dh:+.0%}",
                    f"ΔRecall@{k}": f"{dr:+.1%}",
                    f"ΔMRR@{k}": f"{dm:+.3f}",
                    f"ΔnDCG@{k}": f"{dn:+.3f}",
                    "해석": (
                        "B: 전버전 혼입으로 급락" if s1=="A" and s2=="B" else
                        "C: 시간필터로 B 대비 대폭 회복" if s1=="B" and s2=="C" else
                        "A vs C: C가 MRR/Recall 소폭 우위" if s1=="A" and s2=="C" else
                        "D@5 낮음(Graph 미재순위화 영향)"
                    ),
                })
            tdf = pd.DataFrame(rows)
            st.dataframe(tdf, use_container_width=True, hide_index=True)

        st.info(
            "**핵심 관찰**\n"
            "- **A → B**: 전버전 DB 혼입으로 Hit@5 70%→20%, Recall 급락\n"
            "- **B → C**: 시간필터 적용으로 전구간 회복. C ≥ A\n"
            "- **A → C**: C가 Recall@10/20·MRR 소폭 우위 (valid_to 필터로 미래법령 차단)\n"
            "- **C → D**: D Top-5 성능 저하 — Graph 검색 경로 간 점수 미재순위화(GRAPH_FIRST_STABLE_UNION_NOT_SCORE_RERANKED)\n"
            "- **D@20 = C@20**: Recall·Covered 동일 — 추가 Graph TU가 Top-20 내 순위 확장 효과"
        )

    # ── Tab 3: System D 문항별 진단 ─────────────────────────────────
    with tab3:
        st.markdown("#### System D 문항별 진단 (C vs D, Gold@5/10/20)")

        diag_rows = []
        for q in TT36_D_DIAGNOSTICS:
            fb_icon = "🔴 Fallback" if q["fallback"] else "🟢 Graph"
            diag_rows.append({
                "문항": q["id"],
                "유형": q["type"],
                "Graph 전략": fb_icon,
                "Scope TU수": q["scope"],
                "C Gold@5": q["c@5"],
                "D Gold@5": q["d@5"],
                "C Gold@10": q["c@10"],
                "D Gold@10": q["d@10"],
                "C Gold@20": q["c@20"],
                "D Gold@20": q["d@20"],
                "D vs C @5": "=" if q["d@5"]==q["c@5"] else ("▲" if q["d@5"]>q["c@5"] else "▼"),
            })
        diag_df = pd.DataFrame(diag_rows)

        # 색상 하이라이트
        def highlight_diff(val):
            if val == "▼":
                return "background-color: #ffe0e0; color: #c00"
            if val == "▲":
                return "background-color: #e0ffe0; color: #060"
            return ""

        styled = diag_df.style.applymap(highlight_diff, subset=["D vs C @5"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.caption(
            "🔴 Fallback = GRAPH_SCOPE_EMPTY(scope=0) 또는 FILTERED_ANN_EMPTY(scoped_search=0) → C와 동일 결과. "
            "▼ = D가 C보다 Gold 적게 검색. "
            "Q007·Q008·Q010·Q015: Graph 검색했으나 점수 미재순위화로 Gold가 Top-5에서 밀려남."
        )

        # Fallback 요약
        fallback_qs = [q["id"] for q in TT36_D_DIAGNOSTICS if q["fallback"]]
        nonfallback_worse = [q["id"] for q in TT36_D_DIAGNOSTICS if not q["fallback"] and q["d@5"] < q["c@5"]]
        col1, col2, col3 = st.columns(3)
        col1.metric("Fallback 문항 수", f"{len(fallback_qs)}/20", help=", ".join(fallback_qs))
        col2.metric("Graph 검색 문항", f"{20-len(fallback_qs)}/20")
        col3.metric("Graph 검색 中 @5 성능 저하", f"{len(nonfallback_worse)}문항", help=", ".join(nonfallback_worse))

    # ── Tab 4: 버전 유효성 ──────────────────────────────────────────
    with tab4:
        st.markdown("#### Top-K 검색 결과의 시간적 유효성 분포")
        st.caption("Q: 각 시스템이 반환한 청크의 valid_from/valid_to 기준 분류 (Gold 정합성과 무관)")

        for k in [5, 10, 20]:
            st.markdown(f"##### Top-{k} (총 반환 = 20문항 × {k})")
            rows = []
            for sys in ["A", "B", "C", "D"]:
                m = TT36_METRICS[sys][k]
                total = m["valid"] + m.get("future", 0) + m.get("expired", 0)
                rows.append({
                    "시스템": f"System {sys}",
                    "현행 유효": m["valid"],
                    "미래 시행": m.get("future", 0),
                    "만료 (구버전)": m.get("expired", 0),
                    "합계": total,
                    "유효 비율": f"{m['valid']/total*100:.0f}%" if total else "—",
                })
            tdf = pd.DataFrame(rows)
            st.dataframe(tdf, use_container_width=True, hide_index=True)

        st.warning(
            "**System A**: `valid_to IS NULL` 필터가 미래 시행 법령을 제외하지 않음 — "
            "Top-10 기준 200건 중 42건(21%)이 미래 시행 버전.\n\n"
            "**System B**: 전버전 DB 사용으로 Top-10 기준 200건 중 165건(83%)이 만료 버전.\n\n"
            "**System C/D**: 시간 필터 적용 — 전 구간 현행 유효 100%."
        )

    st.divider()


@st.fragment(run_every="30s")   # 이 블록만 30초마다 자동 갱신
def dashboard():
    source_label, project_due, manuscript, action_plan, research_questions, df = load_data()

    total = len(df)
    done = (df["status"] == "완료").sum()
    active = df["status"].isin(["진행중", "검토중"]).sum()
    todo = (df["status"] == "미착수").sum()
    overall = int(round(df["progress"].mean())) if total else 0

    head_l, head_r = st.columns([4, 1])
    head_l.caption(
        f"데이터 출처: {source_label}  ·  화면 갱신 {pd.Timestamp.now(tz='Africa/Lagos'):%Y-%m-%d %H:%M:%S}"
    )
    if head_r.button("🔄 지금 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("전체 Task", total)
    c2.metric("완료", done)
    c3.metric("진행/검토중", active)
    c4.metric("미착수", todo)
    c5.metric("전체 공정률", f"{overall}%")
    st.progress(overall / 100)
    if project_due:
        st.markdown(f"**작업종료 예정일: {project_due}**")
    st.divider()

    manuscript_section(manuscript)
    rq_section(research_questions)
    action_plan_section(action_plan)
    tt36_pilot_section()

    st.subheader("Phase별 진행률")
    for phase, g in df.groupby("phase", sort=False):
        pct = int(round(g["progress"].mean()))
        label, bar = st.columns([2, 3])
        label.markdown(f"**{phase}**  ·  {(g['status']=='완료').sum()}/{len(g)} 완료")
        bar.progress(pct / 100, text=f"{pct}%")
    st.divider()

    st.subheader("Task 상세 — 항목을 클릭하면 작업내용이 펼쳐집니다")
    show_done = st.checkbox("완료 항목도 보기", value=False)
    view = df if show_done else df[df["status"] != "완료"]

    for phase, group in view.groupby("phase", sort=False):
        st.markdown(f"#### {phase}")
        for _, r in group.iterrows():
            icon = STATUS_COLOR.get(r["status"], "")
            header = f"{icon} {r['id']} · {r['name']}  —  {r['status']} ({int(r['progress'])}%) · {r['owner']}"
            expanded = r["status"] in ("진행중", "검토중") or bool(r.get("blocker"))
            with st.expander(header, expanded=expanded):
                detail_block(r)

    st.divider()
    with st.expander("전체 표로 보기"):
        st.dataframe(
            df[["id", "phase", "name", "owner", "status", "progress", "due"]],
            use_container_width=True, hide_index=True,
        )


st.title("항공안전법령 RAG 검증 — 진행 현황")
dashboard()
