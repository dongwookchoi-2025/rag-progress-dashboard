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

# ── 논문 정보 ──────────────────────────────────────────────────
# 제목·저자·요약·주요지표를 여기 한 곳에서 관리합니다.
# static/ 폴더에 manuscript.pdf, manuscript.hwp 원고가 있어야 다운로드 버튼이 활성화됩니다.
PAPER = {
    "title_ko": "구조·시간·인식 그래프 RAG를 활용한 "
                "대한민국 항공안전법령 질의응답 신뢰성 검증 연구",
    # 공식 영문 제목이 확정되면 아래를 교체하세요 (현재는 국문 기준 초안).
    "title_en": "Verifying the Reliability of Question Answering on Korea's "
                "Aviation Safety Legislation Using Structural, Temporal, "
                "and Cognitive Graph RAG",
    "venue": "한국항공운항학회 투고 예정",
    # 연구요약(초록) — 확정 초록이 있으면 교체하세요 (현재는 연구설계 기준 초안).
    "summary": (
        "본 연구는 대한민국 항공안전법령을 대상으로 네 가지 RAG(검색증강생성) "
        "시스템 — 현행 Vector 기반, 전체버전 Naive, Temporal-Filtered, 그리고 "
        "구조·시간·인식 그래프(SAT-Graph) — 의 질의응답 신뢰성을 비교·검증한다. "
        "법령 특유의 개정 이력과 조문 간 참조 구조가 답변의 정확도와 시점 정합성에 "
        "미치는 영향을 분석하고, 그래프 기반 접근이 환각(hallucination)과 시점 오류를 "
        "얼마나 줄이는지를 정량적으로 평가한다."
    ),
    "authors": {
        "주저자": "최동욱",
        "공동저자": "설지원, 정재훈, 손상우",
        "교신저자": "이규정 교수",
    },
    # ▼▼ 주요 중요지표 — 실제 실험 결과값으로 채우세요 ▼▼
    #   각 항목: {"label": 지표명, "value": 값, "help": 보조설명(선택)}
    #   값이 하나도 없으면 대시보드에는 "입력 필요" 안내가 표시됩니다.
    #   예시(형식만 참고 — 실제 수치로 교체):
    #     {"label": "정답 정확도 (Accuracy)",     "value": "0.00", "help": "SAT-Graph"},
    #     {"label": "충실도 (Faithfulness)",       "value": "0.00", "help": "SAT-Graph"},
    #     {"label": "시점 정합성 (Temporal Acc.)", "value": "0.00"},
    #     {"label": "환각률 (Hallucination)",      "value": "0.0%"},
    "key_metrics": [],
    # 4개 시스템 비교표를 넣고 싶으면 아래에 행을 채우세요(선택).
    #   컬럼: system, accuracy, faithfulness, temporal, hallucination
    #   예: {"system": "SAT-Graph", "accuracy": "0.00", "faithfulness": "0.00",
    #        "temporal": "0.00", "hallucination": "0.0%"}
    "systems_table": [],
}

STATIC_DIR = "static"


def _download_button(filename, label, mime, key):
    """static/ 폴더의 원고 파일을 다운로드 버튼으로 노출."""
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            st.download_button(
                label,
                data=f.read(),
                file_name=filename,
                mime=mime,
                key=key,
                use_container_width=True,
            )
    else:
        st.caption(f"⚠️ {filename} 없음 ({path})")


def paper_header():
    """상단: 정식 제목 · 영문 제목 · 다운로드 · 연구요약 · 저자."""
    st.title(PAPER["title_ko"])
    st.markdown(f"*{PAPER['title_en']}*")
    if PAPER.get("venue"):
        st.caption(PAPER["venue"])

    # 논문 다운로드 링크
    d1, d2, _ = st.columns([1, 1, 3])
    with d1:
        _download_button("manuscript.pdf", "📄 논문 PDF 다운로드",
                         "application/pdf", key="dl_pdf")
    with d2:
        _download_button("manuscript.hwp", "📝 논문 HWP 다운로드",
                         "application/x-hwp", key="dl_hwp")

    # 연구요약
    st.subheader("연구요약")
    st.markdown(PAPER["summary"])

    # 저자 정보 (요약 바로 밑)
    a = PAPER["authors"]
    st.markdown(
        f"**주저자** {a['주저자']}　·　"
        f"**공동저자** {a['공동저자']}　·　"
        f"**교신저자** {a['교신저자']}"
    )
    st.divider()


