// Configure Markdown Parser
if (typeof marked !== "undefined") {
    marked.setOptions({
        breaks: true,
        gfm: true
    });
}

// Global Authentication & Pending State
let currentUser = null;
let pendingQuestion = null;

// DOM
const chatScroll = document.getElementById("chatScroll");
const messagesList = document.getElementById("messagesList");
const welcomeCard = document.getElementById("welcomeCard");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const clearChatBtn = document.getElementById("clearChatBtn");

const toggleTraceBtn = document.getElementById("toggleTraceBtn");
const closeTraceBtn = document.getElementById("closeTraceBtn");
const traceDrawer = document.getElementById("traceDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const traceBadge = document.getElementById("traceBadge");
const traceStepsList = document.getElementById("traceStepsList");
const traceSourcePill = document.getElementById("traceSourcePill");
const traceStepSummary = document.getElementById("traceStepSummary");
const traceTime = document.getElementById("traceTime");

const openUploadBtn = document.getElementById("openUploadBtn");
const closeUploadBtn = document.getElementById("closeUploadBtn");
const cancelUploadBtn = document.getElementById("cancelUploadBtn");
const uploadModal = document.getElementById("uploadModal");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileNameLabel = document.getElementById("fileNameLabel");
const submitUploadBtn = document.getElementById("submitUploadBtn");
const uploadStatusMessage = document.getElementById("uploadStatusMessage");
const documentList = document.getElementById("documentList");
const documentCount = document.getElementById("documentCount");
const documentsNav = document.getElementById("documentsNav");

// Auth DOM Elements
const headerLoginBtn = document.getElementById("headerLoginBtn");
const userProfile = document.getElementById("userProfile");
const profileAvatar = document.getElementById("profileAvatar");
const profileUsername = document.getElementById("profileUsername");
const profileRoleBadge = document.getElementById("profileRoleBadge");
const logoutBtn = document.getElementById("logoutBtn");

const loginModal = document.getElementById("loginModal");
const closeLoginBtn = document.getElementById("closeLoginBtn");
const cancelLoginBtn = document.getElementById("cancelLoginBtn");
const submitLoginBtn = document.getElementById("submitLoginBtn");
const loginForm = document.getElementById("loginForm");
const loginUsername = document.getElementById("loginUsername");
const loginPassword = document.getElementById("loginPassword");
const loginErrorMsg = document.getElementById("loginErrorMsg");
const fillUserDemoBtn = document.getElementById("fillUserDemoBtn");
const fillAdminDemoBtn = document.getElementById("fillAdminDemoBtn");

const SOURCE_CONFIG = {
    private_kb: { label: "Private Knowledge Base", class: "private_kb" },
    web_search: { label: "Public Web Search (Tavily)", class: "web_search" },
    web: { label: "Public Web Search (Tavily)", class: "web_search" },
    direct: { label: "Direct Assistant", class: "direct" },
    insufficient_evidence: { label: "Insufficient Evidence", class: "insufficient_evidence" },
    error: { label: "Error", class: "error" }
};

function escapeHtml(value = "") {
    if (typeof value !== "string") {
        if (value === null || value === undefined) return "";
        if (Array.isArray(value)) {
            return value
                .map((x) => typeof x === "object" && x !== null ? x.text || JSON.stringify(x) : String(x))
                .join("\n");
        }
        if (typeof value === "object") return value.text || JSON.stringify(value);
        value = String(value);
    }

    return value.replace(
        /[&<>'"]/g,
        (c) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "'": "&#39;",
            '"': "&quot;"
        }[c])
    );
}

function renderMarkdown(content = "") {
    if (typeof content !== "string") {
        content = escapeHtml(content);
    }

    if (typeof marked !== "undefined") {
        const rawHtml = marked.parse(content);

        if (typeof DOMPurify !== "undefined") {
            return DOMPurify.sanitize(rawHtml);
        }

        return rawHtml;
    }

    return escapeHtml(content)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/\n/g, "<br>");
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatScroll.scrollTop = chatScroll.scrollHeight;
    });
}

