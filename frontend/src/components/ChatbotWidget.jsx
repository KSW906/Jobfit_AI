import { useState, useEffect, useRef } from 'react'
import styles from './ChatbotWidget.module.css'

export default function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeTab, setActiveTab] = useState('chat') // 'chat' | 'interview'
  const [loading, setLoading] = useState(false)
  
  // 일반 챗 대화 상태
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 저는 AI 커리어 코치입니다. 이력서 첨삭, 기술 스택 연동 고민, 또는 가고 싶은 기업 면접 전략에 대해 무엇이든 편하게 여쭤보세요! 💬' }
  ])

  // 면접 연습 상태
  const [interviewSession, setInterviewSession] = useState(null)
  const [interviewAnswer, setInterviewAnswer] = useState('')
  const [interviewHistory, setInterviewHistory] = useState([])
  const [interviewCompleted, setInterviewCompleted] = useState(false)

  // ⏱️ 타임어택(시간제한) 모드 상태 및 Ref
  const [timeLeft, setTimeLeft] = useState(60)
  const timerRef = useRef(null)
  
  const answerRef = useRef('')
  const sessionRef = useRef(null)
  const loadingRef = useRef(false)

  const messagesEndRef = useRef(null)

  // 최신 상태값 보전을 위한 Ref 갱신 Effect
  useEffect(() => {
    answerRef.current = interviewAnswer
  }, [interviewAnswer])

  useEffect(() => {
    sessionRef.current = interviewSession
  }, [interviewSession])

  useEffect(() => {
    loadingRef.current = loading
  }, [loading])

  // 메시지 전송 시 자동 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatMessages, interviewHistory, isOpen, loading])

  // 창 닫힐 때 확대 모드 초기화
  useEffect(() => {
    if (!isOpen) {
      setIsExpanded(false)
    }
  }, [isOpen])

  // ⏱️ 타임어택 60초 타이머 로직
  useEffect(() => {
    // 기존 타이머 클리어
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    if (isOpen && activeTab === 'interview' && interviewSession?.interview_mode === 'timer' && !interviewCompleted && !loading) {
      const lastMsg = interviewHistory[interviewHistory.length - 1]
      // 마지막 메시지가 AI의 질문(Q1. Q2. Q3.)일 때 타이머 구동
      if (lastMsg && lastMsg.role === 'assistant') {
        setTimeLeft(60)
        
        timerRef.current = setInterval(() => {
          setTimeLeft(prev => {
            if (prev <= 1) {
              clearInterval(timerRef.current)
              timerRef.current = null
              // 시간 초과 자동 제출 호출
              handleTimeoutSubmit()
              return 0
            }
            return prev - 1
          })
        }, 1000)
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [interviewHistory, isOpen, activeTab, interviewSession, interviewCompleted, loading])

  const handleTimeoutSubmit = () => {
    if (loadingRef.current || !sessionRef.current) return
    const ans = answerRef.current.trim()
    const finalAnswer = ans || "(제한시간 내에 답변을 제출하지 못했습니다.)"
    submitAnswer(finalAnswer)
  }

  // 공고 카드에서 "면접 연습하기" 클릭 시 트리거되는 커스텀 이벤트 리스너 연동
  useEffect(() => {
    const handleStartInterview = async (e) => {
      const { job, interview_mode } = e.detail
      if (!job || !job.id) return

      setIsOpen(true)
      setActiveTab('interview')
      setLoading(true)
      setInterviewCompleted(false)

      const modeNames = {
        stress: '🌶️ 압박 면접 모드',
        diagnostic: '🔍 기술 진단 모드',
        friendly: '🌸 친절한 모의 훈련',
        timer: '⏱️ 타임어택 모드'
      }
      const modeName = modeNames[interview_mode] || '기술 진단 모드'

      setInterviewHistory([
        { role: 'system', content: `🎯 [${job.company || '익명 기업'}] ${job.title} 공고 모의 면접을 시작합니다. (${modeName})` }
      ])
      setInterviewSession(null)

      try {
        const token = localStorage.getItem('auth_token')
        const res = await fetch('/api/chat/interview/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ 
            job_posting_id: job.id,
            interview_mode: interview_mode || 'diagnostic'
          })
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || '면접 예상질문 생성 실패')

        setInterviewSession(data)
        setInterviewHistory(prev => [
          ...prev,
          { role: 'assistant', content: `Q1. ${data.question}` }
        ])
      } catch (err) {
        console.error(err)
        setInterviewHistory(prev => [
          ...prev,
          { role: 'assistant', content: `❌ 면접 세션을 시작하지 못했습니다: ${err.message}` }
        ])
      } finally {
        setLoading(false)
      }
    }

    window.addEventListener('start-interview', handleStartInterview)
    return () => window.removeEventListener('start-interview', handleStartInterview)
  }, [])

  // 일반 채팅 메시지 발송
  const handleSendChatMessage = async (e) => {
    e.preventDefault()
    const msg = chatInput.trim()
    if (!msg || loading) return

    const newMessages = [...chatMessages, { role: 'user', content: msg }]
    setChatMessages(newMessages)
    setChatInput('')
    setLoading(true)

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: msg,
          history: chatMessages.filter(m => m.role !== 'system')
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '답변 로드 실패')

      setChatMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      console.error(err)
      setChatMessages(prev => [...prev, { role: 'system', content: `❌ 에러: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  // 면접 답변 공통 제출 처리
  const submitAnswer = async (answerText) => {
    const ans = answerText.trim()
    if (!ans || !sessionRef.current || loadingRef.current) return

    setInterviewHistory(prev => [...prev, { role: 'user', content: ans }])
    setInterviewAnswer('')
    setLoading(true)

    // 타이머 즉시 클리어
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch('/api/chat/interview/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: sessionRef.current.session_id,
          answer: ans
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || '답변 평가 실패')

      // 피드백 말풍선 주입
      setInterviewHistory(prev => [
        ...prev,
        {
          role: 'feedback',
          feedback: data.feedback // score, analysis, model_answer 가 포함됨
        }
      ])

      if (data.is_completed) {
        setInterviewCompleted(true)
        setInterviewHistory(prev => [
          ...prev,
          { role: 'system', content: '🎉 모의 면접 질문이 모두 완료되었습니다! 고생하셨습니다. 답변 피드백을 검토하여 부족한 개념을 보충해 보세요.' }
        ])
      } else {
        setInterviewHistory(prev => [
          ...prev,
          { role: 'assistant', content: `Q${data.current_index + 1}. ${data.next_question}` }
        ])
      }
    } catch (err) {
      console.error(err)
      setInterviewHistory(prev => [
        ...prev,
        { role: 'system', content: `❌ 피드백 채점 에러: ${err.message}` }
      ])
    } finally {
      setLoading(false)
    }
  }

  // 면접 답변 제출 (폼 서브밋 핸들러)
  const handleSubmitInterviewAnswer = (e) => {
    if (e) e.preventDefault()
    submitAnswer(interviewAnswer)
  }

  return (
    <div className={styles.chatbotWrapper}>
      {/* 1. 플로팅 챗봇 토글 버튼 */}
      <button 
        className={`${styles.floatingButton} ${isOpen ? styles.floatingActive : ''}`} 
        onClick={() => setIsOpen(!isOpen)}
        title="AI 커리어 코칭 & 모의면접 비서"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* 2. 챗봇 팝업 윈도우 */}
      {isOpen && (
        <div className={`${styles.chatWindow} ${isExpanded ? styles.expanded : ''}`}>
          {/* 헤더 */}
          <div className={styles.chatHeader}>
            <div className={styles.headerTitleWrap}>
              <div className={styles.headerTitleLeft}>
                <span className={styles.headerStatus}>●</span>
                <h4 className={styles.headerTitle}>AI 커리어 매칭 비서</h4>
              </div>
              <button 
                type="button"
                className={styles.expandBtn}
                onClick={() => setIsExpanded(!isExpanded)}
                title={isExpanded ? "창 축소" : "창 확대 (넓은 화면)"}
              >
                {isExpanded ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"/>
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
                  </svg>
                )}
              </button>
            </div>
            <div className={styles.chatTabs}>
              <button 
                className={`${styles.tabBtn} ${activeTab === 'chat' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('chat')}
              >
                1:1 상담
              </button>
              <button 
                className={`${styles.tabBtn} ${activeTab === 'interview' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('interview')}
              >
                모의 면접
              </button>
            </div>
          </div>

          {/* 콘텐츠 바디 */}
          <div className={styles.chatBody}>
            {activeTab === 'chat' ? (
              /* 일반 1:1 커리어 챗 상담 */
              chatMessages.map((m, idx) => (
                <div key={idx} className={`${styles.bubbleWrap} ${styles[m.role]}`}>
                  <div className={styles.bubble}>
                    {m.content}
                  </div>
                </div>
              ))
            ) : (
              /* 면접 시뮬레이션 모드 */
              <>
                {interviewHistory.map((m, idx) => {
                  if (m.role === 'feedback') {
                    const fb = m.feedback
                    return (
                      <div key={idx} className={styles.feedbackCard}>
                        <div className={styles.feedbackHeader}>
                          <span className={styles.feedbackBadge}>
                            {interviewSession?.interview_mode === 'stress' ? '🌶️ 압박 피드백' :
                             interviewSession?.interview_mode === 'friendly' ? '🌸 친절 코칭 피드백' :
                             interviewSession?.interview_mode === 'timer' ? '⏱️ 타임어택 피드백' :
                             '🔍 기술 진단 피드백'}
                          </span>
                          <span className={`${styles.feedbackScore} ${
                            fb.score >= 80 ? styles.scoreGood :
                            fb.score >= 50 ? styles.scoreWarn : styles.scoreBad
                          }`}>{fb.score}점</span>
                        </div>
                        
                        <div className={styles.feedbackRow}>
                          <span className={styles.feedbackLabel}>상세 분석:</span>
                          <p className={styles.feedbackVal}>{fb.analysis}</p>
                        </div>

                        {/* 친절 모드 도움 힌트 출력 */}
                        {fb.hint && (
                          <div className={styles.friendlyHintCard}>
                            <span className={styles.feedbackLabel}>💡 학습 힌트 & 예문:</span>
                            <p className={styles.friendlyHintVal}>{fb.hint}</p>
                          </div>
                        )}

                        {/* 진단 모드 3인 가상 평가단 점수 출력 */}
                        {fb.personas && (
                          <div className={styles.personaContainer}>
                            <span className={styles.personaTitle}>👥 가상 평가단 진단 결과</span>
                            <div className={styles.personaGrid}>
                              {Object.entries(fb.personas).map(([persona, pdata]) => (
                                <div key={persona} className={styles.personaCard}>
                                  <div className={styles.personaHeader}>
                                    <span className={styles.personaIcon}>
                                      {persona.includes('HR') ? '👤' :
                                       persona.includes('기술') ? '💻' : '👑'}
                                    </span>
                                    <span className={styles.personaName}>{persona}</span>
                                    <span className={styles.personaScore}>{pdata.score}점</span>
                                  </div>
                                  <p className={styles.personaComment}>{pdata.comment}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 압박 모드 꼬리 질문 지적 문구 */}
                        {fb.follow_up_question && (
                          <div className={styles.followupWarning}>
                            ⚠️ <strong>꼬리 질문 경보:</strong> 답변에 명시되지 않은 디테일을 검증하기 위해 하단에 후속 질문이 출제됩니다.
                          </div>
                        )}

                        <div className={styles.feedbackRow}>
                          <span className={styles.feedbackLabel}>추천 모범답안:</span>
                          <p className={styles.feedbackModel}>{fb.model_answer}</p>
                        </div>

                        {/* 🧠 집단지성 최적 답변 */}
                        {fb.optimal_answer && (
                          <div className={styles.optimalWrap}>
                            <div className={styles.optimalHeader}>
                              🧠 집단지성 최적 답변
                              <span className={styles.optimalBadge}>
                                {fb.optimal_answer.sample_count}명 답변 분석 · 평균 {fb.optimal_answer.avg_score}점
                              </span>
                            </div>

                            {/* AI 모범 vs 커뮤니티 비교 분석 */}
                            {fb.optimal_answer.analysis && (
                              <div className={styles.optimalAnalysis}>
                                <span className={styles.optimalAnalysisLabel}>📊 비교 분석</span>
                                <p className={styles.optimalAnalysisText}>{fb.optimal_answer.analysis}</p>
                              </div>
                            )}

                            {/* 커뮤니티 강점 */}
                            {fb.optimal_answer.strengths_from_community && (
                              <div className={styles.optimalStrength}>
                                <span className={styles.optimalStrengthLabel}>✅ 실제 답변에서 발견된 강점</span>
                                <p>{fb.optimal_answer.strengths_from_community}</p>
                              </div>
                            )}

                            {/* 최종 최적 답변 */}
                            <div className={styles.optimalAnswer}>
                              <span className={styles.optimalAnswerLabel}>⭐ 최종 최적 답변</span>
                              <p className={styles.optimalAnswerText}>{fb.optimal_answer.optimal_answer}</p>
                            </div>
                          </div>
                        )}

                        {/* 커뮤니티 통계 (최적 답변 없을 때 — 몇 명 더 필요한지 안내) */}
                        {!fb.optimal_answer && fb.community_stats && (
                          <div className={styles.communityStats}>
                            {fb.community_stats.needed > 0
                              ? `👥 ${fb.community_stats.count}명 답변 수집 중 — ${fb.community_stats.needed}명 더 답변하면 집단지성 최적 답변이 생성됩니다`
                              : `👥 ${fb.community_stats.count}명의 답변을 학습했습니다`
                            }
                          </div>
                        )}
                      </div>
                    )
                  }
                  
                  return (
                    <div key={idx} className={`${styles.bubbleWrap} ${styles[m.role]}`}>
                      <div className={styles.bubble}>
                        {m.content}
                      </div>
                    </div>
                  )
                })}
                {!interviewSession && !loading && (
                  <div className={styles.interviewEmpty}>
                    <span style={{ fontSize: '2.5rem' }}>🎯</span>
                    <p style={{ margin: '8px 0', fontWeight: 'bold' }}>모의 면접 연습이 비어있습니다.</p>
                    <p className={styles.emptySub}>분석 완료 페이지 공고 카드 하단의 <br/><strong>'💬 면접 연습하기'</strong>를 클릭하여 시작해 보세요!</p>
                  </div>
                )}
              </>
            )}

            {/* AI 답변 대기 로더 */}
            {loading && (
              <div className={`${styles.bubbleWrap} ${styles.assistant}`}>
                <div className={styles.bubble}>
                  <div className={styles.loaderWrap}>
                    <span className={styles.dot} />
                    <span className={styles.dot} />
                    <span className={styles.dot} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {activeTab === 'interview' && interviewSession?.interview_mode === 'timer' && !interviewCompleted && !loading && (
            <div className={styles.timerBarWrapper}>
              <div className={styles.timerBadge}>⏱️ {timeLeft}초 남음</div>
              <div className={styles.timerBarBg}>
                <div 
                  className={`${styles.timerBarFill} ${
                    timeLeft <= 15 ? styles.timerRed : timeLeft <= 30 ? styles.timerOrange : styles.timerGreen
                  }`}
                  style={{ width: `${(timeLeft / 60) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* 푸터 입력부 */}
          {activeTab === 'chat' ? (
            <form onSubmit={handleSendChatMessage} className={styles.chatFooter}>
              <input
                className={styles.chatInput}
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                placeholder="커리어 상담 질문을 입력하세요..."
                disabled={loading}
              />
              <button className={styles.sendBtn} type="submit" disabled={!chatInput.trim() || loading}>
                전송
              </button>
            </form>
          ) : (
            <form onSubmit={handleSubmitInterviewAnswer} className={styles.chatFooter}>
              <input
                className={styles.chatInput}
                type="text"
                value={interviewAnswer}
                onChange={e => setInterviewAnswer(e.target.value)}
                placeholder={
                  interviewCompleted ? "면접이 완료되었습니다." :
                  !interviewSession ? "공고 카드의 면접을 먼저 시작해 주세요." : "답변을 입력해 주세요..."
                }
                disabled={!interviewSession || interviewCompleted || loading}
              />
              <button 
                className={styles.sendBtn} 
                type="submit" 
                disabled={!interviewAnswer.trim() || !interviewSession || interviewCompleted || loading}
              >
                답변
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
