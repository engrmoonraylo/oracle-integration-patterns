"""Read and normalize Oracle Integration 3 project archives (.car).

Rev 1.0  2026-11-15  Initial version, rules proven in a hands-on lab on Oracle Integration 3.

The .car is never modified. Normalization only feeds review (expanded tree)
and comparison (fingerprints). Standard library only, so it runs on any
GitHub-hosted runner without installs.
"""
import hashlib
import io
import json
import os
import re
import shutil
import xml.dom.minidom
import xml.etree.ElementTree as ET
import zipfile

# Export noise, proven volatile across no-change exports.
INFO_NOISE = {"validity", "mod"}           # export timestamp; mod is not a stable content hash
BESTPRACTICE_NOISE = {"startTime"}         # best-practice scan time
YAML_NOISE = re.compile(r"^(projectRevision|latestDate|latestBy):.*$")

# Extra fields that differ per instance (ignored only when comparing content
# across instances, never in the review tree).
INFO_INSTANCE_FIELDS = {"persistedState", "retainOriginEndpoint"}
CONNECTION_CONTENT_TAGS = ("displayName", "description", "applicationTypeRef",
                           "securityPolicy", "integrationRole")


# --------------------------------------------------------------------------
# Normalization (review tree)
# --------------------------------------------------------------------------
def _json(data, drop=()):
    obj = json.loads(data)

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in drop}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o
    return json.dumps(strip(obj), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _rpa_json(data):
    # rpa_metadata.json nests JSON inside "details" strings; drop their updatedDate.
    obj = json.loads(data)
    for val in obj.values():
        entries = val if isinstance(val, list) else [val] if isinstance(val, dict) else []
        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("details"), str):
                d = json.loads(e["details"])
                d.pop("updatedDate", None)
                e["details"] = d
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _xml(data):
    # Connection lockInfo changes when someone merely opens the connection.
    data = re.sub(rb"<lockInfo>.*?</lockInfo>", b"", data, flags=re.S)
    try:
        pretty = xml.dom.minidom.parseString(data).toprettyxml(indent="  ")
        return "\n".join(l for l in pretty.splitlines() if l.strip()) + "\n"
    except Exception:
        return data.decode("utf-8", errors="replace")


def _yaml(text):
    out, skip_origin = [], False
    for line in text.splitlines():
        if line.startswith("origin:"):      # tenancy and instance OCIDs: per instance
            skip_origin = True
            continue
        if skip_origin and line.startswith("  "):
            continue
        skip_origin = False
        if not YAML_NOISE.match(line):
            out.append(line)
    return "\n".join(out) + "\n"


