#!/usr/bin/env python3
"""Dashboard extractor for extracting EXTERNAL content from Grafana dashboard JSON files."""

import hashlib
import json
import re
from pathlib import Path


class DashboardExtractor:
    """Extractor for processing Grafana dashboards and extracting EXTERNAL content."""

    def __init__(self, root_dir: Path):
        """
        Initialize dashboard extractor.

        Args:
            root_dir: Root directory for dashboards (assets will be written to root_dir/src/assets)
        """
        self.root_dir = Path(root_dir)
        self.src_dir = self.root_dir / "src"
        self.assets_dir = self.src_dir / "assets"
        self._asset_hashes = {}  # Original state from disk
        self._written_this_run = set()  # Files written in this run
        self._written_hashes = {}  # Hashes of written files
        self._modifications = []  # Track all modifications

    def extract_from_file(self, json_file: Path, base_dir: Path = None) -> bool:
        """
        Main entry point: extract EXTERNAL content from a dashboard JSON file.

        Args:
            json_file: Path to the Grafana dashboard JSON file
            base_dir: Optional base input directory to preserve subdirectory structure

        Returns:
            True if successful, False if errors occurred
        """
        # Validate file exists
        if not json_file.exists():
            print(f"Error: File not found: {json_file}")
            return False

        # Load and parse JSON
        try:
            with open(json_file) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in file: {json_file}")
            print(f"JSON Error: {e}")
            return False

        # Set up output directory structure

        # Detect subdirectory structure if base_dir is provided
        if base_dir:
            json_file_abs = json_file.resolve()
            base_dir_abs = Path(base_dir).resolve()
            try:
                rel_path = json_file_abs.parent.relative_to(base_dir_abs)
                template_dir = self.src_dir / rel_path
            except ValueError:
                template_dir = self.src_dir
        else:
            template_dir = self.src_dir

        # Ensure directories exist
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        template_dir.mkdir(parents=True, exist_ok=True)

        # Print processing header
        dashboard_id = data.get("uid", data.get("id", "dashboard"))
        print(f"Processing: {json_file}")
        print(f"Dashboard ID: {dashboard_id}")
        print(f"Assets directory: {self.assets_dir}")
        print(f"Template directory: {template_dir}")
        print("=" * 50)

        # Load existing asset hashes
        print("\nLoading existing assets...")
        self._load_existing_assets()
        if self._asset_hashes:
            print(f"Found {len(self._asset_hashes)} existing asset(s)")
        else:
            print("No existing assets found")

        # Extract EXTERNAL content
        print("\nProcessing EXTERNAL content...")
        self._modifications = []
        self._extract_from_object(data, root_data=data)

        # Strip the root 'id' field
        if "id" in data:
            print(f"Removing root 'id' field: {data['id']}")
            del data["id"]

        # Set the root version field to '1'
        if "version" in data:
            print("Standardizing version field to 1")
            data["version"] = 1

        # Write jsonnet template
        template_path = template_dir / f"{json_file.stem}.jsonnet"
        self._write_jsonnet_template(data, template_path)

        # Print summary
        print(f"\nCreated template: {template_path}")
        if self._modifications:
            by_path = {}
            for mod in self._modifications:
                path = mod["path"]
                if path not in by_path:
                    by_path[path] = []
                by_path[path].append(mod["filename"])

            print(f"Extracted external content from {len(by_path)} locations:")
            for path, filenames in by_path.items():
                if len(filenames) > 1:
                    print(f"  {path} -> {len(filenames)} segments: {', '.join(filenames)}")
                else:
                    print(f"  {path} -> {filenames[0]}")
        else:
            print("No EXTERNAL references found - created jsonnet file without external assets.")

        print("\n✓ Jsonnet template creation completed successfully")
        return True

    def _load_existing_assets(self):
        """Load all existing asset files and compute their content hashes."""
        self._asset_hashes = {}

        if not self.assets_dir.exists():
            return

        for asset_file in self.assets_dir.glob("*"):
            if asset_file.is_file():
                try:
                    with open(asset_file) as f:
                        content = f.read()
                    self._asset_hashes[asset_file.name] = self._compute_hash(content)
                except Exception as e:
                    print(f"Warning: Could not read {asset_file.name}: {e}")

    def _compute_hash(self, content: str) -> str:
        """
        Compute SHA-256 hash of content.

        Args:
            content: String content to hash

        Returns:
            Hexadecimal hash string (first 16 characters)
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _extract_from_object(self, obj, path: str = "", root_data: dict = None):
        """
        Recursively traverse JSON structure to find and extract EXTERNAL content.

        Args:
            obj: Current object being traversed
            path: Current JSON path
            root_data: The complete dashboard JSON
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                if isinstance(value, str) and "EXTERNAL" in value.split("\n")[0]:
                    print(f"Found EXTERNAL at: {current_path}")
                    obj[key] = self._process_external_value(value, key, current_path, root_data)
                else:
                    self._extract_from_object(value, current_path, root_data)

        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                self._extract_from_object(item, f"{path}[{index}]", root_data)

    def _process_external_value(self, value: str, key: str, path: str, root_data: dict) -> str:
        """
        Process a JSON field value containing EXTERNAL marker(s).

        Args:
            value: The JSON field value containing EXTERNAL marker
            key: The JSON field name
            path: Full JSON path to this field
            root_data: Complete dashboard JSON

        Returns:
            Placeholder string for jsonnet template
        """
        segments = self._split_on_external(value)
        var_names = []

        for external_line, content in segments:
            params = self._parse_external_params(external_line)
            filename = self._extract_filename_from_line(external_line)

            if not filename:
                filename = self._generate_filename(content, key, root_data, path, params)

            new_external_line = self._create_external_line(external_line, filename)
            full_content = new_external_line + "\n" + content
            full_content_normalized = full_content.rstrip("\n") + "\n"
            new_hash = self._compute_hash(full_content_normalized)

            # Check if already written this run
            if filename in self._written_this_run:
                if self._written_hashes.get(filename) == new_hash:
                    print(f"  Skipping {filename} (same content as first panel)")
                else:
                    # Conflict - save to .conflict file
                    conflict_num = 1
                    while (self.assets_dir / f"{filename}.conflict{conflict_num}").exists():
                        conflict_num += 1

                    conflict_filename = f"{filename}.conflict{conflict_num}"
                    print(f"  ⚠️  WARNING: Conflict detected for {filename}")
                    print(f"      First write wins, saving conflicting content to {conflict_filename}")

                    conflict_file = self.assets_dir / conflict_filename
                    with open(conflict_file, "w") as f:
                        f.write(full_content_normalized)
            else:
                # Check if we need to write based on existing content
                should_write = True
                if filename in self._asset_hashes:
                    if self._asset_hashes[filename] == new_hash:
                        should_write = False
                        print(f"  Skipping {filename} (no changes)")
                    else:
                        print(f"  Updating {filename} (content changed)")
                else:
                    print(f"  Creating {filename}")

                if should_write:
                    asset_file = self.assets_dir / filename
                    with open(asset_file, "w") as f:
                        f.write(full_content_normalized)
                    self._written_this_run.add(filename)
                    self._written_hashes[filename] = new_hash

            # Generate variable name
            var_name = filename.replace("-", "_").replace(".", "_")
            if var_name[0].isdigit():
                var_name = "f_" + var_name
            var_names.append(var_name)

            self._modifications.append({"path": path, "filename": filename, "var_name": var_name})

        # Return placeholder
        if len(var_names) == 1:
            return f"__{var_names[0]}__"
        return f"__CONCAT__{' + '.join(var_names)}__"

    def _split_on_external(self, value: str) -> list[tuple[str, str]]:
        """
        Split a multi-line value into segments at EXTERNAL markers.

        Args:
            value: Multi-line string potentially containing EXTERNAL markers

        Returns:
            List of (external_line, content) tuples
        """
        lines = value.split("\n")
        segments = []
        current_external_line = None
        current_content = []

        for line in lines:
            if "EXTERNAL" in line:
                if current_external_line is not None:
                    segments.append((current_external_line, "\n".join(current_content)))

                current_external_line = line
                current_content = []
            else:
                if current_external_line is not None:
                    current_content.append(line)

        if current_external_line is not None:
            segments.append((current_external_line, "\n".join(current_content)))

        return segments

    def _parse_external_params(self, line: str) -> dict | None:
        """
        Parse parameters from EXTERNAL({...}) format.

        Args:
            line: Line containing EXTERNAL marker

        Returns:
            Dictionary of parameters or None
        """
        match = re.match(r".*EXTERNAL\s*\(\s*\{([^}]+)\}\s*\)", line)
        if not match:
            return None

        params = {}
        for pair in re.split(r",\s*", match.group(1)):
            kv_match = re.match(r'^\s*["\']?([^"\':\s]+)["\']?\s*:\s*["\']?([^"\']+)["\']?\s*$', pair)
            if kv_match:
                params[kv_match.group(1).strip()] = kv_match.group(2).strip()
        return params if params else None

    def _extract_filename_from_line(self, line: str) -> str | None:
        """
        Extract existing filename from EXTERNAL marker line.

        Args:
            line: Line containing EXTERNAL marker

        Returns:
            Filename if found, None otherwise
        """
        if "EXTERNAL" not in line or ":" not in line:
            return None

        params = self._parse_external_params(line)
        external_pos = line.find("EXTERNAL")
        after_external = line[external_pos + 8 :]

        if params:
            match = re.search(r"\([^)]*\{[^}]+\}\s*\)\s*:([^ \t\n\r:)}\]]+)", after_external)
            return match.group(1).strip() if match else None
        elif after_external.startswith(":"):
            match = re.match(r":([^ \t\n\r:)}\]]+)", after_external)
            return match.group(1).strip() if match else None

        return None

    def _generate_filename(self, content: str, key: str, root_data: dict, path: str, params: dict = None) -> str:
        """
        Generate a filename for external content.

        Args:
            content: The content to be saved
            key: The JSON field key
            root_data: The complete dashboard JSON
            path: JSON path to this field
            params: Optional parameters from EXTERNAL({...})

        Returns:
            Generated filename
        """
        dashboard_id = root_data.get("uid", root_data.get("id", "dashboard"))

        # Extract panel ID from path
        panel_id = None
        for part in path.split("."):
            if part.startswith("panels["):
                try:
                    panel_index = int(part[7:-1])
                    panels = root_data.get("panels", [])
                    if panel_index < len(panels):
                        panel_id = panels[panel_index].get("id")
                except (ValueError, IndexError, KeyError):
                    pass

        # Apply parameter overrides
        if params:
            dashboard_id = params.get("dashboard_id", dashboard_id)
            panel_id = params.get("panel_id", panel_id)
            key = params.get("key", key)
            ext = params.get("ext")
            if ext and not ext.startswith("."):
                ext = "." + ext
        else:
            ext = None

        if not ext:
            ext = self._determine_file_extension(content)

        if panel_id:
            return f"{dashboard_id}-{panel_id}-{key}{ext}"
        return f"{dashboard_id}-{key}{ext}"

    def _determine_file_extension(self, content: str) -> str:
        """
        Determine appropriate file extension based on content.

        Args:
            content: The content string to analyze

        Returns:
            File extension including leading dot
        """
        content_lower = content.lower().strip()

        js_indicators = [
            content_lower.startswith("function"),
            content_lower.startswith("const "),
            content_lower.startswith("let "),
            content_lower.startswith("var "),
            content_lower.startswith("//"),
            "function(" in content_lower,
            "=>" in content_lower,
            "console.log" in content_lower,
            content_lower.startswith("return {"),
            " = {" in content_lower and "\n" in content,
        ]
        if any(js_indicators):
            return ".js"
        elif content_lower.startswith("<") or "<html" in content_lower:
            return ".html"
        elif content_lower.startswith("#") or content_lower.startswith("##"):
            return ".md"
        elif "select" in content_lower and "from" in content_lower:
            return ".sql"
        return ".txt"

    def _create_external_line(self, original_line: str, filename: str) -> str:
        """
        Create EXTERNAL line with filename, preserving formatting.

        Args:
            original_line: Original line containing EXTERNAL marker
            filename: Filename to insert

        Returns:
            Reconstructed EXTERNAL line
        """
        params = self._parse_external_params(original_line)
        external_pos = original_line.find("EXTERNAL")
        before_external = original_line[:external_pos]

        existing_filename = self._extract_filename_from_line(original_line)

        if existing_filename:
            filename_pos = original_line.find(existing_filename)
            if filename_pos != -1:
                after_filename = original_line[filename_pos + len(existing_filename) :]
            else:
                after_filename = ""
        else:
            if params:
                match = re.search(r"EXTERNAL\s*\([^)]*\{[^}]+\}\s*\)", original_line)
                if match:
                    after_filename = original_line[match.end() :]
                else:
                    after_filename = ""
            else:
                after_filename = original_line[external_pos + 8 :]

        if params:
            match = re.search(r"EXTERNAL\s*\([^)]*\{[^}]+\}\s*\)", original_line)
            if match:
                params_block = match.group(0)
                return f"{before_external}{params_block}:{filename}{after_filename}"

        return f"{before_external}EXTERNAL:{filename}{after_filename}"

    def _write_jsonnet_template(self, data: dict, output_path: Path):
        """
        Write final jsonnet template with imports.

        Args:
            data: Modified dashboard JSON with placeholders
            output_path: Path to write jsonnet file to
        """
        json_content = json.dumps(data, indent=2)

        if not self._modifications:
            with open(output_path, "w") as f:
                f.write(json_content)
            return

        # Deduplicate imports
        unique_imports = {}
        for mod in self._modifications:
            filename = mod["filename"]
            var_name = mod["var_name"]
            if filename not in unique_imports:
                unique_imports[filename] = var_name

        # Generate local variables
        local_vars = [
            f"local {var_name} = importstr './assets/{filename}';"
            for filename, var_name in sorted(unique_imports.items())
        ]

        # Replace placeholders
        def replace_placeholder(match):
            content = match.group(1)
            return content[8:] if content.startswith("CONCAT__") else content

        json_content = re.sub(r'"__(.+?)__"', replace_placeholder, json_content)

        # Write template
        with open(output_path, "w") as f:
            if local_vars:
                f.write("\n".join(local_vars) + "\n\n")
            f.write(json_content)
