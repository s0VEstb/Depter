import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUserProfiles } from '../api/client';

const formatMoney = (n) => n == null ? '—' : Math.round(n).toLocaleString('ru-RU');
const formatDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
};

export default function ProfilePage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [profiles, setProfiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // Если не залогинен — редирект на /login
    useEffect(() => {
        if (!user) {
            navigate('/login');
            return;
        }
        getUserProfiles(user.id)
            .then(setProfiles)
            .catch(() => setError('Не удалось загрузить историю'))
            .finally(() => setLoading(false));
    }, [user, navigate]);

    if (!user) return null;

    const getScoreColor = (score) => {
        if (score <= 400) return 'var(--color-error)';
        if (score <= 650) return 'var(--color-yellow)';
        if (score <= 850) return 'var(--color-success)';
        return 'var(--color-cyan)';
    };

    return (
        <div className="page">
            <div className="container" style={{ paddingTop: '40px', paddingBottom: '60px', maxWidth: '860px' }}>
                {/* Шапка профиля */}
                <div className="glass-card animate-fade-in-up" style={{ opacity: 0, marginBottom: '32px', padding: '28px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
                        {/* Аватар */}
                        <div style={{
                            width: '72px', height: '72px', borderRadius: '50%',
                            background: 'var(--color-gradient)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '2rem', fontWeight: 700, color: '#000', flexShrink: 0,
                        }}>
                            {user.full_name?.charAt(0)?.toUpperCase() || '?'}
                        </div>
                        <div style={{ flex: 1 }}>
                            <h2 style={{ marginBottom: '4px' }}>{user.full_name}</h2>
                            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                📱 {user.phone}
                            </p>
                            {user.email && (
                                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                    ✉️ {user.email}
                                </p>
                            )}
                        </div>
                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                            <button className="btn btn-primary btn-sm"
                                onClick={() => navigate('/upload')}>
                                + Новый скоринг
                            </button>
                            <button className="btn btn-ghost btn-sm"
                                onClick={() => { logout(); navigate('/'); }}>
                                Выйти
                            </button>
                        </div>
                    </div>
                </div>

                {/* История выписок */}
                <h3 className="result-section-title animate-fade-in-up delay-1" style={{ opacity: 0 }}>
                    📋 История скорингов
                </h3>

                {loading && (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
                        <div className="spinner" style={{ width: '48px', height: '48px' }} />
                    </div>
                )}

                {error && <div className="error-banner">❌ {error}</div>}

                {!loading && profiles.length === 0 && (
                    <div className="glass-card animate-fade-in-up delay-2" style={{
                        opacity: 0, textAlign: 'center', padding: '48px'
                    }}>
                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '20px' }}>
                            У вас ещё нет скоринговых отчётов
                        </p>
                        <button className="btn btn-primary"
                            onClick={() => navigate('/upload')}>
                            Загрузить выписку
                        </button>
                    </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {profiles.map((p, i) => (
                        <div key={p.profile_id}
                            className={`glass-card animate-fade-in-up delay-${Math.min(i + 1, 5)}`}
                            style={{
                                opacity: 0, padding: '20px 24px',
                                display: 'grid',
                                gridTemplateColumns: 'auto 1fr auto',
                                alignItems: 'center',
                                gap: '20px',
                                cursor: 'pointer',
                                transition: 'border-color 0.2s ease',
                            }}
                            onClick={() => navigate(`/result/${p.profile_id}`)}
                            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-cyan)'}
                            onMouseLeave={(e) => e.currentTarget.style.borderColor = ''}
                        >
                            {/* Defter Score */}
                            <div style={{ textAlign: 'center', minWidth: '80px' }}>
                                <div style={{
                                    fontSize: '1.8rem', fontWeight: 700,
                                    color: getScoreColor(p.defter_score),
                                }}>
                                    {p.defter_score}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)' }}>
                                    / 1000
                                </div>
                            </div>

                            {/* Детали */}
                            <div>
                                <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                                    Defter Score #{p.profile_id}
                                </div>
                                <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                                    <span>💰 {formatMoney(p.avg_monthly_income_kgs)} KGS/мес</span>
                                    <span>🏦 {p.sources_count} источн.</span>
                                    <span>📅 {p.data_period_months} мес. данных</span>
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--color-grey)', marginTop: '4px' }}>
                                    {formatDate(p.calculated_at)}
                                </div>
                            </div>

                            {/* Лимит + стрелка */}
                            <div style={{ textAlign: 'right' }}>
                                <div className="gradient-text" style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                                    {formatMoney(p.recommended_limit)} KGS
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                                    лимит
                                </div>
                                <div style={{ fontSize: '1.2rem', color: 'var(--color-cyan)', marginTop: '4px' }}>→</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
