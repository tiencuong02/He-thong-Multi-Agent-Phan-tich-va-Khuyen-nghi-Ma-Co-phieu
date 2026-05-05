import React from 'react';

const STARS = Array.from({ length: 85 }, (_, i) => ({
  id: i,
  left: `${((Math.sin(i * 137.508) + 1) / 2 * 100).toFixed(2)}%`,
  top: `${((Math.cos(i * 97.351) + 1) / 2 * 62).toFixed(2)}%`,
  size: `${(Math.abs(Math.sin(i * 23.71)) * 2 + 1).toFixed(1)}px`,
  opacity: +(Math.abs(Math.cos(i * 41.3)) * 0.6 + 0.3).toFixed(2),
  delay: `${(i * 0.17 % 4).toFixed(2)}s`,
}));

const BACK_TREES = Array.from({ length: 22 }, (_, i) => ({
  id: i,
  x: i * 72 + (i % 2) * 14,
  h: 58 + (i % 3) * 22,
  w: 68 + (i % 2) * 20,
  base: 230,
}));

const FRONT_TREES = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  x: i * 78 + 35 + (i % 3) * 10,
  h: 98 + (i % 4) * 24,
  w: 84 + (i % 3) * 16,
  base: 265,
}));

const AuthBackground = () => (
  <>
    <div className="lp-stars" aria-hidden="true">
      {STARS.map(s => (
        <div
          key={s.id}
          className="lp-star"
          style={{
            left: s.left,
            top: s.top,
            width: s.size,
            height: s.size,
            opacity: s.opacity,
            animationDelay: s.delay,
          }}
        />
      ))}
    </div>

    <svg
      className="lp-forest"
      viewBox="0 0 1520 300"
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        fill="#170840"
        d="M0 300 L0 210 C130 168 300 192 460 180 C620 165 780 188 940 172 C1100 156 1260 178 1420 168 L1520 172 L1520 300 Z"
      />
      {BACK_TREES.map(t => (
        <polygon
          key={`bt${t.id}`}
          fill="#0d0428"
          points={`${t.x + t.w / 2},${t.base - t.h} ${t.x},${t.base} ${t.x + t.w},${t.base}`}
        />
      ))}
      {FRONT_TREES.map(t => (
        <g key={`ft${t.id}`}>
          <polygon
            fill="#07021a"
            points={`${t.x + t.w / 2},${t.base - t.h} ${t.x},${t.base} ${t.x + t.w},${t.base}`}
          />
          <polygon
            fill="#07021a"
            points={`${t.x + t.w / 2},${t.base - t.h * 0.56} ${t.x - 10},${t.base - 9} ${t.x + t.w + 10},${t.base - 9}`}
          />
        </g>
      ))}
      <rect fill="#040112" x="0" y="263" width="1520" height="37" />
    </svg>
  </>
);

export default AuthBackground;
