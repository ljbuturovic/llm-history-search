// background.js
importScripts("db.js");

console.log('[Background] Script loaded');

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  console.log('[Background] Received message:', msg);
  if (msg.type === "CAPTURE" && msg.thread) {
    console.log('[Background] Saving thread:', msg.thread);
    saveThread(msg.thread).then(() => {
      console.log('[Background] Thread saved successfully');
    }).catch(err => {
      console.error('[Background] Error saving thread:', err);
    });
  }
});

// Allow your website to query local data
chrome.runtime.onMessageExternal.addListener((msg, sender, sendResponse) => {
  console.log('[Background] External message from:', sender.origin);
  const origin = new URL(sender.origin || "").origin;
  console.log('[Background] Parsed origin:', origin);
  if (origin !== "http://localhost:8000" && origin !== "https://clinicalpersona.com") {
    console.log('[Background] Origin not allowed, rejecting');
    return;
  }

  if (msg.action === "SEARCH") {
    searchThreads(msg.query).then(results => sendResponse({ results }));
    return true; // asynchronous
  }
});
