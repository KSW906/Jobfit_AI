import { useState, useEffect } from 'react'
import styles from './Dashboard.module.css'

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
})

// ── 적합도 성장 추이 라인 차트 (경량 SVG) ──
function GrowthChart({ points }) {
  if (!points || points.length < 2) {
    return (
      <p className={styles.miniEmpty}>
        분석을 2회 이상 실행하면 적합도 성장 추이 그래프가 표시됩니다. (현재 {points?.length || 0}회)
      </p>
    )
  }

  const W = 620, H = 160, PAD = 28
  const xs = points.map((_, i) => PAD + (i * (W - PAD * 2)) / (points.length - 1))
  const toY = (v) => H - PAD - (Math.max(0, Math.min(100, v)) / 100) * (H - PAD * 2)
  const line = points.map((p, i) => `${xs[i]},${toY(p.avg_fit_score)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={styles.lineChart}>
      {[0, 25, 50, 75, 100].map((g) => (
        <g key={g}>
          <line x1={PAD} y1={toY(g)} x2={W - PAD} y2={toY(g)} className={styles.gridLine} />
          <text x={4} y={toY(g) + 3} className={styles.axisText}>{g}</text>
        </g>
      ))}
      <polyline points={line} className={styles.dataLine} />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={xs[i]} cy={toY(p.avg_fit_score)} r="4" className={styles.dataDot} />
          <text x={xs[i]} y={H - 8} className={styles.axisText} textAnchor="middle">{p.date}</text>
        </g>
      ))}
    </svg>
  )
}

export default function InsightsPanel() {
  const [growth, setGrowth] = useState(null)
  const [trends, setTrends] = useState(null)
  const [salary, setSalary] = useState(null)
  const [salarySkill, setSalarySkill] = useState('')
  const [salaryInput, setSalaryInput] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch('/api/insights/skill-growth', { headers: authHeaders() }).then((r) => (r.ok ? r.json() : null)),
      fetch('/api/insights/trends', { headers: authHeaders() }).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([g, t]) => {
        setGrowth(g)
        setTrends(t)
      })
      .catch((e) => console.error('인사이트 로드 실패:', e))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const url = salarySkill
      ? `/api/insights/salary?skill=${encodeURIComponent(salarySkill)}`
      : '/api/insights/salary'
    fetch(url, { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setSalary(d))
      .catch((e) => console.error('연봉 인사이트 로드 실패:', e))
  }, [salarySkill])

  if (loading) {
    return <p className={styles.loading}>인사이트 분석 중...</p>
  }

  const g = growth?.summary
  const maxBucket = Math.max(...(salary?.buckets?.map((b) => b.count) || [1]), 1)
  const fmt = (n) => (n != null ? n.toLocaleString() : '-')

  return (
    <div>
      {/* ── 1. 스킬 성장 대시보드 ── */}
      <div className={styles.insightCard}>
        <h3 className={styles.insightTitle}>📈 나의 적합도 성장 추이</h3>
        {g && g.total_runs >= 2 && (
          <div className={styles.statRow}>
            <div className={styles.statBox}>
              <span className={styles.statBoxNum}>{g.latest_score}%</span>
              <span className={styles.statBoxLabel}>최근 평균 적합도</span>
            </div>
            <div className={styles.statBox}>
              <span className={`${styles.statBoxNum} ${g.score_delta >= 0 ? styles.up : styles.down}`}>
                {g.score_delta >= 0 ? '▲' : '▼'} {Math.abs(g.score_delta)}%
              </span>
              <span className={styles.statBoxLabel}>적합도 변화</span>
            </div>
            <div className={styles.statBox}>
              <span className={`${styles.statBoxNum} ${g.skills_delta >= 0 ? styles.up : styles.down}`}>
                {g.skills_delta >= 0 ? '+' : ''}{g.skills_delta}
              </span>
              <span className={styles.statBoxLabel}>보유 스킬 변화</span>
            </div>
            <div className={styles.statBox}>
              <span className={styles.statBoxNum}>{g.total_runs}</span>
              <span className={styles.statBoxLabel}>총 분석 횟수</span>
            </div>
          </div>
        )}
        <GrowthChart points={growth?.points} />
      </div>

      {/* ── 2. 채용 시장 스킬 트렌드 ── */}
      <div className={styles.insightCard}>
        <h3 className={styles.insightTitle}>🔥 채용 시장 스킬 수요 트렌드</h3>
        <p className={styles.sectionDesc}>
          저장된 공고에서 가장 많이 요구된 스킬입니다. <span className={styles.ownedDot}>●</span> 표시는 내가 보유한 스킬입니다.
        </p>
        {!trends || trends.trends.length === 0 ? (
          <p className={styles.miniEmpty}>아직 집계된 스킬 통계가 없습니다.</p>
        ) : (
          <div className={styles.trendList}>
            {trends.trends.map((t) => (
              <div key={t.skill} className={styles.trendRow}>
                <span className={styles.trendName}>
                  {t.owned && <span className={styles.ownedDot}>●</span>} {t.skill}
                </span>
                <div className={styles.trendBarBg}>
                  <div
                    className={`${styles.trendBarFill} ${t.owned ? styles.trendOwned : ''}`}
                    style={{ width: `${t.ratio * 100}%` }}
                  />
                </div>
                <span className={styles.trendCount}>{t.count}건</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 3. 연봉 인사이트 ── */}
      <div className={styles.insightCard}>
        <h3 className={styles.insightTitle}>💰 연봉 인사이트</h3>
        <form
          className={styles.salaryFilter}
          onSubmit={(e) => {
            e.preventDefault()
            setSalarySkill(salaryInput.trim())
          }}
        >
          <input
            className={styles.salaryInput}
            value={salaryInput}
            onChange={(e) => setSalaryInput(e.target.value)}
            placeholder="스킬로 필터링 (예: React, Python) — 비우면 전체"
          />
          <button type="submit" className={styles.salaryBtn}>조회</button>
          {salarySkill && (
            <button
              type="button"
              className={styles.salaryClear}
              onClick={() => { setSalaryInput(''); setSalarySkill('') }}
            >
              초기화
            </button>
          )}
        </form>

        {!salary || salary.count === 0 ? (
          <p className={styles.miniEmpty}>{salary?.message || '연봉 정보가 있는 공고가 없습니다.'}</p>
        ) : (
          <>
            <div className={styles.statRow}>
              <div className={styles.statBox}>
                <span className={styles.statBoxNum}>{fmt(salary.stats.min)}</span>
                <span className={styles.statBoxLabel}>최저</span>
              </div>
              <div className={styles.statBox}>
                <span className={styles.statBoxNum}>{fmt(salary.stats.median)}</span>
                <span className={styles.statBoxLabel}>중간값</span>
              </div>
              <div className={styles.statBox}>
                <span className={styles.statBoxNum}>{fmt(salary.stats.avg)}</span>
                <span className={styles.statBoxLabel}>평균</span>
              </div>
              <div className={styles.statBox}>
                <span className={styles.statBoxNum}>{fmt(salary.stats.max)}</span>
                <span className={styles.statBoxLabel}>최고</span>
              </div>
            </div>
            <div className={styles.salaryFooter}>
              {salary.skill ? `"${salary.skill}" 요구 공고 ` : '전체 공고 '}
              <strong>{salary.count}</strong>건 기준 분포
            </div>
            <div className={styles.bucketChart}>
              {salary.buckets.map((b, i) => (
                <div key={i} className={styles.bucketCol}>
                  <div className={styles.bucketBarWrap}>
                    <span className={styles.bucketCount}>{b.count}</span>
                    <div
                      className={styles.bucketBar}
                      style={{ height: `${(b.count / maxBucket) * 100}%` }}
                    />
                  </div>
                  <span className={styles.bucketLabel}>{fmt(b.range_min)}~{fmt(b.range_max)}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
