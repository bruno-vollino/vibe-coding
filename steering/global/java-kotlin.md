# Java & Kotlin

1. ESSENTIAL: Try to use idea intellij MCP first to speed up things. If not possible, let me know why and pause.

## Java conventions

### Class Organization
1. Static fields (constants)
2. Instance fields
3. Constructors
4. Public methods
5. Private methods
6. Inner classes / records

### Naming
- Classes: `PascalCase` — e.g., `RunningBallGoalHappeningCalculator`
- Methods: `camelCase` — e.g., `getHappenings()`, `shouldCreateGoalHappenings()`
- Constants: `UPPER_SNAKE_CASE` — e.g., `SIGNAL_PROVIDER`, `FEED_TYPE`
- Packages: lowercase, dot-separated — e.g., `com.bwinparty.efi.provider.runningball.soccer`

### Imports
- No wildcard imports
- Group by: java/javax → third-party (org, com, io) → internal (com.bwinparty)
- Static imports at the end

### Spring Patterns
- Use `@Configuration` + `@Import` for composing config modules
- Use `@Bean` methods for explicit wiring
- Use `@EnableScheduling` for scheduled tasks
- Use `@MockitoBean` (not `@MockBean`) for test mocks in Spring Boot tests

### Reactive
- Return `Mono<T>` or `Flux<T>` from service methods
- Use `StepVerifier` for testing reactive streams
- Chain with `flatMap()`, `map()`, `switchIfEmpty()` — avoid `.block()`
- Use `Mono.defer()` for lazy evaluation

### Records & Data Classes
- Use Java records for simple immutable data carriers
- Use sealed interfaces/classes where appropriate for type hierarchies

## Kotlin

### Style
- Use `lateinit var` for Spring-injected properties
- Use `enum class` with constructor properties: `enum class Foo(val code: Int)`
- Use backtick-quoted names for test methods: `` `awarded first half`() ``
- Use DSL-style lambdas for builder/simulator APIs
- Use data classes for DTOs and value objects

### Null Safety
- Rely on Kotlin's type system (`T` vs `T?`) instead of Optional
- Use `lateinit var` for non-null properties initialized after construction
- Avoid `!!` operator — prefer safe calls (`?.`) or `requireNotNull()`

## Testing (Both Languages)

### Run tests
IMPORTANT: Use intellij mcp instead of maven when possible.

### Dependencies to not add
- jqwik 

### Structure
- Always include `// given`, `// when`, and `// then` comments to delimit test blocks
- Test class naming: `{ClassName}Test` for unit tests, `{Feature}Test` for integration tests
- Use JUnit 5 Jupiter annotations (`@Test`, `@BeforeEach`, `@ParameterizedTest`, `@CsvSource`, etc.)
- Use `@ParameterizedTest` whenever possible to cover multiple scenarios in a single test method

### Java Test Naming
- camelCase, starting with `should` and ending with a `When` clause describing the condition
- Pattern: `should{ExpectedBehavior}When{Condition}` — e.g., `shouldReturnTrueWhenInputIsValid()`, `shouldThrowExceptionWhenIdIsNull()`

### Kotlin Test Naming
- Backtick descriptive phrases: `` `awarded first half`() ``

### Test Class Layout
- Declare the class under test and its dependencies as class-level fields
- Do NOT use `@Mock` or `@InjectMocks` — instantiate mocks with `mock()` and pass them via the constructor
- The class under test should be constructed inline using its constructor with mocked dependencies
- Put `private static` helper methods at the end of the test class

```java
class MyServiceTest {

    final DependencyA dependencyA = mock();
    final DependencyB dependencyB = mock();

    final MyService service = new MyService(dependencyA, dependencyB);

    @Test
    void shouldDoSomethingWhenConditionIsMet() {
        // given
        when(dependencyA.getValue()).thenReturn("test");

        // when
        var result = service.execute();

        // then
        assertThat(result).isEqualTo("expected");
    }

    private static SomeObject createTestObject() {
        return new SomeObject("value");
    }
}
```

### Assertions
- Use AssertJ `assertThat` for all assertions: `assertThat(result).hasSize(2).hasExactlyElementsOfTypes(...)`
- Use static imports for AssertJ methods: `import static org.assertj.core.api.Assertions.assertThat`
- Use `StepVerifier` for reactive streams: `StepVerifier.create(mono).assertNext(...).verifyComplete()`
- Use Mockito `verify()` for interaction testing, `ArgumentCaptor` for capturing arguments

### Test Infrastructure
- Abstract base test classes for shared setup (e.g., `AbstractRunningBallSoccerIntegrationTest`, `TestBase`)
- `@SpringBootTest` for integration tests with explicit class configuration
- Test factories for creating domain objects (e.g., `EventEntryFactory`, `MatchEntryFactory`)
- Allure annotations (`@Epic`, `@Issue`) on integration test classes for reporting
- Test resource files (JSON fixtures) in `src/test/resources/json/`
- Property testing in unit tests in general are useless (the ones you use to add jqwik for), please don't add them unless they are supposed to cover something that unit tests can't.