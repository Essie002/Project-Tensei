// ===== PROJECT TENSEI — PROTOTYPE ENGINE =====
// Simulates the EKS CrashLoopBackOff scenario end-to-end

// ===== STATE =====
let sessionSeconds = 0;
let scenarioStep = 0;
let timerInterval = null;

// ===== DOM REFS =====
const entryScreen = document.getElementById('entry-screen');
const workspaceScreen = document.getElementById('workspace-screen');
const enterBtn = document.getElementById('enter-workspace-btn');
const chatMessages = document.getElementById('chat-messages');
const quickResponses = document.getElementById('quick-responses');
const trailEntries = document.getElementById('trail-entries');
const trailCount = document.getElementById('trail-count');
const sessionTimer = document.getElementById('session-timer');
const nodeGrid = document.getElementById('node-grid');
const logStream = document.getElementById('log-stream');
const topologyDiagram = document.getElementById('topology-diagram');
const engineerPanel = document.getElementById('engineer-panel');
const engineerAvatar = document.getElementById('engineer-avatar');
const handoverModal = document.getElementById('handover-modal');
const closeHandover = document.getElementById('close-handover');
const contextTabs = document.querySelectorAll('.tab');
const aiStatus = document.getElementById('ai-status');

// ===== ENTRY POINT =====
enterBtn.addEventListener('click', () => {
    entryScreen.classList.remove('active');
    workspaceScreen.classList.add('active');
    startSession();
});

closeHandover.addEventListener('click', () => {
    handoverModal.classList.add('hidden');
});

// Tab switching
contextTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        contextTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.querySelectorAll('.context-view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${tab.dataset.tab}`).classList.add('active');
    });
});

// ===== SESSION START =====
function startSession() {
    timerInterval = setInterval(() => {
        sessionSeconds++;
        const min = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
        const sec = String(sessionSeconds % 60).padStart(2, '0');
        sessionTimer.textContent = `${min}:${sec}`;
    }, 1000);

    initClusterView();
    initLogs();
    initTopology();
    runScenario();
}

// ===== CLUSTER VIEW =====
function initClusterView() {
    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'critical', label: 'CrashLoop' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'warning', label: 'High Mem' },
        { name: 'node-3a', status: 'critical', label: 'CrashLoop' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'critical', label: 'CrashLoop' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');
}

// ===== LOGS VIEW =====
function initLogs() {
    const initialLogs = [
        { time: '10:41:02', level: 'error', pod: 'api-server-7d4f8', msg: 'Back-off restarting failed container' },
        { time: '10:41:03', level: 'error', pod: 'api-server-7d4f8', msg: 'ImagePullBackOff: failed to pull image "123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest"' },
        { time: '10:41:05', level: 'warn', pod: 'worker-bf892', msg: 'Liveness probe failed: connection refused' },
        { time: '10:41:08', level: 'error', pod: 'api-server-a3c21', msg: 'CrashLoopBackOff: back-off 5m0s restarting failed container' },
    ];

    logStream.innerHTML = initialLogs.map(l => formatLog(l)).join('');

    // Start streaming new logs every 2-4 seconds
    startLogStreaming();
}

