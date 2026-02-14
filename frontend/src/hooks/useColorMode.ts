import { useState, useEffect, useCallback } from 'react';

type ColorMode = 'light' | 'dark';

function getInitialMode(): ColorMode {
  const stored = localStorage.getItem('smia-color-mode') as ColorMode | null;
  if (stored) return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

function applyMode(mode: ColorMode) {
  document.documentElement.classList.toggle('dark', mode === 'dark');
  document.documentElement.style.colorScheme = mode;
}

export function useColorMode() {
  const [colorMode, setColorMode] = useState<ColorMode>(getInitialMode);

  useEffect(() => {
    applyMode(colorMode);
    localStorage.setItem('smia-color-mode', colorMode);
  }, [colorMode]);

  const toggleColorMode = useCallback(() => {
    setColorMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { colorMode, toggleColorMode, setColorMode };
}
