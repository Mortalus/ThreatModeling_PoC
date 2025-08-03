### Critical Rules - DO NOT VIOLATE

- **NEVER create mock data or simplified components** unless explicitly told to do so

- **NEVER replace existing complex components with simplified versions** - always fix the actual problem

- **ALWAYS work with the existing codebase** - do not create new simplified alternatives

- **ALWAYS find and fix the root cause** of issues instead of creating workarounds

- When debugging issues, focus on fixing the existing implementation, not replacing it

- When something doesn't work, debug and fix it - don't start over with a simple version

- Always consider modular setup, a lot of files are in other folders in smaller components. Read them, consider them and follow this principle!

### TypeScript and Linting

- ALWAYS add explicit types to all function parameters, variables, and return types

- ALWAYS run `pnpm build` or appropriate linter command before considering any code changes complete

- Fix all linter and errors immediately - don't leave them for the user to fix

- When making changes to multiple files, check each one for type errors
