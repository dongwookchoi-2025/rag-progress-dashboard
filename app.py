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
        # 상태 색 아이콘 (앞부분 매칭)
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
