// Contacts page: navigate to a conversation with the entered recipient.
// Kept in an external file (rather than an inline handler) so the page can run
// under a strict script-src 'self' Content-Security-Policy.
// (The no-JS warning banner is removed by js-check.js, loaded on every page.)
function startChat() {
    const recipient = document.getElementById("recipientId").value.trim();
    if (recipient) {
        window.location.href = "/chat/" + encodeURIComponent(recipient);
    }
}

document.getElementById("startChatButton").addEventListener("click", startChat);
