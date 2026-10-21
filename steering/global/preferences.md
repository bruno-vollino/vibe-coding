---
inclusion: always
---

# Directives
- Never change files outside my workspace
- With my permission, you may edit my global steering files in my profile's .kiro directory

# Coding Preferences

## Code Style
- Java: explicit types over `var`. Kotlin: inference when the type is obvious
- Short, focused methods; extract helpers over long methods
- Descriptive names, no abbreviations (except `id`, `url`, `config`)
- Comments explain "why", not "what"; code should be self-documenting
- Utility classes: private constructor with `// no-impl` body
- Always Unix line endings (`\n`), never `\r` or `\r\n`

## Architecture
- Constructor injection over field injection
- `@Configuration` + `@Bean` + `@Import` for modular composition
- Reactive-first: prefer `Mono`/`Flux` over blocking
- Nullable returns: `Optional<T>` in Java, `T?` in Kotlin

## Error Handling
- Handle errors via reactive composition (`onErrorResume`, `onErrorMap`), not try-catch
- Propagate as `Mono.error()` / `Flux.error()` in reactive chains
- Never swallow exceptions silently

## Git
- Prefer the git MCP server over shell git commands; fall back to shell only for operations the MCP server lacks (e.g. blame, rev-parse, merge-base, ls-files, cat-file, fetch)
- Pass the command before its arguments when possible

## Documentation
- Keep README.md current (build commands, architecture, tech stack)
- Javadoc on public API in library modules; none required on internal classes
