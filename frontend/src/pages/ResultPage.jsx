import { useState, useEffect } from 'react'
import styles from './ResultPage.module.css'

export default function ResultPage({ result, onReset }) {
  const [activeTab, setActiveTab] = useState(0)
  const [histories, setHistories] = useState([])
  const [historiesLoading, setHistoriesLoading] = useState(false)
  
  const { results, learning_priority, summary } = result

  const topJob   = results[0]
  const avgScore = summary.avg_fit_score

  // 분석 이력 탭 선택 시 이력 로드
  useEffect(() => {
    if (activeTab === 3) {
      setHistoriesLoading(true)
      fetch('/api/analyze/history')
        .then(res => {
          if (!res.ok) throw new Error('이력 로드 실패')
          return res.json()
        })
        .then(data => {
          setHistories(data || [])
        })
        .catch(err => console.error('Failed to load histories:', err))
        .finally(() => setHistoriesLoading(false))
    }
  }, [activeTab])

  return (
    <div className={styles.page}>
      <div className={styles.blob1} />
      <div className={styles.blob2} />

      <div className={styles.container}>
        {/* 헤더 */}
        <div className={styles.header}>
          <button className={styles.backBtn} onClick={onReset}>← 다시 분석</button>
          <h2 className={styles.title}>분석 결과</h2>
          <p className={styles.sub}>{summary.total_jobs}개 채용공고 분석 완료</p>
        </div>

        {/* 요약 카드 */}
        <div className={styles.summaryGrid}>
          <div className={styles.summaryCard}>
            <div className={styles.scoreRing}>
              <svg viewBox="0 0 80 80" className={styles.ringsvg}>
                <circle cx="40" cy="40" r="32" className={styles.ringBg} />
                <circle
                  cx="40" cy="40" r="32"
                  className={styles.ringFill}
                  strokeDasharray={`${avgScore * 2.01} 201`}
                />
              </svg>
              <span className={styles.scoreNum}>{avgScore}%</span>
            </div>
            <div className={styles.scoreLabel}>평균 적합도</div>
          </div>

          <div className={styles.summaryCard}>
            <div className={styles.statNum}>{summary.analyzed_jobs}</div>
            <div className={styles.statLabel}>비교된 공고</div>
          </div>

          <div className={styles.summaryCard}>
            <div className={styles.statNum}>{learning_priority.length}</div>
            <div className={styles.statLabel}>보완 필요 스킬</div>
          </div>

          {topJob && (
            <div className={`${styles.summaryCard} ${styles.topJobCard}`}>
              <div className={styles.topJobScore}>{topJob.fit_score}%</div>
              <div className={styles.topJobTitle}>{topJob.job.title}</div>
              <div className={styles.topJobCo}>{topJob.job.company}</div>
            </div>
          )}
        </div>

        {/* 탭 */}
        <div className={styles.tabs}>
          {['채용공고 매칭', '스킬 갭 & 피드백', '학습 우선순위', '분석 이력'].map((t, i) => (
            <button
              key={t}
              className={`${styles.tab} ${activeTab === i ? styles.tabActive : ''}`}
              onClick={() => setActiveTab(i)}
            >
              {t}
            </button>
          ))}
        </div>

        {/* 탭 0: 채용공고 */}
        {activeTab === 0 && (
          <div className={styles.tabContent}>
            {results.map((r, idx) => (
              <div key={idx} className={styles.jobCard}>
                <div className={styles.jobTop}>
                  <div>
                    <div className={styles.jobTitle}>{r.job.title}</div>
                    <div className={styles.jobCo}>{r.job.company} · {r.job.location}</div>
                  </div>
                  <div className={`${styles.scoreBadge} ${
                    r.fit_score >= 60 ? styles.scoreHigh :
                    r.fit_score >= 30 ? styles.scoreMid : styles.scoreLow
                  }`}>
                    {r.fit_score}%
                  </div>
                </div>

                {/* 스킬 바 */}
                <div className={styles.barWrap}>
                  <div
                    className={styles.bar}
                    style={{ width: `${r.fit_score}%` }}
                  />
                </div>

                {/* 세부 매칭도 점수 */}
                {r.match_details && (
                  <div className={styles.matchDetails}>
                    <span className={styles.detailTag}>기술 적합도: {r.match_details.skills}%</span>
                    {r.match_details.job_title !== 100 && (
                      <span className={styles.detailTag}>직무 매칭: {r.match_details.job_title}%</span>
                    )}
                    {r.match_details.category !== 100 && (
                      <span className={styles.detailTag}>분야 매칭: {r.match_details.category}%</span>
                    )}
                    {r.match_details.salary !== 100 && (
                      <span className={styles.detailTag}>연봉 적합: {r.match_details.salary}%</span>
                    )}
                    {r.match_details.location !== 100 && (
                      <span className={styles.detailTag}>근무지 매칭: {r.match_details.location}%</span>
                    )}
                  </div>
                )}

                {/* 스킬 태그 */}
                <div className={styles.skillRow}>
                  {r.matched_skills.map(s => (
                    <span key={s} className={styles.skillMatch}>{s}</span>
                  ))}
                  {r.missing_skills.slice(0, 5).map(s => (
                    <span key={s} className={styles.skillMiss}>{s}</span>
                  ))}
                  {r.missing_skills.length > 5 && (
                    <span className={styles.skillMore}>+{r.missing_skills.length - 5}</span>
                  )}
                </div>

                {/* 메타 */}
                <div className={styles.jobMeta}>
                  {r.job.salary && <span>{r.job.salary}</span>}
                  {r.job.employment_type && <span>{r.job.employment_type}</span>}
                  {r.job.apply_url && (
                    <a href={r.job.apply_url} target="_blank" rel="noreferrer" className={styles.applyLink}>
                      지원하기 →
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 탭 1: 스킬 갭 & 피드백 */}
        {activeTab === 1 && (
          <div className={styles.tabContent}>
            {results.map((r, idx) => (
              r.missing_skills.length > 0 && (
                <div key={idx} className={`${styles.feedCard} ${result.resume_used ? styles.feedCardResume : ''}`}>
                  <div className={styles.feedHeader}>
                    <div className={styles.feedTitleWrap}>
                      <span className={styles.feedTitle}>{r.job.title}</span>
                      {result.resume_used && (
                        <span className={styles.resumeCoachBadge}>✨ Claude 이력서 1:1 맞춤 피드백</span>
                      )}
                    </div>
                    <span className={styles.feedScore}>{r.fit_score}% 매칭</span>
                  </div>

                  <div className={styles.gapSection}>
                    <div className={styles.gapLabel}>부족한 스킬</div>
                    <div className={styles.gapSkills}>
                      {r.missing_skills.map(s => (
                        <span key={s} className={styles.gapSkill}>{s}</span>
                      ))}
                    </div>
                  </div>

                  <div className={styles.feedList}>
                    {r.feedback.map((f, i) => (
                      <div key={i} className={styles.feedItem}>
                        <span className={styles.feedDot} />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        )}

        {/* 탭 2: 학습 우선순위 */}
        {activeTab === 2 && (
          <div className={styles.tabContent}>
            <p className={styles.priorityDesc}>
              채용공고에서 자주 요구되는 순으로 정렬된 보완 필요 스킬이에요.
            </p>
            {learning_priority.map((item, idx) => (
              <div key={idx} className={styles.priorityItem}>
                <div className={styles.priorityRank}>#{idx + 1}</div>
                <div className={styles.priorityInfo}>
                  <div className={styles.prioritySkill}>{item.skill}</div>
                  <div className={styles.priorityBar}>
                    <div
                      className={styles.priorityFill}
                      style={{
                        width: `${(item.demand_count / learning_priority[0].demand_count) * 100}%`,
                        background: idx === 0 ? '#f76a8a' : idx === 1 ? '#7c6af7' : '#4ade80'
                      }}
                    />
                  </div>
                </div>
                <div className={styles.priorityCount}>{item.demand_count}개 공고</div>
              </div>
            ))}
          </div>
        )}

        {/* 탭 3: 분석 이력 */}
        {activeTab === 3 && (
          <div className={styles.tabContent}>
            <p className={styles.priorityDesc}>
              최근에 수행한 매칭 분석 실행 이력입니다.
            </p>
            {historiesLoading ? (
              <div className={styles.loadingHistory}>이력을 불러오는 중...</div>
            ) : histories.length === 0 ? (
              <div className={styles.emptyHistory}>저장된 매칭 이력이 없습니다.</div>
            ) : (
              histories.map((h) => (
                <div key={h.id} className={styles.historyCard}>
                  <div className={styles.historyHeader}>
                    <span className={styles.historyTime}>
                      {new Date(h.run_at).toLocaleString('ko-KR')}
                    </span>
                    <span className={styles.historyScore}>
                      평균 적합도: <strong>{h.avg_fit_score}%</strong>
                    </span>
                  </div>

                  <div className={styles.historyStats}>
                    <span>분석 완료 공고: {h.analyzed_jobs} / {h.total_jobs}개</span>
                  </div>

                  <div className={styles.historySnapshot}>
                    <div className={styles.snapshotLabel}>보유 스킬 스냅샷</div>
                    <div className={styles.snapshotTags}>
                      {h.skills_snapshot && h.skills_snapshot.map(s => (
                        <span key={s} className={styles.snapshotTag}>{s}</span>
                      ))}
                    </div>
                  </div>

                  {h.preferences_snapshot && (Object.keys(h.preferences_snapshot).length > 0) && (
                    <div className={styles.historySnapshot}>
                      <div className={styles.snapshotLabel}>선호 조건 스냅샷</div>
                      <div className={styles.snapshotPrefs}>
                        {h.preferences_snapshot.job_title && <span>직무: {h.preferences_snapshot.job_title}</span>}
                        {h.preferences_snapshot.category && <span>분야: {h.preferences_snapshot.category}</span>}
                        {h.preferences_snapshot.salary && <span>연봉: {h.preferences_snapshot.salary}</span>}
                        {h.preferences_snapshot.location && <span>근무지: {h.preferences_snapshot.location}</span>}
                      </div>
                    </div>
                  )}

                  {h.top_matches && h.top_matches.length > 0 && (
                    <div className={styles.historyTopMatches}>
                      <div className={styles.snapshotLabel}>주요 매칭 채용공고</div>
                      <div className={styles.topMatchesList}>
                        {h.top_matches.map((m, mIdx) => (
                          <div key={mIdx} className={styles.topMatchItem}>
                            <span className={styles.topMatchName}>
                              {m.job_title} ({m.company})
                            </span>
                            <span className={styles.topMatchScore}>
                              {m.fit_score}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