const streamingLogs = [
    { level: 'info', pod: 'scheduler', msg: 'Successfully assigned default/api-server-7d4f8 to node-1b' },
    { level: 'error', pod: 'api-server-7d4f8', msg: 'Error: ErrImagePull — 403 Forbidden' },
    { level: 'error', pod: 'worker-bf892', msg: 'ImagePullBackOff: authorization failed for ECR registry' },
    { level: 'warn', pod: 'api-server-a3c21', msg: 'Container runtime: pull access denied, requires IAM ECR permissions' },
    { level: 'error', pod: 'api-server-7d4f8', msg: 'Back-off restarting failed container (restart count: 48)' },
    { level: 'info', pod: 'kubelet', msg: 'Node node-1b: memory pressure threshold exceeded' },
    { level: 'error', pod: 'api-server-a3c21', msg: 'CrashLoopBackOff: back-off 5m0s restarting failed container' },
    { level: 'warn', pod: 'worker-bf892', msg: 'Readiness probe failed: HTTP probe failed with statuscode: 503' },
    { level: 'error', pod: 'api-server-7d4f8', msg: 'Error: ImagePullBackOff — back-off 2m40s pulling image' },
    { level: 'info', pod: 'kubelet', msg: 'Pulling image "123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest"' },
    { level: 'error', pod: 'api-server-7d4f8', msg: 'Failed to pull image: rpc error: code = Unknown desc = 403 Forbidden' },
    { level: 'warn', pod: 'api-server-a3c21', msg: 'Container api-server exceeded memory limit (512Mi)' },
    { level: 'error', pod: 'worker-bf892', msg: 'CrashLoopBackOff: back-off 1m20s restarting failed container' },
    { level: 'info', pod: 'endpoint-ctrl', msg: 'Endpoints api-service updated: 0 ready, 3 not ready' },
    { level: 'error', pod: 'api-server-7d4f8', msg: 'Back-off restarting failed container (restart count: 49)' },
    { level: 'warn', pod: 'kubelet', msg: 'Node node-3a: pod eviction threshold reached' },
    { level: 'error', pod: 'api-server-a3c21', msg: 'Error: ErrImagePull — failed to authorize: 403 Forbidden' },
    { level: 'info', pod: 'scheduler', msg: 'Preempting pod default/api-server-a3c21 on node-3a' },
];

let logStreamIndex = 0;
let logStreamInterval = null;

function startLogStreaming() {
    logStreamInterval = setInterval(() => {
        const log = streamingLogs[logStreamIndex % streamingLogs.length];
        const now = new Date();
        const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;

        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = formatLog({ ...log, time });

        logStream.appendChild(entry);
        logStream.scrollTop = logStream.scrollHeight;

        // Keep max 30 entries visible
        while (logStream.children.length > 30) {
            logStream.removeChild(logStream.firstChild);
        }

        logStreamIndex++;
    }, 2000 + Math.random() * 2000); // Random 2-4 second interval
}

function stopLogStreaming() {
    if (logStreamInterval) {
        clearInterval(logStreamInterval);
        logStreamInterval = null;
    }
}

function formatLog(l) {
    return `<span class="timestamp">[${l.time}]</span> <span class="level-${l.level}">${l.level.toUpperCase()}</span> <span class="pod-name">${l.pod}</span> ${l.msg}`;
}

// ===== TOPOLOGY VIEW =====
function initTopology() {
    topologyDiagram.innerHTML = `
        <div class="topo-node ok">
            <div class="topo-label">Application Load Balancer</div>
            <div class="topo-sub">Healthy — forwarding traffic</div>
        </div>
        <div class="topo-arrow">↓</div>
        <div class="topo-node error">
            <div class="topo-label">EKS Pods (api-server)</div>
            <div class="topo-sub">CrashLoopBackOff — ImagePullBackOff</div>
        </div>
        <div class="topo-arrow">↓ image pull</div>
        <div class="topo-node warning">
            <div class="topo-label">Amazon ECR</div>
            <div class="topo-sub">403 Forbidden — IAM permission denied</div>
        </div>
        <div class="topo-arrow">↓ auth</div>
        <div class="topo-node warning">
            <div class="topo-label">IAM Node Role</div>
            <div class="topo-sub">Missing: ecr:GetDownloadUrlForLayer, ecr:BatchGetImage</div>
        </div>
    `;
}

