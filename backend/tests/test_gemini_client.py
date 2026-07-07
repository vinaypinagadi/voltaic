import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.gemini_client import GeminiAgent
from app.core.config import settings

@pytest.fixture
def gemini_agent():
    with patch("app.agents.gemini_client.genai.configure"):
        agent = GeminiAgent()
        return agent

@pytest.mark.asyncio
async def test_get_embedding_success(gemini_agent):
    with patch("app.agents.gemini_client.genai.embed_content_async", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = {"embedding": [0.1, 0.2, 0.3]}
        settings.GEMINI_API_KEY = "test_key"
        embedding = await gemini_agent.get_embedding("test")
        assert embedding == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_get_embedding_no_api_key(gemini_agent):
    settings.GEMINI_API_KEY = ""
    embedding = await gemini_agent.get_embedding("test")
    assert embedding == [0.0] * 768

@pytest.mark.asyncio
async def test_get_embedding_exception(gemini_agent):
    with patch("app.agents.gemini_client.genai.embed_content_async", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = Exception("API Error")
        settings.GEMINI_API_KEY = "test_key"
        embedding = await gemini_agent.get_embedding("test")
        assert embedding == [0.0] * 768

@pytest.mark.asyncio
async def test_retrieve_context_no_data(gemini_agent, mock_supabase):
    settings.GEMINI_API_KEY = "test_key"
    mock_supabase["execute"].data = []
    
    with patch.object(gemini_agent, "get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = [0.1] * 768
        context = await gemini_agent.retrieve_context("query")
        assert "No relevant stadium rules" in context

@pytest.mark.asyncio
async def test_retrieve_context_success(gemini_agent, mock_supabase):
    settings.GEMINI_API_KEY = "test_key"
    mock_supabase["execute"].data = [
        {"metadata": "Rules", "content": "Rule 1"},
        {"metadata": "Map", "content": "Gate A is North"}
    ]
    
    with patch.object(gemini_agent, "get_embedding", new_callable=AsyncMock) as mock_get_emb:
        mock_get_emb.return_value = [0.1] * 768
        context = await gemini_agent.retrieve_context("query")
        assert "Rule 1" in context
        assert "Gate A is North" in context

@pytest.mark.asyncio
async def test_retrieve_context_exception(gemini_agent):
    settings.GEMINI_API_KEY = "test_key"
    
    with patch("app.agents.gemini_client.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.side_effect = Exception("DB Error")
        
        with patch.object(gemini_agent, "get_embedding", new_callable=AsyncMock) as mock_get_emb:
            mock_get_emb.return_value = [0.1] * 768
            context = await gemini_agent.retrieve_context("query")
            assert "Unable to access vector database" in context

@pytest.mark.asyncio
async def test_generate_chat_stream_mock_no_api_key(gemini_agent):
    settings.GEMINI_API_KEY = ""
    generator = gemini_agent.generate_chat_stream("Hello", "user-123")
    chunks = [chunk async for chunk in generator]
    assert len(chunks) == 1
    assert "[MOCK STREAM]" in chunks[0]

@pytest.mark.asyncio
async def test_generate_chat_stream_success(gemini_agent, mock_supabase):
    settings.GEMINI_API_KEY = "test_key"
    
    mock_supabase["execute"].data = [{"match_id": "WC-2026", "gate": "Gate A"}]
    
    with patch.object(gemini_agent, "retrieve_context", new_callable=AsyncMock) as mock_ret:
        mock_ret.return_value = "Mock Context"
        
        # We need to mock GenerativeModel and its generate_content_async
        mock_model = MagicMock()
        mock_resp = AsyncMock()
        
        async def mock_stream():
            class MockChunk:
                def __init__(self, t):
                    self.text = t
            yield MockChunk("Hello")
            yield MockChunk(" World")
        
        mock_resp = mock_stream()
        mock_model.generate_content_async = AsyncMock(return_value=mock_resp)
        
        with patch("app.agents.gemini_client.genai.GenerativeModel", return_value=mock_model):
            generator = gemini_agent.generate_chat_stream("Hello", "user-123", [{"role": "user", "content": "Hi"}])
            chunks = [chunk async for chunk in generator]
            assert "".join(chunks) == "Hello World"

@pytest.mark.asyncio
async def test_generate_chat_stream_exception(gemini_agent, mock_supabase):
    settings.GEMINI_API_KEY = "test_key"
    
    mock_supabase["execute"].data = []
    
    with patch.object(gemini_agent, "retrieve_context", new_callable=AsyncMock) as mock_ret:
        mock_ret.return_value = "Mock Context"
        
        mock_model = MagicMock()
        mock_model.generate_content_async.side_effect = Exception("Gemini Error")
        
        with patch("app.agents.gemini_client.genai.GenerativeModel", return_value=mock_model):
            generator = gemini_agent.generate_chat_stream("Hello", "user-123")
            chunks = [chunk async for chunk in generator]
            assert "Error:" in chunks[0]
            assert "Gemini Error" in chunks[0]
