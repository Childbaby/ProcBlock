export function Logo() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="ProcBlock Logo"
    >
      {/* Outer hexagon - represents blockchain */}
      <path
        d="M18 2L32 9.5V24.5L18 32L4 24.5V9.5L18 2Z"
        className="stroke-navy-800"
        strokeWidth="2"
        fill="none"
      />
      {/* Inner medical cross */}
      <rect
        x="15"
        y="10"
        width="6"
        height="16"
        rx="1"
        className="fill-teal-medical"
      />
      <rect
        x="10"
        y="15"
        width="16"
        height="6"
        rx="1"
        className="fill-teal-medical"
      />
    </svg>
  );
}
