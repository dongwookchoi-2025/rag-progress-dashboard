#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
progress.json 갱신 스크립트 (2026-09-20)
- TT32: 진행중(50%) → 완료(100%)로 전환, 그래프 결함 blocker 해제, 재실행 결과 반영
- TT41: 신규 Task 추가 (논문 선행연구 재검토·논리 보완·최종 투고, 담당 손상우)
- 최상위 as_of 갱신
- 최상위 action_plan 블록 추가 (대시보드 'TT29–32 Action Plan 적용 현황' 패널용)

사용법: progress.json 이 있는 폴더에서
    python patch_progress.py
원본은 progress.json.bak_YYYYMMDD_HHMMSS 로 백업됩니다.
"""
import json
import os
import shutil
from datetime import datetime

SRC = "progress.json"

# ── TT32 재실행 결과(2026-09-20) ─────────────────────────────
TT32_DETAIL = (
    "완료(2026-09-20). run_system_d()를 'System C temporal-vector seed → "
    "SAT-Graph 확장 → union → rerank → generation'으로 수정하고, graph_scope_empty일 때 "
    "C seed evidence를 보존(graph_scope_empty=True·graph_fallback_used=True)하도록 변경. "
    "self-check(self_check_tt32_empty_graph_scope_fallback) PASS. "
    "TT32만 Q001~Q020 재실행(run_id TT32-D-LIVE-PILOT-20260920T013505497569Z): "
    "PASS 19/20·abstain 3·ERROR 1, 기존 empty-answer(Q002/Q013)는 수정 부수효과로 PASS 전환. "
    "Research_Master 3개 시트(Development_Pilots 신규행, TEAM_TASKS_40 TT32 완료 처리, "
    "CHANGE_LOG CHG087) 반영. A/B/C 재실행 불요. "
    "단 프로젝트 전체 freeze는 Task1~5 미완으로 여전히 PROVISIONAL 보류(TT29~31 참조)."
)

# ── TT41 신규 Task (TT41_논문_선행연구_재검토_및_최종투고_실행계획.md 기준) ──
# 참고: 원본 문서에 pred/succ/collab이 명시되지 않아 아래는 합리적 추정값이며,
#       확정되면 이 부분을 수정하세요.
TT41 = {
    "id": "TT41",
    "phase": "Phase 8 · 논문 작성하고 정리",
    "name": "논문 선행연구 재검토·논리 보완·최종 투고",
    "owner": "손상우",
    "status": "미착수",
    "progress": 0,
    "due": "2026-10-12",
    "goal": (
        "항공운항학회 최종 투고 전 선행연구 인용 링크와 본문–참고문헌 대응을 재확인하고, "
        "서론·이론적 배경·연구설계가 하나의 논리로 이어지는지 점검한 뒤, "
        "편집규칙·행정서류를 확인해 최종본을 제출하고 편집위원회·심사 커뮤니케이션을 담당한다."
    ),
    "pred": "TT39, TT40",
    "succ": "연구 종료",
    "collab": "지도교수·연구진",
    "blocker": "",
    "outputs": (
        "Research_Master.xlsx TT41_PUBLICATION_CONTROL, CHANGE_LOG / "
        "Thesis_Manuscript.docx / 99_Logs_Backup TT41 투고 로그"
    ),
    "detail": (
        "신규 추가(2026-09-20). 최종 투고 목표일 2026-10-12. 실행 게이트 PUB-001~006 — "
        "PUB-001(10/3): 본문 미인용 참고문헌·참고문헌 누락 본문인용 각 0건 정리(또는 삭제/예외 사유), "
        "각 인용 DOI/공식URL·확인일 기록. "
        "PUB-002(10/4): 연구공백→선행연구 한계→연구질문/가설→RAG 설계·평가 연결을 "
        "서론·이론적 배경·연구설계에 명시. "
        "PUB-003(10/4): 최종초안 지도교수 발송, 버전·발송시각·쟁점·회신 기록. "
        "PUB-004(10/5): 연구진 미팅 발표, 결정·담당·기한 기록. "
        "PUB-005(10/11): 학회 편집규칙·행정서류 체크리스트 누락 0건. "
        "PUB-006(10/12): 최종본 투고, 접수번호/확인증·제출파일 SHA-256·연락 로그. "
        "범위 경계: 미확정 TT33 전문가검토/홀드아웃·TT32 재실행 결과를 확정 연구결과로 쓰지 않으며, "
        "변경 시 CHANGE_LOG에 근거·영향 기록."
    ),
}

# ── Action Plan 적용 현황(대시보드 패널용) ────────────────────
ACTION_PLAN = {
    "title": "TT29–32 Action Plan 적용 현황",
    "as_of": "2026-09-20",
    "freeze_status": "PROVISIONAL",
    "freeze_note": (
        "6개 Task 중 Task 6(System D 그래프 버그)만 완료. "
        "Task 1~4 미착수, Task 5 부분적, §5 research performance 지표"
        "(retrieval/temporal, generation/citation)도 미산출 → freeze 보류 유지. "
        "TT32(완료)와 TT29~31(검토중)의 진행률 격차가 이를 그대로 반영."
    ),
    "ref_docs": "TT29_TT32_Action_Plan_적용현황_20260920.md · _v2_RESOLVED_TT32.md",
    "checklist_done": 2,
    "checklist_total": 9,
    "tasks": [
        {"id": "Task 1",
         "name": "TT21 승인 Gold와 Master mirror 동기화 + 구버전 QUESTIONS/Gold SUPERSEDED 마킹",
         "status": "미착수"},
        {"id": "Task 2",
         "name": "RAG_Config_Master.yaml에 evaluation.pilot_source_file 등 승인 소스 지정",
         "status": "미착수"},
        {"id": "Task 3",
         "name": "Run 전 입력검증 게이트(존재/APPROVED/6필드 일치/해시 기록)",
         "status": "미착수"},
        {"id": "Task 4",
         "name": "Manifest에 소스 해시·스냅샷 버전·모델ID·prompt/code-config 해시 등 provenance 기록",
         "status": "미착수"},
        {"id": "Task 5",
         "name": "empty-answer 5건 근본원인 진단",
         "status": "부분적",
         "note": "D의 Q002/Q013은 Task 6 수정 부수효과로 PASS 전환, A/C의 Q018·Q019는 미진단"},
        {"id": "Task 6",
         "name": "System D graph-empty 시 C seed 보존 + TT32 재실행",
         "status": "완료",
         "note": "self-check PASS, TT32 재실행 PASS 19/20·abstain 3·ERROR 1"},
    ],
}


def main():
    if not os.path.exists(SRC):
        raise SystemExit(f"[중단] {SRC} 를 찾을 수 없습니다. progress.json 이 있는 폴더에서 실행하세요.")

    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    # 백업
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{SRC}.bak_{stamp}"
    shutil.copy2(SRC, backup)

    # as_of 갱신
    data["as_of"] = "2026-09-20 05:30"

    tasks = data.setdefault("tasks", [])

    # TT32 갱신
    found = False
    for t in tasks:
        if t.get("id") == "TT32":
            t["status"] = "완료"
            t["progress"] = 100
            t["blocker"] = ""
            t["detail"] = TT32_DETAIL
            found = True
            break
    if not found:
        raise SystemExit("[중단] TT32 항목을 찾지 못했습니다. 파일 구조를 확인하세요.")

    # TT41 추가 (이미 있으면 교체 — 중복 방지)
    tasks[:] = [t for t in tasks if t.get("id") != "TT41"]
    tasks.append(TT41)

    # action_plan 블록 추가/교체
    data["action_plan"] = ACTION_PLAN

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    done = sum(1 for t in tasks if t.get("status") == "완료")
    print(f"[완료] {SRC} 갱신 완료 (백업: {backup})")
    print(f"       TT32 → 완료(100%), TT41 신규 추가(미착수), 전체 Task {len(tasks)}개 · 완료 {done}개")
    print(f"       action_plan 블록 추가 (freeze_status=PROVISIONAL)")


if __name__ == "__main__":
    main()
