
from typing import List, Dict, Optional
import uuid
from app.models.schemas import ConversationMessage

class ConversationManager:
    def __init__(self):
        # In-memory storage for conversations: conversation_id -> List[ConversationMessage]
        self.conversations: Dict[str, List[ConversationMessage]] = {}
    
    def create_conversation(self) -> str:
        """Creates a new conversation and returns its ID"""
        conv_id = str(uuid.uuid4())
        self.conversations[conv_id] = []
        return conv_id
        
    def add_message(self, conversation_id: str, message: ConversationMessage):
        """Adds a message to a conversation"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append(message)
    
    def get_history(self, conversation_id: str) -> List[ConversationMessage]:
        """Retrieves history for a conversation"""
        return self.conversations.get(conversation_id, [])
    
    def get_context_prompt(self, history: List[ConversationMessage], 
                          current_question: str) -> str:
        """Generates a prompt including conversation history"""
        if not history:
            return current_question
            
        context = "\n".join([
            f"{msg.role}: {msg.content}" 
            for msg in history[-5:]  # Últimos 5 mensajes
        ])
        return f"Historial de conversación anterior:\n{context}\n\nPregunta actual del usuario: {current_question}"
