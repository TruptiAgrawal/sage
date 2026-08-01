/**
 * background.js
 * Listens for toolbar icon clicks and sends a toggle message to the active tab.
 */
chrome.action.onClicked.addListener((tab) => {
  if (!tab.id) return;
  chrome.tabs.sendMessage(tab.id, { type: "SAGE_TOGGLE" });
});
