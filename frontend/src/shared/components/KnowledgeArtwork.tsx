import { BookOpen, HeartPulse, Sparkles } from 'lucide-react';

/** Decorative book sculpture; no medical findings or claims are illustrated. */
export function KnowledgeArtwork() {
  return (
    <div className="knowledge-scene" aria-hidden="true">
      <svg className="knowledge-sculpture" viewBox="0 0 560 430" fill="none">
        <defs>
          <linearGradient
            id="atlas-cover"
            x1="160"
            y1="70"
            x2="400"
            y2="360"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#e1f6d5" />
            <stop offset="1" stopColor="#8ac9ad" />
          </linearGradient>
          <linearGradient
            id="atlas-pages"
            x1="180"
            y1="290"
            x2="395"
            y2="350"
            gradientUnits="userSpaceOnUse"
          >
            <stop stopColor="#fffdf0" />
            <stop offset="1" stopColor="#b8cec0" />
          </linearGradient>
          <radialGradient id="atlas-glow">
            <stop stopColor="#a6d6bf" stopOpacity=".28" />
            <stop offset="1" stopColor="#a6d6bf" stopOpacity="0" />
          </radialGradient>
          <filter id="atlas-shadow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="18" />
          </filter>
        </defs>
        <ellipse cx="300" cy="234" rx="235" ry="194" fill="url(#atlas-glow)" />
        <ellipse
          cx="284"
          cy="326"
          rx="148"
          ry="32"
          fill="#0d0724"
          opacity=".35"
          filter="url(#atlas-shadow)"
        />
        <ellipse
          cx="287"
          cy="224"
          rx="221"
          ry="119"
          stroke="#d7f8da"
          strokeOpacity=".17"
          transform="rotate(-24 287 224)"
        />
        <ellipse
          cx="287"
          cy="224"
          rx="188"
          ry="166"
          stroke="#d7f8da"
          strokeOpacity=".12"
          strokeDasharray="3 9"
        />
        <g transform="rotate(-14 280 220)">
          <path
            d="M178 99L370 70Q391 67 395 88L425 306Q428 326 409 331L212 362L180 338Z"
            fill="#6c9e88"
          />
          <path d="M193 318L404 286L410 319L212 350Q199 351 193 340Z" fill="url(#atlas-pages)" />
          <path
            d="M205 327L400 298M207 335L401 306M209 343L402 314"
            stroke="#648e7c"
            strokeOpacity=".4"
          />
          <path
            d="M161 87Q159 72 178 69L369 40Q386 37 389 55L421 282Q423 298 407 301L207 333Q190 336 185 317Z"
            fill="url(#atlas-cover)"
          />
          <path d="M180 69L215 331" stroke="#659a80" strokeWidth="6" />
          <path d="M190 72L223 324" stroke="#f0ffe4" strokeOpacity=".45" />
          <path d="M218 109L341 90" stroke="#356e5a" strokeOpacity=".35" />
          <path
            d="M247 145Q267 131 289 140L297 191Q274 183 255 198Z"
            stroke="#326c57"
            strokeWidth="3"
          />
          <path
            d="M289 140Q307 126 328 132L337 183Q317 177 297 191Z"
            stroke="#326c57"
            strokeWidth="3"
          />
          <path
            d="M267 153L280 151M269 164L282 162M303 147L317 145M305 158L319 156"
            stroke="#326c57"
            strokeWidth="2"
          />
          <text
            x="229"
            y="236"
            fill="#235342"
            fontSize="28"
            fontWeight="600"
            fontFamily="'Be Vietnam Pro',sans-serif"
          >
            Sức khỏe.
          </text>
          <text
            x="234"
            y="269"
            fill="#235342"
            fontSize="28"
            fontWeight="600"
            fontFamily="'Be Vietnam Pro',sans-serif"
          >
            Hiểu thêm.
          </text>
          <path d="M324 47L344 44L355 121L343 113L335 124Z" fill="#8d6fb4" />
          <path d="M241 299L301 290" stroke="#356e5a" strokeOpacity=".5" />
        </g>
        <circle cx="103" cy="172" r="5" fill="#d2edb0" />
        <circle cx="465" cy="235" r="4" fill="#c4a5ea" />
        <path
          d="M426 82V98M418 90H434M119 304V316M113 310H125"
          stroke="#d2edb0"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>
      <span className="sculpture-tag tag-pulse">
        <HeartPulse size={25} />
      </span>
      <span className="sculpture-tag tag-spark">
        <Sparkles size={23} />
      </span>
      <div className="knowledge-note">
        <span>
          <BookOpen size={21} />
        </span>
        <div>
          <strong>Mỗi lần đọc, thêm một góc nhìn.</strong>
          <small>Khám phá kiến thức theo nhịp của bạn.</small>
        </div>
      </div>
    </div>
  );
}
