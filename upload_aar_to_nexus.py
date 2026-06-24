#!/usr/bin/env python3
"""
Minimal standalone script to upload an .aar artifact to Nexus Repository Manager.

Hands the actual transport off to `curl` (system TLS stack, well-behaved with
Expect: 100-continue, etc.) and renders a custom progress ticker against the
bytes streamed into curl's stdin.

Sonatype Nexus REST API:
  POST /service/rest/v1/components?repository={repository}
  https://help.sonatype.com/en/api-reference.html

Dependencies: stdlib only, plus a working `curl` on PATH.
"""

import argparse, os, secrets, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import quote, urlparse


NEXUS_URL = "https://nexus.tools.textnow.io"
UPLOAD_PATH = "/service/rest/v1/components"
DEFAULT_RETRIES = 3
CHUNK_SIZE = 64 * 1024  # bytes per write into curl's stdin


# ---------------------------------------------------------------------------
# Progress ticker
# ---------------------------------------------------------------------------

def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _render(sent: int, total: int, start: float, label: str) -> None:
    pct = (sent / total * 100) if total else 0
    elapsed = max(time.time() - start, 1e-6)
    rate = sent / elapsed
    bar_w = 30
    filled = int(bar_w * sent / total) if total else 0
    bar = "#" * filled + "-" * (bar_w - filled)
    sys.stderr.write(
        f"\r{label} [{bar}] {pct:5.1f}%  "
        f"{_human(sent)}/{_human(total)}  "
        f"{_human(rate)}/s   "
    )
    sys.stderr.flush()


# ---------------------------------------------------------------------------
# Multipart body construction (hand-rolled, no urllib3 dep)
# ---------------------------------------------------------------------------

def _build_multipart(
    fields: list,
    file_field: str,
    file_path: Path,
) -> "tuple[bytes, str]":
    """Build a multipart/form-data body. Returns (body, content_type).

    `fields` is a list of (name, value) string pairs. The file part is added
    last, named `file_field`, with content read from `file_path`.
    """
    boundary = secrets.token_hex(16)
    b = boundary.encode("ascii")
    crlf = b"\r\n"
    parts: list = []
    for name, value in fields:
        parts.append(b"--" + b + crlf)
        parts.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8") + crlf
        )
        parts.append(crlf)
        parts.append(value.encode("utf-8") + crlf)
    parts.append(b"--" + b + crlf)
    parts.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"'
        ).encode("utf-8")
        + crlf
    )
    parts.append(b"Content-Type: application/octet-stream" + crlf)
    parts.append(crlf)
    parts.append(file_path.read_bytes())
    parts.append(crlf)
    parts.append(b"--" + b + b"--" + crlf)
    body = b"".join(parts)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


# ---------------------------------------------------------------------------
# Auth — written to a private temp netrc file so the password never appears
# in argv (where `ps` would expose it).
# ---------------------------------------------------------------------------

def _make_netrc(host: str, user: str, password: str) -> str:
    fd, path = tempfile.mkstemp(prefix="nexus-up-", suffix=".netrc")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"machine {host} login {user} password {password}\n")
        os.chmod(path, 0o600)
        return path
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _stream_to_curl(
    args: list,
    body: bytes,
    label: str,
) -> int:
    """Spawn curl, stream `body` to its stdin in chunks while rendering a
    progress ticker. Returns curl's exit code."""
    proc = subprocess.Popen(args, stdin=subprocess.PIPE)
    total = len(body)
    sent = 0
    start = time.time()
    last_print = 0.0
    try:
        view = memoryview(body)
        while sent < total:
            end = min(sent + CHUNK_SIZE, total)
            try:
                proc.stdin.write(view[sent:end])
                proc.stdin.flush()  # natural pacing via OS pipe backpressure
            except BrokenPipeError:
                # curl exited early (auth/cert/proxy rejected the request).
                break
            sent = end
            now = time.time()
            if now - last_print >= 0.1 or sent >= total:
                last_print = now
                _render(sent, total, start, label)
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
    rc = proc.wait()
    sys.stderr.write("\n")
    sys.stderr.flush()
    return rc


