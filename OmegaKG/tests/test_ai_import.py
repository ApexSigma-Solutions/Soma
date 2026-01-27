from unittest.mock import MagicMock, patch

import pytest

from omega_kg.ai_import import AIConversationImporter


@pytest.fixture
def mock_driver():
    with patch("omega_kg.ai_import.GraphDatabase.driver") as mock:
        yield mock


@pytest.fixture
def mock_settings():
    with patch("omega_kg.ai_import.settings") as mock:
        mock.neo4j_uri = "bolt://localhost:7687"
        mock.neo4j_user = "neo4j"
        mock.neo4j_password = "password"
        mock.obsidian_vault_path = "/tmp/vault"
        mock.ai_conversations_path = None
        yield mock


@pytest.mark.unit
def test_importer_initialization(mock_driver, mock_settings, tmp_path):
    # Mock settings.obsidian_vault_path to be tmp_path
    mock_settings.obsidian_vault_path = str(tmp_path)

    importer = AIConversationImporter()

    assert importer.vault_path == tmp_path.resolve()
    assert (tmp_path / "AI Conversations").exists()
    mock_driver.assert_called_once()


@pytest.mark.unit
def test_extract_tags(mock_driver, mock_settings, tmp_path):
    mock_settings.obsidian_vault_path = str(tmp_path)
    importer = AIConversationImporter()

    tags = importer._extract_tags("Test Title #python #code")
    assert "python" in tags
    assert "code" in tags
    assert len(tags) == 2


@pytest.mark.unit
def test_sanitize_title(mock_driver, mock_settings, tmp_path):
    mock_settings.obsidian_vault_path = str(tmp_path)
    importer = AIConversationImporter()

    title = "Title with <illegal> chars?"
    safe = importer._sanitize_title(title)
    assert "<" not in safe
    assert "?" not in safe
    assert "_" in safe


@pytest.mark.unit
def test_find_claude_conversations(mock_driver, mock_settings, tmp_path):
    mock_settings.obsidian_vault_path = str(tmp_path)

    # Create valid structure
    resources = tmp_path / "Resources"
    claude_dir = resources / "AI_Conversations" / "Claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "conversations.json").touch()

    importer = AIConversationImporter(resources_path=resources)
    found = importer.find_claude_conversations()

    assert found is not None
    assert found.name == "conversations.json"


@pytest.mark.unit
def test_import_conversation_flow(mock_driver, mock_settings, tmp_path):
    """Test the full import flow with mocked Neo4j calls but real file writing"""
    mock_settings.obsidian_vault_path = str(tmp_path)

    # Mock the driver session and run
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session

    importer = AIConversationImporter()

    # Ensure the conversation directory exists (should be created by __init__)
    assert importer.conversation_dir.exists(), (
        "conversation_dir should exist after init"
    )

    messages = [
        {"role": "user", "content": "Hello", "created_at": "2023-01-01T12:00:00"},
        {
            "role": "assistant",
            "content": "Hi there",
            "created_at": "2023-01-01T12:00:01",
        },
    ]

    importer._import_conversation(
        platform="test_platform",
        conversation_id="12345",
        title="Test Chat",
        messages=messages,
        created_at="2023-01-01T12:00:00",
    )

    # Verify file created - use the actual path from importer
    # Note: _sanitize_title preserves spaces, so filename has space
    expected_file = importer.conversation_dir / "test_platform_Test Chat_12345.md"

    assert expected_file.exists(), f"Expected file at {expected_file}"
    content = expected_file.read_text(encoding="utf-8")
    assert "# Test Chat" in content
    assert 'ai-platform: "test_platform"' in content

    # Verify Neo4j calls
    # Should create session, query, response
    assert mock_session.run.call_count >= 3
    # Verify Neo4j calls
    # Should create session, query, response
    assert mock_session.run.call_count >= 3
