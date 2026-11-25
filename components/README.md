# Shared component system

`workspace.css` is the token-based component foundation used by both concepts and generated applications. Components include solid/secondary/destructive buttons, text/date/number/URL inputs, selects, textareas, cards, tables, status badges, meters, navigation, dialogs, toast feedback and empty/loading/error/offline/unauthorized states.

Visual properties are global CSS variables. Forms use explicit labels and native constraints; the server independently validates inputs. Modal focus and Escape behavior use native dialog elements. The UI inserts user content with textContent and DOM creation, not innerHTML. Destructive actions require a concrete confirmation. Loading, API errors and offline conditions expose visible feedback.

Advanced galleries, ghost/gradient/glass button variants, file uploads, calendars, Kanban, drag-and-drop, nested navigation, rich charts and resizable panels remain extension work. Do not add a decorative control without defining and implementing its action.
