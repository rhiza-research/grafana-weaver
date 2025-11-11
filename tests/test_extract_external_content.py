"""Tests for extract_external_content.py module."""

import json

import pytest

from grafana_weaver.extract_external_content import (
    compute_content_hash,
    create_external_line,
    create_jsonnet,
    determine_file_extension,
    extract_external_content,
    extract_filename_from_external_line,
    generate_filename,
    load_existing_asset_hashes,
    parse_external_params,
    process_json_file,
    split_on_external,
)


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        content1 = "SELECT * FROM table"
        content2 = "SELECT * FROM table"
        assert compute_content_hash(content1) == compute_content_hash(content2)

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        content1 = "SELECT * FROM table1"
        content2 = "SELECT * FROM table2"
        assert compute_content_hash(content1) != compute_content_hash(content2)

    def test_hash_length(self):
        """Hash should be 16 characters (truncated SHA-256)."""
        content = "test content"
        hash_value = compute_content_hash(content)
        assert len(hash_value) == 16


class TestParseExternalParams:
    """Tests for parse_external_params function."""

    def test_no_params(self):
        """Line without parameters should return None."""
        line = "// EXTERNAL"
        assert parse_external_params(line) is None

    def test_single_param(self):
        """Single parameter should be parsed correctly."""
        line = "// EXTERNAL({key: 'value'})"
        result = parse_external_params(line)
        assert result == {"key": "value"}

    def test_multiple_params(self):
        """Multiple parameters should be parsed correctly."""
        line = "// EXTERNAL({panel_id: 'test', key: 'script', ext: 'js'})"
        result = parse_external_params(line)
        assert result == {"panel_id": "test", "key": "script", "ext": "js"}

    def test_params_with_quotes(self):
        """Parameters with various quote styles should be parsed."""
        line = "// EXTERNAL({key: \"value\", key2: 'value2'})"
        result = parse_external_params(line)
        assert result == {"key": "value", "key2": "value2"}


class TestDetermineFileExtension:
    """Tests for determine_file_extension function."""

    def test_javascript_detection(self):
        """JavaScript content should be detected."""
        content = "function foo() { return 'bar'; }"
        assert determine_file_extension(content) == ".js"

    def test_javascript_arrow_function(self):
        """Arrow function syntax should be detected as JavaScript."""
        content = "const foo = () => 'bar';"
        assert determine_file_extension(content) == ".js"

    def test_sql_detection(self):
        """SQL content should be detected."""
        content = "SELECT * FROM table WHERE id = 1"
        assert determine_file_extension(content) == ".sql"

    def test_html_detection(self):
        """HTML content should be detected."""
        content = "<div>Hello World</div>"
        assert determine_file_extension(content) == ".html"

    def test_markdown_detection(self):
        """Markdown content should be detected."""
        content = "# Header\n## Subheader"
        assert determine_file_extension(content) == ".md"

    def test_default_fallback(self):
        """Unknown content should default to .txt."""
        content = "Some random text"
        assert determine_file_extension(content) == ".txt"


class TestExtractFilenameFromExternalLine:
    """Tests for extract_filename_from_external_line function."""

    def test_simple_filename(self):
        """Simple EXTERNAL:filename format should be parsed."""
        line = "// EXTERNAL:colors.js"
        assert extract_filename_from_external_line(line) == "colors.js"

    def test_filename_with_params(self):
        """Filename with parameters should be parsed."""
        line = "// EXTERNAL({key: 'foo'}):data.sql"
        assert extract_filename_from_external_line(line) == "data.sql"

    def test_no_filename(self):
        """EXTERNAL without filename should return None."""
        line = "// EXTERNAL"
        assert extract_filename_from_external_line(line) is None

    def test_markdown_comment_style(self):
        """Markdown comment style should be parsed."""
        line = "[comment]: # (EXTERNAL:readme.md)"
        assert extract_filename_from_external_line(line) == "readme.md"


