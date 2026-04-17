import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProfile } from '../api/client';
import GaugeChart from '../components/GaugeChart';
import BarChart from '../components/BarChart';
import LineChart from '../components/LineChart';

/**
 * ResultPage — страница результатов скоринга
 * GET /api/profile/{profile_id}
 * Ряд 1: Score + Метрики | Ряд 2: AI Вердикт | Ряд 3: Графики | Ряд 4: Детали | Ряд 5: Кнопки
 */

const formatMoney = (n) => {
    if (n == null) return '—';
    return Math.round(n).toLocaleString('ru-RU');
};

const SCORE_TOOLTIPS = {
    'Stability Score': 'Показатель стабильности дохода. Высокий — доходы поступают регулярно, без резких провалов.',
    'Trend Score': 'Тренд изменения дохода за период. Положительный — доходы растут, отрицательный — снижаются.',
    'Fraud Penalty': 'Штрафные баллы за подозрительные паттерны: ночные переводы, круглые суммы, несовпадения.',
    'Период данных': 'Количество месяцев, за которые проанализированы финансовые данные.',
    'Источников': 'Количество банковских источников (выписок), из которых собраны данные.',
    'Расходы / Доходы': 'Соотношение расходов к доходам. Чем ниже — тем лучше для кредитоспособности.',
    'Категории': 'Разбивка доходов по категориям операций (переводы, наличные, QR и т.д.).',
};

function DetailWithTooltip({ label, tooltip, children }) {
    return (
        <div className="glass-card score-detail-item has-tooltip">
            <div className="score-detail-label">
                {label}
                {tooltip && (
                    <>
                        <span className="tooltip-icon">ⓘ</span>
                        <div className="tooltip-bubble">{tooltip}</div>
                    </>
                )}
            </div>
            {children}
        </div>
    );
}

