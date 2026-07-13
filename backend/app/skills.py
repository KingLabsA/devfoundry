"""Skills: reusable expert capability modules that shape the pipeline output.

Each skill injects guidance into the spec, design, and codegen stages so runs
produce professional, production-grade results (the "$1k-$10k" quality bar).
Skills are selectable per run; several can combine.
"""

# A house design system every build follows unless a skill overrides it.
DESIGN_SYSTEM = """
DESIGN SYSTEM (follow precisely for a premium, modern result):
- Stack: Vite + React + TypeScript + Tailwind CSS. Component-per-file structure.
- Layout: mobile-first, responsive (sm/md/lg/xl breakpoints), max-w-7xl centered containers,
  generous whitespace (section padding py-16 md:py-24), 12-col mental grid.
- Type scale: clear hierarchy — display (text-5xl/6xl font-bold tracking-tight), h2 (text-3xl),
  body (text-base leading-relaxed text-slate-600). Use a system font stack.
- Color: one primary brand color + neutral slate scale; subtle gradients; consistent accent.
  Support a dark mode class if feasible.
- Components: rounded-xl cards with border + soft shadow (shadow-sm hover:shadow-md),
  buttons with hover/active/focus states and transitions, sticky nav, footer.
- Content: write REAL, specific, benefit-led copy — never 'lorem ipsum' or 'Feature 1'.
- Motion: tasteful transitions (transition, duration-200), hover lifts, no gaudy animation.
- Accessibility: semantic HTML5, labelled controls, alt text, visible focus rings, WCAG AA contrast.
- Polish: empty states, loading states, hover states, 404 handling where relevant.
- Deliverables: package.json (vite scripts), index.html, src/main.tsx, App + components,
  tailwind config, a README with run steps, and at least one test.
"""

SKILLS: dict[str, dict] = {
    "premium-landing": {
        "label": "Premium landing page",
        "desc": "Conversion-focused marketing site: hero, social proof, features, pricing, FAQ, CTA.",
        "guidance": "Build a high-converting landing page: sticky nav, gradient hero with a clear "
                    "value prop + primary CTA, logo/social-proof strip, 3-6 feature cards with icons, "
                    "a pricing table (3 tiers, highlighted middle), testimonials, FAQ accordion, and a "
                    "footer with links. Persuasive, specific copy tailored to the product.",
    },
    "saas-dashboard": {
        "label": "SaaS dashboard",
        "desc": "App shell with sidebar nav, KPI cards, charts, data tables, and forms.",
        "guidance": "Build an application dashboard: left sidebar navigation, top bar with search + user "
                    "menu, a KPI stat-card row, at least one chart (use a lightweight lib or SVG), a "
                    "sortable/filterable data table, and a create/edit form in a modal. Clean, dense-but-"
                    "legible enterprise UI.",
    },
    "ecommerce": {
        "label": "E-commerce storefront",
        "desc": "Product grid, product detail, cart, and checkout flow.",
        "guidance": "Build a storefront: responsive product grid with cards (image, title, price, quick-add), "
                    "product detail page, a slide-over cart with quantity controls and totals, and a "
                    "checkout form. Include realistic sample products.",
    },
    "portfolio": {
        "label": "Portfolio / personal site",
        "desc": "Elegant personal site: hero, projects, about, contact.",
        "guidance": "Build a refined personal portfolio: hero with name + tagline, a projects grid with "
                    "hover detail, an about section with skills, and a contact form. Editorial, confident design.",
    },
    "web-app-crud": {
        "label": "Full CRUD web app",
        "desc": "End-to-end app: API + persistence + UI for a real domain (notes, tasks, etc.).",
        "guidance": "Build a complete CRUD app with a small API layer, persistence (in-memory or SQLite), "
                    "list/create/edit/delete UI, form validation, and optimistic updates.",
    },
    "docs-blog": {
        "label": "Docs / blog site",
        "desc": "Content site with markdown, navigation, and search.",
        "guidance": "Build a content site: markdown-rendered articles, a sidebar table of contents, tag "
                    "filtering, client-side search, and a clean reading layout with good typography.",
    },
    "a11y-first": {
        "label": "Accessibility-first",
        "desc": "Extra emphasis on WCAG AA+, keyboard nav, and screen-reader support.",
        "guidance": "Prioritize accessibility: full keyboard navigation, ARIA where needed, skip links, "
                    "focus management, prefers-reduced-motion support, and AA+ contrast throughout.",
    },
    "seo-optimized": {
        "label": "SEO-optimized",
        "desc": "Meta tags, semantic structure, Open Graph, structured data.",
        "guidance": "Optimize for SEO: complete meta tags, Open Graph/Twitter cards, semantic headings, "
                    "descriptive alt text, a sitemap-friendly structure, and JSON-LD structured data.",
    },
}


def catalog() -> list[dict]:
    return [{"id": k, "label": v["label"], "desc": v["desc"]} for k, v in SKILLS.items()]


def build_guidance(skill_ids: list[str]) -> str:
    """Compose the design system + selected skills into a guidance block for the LLM."""
    parts = [DESIGN_SYSTEM.strip()]
    for sid in skill_ids:
        skill = SKILLS.get(sid)
        if skill:
            parts.append(f"SKILL — {skill['label']}: {skill['guidance']}")
    return "\n\n".join(parts)
