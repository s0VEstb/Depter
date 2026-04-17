import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { registerUser } from '../api/client';
import { useAuth } from '../context/AuthContext';

/**
 * RegisterPage — регистрация заёмщика
 * Glassmorphism-форма с валидацией и отправкой на POST /api/users
 */

// Варианты типов занятости
const OCCUPATION_OPTIONS = [
    { value: 'patent', label: 'Патент' },
    { value: 'employed', label: 'Наёмный' },
    { value: 'self_employed', label: 'Самозанятый' },
    { value: 'ip', label: 'ИП' },
    { value: 'other', label: 'Другое' },
];

const BUSINESS_TYPES = ['ИП', 'ООО', 'ОсОО', 'Физлицо', 'Другое'];

const CITIES = ['Бишкек', 'Ош', 'Джалал-Абад', 'Каракол', 'Нарын', 'Баткен', 'Талас', 'Токмок'];

export default function RegisterPage() {
    const navigate = useNavigate();
    const { login } = useAuth();

    const [form, setForm] = useState({
        full_name: '',
        phone: '+996',
        email: '',
        password: '',
        confirm_password: '',
        inn: '',
        passport_id: '',
        birth_date: '',
        city: 'Бишкек',
        business_type: 'ИП',
        occupation: 'self_employed',
        consent: false,
    });

    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [apiError, setApiError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    // Обновление поля формы
    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setForm((prev) => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value,
        }));
        // Сбрасываем ошибку при вводе
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: '' }));
        }
        setApiError('');
    };

    // Валидация формы
    const validate = () => {
        const errs = {};

        if (!form.full_name.trim()) errs.full_name = 'Введите ФИО';
        if (!form.phone.match(/^\+996\d{9}$/)) errs.phone = 'Формат: +996XXXXXXXXX';
        if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) errs.email = 'Некорректный email';
        if (!form.password || form.password.length < 6) errs.password = 'Минимум 6 символов';
        if (form.password !== form.confirm_password) errs.confirm_password = 'Пароли не совпадают';
        if (!form.inn.match(/^\d{14}$/)) errs.inn = 'ИНН должен содержать 14 цифр';
        if (!form.passport_id.match(/^[A-Z]{2}\d{7}$/)) errs.passport_id = 'Формат: ID1234567';
        if (!form.birth_date) errs.birth_date = 'Укажите дату рождения';
        if (!form.consent) errs.consent = 'Необходимо дать согласие';

        setErrors(errs);
        return Object.keys(errs).length === 0;
    };

    // Отправка формы
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validate()) return;

        setLoading(true);
        setApiError('');

        try {
            const payload = {
                full_name: form.full_name.trim(),
                phone: form.phone,
                email: form.email.trim(),
                inn: form.inn,
                passport_id: form.passport_id.toUpperCase(),
                birth_date: new Date(form.birth_date).toISOString(),
                city: form.city,
                business_type: form.business_type,
                occupation: form.occupation,
                consent_given_at: new Date().toISOString(),
                consent_version: '1.0',
                password: form.password,
            };

            const data = await registerUser(payload);
            // Сохраняем данные пользователя в AuthContext
            login({
                id: data.id,
                full_name: data.full_name,
                phone: data.phone,
            });
            // Успех — переходим на страницу загрузки
            navigate(`/upload?phone=${encodeURIComponent(form.phone)}&name=${encodeURIComponent(form.full_name)}`);
        } catch (err) {
            if (err.response?.status === 409) {
                // Пользователь уже существует
                setApiError('already_exists');
            } else {
                setApiError(err.response?.data?.detail || 'Ошибка при регистрации. Попробуйте ещё раз.');
            }
        } finally {
            setLoading(false);
        }
    };

    // Переход на загрузку для существующего пользователя
    const goToUpload = () => {
        navigate(`/upload?phone=${encodeURIComponent(form.phone)}&name=${encodeURIComponent(form.full_name)}`);
    };

    return (
        <div className="page">
            <div className="container" style={{ paddingTop: '40px', paddingBottom: '60px' }}>
                <div style={{ maxWidth: '600px', margin: '0 auto' }}>
                    <h1 className="animate-fade-in-up" style={{ opacity: 0, textAlign: 'center', marginBottom: '8px' }}>
                        <span className="gradient-text">Регистрация</span> заёмщика
                    </h1>
                    <p className="animate-fade-in-up delay-1" style={{ opacity: 0, textAlign: 'center', color: 'var(--color-text-secondary)', marginBottom: '32px' }}>
                        Заполните данные для прохождения AI-скоринга
                    </p>

                    <form onSubmit={handleSubmit} className="glass-card animate-fade-in-up delay-2" style={{ opacity: 0 }}>
                        {/* ФИО */}
                        <div className="form-group">
                            <label className="form-label">ФИО *</label>
                            <input
                                type="text"
                                name="full_name"
                                className={`form-input ${errors.full_name ? 'error' : ''}`}
                                placeholder="Иванов Иван Иванович"
                                value={form.full_name}
                                onChange={handleChange}
                            />
                            <span className="form-error">{errors.full_name || ''}</span>
                        </div>

                        {/* Телефон + Email */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <div className="form-group">
                                <label className="form-label">Телефон *</label>
                                <input
                                    type="tel"
                                    name="phone"
                                    className={`form-input ${errors.phone ? 'error' : ''}`}
                                    placeholder="+996700123456"
                                    value={form.phone}
                                    onChange={handleChange}
                                />
                                <span className="form-error">{errors.phone || ''}</span>
                            </div>
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
                        </div>

                        {/* Пароль + Подтверждение пароля */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <div className="form-group">
                                <label className="form-label">Пароль * (мин. 6 символов)</label>
                                <div style={{ position: 'relative', width: '100%' }}>
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        name="password"
                                        className={`form-input ${errors.password ? 'error' : ''}`}
                                        placeholder="••••••••"
                                        value={form.password}
                                        onChange={handleChange}
                                        style={{ width: '100%', paddingRight: '40px', boxSizing: 'border-box' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: '12px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            padding: '4px',
                                            display: 'flex',
                                            alignItems: 'center',
                                        }}
                                        tabIndex={-1}
                                        title={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                                    >
                                        {showPassword ? (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                                <circle cx="12" cy="12" r="3" />
                                            </svg>
                                        ) : (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                                                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                                                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                                                <line x1="1" y1="1" x2="23" y2="23" />
                                            </svg>
                                        )}
                                    </button>
                                </div>
                                <span className="form-error">{errors.password || ''}</span>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Повторите пароль *</label>
                                <div style={{ position: 'relative', width: '100%' }}>
                                    <input
                                        type={showConfirmPassword ? 'text' : 'password'}
                                        name="confirm_password"
                                        className={`form-input ${errors.confirm_password ? 'error' : ''}`}
                                        placeholder="••••••••"
                                        value={form.confirm_password}
                                        onChange={handleChange}
                                        style={{ width: '100%', paddingRight: '40px', boxSizing: 'border-box' }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        style={{
                                            position: 'absolute',
                                            right: '12px',
                                            top: '50%',
                                            transform: 'translateY(-50%)',
                                            background: 'none',
                                            border: 'none',
                                            cursor: 'pointer',
                                            padding: '4px',
                                            display: 'flex',
                                            alignItems: 'center',
                                        }}
                                        tabIndex={-1}
                                        title={showConfirmPassword ? 'Скрыть пароль' : 'Показать пароль'}
                                    >
                                        {showConfirmPassword ? (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                                <circle cx="12" cy="12" r="3" />
                                            </svg>
                                        ) : (
                                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                                                <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                                                <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                                                <line x1="1" y1="1" x2="23" y2="23" />
                                            </svg>
                                        )}
                                    </button>
                                </div>
                                <span className="form-error">{errors.confirm_password || ''}</span>
                            </div>
                        </div>

                        {/* ИНН + Паспорт */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <div className="form-group">
                                <label className="form-label">ИНН *</label>
                                <input
                                    type="text"
                                    name="inn"
                                    className={`form-input ${errors.inn ? 'error' : ''}`}
                                    placeholder="12345678901234"
                                    maxLength={14}
                                    value={form.inn}
                                    onChange={handleChange}
                                />
                                <span className="form-error">{errors.inn || ''}</span>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Номер паспорта *</label>
                                <input
                                    type="text"
                                    name="passport_id"
                                    className={`form-input ${errors.passport_id ? 'error' : ''}`}
                                    placeholder="ID1234567"
                                    maxLength={9}
                                    value={form.passport_id}
                                    onChange={handleChange}
                                    style={{ textTransform: 'uppercase' }}
                                />
                                <span className="form-error">{errors.passport_id || ''}</span>
                            </div>
                        </div>

                        {/* Дата рождения */}
                        <div className="form-group">
                            <label className="form-label">Дата рождения *</label>
                            <input
                                type="date"
                                name="birth_date"
                                className={`form-input ${errors.birth_date ? 'error' : ''}`}
                                value={form.birth_date}
                                onChange={handleChange}
                                style={{ colorScheme: 'dark' }}
                            />
                            <span className="form-error">{errors.birth_date || ''}</span>
                        </div>

                        {/* Город + Тип бизнеса + Занятость */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                            <div className="form-group">
                                <label className="form-label">Город</label>
                                <select
                                    name="city"
                                    className="form-select"
                                    value={form.city}
                                    onChange={handleChange}
                                >
                                    {CITIES.map((c) => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Тип бизнеса</label>
                                <select
                                    name="business_type"
                                    className="form-select"
                                    value={form.business_type}
                                    onChange={handleChange}
                                >
                                    {BUSINESS_TYPES.map((b) => (
                                        <option key={b} value={b}>{b}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Занятость</label>
                                <select
                                    name="occupation"
                                    className="form-select"
                                    value={form.occupation}
                                    onChange={handleChange}
                                >
                                    {OCCUPATION_OPTIONS.map((o) => (
                                        <option key={o.value} value={o.value}>{o.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {/* Согласие */}
                        <div className="form-group" style={{ marginTop: '16px' }}>
                            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    name="consent"
                                    checked={form.consent}
                                    onChange={handleChange}
                                    style={{
                                        width: '20px',
                                        height: '20px',
                                        accentColor: 'var(--color-cyan)',
                                        marginTop: '2px',
                                        flexShrink: 0,
                                    }}
                                />
                                <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    Я даю согласие на обработку персональных данных в соответствии с политикой конфиденциальности Depter *
                                </span>
                            </label>
                            <span className="form-error">{errors.consent || ''}</span>
                        </div>

                        {/* API Error */}
                        {apiError && apiError !== 'already_exists' && (
                            <div className="error-banner" style={{ marginBottom: '16px' }}>
                                ⚠️ {apiError}
                            </div>
                        )}

                        {/* Пользователь уже существует */}
                        {apiError === 'already_exists' && (
                            <div
                                className="glass-card"
                                style={{
                                    textAlign: 'center',
                                    padding: '20px',
                                    marginBottom: '16px',
                                    borderColor: 'var(--color-yellow)',
                                }}
                            >
                                <p style={{ marginBottom: '12px', color: 'var(--color-yellow)' }}>
                                    ⚠️ Пользователь уже зарегистрирован
                                </p>
                                <button type="button" className="btn btn-primary" onClick={goToUpload}>
                                    Перейти к загрузке →
                                </button>
                            </div>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                            style={{ width: '100%', marginTop: '8px' }}
                        >
                            {loading ? (
                                <>
                                    <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
                                    Регистрация...
                                </>
                            ) : (
                                '✨ Зарегистрироваться'
                            )}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
