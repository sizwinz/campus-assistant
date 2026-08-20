import { chatApi } from '../src/lib/api';

describe('chatApi', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockReset();
  });

  describe('sendMessage', () => {
    it('sends message to API and returns response', async () => {
      const mockResponse = {
        response: 'Hello! How can I help you?',
        session_id: 'test-session-123',
        detected_language: 'en',
        confidence: 85,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await chatApi.sendMessage('Hello', 'session-123', 'en');

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chat',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('Hello'),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('throws error on API failure', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      });

      await expect(chatApi.sendMessage('Hello')).rejects.toThrow('API error');
    });

    it('includes backend status and detail in API errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: async () => ({ detail: 'Rate limit exceeded' }),
      });

      await expect(chatApi.sendMessage('Hello')).rejects.toThrow(
        'API error 429: Rate limit exceeded'
      );
    });

    it('includes session_id when provided', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: 'OK' }),
      });

      await chatApi.sendMessage('Hello', 'my-session');

      const callBody = JSON.parse(
        (global.fetch as jest.Mock).mock.calls[0][1].body
      );
      expect(callBody.session_id).toBe('my-session');
    });

    it('includes language when provided', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: 'OK' }),
      });

      await chatApi.sendMessage('Hello', undefined, 'hi');

      const callBody = JSON.parse(
        (global.fetch as jest.Mock).mock.calls[0][1].body
      );
      expect(callBody.language).toBe('hi');
    });
  });
});
