# Agent Instructions

Always give the best possible response first.

Do not hold back quality and then ask whether the user wants something better,
deeper, or more complete. The first answer should already be the best answer
you can provide.

Never hack a test to get a passing outcome.

Do not alter the system under test, test setup, inputs, timing, environment, or
surrounding conditions just to force a positive result. Any such shortcut makes
the test invalid because it can hide real bugs.

All tests must be run under production-realistic conditions.

Test the system as it would actually behave with live users, live processes,
real sequencing, real dependencies, and real constraints. Do not make the test
easier, cleaner, or more forgiving than production unless the purpose of the
test explicitly requires that and it is clearly labeled.
