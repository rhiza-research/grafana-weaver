"""Tests for extract_external_content command."""

import json
from unittest.mock import patch, Mock

import pytest

from types import SimpleNamespace

from grafana_weaver.main import extract_external_content
from grafana_weaver.core.dashboard_extractor import DashboardExtractor


class TestDashboardExtractor:
    """Tests for DashboardExtractor class."""

    def test_compute_hash(self, tmp_path):
        """Same content should produce same hash."""
        extractor = DashboardExtractor(tmp_path)
        content1 = "SELECT * FROM table"
        content2 = "SELECT * FROM table"
        assert extractor._compute_hash(content1) == extractor._compute_hash(content2)

    def test_different_content_different_hash(self, tmp_path):
        """Different content should produce different hash."""
        extractor = DashboardExtractor(tmp_path)
        content1 = "SELECT * FROM table1"
        content2 = "SELECT * FROM table2"
        assert extractor._compute_hash(content1) != extractor._compute_hash(content2)

    def test_hash_length(self, tmp_path):
        """Hash should be 16 characters (truncated SHA-256)."""
        extractor = DashboardExtractor(tmp_path)
        content = "test content"
        hash_value = extractor._compute_hash(content)
        assert len(hash_value) == 16


class TestParseExternalParams:
    """Tests for parse_external_params method."""

    def test_no_params(self, tmp_path):
        """Line without parameters should return None."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL"
        assert extractor._parse_external_params(line) is None

    def test_with_params(self, tmp_path):
        """Line with parameters should return parsed dict."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL({panel_id: 'weekly-results', key: 'params'})"
        params = extractor._parse_external_params(line)
        assert params["panel_id"] == "weekly-results"
        assert params["key"] == "params"

    def test_quoted_values(self, tmp_path):
        """Quoted values should be parsed correctly."""
        extractor = DashboardExtractor(tmp_path)
        line = '// EXTERNAL({panel_id:"weekly-results", key:"params"})'
        params = extractor._parse_external_params(line)
        assert params["panel_id"] == "weekly-results"
        assert params["key"] == "params"


class TestDetermineFileExtension:
    """Tests for determine_file_extension method."""

    def test_javascript_detection(self, tmp_path):
        """JavaScript content should return .js extension."""
        extractor = DashboardExtractor(tmp_path)
        assert extractor._determine_file_extension("function foo() {}") == ".js"
        assert extractor._determine_file_extension("const x = 1;") == ".js"
        assert extractor._determine_file_extension("// comment\nfunction bar() {}") == ".js"

    def test_sql_detection(self, tmp_path):
        """SQL content should return .sql extension."""
        extractor = DashboardExtractor(tmp_path)
        assert extractor._determine_file_extension("SELECT * FROM table") == ".sql"
        assert extractor._determine_file_extension("select id from users") == ".sql"

    def test_html_detection(self, tmp_path):
        """HTML content should return .html extension."""
        extractor = DashboardExtractor(tmp_path)
        assert extractor._determine_file_extension("<div>test</div>") == ".html"
        assert extractor._determine_file_extension("<html><body></body></html>") == ".html"

    def test_markdown_detection(self, tmp_path):
        """Markdown content should return .md extension."""
        extractor = DashboardExtractor(tmp_path)
        assert extractor._determine_file_extension("# Header") == ".md"
        assert extractor._determine_file_extension("## Subheader") == ".md"

    def test_fallback_to_txt(self, tmp_path):
        """Unknown content should return .txt extension."""
        extractor = DashboardExtractor(tmp_path)
        assert extractor._determine_file_extension("random text content") == ".txt"