// ===== SCENARIO ENGINE =====
const scenario = [
    // Step 0: AI greets with context
    {
        delay: 1000,
        action: 'ai_message',
        text: `Hi — I've been watching your cluster for the past 12 minutes. Here's what I see:\n\n• <span class="highlight">47 pod restarts</span> across 3 pods in <code>prod-east-1</code>\n• All failing with <code>ImagePullBackOff</code> errors\n• Pattern started at 10:29 after a deployment update\n\nIs this what brought you here today?`,
        trail: { text: 'AI detected 47 pod restarts — ImagePullBackOff pattern', actor: 'AI Agent' }
    },
    // Step 1: Quick response options
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, that's exactly it", id: 'confirm' },
            { text: "Tell me more about the errors", id: 'more' },
            { text: "It's something else", id: 'other' }
        ]
    },
    // Step 2: Customer confirms (triggered by quick response)
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'confirm',
        customerText: "Yes, that's my issue. My production app is down.",
        trail: { text: 'Customer confirmed: production app affected', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 3: AI investigates
    {
        delay: 1500,
        action: 'ai_typing'
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `Got it. Let me dig deeper. I'm checking three things simultaneously:\n\n1. 🔍 ECR repository permissions\n2. 🔍 Image tag existence in the registry\n3. 🔍 Node IAM role configuration\n\nYou can watch the results stream into the Context Panel on the right.`,
        trail: { text: 'AI running parallel checks: ECR permissions, image tag, IAM role', actor: 'AI Agent' }
    },
    // Step 4: First finding
    {
        delay: 3000,
        action: 'ai_typing'
    },
    {
        delay: 2000,
        action: 'ai_message',
        text: `<span class="highlight">Found it.</span> Your node IAM role (<code>eks-node-role-prod</code>) is missing ECR pull permissions for the <code>api-server</code> repository.\n\nSpecifically, it's missing:\n• <code>ecr:GetDownloadUrlForLayer</code>\n• <code>ecr:BatchGetImage</code>\n• <code>ecr:GetAuthorizationToken</code>\n\nThis is why every pod restart fails — the nodes can't pull the container image. Would you like me to fix this?`,
        trail: { text: 'ROOT CAUSE: Node IAM role missing ECR pull permissions', actor: 'AI Agent' }
    },
    // Step 5: Quick response for fix
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, fix it", id: 'fix' },
            { text: "Show me what you'll change first", id: 'show' },
            { text: "I'll fix it manually", id: 'manual' }
        ]
    },
    // Step 6: Customer approves fix (branching handled in handleQuickResponse)
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'fix',
        customerText: "Yes, fix it please.",
        trail: { text: 'Customer approved: apply ECR permission fix', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 7: AI applies fix
    {
        delay: 1500,
        action: 'ai_typing'
    },
    {
        delay: 1000,
        action: 'update_context',
        contextFn: 'showECRFixApplied'
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `Done. ✅ I've attached the <code>AmazonEC2ContainerRegistryReadOnly</code> policy to your node role.\n\nPods should start pulling the image within the next 30–60 seconds. I'm monitoring...\n\n<em>However</em> — I've noticed something else. There may be a <strong>NetworkPolicy</strong> egress rule that could also block image pulls from the ECR endpoint. My confidence on this one is only <span class="highlight">45%</span> — I'd like to bring in a networking specialist to verify.\n\nWould you like me to connect you with someone?`,
        trail: { text: 'ECR permissions fixed ✅ — Secondary issue: NetworkPolicy (45% confidence)', actor: 'AI Agent' }
    },
    // Step 8: Consent for escalation
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, bring someone in", id: 'escalate' },
            { text: "Let's wait and see if the fix works first", id: 'wait' }
        ]
    },
    // Step 9: Customer consents to escalation
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'escalate',
        customerText: "Yes, bring them in. I want to make sure this is fully resolved.",
        trail: { text: 'Customer consented to specialist escalation', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 10: AI initiates handover
    {
        delay: 1000,
        action: 'ai_message',
        text: `Connecting you with <strong>Sarah K.</strong>, a Networking & VPC Specialist. She'll have the full context of everything we've done together — no need to re-explain anything.\n\nShe's reviewing the investigation now...`,
        trail: { text: 'Escalation triggered — connecting Sarah K. (Networking Specialist)', actor: 'AI Agent' }
    },
    // Step 11: Show handover package (brief flash)
    {
        delay: 1500,
        action: 'show_handover'
    },
    // Step 12: Engineer connecting state
    {
        delay: 2000,
        action: 'engineer_connecting'
    },
    // Step 13: Engineer joins
    {
        delay: 4000,
        action: 'engineer_joined',
        trail: { text: 'Sarah K. joined the workspace — full context loaded', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 14: Engineer first message
    {
        delay: 2000,
        action: 'engineer_message',
        text: `Hi! I can see the AI already identified and fixed the ECR permission issue — nice catch. Let me look at the NetworkPolicy angle. I'm checking your egress rules now.`
    },
    // Step 15: Engineer finding
    {
        delay: 3500,
        action: 'engineer_message',
        text: `Found it. You have a NetworkPolicy that restricts egress to specific CIDR blocks, but it doesn't include the ECR VPC endpoint range. Even with IAM permissions fixed, the pod network can't reach ECR.\n\nI'd recommend adding the ECR VPC endpoint to your egress allowlist. Want me to apply that?`,
        trail: { text: 'Sarah confirmed: NetworkPolicy blocking ECR VPC endpoint egress', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 16: Final quick options
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, apply it", id: 'final_fix' },
            { text: "Show me the YAML change", id: 'show_yaml' }
        ]
    },
    // Step 17: Resolution
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'final_fix',
        customerText: "Yes, let's apply it."
    },
    {
        delay: 2000,
        action: 'engineer_message',
        text: `Applied. ✅ Your pods should be fully healthy within a minute. I'll stay here until we confirm they're stable.`
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `Confirming: all 3 affected pods are now in <span class="highlight">Running</span> state. No more CrashLoopBackOff events. Your application is back online. 🎉\n\n<strong>Summary of what we did:</strong>\n1. ✅ Fixed IAM ECR permissions (node role)\n2. ✅ Fixed NetworkPolicy egress rule (VPC endpoint)\n\nIs there anything else I can help with?`,
        trail: { text: 'RESOLVED — All pods healthy. Application online.', actor: 'AI Agent' }
    },
    // Step 18: Update cluster view
    {
        delay: 1000,
        action: 'fix_cluster'
    }
];

// ===== SCENARIO RUNNER =====
let currentScenarioIndex = 0;

function runScenario() {
    processNextStep();
}

function processNextStep() {
    if (currentScenarioIndex >= scenario.length) return;

    const step = scenario[currentScenarioIndex];

    if (step.action === 'await_customer') {
        // Will be triggered by quick response click
        return;
    }

    setTimeout(() => {
        executeStep(step);
        currentScenarioIndex++;
        processNextStep();
    }, step.delay);
}

function executeStep(step) {
    switch (step.action) {
        case 'ai_message':
            removeTypingIndicator();
            addMessage('ai', 'AI Agent', step.text);
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'ai_typing':
            showTypingIndicator();
            break;

        case 'customer_message':
            addMessage('customer', 'You', step.text);
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'quick_options':
            showQuickOptions(step.options);
            break;

        case 'show_handover':
            handoverModal.classList.remove('hidden');
            setTimeout(() => handoverModal.classList.add('hidden'), 4000);
            break;

        case 'engineer_connecting':
            // Reveal the engineer panel and expand the grid
            document.querySelector('.workspace-body').classList.add('with-engineer');
            document.getElementById('resize-handle-2').classList.add('visible');
            engineerPanel.classList.add('visible');
            showEngineerState('connecting');
            aiStatus.textContent = 'Handing over...';
            break;

        case 'engineer_joined':
            showEngineerState('active');
            engineerAvatar.classList.remove('hidden');
            aiStatus.textContent = 'Supporting';
            document.getElementById('engineer-status').textContent = '● Online';
            document.getElementById('engineer-status').style.color = 'var(--accent-green)';
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'engineer_message':
            addEngineerMessage(step.text);
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'fix_cluster':
            fixClusterView();
            break;

        case 'update_context':
            if (step.contextFn === 'showECRFixApplied') showECRFixApplied();
            if (step.contextFn === 'showPartialRecovery') showPartialRecovery();
            break;
    }
}

// ===== MESSAGE HELPERS =====
function addMessage(type, sender, html) {
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `
        <div class="message-avatar ${type}">${type === 'ai' ? 'AI' : type === 'customer' ? 'Y' : '⚡'}</div>
        <div class="message-body">
            <div class="message-sender">${sender}</div>
            <div class="message-text">${html}</div>
        </div>
    `;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'message typing-msg';
    typing.innerHTML = `
        <div class="message-avatar ai">AI</div>
        <div class="message-body">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typing = chatMessages.querySelector('.typing-msg');
    if (typing) typing.remove();
}

function showQuickOptions(options) {
    quickResponses.innerHTML = options.map(o =>
        `<button class="quick-btn" data-id="${o.id}">${o.text}</button>`
    ).join('');

    quickResponses.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => handleQuickResponse(btn.dataset.id, btn.textContent));
    });
}

function handleQuickResponse(id, text) {
    quickResponses.innerHTML = '';

    // Add customer message
    addMessage('customer', 'You', text);

    // Handle branching for specific options
    if (id === 'show') {
        // Customer wants to see what will change before approving
        addTrailEntry({ text: 'Customer requested: show proposed changes', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => showTypingIndicator(), 500);
        setTimeout(() => {
            removeTypingIndicator();
            addMessage('ai', 'AI Agent', `Here's what I'll change on your node IAM role <code>eks-node-role-prod</code>:\n\n<strong>Action:</strong> Attach policy <code>AmazonEC2ContainerRegistryReadOnly</code>\n\n<strong>This adds:</strong>\n• <code>ecr:GetDownloadUrlForLayer</code>\n• <code>ecr:BatchGetImage</code>\n• <code>ecr:GetAuthorizationToken</code>\n• <code>ecr:BatchCheckLayerAvailability</code>\n• <code>ecr:DescribeRepositories</code>\n\n<strong>Scope:</strong> Read-only access to all ECR repositories in this account. No write/delete permissions.\n\nShall I apply this?`);
            showQuickOptions([
                { text: "Yes, apply it", id: 'fix' },
                { text: "No, I'll do it manually", id: 'manual' }
            ]);
        }, 2000);
        return;
    }

    if (id === 'manual') {
        addTrailEntry({ text: 'Customer chose: manual fix', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem. Here's what you need to do:\n\n1. Go to <strong>IAM → Roles → eks-node-role-prod</strong>\n2. Attach the managed policy <code>AmazonEC2ContainerRegistryReadOnly</code>\n3. Wait 30–60 seconds for pods to retry the image pull\n\nI'll keep monitoring. Let me know once you've applied it and I'll verify the pods recover.\n\nIn the meantime — I've noticed a potential secondary issue with a NetworkPolicy egress rule. My confidence is only <span class="highlight">45%</span> on this one. Want me to bring in a networking specialist to verify?`);
            addTrailEntry({ text: 'AI provided manual fix instructions — monitoring for recovery', actor: 'AI Agent' });
            // Skip ahead to the escalation options
            showQuickOptions([
                { text: "Yes, bring someone in", id: 'escalate' },
                { text: "Let's wait and see first", id: 'wait' }
            ]);
            // Set scenario index to the escalation await step
            currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'escalate');
        }, 2000);
        return;
    }

    if (id === 'more') {
        addTrailEntry({ text: 'Customer requested more details on errors', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => showTypingIndicator(), 500);
        setTimeout(() => {
            removeTypingIndicator();
            addMessage('ai', 'AI Agent', `Here's the breakdown:\n\n• <strong>3 pods affected:</strong> <code>api-server-7d4f8</code>, <code>api-server-a3c21</code>, <code>worker-bf892</code>\n• <strong>Error pattern:</strong> All failing with <code>ImagePullBackOff</code> → the node can't download the container image from ECR\n• <strong>Root cause signal:</strong> Logs show <code>403 Forbidden</code> when pulling from your ECR registry\n• <strong>Timeline:</strong> Started 12 min ago, coincides with a deployment at 10:29\n\nThis looks like a permissions issue — the nodes lost the ability to pull images. Want me to dig into the IAM configuration?`);
            showQuickOptions([
                { text: "Yes, investigate", id: 'confirm' },
                { text: "That's my issue, fix it", id: 'confirm' }
            ]);
        }, 2000);
        return;
    }

    if (id === 'other') {
        addTrailEntry({ text: 'Customer indicated a different issue', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `Got it — tell me more about what you're experiencing and I'll adjust my investigation.`);
        }, 1000);
        return;
    }

    if (id === 'wait') {
        addTrailEntry({ text: 'Customer chose to wait before escalating', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `Understood. I'll keep monitoring the pods. If the issue persists after the permission fix takes effect, I'll flag it.`);
        }, 1000);
        setTimeout(() => {
            // Sync: update context panel to show partial recovery
            showPartialRecovery();
            addMessage('ai', 'AI Agent', `Update: 2 out of 3 pods are now pulling images successfully ✅ — but <code>api-server-a3c21</code> on <code>node-3a</code> is still failing with a <strong>network timeout</strong> trying to reach the ECR endpoint.\n\nYou can see it in the Logs panel — the error is <code>dial tcp 10.0.1.45:443 — connection timed out</code>. This is consistent with a NetworkPolicy blocking egress.\n\nI'd recommend bringing in a networking specialist. Want me to connect you?`);
            addTrailEntry({ text: 'Partial recovery — 2/3 pods healthy. api-server-a3c21 blocked by NetworkPolicy.', actor: 'AI Agent' });
            showQuickOptions([
                { text: "Yes, bring someone in", id: 'escalate' },
                { text: "I'll investigate myself", id: 'manual_end' }
            ]);
        }, 4000);
        // Set scenario index to the escalation await step
        currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'escalate');
        return;
    }

    // Default: advance the scenario normally
    const awaitStep = scenario[currentScenarioIndex];
    if (awaitStep && awaitStep.action === 'await_customer') {
        if (awaitStep.trail) addTrailEntry(awaitStep.trail);
        currentScenarioIndex++;
        processNextStep();
    }
}

