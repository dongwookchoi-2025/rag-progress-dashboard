# -*- coding: utf-8 -*-
"""Aviation RAG 연구 대시보드 — 완전 재설계 (2026-10-14, plotly-free)"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import date

# ── 페이지 설정 ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Aviation RAG 연구 대시보드",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; color: #e0e0e0; }
[data-testid="stHeader"] { background: transparent; }
.hero-card {
    background: linear-gradient(135deg, #1a1f35 0%, #0d1b2a 100%);
    border: 1px solid #2a3a5c; border-radius: 16px;
    padding: 28px 32px; margin-bottom: 20px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.hero-title { font-size: 1.5rem; font-weight: 700; color: #5dade2; line-height: 1.4; margin-bottom: 8px; }
.hero-summary { font-size: 0.87rem; color: #a0aec0; line-height: 1.6; margin-bottom: 16px; }
.hero-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 0.82rem; }
.hero-badge { background: #1e2d45; border: 1px solid #2a3a5c; border-radius: 8px;
              padding: 5px 12px; color: #90caf9; white-space: nowrap; }
.hero-badge span { color: #e0e0e0; }
.stage-banner { background: linear-gradient(90deg, #1a3a2a 0%, #162d3a 100%);
                border-left: 4px solid #27ae60; border-radius: 8px;
                padding: 10px 16px; margin-top: 14px; font-size: 0.85rem; color: #a8e6c3; }
.sec-header { font-size: 1.05rem; font-weight: 700; color: #90caf9;
              border-bottom: 1px solid #2a3a5c; padding-bottom: 6px; margin: 20px 0 14px 0; }
.big-metric { text-align: center; background: #161b2e; border: 1px solid #2a3a5c;
              border-radius: 10px; padding: 14px 10px; }
.big-metric-val { font-size: 2rem; font-weight: 800; color: #5dade2; }
.big-metric-label { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
.task-card-done { background: #0d1f14; border: 1px solid #1a4a2a; border-left: 4px solid #27ae60;
                  border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; }
.task-card-progress { background: #0d1a2a; border: 1px solid #1a3a5c; border-left: 4px solid #2e86de;
                      border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; }
.task-card-pending { background: #1a1a1a; border: 1px solid #2a2a2a; border-left: 4px solid #5a5a5a;
                     border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; opacity: 0.75; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.task-id { font-weight: 700; font-size: 0.85rem; }
.task-name { font-size: 0.88rem; color: #c8d8f0; }
.task-owner { font-size: 0.75rem; color: #94a3b8; }
.pct-done { font-size: 0.8rem; color: #27ae60; font-weight: 600; }
.pct-prog { font-size: 0.8rem; color: #2e86de; font-weight: 600; }
.pct-pend { font-size: 0.8rem; color: #718096; font-weight: 600; }
.task-goal { font-size: 0.78rem; color: #94a3b8; margin-top: 4px; line-height: 1.5; }
.task-blocker { font-size: 0.77rem; color: #f59e0b; margin-top: 6px;
                background: #1a1200; border-radius: 6px; padding: 6px 10px; }
.task-next { font-size: 0.77rem; color: #7dcfff; margin-top: 6px;
             background: #04111f; border-radius: 6px; padding: 6px 10px; }
.phase-header { font-size: 0.9rem; font-weight: 600; color: #7dcfff; margin: 16px 0 8px 0;
                padding: 6px 12px; background: #111827; border-radius: 6px; border-left: 3px solid #2e86de; }
.prog-bar-bg { background: #1e2d45; border-radius: 4px; height: 12px; }
.prog-bar-fill { border-radius: 4px; height: 12px; }
.rq-signal { font-size: 0.8rem; color: #94a3b8; background: #0d1520; border-radius: 6px;
             padding: 10px 14px; line-height: 1.6; border-left: 3px solid #3d6ff5; }
</style>
""", unsafe_allow_html=True)

