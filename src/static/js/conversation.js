window.startChat = function(userId, recipientId) {
    const ws = new WebSocket("ws://" + window.location.host + "/chat/ws/" + userId);
    const recipient = recipientId;
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('messageText');
    const sendButton = document.getElementById('sendButton');
    const statusDiv = document.getElementById('status');

    let myKeyPair = null;
    let sharedSecret = null;
    let isSecure = false;

    function logStatus(message, isError = false) {
        const statusElement = document.createElement('div');
        statusElement.textContent = message;
        statusElement.className = isError ? 'error-message' : 'system-message';
        statusDiv.appendChild(statusElement);
    }

    // 1. Key Generation
    async function generateKeys() {
        logStatus("Generating your encryption keys...");
        try {
            myKeyPair = await window.crypto.subtle.generateKey(
                { name: "ECDH", namedCurve: "P-256" },
                true,
                ["deriveKey"]
            );
            logStatus("Key generation complete.");
            return myKeyPair;
        } catch (error) {
            logStatus("Error generating keys. This browser may not support Web Crypto.", true);
            console.error(error);
        }
    }

    // 2. Key Exchange
    async function sendPublicKey(isReply = false) {
        const publicKey = await window.crypto.subtle.exportKey("jwk", myKeyPair.publicKey);
        logStatus("Sending public key to " + recipient);
        ws.send(JSON.stringify({
            target_user: recipient,
            type: 'key_exchange',
            publicKey: publicKey,
            is_reply: isReply
        }));
    }

    // 3. Shared Secret Derivation
    async function deriveSharedSecret(theirPublicKeyJwk) {
        logStatus("Received public key. Deriving shared secret...");
        try {
            const theirPublicKey = await window.crypto.subtle.importKey(
                "jwk",
                theirPublicKeyJwk,
                { name: "ECDH", namedCurve: "P-256" },
                true,
                []
            );

            const ecdhSecret = await window.crypto.subtle.deriveKey(
                { name: "ECDH", public: theirPublicKey },
                myKeyPair.privateKey,
                { name: "AES-GCM", length: 256 },
                true,
                ["encrypt", "decrypt"]
            );
            
            sharedSecret = ecdhSecret;
            isSecure = true;
            logStatus("Secure connection established. You can now chat safely.");
            messageInput.disabled = false;
            sendButton.disabled = false;
            statusDiv.innerHTML = ''; // Clear status messages
        } catch (error) {
            logStatus("Error deriving shared secret. Communication will not be secure.", true);
            console.error(error);
        }
    }

    // 4. Encryption / Decryption
    async function encryptMessage(message) {
        if (!sharedSecret) {
            logStatus("Cannot send message: no shared secret.", true);
            return;
        }
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const encodedMessage = new TextEncoder().encode(message);

        const encrypted = await window.crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            sharedSecret,
            encodedMessage
        );
        
        return {
            iv: Array.from(iv),
            ciphertext: Array.from(new Uint8Array(encrypted))
        };
    }

    async function decryptMessage(encryptedData) {
        if (!sharedSecret) {
            logStatus("Cannot decrypt message: no shared secret.", true);
            return;
        }
        const { iv, ciphertext } = encryptedData;
        const ivArray = new Uint8Array(iv);
        const ciphertextArray = new Uint8Array(ciphertext);

        try {
            const decrypted = await window.crypto.subtle.decrypt(
                { name: "AES-GCM", iv: ivArray },
                sharedSecret,
                ciphertextArray
            );
            return new TextDecoder().decode(decrypted);
        } catch (e) {
            logStatus("Failed to decrypt message. It may be corrupted or tampered with.", true);
            console.error(e);
            return "DECRYPTION FAILED";
        }
    }

    // WebSocket Event Handlers
    ws.onopen = async () => {
        logStatus("Connected to the server.");
        await generateKeys();
        if (myKeyPair) {
            await sendPublicKey(false);
        }
    };

    ws.onmessage = async function(event) {
        const data = JSON.parse(event.data);

        // Case 1: Received a public key
        if (data.type === 'key_exchange' && data.publicKey && data.sender === recipient) {
            await deriveSharedSecret(data.publicKey);
            if (!data.is_reply) {
                await sendPublicKey(true);
            }
        }
        
        // Case 2: Received an encrypted message
        else if (data.type === 'encrypted_text' && data.sender === recipient) {
            const decryptedMessage = await decryptMessage(data.content);
            const messageElement = document.createElement('div');
            messageElement.innerText = `[${data.sender}]: ${decryptedMessage}`;
            messagesDiv.appendChild(messageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Case 3: A message you sent was echoed back
        else if (data.recipient === recipient && data.type === 'encrypted_text') {
             const decryptedMessage = await decryptMessage(data.content);
             const messageElement = document.createElement('div');
             messageElement.innerText = `[You -> ${data.recipient}]: ${decryptedMessage}`;
             messagesDiv.appendChild(messageElement);
             messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    };

    ws.onclose = () => {
        logStatus("Disconnected from server. Refresh to reconnect.", true);
        messageInput.disabled = true;
        sendButton.disabled = true;
    };

    ws.onerror = (error) => {
        logStatus("WebSocket error occurred.", true);
        console.error("WebSocket Error:", error);
    };
    
    // Sending Messages
    async function sendMessage() {
        const messageText = messageInput.value;
        if (messageText.trim() === "" || !isSecure) {
            return;
        }

        const encryptedContent = await encryptMessage(messageText);

        ws.send(JSON.stringify({
            target_user: recipient,
            type: 'encrypted_text',
            content: encryptedContent
        }));
        messageInput.value = '';
    }
    
    // Attach event listeners
    sendButton.addEventListener('click', sendMessage);
    
    messageInput.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
};