class TestExtractFilenameFromLine:
    """Tests for extract_filename_from_line method."""

    def test_no_filename(self, tmp_path):
        """Line without filename should return None."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL"
        assert extractor._extract_filename_from_line(line) is None

    def test_simple_filename(self, tmp_path):
        """Simple filename should be extracted."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL:colors.js"
        assert extractor._extract_filename_from_line(line) == "colors.js"

    def test_filename_with_params(self, tmp_path):
        """Filename with parameters should be extracted."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL({key:'foo'}):data.sql"
        assert extractor._extract_filename_from_line(line) == "data.sql"


class TestGenerateFilename:
    """Tests for generate_filename method."""

    def test_dashboard_level_content(self, tmp_path):
        """Dashboard-level content should not include panel ID."""
        extractor = DashboardExtractor(tmp_path)
        root_data = {"uid": "dash123"}
        filename = extractor._generate_filename("SELECT * FROM foo", "query", root_data, "templating.query")
        assert filename == "dash123-query.sql"

    def test_panel_level_content(self, tmp_path):
        """Panel-level content should include panel ID."""
        extractor = DashboardExtractor(tmp_path)
        root_data = {"uid": "dash123", "panels": [{"id": 5}]}
        filename = extractor._generate_filename("function() {}", "script", root_data, "panels[0].options.script")
        assert filename == "dash123-5-script.js"

    def test_param_overrides(self, tmp_path):
        """Parameters should override generated values."""
        extractor = DashboardExtractor(tmp_path)
        root_data = {"uid": "dash123"}
        params = {"dashboard_id": "custom", "key": "myquery", "ext": "txt"}
        filename = extractor._generate_filename("content", "query", root_data, "path", params)
        assert filename == "custom-myquery.txt"


class TestSplitOnExternal:
    """Tests for split_on_external method."""

    def test_single_external(self, tmp_path):
        """Single EXTERNAL marker should return one segment."""
        extractor = DashboardExtractor(tmp_path)
        value = "// EXTERNAL\nfunction foo() {}"
        segments = extractor._split_on_external(value)
        assert len(segments) == 1
        assert segments[0][0] == "// EXTERNAL"
        assert "function foo()" in segments[0][1]

    def test_multiple_externals(self, tmp_path):
        """Multiple EXTERNAL markers should return multiple segments."""
        extractor = DashboardExtractor(tmp_path)
        value = "// EXTERNAL:part1.js\nfunction foo() {}\n// EXTERNAL:part2.js\nfunction bar() {}"
        segments = extractor._split_on_external(value)
        assert len(segments) == 2
        assert "part1.js" in segments[0][0]
        assert "part2.js" in segments[1][0]


class TestExtractFromFile:
    """Tests for DashboardExtractor.extract_from_file method."""

    def test_extract_simple_dashboard(self, tmp_path):
        """Simple dashboard without EXTERNAL should be processed."""
        json_file = tmp_path / "dashboard.json"
        json_file.write_text('{"uid": "test", "title": "Test Dashboard", "panels": []}')

        output_dir = tmp_path / "output"
        extractor = DashboardExtractor(output_dir)

        success = extractor.extract_from_file(json_file)

        assert success
        # Check that jsonnet file was created
        jsonnet_file = output_dir / "src" / "dashboard.jsonnet"
        assert jsonnet_file.exists()

    def test_extract_dashboard_with_external(self, tmp_path):
        """Dashboard with EXTERNAL content should extract assets."""
        dashboard_json = {
            "uid": "test",
            "title": "Test Dashboard",
            "panels": [{"id": 1, "options": {"script": "// EXTERNAL\nfunction foo() {}"}}],
        }

        json_file = tmp_path / "dashboard.json"
        json_file.write_text(json.dumps(dashboard_json))

        output_dir = tmp_path / "output"
        extractor = DashboardExtractor(output_dir)

        success = extractor.extract_from_file(json_file)

        assert success
        # Check that jsonnet and asset files were created
        jsonnet_file = output_dir / "src" / "dashboard.jsonnet"
        assert jsonnet_file.exists()

        assets_dir = output_dir / "src" / "assets"
        # Should have created an asset file
        assert assets_dir.exists()
        asset_files = list(assets_dir.glob("*.js"))
        assert len(asset_files) > 0

    def test_extract_nonexistent_file(self, tmp_path):
        """Nonexistent file should return False."""
        output_dir = tmp_path / "output"
        extractor = DashboardExtractor(output_dir)
        success = extractor.extract_from_file(tmp_path / "nonexistent.json")
        assert not success

    def test_extract_invalid_json(self, tmp_path):
        """Invalid JSON should return False."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        output_dir = tmp_path / "output"
        extractor = DashboardExtractor(output_dir)

        success = extractor.extract_from_file(json_file)
        assert not success


