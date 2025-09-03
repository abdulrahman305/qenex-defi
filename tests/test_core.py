"""Unit tests for QENEX OS core functionality"""
import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch, AsyncMock
from qenex_single_unified import QenexUnifiedOS
from core.kernel import Kernel
from ai.ai_assistant import AIAssistant

class TestQenexCore:
    """Test suite for QENEX core components"""
    
    @pytest.fixture
    async def qenex_os(self):
        """Create QENEX OS instance for testing"""
        os = QenexUnifiedOS()
        yield os
        if os.running:
            await os.shutdown()
    
    @pytest.mark.asyncio
    async def test_startup(self, qenex_os):
        """Test QENEX OS startup sequence"""
        await qenex_os.startup()
        assert qenex_os.running == True
        assert qenex_os.version == "5.0.0"
    
    @pytest.mark.asyncio
    async def test_health_check(self, qenex_os):
        """Test health check functionality"""
        await qenex_os.startup()
        health = await qenex_os.health_check()
        assert health['status'] == 'healthy'
        assert 'uptime' in health
    
    @pytest.mark.asyncio
    async def test_module_loading(self, qenex_os):
        """Test module loading and initialization"""
        await qenex_os.startup()
        assert len(qenex_os.modules) > 0
        assert 'ai' in qenex_os.modules
        assert 'monitoring' in qenex_os.modules
    
    @pytest.mark.asyncio
    async def test_shutdown(self, qenex_os):
        """Test graceful shutdown"""
        await qenex_os.startup()
        await qenex_os.shutdown()
        assert qenex_os.running == False
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, qenex_os):
        """Test self-healing error recovery"""
        await qenex_os.startup()
        # Simulate error
        qenex_os.modules['test'] = Mock(side_effect=Exception("Test error"))
        result = await qenex_os.recover_from_error('test', Exception("Test error"))
        assert result == True

class TestAIAssistant:
    """Test suite for AI Assistant"""
    
    @pytest.fixture
    def ai_assistant(self):
        """Create AI assistant instance"""
        return AIAssistant()
    
    @pytest.mark.asyncio
    async def test_process_command(self, ai_assistant):
        """Test command processing"""
        response = await ai_assistant.process_command("status")
        assert response is not None
        assert 'status' in response.lower()
    
    @pytest.mark.asyncio
    async def test_natural_language(self, ai_assistant):
        """Test natural language processing"""
        response = await ai_assistant.process_natural_language("What is the system status?")
        assert response is not None
        assert len(response) > 0

class TestKernel:
    """Test suite for QENEX Kernel"""
    
    @pytest.fixture
    def kernel(self):
        """Create kernel instance"""
        return Kernel()
    
    def test_initialization(self, kernel):
        """Test kernel initialization"""
        assert kernel is not None
        assert kernel.version is not None
    
    @pytest.mark.asyncio
    async def test_resource_management(self, kernel):
        """Test resource management"""
        resources = await kernel.get_resources()
        assert 'cpu' in resources
        assert 'memory' in resources
        assert 'disk' in resources
    
    @pytest.mark.asyncio
    async def test_process_scheduling(self, kernel):
        """Test process scheduling"""
        task = AsyncMock()
        pid = await kernel.schedule_task(task)
        assert pid is not None
        assert pid > 0