# ── TT36 Pilot 실측 데이터 (2026-10-14) ──────────────────────────
TT36_METRICS = {
    "hit":    {"5":  {"A":70,"B":20,"C":70,"D":60},
               "10": {"A":75,"B":30,"C":75,"D":75},
               "20": {"A":80,"B":40,"C":80,"D":80}},
    "recall": {"5":  {"A":39.6,"B":4.2, "C":39.6,"D":31.3},
               "10": {"A":52.1,"B":12.5,"C":56.3, "D":47.9},
               "20": {"A":56.3,"B":20.8,"C":60.4, "D":60.4}},
    "mrr":    {"5":  {"A":0.441,"B":0.107,"C":0.444,"D":0.347},
               "10": {"A":0.475,"B":0.147,"C":0.500,"D":0.407},
               "20": {"A":0.476,"B":0.150,"C":0.501,"D":0.407}},
    "ndcg":   {"5":  {"A":0.374,"B":0.079,"C":0.378,"D":0.311},
               "10": {"A":0.408,"B":0.115,"C":0.438,"D":0.363},
               "20": {"A":0.413,"B":0.121,"C":0.444,"D":0.367}},
}
VERSION_VALIDITY = {
    "A":{"유효(현행)":158,"미래 시행":42,"만료":0},
    "B":{"유효(현행)":14, "미래 시행":21,"만료":165},
    "C":{"유효(현행)":199,"미래 시행":0, "만료":0},
    "D":{"유효(현행)":199,"미래 시행":0, "만료":0},
}
TT36_D_DIAGNOSTICS = [
    ("Q001","SAT-Graph 정상","GRAPH OK","D 정상"),
    ("Q002","추상 개념 조회","GRAPH OK","D 정상 – 엔티티 추출 성공"),
    ("Q003","조문 직접 참조","GRAPH OK","D 정상"),
    ("Q004","별표 행 조회","GRAPH OK","D 정상"),
    ("Q005","Scope=97/ANN=0","FILTERED_ANN_EMPTY","scoped_search=0"),
    ("Q006","자격 엔티티 미매핑","GRAPH_SCOPE_EMPTY","Neo4j 노드 없음 → C fallback"),
    ("Q007","Gold 청크 2개","GRAPH OK","두 청크 모두 검색"),
    ("Q008","현행 조문 조회","GRAPH OK","D 정상"),
    ("Q009","기장·운항승무원","GRAPH_SCOPE_EMPTY","엔티티 미매핑 → C fallback"),
    ("Q010","별표 기준값","GRAPH OK","D 정상"),
    ("Q011","terms=[] 빈 추출","GRAPH_SCOPE_EMPTY","파서 추출 실패 → C fallback"),
    ("Q012","Scope=3/ANN=0","FILTERED_ANN_EMPTY","필터 후 결과 없음 → C fallback"),
    ("Q013","Abstract 기준","GRAPH OK","D 정상"),
    ("Q014","별표 36 기술기준","GRAPH OK","D 정상"),
    ("Q015","시간 경계 조문","GRAPH OK","D 정상"),
    ("Q016","편법 참조","GRAPH_SCOPE_EMPTY","참조 조항 미매핑 → C fallback"),
    ("Q017","제148조 미매핑","GRAPH_SCOPE_EMPTY","노드 없음 → C fallback"),
    ("Q018","제144조 미매핑","GRAPH_SCOPE_EMPTY","노드 없음 → C fallback"),
    ("Q019","제36조 미매핑","GRAPH_SCOPE_EMPTY","노드 없음 → C fallback"),
    ("Q020","제63조 미매핑","GRAPH_SCOPE_EMPTY","노드 없음 → C fallback"),
]

# ── 데이터 로더 ───────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_data():
    with open("extras.json", encoding="utf-8") as f:
        ex = json.load(f)
    df = pd.read_csv("task_grid.csv", encoding="utf-8-sig")
    df["progress"] = pd.to_numeric(df["progress"], errors="coerce").fillna(0).astype(int)
    return ex, df

def scls(s):
    if s == "완료": return "task-card-done"
    if s in ("진행중","검토중"): return "task-card-progress"
    return "task-card-pending"

def pcls(s):
    if s == "완료": return "pct-done"
    if s in ("진행중","검토중"): return "pct-prog"
    return "pct-pend"