class TestGenerateFilename:
    """Tests for generate_filename function."""

    def test_panel_script_filename(self):
        """Panel script should generate filename with panel ID."""
        content = "function foo() {}"
        key = "script"
        root_data = {"uid": "test-dash", "panels": [{"id": 5}]}
        path = "panels[0].options.script"

        filename = generate_filename(content, key, root_data, path)
        assert filename == "test-dash-5-script.js"

    def test_dashboard_level_query(self):
        """Dashboard-level query should not include panel ID."""
        content = "SELECT * FROM foo"
        key = "query"
        root_data = {"uid": "test-dash"}
        path = "templating.query"

        filename = generate_filename(content, key, root_data, path)
        assert filename == "test-dash-query.sql"

    def test_params_override(self):
        """Parameters should override default values."""
        content = "test"
        key = "script"
        root_data = {"uid": "test-dash", "panels": [{"id": 1}]}
        path = "panels[0].options.script"
        params = {"panel_id": "custom", "key": "params", "ext": "txt"}

        filename = generate_filename(content, key, root_data, path, params)
        assert filename == "test-dash-custom-params.txt"


class TestCreateExternalLine:
    """Tests for create_external_line function."""

    def test_simple_external(self):
        """Simple EXTERNAL line should be created."""
        original = "// EXTERNAL"
        filename = "colors.js"
        result = create_external_line(original, filename)
        assert result == "// EXTERNAL:colors.js"

    def test_preserve_params(self):
        """Parameters should be preserved."""
        original = "// EXTERNAL({key: 'foo'})"
        filename = "data.sql"
        result = create_external_line(original, filename)
        assert "EXTERNAL({key: 'foo'}):data.sql" in result

    def test_replace_existing_filename(self):
        """Existing filename should be replaced."""
        original = "// EXTERNAL:old.js"
        filename = "new.js"
        result = create_external_line(original, filename)
        assert result == "// EXTERNAL:new.js"


class TestSplitOnExternal:
    """Tests for split_on_external function."""

    def test_single_external(self):
        """Single EXTERNAL marker should be split correctly."""
        value = "// EXTERNAL\nfunction foo() {}"
        segments = split_on_external(value)
        assert len(segments) == 1
        assert segments[0][0] == "// EXTERNAL"
        assert segments[0][1] == "function foo() {}"

    def test_multiple_externals(self):
        """Multiple EXTERNAL markers should be split correctly."""
        value = "// EXTERNAL:part1.js\ncode1\n// EXTERNAL:part2.js\ncode2"
        segments = split_on_external(value)
        assert len(segments) == 2
        assert segments[0][0] == "// EXTERNAL:part1.js"
        assert segments[0][1] == "code1"
        assert segments[1][0] == "// EXTERNAL:part2.js"
        assert segments[1][1] == "code2"


class TestLoadExistingAssetHashes:
    """Tests for load_existing_asset_hashes function."""

    def test_empty_directory(self, temp_dir):
        """Empty directory should return empty dict."""
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()
        result = load_existing_asset_hashes(assets_dir)
        assert result == {}

    def test_nonexistent_directory(self, temp_dir):
        """Nonexistent directory should return empty dict."""
        assets_dir = temp_dir / "nonexistent"
        result = load_existing_asset_hashes(assets_dir)
        assert result == {}

    def test_existing_files(self, temp_dir):
        """Existing files should be hashed."""
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()

        file1 = assets_dir / "test1.js"
        file1.write_text("content1")

        file2 = assets_dir / "test2.sql"
        file2.write_text("content2")

        result = load_existing_asset_hashes(assets_dir)
        assert len(result) == 2
        assert "test1.js" in result
        assert "test2.sql" in result


class TestCreateJsonnet:
    """Tests for create_jsonnet function."""

    def test_no_modifications(self):
        """Dashboard without EXTERNAL should return plain JSON."""
        data = {"uid": "test", "title": "Test"}
        modifications = []
        result = create_jsonnet(data, modifications)
        assert '"uid": "test"' in result
        assert "importstr" not in result

    def test_single_import(self):
        """Single EXTERNAL should create importstr."""
        data = {"script": "__colors_js__"}
        modifications = [{"filename": "colors.js", "var_name": "colors_js"}]
        result = create_jsonnet(data, modifications)
        assert "local colors_js = importstr './assets/colors.js';" in result
        assert '"script": colors_js' in result

    def test_multiple_imports(self):
        """Multiple EXTERNALs should create multiple importstr."""
        data = {"script": "__CONCAT__colors_js + utils_js__"}
        modifications = [
            {"filename": "colors.js", "var_name": "colors_js"},
            {"filename": "utils.js", "var_name": "utils_js"},
        ]
        result = create_jsonnet(data, modifications)
        assert "local colors_js = importstr './assets/colors.js';" in result
        assert "local utils_js = importstr './assets/utils.js';" in result
        assert '"script": colors_js + utils_js' in result


