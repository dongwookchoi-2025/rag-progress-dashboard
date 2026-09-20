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
STATIC_DIR = "static"

STATUS_COLOR = {"완료": "🟢", "검토중": "🟡", "진행중": "🔵", "미착수": "⚪"}

# ── 논문 정보 ──────────────────────────────────────────────────
# 제목·저자·요약·주요지표를 여기 한 곳에서 관리합니다.
# 지표는 2026-09-20 기준 Research_Master.xlsx(정본)·research_pipeline.log·
# progress.json·논문 초안 V0.4에서 확인한 "실측·동결값"만 기재했습니다.
PAPER = {
    "title_ko": "구조·시간·인식 그래프 RAG를 활용한 "
                "대한민국 항공안전법령 질의응답 신뢰성 검증 연구",
    "title_en": "A Validation Study of Structure-Aware Temporal Graph RAG "
                "for Reliable Question Answering over Korean Aviation "
                "Safety Regulations",
    "venue": "한국항공운항학회 투고 예정",
    # 대시보드 요약 정보
    "submit_venue": "한국항공운항학회 (26년 12월 발행)",
    "expected_end": "2026년 10월 4일",
    "advisor_meeting": "2026년 10월 5일 21시 (한국시간)",
    "meeting_link": "https://teams.live.com/meet/9349506101230?p=0DiRlJMahcZsydxd0d",
    "summary": (
        "본 연구는 대한민국 고정익 항공운송사업 운항승무원 규정을 대상으로 네 가지 "
        "RAG 시스템 — 현행 Vector(A), 전체버전 Naive(B), Temporal-Filtered Vector(C), "
        "구조·시간·인식 그래프 SAT-Graph(D) — 의 질의응답 신뢰성을 동일 문항 반복측정 "
        "(paired design)으로 비교·검증한다. 평가는 파일럿 20문항으로 설정을 동결한 뒤 "
        "Hold-out 80문항으로 최종 측정하며, 검색성능·버전정확도·시간정합성·답변정확성·"
        "인용품질·환각률·거절정확도·지연/비용을 분리해 측정하고 오류를 검색·시간·관계·"
        "생성·인용 단계로 추적한다. B와 C의 차이로 시간필터의 순효과를, C와 D의 차이로 "
        "법령구조·관계탐색의 추가효과를 분리 추정한다."
    ),
    "authors": {
        "주저자": "최동욱",
        "공동저자": "설지원, 정재훈, 손상우",
        "교신저자": "이규정 교수",
    },
    "as_of": "2026-09-20",

    # 본실험(Hold-out 80문항, A/B/C/D 최종 성능비교) 완료 여부.
    # Research_Master.xlsx의 FINAL_METRICS/STATISTICS/Blind_Scores 시트가
    # 채워지면 True로 바꾸고 아래 final_* 를 입력하세요.
    "holdout_done": False,
    "status_note": (
        "**본실험(Hold-out 80문항 · A/B/C/D 최종 성능비교)은 아직 실행 전입니다.** "
        "Research_Master.xlsx의 `FINAL_METRICS`·`STATISTICS`·`Blind_Scores` 시트는 "
        "현재 비어 있고(Phase 6~8 진행 전), TT33(Gold 100문항)은 전문가 검토 대기 상태입니다. "
        "따라서 답변정확성·충실도·환각률 등 **시스템 간 최종 비교지표는 아직 산출되지 않았습니다.** "
        "아래는 그때까지 확보된 **실측·동결값**입니다."
    ),

    # ① 데이터·코퍼스 구축 (동결, 실측)
    "metrics_corpus": [
        {"label": "원문 파일", "value": "99건", "help": "95 XML + 4 PDF (FRZ-TT09-001, cutoff 2026-09-09)"},
        {"label": "조문 컴포넌트", "value": "239,509", "help": "4 norm · 93 semantic doc version 파싱"},
        {"label": "버전(Provision Version)", "value": "212,970", "help": "CURRENT 4,770 / EXPIRED 203,831 / FUTURE 1,704 등"},
        {"label": "최종 검색단위(CONTENT)", "value": "20,957", "help": "법령본문 6,822 + 구조화 운항요건 14,135"},
        {"label": "개정 액션 / 엣지", "value": "6,058 / 18,174", "help": "TT18 amendment actions / directed edges"},
        {"label": "법적 관계", "value": "875", "help": "위계·참조·위임·개정·승인의존 관계"},
    ],

    # ② TT21 청킹 선정 검색성능 (파일럿 20문항, 동결 2026-09-18)
    #    최종 채택 청킹 = structural_article_paragraph
    "metrics_tt21": [
        {"label": "Hit@10", "value": "80.0%"},
        {"label": "Hit@5", "value": "75.0%"},
        {"label": "Recall@5", "value": "57.0%", "help": "2위 후보 대비 +10.5%p"},
        {"label": "MRR@10", "value": "58.3%"},
        {"label": "nDCG@5", "value": "0.486"},
        {"label": "청크 수", "value": "15,654", "help": "일반 후보 대비 약 29% 감소"},
    ],

    # ③ SAT-Graph 지식그래프 규모 (Neo4j 재구축, 2026-09-18 실측)
    "metrics_graph": [
        {"label": "그래프 노드", "value": "289,575", "help": "CTV 212,970 · TextUnit 60,092 · Component 10,451 · Action 6,058 · Norm 4"},
        {"label": "그래프 엣지", "value": "485,907", "help": "HAS_VERSION 212,970 · SUPERSEDES 199,854 · HAS_TEXT 60,092 · CREATES/TERMINATES 각 6,058 · DELEGATES_TO 658 · IMPLEMENTS 217"},
    ],

    # ④ 파일럿 20문항 시스템별 런타임 상태
    #    (Development_Pilots, 최신 run 기준) — 최종 성능지표 아님(runtime health)
    "pilot_rows": [
        {"시스템": "A · Current Vector", "정상(pass)": "18/20", "판단보류(abstain)": 3, "오류(error)": 2},
        {"시스템": "B · All-Version Naive", "정상(pass)": "11/20", "판단보류(abstain)": 6, "오류(error)": 9},
        {"시스템": "C · Temporal-Filtered", "정상(pass)": "19/20", "판단보류(abstain)": 3, "오류(error)": 1},
        {"시스템": "D · SAT-Graph", "정상(pass)": "19/20", "판단보류(abstain)": 3, "오류(error)": 1},
    ],

    # ⑤ 본실험 완료 시 채울 최종 비교표 (지금은 비움)
    #    컬럼 예: {"지표": "답변정확성", "A": "", "B": "", "C": "", "D": ""}
    "final_table": [],

    "sources": (
        "Research_Master.xlsx(정본) · research_pipeline.log · progress.json · "
        "논문 초안 V0.4 (Google Drive, 2026-09-20 기준)"
    ),
}


