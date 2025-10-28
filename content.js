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
  const { pathname } = location;

  // Skip unknown providers (e.g., regular X/Twitter pages that aren't Grok)
  if (provider === 'unknown') {
    console.log('[conversai extension] Skipping unknown provider page');
    return;
  }

  // Skip generic pages that aren't actual conversations
  if (provider === 'gemini' && (pathname === '/app' || pathname === '/app/')) {
    console.log('[conversai extension] Skipping generic Gemini app page');
    return;
  }

  // Skip ChatGPT project overview pages (but allow conversations within projects)
  // Project conversations have /c/ in the path, overview pages don't
  if (provider === 'chatgpt' && pathname.startsWith('/g/') && !pathname.includes('/c/')) {
    console.log('[conversai extension] Skipping ChatGPT project overview page');
    return;
  }

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

  // Generate unique ID: use URL only for stable identification
  // This allows updates to same conversation without creating duplicates
  // (title can change as conversation evolves, but URL stays the same)
  const id = location.href;

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
    console.log('[conversai extension] Runtime unavailable, dropping threads');
    pendingThreads.length = 0;
    return;
  }

  const threadsToSend = pendingThreads.splice(0, pendingThreads.length);
  console.log('[conversai extension] Flushing', threadsToSend.length, 'threads');
  threadsToSend.forEach(thread => {
    // Send message and retry once if service worker is asleep
    const sendWithRetry = (attempt = 1) => {
      try {
        runtime.sendMessage({ type: "CAPTURE", thread }, (response) => {
          if (runtime.lastError) {
            const error = runtime.lastError.message;
            console.error('[conversai extension] Error sending message (attempt ' + attempt + '):', error);
            // If service worker was inactive, Chrome will wake it up, so retry once
            if (attempt === 1 && error.includes('Receiving end does not exist')) {
              console.log('[conversai extension] Retrying after service worker wake-up...');
              setTimeout(() => sendWithRetry(2), 100);
            }
          } else {
            console.log('[conversai extension] Message sent successfully', response);
          }
        });
      } catch (error) {
        console.error('[conversai extension] Exception sending message:', error);
      }
    };
    sendWithRetry();
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