class TestCreateExternalLine:
    """Tests for create_external_line method."""

    def test_add_filename_to_simple_external(self, tmp_path):
        """Filename should be added to simple EXTERNAL line."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL"
        result = extractor._create_external_line(line, "colors.js")
        assert "EXTERNAL:colors.js" in result
        assert result.startswith("//")

    def test_replace_existing_filename(self, tmp_path):
        """Existing filename should be replaced."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL:old.js"
        result = extractor._create_external_line(line, "new.js")
        assert "EXTERNAL:new.js" in result
        assert "old.js" not in result

    def test_preserve_params(self, tmp_path):
        """Parameters should be preserved."""
        extractor = DashboardExtractor(tmp_path)
        line = "// EXTERNAL({key:'foo'}):old.sql"
        result = extractor._create_external_line(line, "new.sql")
        assert "{key:'foo'}" in result
        assert "new.sql" in result
        assert "old.sql" not in result


class TestMain:
    """Tests for main CLI function."""

    @patch("grafana_weaver.main.DashboardExtractor")
    def test_main_success(self, mock_extractor_class, tmp_path):
        """Should create DashboardExtractor and exit with 0 on success."""
        mock_extractor = Mock()
        mock_extractor.extract_from_file.return_value = True
        mock_extractor_class.return_value = mock_extractor

        test_file = tmp_path / "dashboard.json"
        test_file.write_text("{}")

        args = SimpleNamespace(
            json_file=test_file,
            dashboard_dir=tmp_path / "dashboards",
            base_dir=None
        )

        with pytest.raises(SystemExit) as exc_info:
            extract_external_content(args)
        assert exc_info.value.code == 0

        # Verify DashboardExtractor was created with correct root_dir
        mock_extractor_class.assert_called_once()
        call_args = mock_extractor_class.call_args[0]
        assert call_args[0] == tmp_path / "dashboards"

        # Verify extract_from_file was called
        mock_extractor.extract_from_file.assert_called_once()

    @patch("grafana_weaver.main.DashboardExtractor")
    def test_main_failure(self, mock_extractor_class, tmp_path):
        """Should exit with 1 on failure."""
        mock_extractor = Mock()
        mock_extractor.extract_from_file.return_value = False
        mock_extractor_class.return_value = mock_extractor

        test_file = tmp_path / "dashboard.json"
        test_file.write_text("{}")

        args = SimpleNamespace(
            json_file=test_file,
            dashboard_dir=tmp_path / "dashboards",
            base_dir=None
        )

        with pytest.raises(SystemExit) as exc_info:
            extract_external_content(args)
        assert exc_info.value.code == 1

    def test_main_uses_dashboard_dir(self, tmp_path):
        """Should use dashboard_dir from args."""
        # Set up environment
        custom_dir = tmp_path / "custom-dashboards"
        custom_dir.mkdir()

        # Create test dashboard
        test_file = tmp_path / "dashboard.json"
        test_file.write_text('{"uid": "test", "title": "Test"}')

        args = SimpleNamespace(
            json_file=test_file,
            dashboard_dir=custom_dir,
            base_dir=None
        )

        with pytest.raises(SystemExit) as exc_info:
            extract_external_content(args)
        assert exc_info.value.code == 0

        # Verify template was created in the specified directory
        assert (custom_dir / "src" / "dashboard.jsonnet").exists()

    @patch("grafana_weaver.main.DashboardExtractor")
    def test_main_with_base_dir(self, mock_extractor_class, tmp_path):
        """Should pass through base_dir option to extract_from_file."""
        mock_extractor = Mock()
        mock_extractor.extract_from_file.return_value = True
        mock_extractor_class.return_value = mock_extractor

        test_file = tmp_path / "dashboard.json"
        test_file.write_text("{}")

        base_dir = tmp_path / "base"
        base_dir.mkdir()

        args = SimpleNamespace(
            json_file=test_file,
            dashboard_dir=tmp_path / "output",
            base_dir=base_dir
        )

        with pytest.raises(SystemExit):
            extract_external_content(args)

        # Verify extract_from_file was called with base_dir
        mock_extractor.extract_from_file.assert_called_once()
        call_kwargs = mock_extractor.extract_from_file.call_args[1]
        assert call_kwargs["base_dir"] == base_dir
