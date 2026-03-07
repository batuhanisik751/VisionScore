from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from visionscore.api.supabase_client import (
    SupabaseClient,
    get_supabase_client,
    reset_supabase_client,
)
from visionscore.models import (
    AnalysisReport,
    Grade,
    ImageMeta,
    TechnicalScore,
)


@pytest.fixture(autouse=True)
def _reset_client():
    """Ensure the module-level client cache is cleared between tests."""
    reset_supabase_client()
    yield
    reset_supabase_client()


@pytest.fixture
def mock_supabase_sdk():
    with patch("supabase.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client


@pytest.fixture
def client(mock_supabase_sdk) -> SupabaseClient:
    return SupabaseClient(url="https://test.supabase.co", key="test-key")


@pytest.fixture
def sample_report() -> AnalysisReport:
    return AnalysisReport(
        image_meta=ImageMeta(path="test.jpg", width=200, height=200, format="JPEG"),
        technical=TechnicalScore(sharpness=80, exposure=70, noise=60, dynamic_range=75, overall=71),
        overall_score=72.5,
        grade=Grade.B,
    )


# ---------------------------------------------------------------------------
# SupabaseClient tests
# ---------------------------------------------------------------------------


class TestUploadImage:
    async def test_uploads_and_returns_url(self, client, mock_supabase_sdk):
        storage_bucket = MagicMock()
        mock_supabase_sdk.storage.from_.return_value = storage_bucket
        storage_bucket.get_public_url.return_value = (
            "https://test.supabase.co/storage/v1/object/public/images/uploads/abc_photo.jpg"
        )

        url = await client.upload_image(b"fake-image-bytes", "photo.jpg")

        assert "photo.jpg" in url
        storage_bucket.upload.assert_called_once()
        storage_bucket.get_public_url.assert_called_once()


class TestSaveReport:
    async def test_inserts_and_returns_id(self, client, mock_supabase_sdk, sample_report):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.insert.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "abc-123"}])

        report_id = await client.save_report(sample_report, image_url="https://img.url")

        assert report_id == "abc-123"
        mock_supabase_sdk.table.assert_called_with("analysis_reports")
        table.insert.assert_called_once()
        row = table.insert.call_args[0][0]
        assert row["overall_score"] == 72.5
        assert row["grade"] == "B"
        assert row["image_url"] == "https://img.url"


class TestGetReport:
    async def test_returns_report_when_found(self, client, mock_supabase_sdk):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "abc-123", "overall_score": 72.5}])

        result = await client.get_report("abc-123")

        assert result is not None
        assert result["id"] == "abc-123"

    async def test_returns_none_when_not_found(self, client, mock_supabase_sdk):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])

        result = await client.get_report("nonexistent")

        assert result is None


class TestListReports:
    async def test_returns_reports_and_count(self, client, mock_supabase_sdk):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.select.return_value = table
        table.order.return_value = table
        table.range.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "1"}, {"id": "2"}], count=5)

        reports, total = await client.list_reports(limit=2, offset=0)

        assert len(reports) == 2
        assert total == 5
        table.range.assert_called_once_with(0, 1)


class TestDeleteReport:
    async def test_returns_true_when_deleted(self, client, mock_supabase_sdk):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[{"id": "abc-123"}])

        result = await client.delete_report("abc-123")

        assert result is True

    async def test_returns_false_when_not_found(self, client, mock_supabase_sdk):
        table = MagicMock()
        mock_supabase_sdk.table.return_value = table
        table.delete.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])

        result = await client.delete_report("nonexistent")

        assert result is False


# ---------------------------------------------------------------------------
# get_supabase_client tests
# ---------------------------------------------------------------------------


class TestGetSupabaseClient:
    def test_returns_none_when_unconfigured(self):
        with patch("visionscore.api.supabase_client.Settings") as MockSettings:
            MockSettings.return_value = MagicMock(supabase_url=None, supabase_key=None)
            result = get_supabase_client()
            assert result is None

    def test_returns_client_when_configured(self, mock_supabase_sdk):
        with patch("visionscore.api.supabase_client.Settings") as MockSettings:
            MockSettings.return_value = MagicMock(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
            )
            result = get_supabase_client()
            assert result is not None
            assert isinstance(result, SupabaseClient)

    def test_caches_client_instance(self, mock_supabase_sdk):
        with patch("visionscore.api.supabase_client.Settings") as MockSettings:
            MockSettings.return_value = MagicMock(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
            )
            client1 = get_supabase_client()
            client2 = get_supabase_client()
            assert client1 is client2
