// background.js
import { saveThread, searchThreads } from './db.js';

console.log('[Background] Script loaded');

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  console.log('[Background] Received message:', msg, 'from:', sender);
  if (msg.type === "CAPTURE" && msg.thread) {
    console.log('[Background] Saving thread:', msg.thread);
    saveThread(msg.thread).then(() => {
      console.log('[Background] Thread saved successfully');
      sendResponse({ success: true });
    }).catch(err => {
      console.error('[Background] Error saving thread:', err);
      sendResponse({ success: false, error: err.message });
    });
    return true; // Keep channel open for async response
  }
});

// Allow your website to query local data
chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  console.log('[Background] External message from:', sender.origin);
  const origin = new URL(sender.origin || "").origin;
  console.log('[Background] Parsed origin:', origin);
  const isLocalhost = origin.startsWith("http://localhost:");
  const isAllowedDomain = origin === "https://conversai.us";
  if (!isLocalhost && !isAllowedDomain) {
    console.log('[Background] Origin not allowed, rejecting');
    return;
  }

  if (msg.action === "SEARCH") {
    searchThreads(msg.query).then(results => sendResponse({ results }));
    return true; // asynchronous
  }

  if (msg.action === "CLEAR") {
    chrome.storage.local.clear().then(() => {
      console.log('[Background] Storage cleared');
      sendResponse({ success: true });
    });
    return true; // asynchronous
  }
});