// -------------------------------------------------------------
// Authentication Functions
// -------------------------------------------------------------
function updateAuthUI(user) {
    currentUser = user;
    if (user) {
        headerLoginBtn?.classList.add("hidden");
        userProfile?.classList.remove("hidden");
        if (profileUsername) {
            const displayName = user.username.includes("@") ? user.username.split("@")[0] : user.username;
            profileUsername.textContent = displayName;
        }
        if (profileAvatar) {
            profileAvatar.textContent = (user.username[0] || "U").toUpperCase();
        }
        if (profileRoleBadge) {
            profileRoleBadge.textContent = user.role === "admin" ? "Admin" : "Employee";
            profileRoleBadge.className = `role-badge ${user.role === "admin" ? "role-admin" : "role-user"}`;
        }
        // Show Upload Documents button ONLY to admins
        if (user.role === "admin") {
            openUploadBtn?.classList.remove("hidden");
        } else {
            openUploadBtn?.classList.add("hidden");
        }
    } else {
        headerLoginBtn?.classList.remove("hidden");
        userProfile?.classList.add("hidden");
        openUploadBtn?.classList.add("hidden");
    }
}

async function checkSession() {
    try {
        const res = await fetch("/api/me");
        if (res.ok) {
            const data = await res.json();
            updateAuthUI(data);
        } else {
            updateAuthUI(null);
        }
    } catch {
        updateAuthUI(null);
    }
}

function openLoginModal(message = "") {
    loginModal?.classList.remove("hidden");
    if (loginErrorMsg) {
        if (typeof message === "string" && message.trim().length > 0) {
            loginErrorMsg.textContent = message;
            loginErrorMsg.classList.remove("hidden");
        } else {
            loginErrorMsg.textContent = "";
            loginErrorMsg.classList.add("hidden");
        }
    }
    loginUsername?.focus();
}

function closeLoginModal() {
    loginModal?.classList.add("hidden");
    if (loginErrorMsg) {
        loginErrorMsg.textContent = "";
        loginErrorMsg.classList.add("hidden");
    }
}

async function handleLogin() {
    const username = loginUsername.value.trim();
    const password = loginPassword.value;

    if (!username || !password) {
        if (loginErrorMsg) {
            loginErrorMsg.textContent = "Please enter both username and password.";
            loginErrorMsg.classList.remove("hidden");
        }
        return;
    }

    submitLoginBtn.disabled = true;
    if (loginErrorMsg) loginErrorMsg.classList.add("hidden");

    try {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Authentication failed.");
        }

        updateAuthUI(data.user);
        closeLoginModal();
        loginPassword.value = "";

        // If there was a pending question, automatically submit it now
        if (pendingQuestion) {
            const nextQuery = pendingQuestion;
            pendingQuestion = null;
            askAgent(nextQuery);
        }
    } catch (err) {
        if (loginErrorMsg) {
            loginErrorMsg.textContent = err.message;
            loginErrorMsg.classList.remove("hidden");
        }
    } finally {
        submitLoginBtn.disabled = false;
    }
}

async function handleLogout() {
    try {
        await fetch("/api/logout", { method: "POST" });
    } catch (err) {
        console.error("Logout error:", err);
    } finally {
        currentUser = null;
        pendingQuestion = null;
        updateAuthUI(null);
    }
}

// Auth Event Listeners
headerLoginBtn?.addEventListener("click", () => openLoginModal());
closeLoginBtn?.addEventListener("click", () => closeLoginModal());
cancelLoginBtn?.addEventListener("click", () => closeLoginModal());
submitLoginBtn?.addEventListener("click", handleLogin);
logoutBtn?.addEventListener("click", handleLogout);

loginForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    handleLogin();
});

fillUserDemoBtn?.addEventListener("click", () => {
    if (loginUsername) loginUsername.value = "user@novaretail.com";
    if (loginPassword) {
        loginPassword.value = "";
        loginPassword.focus();
    }
});

fillAdminDemoBtn?.addEventListener("click", () => {
    if (loginUsername) loginUsername.value = "admin@novaretail.com";
    if (loginPassword) {
        loginPassword.value = "";
        loginPassword.focus();
    }
});


