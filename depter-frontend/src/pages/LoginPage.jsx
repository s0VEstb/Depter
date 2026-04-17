import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../api/client';

/**
 * LoginPage — вход по email + пароль
 * Glassmorphism-форма в стиле RegisterPage
 */
export default function LoginPage() {
    const navigate = useNavigate();
    const { login } = useAuth();

    const [form, setForm] = useState({ email: '', password: '' });
    const [errors, setErrors] = useState({});
    const [apiError, setApiError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setForm((prev) => ({ ...prev, [name]: value }));
        if (errors[name]) setErrors((p) => ({ ...p, [name]: '' }));
        setApiError('');
    };

    const validate = () => {
        const errs = {};
        if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/))
            errs.email = 'Некорректный email';
        if (form.password.length < 6)
            errs.password = 'Минимум 6 символов';
        setErrors(errs);
        return Object.keys(errs).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validate()) return;

        setLoading(true);
        try {
            const data = await loginUser(form.email, form.password);
            login({
                id: data.id,
                full_name: data.full_name,
                phone: data.phone,
                email: data.email,
            });
            navigate(`/upload?phone=${encodeURIComponent(data.phone)}`);
        } catch (err) {
            setApiError(err.response?.data?.detail || 'Ошибка входа');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page">
            <div className="container" style={{ paddingTop: '80px', paddingBottom: '60px' }}>
                <div style={{ maxWidth: '440px', margin: '0 auto' }}>
                    <h1 className="animate-fade-in-up" style={{ opacity: 0, textAlign: 'center', marginBottom: '8px' }}>
                        <span className="gradient-text">Вход</span> в Depter
                    </h1>
                    <p className="animate-fade-in-up delay-1" style={{ opacity: 0, textAlign: 'center', color: 'var(--color-text-secondary)', marginBottom: '32px' }}>
                        Введите email и пароль для входа
                    </p>

                    <form onSubmit={handleSubmit} className="glass-card animate-fade-in-up delay-2" style={{ opacity: 0 }}>
                        {/* Email */}
                        <div className="form-group">
                            <label className="form-label">Email *</label>
                            <input
                                type="email"
                                name="email"
                                className={`form-input ${errors.email ? 'error' : ''}`}
                                placeholder="ivan@example.com"
                                value={form.email}
                                onChange={handleChange}
                            />
                            <span className="form-error">{errors.email || ''}</span>
                        </div>

                        {/* Пароль */}
                        <div className="form-group">
                            <label className="form-label">Пароль *</label>
                            <input
                                type="password"
                                name="password"
                                className={`form-input ${errors.password ? 'error' : ''}`}
                                placeholder="••••••••"
                                value={form.password}
                                onChange={handleChange}
                            />
                            <span className="form-error">{errors.password || ''}</span>
                        </div>

                        {/* API Error */}
                        {apiError && (
                            <div className="error-banner" style={{ marginBottom: '16px' }}>
                                ⚠️ {apiError}
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                            style={{ width: '100%' }}
                        >
                            {loading ? (
                                <>
                                    <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
                                    Вход...
                                </>
                            ) : (
                                '→ Войти'
                            )}
                        </button>

                        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                            Нет аккаунта?{' '}
                            <Link to="/register" style={{ color: 'var(--color-cyan)' }}>
                                Зарегистрироваться
                            </Link>
                        </p>
                    </form>
                </div>
            </div>
        </div>
    );
}