// ===== ENGINEER HELPERS =====
function showEngineerState(state) {
    document.querySelectorAll('.engineer-state').forEach(s => s.classList.add('hidden'));
    document.getElementById(`eng-state-${state}`).classList.remove('hidden');
}

function addEngineerMessage(text) {
    const chat = document.getElementById('engineer-chat');
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `
        <div class="message-avatar" style="background: var(--accent-green); color: #fff; width:24px; height:24px; font-size:0.6rem;">SK</div>
        <div class="message-body">
            <div class="message-sender">Sarah K.</div>
            <div class="message-text">${text}</div>
        </div>
    `;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

// ===== TRAIL HELPERS =====
let trailCountNum = 0;
function addTrailEntry(entry) {
    trailCountNum++;
    trailCount.textContent = `${trailCountNum} events`;

    const time = new Date();
    const timeStr = `${String(time.getHours()).padStart(2,'0')}:${String(time.getMinutes()).padStart(2,'0')}`;

    const el = document.createElement('div');
    el.className = 'trail-entry';
    el.innerHTML = `
        <div class="trail-entry-time">${timeStr}</div>
        <div class="trail-entry-text">${entry.text}</div>
        <div class="trail-entry-actor ${entry.actorClass || ''}">${entry.actor}</div>
    `;
    trailEntries.appendChild(el);
    trailEntries.scrollLeft = trailEntries.scrollWidth;
}

// ===== CONTEXT PANEL SYNC FUNCTIONS =====
// Update cluster to show partial recovery (2 healthy, 1 still failing)
function showPartialRecovery() {
    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'healthy', label: 'Recovered' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'healthy', label: 'Recovered' },
        { name: 'node-3a', status: 'critical', label: 'CrashLoop' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'healthy', label: 'Healthy' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');

    document.getElementById('restart-count').textContent = '3';
    document.getElementById('restart-count').className = 'stat-value warning';
    document.querySelector('.cluster-status').textContent = '● Degraded';
    document.querySelector('.cluster-status').style.color = 'var(--accent-yellow)';
    document.querySelector('.cluster-status').style.background = 'rgba(255,193,7,0.15)';

    // Switch logs to show partial recovery
    switchToPartialRecoveryLogs();
}

// Switch log stream to show partial recovery state
function switchToPartialRecoveryLogs() {
    stopLogStreaming();

    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;

    // Add recovery + remaining failure logs
    const recoveryLogs = [
        { time, level: 'info', pod: 'api-server-7d4f8', msg: 'Successfully pulled image — container starting' },
        { time, level: 'info', pod: 'worker-bf892', msg: 'Successfully pulled image — container starting' },
        { time, level: 'error', pod: 'api-server-a3c21', msg: 'ImagePullBackOff: dial tcp 10.0.1.45:443 — connection timed out (NetworkPolicy?)' },
    ];
    recoveryLogs.forEach(l => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = formatLog(l);
        logStream.appendChild(entry);
    });
    logStream.scrollTop = logStream.scrollHeight;

    // Start streaming only the failing pod logs
    logStreamInterval = setInterval(() => {
        const now2 = new Date();
        const t = `${String(now2.getHours()).padStart(2,'0')}:${String(now2.getMinutes()).padStart(2,'0')}:${String(now2.getSeconds()).padStart(2,'0')}`;
        const failingLogs = [
            { time: t, level: 'error', pod: 'api-server-a3c21', msg: 'ImagePullBackOff: dial tcp 10.0.1.45:443 — i/o timeout' },
            { time: t, level: 'warn', pod: 'api-server-a3c21', msg: 'NetworkPolicy egress: packet dropped to 10.0.1.45:443 (ECR endpoint)' },
            { time: t, level: 'error', pod: 'api-server-a3c21', msg: 'Back-off restarting failed container — network egress blocked' },
        ];
        const log = failingLogs[Math.floor(Math.random() * failingLogs.length)];
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = formatLog(log);
        logStream.appendChild(entry);
        logStream.scrollTop = logStream.scrollHeight;
        while (logStream.children.length > 30) {
            logStream.removeChild(logStream.firstChild);
        }
    }, 3000);
}

