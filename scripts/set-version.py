#!/usr/bin/env python3
"""Stamp a version into every plugin and marketplace manifest.

Five manifests, three ecosystems:

  plugins/agents-skills/.claude-plugin/plugin.json          Claude plugin
  .claude-plugin/marketplace.json                           Claude marketplace
  plugins/agents-skills-cursor/.cursor-plugin/plugin.json   Cursor plugin
  .cursor-plugin/marketplace.json                           Cursor marketplace
  plugins/agents-skills-codex/plugin.json                   Codex/ChatGPT plugin

The Codex marketplace (.agents/plugins/marketplace.json) carries no version, so it is
not stamped; Codex reads the version from the plugin's own manifest.

Versions are CalVer with a patch counter, YYYY.M.D.N, so several releases on the same
day never collide (the first of a day is `.0`). The release workflow computes the next
free N by probing existing `v<version>` tags. Every ecosystem ships the same version.

  python3 scripts/set-version.py 2026.7.11.0
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_RE = re.compile(r"^\d{4}\.\d{1,2}\.\d{1,2}\.\d+$")

PLUGIN_MANIFESTS = [
    os.path.join("plugins", "agents-skills", ".claude-plugin", "plugin.json"),
    os.path.join("plugins", "agents-skills-cursor", ".cursor-plugin", "plugin.json"),
    os.path.join("plugins", "agents-skills-codex", "plugin.json"),
]
MARKETPLACE_MANIFESTS = [
    os.path.join(".claude-plugin", "marketplace.json"),
    os.path.join(".cursor-plugin", "marketplace.json"),
]


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else ""
    if not VERSION_RE.match(version):
        print("Usage: python3 scripts/set-version.py <YYYY.M.D.N> (patch counter required)")
        sys.exit(1)

    def stamp_plugin(doc):
        doc["version"] = version

    def stamp_marketplace(doc):
        for plugin in doc.get("plugins", []):
            plugin["version"] = version

    targets = [(rel, stamp_plugin) for rel in PLUGIN_MANIFESTS]
    targets += [(rel, stamp_marketplace) for rel in MARKETPLACE_MANIFESTS]

    for rel, mutate in targets:
        path = os.path.join(ROOT, rel)
        with open(path) as f:
            doc = json.load(f)
        mutate(doc)
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
            f.write("\n")
        print(f"{rel} -> {version}")


if __name__ == "__main__":
    main()
