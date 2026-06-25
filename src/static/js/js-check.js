// Removes the no-JS warning banner once JavaScript runs. Used on pages (like the
// login page) that have no other script of their own. Kept external so it works
// under the strict script-src 'self' Content-Security-Policy.
document.getElementById("jsWarning")?.remove();
