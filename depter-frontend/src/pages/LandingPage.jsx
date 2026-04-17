import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

/**
 * LandingPage — Главная страница с hero-блоком, фичами и CTA
 * Анимированный particle-эффект на Canvas в качестве фона
 */
export default function LandingPage() {
    const canvasRef = useRef(null);

    // Particle background effect
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        let animId;
        let particles = [];

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener('resize', resize);

        // Создаём частицы
        const PARTICLE_COUNT = 60;
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                size: Math.random() * 2 + 1,
                color: Math.random() > 0.5 ? '#00BCD4' : '#FFD600',
                opacity: Math.random() * 0.5 + 0.1,
            });
        }

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach((p) => {
                // Двигаем
                p.x += p.vx;
                p.y += p.vy;

                // Заворачиваем
                if (p.x < 0) p.x = canvas.width;
                if (p.x > canvas.width) p.x = 0;
                if (p.y < 0) p.y = canvas.height;
                if (p.y > canvas.height) p.y = 0;

                // Рисуем
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = p.opacity;
                ctx.fill();
            });

            // Линии между близкими частицами
            ctx.globalAlpha = 1;
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 150) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = `rgba(0, 188, 212, ${0.08 * (1 - dist / 150)})`;
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                }
            }

            animId = requestAnimationFrame(draw);
        };
        draw();

        return () => {
            cancelAnimationFrame(animId);
            window.removeEventListener('resize', resize);
        };
    }, []);

    return (
        <div className="page">
            <section className="hero">
                {/* Canvas фон с частицами */}
                <canvas
                    ref={canvasRef}
                    className="hero-bg"
                    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
                />

                <div className="hero-content">
                    {/* Логотип — большой */}
                    <h1 className="hero-title animate-fade-in-up" style={{ opacity: 0 }}>
                        <span className="gradient-text">D</span>epter
                    </h1>

                    {/* Слоган */}
                    <p className="hero-subtitle animate-fade-in-up delay-1" style={{ opacity: 0 }}>
                        AI-скоринг финансовых выписок за минуты.
                        <br />
                        Загрузите PDF — получите кредитный рейтинг и рекомендованный лимит.
                    </p>

                    {/* CTA */}
                    <Link to="/register" className="btn btn-primary btn-lg animate-fade-in-up delay-2" style={{ opacity: 0 }}>
                        🚀 Начать скоринг
                    </Link>
                </div>

                {/* Feature Cards */}
                <div className="features-grid animate-fade-in-up delay-3" style={{ opacity: 0 }}>
                    <div className="glass-card feature-card">
                        <span className="feature-icon">🏦</span>
                        <h3 className="feature-title">Мультибанковский анализ</h3>
                        <p className="feature-desc">
                            Поддержка выписок mBank, Elsom, O!Dengi, Bakai и других банков Кыргызстана
                        </p>
                    </div>

                    <div className="glass-card feature-card">
                        <span className="feature-icon">🤖</span>
                        <h3 className="feature-title">AI-дедупликация</h3>
                        <p className="feature-desc">
                            Интеллектуальное удаление дублей между выписками разных банков
                        </p>
                    </div>

                    <div className="glass-card feature-card">
                        <span className="feature-icon">📊</span>
                        <h3 className="feature-title">Defter Score</h3>
                        <p className="feature-desc">
                            Кредитный рейтинг 0–1000 с рекомендованным лимитом за считанные секунды
                        </p>
                    </div>
                </div>
            </section>
        </div>
    );
}
