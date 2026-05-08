"use client";

import { useState, FormEvent } from "react";

interface LoginFormProps {
  onSubmit: (credentials: { username: string; password: string }) => void;
  isLoading?: boolean;
}

export function LoginForm({ onSubmit, isLoading = false }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({ username, password });
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="clinical-card">
        <div className="text-center mb-8">
          <h2 className="text-display-sm text-navy-800 mb-2">
            ZAMMSA Portal Access
          </h2>
          <p className="text-sm text-navy-500">
            Secure login for authorized personnel only
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-navy-700 mb-1.5"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-clinical"
              placeholder="Enter your username"
              autoComplete="username"
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-navy-700 mb-1.5"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-clinical"
              placeholder="Enter your password"
              autoComplete="current-password"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Authenticating...
              </>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-clinical-300">
          <p className="text-xs text-navy-400 text-center">
            This is a restricted system. All access is logged and monitored.
          </p>
        </div>
      </div>
    </div>
  );
}
