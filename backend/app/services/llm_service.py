"""
LLM Service - Handles AI response generation.
Supports Google Gemini and OpenAI with RAG integration.
"""

import asyncio
from typing import Optional, List, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from loguru import logger

from app.core.config import Settings, get_settings

settings = get_settings()


# System prompt for the campus assistant
SYSTEM_PROMPT = """You are a helpful and friendly Campus Assistant for a technical education institution in Rajasthan, India.

Your role is to:
1. Answer student queries about admissions, fees, scholarships, timetables, and campus facilities
2. Provide information from official college documents and FAQs
3. Be polite, concise, and accurate
4. If you don't know something or the information isn't in the provided context, say so honestly
5. Suggest contacting the relevant office for queries you cannot answer

Guidelines:
- Always be respectful and patient
- Keep responses concise but complete
- Use simple language that students can easily understand
- If a query is unclear, ask for clarification
- For urgent matters, recommend visiting the office in person
- Never make up information - stick to what's provided in the context

You are responding in: {language}
"""

CONTEXT_PROMPT = """Based on the following relevant information from college documents and FAQs:

{context}

Please answer the student's question. If the context doesn't contain relevant information, say that you don't have that specific information and suggest they contact the appropriate office."""


class LLMService:
    """
    Handles LLM interactions for generating responses.
    Uses RAG (Retrieval Augmented Generation) with context.
    """

    def __init__(self, settings_obj: Settings | None = None):
        self.settings = settings_obj or settings
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        """Initialize the LLM based on configuration."""
        provider = self.settings.llm_provider.lower()

        if provider == "gemini" and self.settings.google_api_key:
            self._llm = ChatGoogleGenerativeAI(
                model=self.settings.llm_model,
                google_api_key=self.settings.google_api_key.get_secret_value(),
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
            logger.info(f"Initialized Google Gemini LLM model={self.settings.llm_model}")

        elif provider == "openai" and self.settings.openai_api_key:
            self._llm = ChatOpenAI(
                model=self.settings.llm_model,
                openai_api_key=self.settings.openai_api_key.get_secret_value(),
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
            logger.info(f"Initialized OpenAI LLM model={self.settings.llm_model}")

        elif provider not in {"gemini", "openai"}:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")
        else:
            logger.warning(f"No API key configured for LLM provider '{provider}'. Using fallback responses.")
            self._llm = None

    async def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None,
        language: str = "English",
    ) -> Dict[str, Any]:
        """
        Generate a response using RAG.

        Args:
            query: User's question
            context_documents: Retrieved relevant documents
            conversation_history: Previous conversation messages
            language: Response language name

        Returns:
            Dict with response, confidence, and metadata
        """
        if not self._llm:
            return await self._fallback_response(query, context_documents, language)

        try:
            # Build context from retrieved documents
            context = self._build_context(context_documents)

            # Build conversation history
            messages = self._build_messages(
                query, context, conversation_history, language
            )

            # Generate response
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._llm.invoke(messages),
            )

            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context_documents)

            # Check if escalation needed
            needs_escalation = self._check_escalation_needed(
                query, response.content, confidence
            )

            # Generate suggested follow-up questions
            suggestions = self._generate_suggestions(query, context_documents)

            return {
                "response": response.content,
                "confidence": confidence,
                "needs_escalation": needs_escalation,
                "suggested_questions": suggestions,
                "sources_used": len(context_documents),
            }

        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return await self._fallback_response(query, context_documents, language)

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents."""
        if not documents:
            return "No specific information found in the knowledge base."

        context_parts = []
        for i, doc in enumerate(documents[:5], 1):  # Limit to top 5
            source = doc.get("metadata", {}).get("source_file", "FAQ")
            content = doc["content"][:500]  # Limit content length
            context_parts.append(f"[Source {i}: {source}]\n{content}")

        return "\n\n".join(context_parts)

    def _build_messages(
        self,
        query: str,
        context: str,
        conversation_history: List[Dict[str, str]],
        language: str,
    ) -> List:
        """Build message list for LLM."""
        messages = []

        # System message
        messages.append(
            SystemMessage(content=SYSTEM_PROMPT.format(language=language))
        )

        # Add conversation history (last 5 exchanges)
        if conversation_history:
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # Add context and query
        context_message = CONTEXT_PROMPT.format(context=context)
        full_query = f"{context_message}\n\nStudent's question: {query}"
        messages.append(HumanMessage(content=full_query))

        return messages

    def _calculate_confidence(self, documents: List[Dict[str, Any]]) -> int:
        """Calculate confidence score based on retrieved documents."""
        if not documents:
            return 30  # Low confidence if no context

        # Average of document relevance scores
        scores = [doc.get("score", 0.5) for doc in documents[:3]]
        avg_score = sum(scores) / len(scores)

        # Convert to 0-100 scale
        confidence = int(avg_score * 100)
        return min(max(confidence, 10), 95)  # Clamp between 10-95

    def _check_escalation_needed(
        self, query: str, response: str, confidence: int
    ) -> bool:
        """Determine if human escalation is needed."""
        # Escalation triggers
        escalation_keywords = [
            "complaint", "grievance", "urgent", "emergency",
            "fee refund", "ragging", "harassment", "legal",
            "document verification", "certificate issue",
        ]

        query_lower = query.lower()

        # Check for escalation keywords
        for keyword in escalation_keywords:
            if keyword in query_lower:
                return True

        # Low confidence responses should escalate
        if confidence < 40:
            return True

        # Check if response indicates uncertainty
        uncertainty_phrases = [
            "i don't have", "i'm not sure", "contact the office",
            "i cannot", "not available", "no information",
        ]
        response_lower = response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                return True

        return False

    def _generate_suggestions(
        self, query: str, documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate suggested follow-up questions."""
        suggestions = []

        # Extract categories from documents
        categories = set()
        for doc in documents:
            cat = doc.get("metadata", {}).get("category")
            if cat:
                categories.add(cat)

        # Generate suggestions based on query type
        query_lower = query.lower()

        if "fee" in query_lower or "payment" in query_lower:
            suggestions.append("What are the scholarship options available?")
            suggestions.append("What is the last date for fee payment?")

        elif "admission" in query_lower:
            suggestions.append("What documents are required for admission?")
            suggestions.append("What are the eligibility criteria?")

        elif "exam" in query_lower or "result" in query_lower:
            suggestions.append("When will the results be announced?")
            suggestions.append("How can I apply for re-evaluation?")

        elif "hostel" in query_lower:
            suggestions.append("What is the hostel fee structure?")
            suggestions.append("What facilities are available in the hostel?")

        else:
            suggestions.append("What are the important dates to remember?")
            suggestions.append("How can I contact the office?")

        return suggestions[:3]

    async def _fallback_response(
        self, query: str, documents: List[Dict[str, Any]], language: str
    ) -> Dict[str, Any]:
        """Provide fallback response when LLM is unavailable."""
        if documents:
            # Return best matching document content
            best_match = documents[0]
            response = (
                f"Based on our records:\n\n{best_match['content'][:500]}\n\n"
                "For more details, please contact the relevant office."
            )
            confidence = int(best_match.get("score", 0.5) * 100)
        else:
            response = (
                "I couldn't find specific information about your query. "
                "Please contact the administrative office for assistance, "
                "or try rephrasing your question."
            )
            confidence = 20

        return {
            "response": response,
            "confidence": confidence,
            "needs_escalation": confidence < 50,
            "suggested_questions": [
                "What are the office contact details?",
                "What are the office working hours?",
            ],
            "sources_used": len(documents),
        }

    async def detect_intent(self, query: str) -> str:
        """Detect the intent/category of the query."""
        intent_keywords = {
            "fees": ["fee", "payment", "dues", "amount", "cost"],
            "admission": ["admission", "enroll", "join", "apply", "application"],
            "scholarship": ["scholarship", "financial aid", "concession", "waiver"],
            "examination": ["exam", "result", "marks", "grade", "revaluation"],
            "timetable": ["timetable", "schedule", "class", "timing", "lecture"],
            "hostel": ["hostel", "accommodation", "room", "mess", "stay"],
            "library": ["library", "book", "borrow", "return", "fine"],
            "placement": ["placement", "job", "internship", "company", "campus"],
            "documents": ["certificate", "document", "transcript", "letter"],
            "contact": ["contact", "phone", "email", "office", "address"],
        }

        query_lower = query.lower()

        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return intent

        return "general"


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