class TestExtractExternalIntegration:
    """Integration tests using test_data fixtures."""

    @pytest.mark.parametrize(
        "test_name",
        [
            "basic_extraction",
            "custom_filename",
            "parameterized_filename",
            "concatenated_external",
            "comment_preservation",
            "filename_starts_with_digit",
        ],
    )
    def test_json_to_jsonnet(self, test_name, temp_dir, test_data):
        """Test JSON to Jsonnet+assets extraction with real test data."""
        input_file = test_data.input_json(test_name)
        expected_jsonnet_file = test_data.expected_jsonnet(test_name)
        expected_assets_dir = test_data.assets(test_name)

        # Load input JSON
        with open(input_file) as f:
            data = json.load(f)

        # Create output directory in temp
        output_dir = temp_dir / "output"
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(parents=True)

        # Extract EXTERNAL content
        modifications = []
        asset_hashes = load_existing_asset_hashes(assets_dir)
        extract_external_content(
            data,
            assets_dir=assets_dir,
            root_data=data,
            modifications=modifications,
            asset_hashes=asset_hashes,
        )

        # Remove 'id' field
        if "id" in data:
            del data["id"]

        # Generate jsonnet
        actual_jsonnet = create_jsonnet(data, modifications)

        # Load expected jsonnet
        with open(expected_jsonnet_file) as f:
            expected_jsonnet = f.read()

        # Compare jsonnet output
        assert actual_jsonnet.strip() == expected_jsonnet.strip(), f"Jsonnet output doesn't match for {test_name}"

        # Compare asset files
        if expected_assets_dir.exists():
            for expected_asset in expected_assets_dir.iterdir():
                if expected_asset.is_file():
                    actual_asset = assets_dir / expected_asset.name
                    assert actual_asset.exists(), f"Expected asset {expected_asset.name} not created for {test_name}"

                    assert actual_asset.read_text() == expected_asset.read_text(), (
                        f"Asset {expected_asset.name} content doesn't match for {test_name}"
                    )

    @pytest.mark.parametrize(
        "test_name",
        [
            "basic_extraction",
            "custom_filename",
            "parameterized_filename",
            "concatenated_external",
            "comment_preservation",
            "filename_starts_with_digit",
        ],
    )
    def test_jsonnet_to_json_roundtrip(self, test_name, test_data):
        """Test building Jsonnet+assets back to JSON (round-trip test)."""
        import _jsonnet

        test_data_dir = test_data.dir(test_name)
        input_jsonnet = test_data.expected_jsonnet(test_name)
        input_json_file = test_data.input_json(test_name)
        assets_dir = test_data.assets(test_name)

        # Build jsonnet to JSON using Python jsonnet library
        json_str = _jsonnet.evaluate_file(str(input_jsonnet))
        actual_json = json.loads(json_str)

        # The actual JSON will have the content from asset files which includes
        # the EXTERNAL line with filename. We need to update the expected JSON
        # to match this by reading what's actually in the asset files.

        # Load expected JSON structure from input.json
        with open(input_json_file) as f:
            expected_json = json.load(f)

        # Remove 'id' field from expected if present (it gets stripped during extraction)
        if "id" in expected_json:
            del expected_json["id"]

        # Update expected JSON to have the content from asset files (with EXTERNAL headers)
        # Read all asset files and map them to their content
        asset_contents = {}
        if assets_dir.exists():
            for asset_file in assets_dir.iterdir():
                if asset_file.is_file():
                    asset_contents[asset_file.name] = asset_file.read_text()

        # Replace EXTERNAL markers in expected JSON with actual asset file content
        def replace_external_with_asset_content(obj):
            """Recursively find EXTERNAL markers and replace with asset content."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and "EXTERNAL" in value:
                        # Check if this field contains one or more EXTERNAL markers
                        # We need to handle both:
                        # 1. Single EXTERNAL (with or without filename) - match to single asset
                        # 2. Multiple EXTERNAL (concatenated) - match to multiple assets

                        # Split by lines and find all EXTERNAL markers
                        lines = value.split("\n")
                        external_lines = [line for line in lines if "EXTERNAL" in line]

                        if len(external_lines) == 1:
                            # Single EXTERNAL - find the matching asset
                            # The asset filename might be explicitly specified or auto-generated
                            external_line = external_lines[0]

                            # Check if there's an explicit filename after the params
                            # Format: EXTERNAL({params}):filename or EXTERNAL:filename
                            has_explicit_filename = False
                            if ":" in external_line:
                                # Check if the colon comes after params (if params exist)
                                if "}):" in external_line:
                                    # Has params AND explicit filename
                                    filename = external_line.split("}):")[1].strip()
                                    has_explicit_filename = True
                                elif "})" not in external_line:
                                    # No params, just filename
                                    filename = external_line.split(":", 1)[1].strip()
                                    has_explicit_filename = True

                            if has_explicit_filename and filename in asset_contents:
                                obj[key] = asset_contents[filename]
                            else:
                                # No explicit filename - match by content
                                # The content after the EXTERNAL line should match
                                content_after = value.split("\n", 1)[1] if "\n" in value else ""
                                for filename, asset_content in asset_contents.items():
                                    asset_parts = asset_content.split("\n", 1)
                                    asset_content_after = asset_parts[1] if len(asset_parts) > 1 else ""
                                    if asset_content_after.strip() == content_after.strip():
                                        obj[key] = asset_content
                                        break
                        elif len(external_lines) > 1:
                            # Multiple EXTERNAL markers - concatenate all matching assets
                            result_parts = []
                            for line in lines:
                                if "EXTERNAL" in line and ":" in line:
                                    filename = line.split(":", 1)[1].strip()
                                    if filename in asset_contents:
                                        result_parts.append(asset_contents[filename])

                            if result_parts:
                                obj[key] = "".join(result_parts)
                    else:
                        replace_external_with_asset_content(value)
            elif isinstance(obj, list):
                for item in obj:
                    replace_external_with_asset_content(item)

        replace_external_with_asset_content(expected_json)

        # Compare
        assert actual_json == expected_json, f"Built JSON doesn't match expected output for {test_name}"


class TestHashCheckingAndConflicts:
    """Tests for hash checking and conflict handling."""

    def test_skip_unchanged_file(self, temp_dir):
        """File should not be rewritten if content hasn't changed."""
        # Create initial asset file
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()
        asset_file = assets_dir / "test.js"
        asset_file.write_text("// EXTERNAL:test.js\nconst x = 1;\n")

        # Load existing hashes
        asset_hashes = load_existing_asset_hashes(assets_dir)

        # Process same content again
        data = {"script": "// EXTERNAL:test.js\nconst x = 1;"}
        modifications = []
        extract_external_content(
            data,
            assets_dir=assets_dir,
            root_data={"uid": "test"},
            modifications=modifications,
            asset_hashes=asset_hashes,
        )

        # File should not have been modified (mtime should be same)
        assert asset_file.read_text() == "// EXTERNAL:test.js\nconst x = 1;\n"

    def test_update_changed_file(self, temp_dir):
        """File should be rewritten if content has changed."""
        # Create initial asset file
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()
        asset_file = assets_dir / "test.js"
        asset_file.write_text("// EXTERNAL:test.js\nconst x = 1;\n")

        # Load existing hashes
        asset_hashes = load_existing_asset_hashes(assets_dir)

        # Process different content with same filename
        data = {"script": "// EXTERNAL:test.js\nconst x = 2;"}
        modifications = []
        extract_external_content(
            data,
            assets_dir=assets_dir,
            root_data={"uid": "test"},
            modifications=modifications,
            asset_hashes=asset_hashes,
        )

        # File should be updated
        assert asset_file.read_text() == "// EXTERNAL:test.js\nconst x = 2;\n"

    def test_conflict_detection(self, temp_dir, capsys, test_data):
        """Conflict file should be created when different content targets same filename."""
        input_file = test_data.input_json("conflict_detection")

        # Load input data
        with open(input_file) as f:
            data = json.load(f)

        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()

        modifications = []
        asset_hashes = load_existing_asset_hashes(assets_dir)
        extract_external_content(
            data,
            assets_dir=assets_dir,
            root_data=data,
            modifications=modifications,
            asset_hashes=asset_hashes,
        )

        # Main file should have first panel's content
        main_file = assets_dir / "shared.js"
        assert main_file.exists()
        assert "const version = 1;" in main_file.read_text()

        # Conflict file should exist with second panel's content
        conflict_file = assets_dir / "shared.js.conflict1"
        assert conflict_file.exists()
        assert "const version = 2;" in conflict_file.read_text()

        # Should print warning
        captured = capsys.readouterr()
        assert "WARNING: Conflict detected" in captured.out

    def test_same_content_multiple_panels(self, temp_dir, capsys, test_data):
        """No conflict when multiple panels have identical content for same filename."""
        input_file = test_data.input_json("same_content_multiple_panels")

        # Load input data
        with open(input_file) as f:
            data = json.load(f)

        assets_dir = temp_dir / "assets"
        assets_dir.mkdir()

        modifications = []
        asset_hashes = load_existing_asset_hashes(assets_dir)
        extract_external_content(
            data,
            assets_dir=assets_dir,
            root_data=data,
            modifications=modifications,
            asset_hashes=asset_hashes,
        )

        # Main file should exist
        main_file = assets_dir / "shared.js"
        assert main_file.exists()

        # No conflict file should exist
        conflict_file = assets_dir / "shared.js.conflict1"
        assert not conflict_file.exists()

        # Should print skip message, not warning
        captured = capsys.readouterr()
        assert "same content as first panel" in captured.out
        assert "WARNING" not in captured.out