# ── 막대 HTML (plotly 대체) ──────────────────────────────────────
def bar_chart_html(systems, values, labels=None, colors=None, title="", fmt=".1f"):
    if colors is None:
        colors = ["#3498db","#e74c3c","#2ecc71","#f39c12"]
    if labels is None:
        labels = systems
    max_v = max(values) if max(values) > 0 else 1
    bars = ""
    for i, (s, v) in enumerate(zip(labels, values)):
        pct = v / max_v * 100
        vfmt = f"{v:{fmt}}"
        bars += f"""
        <div style="display:flex;align-items:center;margin-bottom:8px;gap:8px">
          <div style="width:80px;font-size:0.8rem;color:#94a3b8;text-align:right">{s}</div>
          <div style="flex:1;background:#1e2d45;border-radius:4px;height:22px;position:relative">
            <div style="width:{pct:.1f}%;background:{colors[i%len(colors)]};border-radius:4px;height:22px;
                        display:flex;align-items:center;padding-left:6px;
                        font-size:0.78rem;color:#fff;font-weight:600;white-space:nowrap">
              {vfmt}
            </div>
          </div>
        </div>"""
    return f'<div style="margin:8px 0"><div style="font-size:0.85rem;color:#90caf9;margin-bottom:10px;font-weight:600">{title}</div>{bars}</div>'

# ── 헤더 ────────────────────────────────────────────────────────
def render_header(ex):
    ms = ex["manuscript"]
    st.markdown(f"""
<div class="hero-card">
  <div class="hero-title">✈️ {ms['title']}</div>
  <div class="hero-summary">
    대한민국 항공안전법령에서 동일 법령 코퍼스·임베딩(BGE-M3)·생성 LLM을 통제한 상태로
    네 가지 검색 방식을 비교하는 Validation Study.
    <b style="color:#5dade2">B–C 비교</b>로 시간 필터 효과를,
    <b style="color:#5dade2">C–D 비교</b>로 SAT-Graph 구조 정보의 추가 효과를 분리 측정.
  </div>
  <div class="hero-meta">
    <div class="hero-badge">👤 연구책임자 <span>{ms['lead_author']}</span></div>
    <div class="hero-badge">👥 공동연구원 <span>{ms['co_authors']}</span></div>
    <div class="hero-badge">🎓 지도교수 <span>{ms['corresponding_author']}</span></div>
    <div class="hero-badge">📅 투고예정일 <span>2026-10-31</span></div>
    <div class="hero-badge">🏛️ 투고학회 <span>{ms['target_journal']}</span></div>
  </div>
  <div class="stage-banner">
    🔵 현재 단계: Phase 7 진행중 — TT36 Pilot 실행 완료(기술 Freeze 2026-10-14), 공식 동결 승인 및 TT37 Hold-out 본실험 대기
  </div>
</div>
""", unsafe_allow_html=True)

