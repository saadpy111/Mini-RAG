import os
import sys
from io import BytesIO
from pathlib import Path

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from starlette.datastructures import Headers, UploadFile

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# A fresh checkout has no .env file. The application settings require a
# MongoDB URI at import time even for tests that never connect to MongoDB.
if not (ROOT_DIR / ".env").exists():
    os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")

import main  # noqa: E402
from src.business_logic.asset_business_logic import AssetBusinessLogic  # noqa: E402
from src.business_logic.chunk_business_logic import ChunkBusinessLogic  # noqa: E402
from src.business_logic.project_business_logic import ProjectBusinessLogic  # noqa: E402
from src.models.asset import Asset  # noqa: E402
from src.models.data_chunk import DataChunk  # noqa: E402
from src.models.project import Project  # noqa: E402
from src.services import project_service  # noqa: E402


@pytest.fixture
def api_app():
    main.app.dependency_overrides.clear()
    yield main.app
    main.app.dependency_overrides.clear()


@pytest.fixture
def client(api_app):
    # Deliberately not used as a context manager: that would execute the
    # application lifespan and open a real MongoDB connection.
    test_client = TestClient(api_app, raise_server_exceptions=False)
    yield test_client
    test_client.close()


@pytest.fixture
def override_business_logic(api_app):
    def _override(dependency, value):
        api_app.dependency_overrides[dependency] = lambda: value

    return _override


@pytest.fixture
def project_bl():
    from unittest.mock import AsyncMock

    return AsyncMock(spec=ProjectBusinessLogic)


@pytest.fixture
def asset_bl():
    from unittest.mock import AsyncMock

    return AsyncMock(spec=AssetBusinessLogic)


@pytest.fixture
def chunk_bl():
    from unittest.mock import AsyncMock

    return AsyncMock(spec=ChunkBusinessLogic)


@pytest.fixture
def temp_files_dir(monkeypatch, tmp_path):
    files_dir = tmp_path / "files"
    monkeypatch.setattr(project_service, "get_files_dir", lambda: files_dir)
    return files_dir


@pytest.fixture
def make_upload_file():
    def _make(filename="notes.txt", content=b"hello", content_type="text/plain"):
        return UploadFile(
            file=BytesIO(content),
            size=len(content),
            filename=filename,
            headers=Headers({"content-type": content_type}),
        )

    return _make


@pytest.fixture
def project():
    return Project(id=ObjectId(), project_id="project-1")


@pytest.fixture
def make_project():
    def _make(project_id="project-1", object_id=None):
        return Project(
            id=object_id if object_id is not None else ObjectId(),
            project_id=project_id,
        )

    return _make


@pytest.fixture
def make_asset():
    def _make(
        project_id,
        file_id="file-1",
        asset_id=None,
        asset_name="stored.txt",
        asset_type=".txt",
        asset_size=5,
        asset_config=None,
    ):
        return Asset(
            id=asset_id if asset_id is not None else ObjectId(),
            asset_project_id=project_id,
            asset_type=asset_type,
            asset_name=asset_name,
            asset_size=asset_size,
            asset_config=asset_config
            if asset_config is not None
            else {
                "file_id": file_id,
                "original_filename": "notes.txt",
            },
        )

    return _make


@pytest.fixture
def asset(project, make_asset):
    return make_asset(project.id)


@pytest.fixture
def make_data_chunk():
    def _make(
        project_id,
        asset_id,
        text="chunk text",
        order=1,
        metadata=None,
        chunk_id=None,
    ):
        return DataChunk(
            id=chunk_id,
            chunk_text=text,
            chunk_metadata=metadata if metadata is not None else {},
            chunk_order=order,
            chunk_project_id=project_id,
            chunk_asset_id=asset_id,
        )

    return _make


@pytest.fixture
def documents():
    return [
        Document(
            page_content="First document content.",
            metadata={"source": "file-1.txt", "page": 1},
        ),
        Document(
            page_content="Second document content.",
            metadata={"source": "file-1.txt", "page": 2},
        ),
    ]


@pytest.fixture
def assert_api_envelope():
    def _assert(response, is_success, status_code=None, message=None):
        if status_code is not None:
            assert response.status_code == status_code

        body = response.json()
        assert set(body) == {"is_success", "message", "data"}
        assert body["is_success"] is is_success
        assert isinstance(body["message"], str)

        if message is not None:
            assert body["message"] == message
        if not is_success:
            assert body["data"] is None

        return body

    return _assert
