import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useEffect } from 'react';
import ChatInterface from '../src/components/ChatInterface';
import { LanguageProvider, useLanguage } from '../src/hooks/useLanguage';

const sendMessage = jest.fn();

jest.mock('@/hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    isLoading: false,
    sendMessage,
    suggestions: [],
  }),
}));

function SelectHindi() {
  const { setLanguage } = useLanguage();

  useEffect(() => {
    setLanguage('hi');
  }, [setLanguage]);

  return null;
}

describe('ChatInterface', () => {
  beforeEach(() => {
    sendMessage.mockReset();
    window.localStorage.clear();
  });

  it('sends the shared selected language with chat messages', async () => {
    render(
      <LanguageProvider>
        <SelectHindi />
        <ChatInterface />
      </LanguageProvider>
    );

    fireEvent.change(screen.getByLabelText('Type your question'), {
      target: { value: 'fees' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith('fees', 'hi');
    });
  });
});