class TestProcessJsonFile:
    """Tests for process_json_file function."""

    def test_invalid_json(self, temp_dir):
        """Invalid JSON should return False."""
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("not valid json {")

        success = process_json_file(invalid_file)
        assert not success

    def test_nonexistent_file(self, temp_dir):
        """Nonexistent file should return False."""
        nonexistent = temp_dir / "nonexistent.json"
        success = process_json_file(nonexistent)
        assert not success

    def test_successful_processing_with_external(self, temp_dir, capsys, test_data):
        """Successfully process a JSON file with EXTERNAL content."""
        input_file = test_data.input_json("cli_with_external")

        # Process the file with temp output directory
        success = process_json_file(str(input_file), output_dir=str(temp_dir))

        assert success

        # Check console output
        captured = capsys.readouterr()
        assert "Processing:" in captured.out
        assert "Dashboard ID: test-123" in captured.out
        assert "✓ Jsonnet template creation completed successfully" in captured.out

        # Check that files were created in temp_dir
        template_file = temp_dir / "src" / "input.jsonnet"
        assert template_file.exists()

        asset_files = list((temp_dir / "src" / "assets").glob("*.js"))
        assert len(asset_files) == 1

    def test_successful_processing_with_base_dir(self, temp_dir, capsys, test_data):
        """Successfully process a JSON file with base_dir parameter to preserve subdirectory structure."""
        # Create input directory structure: base/team1/input.json
        input_base = temp_dir / "input_base"
        input_subdir = input_base / "team1"
        input_subdir.mkdir(parents=True)

        # Copy test data into the subdirectory
        import shutil

        input_file = input_subdir / "input.json"
        shutil.copy(test_data.input_json("cli_with_subdir"), input_file)

        # Process with base_dir pointing to input_base
        output_root = temp_dir / "output"
        success = process_json_file(str(input_file), base_dir=str(input_base), output_dir=str(output_root))

        assert success

        # Check that subdirectory structure was preserved: output/src/team1/input.jsonnet
        template_file = output_root / "src" / "team1" / "input.jsonnet"
        assert template_file.exists()

        # Check that assets are in shared src/assets directory
        assets_dir = output_root / "src" / "assets"
        assert assets_dir.exists()

    def test_processing_without_external_content(self, temp_dir, capsys, test_data):
        """Process a JSON file without any EXTERNAL markers."""
        input_file = test_data.input_json("cli_without_external")

        # Process the file with temp output directory
        success = process_json_file(str(input_file), output_dir=str(temp_dir))

        assert success

        # Check console output
        captured = capsys.readouterr()
        assert "No EXTERNAL references found" in captured.out

        # Check that template was created
        template_file = temp_dir / "src" / "input.jsonnet"
        assert template_file.exists()