function addMessage(role, content, source = "", citations = []) {
    if (welcomeCard && !welcomeCard.classList.contains("hidden")) {
        welcomeCard.classList.add("hidden");
    }

    const wrap = document.createElement("div");
    wrap.className = `message-wrap ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = role === "user" ? "R" : "AI";

    const contentBox = document.createElement("div");
    contentBox.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    if (role === "user") {
        bubble.textContent = content;
    } else {
        const prose = document.createElement("div");
        prose.className = "prose";
        prose.innerHTML = renderMarkdown(content);
        bubble.appendChild(prose);

        if (source || (citations && citations.length > 0)) {
            const meta = document.createElement("div");
            meta.className = "message-meta";

            if (source) {
                const cfg = SOURCE_CONFIG[source] || {
                    label: `Source: ${source}`,
                    class: "direct"
                };

                const badge = document.createElement("span");
                badge.className = `source-badge ${cfg.class}`;
                badge.textContent = `✓ ${cfg.label}`;
                meta.appendChild(badge);
            }

            if (citations && citations.length > 0) {
                const citeWrap = document.createElement("div");
                citeWrap.className = "citations-list";

                const title = document.createElement("span");
                title.className = "citations-title";
                title.textContent = "Sources:";
                citeWrap.appendChild(title);

                citations.forEach((c) => {
                    const tag = c.url
                        ? document.createElement("a")
                        : document.createElement("span");

                    tag.className = "citation-pill";
                    tag.innerHTML = `📄 ${escapeHtml(c.title || c.url)}`;

                    if (c.url) {
                        tag.href = c.url;
                        tag.target = "_blank";
                        tag.rel = "noopener noreferrer";
                    }

                    citeWrap.appendChild(tag);
                });

                meta.appendChild(citeWrap);
            }

            bubble.appendChild(meta);

            const actions = document.createElement("div");
            actions.className = "message-actions";
            actions.innerHTML = `
                <button type="button" title="Copy answer" aria-label="Copy answer">
                    <svg viewBox="0 0 24 24" fill="none">
                        <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.7"/>
                        <path d="M15 9V6.5A1.5 1.5 0 0 0 13.5 5H6.5A1.5 1.5 0 0 0 5 6.5v7A1.5 1.5 0 0 0 6.5 15H9" stroke="currentColor" stroke-width="1.7"/>
                    </svg>
                </button>
                <button type="button" title="Helpful" aria-label="Helpful">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M7 10v10H4V10h3Zm3 10h6.2a2 2 0 0 0 1.9-1.4l2-6A2 2 0 0 0 18.2 10H14l.6-3.1A2.5 2.5 0 0 0 12.2 4L10 10v10Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
                    </svg>
                </button>
                <button type="button" title="Not helpful" aria-label="Not helpful">
                    <svg viewBox="0 0 24 24" fill="none">
                        <path d="M7 14V4H4v10h3Zm3-10h6.2a2 2 0 0 1 1.9 1.4l2 6A2 2 0 0 1 18.2 14H14l.6 3.1a2.5 2.5 0 0 1-2.4 2.9L10 14V4Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
                    </svg>
                </button>
            `;

            actions.querySelector("button").addEventListener("click", async () => {
                try {
                    await navigator.clipboard.writeText(content);
                } catch (_) {
                    // Clipboard may be unavailable in non-secure local contexts.
                }
            });

            contentBox.appendChild(bubble);
            contentBox.appendChild(actions);
            wrap.appendChild(avatar);
            wrap.appendChild(contentBox);
            messagesList.appendChild(wrap);
            scrollToBottom();
            return;
        }
    }

    contentBox.appendChild(bubble);
    wrap.appendChild(avatar);
    wrap.appendChild(contentBox);
    messagesList.appendChild(wrap);
    scrollToBottom();
}

function showThinking() {
    const wrap = document.createElement("div");
    wrap.className = "message-wrap assistant thinking-placeholder";
    wrap.id = "thinkingMessage";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "AI";

    const contentBox = document.createElement("div");
    contentBox.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble thinking-bubble";
    bubble.innerHTML = `
        <div class="thinking-dots">
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
            <span class="thinking-dot"></span>
        </div>
        <span>Searching policy knowledge base...</span>
    `;

    contentBox.appendChild(bubble);
    wrap.appendChild(avatar);
    wrap.appendChild(contentBox);
    messagesList.appendChild(wrap);
    scrollToBottom();
}

function removeThinking() {
    document.getElementById("thinkingMessage")?.remove();
}

function updateTrace(traceItems = [], source = "—") {
    traceBadge.textContent = traceItems.length;
    traceStepSummary.textContent = `${traceItems.length} completed`;

    const cfg = SOURCE_CONFIG[source] || { label: source || "—" };
    traceSourcePill.textContent = cfg.label;

    if (!traceItems || traceItems.length === 0) {
        traceStepsList.innerHTML = `
            <div class="trace-empty">
                Ask a question to view the agentic decision path.
            </div>
        `;
        traceTime.textContent = "—";
        return;
    }

    traceStepsList.innerHTML = traceItems
        .map((step, idx) => `
            <div class="trace-step-item">
                <strong>${idx + 1}. Agent step</strong>
                ${escapeHtml(step)}
            </div>
        `)
        .join("");

    traceTime.textContent = "Completed";
}

async function askAgent(questionText) {
    const text = questionText.trim();
    if (!text) return;

    // Check if user is logged in before sending
    if (!currentUser) {
        pendingQuestion = text;
        questionInput.value = text;
        autoResizeInput();
        openLoginModal("Please sign in to ask HR policy questions.");
        return;
    }

    pendingQuestion = null;
    addMessage("user", text);
    questionInput.value = "";
    autoResizeInput();

    sendBtn.disabled = true;
    showThinking();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text })
        });

        const data = await response.json();
        removeThinking();

        if (response.status === 401) {
            // Session expired: preserve question, reset auth, prompt login
            pendingQuestion = text;
            questionInput.value = text;
            autoResizeInput();
            updateAuthUI(null);
            openLoginModal("Your session has expired. Please sign in again.");
            return;
        }

        if (response.status === 429) {
            addMessage("assistant", `**You're temporarily rate limited.** ${data.detail || "Please try again later."}`, "error");
            updateTrace(["Rate limit exceeded (429)"], "error");
            return;
        }

        if (!response.ok) {
            throw new Error(data.detail || "Request to HR Copilot failed.");
        }

        addMessage(
            "assistant",
            data.answer,
            data.source_used,
            data.citations || []
        );

        updateTrace(data.trace || [], data.source_used);
    } catch (err) {
        removeThinking();
        addMessage("assistant", `**Error:** ${err.message}`, "error");
        updateTrace(["Request execution failed"], "error");
    } finally {
        sendBtn.disabled = false;
        questionInput.focus();
    }
}

