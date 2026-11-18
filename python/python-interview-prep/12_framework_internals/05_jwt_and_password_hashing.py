"""
JWT (HS256) built from scratch, the attacks that matter, and password hashing done right.

The Python twin of java/java-interview-prep/examples/10_spring_security/01_jwt_hs256_and_password_hashing.java
(see shared/cross-stack-pairs.md). Same six lessons, standard library only: what a token signs, what
it does NOT encrypt, why the algorithm must be pinned, why expiry and rotation exist, and why a
password needs a slow, salted hash instead of SHA-256.

Run me: python 05_jwt_and_password_hashing.py
Deep dive: ../deep_dive/10_web_frameworks.md (Q8, authentication in FastAPI)
"""
import base64
import hashlib
import hmac
import json
import secrets
import time


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# Demo values. A real secret is >= 32 random bytes from a secret store, never a literal in code.
SECRET = b"change-me-32-bytes-minimum-secret!!"
ISSUER, AUDIENCE = "auth.example.com", "orders-api"
NOW = 1_700_000_000            # a fixed clock, so the output is the same on every run


class TokenError(Exception):
    """Raised with the reason a token is rejected (the API maps it to 401)."""


# ================================================================ Base64URL and signing
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))      # JWT strips the padding


def _json(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode()


def sign(claims: dict, key: bytes = SECRET) -> str:
    head = b64url(_json({"alg": "HS256", "typ": "JWT"}))
    body = b64url(_json(claims))
    mac = hmac.new(key, f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64url(mac)}"


def verify(token: str, now: int, key: bytes = SECRET) -> dict:
    """Returns the claims, or raises TokenError. The ORDER matters: check the signature before
    trusting anything in the payload."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("malformed token")
    header = json.loads(b64url_decode(parts[0]))
    if header.get("alg") != "HS256":                     # pin the algorithm; never trust the header's choice
        raise TokenError(f"unexpected alg {header.get('alg')!r} (pin the algorithm server-side)")
    expected = hmac.new(key, f"{parts[0]}.{parts[1]}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64url_decode(parts[2])):     # constant time, like MessageDigest.isEqual
        raise TokenError("bad signature")
    claims = json.loads(b64url_decode(parts[1]))
    if now >= claims["exp"]:
        raise TokenError("token expired")
    if claims.get("iss") != ISSUER or claims.get("aud") != AUDIENCE:
        raise TokenError("wrong issuer or audience")
    return claims


def rejected(label: str, token: str, now: int = NOW, key: bytes = SECRET) -> None:
    try:
        verify(token, now, key)
        print(f"  {label:<24} -> ACCEPTED (this would be a vulnerability)")
    except TokenError as e:
        print(f"  {label:<24} -> REJECTED: {e}")


def main():
    claims = {"sub": "user-42", "roles": ["USER"], "iss": ISSUER, "aud": AUDIENCE, "exp": NOW + 900}

    section("1. Anatomy: header.payload.signature (Base64URL, signed - NOT encrypted)")
    token = sign(claims)
    head, body, sig = token.split(".")
    print(f"  header  = {b64url_decode(head).decode()}")
    print(f"  payload = {b64url_decode(body).decode()}")
    print("            ^ anyone can read this: never put secrets or personal data in a JWT")
    print(f"  signature ({len(sig)} chars) proves integrity and who holds the key")
    print(f"  verify now               -> {verify(token, NOW)['sub']} with roles {verify(token, NOW)['roles']}")
    # EXPERIMENT: paste the token into any JWT decoder site - it decodes with no key at all.

    section("2. Attacks, and how verification stops each one")
    forged = b64url(_json({**claims, "roles": ["ADMIN"]}))
    rejected("edited roles claim", f"{head}.{forged}.{sig}")
    rejected("alg=none downgrade", b64url(_json({"alg": "none", "typ": "JWT"})) + f".{body}.")
    rejected("after expiry", token, now=NOW + 901)
    rejected("signed with another key", sign(claims, key=b"attacker-guessed-secret-value!!!!"))
    rejected("token for another API", sign({**claims, "aud": "billing-api"}))
    print("  Also: check nbf, keep the key >= 256 bits, and rotate keys with a 'kid' header.")
    print("  With PyJWT the pin is the algorithms list:  jwt.decode(token, key, algorithms=['HS256'],")
    print("  audience='orders-api', issuer='auth.example.com'). Libraries that trusted the header's alg when")
    print("  no list was given caused the classic bug (PyJWT 2 refuses to decode without one), and")
    print("  options={'verify_signature': False} turns a decoder into a trust-anything parser.")
    # EXPERIMENT: delete the alg check in verify() and rerun - see which attack line changes, and why
    #             the signature check alone still stops it here (HS256 only). Key confusion (RS256 public
    #             key used as an HS256 secret) is the variant that needs the pin.

    section("3. Symmetric vs asymmetric keys")
    print("  HS256      : one shared secret signs AND verifies, so every verifying service can also mint tokens.")
    print("  RS256/ES256: the auth server signs with a private key; services verify with the public key,")
    print("               fetched from the issuer's JWKS endpoint (PyJWT: jwt.PyJWKClient(jwks_url)).")
    print("  Across teams or services, prefer asymmetric. Spring's equivalent: oauth2-resource-server + issuer-uri.")

    section("4. Token lifecycle")
    print("  short-lived access token (5-15 min) + refresh token (stored server-side, rotated, revocable)")
    print("  a stateless JWT cannot be revoked before 'exp' unless you keep a deny-list (Redis, keyed by 'jti')")
    print("  or switch to opaque tokens checked by introspection - the trade-off is a lookup per request")
    print("  browsers: HttpOnly + Secure + SameSite cookie (XSS cannot read it); services: Authorization: Bearer")

    section("5. Password hashing: slow and salted, never a plain fast hash")
    password = "correct horse battery staple"
    stored = hash_password(password)
    print(f"  stored string : {stored[:46]}...  (algorithm $ iterations $ salt $ hash)")
    print(f"  right password: {check_password(password, stored)}   wrong password: {check_password('guess', stored)}")
    print(f"  same password, new salt -> different hash: {hash_password(password) != stored}")
    t0 = time.perf_counter()
    hash_password(password)
    pbkdf2_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    hashlib.scrypt(password.encode(), salt=secrets.token_bytes(16), n=2**14, r=8, p=1)
    scrypt_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    for i in range(100_000):
        hashlib.sha256(f"guess{i}".encode()).digest()
    sha_ms = (time.perf_counter() - t0) * 1000
    print(f"  PBKDF2-HMAC-SHA256, {ITERATIONS:,} iterations : ~{pbkdf2_ms:.0f} ms per hash (deliberately slow)")
    print(f"  scrypt (n=2**14, memory-hard)       : ~{scrypt_ms:.0f} ms per hash")
    print(f"  plain SHA-256                       : 100,000 guesses in ~{sha_ms:.0f} ms on ONE core")
    print(f"  -> each slow hash costs an attacker ~{pbkdf2_ms * 100_000 / sha_ms:,.0f}x a SHA-256 guess; with plain SHA-256,")
    print("     the common passwords in a leaked table fall to one GPU in minutes.")
    old = hash_password(password, iterations=100_000)
    print(f"  raising the cost later: needs_rehash(old 100k hash) = {needs_rehash(old)}  (re-hash on next login)")
    print("  In practice: argon2-cffi or bcrypt (passlib wraps both); Django defaults to PBKDF2 like this.")
    print("  Java contrast: Spring's DelegatingPasswordEncoder uses the same {id}-prefixed, upgradable idea.")
    # EXPERIMENT: double ITERATIONS and rerun - the per-hash time doubles; that is the knob you turn
    #             every year or two as hardware gets faster.

    section("6. Authentication vs authorization in FastAPI")
    print("  AuthN (who are you?)   : a dependency, get_current_user(token=Depends(oauth2_scheme)), runs verify()")
    print("                           and raises 401 with a 'WWW-Authenticate: Bearer' header on failure")
    print("  AuthZ (what may you do?): a second dependency, require_role('ADMIN'), raises 403")
    print("  401 = not authenticated / bad token; 403 = authenticated but forbidden. Deny by default.")
    print("  Gotcha (see 05_web_apis_fastapi/README.md): a required Header(...) that is MISSING fails")
    print("  validation with 422 before your code runs; only a present-but-wrong value reaches your 401.")
    print("  CSRF matters for cookie auth in browsers; CORS is a browser rule, not an auth mechanism.")


# ================================================================ password storage helpers
ITERATIONS = 600_000          # OWASP's figure for PBKDF2-HMAC-SHA256 (its 210,000 is for SHA-512)


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${b64url(salt)}${b64url(digest)}"


def check_password(password: str, stored: str) -> bool:
    _, iterations, salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), b64url_decode(salt), int(iterations))
    return hmac.compare_digest(candidate, b64url_decode(digest))


def needs_rehash(stored: str) -> bool:
    return int(stored.split("$")[1]) < ITERATIONS


if __name__ == "__main__":
    main()


# EXERCISE 1: add key rotation - a 'kid' header that selects from {kid: key}, where old keys may
#             still VERIFY but only the current key SIGNS. How long must an old key stay?
# EXERCISE 2: add a deny-list: give each token a random 'jti' and reject tokens whose jti is in a set.
#             What does that cost you compared with a fully stateless JWT?
# EXERCISE 3: rewrite verify() with PyJWT (pip install pyjwt) and confirm every attack in section 2
#             is still rejected. Then remove algorithms=[...]: PyJWT 2 refuses - why is that the safe default?
