import { useEffect, useState } from 'react';

/**
 * BarChart — SVG bar chart для дохода по источникам
 * @param {Object} data — { "mbank": 60000, "elsom": 25000 }
 * @param {number} [width=500]
 * @param {number} [height=280]
 */
export default function BarChart({ data = {}, width = 500, height = 280 }) {
    const [animProgress, setAnimProgress] = useState(0);

    useEffect(() => {
        const startTime = performance.now();
        const duration = 1000;
        let raf;

        const animate = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setAnimProgress(eased);
            if (progress < 1) {
                raf = requestAnimationFrame(animate);
            }
        };

        raf = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(raf);
    }, [data]);

    const entries = Object.entries(data);
    if (entries.length === 0) return null;

    const maxVal = Math.max(...entries.map(([, v]) => v));
    const padding = { top: 20, right: 20, bottom: 50, left: 70 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const barWidth = Math.min(60, (chartW / entries.length) * 0.6);
    const gap = (chartW - barWidth * entries.length) / (entries.length + 1);

    // Цвета — градиент от cyan до yellow
    const barColors = ['#00BCD4', '#26C6DA', '#4DD0E1', '#FFD600', '#FFEB3B'];

    // Формат числа
    const formatNum = (n) =>
        n >= 1000 ? `${Math.round(n / 1000)}K` : String(n);

    // Y-axis тики
    const tickCount = 5;
    const yTicks = Array.from({ length: tickCount + 1 }, (_, i) =>
        Math.round((maxVal / tickCount) * i)
    );

    return (
        <svg
            width="100%"
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="xMidYMid meet"
        >
            {/* Y-axis линии и лейблы */}
            {yTicks.map((tick, i) => {
                const y = padding.top + chartH - (tick / maxVal) * chartH;
                return (
                    <g key={`tick-${i}`}>
                        <line
                            x1={padding.left}
                            y1={y}
                            x2={padding.left + chartW}
                            y2={y}
                            stroke="rgba(255,255,255,0.06)"
                            strokeDasharray="4 4"
                        />
                        <text
                            x={padding.left - 10}
                            y={y + 4}
                            textAnchor="end"
                            fill="#8C8C8C"
                            fontSize="11"
                            fontFamily="Inter, sans-serif"
                        >
                            {formatNum(tick)}
                        </text>
                    </g>
                );
            })}

            {/* Bars */}
            {entries.map(([label, value], i) => {
                const x = padding.left + gap * (i + 1) + barWidth * i;
                const barH = (value / maxVal) * chartH * animProgress;
                const y = padding.top + chartH - barH;
                const color = barColors[i % barColors.length];

                return (
                    <g key={label}>
                        {/* Glow effect */}
                        <rect
                            x={x - 2}
                            y={y - 2}
                            width={barWidth + 4}
                            height={barH + 4}
                            rx="6"
                            fill="none"
                            stroke={color}
                            strokeOpacity="0.2"
                            filter="url(#barGlow)"
                        />
                        {/* Бар */}
                        <rect
                            x={x}
                            y={y}
                            width={barWidth}
                            height={barH}
                            rx="4"
                            fill={color}
                            opacity="0.9"
                        />
                        {/* Значение сверху */}
                        <text
                            x={x + barWidth / 2}
                            y={y - 8}
                            textAnchor="middle"
                            fill={color}
                            fontSize="12"
                            fontWeight="600"
                            fontFamily="Inter, sans-serif"
                            opacity={animProgress}
                        >
                            {formatNum(value)}
                        </text>
                        {/* Подпись снизу */}
                        <text
                            x={x + barWidth / 2}
                            y={height - padding.bottom + 20}
                            textAnchor="middle"
                            fill="#FEFEFE"
                            fontSize="12"
                            fontWeight="600"
                            fontFamily="Inter, sans-serif"
                        >
                            {label}
                        </text>
                    </g>
                );
            })}

            <defs>
                <filter id="barGlow">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>
        </svg>
    );
}
