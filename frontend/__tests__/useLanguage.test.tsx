import { render, screen, fireEvent } from '@testing-library/react';
import { LanguageProvider, useLanguage } from '../src/hooks/useLanguage';

function LanguageReader({ label }: { label: string }) {
  const { language, setLanguage } = useLanguage();

  return (
    <button onClick={() => setLanguage('hi')}>
      {label}:{language}
    </button>
  );
}

describe('LanguageProvider', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('shares selected language across hook consumers', () => {
    render(
      <LanguageProvider>
        <LanguageReader label="header" />
        <LanguageReader label="chat" />
      </LanguageProvider>
    );

    fireEvent.click(screen.getByText('header:en'));

    expect(screen.getByText('header:hi')).toBeInTheDocument();
    expect(screen.getByText('chat:hi')).toBeInTheDocument();
    expect(window.localStorage.getItem('campus-assistant-language')).toBe('hi');
  });
});
