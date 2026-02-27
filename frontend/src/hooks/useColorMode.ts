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

  const toggleColorMode = useCallback((e?: React.MouseEvent) => {
    const x = e?.clientX ?? window.innerWidth / 2;
    const y = e?.clientY ?? window.innerHeight / 2;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y),
    );

    document.documentElement.style.setProperty('--toggle-x', `${x}px`);
    document.documentElement.style.setProperty('--toggle-y', `${y}px`);
    document.documentElement.style.setProperty('--toggle-end-radius', `${endRadius}px`);

    const doToggle = () => setColorMode((prev) => (prev === 'dark' ? 'light' : 'dark'));

    if (!document.startViewTransition) {
      doToggle();
      return;
    }

    document.startViewTransition(doToggle);
  }, []);

  return { colorMode, toggleColorMode, setColorMode };
}
