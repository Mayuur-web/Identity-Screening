---
name: Parakh Seva
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf2'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fb'
  on-surface: '#111c2d'
  on-surface-variant: '#43474d'
  inverse-surface: '#263143'
  inverse-on-surface: '#ecf1ff'
  outline: '#74777e'
  outline-variant: '#c4c6ce'
  surface-tint: '#505f76'
  primary: '#000f22'
  on-primary: '#ffffff'
  primary-container: '#152539'
  on-primary-container: '#7c8ca4'
  inverse-primary: '#b7c8e1'
  secondary: '#4a3ee6'
  on-secondary: '#ffffff'
  secondary-container: '#645cff'
  on-secondary-container: '#fffbff'
  tertiary: '#1a0b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#33200c'
  on-tertiary-container: '#a3866b'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d3e4fe'
  primary-fixed-dim: '#b7c8e1'
  on-primary-fixed: '#0b1c30'
  on-primary-fixed-variant: '#38485d'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#331dd2'
  tertiary-fixed: '#ffdcbd'
  tertiary-fixed-dim: '#e1c1a3'
  on-tertiary-fixed: '#291805'
  on-tertiary-fixed-variant: '#59422c'
  background: '#f9f9ff'
  on-background: '#111c2d'
  surface-variant: '#d8e3fb'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  stack-gap-sm: 8px
  stack-gap-md: 16px
  stack-gap-lg: 24px
---

## Brand & Style

The design system is engineered for high-stakes enterprise environments where security, speed, and precision are paramount. The brand personality is **authoritative, analytical, and unwavering**, functioning as a "digital forensic" environment.

The aesthetic follows a **Corporate / Modern** approach with a focus on **high-information density**. It utilizes clean white space to prevent cognitive overload, while leveraging structured data grids and precise alignment to communicate technical rigor. The UI should evoke a sense of absolute reliability—acting as a silent, powerful partner in fraud detection and identity verification.

Key principles:
- **Clarity over Decoration:** Every element must serve a functional purpose in the verification workflow.
- **Explainability:** AI-driven insights are presented through clear visual hierarchies and status indicators.
- **Security-First:** The interface uses robust, structured layouts to instill confidence in the platform's data integrity.

## Colors

The palette is anchored by **Deep Navy (#0A2540)** to project institutional trust and stability. **Indigo (#635BFF)** is reserved for primary actions and interactive states, providing a modern, tech-forward accent.

The semantic system is critical for document verification:
- **Success (Green):** Indicates "Verified" or "Authentic."
- **Warning (Amber):** Signals "Suspicious" or "Manual Review Required."
- **Error (Red):** Flags "Fraudulent," "Expired," or "High Risk."

Surface colors utilize a layered white and light-gray approach to separate navigation, sidebars, and main content areas without relying on heavy borders.

## Typography

The design system utilizes **Inter** exclusively for its exceptional legibility in data-heavy interfaces. The typographic scale is optimized for reading document metadata and technical logs.

- **Headlines:** Bold and tight to anchor sections.
- **Labels:** Small, uppercase, and semi-bold for metadata headers (e.g., "DATE OF BIRTH", "DOCUMENT TYPE").
- **Body Text:** Standardized at 14px for the majority of the UI to maintain high density while ensuring readability.
- **Data Mono:** While Inter is used, specific data fields (like Passport Numbers or Wallet Addresses) should use a medium weight with slightly wider tracking to mimic tabular alignment.

## Layout & Spacing

This design system uses a **12-column fluid grid** for dashboard views and a **fixed 800px column** for individual document review pages. 

- **Density:** We utilize a 4px base unit. In verification tables, vertical padding is reduced (8px) to maximize the amount of information visible on a single screen.
- **Breakpoints:**
  - **Desktop (1280px+):** 12 columns, 24px margins.
  - **Tablet (768px-1279px):** 8 columns, 16px margins.
  - **Mobile (<767px):** 4 columns, 16px margins. Content stacks vertically; large data tables transition to card-based list items.

## Elevation & Depth

To maintain a professional and "flat" enterprise aesthetic, depth is communicated primarily through **tonal layers** and **low-contrast outlines** rather than heavy shadows.

- **Base Level:** Light Gray (#F8FAFC) background.
- **Card Level:** White (#FFFFFF) surface with a 1px border (#E2E8F0).
- **Interactive Level:** Subtle, extra-diffused shadow (Y: 2px, Blur: 4px, 5% opacity) only on hover to indicate clickability.
- **Overlays:** Modals use a slightly stronger shadow and a 40% opacity Navy backdrop to focus user attention on critical decision-making tasks.

## Shapes

The shape language balances modern software trends with professional rigidity. 

- **Standard Elements:** Buttons, Input fields, and small UI components use a **0.5rem (8px)** radius.
- **Containers:** Dashboard cards and document containers use a **0.75rem (12px)** radius to soften the large grid blocks.
- **Status Badges:** Use a fully rounded "Pill" shape to distinguish them from interactive buttons.
- **Icons:** Should follow a 2px stroke width with slightly rounded terminals to match the typography.

## Components

### Buttons
- **Primary:** Navy background, white text. No gradient.
- **Secondary:** White background, 1px #E2E8F0 border, Navy text.
- **Ghost:** No border, Indigo text. Used for secondary actions in tables.

### Input Fields
- 1px #E2E8F0 border, 8px radius. 
- Focus state: 1px Indigo border with a subtle 2px Indigo "glow" (outline-offset).
- Error state: 1px Red border with red helper text.

### Status Badges (High Contrast)
- **Verified:** Light Green background, Dark Green text.
- **Flagged:** Light Amber background, Dark Amber text.
- **Rejected:** Light Red background, Dark Red text.
- All badges use semi-bold, uppercase labels at 11px.

### Cards & Tables
- **Review Cards:** Use a 1px border and 12px padding. 
- **Data Tables:** Horizontal zebra striping is discouraged; use subtle 1px horizontal dividers. Header row should have a light gray background (#F8FAFC).

### Specific AI Components
- **Confidence Score Gauge:** A circular or linear progress bar using semantic colors (Green for >90%, Amber for 60-89%, Red for <60%).
- **Reasoning Snippets:** Small, "Data-Mono" styled text blocks explaining *why* the AI flagged a specific field.