"""Tests for conversation_store — image_data / image_media_type persistence."""
import pytest


@pytest.fixture
def db_conversation(isolated_store):
    """Create a fresh conversation and yield its id."""
    conv = isolated_store.create_conversation(title="test conv")
    return conv["id"]


def test_add_message_stores_image_data(db_conversation):
    """add_message persists image bytes and media type."""
    from backend import conversation_store
    conv_id = db_conversation
    img_bytes = b"\x89PNG\r\n\x1a\n"  # PNG magic bytes
    msg = conversation_store.add_message(
        conv_id, "user", "what is this diagram?",
        image_data=img_bytes,
        image_media_type="image/png",
    )
    assert msg["image_data"] == img_bytes
    assert msg["image_media_type"] == "image/png"


def test_get_conversation_includes_image_data(db_conversation):
    """get_conversation returns image_data on messages that have it."""
    from backend import conversation_store
    conv_id = db_conversation
    img_bytes = b"\x89PNG\r\n\x1a\n"
    conversation_store.add_message(
        conv_id, "user", "describe this",
        image_data=img_bytes,
        image_media_type="image/png",
    )
    conv = conversation_store.get_conversation(conv_id)
    msg = conv["messages"][0]
    assert msg["image_data"] == img_bytes
    assert msg["image_media_type"] == "image/png"


def test_add_message_without_image_keeps_columns_null(db_conversation):
    """add_message without image leaves image columns as None."""
    from backend import conversation_store
    conv_id = db_conversation
    msg = conversation_store.add_message(conv_id, "user", "no image here")
    assert msg["image_data"] is None
    assert msg["image_media_type"] is None
