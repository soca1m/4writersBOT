"""
Test script for Researcher Agent
Tests academic source discovery using Tavily API
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from src.agents.researcher import research_sources_node
from src.workflows.state import OrderWorkflowState


async def test_researcher():
    """Test the researcher agent with a sample topic"""

    print("=" * 80)
    print("RESEARCHER AGENT TEST")
    print("=" * 80)

    # Check Tavily API key
    tavily_key = "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"
    if not tavily_key:
        print("❌ ERROR: TAVILY_API_KEY not found in .env file")
        return

    print(f"✅ Tavily API Key configured: {tavily_key[:8]}...")
    print()

    # Create test state
    test_state: OrderWorkflowState = {
        'order_id': 'TEST-001',
        'order_index': '123',
        'order_description': 'Gender symmetry in intimate partner violence and restorative justice approaches',
        'pages_required': 2,
        'deadline': '2024-01-25',
        'attached_files': [],
        'requirements': {
            'assignment_type': 'essay',
            'main_topic': 'gender symmetry in intimate partner violence and restorative justice',
            'target_word_count': 600,
            'required_sources': 2,
            'main_question': 'How do gender symmetry theories in IPV relate to restorative justice approaches?'
        },
        'parsed_files_content': '',
        'sources_found': [],
        'quotes': [],
        'draft_text': '',
        'word_count': 0,
        'meets_requirements': False,
        'quality_issues': [],
        'plagiarism_score': 0.0,
        'plagiarism_details': {},
        'rewrite_attempts': 0,
        'final_text': '',
        'references': '',
        'status': 'requirements_extracted',
        'agent_logs': [],
        'error': None
    }

    print(f"📋 Test Topic: {test_state['requirements']['main_topic']}")
    print(f"📚 Required Sources: {test_state['requirements']['required_sources']}")
    print()
    print("-" * 80)
    print()

    # Run researcher
    result = await research_sources_node(test_state)

    print()
    print("-" * 80)
    print()
    print(f"Status: {result['status']}")
    print()

    if result['status'] == 'sources_found':
        sources = result['sources_found']
        print(f"✅ Found {len(sources)} academic sources:")
        print()

        for i, source in enumerate(sources, 1):
            print(f"{i}. {source['title']}")
            print(f"   URL: {source['url']}")
            if source.get('year'):
                print(f"   Year: {source['year']}")
            print(f"   Query used: {source['query_used']}")
            print(f"   Content preview: {source['content'][:150]}...")
            print()

    elif result['status'] == 'insufficient_sources':
        print("⚠️  No academic sources found")

    else:
        print(f"❌ Research failed: {result.get('error', 'Unknown error')}")

    # Show agent logs
    if result.get('agent_logs'):
        print()
        print("Agent logs:")
        for log in result['agent_logs']:
            print(f"  {log}")


if __name__ == "__main__":
    asyncio.run(test_researcher())
