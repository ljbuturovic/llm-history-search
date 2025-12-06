# llm-history-search

![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=000.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Browser extension for searching past chatbot conversations across
multiple LLMs

## The Problem

I routinely use four top LLMs (ChatGPT, Claude, Gemini and Grok). But
I don't have a way to track which conversation I had with which
LLM. The only way to find the conversations that I know of is to login
to each LLM and search. This is very tedious.

The llm-history-search extension and accompanying Web site search your
past conversations across the four LLMs. It automatically keeps track
of the conversations locally.

## How to Install and Use

- Install the llm-history-search Chrome extension (easiest: just visit
  [conversai.us](https://conversai.us) and it has the link to the
  extension)

- Once installed, visit and use ChatGPT, Claude, Gemini, or Grok
  (conversations are automatically captured in the background and
  stored in Chrome local storage on your disk)

- Point Chrome to conversai.us and search your conversations by
  keyword

# Important Notes

- llm-history-search searches only conversations performed using
  Chrome on a single computer, not across computers

- llm-history-search searches only conversations performed after the
  extension has been installed. To search prior conversations, you
  must re-visit them after installing llm-history-search

- Target audience: people accessing multiple LLMs from a single
  computer via Chrome
