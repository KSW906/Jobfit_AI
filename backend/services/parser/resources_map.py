# -*- coding: utf-8 -*-

"""
resources_map.py — 기술 스택별 추천 교육용 자원(공식문서, 강좌 등)의 정보 및 링크를 매핑합니다.
"""

RESOURCES_DB = {
    "python": [
        {"type": "doc", "name": "Python 공식 자습서 (한글)", "url": "https://docs.python.org/ko/3/tutorial/"},
        {"type": "youtube", "name": "나도코딩 - 파이썬 코딩 기초 강좌", "url": "https://www.youtube.com/watch?v=kWiCuklohdY"},
        {"type": "course", "name": "인프런 - 프로그래밍 시작하기 : 파이썬", "url": "https://www.inflearn.com/course/%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%98%EB%B0%8D-%EC%8B%9C%EC%9E%91%ED%95%98%EA%B8%B0-%ED%8C%8C%EC%9D%B4%EC%8D%AC"}
    ],
    "javascript": [
        {"type": "doc", "name": "MDN JavaScript 가이드", "url": "https://developer.mozilla.org/ko/docs/Web/JavaScript/Guide"},
        {"type": "doc", "name": "모던 JavaScript 튜토리얼", "url": "https://ko.javascript.info/"},
        {"type": "youtube", "name": "드림코딩 - 자바스크립트 기초 강의", "url": "https://www.youtube.com/watch?v=wcsVJMOK5cY"}
    ],
    "typescript": [
        {"type": "doc", "name": "TypeScript 공식 핸드북 (한글)", "url": "https://typescript-kr.github.io/"},
        {"type": "youtube", "name": "코딩애플 - 타입스크립트 꿀잼 강좌", "url": "https://www.youtube.com/watch?v=xkpcLx_G9R4"}
    ],
    "react": [
        {"type": "doc", "name": "React 공식 신규 문서 (한글)", "url": "https://ko.react.dev/"},
        {"type": "youtube", "name": "코딩앙마 - 리액트 초급 기초 강좌", "url": "https://www.youtube.com/watch?v=35yYObTJH9w"},
        {"type": "course", "name": "인프런 - 한 입 크기로 잘라 먹는 리액트", "url": "https://www.inflearn.com/course/%ED%95%9C%EC%9E%85-%EB%A6%AC%EC%95%A1%ED%8A%B8"}
    ],
    "vue": [
        {"type": "doc", "name": "Vue.js 공식 가이드 (한글)", "url": "https://ko.vuejs.org/guide/introduction.html"},
        {"type": "course", "name": "인프런 - Vue.js 시작하기", "url": "https://www.inflearn.com/course/Age-of-Vuejs"}
    ],
    "node.js": [
        {"type": "doc", "name": "Node.js 공식 자습서 (한글)", "url": "https://nodejs.org/ko/docs/guides/"},
        {"type": "youtube", "name": "조코딩 - Node.js 기초 웹 서버 개발", "url": "https://www.youtube.com/watch?v=Tt_tKhhhJqY"}
    ],
    "java": [
        {"type": "youtube", "name": "생활코딩 - Java 기초 강좌", "url": "https://www.youtube.com/watch?v=JDY7Gq1zY9Q"},
        {"type": "course", "name": "인프런 - 김영한의 자바 입문", "url": "https://www.inflearn.com/course/%EA%B9%80%EC%98%81%ED%95%9C%EC%9D%98-%EC%9E%90%EB%B0%94-%EC%9e%85%eb%ac%b8"}
    ],
    "spring": [
        {"type": "doc", "name": "Spring Boot 공식 문서 가이드", "url": "https://spring.io/guides"},
        {"type": "course", "name": "인프런 - 스프링 입문 (김영한)", "url": "https://www.inflearn.com/course/%EC%8A%A4%ED%94%84%EB%A7%81-%EC%9E%85%EB%AC%B8-%EC%8A%A4%ED%94%84%EB%A7%81%EB%B6%80%ED%8A%B8"}
    ],
    "django": [
        {"type": "doc", "name": "Django 공식 튜토리얼 (한글)", "url": "https://docs.djangoproject.com/ko/5.0/intro/tutorial01/"},
        {"type": "youtube", "name": "김왼손의 왼손코딩 - 장고 입문 강좌", "url": "https://www.youtube.com/watch?v=iWzD2W2p_yM"}
    ],
    "flask": [
        {"type": "doc", "name": "Flask 공식 Quickstart (한글)", "url": "https://flask-docs-kr.readthedocs.io/ko/latest/quickstart.html"},
        {"type": "youtube", "name": "파이썬 웹 개발 Flask 초보 기초 강좌", "url": "https://www.youtube.com/watch?v=9MHYK6V40WY"}
    ],
    "docker": [
        {"type": "doc", "name": "Docker 공식 시작하기 문서", "url": "https://docs.docker.com/get-started/"},
        {"type": "youtube", "name": "얄팍한 코딩사전 - 가장 쉬운 Docker 안내서", "url": "https://www.youtube.com/watch?v=hWPv9LMlme8"},
        {"type": "course", "name": "인프런 - 개발자를 위한 쉬운 Docker 강좌", "url": "https://www.inflearn.com/course/%EB%8F%84%EC%BB%A4-%EC%89%AC%EA%B2%8C-%EB%B0%B0%EC%9A%B0%EA%B8%B0"}
    ],
    "aws": [
        {"type": "doc", "name": "AWS 기본 에센셜 가이드 자료", "url": "https://aws.amazon.com/ko/getting-started/"},
        {"type": "youtube", "name": "생활코딩 - AWS 클라우드 웹호스팅 강좌", "url": "https://www.youtube.com/watch?v=7M_6rVf6P2Q"}
    ],
    "git": [
        {"type": "doc", "name": "Git-SCM 프로북 가이드 (한글)", "url": "https://git-scm.com/book/ko/v2"},
        {"type": "youtube", "name": "지옥에서 온 Git 강좌 (생활코딩)", "url": "https://www.youtube.com/watch?v=YFNQDZsFtg0"}
    ],
    "mysql": [
        {"type": "doc", "name": "MySQL 공식 레퍼런스 설명서", "url": "https://dev.mysql.com/doc/"},
        {"type": "youtube", "name": "생활코딩 - 관계형 데이터베이스 MySQL", "url": "https://www.youtube.com/watch?v=i9WfO8d5RVo"}
    ],
    "postgresql": [
        {"type": "doc", "name": "PostgreSQL 공식 문서 가이드 (한글)", "url": "https://postgresql.kr/docs/13/"},
        {"type": "youtube", "name": "PostgreSQL 데이터베이스 100분 요약 강좌", "url": "https://www.youtube.com/watch?v=qw42OswAtsE"}
    ],
    "mongodb": [
        {"type": "doc", "name": "MongoDB 매뉴얼 공식 가이드", "url": "https://www.mongodb.com/docs/manual/"},
        {"type": "youtube", "name": "코딩악마 - NoSQL MongoDB 초보 강좌", "url": "https://www.youtube.com/watch?v=33K2gP8pW5Y"}
    ],
    "redis": [
        {"type": "doc", "name": "Redis 시작하기 및 가이드", "url": "https://redis.io/docs/latest/develop/get-started/"},
        {"type": "youtube", "name": "우아한테크코딩 - Redis 야무지게 사용하기", "url": "https://www.youtube.com/watch?v=mPB2CZiAkKM"}
    ],
    "kubernetes": [
        {"type": "doc", "name": "Kubernetes 튜토리얼 핸드북 (한글)", "url": "https://kubernetes.io/ko/docs/tutorials/"},
        {"type": "youtube", "name": "조대협 - 쿠버네티스 쌩초보 입문 강좌", "url": "https://www.youtube.com/watch?v=6n5OBsVfV24"}
    ],
    "go": [
        {"type": "doc", "name": "A Tour of Go (한글 예제 튜토리얼)", "url": "https://go-tour-ko.appspot.com/"},
        {"type": "youtube", "name": "Tucker의 Go 프로그래밍 입문 강의", "url": "https://www.youtube.com/watch?v=LgK4P0SjD1M"}
    ],
    "rust": [
        {"type": "doc", "name": "The Rust Programming Language 프로북 (한글)", "url": "https://doc.rust-kr.org/"},
        {"type": "youtube", "name": "쉬운 러스트 프로그래밍 입문", "url": "https://www.youtube.com/watch?v=IPmILk1vH_k"}
    ]
}

def get_resources_for_skill(skill_name: str) -> list:
    """
    특정 스킬 이름에 해당하는 동영상 및 강좌 자원 목록을 반환합니다.
    매핑 목록에 없을 시, 구글 공식 가이드 및 튜토리얼 검색 링크를 가공하여 동적으로 생성합니다.
    """
    key = skill_name.lower().strip()
    if key in RESOURCES_DB:
        return RESOURCES_DB[key]
    
    # 맵에 없을 시 동적 폴백 (Google 검색 기반)
    import urllib.parse
    encoded_skill = urllib.parse.quote(skill_name)
    
    return [
        {
            "type": "doc",
            "name": f"{skill_name} 공식 문서(Documentation) 가이드",
            "url": f"https://www.google.com/search?q={encoded_skill}+official+documentation"
        },
        {
            "type": "youtube",
            "name": f"YouTube - {skill_name} 기초 학습 가이드 동영상",
            "url": f"https://www.youtube.com/results?search_query={encoded_skill}+tutorial"
        }
    ]