# ── RQ 섹션 ────────────────────────────────────────────────────
def render_rq(ex):
    st.markdown('<div class="sec-header">📌 연구 질문 (RQ) 및 현재 단계 답변</div>', unsafe_allow_html=True)
    systems = ["A","B","C","D"]
    sys_colors = ["#3498db","#e74c3c","#2ecc71","#f39c12"]
    hl_map = {"RQ1":["A","B"],"RQ2":["B","C"],"RQ3":["C","D"],"RQ4":["A","B","C","D"]}

    for rq in ex["research_questions"]:
        with st.expander(f"**{rq['id']}** — {rq['question'][:70]}…", expanded=(rq["id"] in ("RQ1","RQ2","RQ3"))):
            c1, c2 = st.columns([3,1])
            with c1:
                st.markdown(f"**❓ 질문:** {rq['question']}")
                st.markdown(f"**🔬 가설 방향:** `{rq['expected_direction']}`")
                signal = rq["current_signal"].replace("【","").replace("】","")
                st.markdown(f'<div class="rq-signal">{signal}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f"**비교:** `{rq['linked_comparison']}`")
                st.markdown(f"**상태:** {rq['status']}")

            if rq["id"] in ("RQ1","RQ2","RQ3","RQ4"):
                st.markdown("**MRR@10 비교:**")
                mrr_vals = [TT36_METRICS["mrr"]["10"][s] for s in systems]
                st.markdown(bar_chart_html(systems, mrr_vals, title="MRR@10", colors=sys_colors, fmt=".3f"), unsafe_allow_html=True)
                st.markdown("**Hit@10 (%) 비교:**")
                hit_vals = [TT36_METRICS["hit"]["10"][s] for s in systems]
                st.markdown(bar_chart_html(systems, hit_vals, title="Hit@10 (%)", colors=sys_colors, fmt=".0f"), unsafe_allow_html=True)

# ── Pilot 탭 ───────────────────────────────────────────────────
def render_pilot():
    st.markdown('<div class="sec-header">🧪 TT36 Pilot 20문항 × 4시스템 성능 분석 (2026-10-14 실측)</div>', unsafe_allow_html=True)
    st.caption("PROVISIONAL — NOT FROZEN. Diagnostic=80건, Error=0. 공식 Freeze 및 TT37 본실험 대기 중.")

    systems = ["A","B","C","D"]
    sys_colors = ["#3498db","#e74c3c","#2ecc71","#f39c12"]
    sys_labels = ["A (Current)","B (Naive)","C (Temporal)","D (SAT-Graph)"]

    t1, t2, t3, t4 = st.tabs(["Top-K 비교", "시스템간 비교", "System D 진단", "버전 유효성"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            k_sel = st.radio("Top-K", ["5","10","20"], index=1, horizontal=True, key="p_k")
        with c2:
            m_sel = st.radio("지표", ["Hit(%)","Recall(%)","MRR","nDCG"], index=0, horizontal=True, key="p_m")
        mk = {"Hit(%)":"hit","Recall(%)":"recall","MRR":"mrr","nDCG":"ndcg"}[m_sel]
        fmt = ".0f" if mk in ("hit","recall") else ".3f"
        vals = [TT36_METRICS[mk][k_sel][s] for s in systems]
        st.markdown(bar_chart_html(sys_labels, vals, title=f"{m_sel} @ Top-{k_sel}", colors=sys_colors, fmt=fmt), unsafe_allow_html=True)

    with t2:
        metric_set = [("Hit@5(%)","hit","5"),("Hit@10(%)","hit","10"),
                      ("Recall@10(%)","recall","10"),("MRR@10","mrr","10"),("nDCG@10","ndcg","10")]
        for m_label, mk, k in metric_set:
            fmt = ".0f" if mk in ("hit","recall") else ".3f"
            vals = [TT36_METRICS[mk][k][s] for s in systems]
            st.markdown(bar_chart_html(sys_labels, vals, title=m_label, colors=sys_colors, fmt=fmt), unsafe_allow_html=True)
            st.markdown("---")

    with t3:
        ok  = sum(1 for d in TT36_D_DIAGNOSTICS if d[2]=="GRAPH OK")
        gse = sum(1 for d in TT36_D_DIAGNOSTICS if d[2]=="GRAPH_SCOPE_EMPTY")
        fae = sum(1 for d in TT36_D_DIAGNOSTICS if d[2]=="FILTERED_ANN_EMPTY")
        st.markdown(bar_chart_html(
            ["GRAPH OK","GRAPH_SCOPE_EMPTY","FILTERED_ANN_EMPTY"],
            [ok, gse, fae],
            title="System D 20문항 진단 결과",
            colors=["#27ae60","#e74c3c","#f39c12"],
            fmt=".0f"
        ), unsafe_allow_html=True)
        df_d = pd.DataFrame(TT36_D_DIAGNOSTICS, columns=["문항","주제","진단","설명"])
        st.dataframe(df_d, hide_index=True, use_container_width=True)

    with t4:
        cats = ["유효(현행)","미래 시행","만료"]
        cat_colors = ["#27ae60","#f39c12","#e74c3c"]
        for cat, clr in zip(cats, cat_colors):
            vals = [VERSION_VALIDITY[s][cat] for s in systems]
            st.markdown(bar_chart_html(sys_labels, vals, title=f"Top-10 중 [{cat}] 건수",
                                       colors=[clr]*4, fmt=".0f"), unsafe_allow_html=True)

# ── Task 카드 ───────────────────────────────────────────────────
def render_task_card(row, show_detail, ex):
    tid = row["id"]
    s = row["status"]
    pct = int(row["progress"])
    emoji = "✅" if s=="완료" else ("🔵" if s in ("진행중","검토중") else "⬜")

    html = f"""
<div class="{scls(s)}">
  <div class="task-header">
    <span class="task-id">{emoji} {tid}</span>
    <span class="task-owner">담당: {row.get('owner','')}</span>
    <span class="{pcls(s)}">{pct}%</span>
  </div>
  <div class="task-name">{row['name']}</div>
  <div class="task-goal">🎯 {row.get('goal','')}</div>"""
    if s == "완료" and row.get("outputs"):
        html += f'<div class="task-goal">📦 {row["outputs"]}</div>'
    if s in ("진행중","검토중") and row.get("blocker"):
        html += f'<div class="task-blocker">⚠️ 대기: {row["blocker"]}</div>'
    if s == "미착수" and row.get("outputs"):
        html += f'<div class="task-next">📋 예정 산출물: {row.get("outputs","")}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    if show_detail and row.get("detail"):
        with st.expander(f"📄 {tid} 상세 보기"):
            st.markdown(row["detail"])
            if tid == "TT36":
                render_pilot()
            if tid == "TT21" and "tables" in ex and "TT21" in ex["tables"]:
                tbl = ex["tables"]["TT21"]
                st.caption(tbl["caption"])
                st.dataframe(pd.DataFrame(tbl["rows"], columns=tbl["columns"]), hide_index=True, use_container_width=True)
            if tid in ("TT29","TT30","TT31","TT32") and "results" in ex and tid in ex["results"]:
                res = ex["results"][tid]
                st.markdown(f"**파일럿 결과:** PASS {res['pass']}, abstain {res['abstain']}, error {res.get('error',0)}")
                st.caption(res.get("note",""))

# ── Task 목록 ──────────────────────────────────────────────────
def render_tasks(df, ex):
    st.markdown('<div class="sec-header">📋 TT01 ~ TT41 세부 진행 현황</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3,1])
    with c1:
        sf = st.multiselect("상태 필터", ["완료","진행중","검토중","미착수"],
                            default=["완료","진행중","검토중","미착수"], key="sf")
    with c2:
        show_detail = st.checkbox("상세 내용 표시", value=True, key="sd")

    fdf = df[df["status"].isin(sf)] if sf else df

    for phase in df["phase"].unique():
        pdf = fdf[fdf["phase"]==phase]
        if pdf.empty:
            continue
        apdf = df[df["phase"]==phase]
        done_c = (apdf["status"]=="완료").sum()
        total_c = len(apdf)
        pct_p = round(done_c/total_c*100)
        st.markdown(
            f'<div class="phase-header">{phase}'
            f' <span style="color:#94a3b8;font-size:0.8rem"> {done_c}/{total_c} 완료 ({pct_p}%)</span></div>',
            unsafe_allow_html=True
        )
        for _, row in pdf.iterrows():
            render_task_card(row, show_detail, ex)

    with st.expander("📊 전체 Task 표"):
        st.dataframe(df[["id","name","phase","owner","status","progress","due"]].rename(columns={
            "id":"ID","name":"태스크명","phase":"Phase","owner":"담당자",
            "status":"상태","progress":"진행률(%)","due":"기한"}),
            hide_index=True, use_container_width=True)

# ── 타임라인 ───────────────────────────────────────────────────
def render_timeline(df):
    st.markdown('<div class="sec-header">📅 연구 타임라인 — 2026-08-15 시작 기준</div>', unsafe_allow_html=True)

    start = date(2026, 8, 15)
    today = date(2026, 10, 14)
    end   = date(2026, 10, 31)
    total_days = (end - start).days
    elapsed = (today - start).days
    elapsed_pct = round(elapsed / total_days * 100, 1)
    days_left = (end - today).days

    done_cnt = (df["status"]=="완료").sum()
    task_pct = round(done_cnt / len(df) * 100, 1)
    avg_prog = round(df["progress"].mean(), 1)

    c1,c2,c3,c4 = st.columns(4)
    for col, val, label, color in [
        (c1, f"{elapsed}일", f"경과일 (/{total_days}일)", "#5dade2"),
        (c2, f"{elapsed_pct}%", "캘린더 진행률", "#27ae60"),
        (c3, f"{task_pct}%", f"Task 완료율 ({done_cnt}/41)", "#3498db"),
        (c4, f"{avg_prog}%", "전체 평균 진행률", "#9b59b6"),
    ]:
        col.markdown(
            f'<div class="big-metric"><div class="big-metric-val" style="color:{color}">{val}</div>'
            f'<div class="big-metric-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gantt — HTML로 직접 구현
    phases_gnt = [
        ("Phase 1 연구방향", date(2026,8,15), date(2026,8,20), "#27ae60"),
        ("Phase 2 법령수집",  date(2026,8,20), date(2026,8,24), "#27ae60"),
        ("Phase 3 전처리",   date(2026,8,24), date(2026,9,3),  "#27ae60"),
        ("Phase 4 DB구축",   date(2026,9,3),  date(2026,9,10), "#27ae60"),
        ("Phase 5 RAG구현",  date(2026,9,10), date(2026,9,22), "#27ae60"),
        ("Phase 6 평가셋",   date(2026,9,16), date(2026,10,13),"#27ae60"),
        ("Phase 7 실험",     date(2026,10,12),date(2026,10,25),"#f39c12"),
        ("Phase 8 논문",     date(2026,9,21), date(2026,10,31),"#9b59b6"),
    ]

    gantt_rows = ""
    for name, s, e, color in phases_gnt:
        left_pct  = (s - start).days / total_days * 100
        width_pct = (e - s).days / total_days * 100
        today_left = (today - start).days / total_days * 100
        gantt_rows += f"""
        <div style="display:flex;align-items:center;margin-bottom:6px;gap:8px">
          <div style="width:130px;font-size:0.75rem;color:#94a3b8;text-align:right;flex-shrink:0">{name}</div>
          <div style="flex:1;background:#1e2d45;border-radius:4px;height:20px;position:relative">
            <div style="position:absolute;left:{left_pct:.1f}%;width:{width_pct:.1f}%;background:{color};
                        border-radius:4px;height:20px;opacity:0.85"></div>
            <div style="position:absolute;left:{today_left:.1f}%;top:0;height:20px;
                        border-left:2px dashed #e74c3c"></div>
          </div>
          <div style="width:80px;font-size:0.72rem;color:#94a3b8;flex-shrink:0">{s.strftime('%-m/%-d')} ~ {e.strftime('%-m/%-d')}</div>
        </div>"""

    # 오늘 / 마감 마커
    today_pct = (today - start).days / total_days * 100
    end_pct   = 100.0

    st.markdown(f"""
<div style="background:#161b2e;border:1px solid #2a3a5c;border-radius:10px;padding:16px 20px;margin-bottom:16px">
  <div style="font-size:0.85rem;color:#90caf9;margin-bottom:12px;font-weight:600">📊 Gantt 차트 (2026-08-15 ~ 2026-10-31)</div>
  {gantt_rows}
  <div style="display:flex;gap:16px;margin-top:12px;font-size:0.75rem">
    <span style="color:#27ae60">■ 완료</span>
    <span style="color:#f39c12">■ 진행중</span>
    <span style="color:#9b59b6">■ 논문</span>
    <span style="color:#e74c3c">-- 오늘 (10/14)</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Phase 진행률 바
    st.markdown("**Phase별 완료율**")
    ps = df.groupby("phase").agg(total=("id","count"), done=("status", lambda x:(x=="완료").sum())).reset_index()
    for _, r in ps.iterrows():
        pct = round(r["done"]/r["total"]*100)
        clr = "#27ae60" if pct==100 else ("#2e86de" if pct>0 else "#5a5a5a")
        st.markdown(
            f'<div style="margin-bottom:10px">'
            f'<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:3px">'
            f'{r["phase"]} &nbsp; <span style="color:#5dade2">{pct}% ({int(r["done"])}/{int(r["total"])})</span></div>'
            f'<div class="prog-bar-bg"><div class="prog-bar-fill" style="width:{pct}%;background:{clr}"></div></div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # 마감 카운트다운
    st.markdown(f"""
<div style="text-align:center;margin-top:24px;padding:20px;background:#1a1200;
     border-radius:12px;border:1px solid #f39c12;">
  <div style="font-size:2.5rem;font-weight:800;color:#f39c12;">{days_left}일</div>
  <div style="color:#a0aec0;font-size:0.9rem;margin-top:4px">
    투고 마감까지 (2026-10-31, 한국항공운항학회)
  </div>
</div>
""", unsafe_allow_html=True)

# ── 메인 대시보드 ──────────────────────────────────────────────
@st.fragment(run_every="30s")
def dashboard():
    ex, df = load_data()

    render_header(ex)

    done_cnt = (df["status"]=="완료").sum()
    prog_cnt = (df["status"].isin(["진행중","검토중"])).sum()
    pend_cnt = (df["status"]=="미착수").sum()
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, val, label, color in [
        (c1, str(done_cnt),  "Task 완료",     "#27ae60"),
        (c2, str(prog_cnt),  "진행중",         "#2e86de"),
        (c3, str(pend_cnt),  "미착수",         "#718096"),
        (c4, f"{round(df['progress'].mean(),1)}%", "평균 진행률", "#5dade2"),
        (c5, "17일",         "투고까지",       "#f59e0b"),
    ]:
        col.markdown(
            f'<div class="big-metric">'
            f'<div class="big-metric-val" style="color:{color}">{val}</div>'
            f'<div class="big-metric-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    tab_overview, tab_rq, tab_tasks, tab_pilot, tab_timeline = st.tabs([
        "📊 개요 & 성능표",
        "🔬 연구 질문 (RQ)",
        "📋 Task (TT01~TT41)",
        "🧪 Pilot 상세 분석",
        "📅 타임라인 & 진행률",
    ])

    with tab_overview:
        st.markdown('<div class="sec-header">📝 연구 요약</div>', unsafe_allow_html=True)
        st.markdown(ex["manuscript"]["summary"])

        st.markdown('<div class="sec-header">🏆 Pilot 20문항 × 4시스템 성능 요약 (2026-10-14 실측)</div>', unsafe_allow_html=True)
        df_sum = pd.DataFrame({
            "시스템":       ["A (Current)","B (Naive)","C (Temporal)","D (SAT-Graph)"],
            "Hit@5(%)":    [70, 20, 70, 60],
            "Hit@10(%)":   [75, 30, 75, 75],
            "Recall@10(%)":[52.1, 12.5, 56.3, 47.9],
            "MRR@10":      [0.475, 0.147, 0.500, 0.407],
            "nDCG@10":     [0.408, 0.115, 0.438, 0.363],
            "버전유효성 Top-10":["158/200 (21%미래)","14/200 (83%만료)","199/200 ✅","199/200 ✅"],
        })
        st.dataframe(df_sum, hide_index=True, use_container_width=True)

        sys_labels = ["A (Current)","B (Naive)","C (Temporal)","D (SAT-Graph)"]
        sys_colors = ["#3498db","#e74c3c","#2ecc71","#f39c12"]
        systems = ["A","B","C","D"]

        for mk, title, fmt in [("mrr","MRR@10",".3f"),("hit","Hit@10(%)",".0f"),("recall","Recall@10(%)",".1f")]:
            vals = [TT36_METRICS[mk]["10"][s] for s in systems]
            st.markdown(bar_chart_html(sys_labels, vals, title=title, colors=sys_colors, fmt=fmt), unsafe_allow_html=True)

        # 논문 다운로드
        st.markdown('<div class="sec-header">📄 논문 원고</div>', unsafe_allow_html=True)
        ms = ex["manuscript"]
        cc1, cc2 = st.columns(2)
        with cc1:
            if os.path.exists(ms.get("pdf_path","")):
                with open(ms["pdf_path"],"rb") as f:
                    st.download_button(f"📥 PDF ({ms.get('pdf_label','')})", data=f,
                                       file_name=ms.get("pdf_download_name","manuscript.pdf"),
                                       mime="application/pdf", use_container_width=True)
            else:
                st.info("PDF: static/manuscript.pdf 없음")
        with cc2:
            if os.path.exists(ms.get("hwp_path","")):
                with open(ms["hwp_path"],"rb") as f:
                    st.download_button(f"📥 HWP ({ms.get('hwp_label','')})", data=f,
                                       file_name=ms.get("hwp_download_name","manuscript.hwp"),
                                       mime="application/octet-stream", use_container_width=True)
            else:
                st.info("HWP: static/manuscript.hwp 없음")

    with tab_rq:
        render_rq(ex)

    with tab_tasks:
        render_tasks(df, ex)

    with tab_pilot:
        render_pilot()

    with tab_timeline:
        render_timeline(df)

dashboard()
