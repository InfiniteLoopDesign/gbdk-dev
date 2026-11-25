#!/usr/bin/env python3
"""Collect exact Debian source packages and notices from the release OCI images."""

import csv
import hashlib
import json
import lzma
import re
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


SNAPSHOT = "https://snapshot.debian.org"
DEBIAN = "https://deb.debian.org"
ARCHITECTURES = {"amd64", "arm64"}


def fetch(url, destination=None, algorithm=None, checksum=None):
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "gbdk-dev-release/1"}), timeout=65) as response:
                if destination is None:
                    return response.read()
                digest = hashlib.new(algorithm)
                temporary = destination.with_suffix(destination.suffix + ".part")
                with temporary.open("wb") as output:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        digest.update(block)
                        output.write(block)
                if digest.hexdigest() != checksum:
                    raise ValueError(f"Checksum mismatch for {url}")
                temporary.replace(destination)
                return
        except (HTTPError, URLError, TimeoutError, ConnectionError) as error:
            if attempt == 3 or (isinstance(error, HTTPError) and error.code == 404):
                raise
            time.sleep(2 ** attempt)


def paragraphs(text):
    for paragraph in text.split("\n\n"):
        fields = {}
        name = None
        for line in paragraph.splitlines():
            if line.startswith((" ", "\t")) and name:
                fields[name] += "\n" + line.strip()
            elif ":" in line:
                name, value = line.split(":", 1)
                fields[name] = value.strip()
        if fields:
            yield fields


def blob(archive, descriptor):
    algorithm, digest = descriptor["digest"].split(":", 1)
    return archive.extractfile(f"blobs/{algorithm}/{digest}")


def image_manifests(archive, descriptors):
    for descriptor in descriptors:
        with blob(archive, descriptor) as content:
            manifest = json.load(content)
        if "manifests" in manifest:
            yield from image_manifests(archive, manifest["manifests"])
        elif descriptor.get("platform", {}).get("os") == "linux":
            yield descriptor["platform"]["architecture"], descriptor["digest"], manifest


def installed_packages(status):
    for package in paragraphs(status.decode()):
        if package.get("Status") != "install ok installed":
            continue
        source = package.get("Source", package["Package"]).split(maxsplit=1)
        source_version = source[1].strip("()") if len(source) == 2 else package["Version"]
        yield package["Package"], package["Architecture"], package["Version"], source[0], source_version


def image_inventory(image, output):
    required = set()
    platforms = {}
    with tarfile.open(image) as archive:
        index = json.load(archive.extractfile("index.json"))
        for arch, manifest_digest, manifest in image_manifests(archive, index["manifests"]):
            if arch in platforms:
                raise ValueError(f"Duplicate platform {arch}")
            platforms[arch] = manifest_digest
            notices = {}
            status = None
            compiler = None
            for layer in manifest["layers"]:
                with blob(archive, layer) as content, tarfile.open(fileobj=content, mode="r|*") as files:
                    for member in files:
                        if not member.isfile():
                            continue
                        path = Path(member.name)
                        if path == Path("var/lib/dpkg/status"):
                            status = files.extractfile(member).read()
                        elif path == Path("opt/gbdk/bin/sdcc"):
                            compiler = files.extractfile(member).read(20)
                        elif (
                            path == Path("opt/gbdk/LICENSE")
                            or path.parent == Path("opt/gbdk/licenses")
                            or path.parent == Path("usr/share/common-licenses")
                            or (path.parts[:3] == ("usr", "share", "doc") and path.name == "copyright")
                        ):
                            notices[path] = files.extractfile(member).read()
            if (
                not status or not compiler or compiler[:4] != b"\x7fELF"
                or int.from_bytes(compiler[18:20], "little") != {"amd64": 62, "arm64": 183}[arch]
                or Path("opt/gbdk/LICENSE") not in notices
                or Path("opt/gbdk/licenses/LICENSE_lcc") not in notices
                or Path("opt/gbdk/licenses/LICENSE_SDCC") not in notices
            ):
                raise ValueError(f"Missing package status, matching compiler, or notices for {arch}")
            packages = sorted(installed_packages(status))
            if not packages:
                raise ValueError(f"No Debian package metadata for {arch}")
            with (output / f"debian-{arch}.tsv").open("w") as table:
                writer = csv.writer(table, delimiter="\t", lineterminator="\n")
                writer.writerow(["binary", "arch", "binary_version", "source", "source_version"])
                writer.writerows(packages)
            required.update((row[3], row[4]) for row in packages)
            for path, data in notices.items():
                destination = output / "notices" / arch / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            print(f"{arch}: {len(packages)} installed Debian binary packages, {len(notices)} notice files", flush=True)
    if platforms.keys() != ARCHITECTURES:
        raise ValueError(f"Expected amd64 and arm64, found {sorted(platforms)}")
    (output / "manifests.json").write_text(json.dumps(platforms, indent=2) + "\n")
    return required


