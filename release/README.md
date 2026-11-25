# GBDK dev image release review

Review the image and its matching source bundle together in the same versioned folder under `dist/`.

| File | Contents |
| --- | --- |
| `gbdk-dev.oci.tar` | One OCI image index with Linux amd64 and arm64 variants |
| `gbdk-dev-source.tar` | Corresponding source, license notices, per-architecture package inventories, and image manifest digests |
| `SHA256SUMS` | Checksums for the image and source archives |
| `packages-*.csv` | Installed Debian packages and matching source versions |
| `cves-*.csv` | Debian package findings from the release scan |

## Notices and source

The image includes the GBDK license overview at `/opt/gbdk/LICENSE`, the individual tool notices at `/opt/gbdk/licenses/`, and Debian's notices under `/usr/share/doc/` and `/usr/share/common-licenses/`. The source bundle copies the image's notice files for review.

GBDK includes the **LCC compiler driver**, derived from LCC by Christopher W. Fraser and David R. Hanson. LCC is available free of charge. Keep the complete `LICENSE_lcc` notice and credit the authors in the public listing. Report issues with this image to its publisher. [LCC upstream](https://github.com/drh/lcc) · [Bundled notice](https://github.com/gbdk-2020/gbdk-2020/blob/4.6.0/licenses/LICENSE_lcc)

The source bundle contains the GBDK 4.6.0 tag and build workflow, SDCC revision 16705 with the GBDK patch set applied, and the pinned patch repository with its build workflow. The Debian source versions come from the installed package database in each final image. Each source package includes its Debian descriptor, original source, and Debian changes where applicable. [GBDK release](https://github.com/gbdk-2020/gbdk-2020/releases/tag/4.6.0) · [Patched SDCC release](https://github.com/gbdk-2020/gbdk-2020-sdcc/releases/tag/sdcc-patched-gbdk-4.6.0)

The Linux SDCC build disables the PIC ports and device libraries. The source bundle omits SDCC's `device/non-free` directory, which supplies none of the shipped compiler tools. The bundle includes the patches separately so reviewers can trace the changes from upstream revision 16705.

## Before publishing

1. Check the two archive checksums with `sha256sum -c SHA256SUMS` in the release folder.
2. Review the package inventories and image manifest digests in the source bundle.
3. Make the matching source bundle publicly downloadable at no charge when the image goes live. Put its release-specific link and the LCC credit in the Docker Hub listing. Keep the source available for each published image revision.

The image and its source are paired. A fresh build can pick up new Debian packages, so collect source again if you rebuild the image for publication.
