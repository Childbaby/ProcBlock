// Global type declarations

declare module '*.svg' {
  import { FC, SVGProps } from 'react'
  const content: FC<SVGProps<SVGSVGElement>>
  export default content
}

declare module '*.png' {
  const content: string
  export default content
}

// Extend Window for any custom globals
interface Window {
  // Add any custom window properties here
}