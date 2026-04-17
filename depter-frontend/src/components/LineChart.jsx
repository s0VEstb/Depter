import { useEffect, useState } from 'react';

/**
 * LineChart — SVG line chart для динамики доходов по месяцам
 * @param {Object} data — { "2025-10": 82000, "2025-11": 88000, ... }
 * @param {number} [width=600]
 * @param {number} [height=300]
 */
export default function LineChart({ data = {}, width = 600, height = 300 }) {
    const [animProgress, setAnimProgress] = useState(0);

    useEffect(() => {
        const startTime = performance.now();
        const duration = 1200;
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

    const values = entries.map(([, v]) => v);
    const maxVal = Math.max(...values) * 1.1;
    const minVal = Math.min(...values) * 0.9;
    const range = maxVal - minVal || 1;

    const padding = { top: 30, right: 30, bottom: 50, left: 70 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Координаты точек
    const points = entries.map(([label, value], i) => ({
        x: padding.left + (i / Math.max(entries.length - 1, 1)) * chartW,
        y: padding.top + chartH - ((value - minVal) / range) * chartH,
        label,
        value,
    }));

    // Polyline path
    const linePath = points
        .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
        .join(' ');

    // Area path (для заливки под линией)
    const areaPath =
        linePath +
        ` L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

    // Y тики
    const tickCount = 5;
    const yTicks = Array.from({ length: tickCount + 1 }, (_, i) =>
        Math.round(minVal + (range / tickCount) * i)
    );

    const formatNum = (n) =>
        n >= 1000 ? `${Math.round(n / 1000)}K` : String(n);

    // Форматирование месяца
    const formatMonth = (m) => {
        const parts = m.split('-');
        const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];
        return months[parseInt(parts[1], 10) - 1] || m;
    };

    // Длина линии для анимации
    const totalLen = points.reduce((acc, p, i) => {
        if (i === 0) return 0;
        const prev = points[i - 1];
        return acc + Math.sqrt((p.x - prev.x) ** 2 + (p.y - prev.y) ** 2);
    }, 0);

    return (
        <svg
            width="100%"
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="xMidYMid meet"
        >
            <defs>
                {/* Cyan gradient для линии */}
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#00BCD4" />
                    <stop offset="100%" stopColor="#FFD600" />
                </linearGradient>

                {/* Area fill gradient */}
                <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="#00BCD4" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="#00BCD4" stopOpacity="0.01" />
                </linearGradient>

                {/* Glow filter */}
                <filter id="lineGlow">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>

            {/* Y-axis сетка */}
            {yTicks.map((tick, i) => {
                const y = padding.top + chartH - ((tick - minVal) / range) * chartH;
                return (
                    <g key={`ytick-${i}`}>
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

            {/* Область под линией */}
            <path d={areaPath} fill="url(#areaGradient)" opacity={animProgress} />

            {/* Основная линия */}
            <path
                d={linePath}
                fill="none"
                stroke="url(#lineGradient)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                filter="url(#lineGlow)"
                strokeDasharray={totalLen}
                strokeDashoffset={totalLen * (1 - animProgress)}
                style={{ transition: 'stroke-dashoffset 0.05s linear' }}
            />

            {/* Точки на графике */}
            {points.map((p, i) => (
                <g key={`point-${i}`} opacity={animProgress > (i / points.length) ? 1 : 0}>
                    {/* Glow circle */}
                    <circle cx={p.x} cy={p.y} r="8" fill="#00BCD4" opacity="0.15" />
                    {/* Dot */}
                    <circle cx={p.x} cy={p.y} r="4" fill="#00BCD4" stroke="#000" strokeWidth="2" />

                    {/* Value label */}
                    <text
                        x={p.x}
                        y={p.y - 14}
                        textAnchor="middle"
                        fill="#FEFEFE"
                        fontSize="11"
                        fontWeight="600"
                        fontFamily="Inter, sans-serif"
                    >
                        {formatNum(p.value)}
                    </text>

                    {/* Month label */}
                    <text
                        x={p.x}
                        y={height - padding.bottom + 20}
                        textAnchor="middle"
                        fill="#8C8C8C"
                        fontSize="11"
                        fontFamily="Inter, sans-serif"
                    >
                        {formatMonth(p.label)}
                    </text>
                </g>
            ))}
        </svg>
    );
}
