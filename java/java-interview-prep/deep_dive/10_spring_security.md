# Spring Security, JWT and OAuth2

> **Runnable:** [`01_jwt_hs256_and_password_hashing.java`](../examples/10_spring_security/01_jwt_hs256_and_password_hashing.java)
> **Crib sheet:** [`topics/06-spring-data-jpa-transactions-security.md`](../topics/06-spring-data-jpa-transactions-security.md) · **Guide:** Q44, Q45

## What interviewers are actually probing

Authentication vs authorisation is the opening; then JWT details (what is signed, what isn't, where to store it, how to revoke), the filter chain,
method security, CSRF/CORS confusion, password storage, and how microservices propagate identity. Wrong answers here are *security* wrong answers, so precision matters.

## Must-know points

- **AuthN**: who are you (credentials → `Authentication`). **AuthZ**: what may you do (roles/authorities/ownership). 401 vs 403.
- Spring Security is a chain of **servlet filters** (`SecurityFilterChain`); the `SecurityContext` holds the authenticated principal (thread-local by default).
- A JWT is **signed** (integrity), not encrypted (confidentiality). Verify signature, `exp`, `nbf`, `iss`, `aud`; pin the algorithm.
- Passwords: **slow, salted adaptive hash** (BCrypt/Argon2/PBKDF2/scrypt via `DelegatingPasswordEncoder`); never SHA-256/MD5, never reversible.
- CSRF protects cookie/session-authenticated browser apps; stateless bearer-token APIs normally disable it. CORS is a browser policy, **not** authentication.
- `WebSecurityConfigurerAdapter` is gone (Spring Security 5.7+/6): declare a `SecurityFilterChain` bean with the lambda DSL.

## Interview questions and full answers

### Q1. Authentication versus authorisation, 401 versus 403?

Authentication establishes identity (password, token, certificate, SSO). Authorisation decides what that identity can do (role/permission/ownership).
**401 Unauthorized** really means "unauthenticated" (missing/invalid credentials; include `WWW-Authenticate`). **403 Forbidden** means authenticated but not permitted. Use 404 instead of 403 when revealing existence is itself a leak.

### Q2. How does Spring Security work internally?

A `DelegatingFilterProxy` hands each request to the `FilterChainProxy`, which selects a `SecurityFilterChain` and runs its filters in a defined order: context persistence, CORS, CSRF, logout, **authentication filters** (`UsernamePasswordAuthenticationFilter`, `BearerTokenAuthenticationFilter`), exception translation, and finally **authorisation** (`AuthorizationFilter`).
Authentication filters build an `Authentication` and call the `AuthenticationManager` → `ProviderManager` → `AuthenticationProvider`(s) (DAO provider + `UserDetailsService` + `PasswordEncoder`, or JWT decoder). On success the principal is stored in the `SecurityContextHolder`.

### Q3. Show a modern resource-server configuration.

```java
@Configuration @EnableMethodSecurity
class SecurityConfig {
    @Bean SecurityFilterChain api(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())                                    // stateless bearer tokens
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(a -> a
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/orders/**").hasAuthority("SCOPE_orders.read")
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())                               // deny by default
            .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))     // issuer-uri / jwk-set-uri from properties
            .build();
    }
}
```

Method level: `@PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")`, `@PostAuthorize`, `@PreFilter`.

### Q4. What is a JWT and what are its weaknesses?

`header.payload.signature`, Base64URL-encoded JSON (example 10/01 prints all three). The signature proves the issuer and integrity; **anyone can read the payload**.
Weaknesses: can't be revoked before `exp` (use short lifetimes + refresh tokens, a deny-list, or opaque tokens with introspection); size on every request; `alg=none`/algorithm-confusion attacks if the verifier trusts the header; secret leakage with HS256 shared keys;
XSS if stored in `localStorage`.

### Q5. HS256 vs RS256?

HS256 is HMAC with **one shared secret**: every verifier can also mint tokens — acceptable inside one service. RS256/ES256 uses a **private key to sign and a public key to verify**: the authorisation server signs; services verify via JWKS (`jwk-set-uri`) and key rotation (`kid`). Prefer asymmetric across services/teams.

### Q6. Where should a token be stored and how do you refresh it?

Browser: `HttpOnly; Secure; SameSite` cookies (not readable by JS, so XSS can't steal them; then CSRF protection matters) or keep the access token in memory with the refresh token in an HttpOnly cookie.
Mobile/server: platform secure storage / secret store. Access token 5–15 minutes; refresh token **rotated on use** and bound to the client, revocable server-side; detect reuse and revoke the family.

### Q7. Explain OAuth2 / OIDC flows briefly.

**Authorization Code + PKCE**: user-facing apps (browser/mobile) — the safe default. **Client Credentials**: service-to-service, no user. **Refresh Token**: obtain new access tokens. (Implicit and Resource Owner Password are deprecated.)
OAuth2 is **authorisation** (scopes); **OIDC** adds an ID token for **authentication** (who the user is). In Spring: `spring-boot-starter-oauth2-client` for login, `-resource-server` for APIs, Spring Authorization Server or Keycloak/Auth0/Entra ID as the IdP.

### Q8. How do you store passwords?

`DelegatingPasswordEncoder` (default `bcrypt`, hash prefixed with `{bcrypt}`) so you can migrate algorithms. The work factor makes each guess expensive and the per-user salt defeats rainbow tables (example 10/01 section 5: ~0.5 s per PBKDF2 hash vs microseconds for SHA-256).
Add rate limiting/lockout, breached-password checks and MFA; never log credentials; never email passwords.

### Q9. CSRF and CORS — what are they and when do they matter?

**CSRF**: a malicious site makes the victim's browser send a request with their **cookies**. It applies when auth is cookie/session-based; mitigated with CSRF tokens and `SameSite`. Pure bearer-header APIs aren't vulnerable (the browser doesn't auto-attach the header), so disabling CSRF there is correct.
**CORS**: the browser's same-origin relaxations; the server lists allowed origins/methods/headers. It prevents *reading* cross-origin responses; it does not stop a request being sent and is not an authentication mechanism.

### Q10. How is identity propagated across microservices?

Gateway authenticates the user and forwards the **access token** (or exchanges it — OAuth2 Token Exchange — for a narrower audience-specific token); each service validates it as a resource server; service-to-service calls without a user use the Client Credentials flow or **mTLS** (service mesh).
Never trust a user id passed in a plain header from the network unless the gateway is the only path and is cryptographically enforced.

### Q11. Common vulnerabilities to mention (OWASP) and your mitigations?

Injection (parameterised queries, never string-concatenated JPQL/SQL), broken access control/IDOR (check ownership, not just role), mass assignment (DTOs), sensitive data exposure (TLS, field masking in logs), security misconfiguration (actuator, CORS `*`), vulnerable dependencies (SCA scans: Dependabot/Snyk/OWASP DC), SSRF, insecure deserialisation (Jackson default typing).

### Q12. Multi-tenant authorisation design?

Tenant id comes from the **validated token claim**, not a request parameter; enforce it centrally (a filter that sets a tenant context + Hibernate filter/`@Where`/row-level security) so no query can forget it; add tests that attempt cross-tenant access. Log tenant id for audit.

## A worked example

Run [`01_jwt_hs256_and_password_hashing.java`](../examples/10_spring_security/01_jwt_hs256_and_password_hashing.java): it signs a token with `HmacSHA256`, then shows an edited roles claim failing the signature check,
the `alg=none` downgrade being rejected because the algorithm is pinned, and expiry. Note the constant-time comparison (`MessageDigest.isEqual`).

## Hands-on drills

1. Configure a resource server against Keycloak (Docker) and call an endpoint with a token from the Client Credentials flow.
2. Add `@PreAuthorize` rules that check object ownership and write a `@WebMvcTest` with `@WithMockUser` that proves 403.
3. Decode a real JWT by hand (Base64URL) and explain every claim.
4. Implement refresh-token rotation with reuse detection (data model + algorithm).
5. List the headers you'd add (HSTS, CSP, X-Content-Type-Options) and what each prevents.

## The 60-second spoken answer

"Authentication says who you are, authorisation says what you can do; a failed login is 401, a forbidden action 403. In Spring Security a
filter chain authenticates, normally as an OAuth2 resource server validating a signed JWT's signature, issuer, audience and expiry, and then
authorises per endpoint and per method, denying by default. Tokens are short-lived with rotating refresh tokens; passwords use
BCrypt or Argon2 through the delegating encoder. I disable CSRF only for stateless bearer APIs, treat CORS as a browser policy not security, and
take tenant and user identity from the validated token rather than request parameters."
