/*
 * 01 - JWT (HS256) from scratch, the attacks that matter, and password hashing
 *
 * Run:  java 01_jwt_hs256_and_password_hashing.java
 *
 * Understanding the bytes makes the interview answers concrete: what is signed, what is NOT
 * encrypted, why 'alg: none' and key confusion matter, why expiry + rotation exist, and why
 * passwords need a slow, salted hash (BCrypt/Argon2/PBKDF2) rather than SHA-256.
 */
import javax.crypto.Mac;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

class JwtHs256AndPasswordHashing {

    static final Base64.Encoder B64 = Base64.getUrlEncoder().withoutPadding();
    static final byte[] SECRET = "change-me-32-bytes-minimum-secret!!".getBytes(StandardCharsets.UTF_8);

    static String b64(String s) { return B64.encodeToString(s.getBytes(StandardCharsets.UTF_8)); }
    static String decode(String s) { return new String(Base64.getUrlDecoder().decode(s), StandardCharsets.UTF_8); }

    static String hmac(String data, byte[] key) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        return B64.encodeToString(mac.doFinal(data.getBytes(StandardCharsets.UTF_8)));
    }

    static String sign(String payloadJson) throws Exception {
        String head = b64("{\"alg\":\"HS256\",\"typ\":\"JWT\"}");
        String body = b64(payloadJson);
        return head + "." + body + "." + hmac(head + "." + body, SECRET);
    }

    /** Returns the claims JSON or throws SecurityException with the reason. */
    static String verify(String jwt, long nowEpoch) throws Exception {
        String[] p = jwt.split("\\.");
        if (p.length != 3) throw new SecurityException("malformed token");
        String header = decode(p[0]);
        if (!header.contains("\"alg\":\"HS256\"")) throw new SecurityException("unexpected alg (pin the algorithm server-side): " + header);
        String expected = hmac(p[0] + "." + p[1], SECRET);
        if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), p[2].getBytes(StandardCharsets.UTF_8)))   // constant time
            throw new SecurityException("bad signature");
        String claims = decode(p[1]);
        long exp = Long.parseLong(claims.replaceAll(".*\"exp\":(\\d+).*", "$1"));
        if (nowEpoch >= exp) throw new SecurityException("token expired");
        return claims;
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
        long now = 1_700_000_000L;

        section("1. Anatomy: header.payload.signature (Base64URL, signed - NOT encrypted)");
        String jwt = sign("{\"sub\":\"ravi\",\"roles\":[\"USER\"],\"iss\":\"auth.example.com\",\"exp\":" + (now + 900) + "}");
        String[] parts = jwt.split("\\.");
        System.out.println("  header  = " + decode(parts[0]));
        System.out.println("  payload = " + decode(parts[1]) + "   <- anyone can read this; never put secrets in it");
        System.out.println("  signature (" + parts[2].length() + " chars) proves integrity + who holds the key");
        System.out.println("  verify now           -> " + verify(jwt, now));

        section("2. Attacks and how verification stops them");
        String forgedPayload = b64("{\"sub\":\"ravi\",\"roles\":[\"ADMIN\"],\"exp\":" + (now + 900) + "}");
        String tampered = parts[0] + "." + forgedPayload + "." + parts[2];
        try { verify(tampered, now); } catch (SecurityException e) { System.out.println("  edited roles claim   -> REJECTED: " + e.getMessage()); }
        String none = b64("{\"alg\":\"none\",\"typ\":\"JWT\"}") + "." + parts[1] + ".";
        try { verify(none + "x", now); } catch (SecurityException e) { System.out.println("  alg=none downgrade   -> REJECTED: " + e.getMessage()); }
        try { verify(jwt, now + 901); } catch (SecurityException e) { System.out.println("  after expiry         -> REJECTED: " + e.getMessage()); }
        System.out.println("  Also: verify iss/aud, check nbf, pin the algorithm, use a key of >= 256 bits, rotate keys via 'kid'.");

        section("3. Symmetric vs asymmetric");
        System.out.println("  HS256 : one shared secret signs AND verifies - every verifying service can also mint tokens.");
        System.out.println("  RS256/ES256: auth server signs with a private key; services verify with the public key (JWKS endpoint).");
        System.out.println("  Prefer asymmetric across teams/services; Spring: spring-security-oauth2-resource-server + issuer-uri.");

        section("4. Token lifecycle design");
        System.out.println("  short-lived access token (5-15 min) + refresh token (stored server-side, rotated, revocable)");
        System.out.println("  stateless JWT cannot be 'logged out' before expiry unless you keep a deny-list or use opaque tokens + introspection");
        System.out.println("  store in HttpOnly+Secure+SameSite cookies for browsers (XSS-safe), Authorization: Bearer for service-to-service");

        section("5. Password hashing: slow + salted, never a plain fast hash");
        char[] pw = "correct horse battery staple".toCharArray();
        byte[] salt1 = new byte[16], salt2 = new byte[16];
        SecureRandom rnd = new SecureRandom(); rnd.nextBytes(salt1); rnd.nextBytes(salt2);
        long t0 = System.nanoTime();
        byte[] h1 = pbkdf2(pw, salt1, 210_000);
        long ms = (System.nanoTime() - t0) / 1_000_000;
        byte[] h2 = pbkdf2(pw, salt2, 210_000);
        System.out.println("  PBKDF2-HMAC-SHA256, 210k iterations: ~" + ms + " ms per hash (deliberately slow)");
        System.out.println("  same password, different salt -> different hashes: " + !Arrays.equals(h1, h2));
        t0 = System.nanoTime();
        for (int i = 0; i < 100_000; i++) MessageDigest.getInstance("SHA-256").digest(("guess" + i).getBytes(StandardCharsets.UTF_8));
        System.out.println("  plain SHA-256: 100,000 guesses in ~" + (System.nanoTime() - t0) / 1_000_000 + " ms on ONE core -> trivially brute-forced");
        System.out.println("  Spring Security: PasswordEncoder = DelegatingPasswordEncoder (bcrypt/argon2/pbkdf2/scrypt, {id}hash prefix, upgradable).");

        section("6. Authentication vs authorization in Spring Security");
        System.out.println("  AuthN: who are you?  filter chain -> AuthenticationManager -> AuthenticationProvider -> SecurityContext");
        System.out.println("  AuthZ: what may you do? authorizeHttpRequests(...) + @PreAuthorize(\"hasRole('ADMIN') or #id == principal.id\")");
        System.out.println("  401 = not authenticated / bad credentials; 403 = authenticated but forbidden. Fail closed, deny by default.");
        System.out.println("  CSRF: needed for cookie/session auth with browsers; disable only for stateless bearer-token APIs.");
        System.out.println("  CORS: a browser rule, configured on the server; it is not an auth mechanism.");
    }

    static byte[] pbkdf2(char[] pw, byte[] salt, int iterations) throws Exception {
        return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(new PBEKeySpec(pw, salt, iterations, 256)).getEncoded();
    }
}

// EXERCISE: add key rotation: a 'kid' header selecting from a map of keys, accepting old keys for verify only.
