// Contacts page: navigate to a conversation with the entered recipient.
// Kept in an external file (rather than an inline handler) so the page can run
// under a strict script-src 'self' Content-Security-Policy.

// This file only runs when JavaScript is enabled, so drop the no-JS warning the
// template renders by default.
document.getElementById("jsWarning")?.remove();

function startChat() {
    const recipient = document.getElementById("recipientId").value.trim();
    if (recipient) {
        window.location.href = "/chat/" + encodeURIComponent(recipient);
    }
}

document.getElementById("startChatButton").addEventListener("click", startChat);
