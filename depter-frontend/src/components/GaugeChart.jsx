import { useEffect, useRef, useState } from 'react';

/**
 * GaugeChart — анимированный дуговой индикатор для Defter Score
 * @param {number} score — значение 0–1000
 * @param {number} [size=240] — размер SVG
 */
export default function GaugeChart({ score = 0, size = 240 }) {
    const [animatedScore, setAnimatedScore] = useState(0);
    const animRef = useRef(null);

    // Цвет по уровню скора
    const getColor = (val) => {
        if (val <= 400) return '#F44336';      // красный — плохой
        if (val <= 650) return '#FFD600';      // жёлтый — средний
        if (val <= 850) return '#4CAF50';      // зелёный — хороший
        return '#00BCD4';                      // бирюзовый — отличный
    };

    // Анимация при загрузке
    useEffect(() => {
        const startTime = performance.now();
        const duration = 1500;

        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // easeOutCubic
            const eased = 1 - Math.pow(1 - progress, 3);
            setAnimatedScore(Math.round(eased * score));

            if (progress < 1) {
                animRef.current = requestAnimationFrame(animate);
            }
        };

        animRef.current = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animRef.current);
    }, [score]);

    const cx = size / 2;
    const cy = size / 2;
    const strokeWidth = 14;
    const radius = (size - strokeWidth * 2) / 2;

    // Дуга от 135° до 405° (270° всего)
    const startAngle = 135;
    const endAngle = 405;
    const totalAngle = endAngle - startAngle; // 270°
    const scoreAngle = startAngle + (animatedScore / 1000) * totalAngle;

    const toRadians = (deg) => (deg * Math.PI) / 180;

    const describeArc = (startDeg, endDeg) => {
        const startRad = toRadians(startDeg);
        const endRad = toRadians(endDeg);
        const x1 = cx + radius * Math.cos(startRad);
        const y1 = cy + radius * Math.sin(startRad);
        const x2 = cx + radius * Math.cos(endRad);
        const y2 = cy + radius * Math.sin(endRad);
        const largeArc = endDeg - startDeg > 180 ? 1 : 0;
        return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
    };

    const color = getColor(animatedScore);

    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {/* Фоновая дуга */}
            <path
                d={describeArc(startAngle, endAngle)}
                fill="none"
                stroke="rgba(255,255,255,0.07)"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
            />

            {/* Активная дуга */}
            {animatedScore > 0 && (
                <path
                    d={describeArc(startAngle, scoreAngle)}
                    fill="none"
                    stroke={color}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    style={{
                        filter: `drop-shadow(0 0 8px ${color}80)`,
                    }}
                />
            )}

            {/* Градиентные точки на шкале */}
            <defs>
                <radialGradient id="glowGauge">
                    <stop offset="0%" stopColor={color} stopOpacity="0.6" />
                    <stop offset="100%" stopColor={color} stopOpacity="0" />
                </radialGradient>
            </defs>

            {/* Число в центре */}
            <text
                x={cx}
                y={cy - 10}
                textAnchor="middle"
                dominantBaseline="central"
                fill={color}
                fontSize={size * 0.22}
                fontWeight="700"
                fontFamily="Inter, sans-serif"
            >
                {animatedScore}
            </text>

            {/* Подпись */}
            <text
                x={cx}
                y={cy + size * 0.12}
                textAnchor="middle"
                fill="#8C8C8C"
                fontSize={size * 0.055}
                fontWeight="600"
                fontFamily="Inter, sans-serif"
            >
                Defter Score
            </text>

            {/* Минимум и максимум */}
            <text
                x={cx - radius * 0.75}
                y={cy + radius * 0.8}
                textAnchor="middle"
                fill="#8C8C8C"
                fontSize="12"
                fontFamily="Inter, sans-serif"
            >
                0
            </text>
            <text
                x={cx + radius * 0.75}
                y={cy + radius * 0.8}
                textAnchor="middle"
                fill="#8C8C8C"
                fontSize="12"
                fontFamily="Inter, sans-serif"
            >
                1000
            </text>
        </svg>
    );
}
