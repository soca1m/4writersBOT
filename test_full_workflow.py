"""
Test script for complete order workflow
New architecture: 7 bots

Flow:
Bot 1 (Requirements) → Bot 2 (Writer) → Bot 3 (Citations) →
Bot 4 (Word Count) ↔ Bot 2 (expand) →
Bot 5 (Quality) ↔ Bot 2 (revise) →
Bot 6 (AI Check) → Bot 7 (References) → END
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from src.workflows.order_workflow import process_order


async def test_full_workflow():
    """Test the complete workflow on a sample order"""

    print("=" * 80)
    print("FULL ORDER WORKFLOW TEST - NEW 7 BOT ARCHITECTURE")
    print("=" * 80)
    print()

    # Test order data
    order_data = {
        'order_id': 'TEST-001',
        'order_index': '123',
        'description': 'Write a short answer about gender symmetry in domestic violence research and how restorative justice approaches can address this issue.',
        'pages': 2,
        'deadline': '2024-01-25 10:00',
        'files': []
    }

    print(f"📋 Order ID: {order_data['order_id']}")
    print(f"📄 Description: {order_data['description'][:80]}...")
    print(f"📃 Pages: {order_data['pages']} ({order_data['pages'] * 300} words minimum)")
    print(f"📎 Files: {len(order_data['files'])}")
    print()
    print("-" * 80)
    print()

    # Process order through workflow
    final_state = await process_order(order_data)

    print()
    print("=" * 80)
    print("WORKFLOW RESULTS")
    print("=" * 80)
    print()
    print(f"Final Status: {final_state['status']}")
    print()

    # Show agent logs
    if final_state.get('agent_logs'):
        print("Agent Logs:")
        for log in final_state['agent_logs']:
            print(f"  {log}")
        print()

    # Show requirements if extracted
    if final_state.get('requirements'):
        req = final_state['requirements']
        print("Requirements Extracted:")
        print(f"  - Type: {req.get('assignment_type', 'N/A')}")
        print(f"  - Topic: {req.get('main_topic', 'N/A')}")
        print(f"  - Main Question: {req.get('main_question', 'N/A')[:60]}...")
        print(f"  - Word Count Target: {req.get('target_word_count', 'N/A')}")
        print(f"  - Required Sources: {req.get('required_sources', 'N/A')}")
        print(f"  - Search Keywords: {req.get('search_keywords', 'N/A')}")
        print()

    # Show sources found
    if final_state.get('sources_found'):
        sources = final_state['sources_found']
        print(f"Sources Found: {len(sources)}")
        for s in sources[:5]:
            print(f"  - {s.get('citation', 'Unknown')}: {s.get('title', '')[:50]}...")
        print()

    # Show word count results
    print(f"Word Count: {final_state.get('word_count', 0)} / {final_state.get('target_word_count', 0)} (target)")
    print(f"Word Count Attempts: {final_state.get('word_count_attempts', 0)}")
    print()

    # Show quality check info
    print(f"Quality OK: {final_state.get('quality_ok', False)}")
    print(f"Quality Check Attempts: {final_state.get('quality_check_attempts', 0)}")
    if final_state.get('quality_issues'):
        print(f"Quality Issues: {final_state['quality_issues']}")
    print()

    # Show AI detection info
    print(f"AI Score: {final_state.get('ai_score', 0):.1f}%")
    print(f"AI Check Attempts: {final_state.get('ai_check_attempts', 0)}")
    print(f"AI Check Passed: {final_state.get('ai_check_passed', False)}")
    print()

    # Show final text preview if available
    if final_state.get('final_text'):
        print("Final Text Preview (first 800 chars):")
        print("-" * 80)
        print(final_state['final_text'][:800])
        print("...")
        print("-" * 80)
        print()

        # Save to file
        output_dir = Path(__file__).parent / 'test'
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / 'output_text.txt'
        output_file.write_text(final_state['final_text'], encoding='utf-8')
        print(f"✅ Full text saved to: {output_file}")
        print()

    # Show error if any
    if final_state.get('error'):
        print(f"❌ Error: {final_state['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
