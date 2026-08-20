"""
Core Chatbot Engine.
Orchestrates all services to handle user queries.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import MessageRole
from app.models.schemas import ChatRequest, ChatResponse, ChatSource
from app.services.translation import get_translation_service
from app.services.vector_store import get_vector_store
from app.services.llm_service import get_llm_service
from app.services.session_manager import get_session_manager
from app.core.config import LANGUAGE_NAMES


class ChatbotEngine:
    """
    Main chatbot engine that orchestrates:
    1. Language detection and translation
    2. Context retrieval from vector store
    3. LLM response generation
    4. Session management
    5. Response translation
    """

    def __init__(
        self,
        translation=None,
        vector_store=None,
        llm=None,
        session_manager=None,
    ):
        self.translation = translation or get_translation_service()
        self.vector_store = vector_store or get_vector_store()
        self.llm = llm or get_llm_service()
        self.session_manager = session_manager or get_session_manager()

    async def process_message(
        self,
        request: ChatRequest,
        db: AsyncSession,
    ) -> ChatResponse:
        """
        Process an incoming chat message.

        Flow:
        1. Get or create session
        2. Detect language and translate to English
        3. Retrieve relevant context from vector store
        4. Generate response using LLM
        5. Translate response to user's language
        6. Save messages and update session
        7. Return response
        """
        try:
            # 1. Get or create session
            session = await self.session_manager.get_or_create_session(
                db=db,
                session_id=request.session_id,
                platform=request.platform,
                user_id=request.user_id,
                language=request.language or "en",
            )

            # 2. Language detection and translation
            english_query, detected_lang, response_lang = await self.translation.process_query(
                request.message,
                request.language,
            )

            # Update session language if different
            if detected_lang != session.language:
                await self.session_manager.update_session_language(
                    db, session, detected_lang
                )

            # 3. Get conversation history for context
            conversation_history = await self.session_manager.get_conversation_history(
                db, session, limit=6
            )

            # Build context string from history
            context_str = None
            if conversation_history:
                recent = conversation_history[-2:]  # Last exchange
                context_str = "\n".join(
                    [f"{m['role']}: {m['content']}" for m in recent]
                )

            # 4. Retrieve relevant documents
            search_results = await self.vector_store.search_with_context(
                query=english_query,
                conversation_context=context_str,
                k=5,
            )

            # 5. Detect intent
            intent = await self.llm.detect_intent(english_query)

            # 6. Generate response
            llm_result = await self.llm.generate_response(
                query=english_query,
                context_documents=search_results,
                conversation_history=conversation_history,
                language=LANGUAGE_NAMES.get(response_lang, "English"),
            )

            # 7. Translate response if needed
            response_text = llm_result["response"]
            if response_lang != "en":
                response_text = await self.translation.prepare_response(
                    response_text, response_lang
                )

            # 8. Translate suggested questions if needed
            suggested_questions = llm_result.get("suggested_questions", [])
            if response_lang != "en" and suggested_questions:
                translated_suggestions = []
                for q in suggested_questions[:3]:
                    translated_q = await self.translation.prepare_response(
                        q, response_lang
                    )
                    translated_suggestions.append(translated_q)
                suggested_questions = translated_suggestions

            # 9. Save messages to session
            # Save user message
            await self.session_manager.add_message(
                db=db,
                session=session,
                role=MessageRole.USER,
                content=english_query,
                original_content=request.message if detected_lang != "en" else None,
                original_language=detected_lang if detected_lang != "en" else None,
                intent=intent,
            )

            # Save assistant response
            sources_data = [
                {
                    "title": s.get("metadata", {}).get("source_file", "FAQ"),
                    "score": s.get("score", 0),
                }
                for s in search_results[:3]
            ]

            await self.session_manager.add_message(
                db=db,
                session=session,
                role=MessageRole.ASSISTANT,
                content=response_text,
                intent=intent,
                confidence=llm_result["confidence"],
                sources=sources_data,
            )

            # 10. Update session context
            await self.session_manager.update_session_context(
                db=db,
                session=session,
                context_updates={
                    "last_intent": intent,
                    "last_confidence": llm_result["confidence"],
                },
            )

            # 11. Build response
            sources = [
                ChatSource(
                    title=s.get("metadata", {}).get("source_file", "FAQ"),
                    content=s.get("content", "")[:200],
                    score=s.get("score", 0),
                    document_id=s.get("metadata", {}).get("document_id"),
                )
                for s in search_results[:3]
            ]

            return ChatResponse(
                response=response_text,
                session_id=session.session_id,
                detected_language=detected_lang,
                response_language=response_lang,
                intent=intent,
                confidence=llm_result["confidence"],
                sources=sources,
                needs_escalation=llm_result.get("needs_escalation", False),
                suggested_questions=suggested_questions,
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    async def get_welcome_message(
        self,
        language: str = "en",
    ) -> str:
        """Get welcome message in specified language."""
        welcome_en = (
            "Hello! 👋 I'm your Campus Assistant. I can help you with:\n\n"
            "• Admission queries\n"
            "• Fee and scholarship information\n"
            "• Examination schedules and results\n"
            "• Timetables and academic calendar\n"
            "• Hostel and campus facilities\n"
            "• Contact information\n\n"
            "How can I assist you today?"
        )

        if language == "en":
            return welcome_en

        return await self.translation.prepare_response(welcome_en, language)

    async def get_fallback_message(
        self,
        language: str = "en",
    ) -> str:
        """Get fallback message for errors."""
        fallback_en = (
            "I apologize, but I'm having trouble processing your request. "
            "Please try again, or contact the administrative office for assistance.\n\n"
            "Office Contact: example@college.edu"
        )

        if language == "en":
            return fallback_en

        return await self.translation.prepare_response(fallback_en, language)


# Singleton instance
_chatbot_engine: Optional[ChatbotEngine] = None


def get_chatbot_engine() -> ChatbotEngine:
    """Get or create chatbot engine instance."""
    global _chatbot_engine
    if _chatbot_engine is None:
        _chatbot_engine = ChatbotEngine()
    return _chatbot_engine