// Update cluster after AI applies the ECR fix (before escalation question)
function showECRFixApplied() {
    // Update restart count to show it's decreasing
    document.getElementById('restart-count').textContent = '12';
    document.getElementById('restart-count').className = 'stat-value warning';

    // Add a success log entry
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = formatLog({ time, level: 'info', pod: 'iam-watcher', msg: 'Policy AmazonEC2ContainerRegistryReadOnly attached to role eks-node-role-prod' });
    logStream.appendChild(entry);
    logStream.scrollTop = logStream.scrollHeight;

    // Update topology to show ECR is now accessible
    topologyDiagram.innerHTML = `
        <div class="topo-node ok">
            <div class="topo-label">Application Load Balancer</div>
            <div class="topo-sub">Healthy — forwarding traffic</div>
        </div>
        <div class="topo-arrow">↓</div>
        <div class="topo-node warning">
            <div class="topo-label">EKS Pods (api-server)</div>
            <div class="topo-sub">2/3 recovering — 1 still failing (network timeout)</div>
        </div>
        <div class="topo-arrow">↓ image pull</div>
        <div class="topo-node ok">
            <div class="topo-label">Amazon ECR</div>
            <div class="topo-sub">✅ IAM permissions fixed — pull authorized</div>
        </div>
        <div class="topo-arrow">↓ network</div>
        <div class="topo-node error">
            <div class="topo-label">NetworkPolicy (Egress)</div>
            <div class="topo-sub">⚠️ Blocking outbound to ECR VPC endpoint CIDR</div>
        </div>
    `;
}

