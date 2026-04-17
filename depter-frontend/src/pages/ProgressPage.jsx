import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJobStatus } from '../api/client';
import ProgressRing from '../components/ProgressRing';

/**
 * ProgressPage — страница прогресса обработки
 * Поллинг GET /api/status/{job_id} каждые 2 секунды
 * При done → переход на результат, при failed → ошибка
 */

// Статусы с иконками и подписями
const STATUS_STEPS = [
    { key: 'parsing', icon: '📄', label: 'Парсинг' },
    { key: 'aggregating', icon: '🧠', label: 'Агрегация' },
    { key: 'scoring', icon: '📊', label: 'Скоринг' },
    { key: 'done', icon: '✅', label: 'Готово' },
];

export default function ProgressPage() {
    const { jobId } = useParams();
    const navigate = useNavigate();

    const [status, setStatus] = useState('pending');
    const [step, setStep] = useState('Ожидание...');
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState(null);
    const intervalRef = useRef(null);

    useEffect(() => {
        if (!jobId) return;

        const poll = async () => {
            try {
                const data = await getJobStatus(jobId);
                setStatus(data.status);
                setStep(data.step || 'Обработка...');
                setProgress(data.progress || 0);

                if (data.status === 'done' && data.profile_id) {
                    clearInterval(intervalRef.current);
                    // Небольшая задержка для анимации 100%
                    setTimeout(() => {
                        navigate(`/result/${data.profile_id}`);
                    }, 1000);
                } else if (data.status === 'failed') {
                    clearInterval(intervalRef.current);
                    setError(data.error || 'Произошла ошибка при обработке');
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        // Первый запрос сразу
        poll();
        // Затем каждые 2 секунды
        intervalRef.current = setInterval(poll, 2000);

        return () => clearInterval(intervalRef.current);
    }, [jobId, navigate]);

    // Определяем текущий шаг для подсветки иконок
    const getCurrentIndex = () => {
        return STATUS_STEPS.findIndex((s) => s.key === status);
    };
    const currentIdx = getCurrentIndex();

    return (
        <div className="page">
            <div className="progress-page container">
                {/* Круговой прогресс */}
                <div className="animate-fade-in-up" style={{ opacity: 0 }}>
                    <ProgressRing progress={progress} size={220} />
                </div>

                {/* Текст статуса */}
                <div className="progress-status animate-fade-in-up delay-1" style={{ opacity: 0 }}>
                    <h2 style={{ marginBottom: '8px' }}>
                        {status === 'failed' ? (
                            <span style={{ color: 'var(--color-error)' }}>Ошибка обработки</span>
                        ) : status === 'done' ? (
                            <span className="gradient-text">Готово!</span>
                        ) : (
                            'Идёт обработка...'
                        )}
                    </h2>
                    <p className="progress-step">{step}</p>
                </div>

                {/* Иконки статусов */}
                <div className="progress-icons animate-fade-in-up delay-2" style={{ opacity: 0 }}>
                    {STATUS_STEPS.map((s, i) => {
                        let className = 'progress-icon-item';
                        if (i < currentIdx) className += ' completed';
                        else if (i === currentIdx) className += ' active';

                        return (
                            <div key={s.key} className={className}>
                                <span className="icon">{s.icon}</span>
                                <span className="label">{s.label}</span>
                            </div>
                        );
                    })}
                </div>

                {/* Ошибка */}
                {error && (
                    <div className="error-banner animate-fade-in" style={{ maxWidth: '500px' }}>
                        ❌ {error}
                    </div>
                )}

                {/* Кнопка при ошибке */}
                {status === 'failed' && (
                    <button className="btn btn-secondary" onClick={() => navigate('/register')}>
                        🔄 Попробовать заново
                    </button>
                )}
            </div>
        </div>
    );
}
