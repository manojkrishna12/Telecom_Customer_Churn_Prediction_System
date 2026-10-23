// Lightweight inline SVG icon set (stroke style, 24px grid).
// Kept dependency-free on purpose: the project adds no npm packages for icons.

function Svg({ children, size = 20, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  )
}

export const AntennaIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="10.5" r="1.6" fill="currentColor" stroke="none" />
    <path d="M10.2 21.5 12 13.8l1.8 7.7" />
    <path d="M9 5.9a4.6 4.6 0 0 0 0 9.2" />
    <path d="M15 5.9a4.6 4.6 0 0 1 0 9.2" />
    <path d="M6.6 3.6a8 8 0 0 0 0 13.8" />
    <path d="M17.4 3.6a8 8 0 0 1 0 13.8" />
  </Svg>
)

export const UserIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="8" r="3.4" />
    <path d="M5.5 20a6.5 6.5 0 0 1 13 0" />
  </Svg>
)

export const UserPercentIcon = (p) => (
  <Svg {...p}>
    <circle cx="9.8" cy="7.6" r="3.2" />
    <path d="M3.8 20a6 6 0 0 1 8.9-5.2" />
    <path d="M15.2 20.6 20.8 13.4" />
    <circle cx="16" cy="19.2" r="1.2" />
    <circle cx="20" cy="14.8" r="1.2" />
  </Svg>
)

export const GearIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="3.1" />
    <path d="M12 3.2v2.4M12 18.4v2.4M3.2 12h2.4M18.4 12h2.4M5.8 5.8l1.7 1.7M16.5 16.5l1.7 1.7M18.2 5.8l-1.7 1.7M7.5 16.5l-1.7 1.7" />
  </Svg>
)

export const CardIcon = (p) => (
  <Svg {...p}>
    <rect x="2.8" y="5.2" width="18.4" height="13.6" rx="2.4" />
    <path d="M2.8 9.8h18.4" />
  </Svg>
)

export const ChartIcon = (p) => (
  <Svg strokeWidth="2.4" {...p}>
    <path d="M5.5 20v-7" />
    <path d="M12 20V5.5" />
    <path d="M18.5 20v-10.5" />
  </Svg>
)

export const ChevronIcon = (p) => (
  <Svg {...p}>
    <path d="M6 14.8l6-6 6 6" />
  </Svg>
)

export const HomeIcon = (p) => (
  <Svg {...p}>
    <path d="M4 10.8 12 4l8 6.8" />
    <path d="M6 9.5V20h12V9.5" />
  </Svg>
)

export const InfoIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="8.6" />
    <path d="M12 11.2v5" />
    <path d="M12 7.6h.01" />
  </Svg>
)

export const DocIcon = (p) => (
  <Svg {...p}>
    <path d="M14 3H7a1.6 1.6 0 0 0-1.6 1.6v14.8A1.6 1.6 0 0 0 7 21h10a1.6 1.6 0 0 0 1.6-1.6V7.6z" />
    <path d="M14 3v4.6h4.6" />
    <path d="M9 12.5h6" />
    <path d="M9 16h6" />
  </Svg>
)

export const CheckIcon = (p) => (
  <Svg strokeWidth="2.6" {...p}>
    <path d="M5 12.8l4.3 4.3L19 7.5" />
  </Svg>
)

export const AlertTriangleIcon = (p) => (
  <Svg {...p}>
    <path d="M12 4.2 20.8 19.4H3.2z" />
    <path d="M12 10v4.2" />
    <path d="M12 17.1h.01" />
  </Svg>
)

export const BoltIcon = (p) => (
  <Svg {...p}>
    <path d="M13.2 2.6 5 13.4h5.4L9.8 21.4 18 10.6h-5.4z" fill="currentColor" stroke="none" />
  </Svg>
)

export const ShieldIcon = (p) => (
  <Svg {...p}>
    <path d="M12 3.2 19 6v5.3c0 4.5-2.9 7.4-7 9-4.1-1.6-7-4.5-7-9V6z" />
    <path d="M9.2 11.6l2 2 3.8-3.8" />
  </Svg>
)

export const NoteIcon = (p) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9.5" fill="currentColor" stroke="none" />
    <path d="M12 10.8v5.4" stroke="#fff" strokeWidth="2.2" />
    <circle cx="12" cy="7.6" r="1.15" fill="#fff" stroke="none" />
  </Svg>
)
