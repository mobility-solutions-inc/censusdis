HTTP compression and CVE-2026-111497
===================================

Census data, metadata, LODES, and shapefile downloads request gzip or deflate
compression and reject any HTTP response with a ``br`` content encoding before
reading its body. This also applies to redirect and error responses, even if
the server ignores ``Accept-Encoding``.

The package requires ``Brotli>=1.2.1`` and ``brotlicffi>=1.2.1.0`` because HTTP
clients can automatically select either decoder. These requirements also
protect Contextily's separate basemap tile downloader, which does not use
the Census download helper. Restart running applications and notebook kernels
after upgrading so they load the patched decoders.

Bundled native libraries still require separate updates
------------------------------------------------------

These changes mitigate HTTP response decoding. They do not replace Brotli
statically linked into PyArrow or bundled with Pillow's FreeType, and they do
not update system Brotli used by curl or other applications.

As of October 23, 2026, the latest PyPI releases are PyArrow 26.0.0 and Pillow
13.0.0, both released before the upstream Brotli security update. The Linux
wheels inspected during the investigation contain an unpatched decoder.
Do not process untrusted Brotli-compressed Parquet data or WOFF2 fonts with
those builds. Use dependencies rebuilt with patched Brotli, or wait for and
verify upstream wheel updates before enabling that processing. Normal Census
downloads use JSON, ZIP shapefiles, gzip CSVs, and map images.

Upgrade system Brotli separately through the operating system's security
updates. Fixed upstream Brotli releases are 1.0.10, 1.1.1, and 1.2.1; a vendor
may backport the fix without changing the upstream version number.

References
----------

* `Brotli security release 1.2.1
  <https://github.com/google/brotli/releases/tag/v1.2.1>`_
* `Requests automatic Brotli decoding
  <https://requests.readthedocs.io/en/latest/user/quickstart/#binary-response-content>`_
* `Arrow Brotli dependency update
  <https://github.com/apache/arrow/pull/55167>`_
