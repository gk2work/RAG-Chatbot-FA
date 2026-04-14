"""
Enhanced RAG Service - Modular Architecture

This module provides a decentralized, modular implementation of the Enhanced RAG Service.
The monolithic 2500+ line service has been broken down into the following components:

- vector_search/: FAISS vector search and embedding services
- lead_management/: Lead extraction and user analysis  
- conversation/: Memory management and session state
- document_search/: Document finder and content filtering
- response_generation/: LLM client and response formatting
- questioning/: Dynamic questioning and sequence management
- utils/: Cache management and performance monitoring
- rag_orchestrator.py: Main service that coordinates all components
"""

from .rag_orchestrator import EnhancedRAGService

__all__ = ['EnhancedRAGService']