def normalized_entries(car_path):
    """Yield (relative_path, normalized_content) for every file in the archive."""
    with zipfile.ZipFile(car_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name, data = info.filename, z.read(info)
            base = os.path.basename(name)
            if base == "oic_project.properties":     # timestamp and export hash only
                continue
            if base == "rpa.zip":                    # inner zip: keep contents, not the binary
                inner = zipfile.ZipFile(io.BytesIO(data))
                for i in inner.infolist():
                    raw = inner.read(i)
                    yield (f"{os.path.dirname(name)}/rpa/{i.filename}",
                           _rpa_json(raw) if i.filename.endswith(".json") else raw)
                continue
            if base == "info.json":
                yield name, _json(data, INFO_NOISE)
            elif base == "bestpractises.json":
                yield name, _json(data, BESTPRACTICE_NOISE)
            elif base.endswith(".json"):
                yield name, _json(data)
            elif base.endswith((".xml", ".xsd", ".dvm", ".wsdl")):
                yield name, _xml(data)
            elif base == "project.yaml":
                yield name, _yaml(data.decode("utf-8"))
            else:
                yield name, data


def expand(car_path, out_dir):
    """Write the normalized review tree for one archive (replaces out_dir)."""
    shutil.rmtree(out_dir, ignore_errors=True)
    for rel, content in normalized_entries(car_path):
        dest = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if isinstance(content, str):
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        else:
            with open(dest, "wb") as f:
                f.write(content)


# --------------------------------------------------------------------------
# Archive model (comparison)
# --------------------------------------------------------------------------
def _parse_project_yaml(text):
    """Minimal parser for the fixed shape of project.yaml (no PyYAML needed)."""
    top, assets, section, item = {}, {}, None, None
    for line in text.splitlines():
        if not line.strip() or line.startswith("---"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, _, val = line.partition(":")
            top[key.strip()] = val.strip()
            section = None
            continue
        m = re.match(r"^  (\w+):\s*$", line)
        if m:
            section = m.group(1)
            assets[section] = []
            continue
        m = re.match(r"^  - (\w+):\s*(.*)$", line)
        if m and section:
            item = {m.group(1): m.group(2)}
            assets[section].append(item)
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and item is not None:
            item[m.group(1)] = m.group(2)
    return top, assets


def _sha(parts):
    h = hashlib.sha256()
    for rel, content in sorted(parts):
        h.update(rel.encode())
        h.update(b"\0")
        h.update(content.encode() if isinstance(content, str) else content)
        h.update(b"\0")
    return h.hexdigest()[:16]


def _connection_content(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return xml_text
    values = {}
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in CONNECTION_CONTENT_TAGS:
            values[tag] = (el.text or "").strip()
    props = sorted((p.findtext("name") or "", p.findtext("value") or "")
                   for p in root.iter() if p.tag.split("}")[-1] == "connectionProperty")
    return json.dumps({"fields": values, "properties": props}, sort_keys=True)


def load(car_path):
    """Return a dict describing the archive: project, integrations, lookups,
    connections and deployments (labels), each with a content fingerprint."""
    files = dict(normalized_entries(car_path))
    yaml_text = files.get("project/project.yaml", "")
    top, assets = _parse_project_yaml(yaml_text)
    meta = {a["id"]: a for a in assets.get("integrations", [])}

    integrations = {}
    folders = {}
    for rel in files:
        m = re.match(r"^project/integrations/([^/]+)/(.+)$", rel)
        if m:
            folders.setdefault(m.group(1), {})[m.group(2)] = files[rel]
    for folder, content in folders.items():
        info = json.loads(content.get("info.json", "{}"))
        props = info.get("properties", {})
        key = f"{props.get('code')}|{props.get('version')}"
        compare = []
        for rel, data in content.items():
            if rel == "PROJECT-INF/bestpractises.json":
                continue                       # scan output, not design
            if rel == "info.json":
                data = _json(data, INFO_INSTANCE_FIELDS)
            compare.append((rel, data))
        m = meta.get(key, {})
        integrations[key] = {
            "code": props.get("code"),
            "version": props.get("version"),
            "name": props.get("name"),
            "folder": folder,
            "state": props.get("persistedState"),
            "scope": props.get("scope"),
            "dependencies": info.get("dependencies", {}),
            "revision": m.get("revision"),
            "updatedBy": m.get("updatedBy"),
            "updatedDate": m.get("updatedDate"),
            "review_fp": _sha(content.items()),     # within one instance
            "content_fp": _sha(compare),            # across instances
        }

    lookups = {}
    for rel, data in files.items():
        m = re.match(r"^project/lookups/(.+)\.dvm$", rel)
        if m:
            lookups[m.group(1)] = {"text": data, "content_fp": _sha([("dvm", data)])}

    connections = {}
    for rel, data in files.items():
        m = re.match(r"^project/connections/(.+)\.xml$", rel)
        if m:
            connections[m.group(1)] = {"review_fp": _sha([("xml", data)]),
                                       "content_fp": _sha([("c", _connection_content(data))])}

    labels = {}
    for rel, data in files.items():
        m = re.match(r"^project/labels/(.+)\.json$", rel)
        if m:
            obj = json.loads(data)
            labels[obj.get("code", m.group(1))] = sorted(
                f"{i['code']}|{i['version']}" for i in obj.get("integrations", []))

    return {
        "path": car_path,
        "project": top.get("code") or top.get("id"),
        "integrations": integrations,
        "lookups": lookups,
        "connections": connections,
        "labels": labels,
    }


def deployment_id(model):
    """The deployment identifier if this archive is a deployment export, else None.
    A deployment export holds exactly one label whose integrations are exactly
    the integrations in the archive (a full project export holds them all)."""
    if len(model["labels"]) != 1:
        return None
    (label, members), = model["labels"].items()
    return label if set(members) == set(model["integrations"]) else None


def lookup_rows(dvm_text):
    """Return {first-column value: row tuple} for a normalized .dvm."""
    try:
        root = ET.fromstring(dvm_text)
    except ET.ParseError:
        return {}
    rows = {}
    for row in root.iter():
        if row.tag.split("}")[-1] == "row":
            cells = tuple((c.text or "") for c in row if c.tag.split("}")[-1] == "cell")
            if cells:
                rows[cells[0]] = cells
    return rows
