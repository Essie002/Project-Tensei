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
        text: `Hi — your CloudWatch alarm <code>EKS-PodRestart-Critical</code> triggered 12 minutes ago. Here's what the alarm data shows:<br><br><strong>Summary:</strong><br>1. <span class="highlight">47 pod restarts</span> across 3 pods in <code>prod-east-1</code><br>2. All failing with <code>ImagePullBackOff</code> errors<br>3. Pattern started at 10:29 — coincides with a recent deployment<br><br>Would you like me to help investigate this? I can suggest diagnostic commands for you to run.`,
        trail: { text: 'CloudWatch alarm data reviewed — 47 pod restarts, ImagePullBackOff', actor: 'AI Agent' }
    },
    // Step 1: Quick response options
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, help me investigate", id: 'confirm' },
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
        text: `Based on the alarm data and error pattern, I'd like to check three things:<br><br>1. 🔍 ECR repository permissions<br>2. 🔍 Image tag existence in the registry<br>3. 🔍 Node IAM role configuration<br><br>I'll suggest commands in the Terminal tab for you to run. The results will appear in the Context Panel as you execute them.`,
        trail: { text: 'AI recommending checks: ECR permissions, image tag, IAM role', actor: 'AI Agent' }
    },
    // Step 4: First finding
    {
        delay: 3000,
        action: 'ai_typing'
    },
    {
        delay: 2000,
        action: 'ai_message',
        text: `<span class="highlight">Root cause identified.</span><br><br><strong>Problem:</strong> Based on the error logs, your node IAM role (<code>eks-node-role-prod</code>) appears to be missing ECR pull permissions.<br><br><strong>Evidence from logs:</strong><br>1. <code>403 Forbidden</code> responses when pulling from ECR<br>2. <code>ecr:GetDownloadUrlForLayer</code> — permission denied<br>3. <code>ecr:BatchGetImage</code> — permission denied<br><br><strong>Impact:</strong> Nodes cannot authenticate to pull the container image → every pod restart fails with ImagePullBackOff.<br><br>I have a suggested fix ready. Would you like to see it?`,
        trail: { text: 'ROOT CAUSE: Node IAM role missing ECR pull permissions', actor: 'AI Agent' }
    },
    // Step 5: Quick response for fix
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Show me the fix", id: 'show' },
            { text: "I'll investigate manually", id: 'manual' }
        ]
    },
    // Step 6: Customer asks to see fix
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'show',
        customerText: "Show me what needs to change.",
        trail: { text: 'Customer requested: show proposed fix', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 7: AI suggests the command (doesn't run it)
    {
        delay: 1500,
        action: 'ai_typing'
    },
    {
        delay: 1000,
        action: 'suggest_command',
        command: 'aws iam attach-role-policy --role-name eks-node-role-prod --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly',
        source: 'AI Agent',
        description: 'Attach ECR read-only policy to node role'
    },
    {
        delay: 500,
        action: 'ai_message',
        text: `Here's my recommended fix. I've loaded the command into your <strong>Sandbox Terminal</strong> (Terminal tab in Context Panel):<br><br><strong>Command:</strong><br><code>aws iam attach-role-policy --role-name eks-node-role-prod --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly</code><br><br><strong>What it does:</strong><br>1. Attaches the AWS-managed <code>AmazonEC2ContainerRegistryReadOnly</code> policy<br>2. Grants read-only ECR pull permissions to your node role<br>3. No write or delete access — safe for production<br><br><strong>Next step:</strong> Review and run the command in the Terminal when ready. I'll monitor for pod recovery.`,
        trail: { text: 'AI suggested fix: attach ECR policy to node role (awaiting customer execution)', actor: 'AI Agent' }
    },
    // Step 8: Wait for customer to run the command
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Done — I've run it", id: 'ran_command' },
            { text: "What does this policy include?", id: 'show_policy' }
        ]
    },
    // Step 9: Customer confirms they ran it
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'ran_command',
        customerText: "Done, I've run the command.",
        trail: { text: 'Customer executed: IAM policy attachment', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 10: AI confirms and surfaces secondary issue
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
        text: `Policy confirmed attached. ✅ Monitoring pod recovery...<br><br><strong>Status update:</strong><br>1. ✅ ECR permissions — fixed<br>2. ⏳ Pods retrying image pull — in progress<br><br><em>However</em> — I've identified a potential secondary issue:<br><br><strong>Concern:</strong> A NetworkPolicy egress rule may also be blocking image pulls from the ECR endpoint.<br><strong>Confidence:</strong> <span class="highlight">45%</span> — not high enough for me to recommend a fix alone.<br><br>I'd like to bring in a networking specialist to verify. Would you like me to connect you with someone?`,
        trail: { text: 'ECR permissions confirmed ✅ — Secondary issue: NetworkPolicy (45% confidence)', actor: 'AI Agent' }
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
        text: `Hi there! I'm Sarah, a networking specialist. I can see this has been a stressful one — production app down is never fun. Let's get you fully sorted.<br><br>I've reviewed everything the AI investigated so far. The ECR permission fix looks good. Let me now focus on the NetworkPolicy angle — I'll have an answer for you shortly.`
    },
    // Step 15: Engineer finding
    {
        delay: 3500,
        action: 'engineer_message',
        text: `<strong>Finding confirmed:</strong><br><br>Your NetworkPolicy <code>api-egress</code> restricts outbound traffic to a specific set of CIDR blocks, but it <strong>does not include</strong> the ECR VPC endpoint range (<code>10.0.1.0/24</code>).<br><br><strong>What this means:</strong><br>Even though IAM permissions are now correct, the pod's network traffic is being dropped before it reaches ECR.<br><br><strong>Suggested fix:</strong><br>I've loaded a <code>kubectl patch</code> command into your Terminal that adds the ECR endpoint CIDR to your egress allowlist.<br><br><strong>Steps:</strong><br>1. Switch to the Terminal tab<br>2. Review the command (click it from Suggested Commands to load)<br>3. Run it when you're satisfied<br><br>This only opens port 443 to that specific CIDR — no broad egress changes. Let me know when you've run it.`,
        trail: { text: 'Sarah confirmed: NetworkPolicy blocking ECR VPC endpoint egress', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 15b: Engineer suggests command
    {
        delay: 1000,
        action: 'suggest_command',
        command: 'kubectl patch networkpolicy api-egress -n default --type=json -p \'[{"op":"add","path":"/spec/egress/-","value":{"to":[{"ipBlock":{"cidr":"10.0.1.0/24"}}],"ports":[{"port":443,"protocol":"TCP"}]}}]\'',
        source: 'Sarah K.',
        description: 'Add ECR VPC endpoint CIDR to NetworkPolicy egress rules'
    },
    // Step 16: Final quick options
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Done — I've run it", id: 'final_fix' },
            { text: "Explain this command first", id: 'explain_cmd' }
        ]
    },
    // Step 17: Resolution
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'final_fix',
        customerText: "Applied. Let me know if it looks good."
    },
    {
        delay: 2000,
        action: 'engineer_message',
        text: `I can see the egress rule is now in place. ✅ Pods are recovering — let me monitor for a moment to confirm full stability.`
    },
    {
        delay: 3000,
        action: 'engineer_message',
        text: `All clear. ✅ All 3 pods are running healthy and pulling images without issues.<br><br><strong>📋 Session Summary:</strong><br><br><strong>What was wrong:</strong><br>1. <strong>Primary issue:</strong> The node IAM role (<code>eks-node-role-prod</code>) was missing ECR pull permissions — pods couldn't authenticate to download container images.<br>2. <strong>Secondary issue:</strong> A NetworkPolicy egress rule was blocking outbound traffic on port 443 to the ECR VPC endpoint CIDR — even with correct permissions, the network layer was dropping the connection.<br><br><strong>What was fixed:</strong><br>1. Attached <code>AmazonEC2ContainerRegistryReadOnly</code> policy to the node role<br>2. Patched NetworkPolicy <code>api-egress</code> to allow TCP/443 to <code>10.0.1.0/24</code><br><br><strong>📖 Helpful AWS documentation:</strong><br>• <a href="#">Amazon ECR: Private registry authentication</a><br>• <a href="#">Amazon EKS: Cluster IAM role permissions</a><br>• <a href="#">Kubernetes NetworkPolicy: Egress rules best practices</a><br><br><strong>💡 Recommendation:</strong> Consider adding ECR VPC endpoint CIDRs to your NetworkPolicy templates to prevent this from recurring on future deployments.<br><br>It was great working with you — don't hesitate to reach out if anything else comes up! 👋`
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `All pods confirmed healthy. ✅ Your application is back online. 🎉<br><br><strong>Resolution summary:</strong><br>1. ✅ Fixed IAM ECR permissions — attached <code>AmazonEC2ContainerRegistryReadOnly</code> to node role<br>2. ✅ Fixed NetworkPolicy egress — added ECR VPC endpoint CIDR to allowlist<br><br><strong>Root causes:</strong><br>• Primary: Node role lacked ECR pull permissions after recent role update<br>• Secondary: NetworkPolicy blocked outbound traffic to ECR VPC endpoint<br><br>Is there anything else I can help with?`,
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

        case 'suggest_command':
            addSuggestedCommand(step.command, step.source, step.description);
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
        // Advance the scenario past the await_customer step
        const awaitStep = scenario[currentScenarioIndex];
        if (awaitStep && awaitStep.action === 'await_customer') {
            if (awaitStep.trail) addTrailEntry(awaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        }
        return;
    }

    if (id === 'manual') {
        addTrailEntry({ text: 'Customer chose: manual investigation', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem. Here's what you need to do:<br><br><strong>Steps to fix:</strong><br>1. Go to <strong>IAM → Roles → eks-node-role-prod</strong><br>2. Click "Attach policies"<br>3. Search for <code>AmazonEC2ContainerRegistryReadOnly</code><br>4. Attach the policy<br>5. Wait 30–60 seconds for pods to retry the image pull<br><br>I'll keep monitoring. Let me know once applied and I'll verify recovery.<br><br><em>Note:</em> I've also identified a potential secondary issue with a NetworkPolicy egress rule (confidence: <span class="highlight">45%</span>). Want me to bring in a networking specialist to verify?`);
            addTrailEntry({ text: 'AI provided manual fix steps — monitoring for recovery', actor: 'AI Agent' });
            showQuickOptions([
                { text: "Yes, bring someone in", id: 'escalate' },
                { text: "Let's wait and see first", id: 'wait' }
            ]);
            currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'escalate');
        }, 2000);
        return;
    }

    if (id === 'more') {
        addTrailEntry({ text: 'Customer requested more details on errors', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => showTypingIndicator(), 500);
        setTimeout(() => {
            removeTypingIndicator();
            addMessage('ai', 'AI Agent', `Here's the full breakdown:<br><br><strong>Affected pods (3):</strong><br>1. <code>api-server-7d4f8</code> — CrashLoopBackOff<br>2. <code>api-server-a3c21</code> — CrashLoopBackOff<br>3. <code>worker-bf892</code> — ImagePullBackOff<br><br><strong>Error pattern:</strong><br>• All failing with <code>ImagePullBackOff</code> → nodes cannot download the container image from ECR<br>• Logs show <code>403 Forbidden</code> when pulling from your ECR registry<br><br><strong>Timeline:</strong><br>• Started 12 minutes ago at 10:29<br>• Coincides with a deployment update to <code>prod-east-1</code><br><br>This looks like a permissions issue — the nodes lost the ability to pull images. Want me to dig into the IAM configuration?`);
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
            addMessage('ai', 'AI Agent', `Understood. I'll keep monitoring pod recovery and flag if the issue persists.`);
        }, 1000);
        setTimeout(() => {
            // Sync: update context panel to show partial recovery
            showPartialRecovery();
            addMessage('ai', 'AI Agent', `<strong>Status update:</strong><br><br>1. ✅ <code>api-server-7d4f8</code> — image pulled successfully, container running<br>2. ✅ <code>worker-bf892</code> — image pulled successfully, container running<br>3. ❌ <code>api-server-a3c21</code> on <code>node-3a</code> — still failing<br><br><strong>Error on failing pod:</strong><br><code>dial tcp 10.0.1.45:443 — connection timed out</code><br><br><strong>Analysis:</strong> This is a network-level block, not a permissions issue. Consistent with a NetworkPolicy egress rule preventing outbound traffic to the ECR VPC endpoint.<br><br>I'd recommend bringing in a networking specialist to confirm. Want me to connect you?`);
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

    if (id === 'show_policy') {
        addTrailEntry({ text: 'Customer requested policy details', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `The <code>AmazonEC2ContainerRegistryReadOnly</code> policy grants:\n\n• <code>ecr:GetDownloadUrlForLayer</code>\n• <code>ecr:BatchGetImage</code>\n• <code>ecr:GetAuthorizationToken</code>\n• <code>ecr:BatchCheckLayerAvailability</code>\n• <code>ecr:DescribeRepositories</code>\n\n<strong>Scope:</strong> Read-only. No ability to push, delete, or modify images. Safe to apply to node roles.\n\nGo ahead and run the command in the Terminal when you're ready.`);
            showQuickOptions([
                { text: "Done — I've run it", id: 'ran_command' }
            ]);
        }, 1500);
        return;
    }

    if (id === 'explain_cmd') {
        addTrailEntry({ text: 'Customer requested command explanation', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addEngineerMessage(`Sure! Here's what that kubectl patch does:\n\n• <strong>Target:</strong> NetworkPolicy named "api-egress" in the default namespace\n• <strong>Action:</strong> Adds a new egress rule allowing outbound TCP/443 to the CIDR 10.0.1.0/24\n• <strong>Why 10.0.1.0/24:</strong> That's your VPC endpoint range for ECR — the pod needs to reach that IP to pull images\n• <strong>Effect:</strong> Only opens port 443 to that specific CIDR. No broad egress changes.\n\nIt's safe to run. Let me know once applied.`);
            showQuickOptions([
                { text: "Done — I've run it", id: 'final_fix' }
            ]);
        }, 1500);
        return;
    }

    if (id === 'ran_command') {
        // Advance to the next step (same as confirming fix)
        const awaitStep = scenario[currentScenarioIndex];
        if (awaitStep && awaitStep.action === 'await_customer') {
            if (awaitStep.trail) addTrailEntry(awaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        }
        return;
    }

    if (id === 'manual_end') {
        addTrailEntry({ text: 'Customer chose to investigate independently', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem. I've loaded a diagnostic command into your Terminal: <code>kubectl describe pod api-server-a3c21 -n default</code>. Check the Terminal tab.\n\nI'll stay here if you need me. Just let me know.`);
            addSuggestedCommand('kubectl describe pod api-server-a3c21 -n default', 'AI Agent', 'Inspect failing pod events and status');
        }, 1000);
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


// ===== SANDBOX TERMINAL =====
const terminalOutput = document.getElementById('terminal-output');
const terminalInput = document.getElementById('terminal-input');
const terminalRunBtn = document.getElementById('terminal-run-btn');
const suggestedCommandsEl = document.getElementById('suggested-commands');

function addSuggestedCommand(command, source, description) {
    const cmdEl = document.createElement('div');
    cmdEl.className = 'suggested-cmd';
    cmdEl.innerHTML = `
        <div style="flex:1">
            <div class="suggested-cmd-text">${command}</div>
            <div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">${description}</div>
        </div>
        <span class="suggested-cmd-source">${source}</span>
        <span class="suggested-cmd-status pending">Pending</span>
    `;
    cmdEl.addEventListener('click', () => {
        // Load command into terminal input
        terminalInput.value = command;
        // Switch to terminal tab
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelector('[data-tab="terminal"]').classList.add('active');
        document.querySelectorAll('.context-view').forEach(v => v.classList.remove('active'));
        document.getElementById('view-terminal').classList.add('active');
        // Mark as loaded
        cmdEl.querySelector('.suggested-cmd-status').textContent = 'Loaded';
        cmdEl.querySelector('.suggested-cmd-status').className = 'suggested-cmd-status approved';
        // Flash the terminal tab
        document.querySelector('[data-tab="terminal"]').style.background = 'var(--accent-green)';
        setTimeout(() => {
            document.querySelector('[data-tab="terminal"]').style.background = '';
        }, 1000);
    });
    suggestedCommandsEl.appendChild(cmdEl);

    // Flash the terminal tab to draw attention
    const termTab = document.querySelector('[data-tab="terminal"]');
    termTab.style.background = 'var(--accent-orange)';
    termTab.style.color = '#000';
    setTimeout(() => {
        termTab.style.background = '';
        termTab.style.color = '';
    }, 2000);
}

// Simulated terminal command execution
const terminalResponses = {
    'aws iam attach-role-policy': [
        { type: 'output', text: 'Attaching policy to role eks-node-role-prod...' },
        { type: 'success', text: '✓ Policy AmazonEC2ContainerRegistryReadOnly attached successfully.' },
        { type: 'output', text: 'Effective immediately. Pods will retry image pull on next restart cycle.' },
    ],
    'kubectl patch networkpolicy': [
        { type: 'output', text: 'networkpolicy.networking.k8s.io/api-egress patched' },
        { type: 'success', text: '✓ Egress rule added: allow TCP/443 to 10.0.1.0/24 (ECR VPC endpoint)' },
        { type: 'output', text: 'Pods affected: api-server-a3c21 (will retry on next cycle)' },
    ],
    'kubectl get pods': [
        { type: 'output', text: 'NAME                    READY   STATUS             RESTARTS   AGE' },
        { type: 'output', text: 'api-server-7d4f8        1/1     Running            48         2h' },
        { type: 'output', text: 'api-server-a3c21        0/1     ImagePullBackOff   52         2h' },
        { type: 'output', text: 'worker-bf892            1/1     Running            12         2h' },
    ],
    'kubectl describe pod': [
        { type: 'output', text: 'Events:' },
        { type: 'output', text: '  Warning  Failed     2m   kubelet  Failed to pull image: dial tcp 10.0.1.45:443 — connection timed out' },
        { type: 'output', text: '  Warning  Failed     1m   kubelet  Back-off pulling image' },
        { type: 'error', text: '  Normal   BackOff    30s  kubelet  Back-off restarting failed container' },
    ],
};

function runTerminalCommand(command) {
    if (!command.trim()) return;

    // Show the command
    const cmdLine = document.createElement('div');
    cmdLine.className = 'terminal-line command';
    cmdLine.textContent = command;
    terminalOutput.appendChild(cmdLine);

    // Find matching response
    let response = null;
    for (const key of Object.keys(terminalResponses)) {
        if (command.includes(key)) {
            response = terminalResponses[key];
            break;
        }
    }

    if (response) {
        // Simulate delayed output
        response.forEach((line, i) => {
            setTimeout(() => {
                const el = document.createElement('div');
                el.className = `terminal-line ${line.type}`;
                el.textContent = line.text;
                terminalOutput.appendChild(el);
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }, 500 + (i * 400));
        });
    } else {
        setTimeout(() => {
            const el = document.createElement('div');
            el.className = 'terminal-line error';
            el.textContent = `command not found: ${command.split(' ')[0]}`;
            terminalOutput.appendChild(el);
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }, 300);
    }

    // Update suggested command status if it matches
    suggestedCommandsEl.querySelectorAll('.suggested-cmd').forEach(cmd => {
        const cmdText = cmd.querySelector('.suggested-cmd-text').textContent;
        if (command.includes(cmdText.substring(0, 30)) || cmdText.includes(command.substring(0, 30))) {
            cmd.querySelector('.suggested-cmd-status').textContent = 'Executed';
            cmd.querySelector('.suggested-cmd-status').className = 'suggested-cmd-status run';
        }
    });

    terminalInput.value = '';
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

terminalRunBtn.addEventListener('click', () => runTerminalCommand(terminalInput.value));
terminalInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runTerminalCommand(terminalInput.value);
});

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
