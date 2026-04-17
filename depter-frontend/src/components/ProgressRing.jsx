import { useEffect, useState, useRef } from 'react';

/**
 * ProgressRing — круговой SVG-прогресс для страницы обработки
 * @param {number} progress — 0–100
 * @param {number} [size=200]
 */
export default function ProgressRing({ progress = 0, size = 200 }) {
    const [animatedVal, setAnimatedVal] = useState(0);
    const animRef = useRef(null);
    const prevProgress = useRef(0);

    useEffect(() => {
        const start = prevProgress.current;
        const end = progress;
        const startTime = performance.now();
        const duration = 600;

        const animate = (now) => {
            const elapsed = now - startTime;
            const t = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - t, 3);
            setAnimatedVal(Math.round(start + (end - start) * eased));

            if (t < 1) {
                animRef.current = requestAnimationFrame(animate);
            } else {
                prevProgress.current = end;
            }
        };

        animRef.current = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animRef.current);
    }, [progress]);

    const cx = size / 2;
    const cy = size / 2;
    const strokeWidth = 10;
    const radius = (size - strokeWidth * 2) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (animatedVal / 100) * circumference;

    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            <defs>
                <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00BCD4" />
                    <stop offset="100%" stopColor="#FFD600" />
                </linearGradient>
                <filter id="ringGlow">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>

            {/* Фоновое кольцо */}
            <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.06)"
                strokeWidth={strokeWidth}
            />

            {/* Прогресс-кольцо */}
            <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke="url(#ringGrad)"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                transform={`rotate(-90 ${cx} ${cy})`}
                filter="url(#ringGlow)"
                style={{ transition: 'stroke-dashoffset 0.1s ease' }}
            />

            {/* Процент в центре */}
            <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#FEFEFE"
                fontSize={size * 0.2}
                fontWeight="700"
                fontFamily="Inter, sans-serif"
            >
                {animatedVal}%
            </text>
        </svg>
    );
}