def _download_button(filename, label, mime, key):
    """static/ 폴더의 원고 파일을 다운로드 버튼으로 노출."""
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            st.download_button(label, data=f.read(), file_name=filename,
                               mime=mime, key=key, use_container_width=True)
    else:
        st.caption(f"⚠️ {filename} 없음 ({path})")


def paper_header():
    """상단: 정식 제목 · 영문 제목 · 다운로드 · 연구요약 · 저자."""
    st.title(PAPER["title_ko"])
    st.markdown(f"*{PAPER['title_en']}*")
    if PAPER.get("venue"):
        st.caption(PAPER["venue"])

    d1, d2, _ = st.columns([1, 1, 3])
    with d1:
        _download_button("manuscript.pdf", "📄 논문 PDF 다운로드",
                         "application/pdf", key="dl_pdf")
    with d2:
        _download_button("manuscript.hwp", "📝 논문 HWP 다운로드",
                         "application/x-hwp", key="dl_hwp")

    st.subheader("연구요약")
    st.markdown(PAPER["summary"])

    a = PAPER["authors"]
    st.markdown(
        f"**주저자** {a['주저자']}　·　"
        f"**공동저자** {a['공동저자']}　·　"
        f"**교신저자** {a['교신저자']}"
    )
    st.divider()


def _metric_cards(items):
    if not items:
        return
    cols = st.columns(len(items))
    for col, m in zip(cols, items):
        col.metric(m.get("label", ""), m.get("value", "—"), help=m.get("help"))


def key_metrics_panel():
    """맨 아래: 연구 주요 중요지표 (실측·동결값)."""
    st.divider()
    st.subheader("주요 중요지표")
    st.caption(f"기준 {PAPER['as_of']}  ·  출처: {PAPER['sources']}")

    if not PAPER.get("holdout_done"):
        st.warning(PAPER["status_note"])

    st.markdown("##### ① 데이터·코퍼스 구축 (동결)")
    _metric_cards(PAPER.get("metrics_corpus"))

    st.markdown("##### ② 최종 청킹 검색성능 · structural_article_paragraph (TT21 파일럿 20문항, 동결)")
    _metric_cards(PAPER.get("metrics_tt21"))

    st.markdown("##### ③ SAT-Graph 지식그래프 규모 (Neo4j, 실측)")
    _metric_cards(PAPER.get("metrics_graph"))

    st.markdown("##### ④ 파일럿 20문항 시스템별 런타임 상태")
    if PAPER.get("pilot_rows"):
        st.dataframe(pd.DataFrame(PAPER["pilot_rows"]),
                     use_container_width=True, hide_index=True)
    st.caption("※ pass/abstain/error는 실행 안정성(runtime health) 점검치이며, "
               "논문에 보고할 최종 성능지표가 아닙니다. 최종 성능은 Hold-out 80문항 본실험(TT37·TT38)에서 산출됩니다.")

    if PAPER.get("final_table"):
        st.markdown("##### ⑤ 본실험 최종 비교 (Hold-out 80문항)")
        st.dataframe(pd.DataFrame(PAPER["final_table"]),
                     use_container_width=True, hide_index=True)


