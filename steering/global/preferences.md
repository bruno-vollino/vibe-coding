# Directives
- Do not ever change files outside my workspace
- If I give you permission, you can modify my global steering files on my profile's .kiro directory

# General Coding Preferences

## Code Style
- Prefer explicit types over `var`/`val` type inference in Java; use inference in Kotlin where the type is obvious
- Keep methods short and focused — extract helpers rather than writing long methods
- Use descriptive names without abbreviations (except standard ones like `id`, `url`, `config`)
- Minimal inline comments — code should be self-documenting; use comments for "why", not "what"
- Private constructors on utility classes with `// no-impl` body comment
- Always use Unix-style line endings (`\n`). Never use carriage return (`\r`) or Windows-style `\r\n`

## Architecture
- Constructor injection over field injection for dependencies
- `@Configuration` classes with `@Bean` methods and `@Import` for modular composition
- Reactive-first: prefer `Mono`/`Flux` composition over blocking operations
- Use `Optional<T>` for nullable return values in Java; use Kotlin's nullable types (`T?`) in Kotlin

## Error Handling
- Handle errors through reactive composition (`onErrorResume`, `onErrorMap`) rather than try-catch
- Propagate errors as `Mono.error()` / `Flux.error()` in reactive chains
- Avoid swallowing exceptions silently

## Git & Branching

## Documentation
- Keep README.md files up to date with build commands, architecture, and tech stack
- Javadoc on public API methods in library modules (ses-soccer)
- No Javadoc required on internal implementation classes