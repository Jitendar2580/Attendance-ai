from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.ai_service import chat_with_attendance_assistant, save_conversation

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
) -> ChatHistoryResponse:
    """Return recent chat exchanges for the current user (oldest first, for display)."""
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    ).all()
    items = list(reversed(rows))
    return ChatHistoryResponse(items=items)


@router.post("", response_model=ChatResponse)
def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Send a message to the attendance assistant and get a response."""
    try:
        # Generate AI response
        ai_response = chat_with_attendance_assistant(db, current_user, request.message)

        # Save conversation to database
        conversation = save_conversation(db, current_user.id, request.message, ai_response)

        return ChatResponse(
            response=ai_response,
            conversation_id=conversation.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )
