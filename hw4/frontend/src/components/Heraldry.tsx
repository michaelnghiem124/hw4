import { API_BASE } from '../lib/api';

/**
 * Heritage marks.
 *
 * The crest and pennant are SVG rather than image files on purpose: vector means
 * the crest is crisp at 24px in the nav and 104px in the hero from one source.
 *
 * Handsome Dan is the exception — he's a real photograph, served from the
 * backend's `/static` mount over `data/`, exactly like the 102 catalogue
 * images. That keeps the repo free of binary art (`data/` is never committed)
 * while giving the mascot a real face instead of a drawing.
 */

/** Campus Customs shield — brass hairline, CC monogram, laurel, 1701 banner. */
export function CrestMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 150"
      role="img"
      aria-label="Campus Customs crest"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M10 12h100v70c0 30-22 48-50 56C32 130 10 112 10 82V12Z"
        fill="currentColor"
        fillOpacity="0.1"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <path
        d="M19 21h82v60c0 25-18 40-41 47-23-7-41-22-41-47V21Z"
        stroke="currentColor"
        strokeWidth="1"
        strokeOpacity="0.55"
      />
      {/* Chief: a row of five pennants, one per residential-college band. */}
      <path d="M19 42h82" stroke="currentColor" strokeWidth="1" strokeOpacity="0.45" />
      {[0, 1, 2, 3, 4].map((i) => (
        <path
          key={i}
          d={`M${26 + i * 14} 28h10l-5 9Z`}
          fill="currentColor"
          fillOpacity="0.75"
        />
      ))}
      <text
        x="60"
        y="86"
        textAnchor="middle"
        fontFamily="'Bodoni Moda', Georgia, serif"
        fontSize="38"
        fontWeight="700"
        letterSpacing="-1"
        fill="currentColor"
      >
        CC
      </text>
      {/* Laurel sprigs flanking the monogram. */}
      <g stroke="currentColor" strokeWidth="1.4" strokeOpacity="0.7" strokeLinecap="round">
        <path d="M28 96c6 4 10 9 12 15" />
        <path d="M92 96c-6 4-10 9-12 15" />
      </g>
      <path d="M40 103h40" stroke="currentColor" strokeWidth="1" strokeOpacity="0.45" />
      <text
        x="60"
        y="118"
        textAnchor="middle"
        fontFamily="Oswald, 'Arial Narrow', sans-serif"
        fontSize="11"
        letterSpacing="3"
        fill="currentColor"
        fillOpacity="0.85"
      >
        NEW HAVEN
      </text>
      {/* Banner under the shield point. */}
      <path
        d="M4 128h112l-10 11H14Z"
        fill="currentColor"
        fillOpacity="0.14"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <text
        x="60"
        y="136.5"
        textAnchor="middle"
        fontFamily="Oswald, 'Arial Narrow', sans-serif"
        fontSize="8.5"
        letterSpacing="3.5"
        fill="currentColor"
      >
        WORN WELL
      </text>
    </svg>
  );
}

/** The real Handsome Dan, in a Yale sweater. */
const DAN_PHOTO = `${API_BASE}/static/${encodeURIComponent('Handsome Dan.jpeg')}`;

/**
 * Handsome Dan's portrait.
 *
 * `crop` tightens the framing to his face — the source is a full-body 3:4
 * portrait, which is unreadable once it's scaled down to a 32px chat avatar.
 * The crop is done with transform-origin/scale in CSS (`.dan-photo-crop`)
 * rather than a second image file.
 */
export function BulldogPhoto({
  className,
  crop = false,
}: {
  className?: string;
  crop?: boolean;
}) {
  return (
    <img
      className={`dan-photo${crop ? ' dan-photo-crop' : ''}${className ? ` ${className}` : ''}`}
      src={DAN_PHOTO}
      alt="Handsome Dan, Yale's bulldog, wearing a Yale sweater"
      loading="lazy"
    />
  );
}

/** A small pennant used as a bullet/divider accent. */
export function PennantMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 16"
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M0 0h24l-8 8 8 8H0Z" fill="currentColor" />
    </svg>
  );
}
