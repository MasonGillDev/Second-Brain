# Anonymous V3 Intake Rate Limiting — Built, Then Reverted for WAF

**Project:** Slyd Platform (platform + website)
**Date:** 2026-08-03
**Author:** d2a804d6-22cf-4461-98b9-3c249be2e4d6
**Directory:** /Users/masongill/Slyd-Platform/platform

## What Was Done

Backlog item 7 / P0. **Net code change: zero.** A full application-layer rate
limiter was built across both repos, then reverted in favour of an AWS WAF
rate-based rule. Both repos verified back at their pre-change baselines
(platform 75 pass / 6 pre-existing failures, website 7/7, both 0 build errors).

The remaining artefacts are `Slyd-Platform/docs/waf-rate-limiting.md` (the rule
spec) and this record.

### The problem (unchanged, still open)

Every anonymous V3 intake POST is unthrottled at both hops. Each creates a
Demand/SellSubmission/SiteSubmission/DeploymentBuild/LotDeposit row, a parallel
FormSubmission, a hash-chained audit event, and an ops email — so a script can
burn the ops queue, the SendGrid quota, the append-only audit chain, and the
random 4-digit DisplayId space (collisions there 500 for real users).

### Why the application-layer version was abandoned

It worked and was tested. It was also far heavier than the problem.

The threat is volumetric — bots hammering public forms. WAF does that at the
load balancer: real client IP with no reconstruction, stateless across ECS
tasks, and no ability to break application logic because it isn't in the
application.

Everything expensive in the app version existed only to rebuild, in C#, what the
ALB already knows:

- A trusted-client-IP resolver walking the XFF chain right-to-left, with
  Cloudflare-range and VPC-CIDR config behind it.
- A shared-secret header handshake between website and platform, because the
  website proxies visitor traffic server-to-server and the platform would
  otherwise see one IP for every visitor.
- Blazor circuit plumbing (`PersistentComponentState` + a `CircuitHandler`
  inbound-activity hook + an AsyncLocal accessor), because `Need.razor` is
  `@rendermode InteractiveServer` and calls the intake service straight from the
  circuit where there is no `HttpContext`.

**Nothing was kept.** Per-endpoint cost asymmetry (5/min write vs 60/min read)
is the one thing WAF can't express — but every policy needs a partition key, and
there is no safe key without the whole stack. Keying on
`Connection.RemoteIpAddress` behind an ALB gives every visitor the load
balancer's address and one shared bucket: site-breaking. The website-side
policies that *could* key correctly cover exactly the `POST /api/*` traffic WAF
already handles.

## Findings worth keeping

Four things learned here are true independent of the approach.

### 1. `ForwardedHeaders` with `XForwardedFor` does not give you a trustworthy IP

It rewrites `RemoteIpAddress` from the chain **without knowing where the
trustworthy segment ends**, so a forged leading entry wins. A pipeline test
caught it: 41 of 42 requests rotating a spoofed `X-Forwarded-For` got through.

The correct approach is to walk the chain **right-to-left**, stepping past hops
inside your own networks — forged entries land to the LEFT of what your proxies
appended, so the walk reaches the real edge first. This is also why WAF's
`AggregateKeyType` must be `IP` and not `FORWARDED_IP` on our topology.

### 2. `IHttpClientFactory` pools handlers outside the caller's DI scope

Proved with a probe: a `DelegatingHandler` saw a scoped service matching
*neither* of two callers, and both callers shared one handler instance. So
injecting a circuit-scoped visitor context into a message handler would have
stamped **one visitor's IP onto another visitor's submission** — a cross-user
leak inside a security fix. Handlers must read ambient state
(`IHttpContextAccessor`-style AsyncLocal), never scoped dependencies.

### 3. `/need` submits from a Blazor circuit, not a controller

`Need.razor` is `@rendermode InteractiveServer` and calls
`IntakeService.SubmitNeedAsync` directly — no controller, no `HttpContext`,
because a circuit outlives the request that created it.

This matters beyond rate limiting: **anything that tries to attribute a `/need`
submission to a visitor from `HttpContext` will silently fail.** Backlog item
8(a) — forwarding real client IP / UA / originating page URL — hits exactly this
wall and will need the circuit-capture work.

### 4. Topology, established rather than assumed

`dig slyd.com` → `54.186.152.117` / `100.23.37.143`, AWS us-west-2 ELB
addresses. **Cloudflare hosts DNS but does not proxy.** Deploys are ECS + ECR
behind ALBs, no CloudFront. This determines the WAF key type, and it means
populating Cloudflare IP ranges anywhere in our config would be an attack path
(anyone can point their own Cloudflare zone at our ALB and then dictate
`CF-Connecting-IP`).

## Process note

I drifted. "Rate limit the intake endpoints" was taken literally and each
consequence followed reasonably — but the destination was a custom IP-resolution
stack spanning two repos with a shared-secret handshake, for a problem the load
balancer solves natively. Mason asked whether infrastructure could replace it;
it could, and mostly should have from the start.

Worth asking earlier next time: *is this a job for the application at all?*

## To Do Next

- **Apply the WAF rule.** Spec in `Slyd-Platform/docs/waf-rate-limiting.md`:
  website ALB, rate-based, `AggregateKeyType: IP`, scoped to `POST /api/*`,
  300 per 5 min, deployed in Count mode first. Claude cannot execute AWS
  operations — this is a human task.
- **Answer whether the platform API is internet-reachable.** If it's only
  reachable from the website and admin, no second rule is needed and a security
  group closes it. If it is reachable, a rule there must exclude the website's
  egress addresses or it will throttle the whole site.
- **Check whether a Web ACL already exists** on these ALBs — "add a rule" versus
  "stand up a Web ACL" is a materially different ask.
- **Correct the platform's Swagger copy**, which advertises "60 requests per
  minute / 1000 per hour" limits that have never applied to intake.
- **Retire `RateLimitingMiddleware.cs`** (spoofable key, unbounded
  `List<DateTime>` growth) — but land it *with* the WAF rule, not before, so
  there's no window with neither.
- **Still not addressed by any rate limit:** the deposit endpoint returns SLYD's
  wire details to any caller against an enumerable lot id. Needs its own task.