export default function ResultPage() {
    const { profileId } = useParams();
    const navigate = useNavigate();

    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!profileId) return;

        const fetchProfile = async () => {
            try {
                const data = await getProfile(profileId);
                // Проверка владельца: профиль должен принадлежать текущему пользователю
                const stored = localStorage.getItem('depter_user');
                const currentUser = stored ? JSON.parse(stored) : null;
                if (data.user_id && currentUser && data.user_id !== currentUser.id) {
                    setError('Вы не можете просматривать чужой отчёт.');
                    return;
                }
                setProfile(data);
            } catch (err) {
                setError(err.response?.data?.detail || 'Не удалось загрузить профиль');
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, [profileId]);

    // Загрузка
    if (loading) {
        return (
            <div className="page">
                <div
                    className="container"
                    style={{
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        minHeight: 'calc(100vh - 80px)',
                    }}
                >
                    <div className="spinner" style={{ width: '60px', height: '60px' }} />
                </div>
            </div>
        );
    }

    // Ошибка
    if (error) {
        return (
            <div className="page">
                <div
                    className="container"
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        minHeight: 'calc(100vh - 80px)',
                        gap: '24px',
                    }}
                >
                    <div className="error-banner">❌ {error}</div>
                    <button className="btn btn-secondary" onClick={() => navigate('/')}>
                        На главную
                    </button>
                </div>
            </div>
        );
    }

    if (!profile) return null;

    const {
        defter_score,
        recommended_limit,
        avg_income_monthly,
        income_trend,
        stability,
        fraud_risk_score,
        income_by_source,
        income_by_category,
        score_components,
        sources,
        sources_count,
        data_period_months,
        total_income,
        total_expense,
        avg_expense_monthly,
        expense_to_income_ratio,
        net_cashflow_monthly,
        overdraft_count,
        max_overdraft_amount,
        income_anomaly_detected,
        ai_verdict,
    } = profile;

    // Определение стрелки тренда
    const trendArrow = income_trend >= 0 ? '↑' : '↓';
    const trendColor = income_trend >= 0 ? 'var(--color-success)' : 'var(--color-error)';
    const trendPercent = `${income_trend >= 0 ? '+' : ''}${(income_trend * 100).toFixed(0)}%`;

    // Цвет стабильности
    const stabilityPercent = Math.round(stability * 100);
    const stabilityColor =
        stabilityPercent >= 80 ? 'var(--color-success)' :
            stabilityPercent >= 60 ? 'var(--color-yellow)' :
                'var(--color-error)';

    // Цвет фрода
    const fraudColor =
        fraud_risk_score <= 20 ? 'var(--color-success)' :
            fraud_risk_score <= 50 ? 'var(--color-warning)' :
                'var(--color-error)';

    return (
        <div className="page">
            <div className="container result-page">
                {/* ═══════ Ряд 1 — Score + Метрики ═══════ */}
                <section className="result-section animate-fade-in-up" style={{ opacity: 0 }}>
                    <div className="score-metrics-row">
                        {/* Левая часть — Gauge + Лимит */}
                        <div className="glass-card score-left">
                            <div className="score-gauge-wrapper">
                                <GaugeChart score={defter_score} size={220} />
                                <span className="score-label">Кредитный рейтинг</span>
                            </div>
                            <div className="score-limit-inline">
                                <div className="score-limit-value gradient-text">
                                    {formatMoney(recommended_limit)} KGS
                                </div>
                                <div className="score-limit-label">Рекомендованный лимит</div>
                            </div>
                        </div>
                        {/* Правая часть — 4 метрики */}
                        <div className="metrics-side">
                            <h3 className="result-section-title" style={{ marginBottom: '16px' }}>
                                📋 Ключевые метрики
                            </h3>
                            <div className="metrics-grid-2x2">
                                {/* Средний доход */}
                                <div className="glass-card metric-card">
                                    <span className="metric-icon">💰</span>
                                    <div className="metric-value">{formatMoney(avg_income_monthly)}</div>
                                    <div className="metric-label">Средний доход / мес (KGS)</div>
                                </div>

                                {/* Тренд */}
                                <div className="glass-card metric-card">
                                    <span className="metric-icon">📈</span>
                                    <div className="metric-value" style={{ color: trendColor }}>
                                        {trendArrow} {trendPercent}
                                    </div>
                                    <div className="metric-label">Тренд дохода</div>
                                </div>

                                {/* Стабильность */}
                                <div className="glass-card metric-card">
                                    <span className="metric-icon">🔒</span>
                                    <div className="metric-value">
                                        {stabilityPercent}%
                                        <span
                                            className="badge"
                                            style={{
                                                marginLeft: '8px',
                                                fontSize: '0.6rem',
                                                background: `${stabilityColor}20`,
                                                color: stabilityColor,
                                            }}
                                        >
                                            {stabilityPercent >= 80 ? 'Высокая' : stabilityPercent >= 60 ? 'Средняя' : 'Низкая'}
                                        </span>
                                    </div>
                                    <div className="metric-label">Стабильность</div>
                                </div>

                                {/* Риск фрода */}
                                <div className="glass-card metric-card">
                                    <span className="metric-icon">⚠️</span>
                                    <div className="metric-value" style={{ color: fraudColor }}>
                                        {fraud_risk_score}
                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>/100</span>
                                    </div>
                                    <div className="metric-label">Риск фрода</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* ═══════ Ряд 2 — AI Verdict ═══════ */}
                {ai_verdict && (
                    <section className="result-section animate-fade-in-up delay-1" style={{ opacity: 0 }}>
                        <h3 className="result-section-title">🤖 AI Вердикт</h3>
                        <div className="glass-card" style={{ padding: '28px' }}>
                            {/* Решение + Уровень риска */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
                                <span
                                    className="badge"
                                    style={{
                                        fontSize: '1.1rem',
                                        padding: '8px 20px',
                                        background: ai_verdict.decision === 'ОДОБРЕНО'
                                            ? 'rgba(76, 175, 80, 0.2)' : ai_verdict.decision === 'ОТКАЗ'
                                                ? 'rgba(244, 67, 54, 0.2)' : 'rgba(255, 193, 7, 0.2)',
                                        color: ai_verdict.decision === 'ОДОБРЕНО'
                                            ? 'var(--color-success)' : ai_verdict.decision === 'ОТКАЗ'
                                                ? 'var(--color-error)' : 'var(--color-yellow)',
                                        borderRadius: '8px',
                                    }}
                                >
                                    {ai_verdict.decision === 'ОДОБРЕНО' ? '✅' :
                                        ai_verdict.decision === 'ОТКАЗ' ? '❌' : '⚠️'}
                                    {' '}{ai_verdict.decision}
                                </span>
                                <span
                                    className="badge"
                                    style={{
                                        padding: '6px 14px',
                                        background: ai_verdict.risk_level === 'НИЗКИЙ'
                                            ? 'rgba(76, 175, 80, 0.15)' : ai_verdict.risk_level === 'ВЫСОКИЙ'
                                                ? 'rgba(244, 67, 54, 0.15)' : 'rgba(255, 193, 7, 0.15)',
                                        color: ai_verdict.risk_level === 'НИЗКИЙ'
                                            ? 'var(--color-success)' : ai_verdict.risk_level === 'ВЫСОКИЙ'
                                                ? 'var(--color-error)' : 'var(--color-yellow)',
                                    }}
                                >
                                    Риск: {ai_verdict.risk_level}
                                </span>
                                {ai_verdict.confidence != null && (
                                    <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                                        Уверенность: {(ai_verdict.confidence * 100).toFixed(0)}%
                                    </span>
                                )}
                            </div>

                            {/* Саммари */}
                            {ai_verdict.summary && (
                                <p style={{
                                    color: 'var(--color-text-secondary)',
                                    lineHeight: '1.6',
                                    marginBottom: '16px',
                                    fontSize: '0.95rem',
                                }}>
                                    {ai_verdict.summary}
                                </p>
                            )}

                            {/* Расширенные метрики */}
                            {(total_expense != null || overdraft_count != null) && (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                                    {total_income != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Общий доход</div>
                                            <div style={{ fontWeight: 600, color: 'var(--color-success)' }}>{formatMoney(total_income)} KGS</div>
                                        </div>
                                    )}
                                    {total_expense != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Общий расход</div>
                                            <div style={{ fontWeight: 600, color: 'var(--color-error)' }}>{formatMoney(total_expense)} KGS</div>
                                        </div>
                                    )}
                                    {avg_expense_monthly != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Средний расход / мес</div>
                                            <div style={{ fontWeight: 600 }}>{formatMoney(avg_expense_monthly)} KGS</div>
                                        </div>
                                    )}
                                    {net_cashflow_monthly != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Чистый cash flow / мес</div>
                                            <div style={{ fontWeight: 600, color: net_cashflow_monthly >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                                                {net_cashflow_monthly >= 0 ? '+' : ''}{formatMoney(net_cashflow_monthly)} KGS
                                            </div>
                                        </div>
                                    )}
                                    {overdraft_count != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Овердрафтов</div>
                                            <div style={{ fontWeight: 600, color: overdraft_count > 0 ? 'var(--color-error)' : 'var(--color-success)' }}>{overdraft_count}</div>
                                        </div>
                                    )}
                                    {income_anomaly_detected != null && (
                                        <div style={{ fontSize: '0.85rem' }}>
                                            <div style={{ color: 'var(--color-text-secondary)' }}>Аномалия дохода</div>
                                            <div style={{ fontWeight: 600, color: income_anomaly_detected ? 'var(--color-error)' : 'var(--color-success)' }}>
                                                {income_anomaly_detected ? '⚠️ Обнаружена' : '✅ Нет'}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Риск-флаги */}
                            {ai_verdict.risk_flags?.length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                    {ai_verdict.risk_flags.map((flag, i) => (
                                        <span
                                            key={i}
                                            className="badge"
                                            style={{
                                                background: 'rgba(244, 67, 54, 0.12)',
                                                color: 'var(--color-error)',
                                                fontSize: '0.8rem',
                                                padding: '4px 10px',
                                            }}
                                        >
                                            ⚡ {flag}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* ═══════ Ряд 3 — Графики бок о бок ═══════ */}
                <section className="result-section animate-fade-in-up delay-2" style={{ opacity: 0 }}>
                    <div className="charts-row">
                        <div className="glass-card chart-half">
                            <h4 className="chart-title">🏦 Источники дохода</h4>
                            <BarChart data={income_by_source || {}} width={420} height={250} />
                            <div className="sources-list">
                                {(sources || []).map((src) => (
                                    <span key={src} className="badge badge-cyan">{src}</span>
                                ))}
                            </div>
                        </div>
                        <div className="glass-card chart-half">
                            <h4 className="chart-title">📉 Динамика доходов по месяцам</h4>
                            <LineChart
                                data={score_components?.monthly_income || {}}
                                width={420}
                                height={250}
                            />
                        </div>
                    </div>
                </section>

                {/* ═══════ Ряд 4 — Детали скоринга (с tooltips) ═══════ */}
                <section className="result-section animate-fade-in-up delay-3" style={{ opacity: 0 }}>
                    <h3 className="result-section-title">🔍 Детали скоринга</h3>
                    <div className="score-details-grid">
                        <DetailWithTooltip label="Stability Score" tooltip={SCORE_TOOLTIPS['Stability Score']}>
                            <div className="score-detail-value gradient-text">
                                {score_components?.stability_score ?? Math.round(stability * 350)}
                            </div>
                        </DetailWithTooltip>
                        <DetailWithTooltip label="Trend Score" tooltip={SCORE_TOOLTIPS['Trend Score']}>
                            <div className="score-detail-value gradient-text">
                                {score_components?.trend_score ?? (income_trend * 100).toFixed(1)}
                            </div>
                        </DetailWithTooltip>
                        <DetailWithTooltip label="Fraud Penalty" tooltip={SCORE_TOOLTIPS['Fraud Penalty']}>
                            <div className="score-detail-value" style={{ color: fraudColor }}>
                                {score_components?.fraud_penalty ?? fraud_risk_score ?? 0}
                            </div>
                        </DetailWithTooltip>
                        <DetailWithTooltip label="Период данных" tooltip={SCORE_TOOLTIPS['Период данных']}>
                            <div className="score-detail-value gradient-text">
                                {data_period_months ?? '—'} мес.
                            </div>
                        </DetailWithTooltip>
                        <DetailWithTooltip label="Источников" tooltip={SCORE_TOOLTIPS['Источников']}>
                            <div className="score-detail-value gradient-text">
                                {sources_count ?? '—'}
                            </div>
                        </DetailWithTooltip>
                        {expense_to_income_ratio != null && (
                            <DetailWithTooltip label="Расходы / Доходы" tooltip={SCORE_TOOLTIPS['Расходы / Доходы']}>
                                <div className="score-detail-value" style={{
                                    color: expense_to_income_ratio > 1
                                        ? 'var(--color-error)'
                                        : expense_to_income_ratio > 0.85
                                            ? 'var(--color-warning)'
                                            : 'var(--color-success)',
                                }}>
                                    {(expense_to_income_ratio * 100).toFixed(0)}%
                                </div>
                            </DetailWithTooltip>
                        )}
                        {income_by_category && (
                            <DetailWithTooltip label="Категории" tooltip={SCORE_TOOLTIPS['Категории']}>
                                <div style={{ marginTop: '8px' }}>
                                    {Object.entries(income_by_category).map(([cat, val]) => (
                                        <div
                                            key={cat}
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                fontSize: '0.85rem',
                                                marginBottom: '4px',
                                            }}
                                        >
                                            <span style={{ color: 'var(--color-text-secondary)' }}>{cat}</span>
                                            <span style={{ fontWeight: 600 }}>{formatMoney(val)}</span>
                                        </div>
                                    ))}
                                </div>
                            </DetailWithTooltip>
                        )}
                    </div>
                </section>

                {/* ═══════ Ряд 5 — Кнопки действий ═══════ */}
                <div className="action-buttons animate-fade-in-up delay-4" style={{ opacity: 0 }}>
                    <button className="btn btn-secondary" onClick={() => window.print()}>
                        📥 Скачать PDF-отчёт
                    </button>
                    <button className="btn btn-primary" onClick={() => navigate('/')}>
                        🔄 Новый скоринг
                    </button>
                </div>
            </div>
        </div>
    );
}