def upload_aar(
    username: str,
    password: str,
    repository: str,
    group_id: str,
    artifact_id: str,
    version: str,
    aar_file: Path,
    verify: "bool | str" = True,
    retries: int = DEFAULT_RETRIES,
) -> None:
    if not aar_file.is_file():
        raise FileNotFoundError(f"AAR file not found: {aar_file}")
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("`curl` is not on PATH.")

    file_size = aar_file.stat().st_size
    print(
        f"Uploading {aar_file.name} ({_human(file_size)}) -> "
        f"{repository} as {group_id}:{artifact_id}:{version}",
        file=sys.stderr,
    )

    fields = [
        ("maven2.groupId", group_id),
        ("maven2.artifactId", artifact_id),
        ("maven2.version", version),
        ("maven2.generate-pom", "true"),
        ("maven2.packaging", "aar"),
        ("maven2.asset1.extension", "aar"),
    ]
    body, content_type = _build_multipart(fields, "maven2.asset1", aar_file)
    total = len(body)

    host = urlparse(NEXUS_URL).hostname or ""
    netrc_path = _make_netrc(host, username, password)

    try:
        url = f"{NEXUS_URL}{UPLOAD_PATH}?repository={quote(repository)}"
        base_args = [
            curl,
            "--fail-with-body",          # non-zero exit on 4xx/5xx, body to stdout
            "--show-error",
            "--silent",                  # suppress curl's own progress meter;
                                         # we render our own.
            "--expect100-timeout", "10",
            "--netrc-file", netrc_path,
            "-X", "POST",
            "-T", "-",                   # stream body from stdin
            "-H", f"Content-Type: {content_type}",
            "-H", f"Content-Length: {total}",
        ]
        if verify is False:
            base_args.append("--insecure")
        elif isinstance(verify, str):
            base_args += ["--cacert", verify]
        base_args.append(url)

        last_rc = 0
        for attempt in range(1, retries + 1):
            label = f"  upload (try {attempt}/{retries})"
            last_rc = _stream_to_curl(base_args, body, label)
            if last_rc == 0:
                print(
                    f"Uploaded: {group_id}:{artifact_id}:{version} "
                    f"({aar_file.name}) -> {repository}"
                )
                return
            if attempt < retries:
                backoff = min(2 ** (attempt - 1), 8)
                print(
                    f"  attempt {attempt} failed (curl exit {last_rc}); "
                    f"retrying in {backoff}s...",
                    file=sys.stderr,
                )
                time.sleep(backoff)

        size_mb = total / (1024 * 1024)
        raise RuntimeError(
            f"Upload failed after {retries} attempt(s) — last curl exit "
            f"status {last_rc}. The {size_mb:.1f} MB body never made it "
            "through. Likely causes: TLS-intercepting proxy with body-size "
            "or inspection-timeout limits, server-side request limits, or "
            "auth/permission rejection. Try --insecure to rule out cert "
            "issues, or --ca-bundle to point at the corp CA."
        )
    finally:
        try:
            os.unlink(netrc_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="Upload an .aar to Nexus via curl with a progress ticker."
    )
    p.add_argument("--user", required=True, help="Nexus username")
    p.add_argument("--password", required=True, help="Nexus password")
    p.add_argument("--repository", required=True, help="Target Nexus repository name")
    p.add_argument("--group-id", required=True, help="Maven groupId")
    p.add_argument("--artifact-id", required=True, help="Maven artifactId")
    p.add_argument("--version", required=True, help="Artifact version")
    p.add_argument("--file", required=True, type=Path, help="Path to .aar file")
    p.add_argument(
        "--ca-bundle",
        type=Path,
        help="Path to a CA bundle (PEM) used to verify the Nexus TLS cert. "
             "Useful behind a TLS-intercepting corporate proxy.",
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification entirely. Use only as a last resort.",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retry attempts on transient failures (default: {DEFAULT_RETRIES}).",
    )
    args = p.parse_args()

    if args.insecure:
        verify: "bool | str" = False
        print("WARNING: TLS verification disabled (--insecure)", file=sys.stderr)
    elif args.ca_bundle is not None:
        if not args.ca_bundle.is_file():
            print(f"CA bundle not found: {args.ca_bundle}", file=sys.stderr)
            return 2
        verify = str(args.ca_bundle)
    else:
        verify = True

    try:
        upload_aar(
            username=args.user,
            password=args.password,
            repository=args.repository,
            group_id=args.group_id,
            artifact_id=args.artifact_id,
            version=args.version,
            aar_file=args.file,
            verify=verify,
            retries=max(1, args.retries),
        )
    except (RuntimeError, FileNotFoundError) as e:
        print(f"\n{e}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
