# -*- coding: utf-8 -*-
"""8대 2차 가공·롱폼 허브 소재 수집 및 원클릭 레시피 생성기 (토큰 0소모 · 지연 로딩용)

    python transform_hub_watch.py          수집·생성 → web/transform_hub.js, transform_hub_store.json
    python transform_hub_watch.py --dry    저장 없이 요약만 출력

유벤져스 1~5강 전수 노하우(1강 55세+ 시니어 90% 타깃, 2강 저작권·재사용 방어, 3강 테디쌤 썸네일 3단 문구 &
빈이파파 Google Flow 6초 AI 후킹 인트로, 4강 시크릿 모드 제목 2개 조합 & 30초 잔존율 70%, 5강 대본 역설계)와
UV 글로벌 반응 편집기 핵심 모듈(voiceonly, songguard, 48종 GSAP, capcut) 및 3-AI 합동 위원회 추천 주제를
8대 카테고리로 통합하여 제공한다.

사이트 초기 로딩 무게를 0바이트로 유지하기 위해, 사용자가 상단 탭 '🏛️ 2차 가공·롱폼 허브 (8대 주제)'를
클릭할 때만 web/transform_hub.js 가 온디맨드로 지연 로딩(Lazy Load)된다.
"""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "web", "transform_hub.js")
STORE = os.path.join(BASE, "transform_hub_store.json")
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

BADGE_RE = re.compile(
    r"(?:월\s*)?\d[\d,]*(?:\.\d+)?\s*(?:조\s*원|억\s*원|만\s*원|천\s*원|원|달러|엔|위안|%|퍼센트|배|만\s*명|세|년|개월|시간|위|건|km|톤)"
)

CATEGORIES = [
    {
        "id": "cat1_politics",
        "label": "① 🏛️ 유형C: 정치·시사 브리핑",
        "short_label": "🏛️ 정치·시사(유형C)",
        "safety": 99,
        "transform_score": 95,
        "rpm": "상 (5060 타깃 40~55분)",
        "license_default": "공공누리 1유형 (KTV·국회방송·정책브리핑)",
        "engine_stack": "5강 정치프롬프트 + 4대 페르소나 + UV 48종 GSAP + voiceonly/songguard",
        "desc": "청문회·국무회의·KTV 브리핑 다중 교차 재구성 + 4대 페르소나(사실 확인·제도 해설·생활 영향·반론 검토) 차분한 분석",
    },
    {
        "id": "cat2_economy",
        "label": "② 💰 생활경제·연금·부동산",
        "short_label": "💰 경제·연금·부동산",
        "safety": 99,
        "transform_score": 96,
        "rpm": "최상 (전체 1위 고단가)",
        "license_default": "공공누리 1유형 (한국은행·통계청·국토부·예산정책처)",
        "engine_stack": "huashu-art-motion(경제그래프) + UV chart-* GSAP + Codex 수치검증",
        "desc": "55세+ 시니어 90% 타깃 최고 관심사(국민연금·기초연금·건보료·세금·부동산·금리)를 내 지갑 계산 사례와 데이터 차트로 해설",
    },
    {
        "id": "cat3_history",
        "label": "③ 📜 한국 근현대사·경제성장사·지정학",
        "short_label": "📜 근현대사·지정학",
        "safety": 100,
        "transform_score": 98,
        "rpm": "상 (시니어 20~40분 롱폼)",
        "license_default": "Public Domain / 공공누리 (국가기록원·NARA·LOC)",
        "engine_stack": "vox-history-docu-studio(2.5D 패럴랙스·고증지도) + claude-drawing-skill(Draw-on)",
        "desc": "1강 시니어 시청 이유 1위('내가 살아온 산업화 세대 인생의 결산과 자부심')를 흑백 공공 사료와 고증 지도·연표로 재구성",
    },
    {
        "id": "cat4_infra",
        "label": "④ 🚄 메가 인프라·기술·방산 작동원리",
        "short_label": "🚄 인프라·기술·방산",
        "safety": 98,
        "transform_score": 96,
        "rpm": "상 (남성 89% 타깃 직격)",
        "license_default": "공공누리 / 공개 특허·국토부·철도공단·방사청",
        "engine_stack": "manimce-best-practices(기하·메커니즘) + huashu-art-motion + 3개국 비교",
        "desc": "1강 12갈래 중 남성 시니어(89%)가 열광하는 K-고속철도·초장대교량·조선·반도체·방산이 어떻게 작동하고 왜 세계 표준이 됐는지 해설",
    },
    {
        "id": "cat5_docu",
        "label": "⑤ 😭 한·일·대만 기적의 실화·인물 다큐",
        "short_label": "😭 한·일·대만 실화다큐",
        "safety": 100,
        "transform_score": 98,
        "rpm": "상 (글로벌 3개국 동시 확장)",
        "license_default": "CC0 / Public Domain / 한·일·대만 지자체 공개 기록",
        "engine_stack": "tw/jp-docu-factory + claude-drawing-skill + Rule 6(Google Flow 0원→Kling/LTX-2.3)",
        "desc": "가오슝 10위안 도시락 할머니(莊朱玉女)·일본 가미카쓰초 나뭇잎 기적(彩)·한국 산업화 영웅 등 눈물과 감동의 100% 저작권 클린 실화 다큐",
    },
    {
        "id": "cat6_classics",
        "label": "⑥ 📖 성경·고전·역사 명연설 역설계 강론",
        "short_label": "📖 성경·고전·명연설",
        "safety": 100,
        "transform_score": 95,
        "rpm": "중상 (1~2시간 초장편 시청시간 폭발)",
        "license_default": "100% Public Domain (저작권 만료 경전·고전·역사 원전)",
        "engine_stack": "5강 대본 역설계 프롬프트 + anidoodle(손그림 타임랩스) + huashu(수묵화)",
        "desc": "타인 설교 무단 재편집(@나오TV 삭제 사태) 리스크 없이, 퍼블릭 도메인 경전·고전 원전을 인기 강론 화법으로 역설계해 들려주는 시니어 힐링 장편",
    },
    {
        "id": "cat7_global",
        "label": "⑦ 🌍 글로벌 외신·해외 전문가 교차 브리핑",
        "short_label": "🌍 글로벌 외신·전문가",
        "safety": 95,
        "transform_score": 92,
        "rpm": "상 (4060 남성·해외시각 비교)",
        "license_default": "Public Domain (백악관·UN·CRS) + 공정 인용 다중 교차",
        "engine_stack": "UV compile.py(다중 합본) + translate.py + vox 형광펜 원문 인용카드",
        "desc": "단일 영상 번역이 아니라 백악관·UN·해외 석학 키노트·외신 리포트 3~4개를 교차 합본하여 입체적으로 비교·해설하는 글로벌 브리핑",
    },
    {
        "id": "cat8_court",
        "label": "⑧ ⚖️ 실제 법정 재판·바디캠 사건 재구성",
        "short_label": "⚖️ 법정·바디캠 사건",
        "safety": 95,
        "transform_score": 90,
        "rpm": "중상 (초반 30초 잔존율·조회수 폭발력 최강)",
        "license_default": "미국 법원 공개 재판 기록 / 주정부 FOIA 바디캠 (Public Domain)",
        "engine_stack": "UV select/translate + timeline-* GSAP 그래픽 + voiceonly 현장음 클린화",
        "desc": "미국 주정부 정보공개법(FOIA) 바디캠 및 공개 법정 기록을 사건 타임라인 그래픽과 한국어 정밀 해설로 재구성하는 고몰입 사건 파일",
    },
]


