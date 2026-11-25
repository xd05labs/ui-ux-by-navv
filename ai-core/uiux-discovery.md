# UI/UX discovery comes first

For a user invoking AppForge to design or build an application, start a conversational UI/UX wizard. A pasted guide is an invitation to begin the wizard, not to summarize the repository. Repository maintenance, explicit backend-only requests and questions about AppForge itself follow their stated task instead.

Read any software description and previous design answers. Briefly acknowledge known preferences, then ask the first unanswered design question from `wizard/uiux-flow.json`. If no design decisions are known, the first question must be **Which UI style would you like?** Display the actual lettered style options and wait for a reply. Do not lead with architecture, deployment, business workflow questions, installation commands or a capability lecture. UI/UX conversation requires no filesystem or terminal tools.

## Conversation rules

- Show one design stage per reply, with at most three questions. Do not dump the whole questionnaire at once. Give every question concrete choices, a recommendation with a short reason, Auto, and Custom.
- Use the host's native choice controls when available; otherwise use a readable lettered list. Do not require a special UI tool to continue the conversation.
- With EVERY design question, display its actual comparison image from the matching menu in AI_START.md, using a Markdown image or the host's image display. Put the sample before the choices and keep a clickable **Open visual samples** link. Every tile's letter/number matches the menu. Display only the current question's sample; an expanded style menu uses the separately numbered all-style sample. Do not replace samples with descriptions alone or merely say a sample exists.
- If images cannot render, say so briefly, keep the direct image link and text choices, and let the user open the preview. Never claim an unseen image was displayed. A document cannot grant image rendering to a host. When two questions share a stage, show each sample beside its own numbered question; do not mix their option letters.
- Samples are illustrative concepts, not a finished app, exact implementation promises or brand assets. Background image/video/3D examples and motion storyboards are labeled static concepts. Respect reduced motion; never describe a static PNG as an animation. Preserve already selected preferences when tailoring later previews. For Custom choices or requested variations, show a tailored preview with available host tools; if unavailable, state that limit and retain the reference sample/link without pretending it represents the custom design. Show an actual tailored design preview at review when supported, and keep review pending if the user requested a preview that cannot yet be produced.
- Start with eight curated styles and an option to see all catalog styles. Keep the displayed letter-to-style mapping stable. More styles expands the list without selecting a style or advancing the stage.
- Preserve a style or palette explicitly supplied by the user; ask the next unanswered design choice instead. Blueprint/config defaults are recommendations, not answered questions or approval.
- Auto selects the recommendation for the current question only. Continue to the next unanswered design stage. Only an explicit request to choose all remaining design details authorizes automatic selection of the whole design.
- When a stage contains two questions, number them and accept answers such as Q1 C, Q2 G. A bare letter or Auto answers the first unanswered question only; then ask the remaining question rather than guessing both.
- Accept short answers such as B, dark, ocean blue, or Custom: minimal plus matte glass. Resolve ambiguous answers briefly. Record canonical config paths/values plus the user's original custom notes and provenance.
- Complete style, theme/palette, layout/navigation, component density/radius, typography/icons, background, motion and optional branding choices as relevant. Preserve accessibility, contrast, keyboard navigation, responsive behavior and reduced-motion preferences.
- A selected visual effect or layout is a design requirement. When the shipped renderer cannot implement it, retain it for agent-assisted application work; do not claim the choice is implemented or discard it silently.

## Review gate

After design discovery, show a concise design summary with the chosen style, actual palette colors, theme, navigation, component treatment, typography, background and motion. Offer **Approve design**, **Change a choice**, or **Show two variations**. Do not replace missing choices with an unsolicited completed design. Honor an explicit prior authorization to choose everything or proceed autonomously within constraints, while still showing the selected design.

Only after the design is selected should you continue unanswered application/workflow questions and propose the architecture and implementation plan. Then follow the central approval, generation and validation protocol. Do not generate application code just because the user answered the first style question.

## State and resumption

Save each explicit answer immediately when file tools exist; otherwise emit a compact design checkpoint in chat. Record question path, canonical value, original custom detail and user/recommended/automatic provenance. On resume, skip only actually answered fields and keep design approval distinct from an automatically suggested default. Full implementation context is in AI_CONTEXT.md; reading it must not restart discovery or bypass this review gate.
