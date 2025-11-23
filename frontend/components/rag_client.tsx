/**
 * RAG Chat Client Components for AgriGuard
 * Integrates with RAG service for intelligent agricultural chatbot
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface AgriContextData {
  county?: string;
  week?: number;
  year?: number;
  csi_overall?: number;
  water_stress?: number;
  heat_stress?: number;
  vegetation_health?: number;
  atmospheric_stress?: number;
  predicted_yield?: number;
  yield_uncertainty?: number;
  recommendations?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{
    text: string;
    score: number;
  }>;
}

interface RAGResponse {
  response: string;
  retrieved_contexts: Array<{
    text: string;
    score: number;
    source?: string;
  }>;
  model: string;
  timestamp: string;
  context_used: boolean;
}

interface RAGHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  chroma_connected: boolean;
  gemini_configured: boolean;
  collection_count: number;
  timestamp: string;
}

// ============================================================================
// CUSTOM HOOKS
// ============================================================================

/**
 * Hook for RAG chat functionality
 */
const useRAGChat = (ragServiceUrl: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (
      query: string,
      agriContext?: AgriContextData,
      includeContext = true
    ): Promise<void> => {
      if (!query.trim()) return;

      setLoading(true);
      setError(null);

      try {
        // Add user message to history
        const userMessage: ChatMessage = {
          role: 'user',
          content: query,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);

        // Call RAG service
        const response = await fetch(`${ragServiceUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            county: agriContext?.county,
            week: agriContext?.week,
            year: agriContext?.year,
            include_context: includeContext,
            agri_context: agriContext,
          }),
        });

        if (!response.ok) {
          throw new Error(`RAG API error: ${response.status}`);
        }

        const data: RAGResponse = await response.json();

        // Add assistant message to history
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: data.response,
          timestamp: data.timestamp,
          sources: data.retrieved_contexts,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('RAG chat error:', err);
      } finally {
        setLoading(false);
      }
    },
    [ragServiceUrl]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    loading,
    error,
    sendMessage,
    clearMessages,
  };
};

/**
 * Hook for RAG health checks
 */
const useRAGHealth = (ragServiceUrl: string, interval = 30000) => {
  const [health, setHealth] = useState<RAGHealthStatus | null>(null);
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${ragServiceUrl}/health`);
        if (response.ok) {
          const data: RAGHealthStatus = await response.json();
          setHealth(data);
          setIsHealthy(data.status === 'healthy');
        }
      } catch (err) {
        console.error('Health check failed:', err);
        setIsHealthy(false);
      }
    };

    checkHealth();
    const timer = setInterval(checkHealth, interval);
    return () => clearInterval(timer);
  }, [ragServiceUrl, interval]);

  return { health, isHealthy };
};

/**
 * Hook for retrieval endpoint (testing/debugging)
 */