function autoResizeInput() {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 130) + "px";
}

questionInput.addEventListener("input", autoResizeInput);

questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
    }
});

chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    askAgent(questionInput.value);
});

document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        const query = chip.getAttribute("data-query");
        if (query) {
            questionInput.value = query;
            autoResizeInput();
            askAgent(query);
        }
    });
});

clearChatBtn.addEventListener("click", () => {
    messagesList.innerHTML = "";
    if (welcomeCard) welcomeCard.classList.remove("hidden");
    updateTrace([], "—");
    questionInput.focus();
});

function openTraceDrawer() {
    traceDrawer.classList.add("open");
    drawerBackdrop.classList.add("visible");
}

function closeTraceDrawer() {
    traceDrawer.classList.remove("open");
    drawerBackdrop.classList.remove("visible");
}

toggleTraceBtn.addEventListener("click", openTraceDrawer);
closeTraceBtn.addEventListener("click", closeTraceDrawer);
drawerBackdrop.addEventListener("click", closeTraceDrawer);

function openUploadModal() {
    if (!currentUser || currentUser.role !== "admin") {
        openLoginModal();
        if (loginErrorMsg) {
            loginErrorMsg.textContent = "Admin login required to upload documents.";
            loginErrorMsg.classList.remove("hidden");
        }
        return;
    }
    uploadModal.classList.remove("hidden");
    uploadStatusMessage.className = "status-msg hidden";
    uploadStatusMessage.textContent = "";
}

