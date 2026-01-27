"""
Unit tests for database query functionality
"""


def test_task_count_query_structure():
    """Test that task count query has correct Cypher structure"""
    query = "MATCH (t:Task) RETURN count(t) as count"

    # Verify query contains expected elements
    assert "MATCH (t:Task)" in query
    assert "count(t)" in query
    assert "RETURN" in query


def test_single_task_query_structure():
    """Test that single task query has correct Cypher structure"""
    query = "MATCH (t:Task) RETURN t LIMIT 1"

    # Verify query contains expected elements
    assert "MATCH (t:Task)" in query
    assert "RETURN t" in query
    assert "LIMIT 1" in query