def extract_badges(text):
    found = []
    for m in BADGE_RE.finditer(text or ""):
        val = re.sub(r"\s+", " ", m.group(0)).strip()
        if val not in found:
            found.append(val)
        if len(found) >= 4:
            break
    return found


def get_curated_seed_items(today_str):
    """8대 카테고리별로 즉시 원클릭 테스트가 가능한 대표 S/A급 기획·원본 매칭 시드 목록"""
    return [
        # ① 유형 C: 정치·시사 브리핑
        {
            "id": "th_pol_01",
            "category": "cat1_politics",
            "grade": "S",
            "score": 97,
            "title": "[시크릿 조합] \"도대체 회의록에 뭐가 적혀 있길래?\" 국무회의·국회 브리핑 원문 대조로 본 핵심 쟁점 3가지와 내 세금 변화",
            "orig_title": "대한민국 정책브리핑 · 국회 영상회의록 주요 민생·예산 쟁점 브리핑 다중 교차",
            "url": "https://www.korea.kr/news/policyBriefingList.do",
            "source": "정책브리핑(korea.kr) · 국회 영상회의록",
            "published": today_str,
            "license": "공공누리 제1유형 (상업적 이용·변경 가능)",
            "safety": 99,
            "transform_score": 96,
            "rpm": "상 (5060 시니어 40분+)",
            "target_len": "롱폼 35~50분 + 쇼츠 3편",
            "badges": ["공공누리 1유형", "4대 페르소나", "원문 100% 대조"],
            "thumb_3tier": {
                "top": "회의록 원문 열어보니.. 대체 무슨 일이?!",
                "mid": "국무회의·상임위 브리핑 3개 교차 검증",
                "bot": "단 3분 만에 드러난 내 세금·연금 직격탄",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Google Flow AI 훅] 서류철을 보며 의아해하는 원로 해설자 캐릭터: \"아니, 방송에서는 왜 이 3번째 조항 숫자를 아무도 말 안 해주는 겁니까?\"",
                "s6_18": "[6~18초 충격 수치 & 원문 인서트] 실제 브리핑 핵심 5초 육성(`voiceonly` 클린화) + GSAP 빨간 형광펜 수치 카드 등장",
                "s18_30": "[18~30초 Draw-on 클리프행어] `claude-drawing-skill`로 찬반 핵심 구조도를 한 획씩 그리며 \"오늘 4명의 해설자가 원문 그대로 끝까지 파헤쳐 드립니다\"",
            },
            "engine_recipe": "UV refcheck(화이트리스트) ➔ voiceonly(0.72) ➔ 4대 페르소나 대본(해설 65%+) ➔ UV 48종 GSAP(chart/quote) ➔ CapCut 초안 + MP4",
        },
        {
            "id": "th_pol_02",
            "category": "cat1_politics",
            "grade": "S",
            "score": 94,
            "title": "[시크릿 조합] \"장관님, 그 숫자는 통계청 자료랑 다르지 않습니까!\" 국정감사·청문회 질의응답 교차 팩트체크 총정리",
            "orig_title": "국회 상임위 주요 질의응답 및 정부 부처 공식 해명자료 교차 재구성",
            "url": "https://www.assembly.go.kr/",
            "source": "국회 인터넷의사중계 · 정책브리핑 반박자료",
            "published": today_str,
            "license": "공공저작물 / 시사 보도·비평 공정인용",
            "safety": 98,
            "transform_score": 95,
            "rpm": "상 (시청지속시간 최상)",
            "target_len": "롱폼 40분 + 쇼츠 3편",
            "badges": ["양측 원문 대조", "통계청 수치 검증", "시니어 맞춤 0.93x"],
            "thumb_3tier": {
                "top": "\"그 숫자는 틀렸습니다!\" 정적 흐른 회의장",
                "mid": "청문회 질의 vs 부처 공식 통계 1:1 대조",
                "bot": "서류 한 장 공개되자 3초 만에 뒤집힌 분위기",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Cold Open] 질의 중 가장 날카로운 숫자 반박 5초 현장 육성 + Google Flow 분석가 반응 컷",
                "s6_18": "[6~18초 Stakes] '질의 측 주장 수치 vs 통계청 실제 수치' 양면 비교 GSAP 모션카드",
                "s18_30": "[18~30초 Bridge] \"누구 말이 맞는지 오늘 공식 보고서 원문 3개를 나란히 띄워놓고 확인해 보시죠\"",
            },
            "engine_recipe": "Claim-Source Verifier(Codex 수치 검수) + 4대 페르소나 중립 해설 + UV timeline/comparison 그래픽",
        },
        # ② 생활경제·연금·부동산
        {
            "id": "th_eco_01",
            "category": "cat2_economy",
            "grade": "S",
            "score": 98,
            "title": "[시크릿 조합] \"모르면 매달 34만 원씩 그냥 날립니다\" 올해 바뀌는 국민연금·기초연금·건보료 개편안 내 수령액 실전 계산표",
            "orig_title": "보건복지부·국민연금공단·정책브리핑 연금 및 건강보험료 부과체계 안내 브리핑",
            "url": "https://www.korea.kr/news/policyNewsList.do",
            "source": "보건복지부 · 대한민국 정책브리핑(공공누리 1유형)",
            "published": today_str,
            "license": "공공누리 제1유형 (상업적 이용·변경 가능)",
            "safety": 100,
            "transform_score": 97,
            "rpm": "최상 (금융·연금 고단가 광고)",
            "target_len": "롱폼 18~25분 + 쇼츠 3편",
            "badges": ["55세+ 시니어 1위", "월 수령액 시뮬레이션", "고CPM 금융"],
            "thumb_3tier": {
                "top": "신청 안 하면 매달 이 돈을 못 받는다고요?!",
                "mid": "60세·65세 이상 연금·건보료 개편 핵심 요약",
                "bot": "내 통장에 실제로 찍히는 금액 3초 계산표",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Google Flow AI 훅] 연금 고지서를 들고 안경을 고쳐 쓰는 시니어 캐릭터: \"아니, 옆집 김 선생은 똑같이 냈는데 왜 나보다 30만 원을 더 받습니까?\"",
                "s6_18": "[6~18초 핵심 숫자 충격] `huashu-art-motion` 막대그래프로 조건별 수령액 격차 실시간 렌더링",
                "s18_30": "[18~30초 Draw-on 클리프행어] \"특히 피부양자 박탈 기준과 감액 구간, 딱 3가지만 체크하시면 매달 새는 돈을 막을 수 있습니다\"",
            },
            "engine_recipe": "정책브리핑 원문 + Codex 가구별 모의계산표 + huashu-art-motion 경제차트 + 시니어 64px 고대비 자막",
        },
        {
            "id": "th_eco_02",
            "category": "cat2_economy",
            "grade": "A",
            "score": 93,
            "title": "[시크릿 조합] \"한국은행 보고서에 찍힌 충격 숫자\" 금리·가계부채·서울 및 지방 아파트 실거래 데이터 10년 추이 완전 분석",
            "orig_title": "한국은행 통화신용정책 보고서 · 국토교통부 실거래가 공개시스템 브리핑",
            "url": "https://www.bok.or.kr/",
            "source": "한국은행 · 국토교통부 · 통계청 KOSIS",
            "published": today_str,
            "license": "공공데이터 / 공공누리 제1유형",
            "safety": 99,
            "transform_score": 96,
            "rpm": "최상 (부동산·자산관리 RPM 최상위)",
            "target_len": "롱폼 15~22분 + 쇼츠 3편",
            "badges": ["한은 공식 데이터", "실거래가 차트", "RPM 최상위"],
            "thumb_3tier": {
                "top": "한국은행 보고서 42페이지에 숨겨진 숫자!",
                "mid": "서울·수도권·지방 아파트 10년 데이터 비교",
                "bot": "지금 집 가진 분들이 반드시 봐야 할 3가지 신호",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Cold Open] 한국은행 총재 브리핑 핵심 4초 발언 + 빨간색 추세선 급변 애니메이션",
                "s6_18": "[6~18초 Stakes] 뉴스 기사가 말해주지 않는 가계부채 연령대별 비중(60대 이상 비중) 차트 공개",
                "s18_30": "[18~30초 Bridge] \"감이나 소문이 아니라 한국은행과 국토부 공식 숫자만으로 향후 2년 시나리오를 짚어드립니다\"",
            },
            "engine_recipe": "d3-viz / manim 데이터 애니메이션 + UV chart-line/chart-bar GSAP 오버레이 + 4대 페르소나 해설",
        },
        # ③ 한국 근현대사·경제성장사·지정학
        {
            "id": "th_his_01",
            "category": "cat3_history",
            "grade": "S",
            "score": 96,
            "title": "[시크릿 조합] \"불가능하다며 세계은행도 대출을 거절했습니다\" 허허벌판 모래사장에 세계 1위 포항제철·경부고속도로를 세운 기밀문서 공개",
            "orig_title": "국가기록원 경제개발 5개년 계획 및 포항종합제철·경부고속도로 건설 기록물 아카이브",
            "url": "https://www.archives.go.kr/",
            "source": "국가기록원 · 미 국립문서보관소(NARA) 공개 문서",
            "published": today_str,
            "license": "공공누리 / Public Domain (저작권 클린 100%)",
            "safety": 100,
            "transform_score": 98,
            "rpm": "상 (55세+ 시니어 완주율 1위)",
            "target_len": "롱폼 25~40분 + 쇼츠 3편",
            "badges": ["시니어 자부심 1위", "국가기록원 사료", "한·영·일 글로벌 확장"],
            "thumb_3tier": {
                "top": "\"한국에 돈 빌려주면 100% 떼인다!\" 비웃던 세계은행",
                "mid": "1968년 미국 기밀문서에 적혀 있던 충격 보고서",
                "bot": "단 5년 만에 전 세계 경제학자들을 침묵시킨 기적",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Google Flow AI 훅] 1960년대 영문 타자기 보고서를 내려놓으며 고개를 젓는 서양 심사관 + \"철강 공장은커녕 쌀부터 사 먹으라던 조롱\"",
                "s6_18": "[6~18초 1차 사료 카드] `vox-history-docu-studio` 형광펜 인용 카드로 실제 IBRD(세계은행) 부정 평가 원문 문장 하이라이트",
                "s18_30": "[18~30초 Draw-on 지도 브릿지] 영일만 모래바람 위로 제철소 도면이 한 획씩 그려지며(`claude-drawing-skill`) 본편 시작",
            },
            "engine_recipe": "vox-history-docu-studio(2.5D 패럴랙스 + 고증지도 + 형광펜 사료카드) + claude-drawing-skill + Suno V5 오케스트라",
        },
        # ④ 메가 인프라·기술·방산 작동원리
        {
            "id": "th_inf_01",
            "category": "cat4_infra",
            "grade": "S",
            "score": 95,
            "title": "[시크릿 조합] \"바다 밑 60미터 암반을 어떻게 1mm 오차로 뚫었을까?\" 해외 엔지니어들이 K-해저터널·초장대교량 공법을 보고 놀란 이유",
            "orig_title": "국토교통부 보령해저터널·이순신대교·GTX 대심도 터널 NATM 및 TBM 공법 기술 브리핑",
            "url": "https://www.molit.go.kr/",
            "source": "국토교통부 · 한국도로공사 · 한국철도시설공단 공개 기술자료",
            "published": today_str,
            "license": "공공누리 제1유형 (기술 백서 및 브리핑)",
            "safety": 99,
            "transform_score": 97,
            "rpm": "상 (남성 89% 시청층 초고몰입)",
            "target_len": "롱폼 15~25분 + 쇼츠 3편",
            "badges": ["작동원리 3D/Manim", "한·일·대만 비교", "남성 시니어 89% 타깃"],
            "thumb_3tier": {
                "top": "수압 6기압 바닷속을 어떻게 안 무너지고 뚫었지?!",
                "mid": "해외 토목학회가 주목한 한국 해저터널·대교 기술",
                "bot": "단면도를 쪼개서 본 소름 돋는 0.1mm 정밀 공법",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Google Flow AI 훅] 거대한 해저 TBM 굴착기 단면과 놀란 엔지니어: \"위에는 수십만 톤 바닷물이 누르는데 어떻게 물 한 방울 안 새고 뚫어냅니까?\"",
                "s6_18": "[6~18초 메커니즘 시각화] `manimce-best-practices`로 해저 수압 분산 아치와 고강도 숏크리트 공법을 도형 애니메이션으로 즉시 시각화",
                "s18_30": "[18~30초 3개국 비교 브릿지] 한국·일본·유럽 해저터널 시공 단가와 공기 단축 기록을 GSAP 비교표로 제시",
            },
            "engine_recipe": "manimce-best-practices(구조 역학 시각화) + huashu-art-motion(청사진 화풍) + 국토부 공공누리 브리핑",
        },
        # ⑤ 한·일·대만 기적의 실화·인물 다큐
        {
            "id": "th_doc_01",
            "category": "cat5_docu",
            "grade": "S",
            "score": 98,
            "title": "[시크릿 조합] \"할머니, 집 7채를 다 팔아서 왜 남의 밥을 차려주십니까?\" 가오슝 부두 노동자들을 50년간 먹여 살린 '10위안 도시락 할머니' 좡주위뉘(莊朱玉女)의 눈물",
            "orig_title": "대만 가오슝 '10위안 도시락 할머니' 좡주위뉘(莊朱玉女, 1920~2015) 50년 선행 실화 다큐멘터리",
            "url": "https://commons.wikimedia.org/",
            "source": "대만 공공 문화 기록 · Wikimedia Commons (CC0 / CC-BY)",
            "published": today_str,
            "license": "CC0 / Public Domain / 자체 생성 시네마틱 아트워크 (저작권 100% 클린)",
            "safety": 100,
            "transform_score": 99,
            "rpm": "상 (한국·대만·일본 3개국 동시 발행)",
            "target_len": "롱폼 15~20분 + 파생 쇼츠 3편",
            "badges": ["3-AI 만장일치 1호", "바코드랩 4단계 서사", "Rule 6 황금비율"],
            "thumb_3tier": {
                "top": "집 7채를 팔아 50년간 350원짜리 밥을 파신 할머니?!",
                "mid": "가오슝 부두 노동자들의 어머니 좡주위뉘(莊朱玉女)",
                "bot": "장례식 날 수천 명이 거리로 쏟아져 나와 오열한 이유",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Tier 3 하이라이트 훅] 새벽 4시 빗속에서 무거운 채소 바구니를 끌며 미소 짓는 할머니 시네마틱 모션(Google Flow 0원 ➔ Kling 백업)",
                "s6_18": "[6~18초 숫자 대비] '물가 50배 폭등 vs 50년 동안 단돈 10위안(350원) 도시락, 대신 팔아치운 집 7채' 다크룸 에디토리얼 모션카드",
                "s18_30": "[18~30초 수묵 Draw-on 브릿지] `huashu-art-motion` 수묵화로 가오슝 항구가 피어나며 바코드랩 1막 진입",
            },
            "engine_recipe": "tw-docu-factory + Rule 6 하이브리드 3단 황금비율(Tier1 코드모션 90% + Tier2 Flow/LTX + Tier3 Kling) + 3개국 다국어 로컬라이징",
        },
        {
            "id": "th_doc_02",
            "category": "cat5_docu",
            "grade": "S",
            "score": 97,
            "title": "[시크릿 조합] \"뒷산에 떨어진 나뭇잎을 주워서 연매출 26억을 벌었다고요?!\" 감귤 농사가 전멸한 산골 마을 80세 할머니들의 태블릿 PC 반란, 일본 가미카쓰초 '이로도리(彩)' 실화",
            "orig_title": "일본 도쿠시마현 가미카쓰초 '이로도리(彩)' 잎사귀 비즈니스 기적 실화 다큐멘터리",
            "url": "https://commons.wikimedia.org/",
            "source": "일본 가미카쓰초 공개 지역활성화 백서 · Wikimedia Commons",
            "published": today_str,
            "license": "CC0 / CC-BY / 공공 지역활성화 백서 데이터",
            "safety": 100,
            "transform_score": 99,
            "rpm": "상 (일본 초고단가 + 한국 시니어 영감)",
            "target_len": "롱폼 15~20분 + 파생 쇼츠 3편",
            "badges": ["일본 감동다큐 1호", "연매출 2.6억 엔", "80세 시니어 기적"],
            "thumb_3tier": {
                "top": "\"산에 널린 나뭇잎이 한 장에 천 원이라고요?!\"",
                "mid": "감귤 얼어 죽은 절망의 산골 마을 80세 할머니들",
                "bot": "태블릿 하나로 연매출 2.6억 엔 신화를 쓴 기적 실화",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Tier 3 하이라이트 훅] 단풍잎을 정성껏 선별하다가 태블릿 PC 주문 알림에 환하게 웃는 80대 할머니 모션 컷",
                "s6_18": "[6~18초 반전 수치] '평균 연령 70~80세 · 인구 1,500명 소멸위기 마을 ➔ 일본 고급 요정 점유율 80% · 연매출 2.6억 엔' GSAP 카드",
                "s18_30": "[18~30초 Draw-on 지도 브릿지] 도쿠시마현 산골 지도가 그려지며 1981년 영하 12도 한파의 날로 타임슬립",
            },
            "engine_recipe": "jp-docu-factory + claude-drawing-skill(Draw-on) + anidoodle(수채화 회상씬) + Rule 6 황금비율",
        },
        # ⑥ 성경·고전·역사 명연설 역설계 강론
        {
            "id": "th_cls_01",
            "category": "cat6_classics",
            "grade": "S",
            "score": 95,
            "title": "[시크릿 조합] \"자식에게 재산을 다 주면 왜 눈물로 늙어가는가\" 다산 정약용의 『목민심서·하피첩』과 솔로몬의 잠언이 60대 이후 인생에 남긴 소름 돋는 경고",
            "orig_title": "퍼블릭 도메인 고전(다산 정약용 하피첩·논어·솔로몬 잠언) 원전 + 5강 인기 강론 화법 3단계 역설계",
            "url": "https://db.itkc.or.kr/",
            "source": "한국고전번역원(공공누리) · 개역한글/KJV 성경(Public Domain)",
            "published": today_str,
            "license": "100% Public Domain (저작권 영구 만료 원전 + 자체 대본·음성)",
            "safety": 100,
            "transform_score": 97,
            "rpm": "중상 (1~2시간 연속 재생 · 시청시간 8,000시간 치트키)",
            "target_len": "장편 45~90분 + 중편 15분 + 쇼츠 3편",
            "badges": ["저작권 폭파 위험 0%", "5강 화법 역설계", "수면·힐링 초장편"],
            "thumb_3tier": {
                "top": "\"늙어서 이 3가지를 내어주면 자식도 떠납니다\"",
                "mid": "유배지에서 다산 정약용이 피눈물로 남긴 편지",
                "bot": "60대 이후 인생 후반전을 지키는 500년 고전의 지혜",
            },
            "hook_30s": {
                "s0_6": "[0~6초 수묵/손그림 훅] `huashu-art-motion` 강진 유배지 고택에 빗소리가 흐르며 치마폭(하피첩)에 붓글씨가 써지는 장면",
                "s6_18": "[6~18초 공감 질문] 5강 강론 화법 역설계: 일상 속 가장 아픈 가족·노후 고민 한 문장으로 시청자 마음을 어루만지며 시작",
                "s18_30": "[18~30초 원전 인용 브릿지] `anidoodle` 따뜻한 연필 수채화 타임랩스와 함께 4장 구조의 인생 이야기 진입",
            },
            "engine_recipe": "5강 3단계 역설계 프롬프트(문장 표절 0%, 호흡·클리프행어 구조만 적용) + anidoodle + huashu-art-motion + ElevenLabs 차분한 강론 보이스",
        },
        # ⑦ 글로벌 외신·해외 전문가 교차 브리핑
        {
            "id": "th_glb_01",
            "category": "cat7_global",
            "grade": "A",
            "score": 93,
            "title": "[시크릿 조합] \"미국 의회 보고서에 한국 이름이 47번 등장한 진짜 이유\" 백악관 브리핑·미 의회조사국(CRS)·유럽 싱크탱크 3자 교차 분석",
            "orig_title": "미국 의회조사국(CRS) 공개 보고서 · 백악관 브리핑(Public Domain) · 해외 석학 대담 교차 재구성",
            "url": "https://crsreports.congress.gov/",
            "source": "미 연방정부 공개 기록(Public Domain) · 글로벌 싱크탱크 공개 세미나",
            "published": today_str,
            "license": "US Government Work (Public Domain) + 다중 교차 비평 공정인용",
            "safety": 96,
            "transform_score": 94,
            "rpm": "상 (4060 남성 지식층 장시간 시청)",
            "target_len": "롱폼 18~30분 + 쇼츠 3편",
            "badges": ["미 의회 공식문서", "3개국 시각 교차", "UV compile 합본"],
            "thumb_3tier": {
                "top": "미 의회 비공개 같던 보고서에 'KOREA'가 47번?!",
                "mid": "미국·유럽·일본 전문가들이 동시에 지목한 변수",
                "bot": "외신 원문 3개를 나란히 대조해보니 드러난 진짜 속내",
            },
            "hook_30s": {
                "s0_6": "[0~6초 Cold Open] 백악관/싱크탱크 브리핑에서 'South Korea'를 언급하는 결정적 5초 영문 육성 + 한국어 반전 자막",
                "s6_18": "[6~18초 원문 형광펜 카드] `vox-history-docu-studio` 스타일로 CRS 영문 보고서 원문 핵심 문장에 노란 형광펜이 그어지며 한글 번역 병기",
                "s18_30": "[18~30초 다중 시각 브릿지] \"미국, 유럽, 일본의 시각이 어떻게 다른지 3개의 원문을 교차해서 짚어드립니다\"",
            },
            "engine_recipe": "UV compile.py(다중 소스 교차) + translate.py + vox 형광펜 원문 카드 + 4대 페르소나 지정학 해설",
        },
        # ⑧ 실제 법정 재판·바디캠 사건 재구성
        {
            "id": "th_crt_01",
            "category": "cat8_court",
            "grade": "A",
            "score": 92,
            "title": "[시크릿 조합] \"경관님, 제 트렁크는 절대 열면 안 됩니다..\" 평범한 과속 단속이 미국 주법원 역대급 재판으로 번진 바디캠·법정 기록 전말",
            "orig_title": "미국 주정부 정보공개법(FOIA) 경찰 바디캠 및 주법원 공개 재판 기록 타임라인 재구성",
            "url": "https://www.uscourts.gov/",
            "source": "미국 FOIA 공개 바디캠 · 주법원 공개 공판 기록 (Public Domain)",
            "published": today_str,
            "license": "US FOIA Public Record (공공 기록물) + 독창적 사건 타임라인 분석",
            "safety": 95,
            "transform_score": 91,
            "rpm": "중상 (초반 30초 잔존율 80%+ 조회수 폭발형)",
            "target_len": "롱폼 15~25분 + 쇼츠 3편",
            "badges": ["FOIA 공공기록", "타임라인 재구성", "30초 잔존율 최강"],
            "thumb_3tier": {
                "top": "\"잠깐만요! 그 가방은 열면 안 됩니다!\" 떨리는 손",
                "mid": "단순 신호위반 단속 중 바디캠에 그대로 찍힌 장면",
                "bot": "판사마저 판결문을 읽다 멈춰버린 사건의 반전 전말",
            },
            "hook_30s": {
                "s0_6": "[0~6초 현장 육성 Cold Open] 바디캠 특유의 타임코드 UI + 가장 긴장감 넘치는 5초 문답(`voiceonly`로 사이렌/잡음 정돈) + 한글 자막",
                "s6_18": "[6~18초 사건 타임라인 카드] UV `timeline-*` GSAP 그래픽으로 '단속 시각 ➔ 결정적 단서 발견 ➔ 법정 선고' 3단계 구조를 5초 만에 제시",
                "s18_30": "[18~30초 법률·심리 브릿지] \"왜 용의자는 그 순간 스스로 증거를 내놓았을까요? 공개된 공판 기록으로 사건을 처음부터 재구성합니다\"",
            },
            "engine_recipe": "UV select/translate + voiceonly/songguard + UV timeline-* GSAP 오버레이 + CapCut 초안 생성",
        },
    ]


