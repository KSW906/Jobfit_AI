import { useState, useEffect } from 'react'
import InputPage from './pages/InputPage'
import ResultPage from './pages/ResultPage'
import AuthPage from './pages/AuthPage'
import ChatbotWidget from './components/ChatbotWidget'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('auth_token'))
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  // 애플리케이션 시작 시 토큰 유효성 검증
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('auth_token')
      if (storedToken) {
        try {
          const res = await fetch('/api/auth/me', {
            headers: { 
              'Authorization': `Bearer ${storedToken}` 
            }
          })
          const data = await res.json()
          if (res.ok && data.logged_in) {
            setUser(data.user)
            setToken(storedToken)
          } else {
            localStorage.removeItem('auth_token')
            setToken(null)
            setUser(null)
          }
        } catch (e) {
          console.error('인증 체크 에러:', e)
        }
      }
      setAuthChecked(true)
    }
    checkAuth()
  }, [])

  const handleLoginSuccess = (newToken, loggedInUser) => {
    setToken(newToken)
    setUser(loggedInUser)
  }

  const handleLogout = async () => {
    const currentToken = localStorage.getItem('auth_token')
    if (currentToken) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 
            'Authorization': `Bearer ${currentToken}` 
          }
        })
      } catch (e) {
        console.error('로그아웃 요청 실패:', e)
      }
    }
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
    setResult(null)
    setError(null)
  }

  const handleAnalyze = async (skills, limit, preferences, priorities, resume, feedbackMode) => {
    setLoading(true)
    setError(null)
    setResult(null)

    const currentToken = localStorage.getItem('auth_token')

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${currentToken}`
        },
        body: JSON.stringify({
          my_skills: skills,
          limit,
          preferences,
          priorities,
          resume,
          feedback_mode: feedbackMode
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || '분석 실패')
      }

      const data = await res.json()
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // 🕒 과거 분석 이력 상세 로드 및 Result 구조 매핑 복원 함수
  const handleLoadHistory = async (historyId) => {
    setLoading(true)
    setError(null)
    const currentToken = localStorage.getItem('auth_token')

    try {
      const res = await fetch(`/api/analyze/history/${historyId}`, {
        headers: { 
          'Authorization': `Bearer ${currentToken}` 
        }
      })

      if (!res.ok) throw new Error('이전 분석 기록을 로드하지 못했습니다.')
      const data = await res.json()

      // 보관된 스냅샷 규격을 현재 대시보드 구조에 맞춰 강제 매핑 및 데이터 부활
      setResult({
        results: data.top_matches.map(m => ({
          job: {
            title: m.job_title,
            company: m.company,
            location: m.location,
            salary: m.salary,
            employment_type: "보관된 기록",
            apply_url: null
          },
          fit_score: m.fit_score,
          matched_skills: m.matched_skills || [],
          missing_skills: [],
          feedback: ["이전 보관 리포트 요약본입니다. 전체 상세 피드백은 실시간 분석 결과 탭을 활용해 주세요."],
          match_details: { skills: m.fit_score, job_title: 100, category: 100, salary: 100, location: 100 }
        })),
        summary: {
          total_jobs: data.total_jobs,
          analyzed_jobs: data.analyzed_jobs,
          avg_fit_score: data.avg_fit_score
        },
        learning_priority: data.skills_snapshot.map(s => ({ skill: s, demand_count: 1 })),
        resume_used: false
      })

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResult(null)
    setError(null)
  }

  if (!authChecked) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0a0a0f',
        color: '#6b6b85',
        fontFamily: 'sans-serif'
      }}>
        인증 로드 중...
      </div>
    )
  }

  if (!token) {
    return <AuthPage onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <>
      <header style={{
        position: 'absolute',
        top: 20,
        right: 20,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        gap: 15,
        background: 'rgba(26, 26, 36, 0.6)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: 50,
        padding: '8px 18px',
        backdropFilter: 'blur(8px)',
        fontSize: 13,
        color: '#f0f0f8'
      }}>
        <span>👤 {user ? user.username : '사용자'}님</span>
        <button 
          onClick={handleLogout}
          style={{
            background: 'none',
            border: 'none',
            color: '#f76a8a',
            fontWeight: 600,
            cursor: 'pointer',
            fontSize: 13,
            padding: 0
          }}
        >
          로그아웃
        </button>
      </header>

      {loading && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(10,10,15,0.8)', zIndex: 999,
          display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#b8b0ff',
          fontSize: '16px', fontWeight: 'bold'
        }}>
          데이터 처리 및 매칭 엔진 구동 중...
        </div>
      )}

      {!result
        ? <InputPage onAnalyze={handleAnalyze} onLoadHistory={handleLoadHistory} loading={loading} error={error} />
        : <ResultPage result={result} onReset={handleReset} onLoadHistory={handleLoadHistory} />
      }
      {token && <ChatbotWidget />}
    </>
  )
}