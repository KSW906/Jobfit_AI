import styles from './Dashboard.module.css'

export default function BookmarkPanel({ bookmarks, onToggle }) {
  if (!bookmarks || bookmarks.length === 0) {
    return (
      <div className={styles.empty}>
        <span style={{ fontSize: '2.5rem' }}>🔖</span>
        <p style={{ margin: '8px 0', fontWeight: 'bold' }}>저장한 공고가 없습니다.</p>
        <p className={styles.emptySub}>
          채용공고 매칭 탭에서 마음에 드는 공고의 <strong>☆ 저장</strong> 버튼을 눌러 보관해 보세요.
        </p>
      </div>
    )
  }

  return (
    <div>
      <p className={styles.sectionDesc}>
        🔖 저장한 관심 공고 <strong>{bookmarks.length}</strong>건입니다. 언제든 다시 확인하고 지원하세요.
      </p>
      {bookmarks.map((b) => {
        const job = b.job || {}
        const skills = job.skills || []
        return (
          <div key={b.id} className={styles.bmCard}>
            <div className={styles.bmTop}>
              <div>
                <div className={styles.bmTitle}>{job.title || '(삭제된 공고)'}</div>
                <div className={styles.bmCo}>
                  {job.company || '익명 기업'}{job.location ? ` · ${job.location}` : ''}
                  {job.salary ? ` · 💰 ${job.salary}` : ''}
                </div>
              </div>
              <button
                className={styles.bmRemoveBtn}
                onClick={() => onToggle(job)}
                title="북마크 해제"
              >
                ★ 해제
              </button>
            </div>

            {skills.length > 0 && (
              <div className={styles.bmSkillRow}>
                {skills.slice(0, 8).map((s) => (
                  <span key={s} className={styles.bmSkillTag}>{s}</span>
                ))}
                {skills.length > 8 && (
                  <span className={styles.bmSkillMore}>+{skills.length - 8}</span>
                )}
              </div>
            )}

            {job.apply_url && (
              <a href={job.apply_url} target="_blank" rel="noreferrer" className={styles.bmApply}>
                지원하기 →
              </a>
            )}
          </div>
        )
      })}
    </div>
  )
}
