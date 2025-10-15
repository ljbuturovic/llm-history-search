// content.js
console.log('[conversai extension] Content script loaded');

function detectProvider() {
  const { hostname, pathname } = location;

  if (hostname.includes("chatgpt")) return "chatgpt";
  if (hostname.includes("claude")) return "claude";
  if (hostname.includes("gemini")) return "gemini";
  if (
    hostname.includes("grok.com") ||
    hostname === "x.ai" ||
    hostname.endsWith(".x.ai") ||
    (hostname.includes("x.com") && pathname.includes("/grok"))
  ) return "grok";
  return "unknown";
}

function getRuntime() {
  if (typeof chrome === 'undefined' || !chrome.runtime) return null;
  return chrome.runtime;
}

function collectText() {
  const provider = detectProvider();
  let text = '';

  // Provider-specific selectors to get only conversation content
  if (provider === 'chatgpt') {
    // ChatGPT: get main conversation area
    const main = document.querySelector('main') || document.querySelector('[role="main"]');
    text = main ? main.innerText : document.body.innerText;
  } else if (provider === 'claude') {
    // Claude: get conversation container (excluding sidebar)
    const conv = document.querySelector('.flex.min-h-full.w-full.overflow-x-clip > .w-full.relative.min-w-0');
    text = conv ? conv.innerText : document.body.innerText;
  } else if (provider === 'gemini') {
    // Gemini: get chat container
    const chat = document.querySelector('.conversation-container') || document.querySelector('main');
    text = chat ? chat.innerText : document.body.innerText;
  } else if (provider === 'grok') {
    // Grok: get main conversation area
    const main = document.querySelector('main') || document.querySelector('[role="main"]');
    text = main ? main.innerText : document.body.innerText;
  } else {
    text = document.body.innerText;
  }

  text = text.slice(0, 50000); // limit size

  // Generate unique ID: use URL + title hash for stable identification
  // This allows updates to same conversation without creating duplicates
  const titleHash = document.title.split('').reduce((hash, char) => {
    return ((hash << 5) - hash) + char.charCodeAt(0);
  }, 0);
  const id = `${location.href}#${titleHash}`;

  const thread = {
    id: id,
    provider,
    url: location.href,
    title: document.title,
    text,
    capturedAt: new Date().toISOString()
  };
  console.log('[conversai extension] Capturing thread:', thread);
  queueThread(thread);
}

const pendingThreads = [];
let flushTimer = null;

function queueThread(thread) {
  pendingThreads.push(thread);
  if (!flushTimer) {
    flushTimer = setTimeout(flushThreads, 100);
  }
}

function flushThreads() {
  flushTimer = null;
  const runtime = getRuntime();
  if (!runtime?.id) {
    // Runtime unavailable - likely extension context invalidated during page navigation
    // Silently drop threads as this is expected behavior
    pendingThreads.length = 0;
    return;
  }

  const threadsToSend = pendingThreads.splice(0, pendingThreads.length);
  threadsToSend.forEach(thread => {
    try {
      runtime.sendMessage({ type: "CAPTURE", thread }, () => {
        // Silently ignore lastError - expected during page navigation/context invalidation
        if (runtime.lastError) {
          // Do nothing - this is expected behavior
        }
      });
    } catch (error) {
      // Silently ignore errors - expected during extension context invalidation
    }
  });
}

// Observe DOM changes and periodically save
const observer = new MutationObserver(() => {
  clearTimeout(window.__conversaiTimer);
  window.__conversaiTimer = setTimeout(collectText, 2000);
});
observer.observe(document.body, { childList: true, subtree: true });

window.addEventListener('pagehide', () => {
  observer.disconnect();
  clearTimeout(window.__conversaiTimer);
  if (flushTimer) {
    clearTimeout(flushTimer);
    flushThreads();
  }
});

// Initial capture
collectText();
