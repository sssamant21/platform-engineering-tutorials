#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for name in canary_a canary_b; do
  test -f "sandbox/$name.conf" || { echo "Run the safe Ansible playbook first" >&2; exit 1; }
done
backup_dir="$(mktemp -d)"
trap 'rm -rf "$backup_dir"' EXIT
for name in canary_a canary_b; do
  cp "sandbox/$name.conf" "$backup_dir/$name.conf"
  before="$(sha256sum "$backup_dir/$name.conf" | cut -d ' ' -f 1)"
  printf 'injected drift\n' >> "sandbox/$name.conf"
  cp "$backup_dir/$name.conf" "sandbox/$name.conf"
  after="$(sha256sum "sandbox/$name.conf" | cut -d ' ' -f 1)"
  test "$before" = "$after" || { echo "Checksum mismatch: $name" >&2; exit 1; }
done
echo "PASS: local sandbox backup/restore checksum drill (NOT database DR)"
