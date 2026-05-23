import { useState, useEffect } from 'react'
import InputPage from './pages/InputPage'
import ResultPage from './pages/ResultPage'
import AuthPage from './pages/AuthPage'

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
            // 무효한 토큰 처리
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

  const handleAnalyze = async (skills, limit, preferences, priorities, resume) => {
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
          resume
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
      {/* 글로벌 사용자 인증 헤더 */}
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

      {!result
        ? <InputPage onAnalyze={handleAnalyze} loading={loading} error={error} />
        : <ResultPage result={result} onReset={handleReset} />
      }
    </>
  )
}
