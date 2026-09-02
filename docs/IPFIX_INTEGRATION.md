# IPFIX Integration

## Status: PLANNED / UNSUPPORTED

IPFIX is kept separate from NetFlow because its Information Elements and
template lifecycle require protocol-specific handling. This release includes
only an explicit unsupported extension point. No IPFIX listener, template
decoder, wire parser, or forecast path is enabled, and the registry rejects
`IPFIX` creation.

Future work must define template expiry and refresh, exporter identity,
bounded datagram/record handling, duplicate detection, malformed input policy,
rate limiting, and the minimum Information Elements needed for every frozen
state feature. Bind only on an explicitly configured private interface and
protect the exporter boundary with network controls; do not claim application
authentication that IPFIX itself does not provide.