@st.cache_data(ttl=10)          # 원본을 10초에 한 번만 재조회
def load_data():
    with open(SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["tasks"])
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").fillna(0).astype(int)
    return data.get("as_of", ""), data.get("action_plan"), df, data.get("handoff_note", "")


def _issue_is_clean(txt):
    """오류가 없는(또는 해당 없는) 이슈 문구인지 판정."""
    t = (txt or "").strip()
    return (not t) or ("오류 0" in t) or t.startswith("해당 없음") or t.startswith("차단오류 없음")


def detail_block(r):
    """펼쳤을 때 보이는 상세 작업내용 — 연구결과 요약·산출물·오류/이슈를 함께 표시."""
    # 연구결과 요약 (무엇이 나왔나) — 가장 위에 강조
    if r.get("result"):
        st.info(f"📊 **연구결과 요약**　{r['result']}")

    # 핵심 수치 표 (지표 · 값)
    metrics = r.get("metrics")
    if isinstance(metrics, list) and metrics:
        st.markdown("**핵심 수치**")
        st.dataframe(pd.DataFrame(metrics, columns=["지표", "값"]),
                     use_container_width=True, hide_index=True)

    st.markdown(f"**핵심목표**  {r['goal']}")
    if r.get("detail"):
        st.markdown(f"**작업내용**  {r['detail']}")

    # 결과 표(청킹 비교 등) — 일부 TT에만 존재하므로 리스트일 때만 렌더
    tables = r.get("tables")
    if isinstance(tables, list):
        for tb in tables:
            st.markdown(f"**{tb.get('title','')}**")
            st.dataframe(pd.DataFrame(tb.get("rows", []), columns=tb.get("columns")),
                         use_container_width=True, hide_index=True)

    # 파일럿 Gold 질문 등
    questions = r.get("questions")
    if isinstance(questions, list) and questions:
        st.markdown(f"**파일럿 Gold 질문 ({len(questions)}문항)**")
        st.dataframe(pd.DataFrame(questions),
                     use_container_width=True, hide_index=True)

    # 산출물
    if r.get("outputs"):
        st.markdown(f"**산출물**  {r['outputs']}")
    if r.get("inputs"):
        st.caption(f"주요 입력: {r['inputs']}")

    # 오류 / 이슈
    issue = r.get("issues", "")
    if _issue_is_clean(issue):
        st.caption(f"✅ 오류/이슈: {issue or '무결성/QA 검사 통과 — 오류 0'}")
    else:
        st.warning(f"**⚠️ 오류/이슈**  {issue}")

    # 현재 차단/보류 사유(있을 때만)
    if r.get("blocker"):
        st.error(f"**⛔ 차단/보류 사유**  {r['blocker']}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**선행 Task**  {r.get('pred') or '—'}")
    with c2:
        st.markdown(f"**후속 Task**  {r.get('succ') or '—'}")
    if r.get("collab"):
        st.caption(f"협업/검토: {r['collab']}")

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
    as_of, ap, df, handoff = load_data()

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
    now_wat = pd.Timestamp.now(tz="Africa/Lagos")
    head_l.caption(
        f"데이터 기준 {as_of}{mtime_txt}  ·  원본: Research_Master.xlsx TEAM_TASKS_40"
        f"  ·  화면 갱신 {now_wat:%H:%M:%S} (WAT/나이지리아, KST=+8h)"
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

    # 전체 공정률 아래 요약 정보
    st.markdown(
        f"**투고예정학회:** {PAPER['submit_venue']}  \n"
        f"**예상 작업종료일:** {PAPER['expected_end']}  \n"
        f"**지도교수님과 논문초안 리뷰 미팅:** {PAPER['advisor_meeting']}  \n"
        f"**미팅링크:** {PAPER['meeting_link']}"
    )
    st.caption("⏰ 모든 업데이트/갱신 시간은 나이지리아(WAT) 기준입니다. 한국시간(KST)은 +8시간 하세요.")

    if handoff:
        st.warning(f"🔄 **재실행 대기 (핸드오프 2026-09-20)**　{handoff}")
    st.divider()

    action_plan_panel(ap)
    if ap:
        st.divider()

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


# ── 페이지 구성 ────────────────────────────────────────────────
paper_header()                 # 제목·영문제목·다운로드·요약·저자

st.header("진행 현황")
dashboard()                    # 기존 진행현황 대시보드

key_metrics_panel()            # 맨 아래: 주요 중요지표(실측·동결값)
