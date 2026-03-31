import logging
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.services.rag.vector_store import VectorStoreService
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGPipelineService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
        # Use Gemini AI for 100% free generation
        # Requires GEMINI_API_KEY in environment
        try:
            if settings.GEMINI_API_KEY:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-flash-latest",
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=0.2,
                    convert_system_message_to_human=True
                )
                logger.info("RAG: Successfully initialized Gemini 1.5 Flash brain.")
            else:
                logger.warning("RAG: GEMINI_API_KEY not set. Check your .env file.")
                self.llm = None
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            self.llm = None
        
    def _extract_ticker_from_query(self, query: str) -> Optional[str]:
        """
        Extract the stock ticker symbol (if any) from the user query.
        """
        if not self.llm:
            return None
            
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a financial entity extractor. Extract the stock ticker symbol (e.g. FPT, VNM, HPG) from the user's query. If no ticker is found, simply output 'NONE'. Output ONLY the uppercase ticker symbol or 'NONE', nothing else. Typical Vietnamese syntax: 'phân tích mã ACB', 'cho tôi biết về FPT'."),
            ("user", "{query}")
        ])
        
        try:
            chain = extraction_prompt | self.llm | StrOutputParser()
            result = chain.invoke({"query": query}).strip().upper()
            
            if result == "NONE" or len(result) > 5: # basic sanity check
                return None
            return result
        except Exception as e:
            logger.error(f"Error extracting ticker: {e}")
            return None

    async def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        1. Extract Ticker
        2. Retrieve Context (filtered by Ticker if found)
        3. Generate Answer
        """
        if not self.llm or not self.vector_store or not self.vector_store.vector_store:
            return {
                "answer": "Hệ thống RAG chưa được cấu hình đầy đủ (Vui lòng kiểm tra GEMINI_API_KEY hoặc PINECONE_API_KEY trong .env).",
                "ticker_identified": None,
                "sources": []
            }

        ticker = self._extract_ticker_from_query(query)
        
        filter_metadata = {}
        if ticker:
            filter_metadata["ticker"] = ticker
            logger.info(f"RAG: Extracted ticker '{ticker}' from query.")
            
        # Retrieve context from Vector Store
        docs = self.vector_store.search_similar_documents(query=query, k=5, filter_metadata=filter_metadata)
        
        if not docs:
            logger.info("RAG: No relevant documents found in the vector store.")
            return {
                "answer": "Xin lỗi, hiện tại hệ thống chưa có báo cáo tài chính nào liên quan đến câu hỏi của bạn trong cơ sở dữ liệu.",
                "ticker_identified": ticker,
                "sources": []
            }
            
        # Format context
        context_text = "\n\n---\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')} (Page {doc.metadata.get('page', '?')})\nContent: {doc.page_content}" 
            for doc in docs
        ])
        
        # Generation Prompt
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một chuyên gia phân tích tài chính thông minh của hệ thống. 
Bạn được cung cấp các đoạn trích từ báo cáo tài chính, báo cáo thường niên thực tế dưới phần 'Ngữ cảnh'.
Hãy sử dụng CHỈ CÁC THÔNG TIN TRONG NGỮ CẢNH để trả lời câu hỏi của người dùng.
Nếu ngữ cảnh không chứa đủ thông tin để trả lời, hãy nói rõ là "Tôi không có đủ thông tin từ báo cáo tài chính để trả lời chính xác".
ĐỪNG tự sáng tác thêm số liệu. 
Trả lời bằng tiếng Việt, trình bày rõ ràng, dễ hiểu, định dạng markdown. Nếu có số liệu, hãy trích dẫn nguồn rõ ràng (VD: Theo Báo cáo tài chính quý 1, trang X...)."""),
            ("user", "Ngữ cảnh:\n{context}\n\nCâu hỏi: {query}")
        ])
        
        try:
            qa_chain = qa_prompt | self.llm | StrOutputParser()
            
            logger.info("RAG: Generating answer from LLM...")
            answer = qa_chain.invoke({
                "context": context_text,
                "query": query
            })
            
            # Extract sources for transparency
            sources = []
            for doc in docs:
                source_info = {
                    "source": doc.metadata.get('source', 'Unknown'),
                    "page": doc.metadata.get('page', '?'),
                    "doc_type": doc.metadata.get('doc_type', 'Unknown'),
                    "period": doc.metadata.get('period', '')
                }
                if source_info not in sources:
                    sources.append(source_info)
                    
            return {
                "answer": answer,
                "ticker_identified": ticker,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"Error generating RAG answer: {e}")
            return {
                "answer": f"Đã xảy ra lỗi khi tạo câu trả lời: {str(e)}",
                "ticker_identified": ticker,
                "sources": []
            }