function closeUploadModal() {
    uploadModal.classList.add("hidden");
}

openUploadBtn?.addEventListener("click", () => openUploadModal());
closeUploadBtn?.addEventListener("click", () => closeUploadModal());
cancelUploadBtn?.addEventListener("click", () => closeUploadModal());

uploadModal.addEventListener("click", (event) => {
    if (event.target === uploadModal) closeUploadModal();
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        fileNameLabel.textContent = `Selected: ${fileInput.files[0].name}`;
    } else {
        fileNameLabel.textContent = "Click or drag & drop a file here";
    }
});

dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");

    if (event.dataTransfer.files.length > 0) {
        fileInput.files = event.dataTransfer.files;
        fileNameLabel.textContent = `Selected: ${fileInput.files[0].name}`;
    }
});

function addDocumentToSidebar(fileName) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "document-item";

    item.innerHTML = `
        <span class="file-icon">
            <svg viewBox="0 0 24 24" fill="none">
                <path d="M6 3.5h8l4 4V20.5H6V3.5Z" stroke="currentColor" stroke-width="1.7"/>
                <path d="M14 3.5v4h4" stroke="currentColor" stroke-width="1.7"/>
            </svg>
        </span>
        <span class="document-info">
            <strong>${escapeHtml(fileName)}</strong>
            <small>Private KB • Indexed</small>
        </span>
        <span class="document-menu">•••</span>
    `;

    documentList.appendChild(item);
    documentCount.textContent = documentList.querySelectorAll(".document-item").length;
}

submitUploadBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];

    if (!file) {
        uploadStatusMessage.className = "status-msg error";
        uploadStatusMessage.textContent = "Please select a document file (.pdf, .docx, .md, .txt).";
        return;
    }

    uploadStatusMessage.className = "status-msg info";
    uploadStatusMessage.textContent = "Chunking and indexing into Pinecone...";
    submitUploadBtn.disabled = true;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/ingest", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.status === 401) {
            updateAuthUI(null);
            closeUploadModal();
            openLoginModal();
            throw new Error("Session expired. Please log in as Admin.");
        }

        if (response.status === 403) {
            throw new Error("Admin access required to upload documents.");
        }

        if (response.status === 429) {
            throw new Error(data.detail || "Upload rate limit exceeded. Please wait a moment.");
        }

        if (!response.ok) {
            throw new Error(data.detail || "Indexing failed");
        }

        uploadStatusMessage.className = "status-msg success";
        uploadStatusMessage.textContent =
            `✓ Successfully indexed "${data.file}" into ${data.chunks} chunks (${data.ids_created} vector embeddings).`;

        addDocumentToSidebar(data.file || file.name);

        setTimeout(() => {
            fileInput.value = "";
            fileNameLabel.textContent = "Click or drag & drop a file here";
        }, 1200);
    } catch (err) {
        uploadStatusMessage.className = "status-msg error";
        uploadStatusMessage.textContent = `Error: ${err.message}`;
    } finally {
        submitUploadBtn.disabled = false;
    }
});

// Documents nav: visually focus the document section without requiring a new backend endpoint.
documentsNav.addEventListener("click", () => {
    documentList.scrollIntoView({ behavior: "smooth", block: "nearest" });

    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    documentsNav.classList.add("active");

    setTimeout(() => {
        document.querySelector('[data-section="chat"]').classList.add("active");
        documentsNav.classList.remove("active");
    }, 900);
});

// Escape closes overlays.
document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;

    if (traceDrawer.classList.contains("open")) {
        closeTraceDrawer();
    }

    if (!uploadModal.classList.contains("hidden")) {
        closeUploadModal();
    }

    if (!loginModal.classList.contains("hidden")) {
        closeLoginModal();
    }
});

// Keep chat as active navigation after normal interaction.
document.querySelector('[data-section="chat"]').addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    document.querySelector('[data-section="chat"]').classList.add("active");
    questionInput.focus();
});

updateTrace([], "—");
checkSession();
