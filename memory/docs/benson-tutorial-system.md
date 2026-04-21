# Benson Tutorial System

Interactive first-run walkthrough that highlights UI elements and waits for the user to click them. No auto-navigation — the user stays in control.

## Architecture

Three pieces:

| File | Role |
|------|------|
| `Benson.Client/Services/TutorialService.cs` | State machine — holds step list, current index, completion logic |
| `Benson.Client/Components/TutorialOverlay.razor` | Renders the spotlight cutout, glow ring, and tooltip |
| `Benson.Server/Components/App.razor` | JS interop under `gamma.tutorial.*` — bounding rects, click capture, MutationObserver |

CSS lives at the bottom of `Benson.Server/wwwroot/app.css` under the "Tutorial Overlay" section.

Registered as a scoped service in both `Benson.Client/Program.cs` and `Benson.Server/Extensions/ServiceCollectionExtensions.cs` (needed for SSR prerender).

The overlay component is mounted in `Benson.Client/Layout/MainLayout.razor`. Auto-starts on first visit (checks `localStorage` for `benson_tutorial_completed`). A small `?` button in the sidebar header (`Sidebar.razor`) lets users restart it.

## How It Works

1. `TutorialService.StartAsync()` sets `IsActive = true`, initializes JS interop, fires `OnStepChanged`.
2. `TutorialOverlay` renders an SVG mask with a cutout hole around the target element (via CSS selector), plus a tooltip with step text.
3. The overlay is `pointer-events: none` so clicks pass through to the real UI underneath.
4. Step advancement depends on the `CompletionTrigger`:
   - **ClickTarget** — JS capture-phase listener (`gamma.tutorial.watchClicks`) detects the click, calls `OnTargetClicked` via JSInvokable, which advances the step. The click also reaches the real element.
   - **Navigation** — `NavigationManager.LocationChanged` fires, checks if the new URL matches `ExpectedUrl`.
   - **ManualNext** — user clicks the "Next" button in the tooltip.
5. For page transitions, `WaitForSelector` uses a `MutationObserver` to wait for the target element to appear before positioning the spotlight.

## Editing the Tutorial

All steps are in the static `Steps` list in `TutorialService.cs` (~line 27). Steps play sequentially top-to-bottom.

### Step fields

```csharp
new()
{
    Title = "Step Title",                              // Tooltip heading
    Description = "Instruction text for the user",     // Tooltip body
    Selector = ".css-selector",                        // Element to highlight (null = centered overlay, no spotlight)
    Placement = TooltipPlacement.Right,                // Top | Bottom | Left | Right | Center
    CompletionTrigger = CompletionTrigger.ClickTarget, // ClickTarget | Navigation | ManualNext
    WaitForSelector = ".css-selector",                 // Optional: wait for this to appear before showing
    ExpectedUrl = "/agents"                            // Optional: required for Navigation trigger
}
```

### Adding a step

Insert a new `TutorialStep` object in the `Steps` list at the desired position. Example:

```csharp
new()
{
    Title = "Open MCP Tools",
    Description = "Click to see available tool integrations.",
    Selector = "a.nav-item[href='/mcp']",
    Placement = TooltipPlacement.Right,
    CompletionTrigger = CompletionTrigger.Navigation,
    ExpectedUrl = "/mcp"
},
```

### Removing a step

Delete the entry from the list. Step numbering is implicit from list position.

### Selector tips

- Use `:has()` to disambiguate when multiple elements share a class. For example, `.vault-add-section:has(.add-key-form)` targets the Spawn Agent form specifically, not the Escrow Defaults form above it.
- For nav items, `a.nav-item[href='/agents']` is reliable.
- For nav group headers, `.nav-group:has(a[href='/agents']) .nav-group-header` works.
- Test selectors in browser DevTools with `document.querySelector("...")` before adding them.

### Branching / conditional steps

Currently linear. To skip steps conditionally, modify `NextAsync()` in `TutorialService.cs` to check state and increment past steps that should be skipped:

```csharp
while (CurrentStepIndex < Steps.Count && ShouldSkip(Steps[CurrentStepIndex]))
    CurrentStepIndex++;
```

### Resetting tutorial state

Tutorial completion is stored in `localStorage` as `benson_tutorial_completed`. The sidebar `?` button clears this and calls `StartAsync()`. Users can also clear it manually in DevTools.