// ===== FIX CLUSTER VIEW =====
function fixClusterView() {
    // Stop the error log stream
    stopLogStreaming();

    // Add resolution logs
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const resolutionLogs = [
        { time, level: 'info', pod: 'api-server-7d4f8', msg: 'Successfully pulled image "123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest"' },
        { time, level: 'info', pod: 'api-server-a3c21', msg: 'Started container api-server' },
        { time, level: 'info', pod: 'worker-bf892', msg: 'Started container worker' },
        { time, level: 'info', pod: 'endpoint-ctrl', msg: 'Endpoints api-service updated: 3 ready, 0 not ready' },
    ];
    resolutionLogs.forEach(l => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = formatLog(l);
        logStream.appendChild(entry);
    });
    logStream.scrollTop = logStream.scrollHeight;

    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'healthy', label: 'Recovered' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'healthy', label: 'Recovered' },
        { name: 'node-3a', status: 'healthy', label: 'Recovered' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'healthy', label: 'Recovered' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');

    document.getElementById('restart-count').textContent = '0';
    document.getElementById('restart-count').className = 'stat-value';
    document.querySelector('.cluster-status').textContent = '● Healthy';
    document.querySelector('.cluster-status').className = 'cluster-status';
    document.querySelector('.cluster-status').style.color = 'var(--accent-green)';
    document.querySelector('.cluster-status').style.background = 'rgba(76,175,80,0.15)';
}

