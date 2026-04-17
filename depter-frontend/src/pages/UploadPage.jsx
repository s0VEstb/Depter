import { useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { uploadFiles } from '../api/client';
import { useAuth } from '../context/AuthContext';

/**
 * UploadPage — загрузка PDF-выписок
 * Drag-and-drop зона, список файлов, отправка на скоринг
 */

const MAX_FILES = 3;
const MAX_SIZE_MB = 20;

export default function UploadPage() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user } = useAuth();

    // Приоритет: query params → AuthContext → пусто
    const phone = searchParams.get('phone') || user?.phone || '';
    const name = searchParams.get('name') || user?.full_name || '';

    const [files, setFiles] = useState([]);
    const [dragOver, setDragOver] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const fileInputRef = useRef(null);

    // Валидация и добавление файлов
    const addFiles = (newFiles) => {
        setError('');
        const validFiles = [];
        for (const file of newFiles) {
            if (file.type !== 'application/pdf') {
                setError('Допустимы только PDF-файлы');
                continue;
            }
            if (file.size > MAX_SIZE_MB * 1024 * 1024) {
                setError(`Файл "${file.name}" больше ${MAX_SIZE_MB} МБ`);
                continue;
            }
            validFiles.push(file);
        }

        setFiles((prev) => {
            const combined = [...prev, ...validFiles];
            if (combined.length > MAX_FILES) {
                setError(`Максимум ${MAX_FILES} файла`);
                return combined.slice(0, MAX_FILES);
            }
            return combined;
        });
    };

    // Удаление файла
    const removeFile = (index) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    // Drag events
    const handleDragOver = (e) => {
        e.preventDefault();
        setDragOver(true);
    };
    const handleDragLeave = () => setDragOver(false);
    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        addFiles(Array.from(e.dataTransfer.files));
    };

    // Click для выбора файлов
    const handleZoneClick = () => fileInputRef.current?.click();

    // Форматирование размера файла
    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    // Отправка на скоринг
    const handleSubmit = async () => {
        if (files.length === 0) {
            setError('Добавьте хотя бы один PDF-файл');
            return;
        }
        if (!phone) {
            setError('Не указан телефон пользователя');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const result = await uploadFiles(files, phone, name);
            // При 202 — переход на страницу прогресса
            navigate(`/progress/${result.job_id}`);
        } catch (err) {
            setError(err.response?.data?.detail || 'Ошибка загрузки. Попробуйте ещё раз.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page">
            <div className="container" style={{ paddingTop: '40px', paddingBottom: '60px' }}>
                <div style={{ maxWidth: '650px', margin: '0 auto' }}>
                    <h1 className="animate-fade-in-up" style={{ opacity: 0, textAlign: 'center', marginBottom: '8px' }}>
                        <span className="gradient-text">Загрузка</span> выписок
                    </h1>
                    <p className="animate-fade-in-up delay-1" style={{ opacity: 0, textAlign: 'center', color: 'var(--color-text-secondary)', marginBottom: '32px' }}>
                        Загрузите PDF-выписки для AI-анализа (до {MAX_FILES} файлов)
                    </p>

                    {/* Информация о пользователе */}
                    {phone && (
                        <div
                            className="glass-card animate-fade-in-up delay-1"
                            style={{ opacity: 0, display: 'flex', alignItems: 'center', gap: '12px', padding: '16px 20px', marginBottom: '24px' }}
                        >
                            <span style={{ fontSize: '1.5rem' }}>👤</span>
                            <div>
                                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{name || 'Пользователь'}</div>
                                <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>{phone}</div>
                            </div>
                        </div>
                    )}

                    {/* Drag-and-drop зона */}
                    <div
                        className={`upload-zone animate-fade-in-up delay-2 ${dragOver ? 'drag-over' : ''}`}
                        style={{ opacity: 0 }}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={handleZoneClick}
                    >
                        <span className="upload-zone-icon">📄</span>
                        <p className="upload-zone-text">
                            Перетащите PDF-файлы сюда или <span style={{ color: 'var(--color-cyan)', fontWeight: 600 }}>нажмите для выбора</span>
                        </p>
                        <p className="upload-zone-hint">
                            Поддерживаемые банки: mBank, Elsom, O!Dengi, Bakai • До {MAX_SIZE_MB} MB каждый
                        </p>

                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".pdf"
                            multiple
                            onChange={(e) => addFiles(Array.from(e.target.files))}
                            style={{ display: 'none' }}
                        />
                    </div>

                    {/* Список файлов */}
                    {files.length > 0 && (
                        <div className="file-list animate-fade-in">
                            {files.map((file, i) => (
                                <div className="file-item" key={`${file.name}-${i}`}>
                                    <div className="file-item-info">
                                        <span>📎</span>
                                        <span className="file-item-name">{file.name}</span>
                                        <span className="file-item-size">{formatSize(file.size)}</span>
                                    </div>
                                    <button
                                        className="file-item-remove"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            removeFile(i);
                                        }}
                                        title="Удалить"
                                    >
                                        ✕
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Ошибка */}
                    {error && (
                        <div className="error-banner" style={{ marginTop: '16px' }}>
                            ⚠️ {error}
                        </div>
                    )}

                    {/* Кнопка отправки */}
                    <button
                        className="btn btn-primary btn-lg"
                        onClick={handleSubmit}
                        disabled={loading || files.length === 0}
                        style={{
                            width: '100%',
                            marginTop: '24px',
                            opacity: files.length === 0 ? 0.5 : 1,
                        }}
                    >
                        {loading ? (
                            <>
                                <span className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
                                Загрузка...
                            </>
                        ) : (
                            `🚀 Отправить на скоринг (${files.length} ${files.length === 1 ? 'файл' : 'файла'})`
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
