#!/usr/bin/env python3
"""
Test script for new soft_batch features.

Tests chunking, RAG, and database integration.
"""
import os
import sys

def test_chunking():
    """Test document chunking."""
    print("\n" + "="*60)
    print("TEST 1: Document Chunking")
    print("="*60)
    
    from chunking import chunk_document
    
    sample_text = """
Soft Batch is a modern artisanal bakery focused on creating warm, cozy experiences.

Our Philosophy:
We believe in using only the finest ingredients. Every cookie, pastry, and bread is made fresh daily.

Our Specialties:
We're famous for our chocolate chip cookies with a perfectly soft center. Our sourdough bread has a crispy crust and tangy flavor. All seasonal tarts use local, fresh ingredients.

Community Focus:
We're more than a bakery. We're a gathering place. Every Sunday, we host baking workshops.
""".strip()
    
    strategies = [
        ("paragraphs", 200),
        ("fixed_chars", 150),
        ("sentences", 3)
    ]
    
    for strategy, size in strategies:
        print(f"\n  Strategy: {strategy} (size={size})")
        chunks = chunk_document(sample_text, strategy=strategy, chunk_size=size)
        print(f"  → Generated {len(chunks)} chunks")
        
        if chunks:
            preview = chunks[0].text[:80].replace('\n', ' ')
            print(f"  → First chunk: {preview}...")
    
    print("\n  ✅ Chunking tests passed!")
    return True


def test_database():
    """Test new database tables."""
    print("\n" + "="*60)
    print("TEST 2: Database Schema")
    print("="*60)
    
    from database import init_db, get_db, DEFAULT_DB_PATH
    
    # Initialize if needed
    if not os.path.exists(DEFAULT_DB_PATH):
        print("  Initializing database...")
        init_db()
    
    # Check new tables exist
    new_tables = ['document_chunks', 'notion_documents', 'mastodon_interactions']
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in new_tables:
            if table in existing_tables:
                print(f"  ✓ Table '{table}' exists")
            else:
                print(f"  ✗ Table '{table}' missing!")
                return False
    
    print("\n  ✅ Database tests passed!")
    return True


def test_rag_mock():
    """Test RAG system with mock data."""
    print("\n" + "="*60)
    print("TEST 3: RAG System (Mock)")
    print("="*60)
    
    from chunking import chunk_document
    from database import save_document_chunk, get_document_chunks
    import json
    
    sample_doc = """
Soft Batch uses only organic flour from local mills.
We bake fresh every morning starting at 5am.
Our signature item is the chocolate chip cookie with sea salt.
All our packaging is 100% compostable and eco-friendly.
""".strip()
    
    # Chunk the document
    print("  Chunking sample document...")
    chunks = chunk_document(sample_doc, strategy="sentences", chunk_size=1)
    print(f"  → Generated {len(chunks)} chunks")
    
    # Save chunks (without embeddings for this test)
    print("  Saving chunks to database...")
    source_id = "test_doc_001"
    
    for chunk in chunks:
        save_document_chunk(
            source_id=source_id,
            source_type="test",
            chunk_text=chunk.text,
            chunk_number=chunk.chunk_number,
            chunk_strategy="sentences",
            metadata=json.dumps(chunk.metadata)
        )
    
    # Retrieve chunks
    print("  Retrieving chunks from database...")
    retrieved = get_document_chunks(source_id, "test")
    print(f"  → Retrieved {len(retrieved)} chunks")
    
    if len(retrieved) == len(chunks):
        print("  ✓ All chunks stored and retrieved correctly")
    else:
        print("  ✗ Chunk count mismatch!")
        return False
    
    print("\n  ✅ RAG tests passed!")
    print("  ⚠️  Note: Full embedding tests require OPENROUTER_API_KEY")
    return True


def test_listeners_import():
    """Test that listener modules can be imported."""
    print("\n" + "="*60)
    print("TEST 4: Listener Modules")
    print("="*60)
    
    try:
        print("  Importing notion_listener...")
        from notion_listener import NotionListener
        print("  ✓ NotionListener imported")
        
        print("  Importing mastodon_listener...")
        from mastodon_listener import MastodonListener
        print("  ✓ MastodonListener imported")
        
        print("\n  ✅ Listener import tests passed!")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_enhanced_llm():
    """Test enhanced LLM functions."""
    print("\n" + "="*60)
    print("TEST 5: Enhanced LLM Functions")
    print("="*60)
    
    try:
        print("  Importing generate_social_post...")
        from llm import generate_social_post
        print("  ✓ generate_social_post imported")
        
        print("  Importing generate_comment_reply...")
        from llm import generate_comment_reply
        print("  ✓ generate_comment_reply imported")
        
        print("\n  ✅ LLM enhancement tests passed!")
        print("  ⚠️  Note: Actual generation requires OPENROUTER_API_KEY")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" SOFT BATCH - NEW FEATURES TEST SUITE")
    print("="*70)
    
    tests = [
        ("Chunking", test_chunking),
        ("Database", test_database),
        ("RAG System", test_rag_mock),
        ("Listeners", test_listeners_import),
        ("LLM Enhancements", test_enhanced_llm),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n  ✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n  Result: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n  🎉 All tests passed! Your soft_batch installation is ready.")
        print("\n  Next steps:")
        print("    1. Set up environment variables (NOTION_API_KEY, etc.)")
        print("    2. Run: python main.py sync")
        print("    3. Run: python main.py (try RAG-enhanced post generation)")
        print("    4. Optional: Start listeners with python main.py notion-listen")
    else:
        print("\n  ⚠️  Some tests failed. Check the output above.")
    
    print("="*70 + "\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