// ===== MANUAL INPUT =====
document.getElementById('send-btn').addEventListener('click', sendCustomerMessage);
document.getElementById('customer-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCustomerMessage();
});

function sendCustomerMessage() {
    const input = document.getElementById('customer-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage('customer', 'You', text);
    input.value = '';

    // If we're waiting for customer input, advance scenario
    const awaitStep = scenario[currentScenarioIndex];
    if (awaitStep && awaitStep.action === 'await_customer') {
        if (awaitStep.trail) addTrailEntry(awaitStep.trail);
        quickResponses.innerHTML = '';
        currentScenarioIndex++;
        processNextStep();
    }
}


// ===== RESIZABLE PANELS =====
function initResize() {
    const handle1 = document.getElementById('resize-handle-1');
    const handle2 = document.getElementById('resize-handle-2');
    const chatPanel = document.getElementById('panel-chat');
    const contextPanel = document.getElementById('panel-context');
    const engineerPanelEl = document.getElementById('engineer-panel');
    const workspaceBody = document.getElementById('workspace-body');

    let isResizing = false;
    let currentHandle = null;

    function startResize(handle) {
        return function(e) {
            isResizing = true;
            currentHandle = handle;
            handle.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        };
    }

    handle1.addEventListener('mousedown', startResize(handle1));
    handle2.addEventListener('mousedown', startResize(handle2));

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const bodyRect = workspaceBody.getBoundingClientRect();
        const mouseX = e.clientX - bodyRect.left;
        const totalWidth = bodyRect.width;

        if (currentHandle === handle1) {
            // Resizing between chat and context
            const chatWidth = Math.max(200, Math.min(mouseX - 2, totalWidth * 0.6));
            chatPanel.style.flex = 'none';
            chatPanel.style.width = chatWidth + 'px';
        } else if (currentHandle === handle2) {
            // Resizing between context and engineer
            const engineerWidth = Math.max(200, Math.min(totalWidth - mouseX - 2, totalWidth * 0.5));
            engineerPanelEl.style.flex = 'none';
            engineerPanelEl.style.width = engineerWidth + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            if (currentHandle) currentHandle.classList.remove('active');
            currentHandle = null;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

initResize();
