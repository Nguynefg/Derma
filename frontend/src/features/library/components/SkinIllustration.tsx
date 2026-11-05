import { useId } from 'react';
import {
  Activity,
  HeartPulse,
  Wind,
  Brain,
  Bone,
  Droplets,
  Ear,
  Utensils,
  Stethoscope,
} from 'lucide-react';

/** Original schematic illustration; never a patient photo or diagnostic reference. */
export function SkinIllustration({
  disease,
}: {
  disease: { slug?: string; category: string; name: string; specialty?: string };
}) {
  const id = useId();
  if (disease.specialty && disease.specialty !== 'Da liễu') {
    const icons: Record<string, typeof Activity> = {
      'Hô hấp': Wind,
      'Tiêu hóa': Utensils,
      'Tim mạch': HeartPulse,
      'Nội tiết': Activity,
      'Thần kinh': Brain,
      'Cơ xương khớp': Bone,
      'Thận & tiết niệu': Droplets,
      'Tai mũi họng': Ear,
    };
    const Icon = icons[disease.specialty] || Stethoscope;
    return (
      <div
        className="health-illustration"
        role="img"
        aria-label={'Biểu tượng chuyên khoa ' + disease.specialty}
      >
        <span>
          <Icon size={64} strokeWidth={1.4} />
        </span>
        <strong>{disease.specialty}</strong>
        <small>KIẾN THỨC SỨC KHỎE</small>
      </div>
    );
  }
  const key = `${disease.slug} ${disease.category}`.toLowerCase();
  const kind = /vitiligo/.test(key)
    ? 'pigment'
    : /tóc|rụng|alopecia/.test(key)
      ? 'hair'
      : /nấm|fungal|ringworm/.test(key)
        ? 'ring'
        : /mụn|acne|nang lông/.test(key)
          ? 'spots'
          : /vảy|psoriasis|viêm/.test(key)
            ? 'patch'
            : 'skin';
  return (
    <svg
      className={'skin-illustration ' + kind}
      viewBox="0 0 480 220"
      role="img"
      aria-label={'Minh họa sơ đồ cho chủ đề ' + disease.name}
    >
      <defs>
        <linearGradient id={id} x2="1" y2="1">
          <stop stopColor="#eee0ff" />
          <stop offset="1" stopColor="#d8e9e5" />
        </linearGradient>
      </defs>
      <rect width="480" height="220" rx="22" fill={`url(#${id})`} />
      <circle cx="405" cy="38" r="84" fill="white" opacity=".32" />
      <path d="M60 150C110 90 168 105 225 118S335 85 420 126V200H60Z" fill="#d9a5a7" />
      <path
        d="M60 150C110 90 168 105 225 118S335 85 420 126"
        fill="none"
        stroke="#a86c85"
        strokeWidth="5"
      />
      <path
        d="M60 175C160 140 215 175 300 160S390 159 420 160"
        fill="none"
        stroke="#f3ced0"
        strokeWidth="14"
      />
      {kind === 'pigment' && (
        <>
          <ellipse cx="180" cy="127" rx="42" ry="19" fill="#fff7f0" />
          <ellipse cx="300" cy="117" rx="29" ry="14" fill="#fff7f0" />
        </>
      )}
      {kind === 'ring' && (
        <ellipse
          cx="242"
          cy="123"
          rx="57"
          ry="29"
          fill="none"
          stroke="#b56079"
          strokeWidth="11"
          strokeDasharray="5 3"
        />
      )}
      {kind === 'spots' &&
        [135, 195, 253, 310, 355].map((x, i) => (
          <g key={x}>
            <circle cx={x} cy={121 + (i % 2) * 9} r={i % 2 ? 11 : 7} fill="#b75e7a" />
            <circle cx={x - 2} cy={118 + (i % 2) * 9} r="3" fill="#f3c0b6" />
          </g>
        ))}
      {kind === 'patch' && (
        <>
          <ellipse cx="230" cy="123" rx="63" ry="22" fill="#c17b93" />
          {[190, 210, 230, 250, 270].map((x) => (
            <path key={x} d={`M${x} 116l9 4m-7 7l8 3`} stroke="#fff0e9" strokeWidth="3" />
          ))}
        </>
      )}
      {kind === 'hair' &&
        [150, 210, 270, 330].map((x) => (
          <path
            key={x}
            d={`M${x} 164q-4-32 4-64t-10-44`}
            fill="none"
            stroke="#614364"
            strokeWidth="5"
          />
        ))}
      <rect x="22" y="20" width="100" height="26" rx="13" fill="#fff" opacity=".8" />
      <text x="72" y="37" textAnchor="middle" fill="#6f4889" fontSize="11" fontFamily="sans-serif">
        SƠ ĐỒ MINH HỌA
      </text>
      <circle cx="398" cy="176" r="17" fill="#fff" opacity=".65" />
      <path d="M391 176h14m-7-7v14" stroke="#8050aa" strokeWidth="2" />
    </svg>
  );
}
