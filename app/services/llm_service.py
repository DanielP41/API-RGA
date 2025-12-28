from langchain_core.prompts import PromptTemplate
import time
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, provider: str, model_name: str, temperature: float, max_tokens: int, api_key: str = None):
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(model=model_name, temperature=temperature, max_tokens=max_tokens, openai_api_key=api_key)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            self.llm = ChatAnthropic(model_name=model_name, temperature=temperature, max_tokens=max_tokens, anthropic_api_key=api_key)
        elif provider == "deepseek":
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model_name, 
                temperature=temperature, 
                max_tokens=max_tokens, 
                openai_api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
        elif provider == "ollama":
            from langchain_community.chat_models import ChatOllama
            self.llm = ChatOllama(model=model_name, temperature=temperature)
        else:
            raise ValueError(f"Proveedor de LLM no soportado: {provider}")
            
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self):
        template = """Eres un asistente experto que responde preguntas basándose en documentación técnica.

Contexto relevante:
{context}

Pregunta: {question}

Instrucciones:
- Responde de manera clara y concisa
- Basa tu respuesta ÚNICAMENTE en el contexto proporcionado
- Si la información no está en el contexto, indica que no tienes suficiente información
- Cita las fuentes cuando sea relevante

Respuesta:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def generate_answer(self, query: str, retrieved_docs):
        """Genera una respuesta usando el LLM"""
        logger.info(f"Generando respuesta para la consulta: {query}")
        start_time = time.time()
        
        # Preparar contexto
        context = "\n\n".join([doc.page_content for doc, _ in retrieved_docs])
        
        # Crear prompt
        prompt = self.prompt_template.format(
            context=context,
            question=query
        )
        
        # Generar respuesta
        response = self.llm.invoke(prompt)
        
        latency = (time.time() - start_time) * 1000  # en ms
        logger.info(f"Respuesta generada en {latency:.2f}ms")
        
        return response.content, latency
