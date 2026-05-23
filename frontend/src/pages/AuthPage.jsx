import { useState } from 'react'
import styles from './AuthPage.module.css'

export default function AuthPage({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMsg(null)

    const trimmedUsername = username.trim()
    const trimmedEmail = email.trim()
    const trimmedPassword = password.trim()

    if (!trimmedUsername || !trimmedPassword || (isRegister && !trimmedEmail)) {
      setError('모든 필수 항목을 입력해 주세요.')
      setLoading(false)
      return
    }

    try {
      if (isRegister) {
        // 회원가입 요청
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: trimmedUsername,
            email: trimmedEmail,
            password: trimmedPassword,
          }),
        })

        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.error || '회원가입에 실패했습니다.')
        }

        // 회원가입 성공 시, 바로 자동 로그인 시도
        const loginRes = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: trimmedUsername,
            password: trimmedPassword,
          }),
        })

        const loginData = await loginRes.json()
        if (!loginRes.ok) {
          setIsRegister(false)
          setSuccessMsg('회원가입이 완료되었습니다! 로그인해 주세요.')
          setPassword('')
        } else {
          localStorage.setItem('auth_token', loginData.token)
          onLoginSuccess(loginData.token, loginData.user)
        }
      } else {
        // 로그인 요청
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: trimmedUsername,
            password: trimmedPassword,
          }),
        })

        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.error || '로그인에 실패했습니다.')
        }

        localStorage.setItem('auth_token', data.token)
        onLoginSuccess(data.token, data.user)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleMode = () => {
    setIsRegister(prev => !prev)
    setError(null)
    setSuccessMsg(null)
    setUsername('')
    setEmail('')
    setPassword('')
  }

  return (
    <div className={styles.page}>
      {/* 배경 데코레이션 블롭 */}
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.container}>
        {/* 헤더 */}
        <div className={styles.header}>
          <div className={styles.badge}>Jobfit-AI 커리어 엔진</div>
          <h1 className={styles.title}>
            {isRegister ? (
              <>
                새로운 <span className={styles.accent}>커리어 여정</span>을<br />시작해볼까요?
              </>
            ) : (
              <>
                나만을 위한 <br /><span className={styles.accent}>맞춤형 채용 엔진</span>
              </>
            )}
          </h1>
          <p className={styles.subtitle}>
            {isRegister 
              ? '계정을 생성하여 스킬 진단과 맞춤 채용 정보를 기록해 보세요.' 
              : '로그인하여 맞춤 공고 확인 및 AI 스킬 로드맵을 이어가세요.'}
          </p>
        </div>

        {/* 폼 카드 */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>
            {isRegister ? '회원가입' : '로그인'}
          </h2>
          
          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label className={styles.label}>아이디</label>
              <input
                type="text"
                className={styles.input}
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="아이디를 입력하세요"
                required
              />
            </div>

            {isRegister && (
              <div className={styles.inputGroup}>
                <label className={styles.label}>이메일</label>
                <input
                  type="email"
                  className={styles.input}
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                />
              </div>
            )}

            <div className={styles.inputGroup}>
              <label className={styles.label}>비밀번호</label>
              <input
                type="password"
                className={styles.input}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
                required
              />
            </div>

            {error && <div className={styles.error}>⚠ {error}</div>}
            {successMsg && <div className={styles.success}>✓ {successMsg}</div>}

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={loading}
            >
              {loading ? (
                <span className={styles.spinnerWrap}>
                  <span className={styles.spinner} /> 처리 중...
                </span>
              ) : (
                isRegister ? '회원가입 완료 →' : '로그인하기 →'
              )}
            </button>
          </form>

          {/* 전환 가이드 */}
          <div className={styles.toggleGuide}>
            {isRegister ? '이미 계정이 있으신가요?' : '아직 계정이 없으신가요?'}
            <button type="button" className={styles.toggleBtn} onClick={toggleMode}>
              {isRegister ? '로그인하러 가기' : '회원가입하러 가기'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