const useRAGRetrieval = (ragServiceUrl: string) => {
  const [contexts, setContexts] = useState<
    Array<{ text: string; score: number }>
  >([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const retrieve = useCallback(
    async (query: string, topK = 5): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${ragServiceUrl}/retrieve?query=${encodeURIComponent(query)}&top_k=${topK}`,
          { method: 'POST' }
        );

        if (!response.ok) {
          throw new Error(`Retrieval error: ${response.status}`);
        }

        const data = await response.json();
        setContexts(data.contexts);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('Retrieval error:', err);
      } finally {
        setLoading(false);
      }
    },
    [ragServiceUrl]
  );

  return { contexts, loading, error, retrieve };
};

// ============================================================================
// UI COMPONENTS
// ============================================================================

/**
 * Chat message component
 */
const ChatMessageComponent: React.FC<{
  message: ChatMessage;
  showSources?: boolean;
}> = ({ message, showSources = false }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-xs px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-none'
            : 'bg-gray-200 text-gray-800 rounded-bl-none'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className={`text-xs mt-2 ${isUser ? 'text-blue-100' : 'text-gray-600'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>

        {showSources && message.sources && message.sources.length > 0 && (
          <div className="mt-2 text-xs border-t pt-2">
            <p className="font-semibold mb-1">Sources:</p>
            {message.sources.map((source, idx) => (
              <div key={idx} className="bg-opacity-50 bg-gray-300 p-1 mb-1 rounded">
                <p className="truncate">{source.text}</p>
                <p className="text-gray-700">Score: {source.score.toFixed(2)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Main AgriBot chat component
 */
interface AgriBotProps {
  ragServiceUrl: string;
  county?: string;
  week?: number;
  currentData?: {
    overall_stress_index?: number;
    water_stress_index?: { value: number };
    heat_stress_index?: { value: number };
    vegetation_health_index?: { value: number };
    atmospheric_stress_index?: { value: number };
  };
  yield_?: {
    predicted_yield?: number;
    uncertainty?: number;
  };
  recommendations?: string;
  showSources?: boolean;
}

const AgriBot: React.FC<AgriBotProps> = ({
  ragServiceUrl,
  county,
  week,
  currentData,
  yield_,
  recommendations,
  showSources = true,
}) => {
  const { messages, loading, error, sendMessage, clearMessages } =
    useRAGChat(ragServiceUrl);
  const { isHealthy } = useRAGHealth(ragServiceUrl);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showSourcesLocal, setShowSourcesLocal] = useState(showSources);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || loading) return;

    const agriContext: AgriContextData = {
      county,
      week,
      csi_overall: currentData?.overall_stress_index,
      water_stress: currentData?.water_stress_index?.value,
      heat_stress: currentData?.heat_stress_index?.value,
      vegetation_health: currentData?.vegetation_health_index?.value,
      atmospheric_stress: currentData?.atmospheric_stress_index?.value,
      predicted_yield: yield_?.predicted_yield,
      yield_uncertainty: yield_?.uncertainty,
      recommendations,
    };

    await sendMessage(inputValue, agriContext);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !loading) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isHealthy) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800 font-semibold">
          ⚠️ RAG Service Unavailable
        </p>
        <p className="text-yellow-700 text-sm mt-1">
          The AI chatbot is currently unavailable. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-blue-600 text-white px-4 py-3 rounded-t-lg flex justify-between items-center">
        <div>
          <h3 className="font-bold text-lg">🤖 AgriBot</h3>
          <p className="text-xs text-green-100">AI-powered crop insights</p>
        </div>
        {county && (
          <div className="text-right text-sm">
            <p className="font-semibold">{county}</p>
            {week && <p className="text-xs text-green-100">Week {week}</p>}
          </div>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            <p className="text-sm">
              👋 Welcome! Ask me about corn stress, yields, or farming practices.
            </p>
            <p className="text-xs mt-2">
              {county ? `Analyzing ${county} County - Week ${week || 'current'}` : 'Select a county to get started'}
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <ChatMessageComponent
            key={idx}
            message={msg}
            showSources={showSourcesLocal}
          />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 px-4 py-3 rounded-lg rounded-bl-none">
              <p className="text-sm">AgriBot is thinking...</p>
            </div>
          </div>
        )}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded text-sm">
            Error: {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about stress, yield, or farming practices..."
            disabled={loading || !isHealthy}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !isHealthy || !inputValue.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? '...' : '📤'}
          </button>
        </div>

        {/* Options */}
        <div className="flex justify-between text-xs">
          <label className="flex items-center gap-1 cursor-pointer text-gray-600 hover:text-gray-800">
            <input
              type="checkbox"
              checked={showSourcesLocal}
              onChange={(e) => setShowSourcesLocal(e.target.checked)}
              className="w-4 h-4"
            />
            Show sources
          </label>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-gray-600 hover:text-gray-800 underline"
            >
              Clear chat
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// EXPORT
// ============================================================================

export {
  AgriBot,
  ChatMessageComponent,
  useRAGChat,
  useRAGHealth,
  useRAGRetrieval,
  type ChatMessage,
  type AgriContextData,
  type RAGResponse,
  type RAGHealthStatus,
};

export default AgriBot;
