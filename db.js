// db.js - Using chrome.storage instead of IndexedDB
export async function saveThread(thread) {
  console.log('[DB] saveThread called with:', thread);
  try {
    // Get existing threads
    const result = await chrome.storage.local.get(['threads']);
    const threads = result.threads || {};

    // Save thread with URL as key
    threads[thread.id] = thread;

    // Store back
    await chrome.storage.local.set({ threads });
    console.log('[DB] Thread saved successfully to chrome.storage');
  } catch (error) {
    console.error('[DB] Error saving thread:', error);
    throw error;
  }
}

export async function searchThreads(query) {
  console.log('[DB] searchThreads called with query:', query);
  try {
    const result = await chrome.storage.local.get(['threads']);
    const threads = result.threads || {};
    const results = [];

    // Split query into words for multi-word search
    const queryWords = query.toLowerCase().trim().split(/\s+/);

    for (const [id, thread] of Object.entries(threads)) {
      const titleLower = thread.title.toLowerCase();
      const textLower = thread.text.toLowerCase();

      // Check if all query words are present in title or text
      const allWordsInTitle = queryWords.every(word => titleLower.includes(word));
      const allWordsInText = queryWords.every(word => textLower.includes(word));

      if (allWordsInTitle || allWordsInText) {
        results.push({
          ...thread,
          // Add relevance score: title matches score higher
          relevance: allWordsInTitle ? 2 : 1
        });
      }
    }

    // Sort by relevance (title matches first), then by capture time
    results.sort((a, b) => {
      if (a.relevance !== b.relevance) {
        return b.relevance - a.relevance;
      }
      return new Date(b.capturedAt) - new Date(a.capturedAt);
    });

    console.log('[DB] Search found', results.length, 'results');
    return results;
  } catch (error) {
    console.error('[DB] Error searching threads:', error);
    throw error;
  }
}
