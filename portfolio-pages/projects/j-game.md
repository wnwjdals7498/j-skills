---
layout: default
title: J Game - 오프라인 한국어 낱말퍼즐
---

# J Game - 오프라인 한국어 낱말퍼즐

[소스 코드 보기](https://github.com/wnwjdals7498/j-game)

## 목표

기기 안의 SQLite 사전 데이터를 이용해 십자말 형태의 한국어 낱말퍼즐을 생성하는 Flutter 애플리케이션입니다. 게임 실행에 서버를 요구하지 않으며, 단어 데이터는 주기적으로 갱신할 수 있도록 설계했습니다.

## 구현 포인트

- 단어별 정답·오답 통계를 반영한 퍼즐 출제
- 2~5음절 낱말을 교차 배치하는 격자 생성 로직
- Drift와 SQLite를 사용한 오프라인 데이터 관리
- manifest와 체크섬 검증을 거치는 데이터베이스 갱신
- 다운로드 실패 시 기존 데이터베이스를 유지하는 통합 테스트

## 사용 기술

Flutter, Dart, Drift, SQLite, Provider, GitHub Releases

## 검증

앱의 불변 조건 검사, 정적 분석, 단위·통합 테스트를 분리해 실행합니다. 자세한 절차는 저장소 README와 `docs/`에 기록했습니다.
