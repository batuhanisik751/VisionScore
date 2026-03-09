from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from pydantic import BaseModel

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.models import ImageMeta
from visionscore.pipeline.loader import LoadedImage
from visionscore.plugins.info import PluginInfo
from visionscore.plugins.registry import PluginRegistry


# -- helpers --

class _DummyResult(BaseModel):
    overall: float = 50.0


class _DummyPlugin(BaseAnalyzer):
    plugin_info = PluginInfo(name="dummy", display_name="Dummy", version="0.1.0")

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel:
        return _DummyResult()


class _AltPlugin(BaseAnalyzer):
    plugin_info = PluginInfo(name="dummy", display_name="Alt Dummy", version="0.2.0")

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel:
        return _DummyResult()


# -- tests --

class TestPluginRegistry:
    def test_register_and_retrieve(self) -> None:
        reg = PluginRegistry()
        reg.register(_DummyPlugin, _DummyPlugin.plugin_info)

        assert reg.get("dummy") is not None
        info, cls = reg.get("dummy")  # type: ignore[misc]
        assert info.name == "dummy"
        assert cls is _DummyPlugin
        assert len(reg.get_all()) == 1

    def test_unregister(self) -> None:
        reg = PluginRegistry()
        reg.register(_DummyPlugin, _DummyPlugin.plugin_info)
        reg.unregister("dummy")

        assert reg.get("dummy") is None
        assert len(reg.get_all()) == 0

    def test_duplicate_name_overwrites(self) -> None:
        reg = PluginRegistry()
        reg.register(_DummyPlugin, _DummyPlugin.plugin_info)
        reg.register(_AltPlugin, _AltPlugin.plugin_info)

        info, cls = reg.get("dummy")  # type: ignore[misc]
        assert cls is _AltPlugin
        assert info.display_name == "Alt Dummy"
        assert len(reg.get_all()) == 1

    def test_discover_directory(self, tmp_path: Path) -> None:
        plugin_code = textwrap.dedent("""\
            from pydantic import BaseModel
            from visionscore.analyzers.base import BaseAnalyzer
            from visionscore.models import ImageMeta
            from visionscore.pipeline.loader import LoadedImage
            from visionscore.plugins.info import PluginInfo

            class DiscResult(BaseModel):
                overall: float = 42.0

            class DiscoverMe(BaseAnalyzer):
                plugin_info = PluginInfo(
                    name="discovered",
                    display_name="Discovered Plugin",
                )

                def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel:
                    return DiscResult()
        """)
        (tmp_path / "disc_plugin.py").write_text(plugin_code)

        reg = PluginRegistry()
        reg.discover_directory(tmp_path)

        assert reg.get("discovered") is not None

    def test_discover_directory_invalid_module_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "bad_plugin.py").write_text("def this is invalid python !!!")

        reg = PluginRegistry()
        reg.discover_directory(tmp_path)

        assert len(reg.get_all()) == 0

    def test_discover_directory_no_plugin_info_skipped(self, tmp_path: Path) -> None:
        plugin_code = textwrap.dedent("""\
            from pydantic import BaseModel
            from visionscore.analyzers.base import BaseAnalyzer
            from visionscore.models import ImageMeta
            from visionscore.pipeline.loader import LoadedImage

            class NoInfoPlugin(BaseAnalyzer):
                def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel:
                    return BaseModel()
        """)
        (tmp_path / "noplugin.py").write_text(plugin_code)

        reg = PluginRegistry()
        reg.discover_directory(tmp_path)

        assert len(reg.get_all()) == 0

    def test_discover_entry_points_no_crash(self) -> None:
        reg = PluginRegistry()
        # Should not raise even when no matching entry points exist
        reg.discover_entry_points()
        # We just verify it didn't crash -- result depends on environment
