"""
Test script for complete order workflow
Tests: analyzer → requirements_extractor → writer → word_count_checker
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
    """Test the complete workflow on a real order"""

    print("=" * 80)
    print("FULL ORDER WORKFLOW TEST")
    print("=" * 80)
    print()

    # Test order data
    order_data = {
        'order_id': 'TEST-001',
        'order_index': '123',
        'description': 'Short Answer Question on Gender Symmetry and Restorative Justice',
        'pages': 2,
        'deadline': '2024-01-25 10:00',
        'files': [
            'test/CRIM 4232 Week 12 Short Answer question.docx'
        ]
    }

    print(f"📋 Order ID: {order_data['order_id']}")
    print(f"📄 Description: {order_data['description']}")
    print(f"📃 Pages: {order_data['pages']}")
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
        print(f"  - Word Count Target: {req.get('target_word_count', 'N/A')}")
        print(f"  - Required Sources: {req.get('required_sources', 'N/A')}")
        print()

    # Show word count results
    if final_state.get('word_count'):
        target = final_state['pages_required'] * 300
        print(f"Word Count: {final_state['word_count']} / {target} (target)")
        print()

    # Show final text preview if available
    if final_state.get('final_text'):
        print("Final Text Preview (first 500 chars):")
        print("-" * 80)
        print(final_state['final_text'][:500])
        print("...")
        print("-" * 80)
        print()

        # Save to file
        output_file = Path(__file__).parent / 'test' / 'output_text.txt'
        output_file.write_text(final_state['final_text'], encoding='utf-8')
        print(f"✅ Full text saved to: {output_file}")
        print()

    # Show error if any
    if final_state.get('error'):
        print(f"❌ Error: {final_state['error']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
