"""
Test script for 10-page order (bypassing analyzer)
Tests: requirements_extractor → writer → word_count_checker cycle
"""
import asyncio
from pathlib import Path

from src.workflows.state import OrderWorkflowState
from src.agents.requirements_extractor import extract_requirements_node
from src.agents.writer import write_text_node
from src.agents.word_count_checker import check_word_count_node


async def test_10_pages():
    """Test writing workflow on a 10-page order"""

    print("=" * 80)
    print("10-PAGE ORDER TEST")
    print("=" * 80)
    print()

    # Create initial state for 10 pages
    state: OrderWorkflowState = {
        'order_id': 'TEST-10P',
        'order_index': '999',
        'order_description': 'Comprehensive analysis of gender symmetry in intimate partner violence and restorative justice approaches',
        'pages_required': 10,  # 10 pages = 3000 words target
        'deadline': '2024-01-30',
        'attached_files': ['test/CRIM 4232 Week 12 Short Answer question.docx'],
        'requirements': {},
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
        'status': 'accepted',  # Bypass analyzer
        'agent_logs': [],
        'error': None
    }

    print(f"📋 Order ID: {state['order_id']}")
    print(f"📄 Description: {state['order_description']}")
    print(f"📃 Pages: {state['pages_required']}")
    print(f"🎯 Target word count: {state['pages_required'] * 300} words")
    print()
    print("-" * 80)
    print()

    # Step 1: Extract requirements
    print("STEP 1: Extracting requirements...")
    print()
    state = await extract_requirements_node(state)

    if state['status'] == 'insufficient_info':
        print("❌ Insufficient information to proceed")
        return

    print()
    print("-" * 80)
    print()

    # Step 2: Writing cycle with word count checking
    max_attempts = 5  # Limit expansion attempts
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        print(f"STEP 2.{attempt}: Writing/Expanding text...")
        print()

        state = await write_text_node(state)

        if state['status'] == 'writing_failed':
            print(f"❌ Writing failed: {state.get('error')}")
            break

        print()
        print("-" * 80)
        print()
        print(f"STEP 3.{attempt}: Checking word count...")
        print()

        state = await check_word_count_node(state)

        current_count = state['word_count']
        target = state['pages_required'] * 300

        print(f"📊 Current: {current_count} words, Target: {target} words")

        if state['status'] == 'word_count_ok':
            print("✅ Word count acceptable!")
            break
        elif state['status'] == 'insufficient_words':
            words_needed = target - current_count
            print(f"⚠️  Need {words_needed} more words, expanding...")
            print()
            print("-" * 80)
            print()
        elif state['status'] == 'too_many_words':
            print("⚠️  Too many words, but accepting")
            break
        else:
            print(f"❌ Word count check failed: {state.get('error')}")
            break

    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print()
    print(f"Final Status: {state['status']}")
    print(f"Final Word Count: {state['word_count']} / {state['pages_required'] * 300}")
    print(f"Expansion Attempts: {attempt}")
    print()

    # Show agent logs
    if state.get('agent_logs'):
        print("Agent Logs:")
        for log in state['agent_logs']:
            print(f"  {log}")
        print()

    # Save final text
    if state.get('final_text'):
        output_file = Path(__file__).parent / 'test' / 'output_10pages.txt'
        output_file.write_text(state['final_text'], encoding='utf-8')
        print(f"✅ Full text saved to: {output_file}")
        print()

        # Show preview
        print("Text Preview (first 1000 chars):")
        print("-" * 80)
        print(state['final_text'][:1000])
        print("...")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(test_10_pages())
