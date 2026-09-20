import os
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="항공안전법령 RAG 검증 진행 현황", layout="wide")

# ── 데이터 소스 ────────────────────────────────────────────────
# 상세 진행 데이터는 progress.json 하나에 들어 있습니다. 이 파일은
# Research_Master.xlsx의 TEAM_TASKS_40 시트를 기준으로 만든 스냅샷이라,
# 마스터가 바뀌면 이 JSON만 새 버전으로 교체하면 됩니다.
SOURCE = "progress.json"

STATUS_COLOR = {"완료": "🟢", "검토중": "🟡", "진행중": "🔵", "미착수": "⚪"}


@st.cache_data(ttl=10)          # 원본을 10초에 한 번만 재조회
def load_data():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["tasks"])
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").fillna(0).astype(int)
    return data.get("as_of", ""), data.get("manuscript"), df


@st.cache_data(ttl=10)
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

    # 다운로드 버튼 (저장소에 담긴 파일 바이트를 그대로 내려줌 — 원본 그대로)
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
    """펼쳤을 때 보이는 상세 작업내용."""
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


@st.fragment(run_every="10s")   # 이 블록만 10초마다 자동 갱신
def dashboard():
    as_of, manuscript, df = load_data()

    total = len(df)
    done = (df["status"] == "완료").sum()
    active = df["status"].isin(["진행중", "검토중"]).sum()
    todo = (df["status"] == "미착수").sum()
    overall = int(round(df["progress"].mean())) if total else 0

    head_l, head_r = st.columns([4, 1])
    mtime_txt = ""
    if os.path.exists(SOURCE):
        mtime = pd.Timestamp(os.path.getmtime(SOURCE), unit="s", tz="Africa/Lagos")
        mtime_txt = f"  ·  파일 최종수정 {mtime:%Y-%m-%d %H:%M}"
    head_l.caption(
        f"데이터 기준 {as_of}{mtime_txt}  ·  원본: Research_Master.xlsx TEAM_TASKS_40"
        f"  ·  화면 갱신 {pd.Timestamp.now():%H:%M:%S}"
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
    st.divider()

    # ── 최신 원고 (PDF 뷰어 + 다운로드) ────────────────────────
    manuscript_section(manuscript)

    # ── Phase별 요약 ───────────────────────────────────────────
    st.subheader("Phase별 진행률")
    for phase, g in df.groupby("phase", sort=False):
        pct = int(round(g["progress"].mean()))
        label, bar = st.columns([2, 3])
        label.markdown(f"**{phase}**  ·  {(g['status']=='완료').sum()}/{len(g)} 완료")
        bar.progress(pct / 100, text=f"{pct}%")
    st.divider()

    # ── Task 상세 (클릭하면 펼쳐짐) ─────────────────────────────
    st.subheader("Task 상세 — 항목을 클릭하면 작업내용이 펼쳐집니다")
    show_done = st.checkbox("완료 항목도 보기", value=False)
    view = df if show_done else df[df["status"] != "완료"]

    for phase, group in view.groupby("phase", sort=False):
        st.markdown(f"#### {phase}")
        for _, r in group.iterrows():
            icon = STATUS_COLOR.get(r["status"], "")
            header = f"{icon} {r['id']} · {r['name']}  —  {r['status']} ({int(r['progress'])}%) · {r['owner']}"
            # 진행중·검토중·차단 항목은 기본으로 펼쳐서 눈에 띄게
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
