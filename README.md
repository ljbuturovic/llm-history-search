# llm-history-search

![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=000.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Chrome extension for searching past chatbot conversations across
multiple LLMs

## The Problem

I routinely use five top LLMs (ChatGPT, Claude, Gemini, Grok, and
Perplexity). But I don't have a way to track which conversation I had
with which LLM. The only way to find the conversations that I know of
is to login to each LLM and search. This is very tedious.

The llm-history-search extension and accompanying Web site search your
past conversations across these LLMs. It automatically keeps track
of the conversations locally.

## How to Install and Use

- Install the llm-history-search Chrome extension (easiest: just visit
  [conversai.us](https://conversai.us) and it has the link to the
  extension)

- Once installed, visit and use ChatGPT, Claude, Gemini, Grok, or
  Perplexity. Conversations are automatically captured in the background
  and stored in Chrome local storage on your disk

- Point Chrome to [conversai.us](https://conversai.us) and search your
  conversations by keywords

# Important Notes

- llm-history-search searches only conversations performed using
  Chrome on a single computer, not across computers

- llm-history-search searches only conversations performed after the
  extension has been installed. To search prior conversations, you
  must re-visit them after installing llm-history-search

- Target audience: people accessing multiple LLMs from a single
  computer via Chrome

## Developer Note: Capturing Conversation Content

The extension works by reading the text content of AI conversation pages as you browse them. To avoid capturing irrelevant content (like the sidebar that lists all your past conversations), the extension uses CSS selectors to target only the actual conversation area of each page.

### Why this can break

Each AI provider (Claude, ChatGPT, etc.) builds their pages differently, and they update their HTML structure periodically. When that happens, the selector that was working may no longer find the right element on the page.

**There are two ways this can manifest as a bug:**

1. **Search returns too many unrelated results** — the selector broke and the extension fell back to capturing the entire page, including the sidebar. Since the sidebar lists all your conversation titles, every conversation ends up containing every other conversation's title in its stored text. Searching for any word that appears in any sidebar title will match all conversations.

2. **Search returns no results for a conversation you know exists** — the selector broke and there is no fallback, so the conversation is stored with empty text. It can only be found if the search term appears in the conversation's title.

### How to fix it

When a selector breaks for a provider, you need to find a new one by inspecting the page HTML in Chrome DevTools:

1. Open a conversation on the affected provider's website
2. Open DevTools (F12) → Console tab
3. Try `document.querySelector('[data-testid*="message"]')` — look for elements with stable `data-*` attributes rather than CSS class names, as class names change more often
4. Once you find an element inside the conversation area, use `.closest('div[data-something]')` to walk up to the container
5. Verify it returns actual conversation text with `.innerText.slice(0, 200)`

**Prefer `data-*` attributes and `role` attributes over CSS class names** — they are tied to functionality and tend to survive UI redesigns. CSS class names (especially Tailwind utility classes like `flex`, `min-h-full`, etc.) change frequently.

### Current selectors

| Provider | Selector | Notes |
|---|---|---|
| Claude | `[data-autoscroll-container]` | Found 2026-03; previous Tailwind selector broke |
| ChatGPT | `main` | Standard HTML element, stable |
| Gemini | `.conversation-container` or `main` | |
| Grok | `main` | |
| Perplexity | `main` | |

If a selector breaks and you need to clear contaminated data, use the **Clear Data** button in the app, then re-visit your conversations to recapture them.
