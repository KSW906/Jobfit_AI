import { useState, useEffect } from 'react'
import styles from './ResultPage.module.css'

export default function ResultPage({ result, onReset }) {
  const [activeTab, setActiveTab] = useState(0)
  const [histories, setHistories] = useState([])
  const [historiesLoading, setHistoriesLoading] = useState(false)

  // 이력서 비교 관련 상태
  const [compList, setCompList] = useState([])
  const [compListLoading, setCompListLoading] = useState(false)
  const [selectedCompId, setSelectedCompId] = useState(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareResult, setCompareResult] = useState(null)
  const [compareError, setCompareError] = useState(null)

  // 앙상블 분석 관련 상태
  const [ensembleJobIdx, setEnsembleJobIdx] = useState(0)
  const [ensembleLoading, setEnsembleLoading] = useState(false)
  const [ensembleResult, setEnsembleResult] = useState(null)
  const [ensembleError, setEnsembleError] = useState(null)

  const { results, learning_priority, summary } = result

  const topJob   = results[0]
  const avgScore = summary.avg_fit_score

  // 분석 이력 탭 선택 시 이력 로드
  useEffect(() => {
    if (activeTab === 3) {
      setHistoriesLoading(true)
      const token = localStorage.getItem('auth_token')
      fetch('/api/analyze/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => {
          if (!res.ok) throw new Error('이력 로드 실패')
          return res.json()
        })
        .then(data => setHistories(data || []))
        .catch(err => console.error('Failed to load histories:', err))
        .finally(() => setHistoriesLoading(false))
    }

    // 이력서 비교 탭 선택 시 비교 이력서 목록 로드
    if (activeTab === 4) {
      setCompListLoading(true)
      const token = localStorage.getItem('auth_token')
      fetch('/api/comparison-resumes', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => {
          if (!res.ok) throw new Error('비교 이력서 목록 로드 실패')
          return res.json()
        })
        .then(data => {
          setCompList(data || [])
          if (data && data.length > 0) setSelectedCompId(data[0].id)
        })
        .catch(err => console.error('Failed to load comparison resumes:', err))
        .finally(() => setCompListLoading(false))
    }
  }, [activeTab])

  const handleCompare = async () => {
    if (!selectedCompId) return
    setCompareLoading(true)
    setCompareResult(null)
    setCompareError(null)
    const token = localStorage.getItem('auth_token')
    try {
      const res = await fetch('/api/compare-resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ comparison_resume_id: selectedCompId })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '비교 분석 실패')
      setCompareResult(data)
    } catch (e) {
      setCompareError(e.message)
    } finally {
      setCompareLoading(false)
    }
  }

  const handleEnsemble = async () => {
    const job = results[ensembleJobIdx]
    if (!job) return
    setEnsembleLoading(true)
    setEnsembleResult(null)
    setEnsembleError(null)
    const token = localStorage.getItem('auth_token')
    try {
      const res = await fetch('/api/analyze/ensemble', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          job_title: job.job.title,
          job_description: job.job.description || job.job.title,
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '앙상블 분석 실패')
      setEnsembleResult(data)
    } catch (e) {
      setEnsembleError(e.message)
    } finally {
      setEnsembleLoading(false)
    }
  }

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
          {['채용공고 매칭', '스킬 갭 & 피드백', '학습 우선순위', '분석 이력', '이력서 비교', '🤖 AI 앙상블'].map((t, i) => (
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
                    {Object.entries(r.match_details).map(([key, val]) => (
                      <div key={key} className={styles.matchDetailItem}>
                        <span className={styles.matchDetailLabel}>{
                          { skills: '스킬', job_title: '직무명', category: '카테고리', salary: '연봉', location: '근무지' }[key] || key
                        }</span>
                        <span className={styles.matchDetailVal}>{val}%</span>
                      </div>
                    ))}
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
                </div>

                {r.job.apply_url && (
                  <a href={r.job.apply_url} target="_blank" rel="noreferrer" className={styles.applyLink}>
                    지원하기 →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 탭 1: 스킬 갭 & 피드백 */}
        {activeTab === 1 && (
          <div className={styles.tabContent}>
            {results.slice(0, 3).map((r, idx) => (
              r.missing_skills.length > 0 && (
                <div key={idx} className={styles.feedCard}>
                  <div className={styles.feedJobTitle}>{r.job.title}</div>
                  <div className={styles.missingSkills}>
                    {r.missing_skills.map(s => (
                      <span key={s} className={styles.missingTag}>{s}</span>
                    ))}
                  </div>
                  {r.feedback && r.feedback.length > 0 && (
                    <ul className={styles.feedList}>
                      {r.feedback.map((f, fi) => (
                        <li key={fi} className={styles.feedItem}>{f}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            ))}
          </div>
        )}

        {/* 탭 2: 학습 우선순위 */}
        {activeTab === 2 && (
          <div className={styles.tabContent}>
            <p className={styles.priorityDesc}>
              🎯 채용 시장에서의 수요도(공고 등록 수)가 높고 현재 내 기술 스택에는 없는 스킬들을 우선순위대로 선별했습니다.
            </p>
            <div className={styles.prioList}>
              {(() => {
                const maxDemand = Math.max(...learning_priority.map(item => item.demand_count), 1);
                return learning_priority.map((item, i) => {
                  const rankEmoji = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : null;
                  const ratio = item.demand_count / maxDemand;
                  const isHot = ratio >= 0.7;
                  const isWarm = ratio >= 0.4 && ratio < 0.7;

                  return (
                    <div key={i} className={styles.priorityCard}>
                      <div className={styles.priorityHeader}>
                        <div className={`${styles.priorityRankBadge} ${
                          i === 0 ? styles.rankFirst :
                          i === 1 ? styles.rankSecond :
                          i === 2 ? styles.rankThird : styles.rankNormal
                        }`}>
                          {rankEmoji || `#${i + 1}`}
                        </div>
                        <div className={styles.priorityTitleWrap}>
                          <div className={styles.priorityNameRow}>
                            <h4 className={styles.prioritySkillName}>{item.skill}</h4>
                            {isHot ? (
                              <span className={`${styles.prioLevelBadge} ${styles.prioLevelHot}`}>🚨 급상승 스택</span>
                            ) : isWarm ? (
                              <span className={`${styles.prioLevelBadge} ${styles.prioLevelWarm}`}>🔥 주요 추천</span>
                            ) : (
                              <span className={`${styles.prioLevelBadge} ${styles.prioLevelNormal}`}>👍 꾸준한 수요</span>
                            )}
                          </div>
                          <span className={styles.priorityMarketDemand}>
                            시장 수요: <strong>{item.demand_count}건</strong>의 채용 공고에서 요구됨
                          </span>
                        </div>
                      </div>

                      {/* 수요 지표 바 */}
                      <div className={styles.priorityProgressBarWrap}>
                        <div className={styles.priorityProgressBarLabel}>시장 스킬 점유율</div>
                        <div className={styles.priorityProgressBar}>
                          <div
                            className={styles.priorityProgressBarFill}
                            style={{ width: `${ratio * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* 학습 가이드 안내 문구 & 원클릭 구글 검색 로드맵 */}
                      <div className={styles.priorityFooter}>
                        <p className={styles.priorityGuideText}>
                          이 기술 스택은 현재 채용 시장에서 매우 수요가 많습니다. 기초 개념 습득과 포트폴리오 적용을 시작해 보세요.
                        </p>

                        {item.resources && item.resources.length > 0 && (
                          <div className={styles.resourceSection}>
                            <h5 className={styles.resourceSecTitle}>추천 학습 콘텐츠</h5>
                            <div className={styles.resourceGrid}>
                              {item.resources.map((res, idx) => {
                                let icon = '📚';
                                if (res.type === 'youtube') icon = '🎬';
                                if (res.type === 'course') icon = '🎓';
                                return (
                                  <a
                                    key={idx}
                                    href={res.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className={`${styles.resourceCard} ${
                                      res.type === 'youtube' ? styles.resYoutube :
                                      res.type === 'course' ? styles.resCourse : styles.resDoc
                                    }`}
                                  >
                                    <span className={styles.resIcon}>{icon}</span>
                                    <div className={styles.resInfo}>
                                      <span className={styles.resTypeName}>
                                        {res.type === 'doc' ? '공식 문서' :
                                         res.type === 'youtube' ? 'YouTube' : '교육 강좌'}
                                      </span>
                                      <span className={styles.resName}>{res.name}</span>
                                    </div>
                                    <span className={styles.resArrow}>↗</span>
                                  </a>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        <a
                          href={`https://www.google.com/search?q=${encodeURIComponent(item.skill + ' 공식문서 튜토리얼')}`}
                          target="_blank"
                          rel="noreferrer"
                          className={styles.prioSearchLink}
                        >
                          🔍 Google에서 관련 강좌 더 보기 ↗
                        </a>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        )}

        {/* 탭 3: 분석 이력 */}
        {activeTab === 3 && (
          <div className={styles.tabContent}>
            {historiesLoading ? (
              <p className={styles.loading}>이력 불러오는 중...</p>
            ) : histories.length === 0 ? (
              <p className={styles.empty}>저장된 분석 이력이 없습니다.</p>
            ) : (
              histories.map((h, i) => (
                <div key={i} className={styles.historyCard}>
                  <div className={styles.historyDate}>{h.run_at_date} {h.run_at_time}</div>
                  <div className={styles.historyScore}>평균 적합도: <strong>{h.avg_fit_score}%</strong></div>
                  <div className={styles.historyJobs}>분석 공고: {h.analyzed_jobs}건</div>
                  {h.top_matches && h.top_matches.slice(0, 3).map((m, mi) => (
                    <div key={mi} className={styles.historyMatch}>
                      {m.job_title} — {m.company} ({m.fit_score}%)
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        )}

        {/* 탭 4: 이력서 비교 */}
        {activeTab === 4 && (
          <div className={styles.tabContent}>
            <p className={styles.prioDesc}>
              관리자가 등록한 합격자/경쟁자 이력서와 내 이력서를 AI가 심층 비교합니다.
            </p>

            {compListLoading ? (
              <p className={styles.loading}>비교 이력서 목록 불러오는 중...</p>
            ) : compList.length === 0 ? (
              <p className={styles.empty}>등록된 비교 이력서가 없습니다. 관리자에게 문의해주세요.</p>
            ) : (
              <>
                {/* 비교 이력서 선택 */}
                <div className={styles.compSelectWrap}>
                  <label className={styles.compSelectLabel}>비교할 이력서 선택</label>
                  <div className={styles.compCards}>
                    {compList.map(item => (
                      <div
                        key={item.id}
                        className={`${styles.compCard} ${selectedCompId === item.id ? styles.compCardActive : ''}`}
                        onClick={() => {
                          setSelectedCompId(item.id)
                          setCompareResult(null)
                          setCompareError(null)
                        }}
                      >
                        <div className={styles.compCardLabel}>{item.label}</div>
                        <div className={styles.compCardName}>{item.target_name}</div>
                        {item.skills.length > 0 && (
                          <div className={styles.compCardSkills}>
                            {item.skills.slice(0, 4).map(s => (
                              <span key={s} className={styles.compSkillTag}>{s}</span>
                            ))}
                            {item.skills.length > 4 && (
                              <span className={styles.compSkillMore}>+{item.skills.length - 4}</span>
                            )}
                          </div>
                        )}
                        <div className={styles.compCardPreview}>{item.preview}</div>
                      </div>
                    ))}
                  </div>

                  <button
                    className={styles.compareBtn}
                    onClick={handleCompare}
                    disabled={!selectedCompId || compareLoading}
                  >
                    {compareLoading ? 'AI 비교 분석 중...' : '🔍 AI 비교 분석 시작'}
                  </button>
                </div>

                {/* 에러 */}
                {compareError && (
                  <div className={styles.compareError}>{compareError}</div>
                )}

                {/* 비교 결과 */}
                {compareResult && (
                  <div className={styles.compareResultWrap}>
                    <div className={styles.compareResultTitle}>
                      📊 비교 결과: <strong>{compareResult.comparison_label}</strong>와의 분석
                    </div>

                    <div className={styles.compareAssessment}>
                      {compareResult.overall_assessment}
                    </div>

                    <div className={styles.compareGrid}>
                      {/* 강점 */}
                      <div className={styles.compareSection}>
                        <div className={`${styles.compareSectionTitle} ${styles.strengthTitle}`}>
                          ✅ 나의 강점
                        </div>
                        <ul className={styles.compareList}>
                          {compareResult.strengths?.map((s, i) => (
                            <li key={i} className={styles.compareListItem}>{s}</li>
                          ))}
                        </ul>
                      </div>

                      {/* 약점 */}
                      <div className={styles.compareSection}>
                        <div className={`${styles.compareSectionTitle} ${styles.weaknessTitle}`}>
                          ⚠️ 보완할 점
                        </div>
                        <ul className={styles.compareList}>
                          {compareResult.weaknesses?.map((w, i) => (
                            <li key={i} className={styles.compareListItem}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* 스킬 갭 */}
                    {compareResult.skill_gap?.length > 0 && (
                      <div className={styles.compareSection}>
                        <div className={`${styles.compareSectionTitle} ${styles.gapTitle}`}>
                          🎯 부족한 핵심 역량
                        </div>
                        <div className={styles.skillGapTags}>
                          {compareResult.skill_gap.map((s, i) => (
                            <span key={i} className={styles.skillGapTag}>{s}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 조언 */}
                    <div className={styles.compareSection}>
                      <div className={`${styles.compareSectionTitle} ${styles.adviceTitle}`}>
                        💡 개선 조언
                      </div>
                      <ol className={styles.adviceList}>
                        {compareResult.advice?.map((a, i) => (
                          <li key={i} className={styles.adviceItem}>{a}</li>
                        ))}
                      </ol>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* 탭 5: AI 앙상블 */}
        {activeTab === 5 && (
          <div className={styles.tabContent}>
            <p className={styles.prioDesc}>
              Claude · Gemini · GPT-4o가 동시에 분석하고, 앙상블로 점수를 종합합니다. AI 간 의견이 다를 경우 불일치 알림이 표시됩니다.
            </p>

            <div className={styles.compSelectWrap}>
              <label className={styles.compSelectLabel}>분석할 공고 선택</label>
              <select
                className={styles.ensembleSelect}
                value={ensembleJobIdx}
                onChange={e => { setEnsembleJobIdx(Number(e.target.value)); setEnsembleResult(null); setEnsembleError(null); }}
              >
                {results.map((r, i) => (
                  <option key={i} value={i}>{r.job.title} — {r.job.company} ({r.fit_score}%)</option>
                ))}
              </select>

              <button className={styles.compareBtn} onClick={handleEnsemble} disabled={ensembleLoading}>
                {ensembleLoading ? '3개 AI 분석 중...' : '🤖 앙상블 분석 시작'}
              </button>
            </div>

            {ensembleError && <div className={styles.compareError}>{ensembleError}</div>}

            {ensembleResult && (
              <div className={styles.compareResultWrap}>

                <div className={styles.ensembleScoreRow}>
                  <div className={styles.ensembleScoreBig}>
                    <div className={styles.ensembleScoreNum}>{ensembleResult.ensemble_score}%</div>
                    <div className={styles.ensembleScoreLabel}>앙상블 종합 점수</div>
                  </div>
                  <div className={styles.ensembleModelScores}>
                    {Object.entries(ensembleResult.model_scores || {}).map(([model, score]) => (
                      <div key={model} className={styles.ensembleModelItem}>
                        <div className={styles.ensembleModelName}>{model === 'claude' ? 'Claude' : model === 'gemini' ? 'Gemini' : 'GPT-4o'}</div>
                        <div className={styles.ensembleModelScore}>{score}%</div>
                        <div className={styles.ensembleModelBar}>
                          <div className={styles.ensembleModelBarFill} style={{ width: `${score}%`, background: model === 'claude' ? '#7c3aed' : model === 'gemini' ? '#0f9e7b' : '#0ea5e9' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  {ensembleResult.disagreement && (
                    <div className={styles.ensembleDisagreement}>
                      ⚠️ AI 간 점수 편차 {ensembleResult.score_variance}점 — 결과를 참고용으로만 활용하세요
                    </div>
                  )}
                </div>

                {ensembleResult.skill_gap && (
                  <div className={styles.compareSection}>
                    <div className={`${styles.compareSectionTitle} ${styles.gapTitle}`}>🎯 스킬 갭 분석 (신뢰도별)</div>
                    {ensembleResult.skill_gap.high?.length > 0 && (
                      <div className={styles.ensembleGapGroup}>
                        <span className={styles.ensembleGapLabel}>🔴 전체 AI 동의 (반드시 보완)</span>
                        <div className={styles.skillGapTags}>
                          {ensembleResult.skill_gap.high.map(s => <span key={s} className={styles.skillGapTag}>{s}</span>)}
                        </div>
                      </div>
                    )}
                    {ensembleResult.skill_gap.medium?.length > 0 && (
                      <div className={styles.ensembleGapGroup}>
                        <span className={styles.ensembleGapLabel}>🟡 과반수 동의 (권장 보완)</span>
                        <div className={styles.skillGapTags}>
                          {ensembleResult.skill_gap.medium.map(s => <span key={s} className={`${styles.skillGapTag} ${styles.skillGapMedium}`}>{s}</span>)}
                        </div>
                      </div>
                    )}
                    {ensembleResult.skill_gap.matched?.length > 0 && (
                      <div className={styles.ensembleGapGroup}>
                        <span className={styles.ensembleGapLabel}>🟢 보유 확인 스킬</span>
                        <div className={styles.skillGapTags}>
                          {ensembleResult.skill_gap.matched.map(s => <span key={s} className={`${styles.skillGapTag} ${styles.skillGapMatched}`}>{s}</span>)}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className={styles.compareGrid}>
                  <div className={styles.compareSection}>
                    <div className={`${styles.compareSectionTitle} ${styles.strengthTitle}`}>✅ 공통 강점</div>
                    <ul className={styles.compareList}>
                      {ensembleResult.representative_strengths?.map((s, i) => (
                        <li key={i} className={styles.compareListItem}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div className={styles.compareSection}>
                    <div className={`${styles.compareSectionTitle} ${styles.adviceTitle}`}>💡 공통 개선 조언</div>
                    <ul className={styles.compareList}>
                      {ensembleResult.representative_feedback?.map((f, i) => (
                        <li key={i} className={styles.compareListItem}>{f}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className={styles.compareSection}>
                  <div className={styles.compareSectionTitle} style={{color:'var(--color-text-secondary)'}}>📋 AI별 원본 의견</div>
                  <div className={styles.ensembleRawGrid}>
                    {Object.entries(ensembleResult.strengths_by_model || {}).map(([model, items]) => (
                      <div key={model} className={styles.ensembleRawCard}>
                        <div className={styles.ensembleRawTitle} style={{color: model === 'claude' ? '#c4b5fd' : model === 'gemini' ? '#6ee7b7' : '#93c5fd'}}>
                          {model === 'claude' ? '🟣 Claude' : model === 'gemini' ? '🟢 Gemini' : '🔵 GPT-4o'}
                        </div>
                        <div className={styles.ensembleRawSection}>강점</div>
                        {items?.map((s, i) => <div key={i} className={styles.ensembleRawItem}>{s}</div>)}
                        <div className={styles.ensembleRawSection}>조언</div>
                        {(ensembleResult.feedback_by_model?.[model] || []).map((f, i) => <div key={i} className={styles.ensembleRawItem}>{f}</div>)}
                      </div>
                    ))}
                  </div>
                </div>

                <div className={styles.ensembleMeta}>
                  분석 소요: {ensembleResult.elapsed_sec}초 · 성공 모델: {ensembleResult.available_models?.join(', ')}
                  {ensembleResult.failed_models?.length > 0 && ` · 실패: ${ensembleResult.failed_models.join(', ')}`}
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
