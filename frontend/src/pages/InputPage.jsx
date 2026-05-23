import { useState, useEffect } from 'react'
import styles from './InputPage.module.css'

const SUGGESTED_SKILLS = [
  'Python', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Node.js',
  'Java', 'Spring', 'Flask', 'Django', 'Docker', 'AWS', 'Git',
  'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Kubernetes', 'Go', 'Rust',
]

export default function InputPage({ onAnalyze, loading, error }) {
  const [skills, setSkills]   = useState([])
  const [input, setInput]     = useState('')
  const [limit, setLimit]     = useState(5)

  // 선호 조건 및 우선순위(가중치) 상태 추가
  const [showPreferences, setShowPreferences] = useState(false)
  const [prefTitle, setPrefTitle]             = useState('')
  const [prefCategory, setPrefCategory]       = useState('')
  const [prefSalary, setPrefSalary]           = useState('')
  const [prefLocation, setPrefLocation]       = useState('')

  const [wSkills, setWSkills]                 = useState(3)
  const [wTitle, setWTitle]                   = useState(1)
  const [wCategory, setWCategory]             = useState(1)
  const [wSalary, setWSalary]                 = useState(1)
  const [wLocation, setWLocation]             = useState(1)

  // 이력서 상태 추가
  const [showResume, setShowResume]           = useState(false)
  const [resume, setResume]                   = useState('')

  const [stats, setStats] = useState({ remotive: 0, adzuna: 0, total: 0 })
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)

  const fetchStats = () => {
    fetch('/api/jobs/stats')
      .then(res => {
        if (!res.ok) throw new Error('통계 로드 실패')
        return res.json()
      })
      .then(data => setStats(data))
      .catch(err => console.error('Failed to load stats:', err))
  }

  // 컴포넌트 마운트 시 사용자 프로필 로드
  useEffect(() => {
    fetchStats()
    const token = localStorage.getItem('auth_token')
    fetch('/api/profile', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error('프로필 로드 실패')
        return res.json()
      })
      .then(data => {
        if (data) {
          if (data.skills) setSkills(data.skills)
          if (data.resume) {
            setResume(data.resume)
            setShowResume(true)
          }
          if (data.preferences) {
            setPrefTitle(data.preferences.job_title || '')
            setPrefCategory(data.preferences.category || '')
            setPrefSalary(data.preferences.salary || '')
            setPrefLocation(data.preferences.location || '')
            if (
              data.preferences.job_title ||
              data.preferences.category ||
              data.preferences.salary ||
              data.preferences.location
            ) {
              setShowPreferences(true)
            }
          }
          if (data.priorities) {
            setWSkills(data.priorities.skills ?? 3)
            setWTitle(data.priorities.job_title ?? 1)
            setWCategory(data.priorities.category ?? 1)
            setWSalary(data.priorities.salary ?? 1)
            setWLocation(data.priorities.location ?? 1)
          }
        }
      })
      .catch(err => console.error('Failed to load profile:', err))
  }, [])

  const addSkill = (skill) => {
    const trimmed = skill.trim()
    if (!trimmed) return
    if (skills.map(s => s.toLowerCase()).includes(trimmed.toLowerCase())) return
    setSkills(prev => [...prev, trimmed])
    setInput('')
  }

  const removeSkill = (s) => setSkills(prev => prev.filter(x => x !== s))

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addSkill(input)
    }
    if (e.key === 'Backspace' && !input && skills.length) {
      setSkills(prev => prev.slice(0, -1))
    }
  }

  const handleSubmit = async () => {
    if (skills.length === 0) return
    
    const preferences = {
      job_title: prefTitle,
      category: prefCategory,
      salary: prefSalary ? Number(prefSalary) : null,
      location: prefLocation
    }

    const priorities = {
      skills: wSkills,
      job_title: prefTitle ? wTitle : 0,
      category: prefCategory ? wCategory : 0,
      salary: prefSalary ? wSalary : 0,
      location: prefLocation ? wLocation : 0
    }

    // 서버에 프로필 영구 저장
    try {
      const token = localStorage.getItem('auth_token')
      await fetch('/api/profile', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          skills,
          resume,
          preferences,
          priorities
        })
      })
    } catch (err) {
      console.error('Failed to save profile:', err)
    }

    onAnalyze(skills, limit, preferences, priorities, resume)
  }

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/jobs/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (!res.ok) throw new Error('동기화 실패')
      const data = await res.json()
      setSyncResult(data)
      fetchStats()
    } catch (err) {
      console.error(err)
      setSyncResult({ error: err.message })
    } finally {
      setSyncing(false)
    }
  }


  return (
    <div className={styles.page}>
      {/* 배경 장식 */}
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.container}>
        {/* 헤더 */}
        <div className={styles.header}>
          <div className={styles.badge}>AI 채용 분석</div>
          <h1 className={styles.title}>
            내 스킬과<br />
            <span className={styles.accent}>채용 시장</span>을<br />
            비교해보세요
          </h1>
          <p className={styles.subtitle}>
            보유 기술을 입력하면 실제 채용 공고와 비교해<br />
            부족한 스킬과 학습 방향을 제안해드려요
          </p>
        </div>

        {/* 스킬 입력 카드 */}
        <div className={styles.card}>
          <label className={styles.label}>보유 스킬 입력</label>

          {/* 태그 입력창 */}
          <div className={styles.tagInput}>
            {skills.map(s => (
              <span key={s} className={styles.tag}>
                {s}
                <button onClick={() => removeSkill(s)} className={styles.tagX}>×</button>
              </span>
            ))}
            <input
              className={styles.input}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={skills.length === 0 ? 'Python, React, Docker... (Enter로 추가)' : ''}
            />
          </div>

          {/* 추천 스킬 */}
          <div className={styles.suggestWrap}>
            <span className={styles.suggestLabel}>빠른 선택</span>
            <div className={styles.suggests}>
              {SUGGESTED_SKILLS.filter(s =>
                !skills.map(x => x.toLowerCase()).includes(s.toLowerCase())
              ).map(s => (
                <button key={s} className={styles.suggest} onClick={() => addSkill(s)}>
                  + {s}
                </button>
              ))}
            </div>
          </div>

          {/* 분석 수 */}
          <div className={styles.limitRow}>
            <label className={styles.limitLabel}>비교할 채용공고 수</label>
            <div className={styles.limitBtns}>
              {[5, 10, 20].map(n => (
                <button
                  key={n}
                  className={`${styles.limitBtn} ${limit === n ? styles.limitActive : ''}`}
                  onClick={() => setLimit(n)}
                >
                  {n}개
                </button>
              ))}
            </div>
          </div>

          {/* 선호 조건 및 가중치 토글 버튼 */}
          <button
            type="button"
            className={styles.prefToggleBtn}
            onClick={() => setShowPreferences(prev => !prev)}
          >
            {showPreferences ? '⚡ 선호 조건 접기' : '⚙️ 선호 조건 및 우선순위 설정 (선택)'}
          </button>

          {/* 선호 조건 패널 */}
          {showPreferences && (
            <div className={styles.preferencesPanel}>
              {/* 스킬 가중치 */}
              <div className={styles.prefGroup}>
                <div className={styles.prefLabelRow}>
                  <label className={styles.prefLabel}>보유 스킬 중요도</label>
                  <div className={styles.weightSelector}>
                    {[
                      { label: '보통', val: 1 },
                      { label: '높음', val: 3 },
                      { label: '매우 높음', val: 5 }
                    ].map(w => (
                      <button
                        key={w.val}
                        type="button"
                        className={`${styles.weightBtn} ${wSkills === w.val ? styles.weightActive : ''}`}
                        onClick={() => setWSkills(w.val)}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* 선호 직무 */}
              <div className={styles.prefGroup}>
                <div className={styles.prefLabelRow}>
                  <label className={styles.prefLabel}>희망 직무명</label>
                  <div className={styles.weightSelector}>
                    {[
                      { label: '무관', val: 0 },
                      { label: '보통', val: 1 },
                      { label: '높음', val: 3 },
                      { label: '매우 높음', val: 5 }
                    ].map(w => (
                      <button
                        key={w.val}
                        type="button"
                        className={`${styles.weightBtn} ${wTitle === w.val ? styles.weightActive : ''}`}
                        onClick={() => setWTitle(w.val)}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  className={styles.prefInput}
                  value={prefTitle}
                  onChange={e => setPrefTitle(e.target.value)}
                  placeholder="예: Developer, 백엔드"
                />
              </div>

              {/* 선호 분야 */}
              <div className={styles.prefGroup}>
                <div className={styles.prefLabelRow}>
                  <label className={styles.prefLabel}>희망 직무 분야</label>
                  <div className={styles.weightSelector}>
                    {[
                      { label: '무관', val: 0 },
                      { label: '보통', val: 1 },
                      { label: '높음', val: 3 },
                      { label: '매우 높음', val: 5 }
                    ].map(w => (
                      <button
                        key={w.val}
                        type="button"
                        className={`${styles.weightBtn} ${wCategory === w.val ? styles.weightActive : ''}`}
                        onClick={() => setWCategory(w.val)}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  className={styles.prefInput}
                  value={prefCategory}
                  onChange={e => setPrefCategory(e.target.value)}
                  placeholder="예: Software Development, it-jobs"
                />
              </div>

              {/* 희망 연봉 */}
              <div className={styles.prefGroup}>
                <div className={styles.prefLabelRow}>
                  <label className={styles.prefLabel}>최소 희망 연봉 (숫자만)</label>
                  <div className={styles.weightSelector}>
                    {[
                      { label: '무관', val: 0 },
                      { label: '보통', val: 1 },
                      { label: '높음', val: 3 },
                      { label: '매우 높음', val: 5 }
                    ].map(w => (
                      <button
                        key={w.val}
                        type="button"
                        className={`${styles.weightBtn} ${wSalary === w.val ? styles.weightActive : ''}`}
                        onClick={() => setWSalary(w.val)}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="number"
                  className={styles.prefInput}
                  value={prefSalary}
                  onChange={e => setPrefSalary(e.target.value)}
                  placeholder="예: 50000"
                />
              </div>

              {/* 희망 근무지 */}
              <div className={styles.prefGroup}>
                <div className={styles.prefLabelRow}>
                  <label className={styles.prefLabel}>희망 근무 위치</label>
                  <div className={styles.weightSelector}>
                    {[
                      { label: '무관', val: 0 },
                      { label: '보통', val: 1 },
                      { label: '높음', val: 3 },
                      { label: '매우 높음', val: 5 }
                    ].map(w => (
                      <button
                        key={w.val}
                        type="button"
                        className={`${styles.weightBtn} ${wLocation === w.val ? styles.weightActive : ''}`}
                        onClick={() => setWLocation(w.val)}
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  className={styles.prefInput}
                  value={prefLocation}
                  onChange={e => setPrefLocation(e.target.value)}
                  placeholder="예: London, 서울"
                />
              </div>
            </div>
          )}

          {/* 이력서 입력 토글 버튼 */}
          <button
            type="button"
            className={styles.resumeToggleBtn}
            onClick={() => setShowResume(prev => !prev)}
          >
            {showResume ? '⚡ 이력서 입력 접기' : '📝 이력서 정보 입력 (선택 - Claude AI 1:1 맞춤 피드백)'}
          </button>

          {/* 이력서 입력 패널 */}
          {showResume && (
            <div className={styles.resumePanel}>
              <label className={styles.prefLabel}>내 이력서 (텍스트)</label>
              <p className={styles.resumeDesc}>
                이력서의 프로젝트 경험이나 주요 경력 내용을 자유롭게 입력해 주세요. Claude AI가 분석하여 부족한 스킬에 대한 1:1 맞춤형 피드백을 제공합니다.
              </p>
              <textarea
                className={styles.resumeTextarea}
                value={resume}
                onChange={e => setResume(e.target.value)}
                placeholder="예: React와 Node.js 기반 웹 프로젝트 개발을 주로 수행했습니다. AWS EC2와 S3를 배포에 사용하였으며, Docker나 CI/CD 도입 경험은 없어서 기술 보완을 원합니다."
                rows={6}
              />
            </div>
          )}

          {/* 에러 */}
          {error && <div className={styles.error}>⚠ {error}</div>}

          {/* 분석 버튼 */}
          <button
            className={styles.analyzeBtn}
            onClick={handleSubmit}
            disabled={loading || skills.length === 0}
          >
            {loading ? (
              <span className={styles.spinnerWrap}>
                <span className={styles.spinner} /> 분석 중...
              </span>
            ) : (
              `${skills.length > 0 ? skills.length + '개 스킬' : ''} 분석 시작 →`
            )}
          </button>
        </div>

        {/* 채용 데이터 동기화 대시보드 */}
        <div className={styles.syncCard}>
          <div className={styles.syncHeader}>
            <span className={styles.syncTitleIcon}>🔄</span>
            <div className={styles.syncTitleWrap}>
              <h3 className={styles.syncTitle}>채용 데이터 동기화</h3>
              <p className={styles.syncDesc}>실시간 채용 공고를 크롤링하여 데이터베이스를 최신 상태로 유지합니다.</p>
            </div>
          </div>

          <div className={styles.statsGrid}>
            <div className={styles.statBox}>
              <span className={styles.statLabel}>Remotive (해외)</span>
              <span className={styles.statVal}>{stats.remotive}개</span>
            </div>

            <div className={styles.statBox}>
              <span className={styles.statLabel}>Adzuna (해외)</span>
              <span className={styles.statVal}>{stats.adzuna}개</span>
            </div>
            <div className={`${styles.statBox} ${styles.statBoxTotal}`}>
              <span className={styles.statLabel}>전체 채용공고</span>
              <span className={styles.statVal}>{stats.total}개</span>
            </div>
          </div>

          {syncResult && (
            <div className={syncResult.error ? styles.syncErrBox : styles.syncSuccessBox}>
              {syncResult.error ? (
                <span>⚠ 동기화 중 오류가 발생했습니다: {syncResult.error}</span>
              ) : (
                <div className={styles.syncResults}>
                  <div className={styles.syncResHeader}>✅ 동기화 완료!</div>
                  <ul className={styles.syncResList}>
                    {Object.entries(syncResult.results || {}).map(([source, r]) => (
                      <li key={source} className={styles.syncResItem}>
                        <span className={styles.syncSourceName}>{source === 'remotive' ? 'Remotive' : 'Adzuna'}:</span>
                        {r.status === 'success' ? (
                          <span className={styles.syncSourceSuccess}>
                            +{r.saved} 저장 ({r.skipped} 스킵)
                          </span>
                        ) : r.status === 'skipped' ? (
                          <span className={styles.syncSourceSkipped}>건너뜀 (인증키 없음)</span>
                        ) : (
                          <span className={styles.syncSourceError}>에러</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <div className={styles.syncSummary}>
                    총 <strong>{syncResult.summary?.total_saved}</strong>개의 공고가 추가되었습니다.
                  </div>
                </div>
              )}
            </div>
          )}

          <button
            className={styles.syncBtn}
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? (
              <span className={styles.spinnerWrap}>
                <span className={styles.spinner} /> 동기화 진행 중...
              </span>
            ) : (
              '실시간 채용 데이터 동기화 (Sync All)'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
