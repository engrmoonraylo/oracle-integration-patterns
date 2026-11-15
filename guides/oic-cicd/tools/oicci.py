"""OIC CI/CD checks for Oracle Integration 3 project archives.

Rev 1.0  2026-11-15  Initial version, rules proven in the OIC CI/CD POC.

Commands
  expand  <car> <out_dir>                 write the normalized review tree
  summary <car> [--previous <car>]        what changed, per integration (commit text)
  check   <release.car> [--prod <car>]    pre-import guard; exit 1 on a blocking finding
  verify  <release.car> --prod <car>      post-import check; exit 1 if the release did not land
  verify-all <releases_dir> --prod <car>  verify every release of that project already imported
  info    <car> --field project|deployment  print one identity field (for workflow scripts)

Behaviors the rules rely on (proven against two OIC instances):
  - A full project archive imports only where the project does not exist yet.
  - A deployment archive imports into an existing project. An integration
    version that already exists in the target is silently skipped, not replaced.
  - Existing lookups (and, by assumption, connections) are never overwritten;
    missing ones are created.
  - A deployment identifier that already exists in the target is rejected.
  - Imported integrations arrive inactive.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oiccar  # noqa: E402

BLOCK, WARN, INFO, OK = "BLOCK", "WARN", "INFO", "OK"
ICON = {BLOCK: "⛔", WARN: "⚠️", INFO: "ℹ️", OK: "✅"}


def _major(version):
    return (version or "").split(".")[0]


def _emit(title, findings):
    lines = [f"### {title}", "", "| | Item | Finding |", "|---|---|---|"]
    for level, item, text in findings:
        # A bare "|" inside CODE|VERSION would split the markdown table cell.
        lines.append(f"| {ICON[level]} {level} | `{item.replace('|', chr(92) + '|')}` | {text} |")
    out = "\n".join(lines) + "\n"
    print(out)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(out + "\n")


# --------------------------------------------------------------------------
def cmd_expand(args):
    oiccar.expand(args.car, args.out_dir)
    print(f"expanded {args.car} -> {args.out_dir}")
    return 0


def cmd_summary(args):
    """One line per changed artifact, for commit messages."""
    new = oiccar.load(args.car)
    old = oiccar.load(args.previous) if args.previous else None
    lines = []
    for key, i in sorted(new["integrations"].items()):
        prev = old["integrations"].get(key) if old else None
        who = f" (updated by {i['updatedBy']})" if i.get("updatedBy") else ""
        if prev is None:
            lines.append(f"added    {i['code']} {i['version']}{who}")
        elif prev["review_fp"] != i["review_fp"]:
            lines.append(f"changed  {i['code']} {i['version']}{who}")
        elif prev["state"] != i["state"]:
            lines.append(f"state    {i['code']} {i['version']}: {prev['state']} -> {i['state']}")
    if old:
        for key, i in sorted(old["integrations"].items()):
            if key not in new["integrations"]:
                lines.append(f"removed  {i['code']} {i['version']}")
    for kind in ("lookups", "connections"):
        for name, a in sorted(new[kind].items()):
            prev = old[kind].get(name) if old else None
            if prev is None:
                lines.append(f"added    {kind[:-1]} {name}")
            elif prev.get("review_fp", prev["content_fp"]) != a.get("review_fp", a["content_fp"]):
                lines.append(f"changed  {kind[:-1]} {name}")
    dep = oiccar.deployment_id(new)
    header = f"Deployment {dep}" if dep else f"Project {new['project']}"
    print(header + (": no content change" if not lines else ""))
    for l in lines:
        print("  " + l)
    return 0


def cmd_check(args):
    rel = oiccar.load(args.release)
    dep = oiccar.deployment_id(rel)
    findings = []

    if args.prod is None:
        findings.append((INFO, rel["project"], "No PROD state supplied: treated as a first install "
                         "(full project import into an instance without this project)."))
        _emit(f"Release guard: {os.path.basename(args.release)}", findings)
        return 0

    prod = oiccar.load(args.prod)
    if dep is None:
        findings.append((BLOCK, os.path.basename(args.release),
                         "Not a deployment export. A full project archive is rejected by an instance "
                         "that already has the project; export a project deployment instead."))
        _emit(f"Release guard: {os.path.basename(args.release)}", findings)
        return 1

    if dep in prod["labels"]:
        findings.append((BLOCK, dep, "Deployment identifier already exists in PROD; the import will be "
                         "rejected. Use a new identifier for every release."))
    else:
        findings.append((OK, dep, "New deployment identifier."))

    for key, i in sorted(rel["integrations"].items()):
        target = prod["integrations"].get(key)
        if target is None:
            older = sorted(k for k, p in prod["integrations"].items()
                           if p["code"] == i["code"] and _major(p["version"]) == _major(i["version"]))
            note = f" Activating it will deactivate the active version among: {', '.join(older)}." if older else ""
            findings.append((OK, key, "New integration version; will be added." + note))
        elif target["content_fp"] == i["content_fp"]:
            findings.append((INFO, key, "Same version and same content already in PROD; nothing to deploy."))
        else:
            findings.append((BLOCK, key, "Same version already in PROD with different content. OIC will "
                             "silently skip it and the change will not reach PROD. Create a new "
                             "integration version in DEV and include that version."))

    for name, lk in sorted(rel["lookups"].items()):
        target = prod["lookups"].get(name)
        if target is None:
            findings.append((INFO, name, "Lookup missing in PROD; will be created with the DEV values."))
        elif target["content_fp"] != lk["content_fp"]:
            dev_rows = oiccar.lookup_rows(lk["text"])
            prod_rows = oiccar.lookup_rows(target["text"])
            added = len(set(dev_rows) - set(prod_rows))
            changed = sum(1 for k in dev_rows if k in prod_rows and dev_rows[k] != prod_rows[k])
            findings.append((WARN, name, f"Lookup differs from PROD ({added} new, {changed} changed rows) "
                             "and will NOT be applied; PROD values are kept. Use the lookup release "
                             "step if the change is intended."))
        else:
            findings.append((OK, name, "Lookup identical to PROD."))

    for name, cn in sorted(rel["connections"].items()):
        target = prod["connections"].get(name)
        if target is None:
            findings.append((INFO, name, "Connection missing in PROD; will be created and must be "
                             "configured in PROD before activation."))
        elif target["content_fp"] != cn["content_fp"]:
            findings.append((WARN, name, "Connection differs from PROD and will not be applied "
                             "(assumed same behavior as lookups)."))

    findings.append((INFO, "activation", "Imported integrations arrive inactive. Activate the release "
                     "deployment in PROD after verification."))
    _emit(f"Release guard: {dep}", findings)
    return 1 if any(f[0] == BLOCK for f in findings) else 0


def cmd_verify(args):
    rel = oiccar.load(args.release)
    prod = oiccar.load(args.prod)
    dep = oiccar.deployment_id(rel) or os.path.basename(args.release)
    findings = []

    if dep not in prod["labels"]:
        findings.append((BLOCK, dep, "Deployment not found in PROD: release not imported."))
        _emit(f"Post-import verification: {dep}", findings)
        return 1
    findings.append((OK, dep, "Deployment present in PROD."))

    for key, i in sorted(rel["integrations"].items()):
        target = prod["integrations"].get(key)
        if target is None:
            findings.append((BLOCK, key, "Missing in PROD."))
        elif target["content_fp"] != i["content_fp"]:
            findings.append((BLOCK, key, "Present in PROD but content differs from the release "
                             "(silently skipped at import, or edited in PROD)."))
        else:
            state = target["state"] or "unknown"
            level = OK if state == "ACTIVATED" else WARN
            findings.append((level, key, f"Content matches the release. State in PROD: {state}."))

    for name, lk in sorted(rel["lookups"].items()):
        target = prod["lookups"].get(name)
        if target is None:
            findings.append((BLOCK, name, "Lookup missing in PROD."))
        elif target["content_fp"] != lk["content_fp"]:
            findings.append((WARN, name, "Lookup kept its PROD values (expected: lookups are never "
                             "overwritten)."))
        else:
            findings.append((OK, name, "Lookup matches the release."))

    _emit(f"Post-import verification: {dep}", findings)
    return 1 if any(f[0] == BLOCK for f in findings) else 0


def cmd_verify_all(args):
    prod = oiccar.load(args.prod)
    failed, pending = 0, []
    for name in sorted(os.listdir(args.releases_dir)):
        if not name.endswith(".car"):
            continue
        path = os.path.join(args.releases_dir, name)
        rel = oiccar.load(path)
        dep = oiccar.deployment_id(rel)
        if rel["project"] != prod["project"] or dep is None:
            continue
        if dep not in prod["labels"]:
            pending.append(dep)
            continue
        failed |= cmd_verify(argparse.Namespace(release=path, prod=args.prod))
    if pending:
        _emit("Releases not yet imported into PROD", [(INFO, d, "Pending import.") for d in pending])
    return failed


def cmd_info(args):
    model = oiccar.load(args.car)
    print(model["project"] if args.field == "project" else (oiccar.deployment_id(model) or ""))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("expand"); s.add_argument("car"); s.add_argument("out_dir"); s.set_defaults(fn=cmd_expand)
    s = sub.add_parser("summary"); s.add_argument("car"); s.add_argument("--previous"); s.set_defaults(fn=cmd_summary)
    s = sub.add_parser("check"); s.add_argument("release"); s.add_argument("--prod"); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("verify"); s.add_argument("release"); s.add_argument("--prod", required=True); s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("verify-all"); s.add_argument("releases_dir"); s.add_argument("--prod", required=True); s.set_defaults(fn=cmd_verify_all)
    s = sub.add_parser("info"); s.add_argument("car"); s.add_argument("--field", choices=["project", "deployment"], required=True); s.set_defaults(fn=cmd_info)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