def fetch_live_kogl_for_hub(today_str):
    """kr_news_store.json에 수집된 검증된 공공누리 1유형/경제 브리핑 기사를 읽어 8대 카테고리용 2차 가공 기획 카드로 자동 변환"""
    items = []
    kr_store = os.path.join(BASE, "kr_news_store.json")
    if not os.path.exists(kr_store):
        return items
    try:
        data = json.load(open(kr_store, encoding="utf-8"))
        news_list = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for n in news_list:
            raw_title = (n.get("title") or "").strip()
            link = (n.get("url") or "").strip()
            desc = (n.get("summary") or "").strip()
            if not raw_title or not link:
                continue
            # 공공누리 1유형 또는 경제 핵심 기사만 선별
            if n.get("category") not in ("kogl1", "economy"):
                continue
            badges = n.get("badges") or extract_badges(f"{raw_title} {desc}") or ["공공누리 1유형", "원문 브리핑"]
            target_cat = "cat1_politics"
            if any(k in raw_title for k in ("연금", "세금", "부동산", "금리", "지원금", "건보", "물가", "소상공인", "취업", "금융", "환율", "배당", "주가", "은행", "대출")):
                target_cat = "cat2_economy"
            elif any(k in raw_title for k in ("철도", "고속도로", "터널", "우주", "방산", "반도체", "원전", "교량", "해양", "AI", "수출", "선박")):
                target_cat = "cat4_infra"
            elif any(k in raw_title for k in ("미국", "일본", "중국", "정상", "외교", "관세", "유엔", "글로벌")):
                target_cat = "cat7_global"

            clean_t = re.sub(r"\[.*?\]", "", raw_title).strip()
            uid = "th_live_" + str(n.get("id") or abs(hash(link)) % 10000000)
            score = min(97, max(86, int(n.get("score") or 85)))
            grade = "S" if score >= 91 else "A"
            b0 = badges[0] if badges else "핵심 수치"
            items.append({
                "id": uid,
                "category": target_cat,
                "grade": grade,
                "score": score,
                "title": f"[시크릿 조합] \"{clean_t}\" — 원문 숫자와 내 지갑·일상에 미치는 실제 영향 완전 해설",
                "orig_title": raw_title,
                "url": link,
                "thumb": n.get("thumb") or "",
                "source": n.get("source") or "대한민국 정책브리핑",
                "published": n.get("published") or today_str,
                "license": n.get("license") or "공공누리 제1유형 (출처표시·상업적 이용 가능)",
                "safety": 99 if n.get("category") == "kogl1" else 95,
                "transform_score": 96,
                "rpm": "최상" if target_cat == "cat2_economy" else "상",
                "target_len": "롱폼 15~30분 + 쇼츠 3편",
                "badges": badges[:4],
                "thumb_3tier": {
                    "top": f"브리핑 원문 열어보니.. \"{b0}\"?!",
                    "mid": clean_t[:28],
                    "bot": "당장 누구부터 바뀌는지 3분 만에 핵심 정리",
                },
                "hook_30s": {
                    "s0_6": f"[0~6초 Google Flow AI 훅] 공식 브리핑 문서를 짚으며 질문하는 해설자: \"방금 발표된 '{clean_t[:18]}...', 진짜 핵심 숫자는 따로 있습니다!\"",
                    "s6_18": f"[6~18초 핵심 숫자 카드] 브리핑 원문 핵심({desc[:68]}...) + GSAP 수치 강조 배지({', '.join(badges[:2])})",
                    "s18_30": "[18~30초 Draw-on 클리프행어] 4대 페르소나(사실 확인·제도 해설·생활 영향·반론 검토)가 입체적으로 분석 시작",
                },
                "engine_recipe": "정책브리핑 공공누리 원문 + 4대 페르소나 해설 + huashu/GSAP 데이터 차트 + CapCut 초안 & MP4",
            })
            if len(items) >= 14:
                break
    except Exception as e:
        print(f"[참고] kr_news_store 연동 건너뜀: {e}")
    return items


def main():
    dry = "--dry" in sys.argv
    now_kst = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")

    seeds = get_curated_seed_items(today_str)
    live = fetch_live_kogl_for_hub(today_str)

    # ID 중복 제거 병합
    seen = set()
    merged = []
    for it in seeds + live:
        if it["id"] not in seen:
            seen.add(it["id"])
            merged.append(it)

    print(f"[8대 2차가공 허브] 카테고리 {len(CATEGORIES)}개 · 총 소재 {len(merged)}개 (시드 {len(seeds)} + 실시간 {len(live)}) 준비 완료")
    if dry:
        return

    payload = {
        "updated": now_kst.strftime("%Y-%m-%d %H:%M KST"),
        "categories": CATEGORIES,
        "items": merged,
    }
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    js_content = (
        f"window.TRANSFORM_HUB_UPDATED = {json.dumps(payload['updated'], ensure_ascii=False)};\n"
        f"window.TRANSFORM_HUB_CATS = {json.dumps(CATEGORIES, ensure_ascii=False)};\n"
        f"window.TRANSFORM_HUB = {json.dumps(merged, ensure_ascii=False)};\n"
    )
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"저장 완료: {OUT} ({len(js_content):,} bytes)")


if __name__ == "__main__":
    main()