def load_index(root_suite):
    root, suite = root_suite
    url = f"{root}/dists/{suite}/main/source/Sources.xz"
    return root, lzma.decompress(fetch(url)).decode()


def archive_index(required):
    sources = {}
    roots = [
        (f"{DEBIAN}/debian", "trixie"),
        (f"{DEBIAN}/debian", "trixie-updates"),
        (f"{DEBIAN}/debian-security", "trixie-security"),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for root, index in pool.map(load_index, roots):
            for fields in paragraphs(index):
                key = fields.get("Package"), fields.get("Version")
                if key in required and fields.get("Checksums-Sha256"):
                    sources[key] = [
                        (filename, "sha256", checksum, f"{root}/{fields['Directory']}/{filename}")
                        for checksum, _, filename in (line.split() for line in fields["Checksums-Sha256"].splitlines() if line)
                    ]
    return sources


def snapshot_files(package, version):
    endpoint = f"{SNAPSHOT}/mr/package/{quote(package, safe='')}/{quote(version, safe='')}/srcfiles"
    records = []
    for record in json.loads(fetch(endpoint))["result"]:
        digest = record["hash"]
        info = json.loads(fetch(f"{SNAPSHOT}/mr/file/{digest}/info"))["result"]
        records.append((info[0]["name"], "sha1", digest, f"{SNAPSHOT}/file/{digest}"))
    return records


def verify_dsc(directory):
    files = list(directory.glob("*.dsc"))
    if len(files) != 1:
        raise ValueError(f"Expected one source descriptor in {directory}")
    match = re.search(r"^Checksums-Sha256:\n((?:[ \t][^\n]*\n)+)", files[0].read_text(), re.MULTILINE)
    if not match:
        raise ValueError(f"No SHA-256 checksums in {files[0]}")
    for line in match.group(1).splitlines():
        checksum, size, filename = line.split()
        path = directory / filename
        with path.open("rb") as source:
            if path.stat().st_size != int(size) or hashlib.file_digest(source, "sha256").hexdigest() != checksum:
                raise ValueError(f"Descriptor checksum mismatch: {path}")


def collect_source(key, index, output):
    package, version = key
    directory = output / "debian" / package / version
    directory.mkdir(parents=True, exist_ok=True)
    records = index.get(key) or snapshot_files(package, version)
    try:
        retrieve_records(records, directory)
    except HTTPError as error:
        if key not in index or error.code != 404:
            raise
        retrieve_records(snapshot_files(package, version), directory)
    verify_dsc(directory)
    return key


def retrieve_records(records, directory):
    for filename, algorithm, checksum, url in records:
        if Path(filename).name != filename:
            raise ValueError(f"Invalid source filename: {filename}")
        path = directory / filename
        if path.is_file():
            with path.open("rb") as source:
                if hashlib.file_digest(source, algorithm).hexdigest() == checksum:
                    continue
        fetch(url, path, algorithm, checksum)


def main():
    image, output = map(Path, sys.argv[1:])
    output.mkdir(parents=True, exist_ok=True)
    required = image_inventory(image, output)
    index = archive_index(required)
    print(f"Collecting {len(required)} exact Debian source versions ({len(index)} in current Debian indexes)", flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for key in pool.map(lambda key: collect_source(key, index, output), sorted(required)):
            print("Verified:", *key, flush=True)


if __name__ == "__main__":
    main()
