# Security policy

Report suspected signing-key compromise privately to the repository owner.
Stop releases immediately, remove the compromised environment secret, preserve
published immutable assets for investigation, and ship an app update with a new
pinned public key/key ID before resuming publication. The initial design does
not accept remotely introduced keys.

Discovery data is untrusted. Only official Google full-OTA metadata with an
official digest may enter the reviewed candidate set. Private keys must exist
only in the protected GitHub Environment secret
`CATALOG_SIGNING_KEY_PKCS8_BASE64`; workflows must never print it.