def key_metrics_panel():
    """맨 아래: 연구 주요 중요지표."""
    st.divider()
    st.subheader("주요 중요지표")

    metrics = PAPER.get("key_metrics") or []
    table = PAPER.get("systems_table") or []

    if not metrics and not table:
        st.info(
            "지표 값이 아직 입력되지 않았습니다. "
            "app.py 상단의 `PAPER[\"key_metrics\"]`(핵심 지표) 또는 "
            "`PAPER[\"systems_table\"]`(4개 시스템 비교표)에 "
            "실제 실험 결과값을 넣으면 이 자리에 표시됩니다."
        )
        return

    # 핵심 지표 카드
    if metrics:
        cols = st.columns(len(metrics))
        for col, m in zip(cols, metrics):
            col.metric(m.get("label", ""), m.get("value", "—"),
                       help=m.get("help"))

    # 4개 시스템 비교표
    if table:
        st.markdown("**시스템별 비교**")
        tdf = pd.DataFrame(table).rename(columns={
            "system": "시스템",
            "accuracy": "정확도",
            "faithfulness": "충실도",
            "temporal": "시점 정합성",
            "hallucination": "환각률",
        })
        st.dataframe(tdf, use_container_width=True, hide_index=True)


@st.cache_data(ttl=10)          # 원본을 10초에 한 번만 재조회
def load_data():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["tasks"])
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").fillna(0).astype(int)
    return data.get("as_of", ""), data.get("action_plan"), df


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
    st.caption(f"담당 {r['owner']}  ·  마감 {r['due']}  ·  진행률 {int(r['progress'])}%")
    st.progress(int(r["progress"]) / 100)


AP_STATUS_ICON = {"완료": "✅", "부분적": "🟡", "미착수": "⬜"}


def action_plan_panel(ap):
    """TT29–32 Action Plan 적용 현황 요약 패널 (progress.json 의 action_plan 블록을 렌더링)."""
    if not ap:
        return
    fs = ap.get("freeze_status", "")
    badge = {"PROVISIONAL": "🟠 PROVISIONAL · freeze 보류",
             "FROZEN": "🟢 FROZEN"}.get(fs, fs)
    st.subheader(f"{ap.get('title', 'Action Plan 적용 현황')}  —  {badge}")
    aptasks = ap.get("tasks", [])
    done_n = sum(1 for t in aptasks if t.get("status") == "완료")
    st.caption(
        f"Task {done_n}/{len(aptasks)} 완료  ·  "
        f"Acceptance checklist {ap.get('checklist_done', '?')}/{ap.get('checklist_total', '?')} 충족  ·  "
        f"기준 {ap.get('as_of', '')}"
    )
    if ap.get("freeze_note"):
        st.info(ap["freeze_note"])
    for t in aptasks:
        ic = AP_STATUS_ICON.get(t.get("status"), "")
        st.markdown(f"{ic}  **{t.get('id', '')}** · {t.get('name', '')} — {t.get('status', '')}")
        if t.get("note"):
            st.caption(f"　└ {t['note']}")
    if ap.get("ref_docs"):
        st.caption(f"기준 문서: {ap['ref_docs']}")


@st.fragment(run_every="10s")   # 이 블록만 10초마다 자동 갱신
def dashboard():
    as_of, ap, df = load_data()

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

    # ── TT29–32 Action Plan 적용 현황 ──────────────────────────
    action_plan_panel(ap)
    if ap:
        st.divider()

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


# ── 페이지 구성 ────────────────────────────────────────────────
paper_header()                 # 제목·영문제목·다운로드·요약·저자

st.header("진행 현황")
dashboard()                    # 기존 진행현황 대시보드

key_metrics_panel()            # 맨 아래: 주요 중요지표
