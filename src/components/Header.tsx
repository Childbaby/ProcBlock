"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/Logo";

export function Header() {
  const pathname = usePathname();

  const navItems = [
    { href: "/dashboard", label: "Overview" },
    { href: "/scanner", label: "Field Scanner" },
    { href: "/verify", label: "Public Verification" },
  ];

  return (
    <header className="bg-clinical-50 border-b border-clinical-300 shadow-medical sticky top-0 z-50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
        <div className="flex items-center justify-between h-18">
          <Link href="/" className="flex items-center gap-3">
            <Logo />
            <div>
              <h1 className="text-lg font-semibold text-navy-800 leading-tight">
                ProcBlock
              </h1>
              <p className="text-xs text-navy-400 leading-tight">
                ZAMMSA Portal
              </p>
            </div>
          </Link>

          <nav className="flex items-center gap-1" aria-label="Main navigation">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-4 py-2 rounded-medical text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-navy-800 text-clinical-50 shadow-medical"
                      : "text-navy-600 hover:bg-navy-50 hover:text-navy-800"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
